from dataclasses import dataclass
from itertools import islice

from django.db import connection

from server.watershed.loaders.writers import (
    HILLSLOPES_FIELD_MAP,
    LANDUSE_FIELD_MAP,
    SOILS_FIELD_MAP,
    WATERSHED_FIELD_SOURCES,
)
from server.watershed.models import (
    ActiveDataRelease,
    Channel,
    DataReleaseAttempt,
    RunCapability,
    Subcatchment,
    Watershed,
    WatershedRunAlias,
)
from server.watershed.runtime_capabilities import validate_runtime_configuration
from server.watershed.staging_models import (
    DataReleaseStagingState,
    StagedChannel,
    StagedRunCapability,
    StagedSubcatchment,
    StagedWatershed,
)


class EmptyBaseMutationError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmptyBaseApplyResult:
    watershed_rows: int
    subcatchment_rows: int
    channel_rows: int
    capability_rows: int
    maximum_batch_rows: int


WATERSHED_FIELDS = frozenset(WATERSHED_FIELD_SOURCES) - {"runid", "geom"}
SUBCATCHMENT_FIELDS = frozenset(
    field
    for mapping in (HILLSLOPES_FIELD_MAP, SOILS_FIELD_MAP, LANDUSE_FIELD_MAP)
    for field, _, _ in mapping
)


def _batches(queryset, batch_size):
    iterator = queryset.iterator(chunk_size=batch_size)
    while batch := list(islice(iterator, batch_size)):
        yield batch


def _assert_exact_staging(attempt, state):
    release = attempt.release
    expected = {
        "watershed_rows": release.actual_watersheds,
        "subcatchment_rows": release.actual_subcatchments,
        "channel_rows": release.actual_channels,
        "capability_rows": release.run_states.filter(
            capability_fingerprint__isnull=False
        ).count(),
    }
    observed = {
        "watershed_rows": state.watershed_rows,
        "subcatchment_rows": state.subcatchment_rows,
        "channel_rows": state.channel_rows,
        "capability_rows": state.capability_rows,
    }
    if observed != expected:
        raise EmptyBaseMutationError("Staging counts do not match the target release.")
    staged_models = (
        StagedWatershed,
        StagedSubcatchment,
        StagedChannel,
        StagedRunCapability,
    )
    if any(
        model.objects.filter(attempt=attempt)
        .exclude(validation_status=model.ValidationStatus.VALIDATED)
        .exists()
        for model in staged_models
    ):
        raise EmptyBaseMutationError("Every staged row must be validated.")
    staged_run_ids = set(
        StagedWatershed.objects.filter(attempt=attempt).values_list(
            "run_state_id", flat=True
        )
    )
    release_run_ids = set(
        release.run_states.values_list("pk", flat=True)
    )
    if staged_run_ids != release_run_ids:
        raise EmptyBaseMutationError("Staged watershed membership differs from release runs.")
    for run_state in release.run_states.iterator(chunk_size=1000):
        run_filter = {"attempt": attempt, "run_state": run_state}
        expected_run_counts = (
            1,
            run_state.actual_subcatchments,
            run_state.actual_channels,
            int(run_state.capability_fingerprint is not None),
        )
        observed_run_counts = (
            StagedWatershed.objects.filter(**run_filter).count(),
            StagedSubcatchment.objects.filter(**run_filter).count(),
            StagedChannel.objects.filter(**run_filter).count(),
            StagedRunCapability.objects.filter(**run_filter).count(),
        )
        if observed_run_counts != expected_run_counts:
            raise EmptyBaseMutationError(
                "Staged per-run counts do not match the release ledger."
            )


def _assert_empty_base(attempt):
    active = ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    if active.state != ActiveDataRelease.State.EMPTY or active.release_id is not None:
        raise EmptyBaseMutationError("The serving base is not EMPTY.")
    if attempt.previous_active_release_id is not None:
        raise EmptyBaseMutationError("The reviewed attempt base is not EMPTY.")
    if any(model.objects.exists() for model in (Watershed, Subcatchment, Channel)):
        raise EmptyBaseMutationError("The EMPTY pointer has populated serving rows.")
    if RunCapability.objects.filter(run_state__release=attempt.release).exists():
        raise EmptyBaseMutationError("Target capability rows already exist.")


