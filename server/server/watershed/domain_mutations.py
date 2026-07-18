from dataclasses import dataclass
from itertools import islice

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import connection, transaction

from server.watershed.fingerprint_contract import canonical_sha256
from server.watershed.identity import activate_run_alias
from server.watershed.loaders.config import GeometryConfig
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
    WatershedIdentity,
    WatershedRunAlias,
)
from server.watershed.release_ledger import activate_release
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


class ReconciliationError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmptyBaseApplyResult:
    watershed_rows: int
    subcatchment_rows: int
    channel_rows: int
    capability_rows: int
    maximum_batch_rows: int


@dataclass(frozen=True)
class ReconciliationResult:
    added: int
    changed: int
    removed: int
    retained: int
    child_rows_created: int
    child_rows_updated: int
    child_rows_deleted: int
    capability_rows: int


WATERSHED_FIELDS = frozenset(WATERSHED_FIELD_SOURCES) - {"runid", "geom"}
SUBCATCHMENT_FIELDS = frozenset(
    field
    for mapping in (HILLSLOPES_FIELD_MAP, SOILS_FIELD_MAP, LANDUSE_FIELD_MAP)
    for field, _, _ in mapping
)
RECONCILIATION_ADVISORY_LOCK = 0x5557414442323300


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


def _watershed_values(staged, *, derive_simplified=False):
    unexpected = set(staged.metadata) - WATERSHED_FIELDS
    if unexpected:
        raise EmptyBaseMutationError("Staged watershed metadata is not canonical.")
    simplified = staged.simplified_geom
    if derive_simplified and simplified is None:
        simplified = staged.geom.simplify(
            GeometryConfig.from_environment().simplify_tolerance,
            preserve_topology=True,
        )
        if isinstance(simplified, Polygon):
            simplified = MultiPolygon(simplified)
        if not isinstance(simplified, MultiPolygon) or simplified.empty:
            raise ReconciliationError("Simplified watershed geometry is invalid.")
        simplified.srid = 4326
    return {
        **{field: None for field in WATERSHED_FIELDS},
        **staged.metadata,
        "runid": staged.runid,
        "logical_watershed": staged.watershed_identity,
        "geom": staged.geom,
        "simplified_geom": simplified,
    }


def _subcatchment_values(staged, watershed_id):
    unexpected = set(staged.attributes) - SUBCATCHMENT_FIELDS
    if unexpected:
        raise EmptyBaseMutationError(
            "Staged subcatchment attributes are not canonical."
        )
    return {
        **{field: None for field in SUBCATCHMENT_FIELDS},
        **staged.attributes,
        "watershed_id": watershed_id,
        "logical_watershed": staged.watershed_identity,
        "topazid": staged.topazid,
        "weppid": staged.weppid,
        "geom": staged.geom,
    }


def _channel_values(staged, watershed_id):
    if staged.attributes:
        raise EmptyBaseMutationError("Staged channel attributes are not canonical.")
    return {
        "watershed_id": watershed_id,
        "logical_watershed": staged.watershed_identity,
        "topazid": staged.topazid,
        "weppid": staged.weppid,
        "order": staged.order,
        "geom": staged.geom,
    }


