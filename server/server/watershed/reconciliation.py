from dataclasses import dataclass

from django.db import transaction

from server.watershed.models import ActiveDataRelease, DataRelease
from server.watershed.release_validation import compute_serving_fingerprints


class ReconciliationVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ActiveReleaseVerification:
    release_id: str
    manifest_sha256: str
    domain_fingerprint: str
    watershed_rows: int
    subcatchment_rows: int
    channel_rows: int
    capability_rows: int


@transaction.atomic
def verify_active_release_noop(release):
    active = ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    release = DataRelease.objects.get(pk=release.pk)
    if not (
        active.state == ActiveDataRelease.State.ACTIVE
        and active.release_id == release.release_id
        and active.manifest_sha256 == release.manifest_sha256
        and release.status == DataRelease.Status.ACTIVE
    ):
        raise ReconciliationVerificationError(
            "Requested no-op release is not the exact active release."
        )
    observed = compute_serving_fingerprints(release)
    expected_capabilities = release.run_states.filter(
        capability_fingerprint__isnull=False
    ).count()
    if not (
        observed.domain == release.domain_fingerprint
        and observed.watershed_rows == release.actual_watersheds
        and observed.subcatchment_rows == release.actual_subcatchments
        and observed.channel_rows == release.actual_channels
        and observed.capability_rows == expected_capabilities
    ):
        raise ReconciliationVerificationError(
            "Requested no-op serving state differs from the active ledger."
        )
    return ActiveReleaseVerification(
        release_id=release.release_id,
        manifest_sha256=release.manifest_sha256,
        domain_fingerprint=observed.domain,
        watershed_rows=observed.watershed_rows,
        subcatchment_rows=observed.subcatchment_rows,
        channel_rows=observed.channel_rows,
        capability_rows=observed.capability_rows,
    )
