import re
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from server.watershed.models import (
    ActiveDataRelease,
    DataRelease,
    DataReleaseAttempt,
    DataRunState,
)


class ReleaseLedgerError(RuntimeError):
    pass


class LeaseConflictError(ReleaseLedgerError):
    pass


class InvalidTransitionError(ReleaseLedgerError):
    pass


class ActivationError(ReleaseLedgerError):
    pass


SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key)\s*[:=]\s*"
    r"(?:\"[^\"]*\"|'[^']*'|\S+)"
)
URI_USERINFO = re.compile(r"(https?://)[^/@\s]+@", re.IGNORECASE)
CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]+")
FORBIDDEN_CONFIGURATION_KEYS = {
    "password",
    "passwd",
    "token",
    "secret",
    "secret_ref",
    "api_key",
    "apikey",
    "credential",
    "credentials",
}


def sanitize_failure_summary(summary):
    sanitized = URI_USERINFO.sub(r"\1[REDACTED]@", str(summary))
    sanitized = SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        sanitized,
    )
    sanitized = CONTROL_CHARACTERS.sub(" ", sanitized)
    return " ".join(sanitized.split())[:512]


def validate_public_configuration(value, path="runtime_configuration"):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_CONFIGURATION_KEYS:
                raise ValidationError(f"Secret-bearing configuration key: {path}.{key}")
            validate_public_configuration(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_public_configuration(child, f"{path}[{index}]")


@transaction.atomic
def begin_release_attempt(
    *,
    release,
    actor_kind,
    actor_identifier,
    target_environment,
    application_git_commit,
    reviewed_plan_sha256,
    lease_owner,
    lease_duration=timedelta(minutes=30),
):
    active = ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    existing = (
        DataReleaseAttempt.objects.select_for_update()
        .filter(lease_active=True)
        .first()
    )
    if existing:
        qualifier = "expired; recovery required" if existing.lease_expired else "active"
        raise LeaseConflictError(f"A release lease is already {qualifier}.")
    if lease_duration <= timedelta(0):
        raise ValidationError("Lease duration must be positive.")
    now = timezone.now()
    return DataReleaseAttempt.objects.create(
        release=release,
        previous_active_release=active.release,
        actor_kind=actor_kind,
        actor_identifier=actor_identifier,
        target_environment=target_environment,
        application_git_commit=application_git_commit,
        reviewed_plan_sha256=reviewed_plan_sha256,
        lease_owner=lease_owner,
        lease_heartbeat_at=now,
        lease_expires_at=now + lease_duration,
    )


ALLOWED_ATTEMPT_TRANSITIONS = {
    DataReleaseAttempt.Status.PLANNING: {
        DataReleaseAttempt.Status.STAGING,
        DataReleaseAttempt.Status.FAILED,
    },
    DataReleaseAttempt.Status.STAGING: {
        DataReleaseAttempt.Status.APPLYING,
        DataReleaseAttempt.Status.FAILED,
    },
    DataReleaseAttempt.Status.APPLYING: {
        DataReleaseAttempt.Status.SUCCEEDED,
        DataReleaseAttempt.Status.FAILED,
    },
    DataReleaseAttempt.Status.SUCCEEDED: {DataReleaseAttempt.Status.ROLLED_BACK},
    DataReleaseAttempt.Status.FAILED: {DataReleaseAttempt.Status.ROLLED_BACK},
    DataReleaseAttempt.Status.ROLLED_BACK: set(),
}


@transaction.atomic
def transition_attempt(
    attempt,
    target_status,
    *,
    actual_plan_sha256=None,
    failure_phase=None,
    failure_summary=None,
):
    attempt = DataReleaseAttempt.objects.select_for_update().get(pk=attempt.pk)
    if target_status not in ALLOWED_ATTEMPT_TRANSITIONS[attempt.status]:
        raise InvalidTransitionError(
            f"Attempt cannot transition from {attempt.status} to {target_status}."
        )
    now = timezone.now()
    if target_status == DataReleaseAttempt.Status.STAGING:
        attempt.validated_at = now
    elif target_status == DataReleaseAttempt.Status.APPLYING:
        if not actual_plan_sha256:
            raise ValidationError("Applying requires the actual plan SHA-256.")
        attempt.actual_plan_sha256 = actual_plan_sha256
        attempt.applied_at = now
    elif target_status == DataReleaseAttempt.Status.FAILED:
        if not failure_phase or not failure_summary:
            raise ValidationError("Failure phase and summary are required.")
        attempt.failure_phase = failure_phase
        attempt.failure_summary = sanitize_failure_summary(failure_summary)
        attempt.completed_at = now
        attempt.lease_active = False
    elif target_status in (
        DataReleaseAttempt.Status.SUCCEEDED,
        DataReleaseAttempt.Status.ROLLED_BACK,
    ):
        attempt.completed_at = now
        attempt.lease_active = False
    attempt.status = target_status
    attempt.save()
    return attempt


def _validate_release_contents(release):
    run_states = DataRunState.objects.filter(release=release).select_related(
        "collection",
        "watershed_identity",
    )
    totals = run_states.aggregate(
        watersheds=Sum("actual_watersheds"),
        subcatchments=Sum("actual_subcatchments"),
        channels=Sum("actual_channels"),
    )
    expected = {
        "watersheds": release.actual_watersheds,
        "subcatchments": release.actual_subcatchments,
        "channels": release.actual_channels,
    }
    actual = {key: value or 0 for key, value in totals.items()}
    if actual != expected:
        raise ActivationError("Release run-state counts do not match the ledger.")
    if run_states.exclude(
        validation_status=DataRunState.ValidationStatus.VALIDATED
    ).exists():
        raise ActivationError("Every release run state must be validated.")
    for run_state in run_states:
        if run_state.collection_id != run_state.watershed_identity.collection_id:
            raise ActivationError("Run collection does not match watershed identity.")
        capabilities = list(run_state.capabilities.all())
        if run_state.capability_fingerprint is None and capabilities:
            raise ActivationError("Unexpected capability rows exist for a run.")
        if run_state.capability_fingerprint is not None:
            if len(capabilities) != 1:
                raise ActivationError("A declared capability requires exactly one row.")
            capability = capabilities[0]
            if (
                capability.watershed_identity_id != run_state.watershed_identity_id
                or capability.capability_fingerprint
                != run_state.capability_fingerprint
            ):
                raise ActivationError("Capability identity or fingerprint mismatch.")


@transaction.atomic
def activate_release(attempt):
    active = ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    attempt = DataReleaseAttempt.objects.select_for_update().get(pk=attempt.pk)
    release = DataRelease.objects.select_for_update().get(pk=attempt.release_id)
    if attempt.status != DataReleaseAttempt.Status.APPLYING:
        raise ActivationError("Only an applying attempt may activate a release.")
    if attempt.actual_plan_sha256 != attempt.reviewed_plan_sha256:
        raise ActivationError("Actual and reviewed deployment plans differ.")
    if active.release_id != attempt.previous_active_release_id:
        raise ActivationError("The active base release changed after review.")
    if release.status not in (
        DataRelease.Status.VALIDATED,
        DataRelease.Status.SUPERSEDED,
    ):
        raise ActivationError("Target release is not activatable.")
    _validate_release_contents(release)

    now = timezone.now()
    if active.release:
        previous = active.release
        previous.status = DataRelease.Status.SUPERSEDED
        previous._allow_lifecycle_change = True
        previous.save(update_fields=("status",))
    release.status = DataRelease.Status.ACTIVE
    release._allow_lifecycle_change = True
    if release.first_activated_at is None:
        release.first_activated_at = now
        release.save(update_fields=("status", "first_activated_at"))
    else:
        release.save(update_fields=("status",))
    active.state = ActiveDataRelease.State.ACTIVE
    active.release = release
    active.manifest_sha256 = release.manifest_sha256
    active.data_contract = release.data_contract
    active.activated_at = now
    active._allow_activation_change = True
    active.save()
    attempt.status = DataReleaseAttempt.Status.SUCCEEDED
    attempt.completed_at = now
    attempt.lease_active = False
    attempt.save()
    return active
