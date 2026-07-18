import shutil
from dataclasses import dataclass
from datetime import timedelta
from itertools import islice
from pathlib import Path

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from server.watershed.models import DataReleaseAttempt
from server.watershed.release_ledger import sanitize_failure_summary, transition_attempt
from server.watershed.staging_models import (
    DataReleaseStagingState,
    StagedChannel,
    StagedRunCapability,
    StagedSubcatchment,
    StagedWatershed,
)


class StagingError(RuntimeError):
    pass


class StagingLeaseError(StagingError):
    pass


@dataclass(frozen=True)
class SpaceBudget:
    artifact_bytes: int
    staging_bytes: int
    index_bytes: int
    backup_bytes: int
    wal_bytes: int
    margin_bytes: int

    def __post_init__(self):
        if any(value < 0 for value in self.components.values()):
            raise ValueError("Space budget components must be non-negative.")

    @property
    def components(self):
        return {
            "artifact_bytes": self.artifact_bytes,
            "staging_bytes": self.staging_bytes,
            "index_bytes": self.index_bytes,
            "backup_bytes": self.backup_bytes,
            "wal_bytes": self.wal_bytes,
            "margin_bytes": self.margin_bytes,
        }

    @property
    def required_bytes(self):
        return sum(self.components.values())


@dataclass(frozen=True)
class LoadResult:
    watershed_rows: int
    subcatchment_rows: int
    channel_rows: int
    capability_rows: int
    maximum_batch_rows: int


@dataclass(frozen=True)
class CleanupResult:
    status: str
    deleted_rows: int = 0
    error: str | None = None


STAGING_MODELS = (
    StagedRunCapability,
    StagedChannel,
    StagedSubcatchment,
    StagedWatershed,
)
ROW_SPECS = (
    (StagedWatershed, "watershed_rows"),
    (StagedSubcatchment, "subcatchment_rows"),
    (StagedChannel, "channel_rows"),
    (StagedRunCapability, "capability_rows"),
)


def available_bytes(path):
    return shutil.disk_usage(Path(path)).free


@transaction.atomic
def open_staging(
    attempt,
    *,
    budget,
    observed_available_bytes,
    retention_until=None,
):
    attempt = DataReleaseAttempt.objects.select_for_update().get(pk=attempt.pk)
    if attempt.status != DataReleaseAttempt.Status.STAGING:
        raise StagingError("Capacity preflight requires a staging attempt.")
    if not attempt.lease_active or attempt.lease_expired:
        raise StagingLeaseError("Capacity preflight requires a live lease.")
    retention_until = retention_until or timezone.now() + timedelta(hours=24)
    status = (
        DataReleaseStagingState.Status.LOADING
        if observed_available_bytes >= budget.required_bytes
        else DataReleaseStagingState.Status.SPACE_REJECTED
    )
    state = DataReleaseStagingState.objects.create(
        attempt=attempt,
        status=status,
        available_bytes=observed_available_bytes,
        retention_until=retention_until,
        **budget.components,
    )
    if status == DataReleaseStagingState.Status.SPACE_REJECTED:
        transition_attempt(
            attempt,
            DataReleaseAttempt.Status.FAILED,
            failure_phase="space-preflight",
            failure_summary=(
                f"required_bytes={budget.required_bytes} "
                f"available_bytes={observed_available_bytes}"
            ),
        )
    return state


def _next_batch(records, batch_size):
    return list(islice(records, batch_size))


@transaction.atomic
def heartbeat_staging(attempt_id, lease_owner, lease_extension):
    attempt = DataReleaseAttempt.objects.select_for_update().get(pk=attempt_id)
    now = timezone.now()
    if (
        not attempt.lease_active
        or attempt.lease_owner != lease_owner
        or attempt.lease_expires_at <= now
    ):
        raise StagingLeaseError("The staging lease is not live or owned.")
    attempt.lease_heartbeat_at = now
    attempt.lease_expires_at = now + lease_extension
    attempt.save(update_fields=("lease_heartbeat_at", "lease_expires_at"))


def _load_model_batches(
    *,
    model,
    counter_field,
    records,
    attempt,
    batch_size,
    lease_extension,
):
    iterator = iter(records)
    loaded = 0
    maximum_batch = 0
    while True:
        dictionaries = _next_batch(iterator, batch_size)
        if not dictionaries:
            break
        rows = []
        for values in dictionaries:
            row = model(attempt=attempt, **values)
            row.full_clean(validate_unique=False, validate_constraints=False)
            rows.append(row)
        heartbeat_staging(attempt.pk, attempt.lease_owner, lease_extension)
        with transaction.atomic():
            model.objects.bulk_create(rows, batch_size=batch_size)
            DataReleaseStagingState.objects.filter(attempt=attempt).update(
                **{counter_field: F(counter_field) + len(rows)}
            )
        loaded += len(rows)
        maximum_batch = max(maximum_batch, len(rows))
    return loaded, maximum_batch


def load_staging_model_rows(
    attempt,
    *,
    model,
    records,
    batch_size=1000,
    lease_extension=timedelta(minutes=30),
):
    if batch_size < 1:
        raise ValueError("Batch size must be positive.")
    row_spec = next(
        (spec for spec in ROW_SPECS if spec[0] is model),
        None,
    )
    if row_spec is None:
        raise ValueError("Unsupported staging model.")
    attempt = DataReleaseAttempt.objects.get(pk=attempt.pk)
    state = DataReleaseStagingState.objects.get(attempt=attempt)
    if state.status != DataReleaseStagingState.Status.LOADING:
        raise StagingError("Rows require a loading staging state.")
    if attempt.status != DataReleaseAttempt.Status.STAGING:
        raise StagingError("Rows require a staging attempt.")
    return _load_model_batches(
        model=model,
        counter_field=row_spec[1],
        records=records,
        attempt=attempt,
        batch_size=batch_size,
        lease_extension=lease_extension,
    )