def apply_staged_empty_base(attempt, *, batch_size=1000):
    if batch_size < 1:
        raise ValueError("Batch size must be positive.")
    if not connection.in_atomic_block:
        raise EmptyBaseMutationError(
            "EMPTY apply requires the caller's activation transaction."
        )
    attempt = (
        DataReleaseAttempt.objects.select_for_update()
        .select_related("release")
        .get(pk=attempt.pk)
    )
    if attempt.status != DataReleaseAttempt.Status.APPLYING:
        raise EmptyBaseMutationError("EMPTY apply requires an applying attempt.")
    state = DataReleaseStagingState.objects.select_for_update().get(attempt=attempt)
    if state.status != DataReleaseStagingState.Status.READY:
        raise EmptyBaseMutationError("EMPTY apply requires READY staging.")
    _assert_empty_base(attempt)
    _assert_exact_staging(attempt, state)

    maximum_batch = 0
    watershed_count = 0
    watershed_rows = (
        StagedWatershed.objects.filter(attempt=attempt)
        .select_related("watershed_identity")
        .order_by("runid")
    )
    for staged_batch in _batches(watershed_rows, batch_size):
        rows = []
        for staged in staged_batch:
            unexpected = set(staged.metadata) - WATERSHED_FIELDS
            if unexpected:
                raise EmptyBaseMutationError("Staged watershed metadata is not canonical.")
            if not WatershedRunAlias.objects.filter(
                runid=staged.runid,
                watershed_identity=staged.watershed_identity,
                is_current=True,
            ).exists():
                raise EmptyBaseMutationError("Current run alias is absent or inconsistent.")
            row = Watershed(
                runid=staged.runid,
                logical_watershed=staged.watershed_identity,
                geom=staged.geom,
                simplified_geom=staged.simplified_geom,
                **staged.metadata,
            )
            row.full_clean(validate_unique=False, validate_constraints=False)
            rows.append(row)
        Watershed.objects.bulk_create(rows, batch_size=batch_size)
        watershed_count += len(rows)
        maximum_batch = max(maximum_batch, len(rows))

    subcatchment_count = 0
    subcatchment_rows = (
        StagedSubcatchment.objects.filter(attempt=attempt)
        .select_related("run_state", "watershed_identity")
        .order_by("run_state__runid", "topazid")
    )
    for staged_batch in _batches(subcatchment_rows, batch_size):
        rows = []
        for staged in staged_batch:
            unexpected = set(staged.attributes) - SUBCATCHMENT_FIELDS
            if unexpected:
                raise EmptyBaseMutationError(
                    "Staged subcatchment attributes are not canonical."
                )
            row = Subcatchment(
                watershed_id=staged.run_state.runid,
                logical_watershed=staged.watershed_identity,
                topazid=staged.topazid,
                weppid=staged.weppid,
                geom=staged.geom,
                **staged.attributes,
            )
            row.full_clean(validate_unique=False, validate_constraints=False)
            rows.append(row)
        Subcatchment.objects.bulk_create(rows, batch_size=batch_size)
        subcatchment_count += len(rows)
        maximum_batch = max(maximum_batch, len(rows))

    channel_count = 0
    channel_rows = (
        StagedChannel.objects.filter(attempt=attempt)
        .select_related("run_state", "watershed_identity")
        .order_by("run_state__runid", "topazid", "weppid", "order")
    )
    for staged_batch in _batches(channel_rows, batch_size):
        rows = []
        for staged in staged_batch:
            if staged.attributes:
                raise EmptyBaseMutationError("Staged channel attributes are not canonical.")
            row = Channel(
                watershed_id=staged.run_state.runid,
                logical_watershed=staged.watershed_identity,
                topazid=staged.topazid,
                weppid=staged.weppid,
                order=staged.order,
                geom=staged.geom,
            )
            row.full_clean(validate_unique=False, validate_constraints=False)
            rows.append(row)
        Channel.objects.bulk_create(rows, batch_size=batch_size)
        channel_count += len(rows)
        maximum_batch = max(maximum_batch, len(rows))

    capability_count = 0
    capability_rows = (
        StagedRunCapability.objects.filter(attempt=attempt)
        .select_related("run_state", "watershed_identity")
        .order_by("run_state__runid", "capability_type")
    )
    for staged_batch in _batches(capability_rows, batch_size):
        rows = []
        for staged in staged_batch:
            row = RunCapability(
                run_state=staged.run_state,
                watershed_identity=staged.watershed_identity,
                capability_type=staged.capability_type,
                mode=staged.mode,
                durable_base_uri=staged.durable_base_uri,
                index_uri=staged.index_uri,
                index_sha256=staged.index_sha256,
                capability_fingerprint=staged.capability_fingerprint,
                runtime_configuration=staged.runtime_configuration,
            )
            row.full_clean(validate_unique=False, validate_constraints=False)
            validate_runtime_configuration(row)
            rows.append(row)
        RunCapability.objects.bulk_create(rows, batch_size=batch_size)
        capability_count += len(rows)
        maximum_batch = max(maximum_batch, len(rows))

    return EmptyBaseApplyResult(
        watershed_rows=watershed_count,
        subcatchment_rows=subcatchment_count,
        channel_rows=channel_count,
        capability_rows=capability_count,
        maximum_batch_rows=maximum_batch,
    )