def _capability_row(staged):
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
    return row


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
            if not WatershedRunAlias.objects.filter(
                runid=staged.runid,
                watershed_identity=staged.watershed_identity,
                is_current=True,
            ).exists():
                raise EmptyBaseMutationError("Current run alias is absent or inconsistent.")
            row = Watershed(
                **_watershed_values(staged, derive_simplified=True)
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
            row = Subcatchment(
                **_subcatchment_values(staged, staged.run_state.runid)
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
            row = Channel(**_channel_values(staged, staged.run_state.runid))
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
            rows.append(_capability_row(staged))
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


def _lock_reconciliation_scope(identity_ids):
    list(
        Watershed.objects.select_for_update()
        .filter(logical_watershed_id__in=identity_ids)
        .order_by("runid")
    )
    list(
        Subcatchment.objects.select_for_update()
        .filter(logical_watershed_id__in=identity_ids)
        .order_by("logical_watershed_id", "topazid")
    )
    list(
        Channel.objects.select_for_update()
        .filter(logical_watershed_id__in=identity_ids)
        .order_by("logical_watershed_id", "topazid", "weppid", "order")
    )
    list(
        WatershedIdentity.objects.select_for_update()
        .filter(pk__in=identity_ids)
        .order_by("watershed_key")
    )


def _reconcile_subcatchments(attempt, staged_watershed, *, batch_size):
    identity = staged_watershed.watershed_identity
    existing = {
        row.topazid: row
        for row in Subcatchment.objects.filter(logical_watershed=identity)
    }
    staged_rows = list(
        StagedSubcatchment.objects.filter(
            attempt=attempt,
            watershed_identity=identity,
        ).order_by("topazid")
    )
    staged_keys = {row.topazid for row in staged_rows}
    deleted, _ = Subcatchment.objects.filter(
        logical_watershed=identity
    ).exclude(topazid__in=staged_keys).delete()
    created = []
    updated = []
    update_fields = (
        "watershed",
        "logical_watershed",
        "weppid",
        "geom",
        *sorted(SUBCATCHMENT_FIELDS),
    )
    for staged in staged_rows:
        values = _subcatchment_values(staged, staged_watershed.runid)
        row = existing.get(staged.topazid)
        if row is None:
            created.append(Subcatchment(**values))
            continue
        for field, value in values.items():
            setattr(row, field, value)
        row.full_clean(validate_unique=False, validate_constraints=False)
        updated.append(row)
    Subcatchment.objects.bulk_create(created, batch_size=batch_size)
    Subcatchment.objects.bulk_update(
        updated,
        update_fields,
        batch_size=batch_size,
    )
    return len(created), len(updated), deleted


def _reconcile_channels(attempt, staged_watershed, *, batch_size):
    identity = staged_watershed.watershed_identity
    existing = {
        (row.topazid, row.weppid, row.order): row
        for row in Channel.objects.filter(logical_watershed=identity)
    }
    staged_rows = list(
        StagedChannel.objects.filter(
            attempt=attempt,
            watershed_identity=identity,
        ).order_by("topazid", "weppid", "order")
    )
    staged_keys = {(row.topazid, row.weppid, row.order) for row in staged_rows}
    obsolete_ids = [
        row.pk
        for key, row in existing.items()
        if key not in staged_keys
    ]
    deleted, _ = Channel.objects.filter(pk__in=obsolete_ids).delete()
    created = []
    updated = []
    update_fields = ("watershed", "logical_watershed", "geom")
    for staged in staged_rows:
        key = (staged.topazid, staged.weppid, staged.order)
        values = _channel_values(staged, staged_watershed.runid)
        row = existing.get(key)
        if row is None:
            created.append(Channel(**values))
            continue
        for field, value in values.items():
            setattr(row, field, value)
        row.full_clean(validate_unique=False, validate_constraints=False)
        updated.append(row)
    Channel.objects.bulk_create(created, batch_size=batch_size)
    Channel.objects.bulk_update(updated, update_fields, batch_size=batch_size)
    return len(created), len(updated), deleted


def _activate_target_alias(staged):
    current = WatershedRunAlias.objects.filter(
        watershed_identity=staged.watershed_identity,
        is_current=True,
    ).first()
    if current is None or current.runid != staged.runid:
        activate_run_alias(staged.watershed_identity, staged.runid)


def _replace_target_capabilities(attempt, *, batch_size):
    RunCapability.objects.filter(run_state__release=attempt.release).delete()
    rows = [
        _capability_row(staged)
        for staged in StagedRunCapability.objects.filter(attempt=attempt)
        .select_related("run_state", "watershed_identity")
        .order_by("run_state__runid", "capability_type")
    ]
    RunCapability.objects.bulk_create(rows, batch_size=batch_size)
    return len(rows)


def _assert_reviewed_plan(attempt, deployment_plan, source_forward_plan=None):
    digest = canonical_sha256(deployment_plan)
    if not (
        digest == attempt.reviewed_plan_sha256 == attempt.actual_plan_sha256
    ):
        raise ReconciliationError("Actual and reviewed plan digests differ.")
    if attempt.previous_active_release_id is None:
        raise ReconciliationError("Populated reconciliation requires a reviewed base.")
    from server.watershed.planner import (
        plan_exact_inverse,
        plan_forward,
    )

    regenerated = plan_forward(
        attempt.previous_active_release,
        attempt.release,
        allow_large_removals=True,
    )
    if deployment_plan.get("plan_kind") == "forward":
        if regenerated != deployment_plan or source_forward_plan is not None:
            raise ReconciliationError("Regenerated forward plan differs from review.")
    elif deployment_plan.get("plan_kind") == "exact-inverse":
        if (
            source_forward_plan is None
            or plan_exact_inverse(source_forward_plan) != deployment_plan
        ):
            raise ReconciliationError("Exact inverse is not bound to its forward plan.")
        comparable_fields = (
            "fingerprint_version",
            "data_contract",
            "identity_contract",
            "supported_migration",
            "materializer",
            "base",
            "target",
            "actions",
            "expected_row_delta",
        )
        if any(
            regenerated[field] != deployment_plan[field]
            for field in comparable_fields
        ):
            raise ReconciliationError("Regenerated inverse direction differs from review.")
    else:
        raise ReconciliationError("Unsupported deployment plan kind.")
    from server.watershed.release_validation import compute_serving_fingerprints

    observed = compute_serving_fingerprints(attempt.previous_active_release)
    expected_capabilities = attempt.previous_active_release.run_states.filter(
        capability_fingerprint__isnull=False
    ).count()
    if (
        observed.watershed_rows
        != attempt.previous_active_release.actual_watersheds
        or observed.subcatchment_rows
        != attempt.previous_active_release.actual_subcatchments
        or observed.channel_rows != attempt.previous_active_release.actual_channels
        or observed.capability_rows != expected_capabilities
    ):
        raise ReconciliationError("Observed base row counts differ from review.")
    return deployment_plan


@transaction.atomic
def apply_staged_release(
    attempt,
    deployment_plan,
    *,
    source_forward_plan=None,
    batch_size=1000,
):
    if batch_size < 1:
        raise ValueError("Batch size must be positive.")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            [RECONCILIATION_ADVISORY_LOCK],
        )
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
    ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    attempt = (
        DataReleaseAttempt.objects.select_for_update()
        .select_related("release")
        .get(pk=attempt.pk)
    )
    if attempt.status != DataReleaseAttempt.Status.APPLYING:
        raise ReconciliationError("Reconciliation requires an applying attempt.")
    state = DataReleaseStagingState.objects.select_for_update().get(attempt=attempt)
    if state.status != DataReleaseStagingState.Status.READY:
        raise ReconciliationError("Reconciliation requires READY staging.")
    _assert_exact_staging(attempt, state)
    plan = _assert_reviewed_plan(
        attempt,
        deployment_plan,
        source_forward_plan,
    )

    base_states = {
        row.watershed_identity.watershed_key: row
        for row in attempt.previous_active_release.run_states.select_related(
            "watershed_identity"
        )
    }
    target_states = {
        row.watershed_identity.watershed_key: row
        for row in attempt.release.run_states.select_related("watershed_identity")
    }
    staged_watersheds = {
        row.watershed_identity.watershed_key: row
        for row in StagedWatershed.objects.filter(attempt=attempt).select_related(
            "watershed_identity"
        )
    }
    identity_ids = {
        row.watershed_identity_id for row in (*base_states.values(), *target_states.values())
    }
    _lock_reconciliation_scope(identity_ids)

    counts = {operation: 0 for operation in ("add", "change", "remove", "retain")}
    children = {"created": 0, "updated": 0, "deleted": 0}
    for action in plan["actions"]:
        key = action["watershed_key"]
        operation = action["operation"]
        counts[operation] += 1
        before = base_states.get(key)
        after = target_states.get(key)
        existing = Watershed.objects.filter(
            logical_watershed=before.watershed_identity if before else after.watershed_identity
        ).first()

        if operation == "remove":
            if existing is None or existing.runid != before.runid:
                raise ReconciliationError("Reviewed removal is absent or changed.")
            deleted, _ = Channel.objects.filter(
                logical_watershed=before.watershed_identity
            ).delete()
            children["deleted"] += deleted
            deleted, _ = Subcatchment.objects.filter(
                logical_watershed=before.watershed_identity
            ).delete()
            children["deleted"] += deleted
            existing.delete()
            before.watershed_identity.status = WatershedIdentity.Status.RETIRED
            before.watershed_identity.save(update_fields=("status",))
            WatershedRunAlias.objects.filter(
                watershed_identity=before.watershed_identity
            ).update(is_current=False)
            continue

        staged = staged_watersheds[key]
        identity = staged.watershed_identity
        if operation == "add":
            if existing is not None:
                raise ReconciliationError("Reviewed addition already has serving state.")
            watershed = Watershed(
                **_watershed_values(staged, derive_simplified=True)
            )
            watershed.full_clean(validate_unique=False, validate_constraints=False)
            watershed.save(force_insert=True)
            created, updated, deleted = _reconcile_subcatchments(
                attempt, staged, batch_size=batch_size
            )
            children["created"] += created
            children["updated"] += updated
            children["deleted"] += deleted
            created, updated, deleted = _reconcile_channels(
                attempt, staged, batch_size=batch_size
            )
            children["created"] += created
            children["updated"] += updated
            children["deleted"] += deleted
        else:
            if existing is None or existing.runid != before.runid:
                raise ReconciliationError("Reviewed retained state is absent or changed.")
            if existing.runid != staged.runid:
                Watershed.objects.filter(pk=existing.runid).update(runid=staged.runid)
                Subcatchment.objects.filter(logical_watershed=identity).update(
                    watershed_id=staged.runid
                )
                Channel.objects.filter(logical_watershed=identity).update(
                    watershed_id=staged.runid
                )
            updates = {}
            if "metadata" in action["change_channels"]:
                values = _watershed_values(staged)
                updates.update({field: values[field] for field in WATERSHED_FIELDS})
            if "geometry" in action["change_channels"]:
                values = _watershed_values(staged, derive_simplified=True)
                updates.update(
                    geom=values["geom"],
                    simplified_geom=values["simplified_geom"],
                )
            if updates:
                Watershed.objects.filter(logical_watershed=identity).update(**updates)
            if "children" in action["change_channels"]:
                created, updated, deleted = _reconcile_subcatchments(
                    attempt, staged, batch_size=batch_size
                )
                children["created"] += created
                children["updated"] += updated
                children["deleted"] += deleted
                created, updated, deleted = _reconcile_channels(
                    attempt, staged, batch_size=batch_size
                )
                children["created"] += created
                children["updated"] += updated
                children["deleted"] += deleted
        identity.status = WatershedIdentity.Status.ACTIVE
        identity.save(update_fields=("status",))
        _activate_target_alias(staged)

    capability_rows = _replace_target_capabilities(attempt, batch_size=batch_size)
    activate_release(attempt)
    from server.watershed.release_validation import compute_serving_fingerprints

    observed = compute_serving_fingerprints(attempt.release)
    if (
        observed.domain != attempt.release.domain_fingerprint
        or observed.watershed_rows != attempt.release.actual_watersheds
        or observed.subcatchment_rows != attempt.release.actual_subcatchments
        or observed.channel_rows != attempt.release.actual_channels
        or observed.capability_rows != capability_rows
    ):
        raise ReconciliationError("Reconciled serving state differs from the target ledger.")
    return ReconciliationResult(
        added=counts["add"],
        changed=counts["change"],
        removed=counts["remove"],
        retained=counts["retain"],
        child_rows_created=children["created"],
        child_rows_updated=children["updated"],
        child_rows_deleted=children["deleted"],
        capability_rows=capability_rows,
    )