@transaction.atomic
def mark_staging_ready(attempt):
    attempt = DataReleaseAttempt.objects.select_for_update().get(pk=attempt.pk)
    state = DataReleaseStagingState.objects.select_for_update().get(attempt=attempt)
    if attempt.status != DataReleaseAttempt.Status.STAGING:
        raise StagingError("READY requires a staging attempt.")
    if state.status != DataReleaseStagingState.Status.LOADING:
        raise StagingError("READY requires a loading staging state.")
    for model in STAGING_MODELS:
        model.objects.filter(attempt=attempt).update(
            validation_status=model.ValidationStatus.VALIDATED,
        )
    state.status = DataReleaseStagingState.Status.READY
    state.save(update_fields=("status", "updated_at"))
    return state


def load_staging_rows(
    attempt,
    *,
    watersheds=(),
    subcatchments=(),
    channels=(),
    capabilities=(),
    batch_size=1000,
    lease_extension=timedelta(minutes=30),
):
    totals = {}
    maximum_batch = 0
    record_sets = (watersheds, subcatchments, channels, capabilities)
    for (model, counter_field), records in zip(ROW_SPECS, record_sets, strict=True):
        loaded, observed_batch = load_staging_model_rows(
            attempt,
            model=model,
            records=records,
            batch_size=batch_size,
            lease_extension=lease_extension,
        )
        totals[counter_field] = loaded
        maximum_batch = max(maximum_batch, observed_batch)
    mark_staging_ready(attempt)
    return LoadResult(
        watershed_rows=totals["watershed_rows"],
        subcatchment_rows=totals["subcatchment_rows"],
        channel_rows=totals["channel_rows"],
        capability_rows=totals["capability_rows"],
        maximum_batch_rows=maximum_batch,
    )


def cleanup_staging(attempt, *, now=None, fault=None):
    now = now or timezone.now()
    state = DataReleaseStagingState.objects.get(attempt=attempt)
    if state.retention_until > now:
        if state.status != DataReleaseStagingState.Status.CLEANUP_PENDING:
            state.status = DataReleaseStagingState.Status.CLEANUP_PENDING
            state.last_cleanup_error = None
            state.save(update_fields=("status", "last_cleanup_error", "updated_at"))
        return CleanupResult(status="retained")

    state.status = DataReleaseStagingState.Status.CLEANUP_PENDING
    state.cleanup_attempts += 1
    state.last_cleanup_error = None
    state.save(
        update_fields=(
            "status",
            "cleanup_attempts",
            "last_cleanup_error",
            "updated_at",
        )
    )
    try:
        with transaction.atomic():
            if fault:
                fault()
            deleted_rows = 0
            for model in STAGING_MODELS:
                deleted, _ = model.objects.filter(attempt=attempt).delete()
                deleted_rows += deleted
    except Exception as exc:
        error = sanitize_failure_summary(str(exc) or type(exc).__name__)
        DataReleaseStagingState.objects.filter(attempt=attempt).update(
            last_cleanup_error=error,
        )
        return CleanupResult(status="pending", error=error)

    DataReleaseStagingState.objects.filter(attempt=attempt).update(
        status=DataReleaseStagingState.Status.CLEANED,
        watershed_rows=0,
        subcatchment_rows=0,
        channel_rows=0,
        capability_rows=0,
        last_cleanup_error=None,
    )
    return CleanupResult(status="cleaned", deleted_rows=deleted_rows)


def recover_expired_attempts(*, now=None):
    now = now or timezone.now()
    attempt_ids = list(
        DataReleaseAttempt.objects.filter(
            lease_active=True,
            lease_expires_at__lte=now,
            status__in=(
                DataReleaseAttempt.Status.PLANNING,
                DataReleaseAttempt.Status.STAGING,
                DataReleaseAttempt.Status.APPLYING,
            ),
        ).values_list("pk", flat=True)
    )
    results = []
    for attempt_id in attempt_ids:
        with transaction.atomic():
            attempt = DataReleaseAttempt.objects.select_for_update().get(pk=attempt_id)
            if not attempt.lease_active or attempt.lease_expires_at > now:
                continue
            prior_status = attempt.status
            transition_attempt(
                attempt,
                DataReleaseAttempt.Status.FAILED,
                failure_phase="lease-expired",
                failure_summary=f"expired attempt recovered from {prior_status}",
            )
        try:
            cleanup = cleanup_staging(attempt, now=now)
        except DataReleaseStagingState.DoesNotExist:
            cleanup = CleanupResult(status="no-staging")
        results.append((attempt_id, prior_status, cleanup.status))
    return results


def retry_pending_cleanup(*, now=None):
    now = now or timezone.now()
    attempt_ids = list(
        DataReleaseStagingState.objects.filter(
            status=DataReleaseStagingState.Status.CLEANUP_PENDING,
            retention_until__lte=now,
        ).values_list("attempt_id", flat=True)
    )
    return [
        cleanup_staging(
            DataReleaseAttempt.objects.get(pk=attempt_id),
            now=now,
        )
        for attempt_id in attempt_ids
    ]
