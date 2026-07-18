from dataclasses import dataclass

from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader

from server.watershed.domain_mutations import (
    EmptyBaseMutationError,
    _assert_exact_staging,
)
from server.watershed.fingerprint_contract import canonical_sha256
from server.watershed.materializer import CORE_ARTIFACT_MEDIA_TYPES
from server.watershed.models import (
    ActiveDataRelease,
    DataRelease,
    DataReleaseAttempt,
    DataRunState,
    RunCapability,
)
from server.watershed.runtime_capabilities import (
    RuntimeCapabilityError,
    validate_runtime_configuration,
)
from server.watershed.staging_models import DataReleaseStagingState, StagedRunCapability


class DeploymentCompatibilityError(RuntimeError):
    pass


MINIMUM_APPLICATION_MIGRATION = (
    "watershed",
    "0011_capability_runtime_types",
)
SUPPORTED_CONTRACTS = (1, 1, 1, 1, 1)


@dataclass(frozen=True)
class ApplicationCompatibility:
    active_state: str
    active_release_id: str | None
    migration: str


@dataclass(frozen=True)
class ReleaseCompatibility:
    release_id: str
    active_base: str
    migration: str
    artifact_rows: int
    capability_rows: int
    plan_sha256: str


def _require(condition, message):
    if not condition:
        raise DeploymentCompatibilityError(message)


def _migration_state():
    loader = MigrationLoader(connection)
    leaves = loader.graph.leaf_nodes("watershed")
    _require(len(leaves) == 1, "Watershed migration leaf is ambiguous.")
    leaf = leaves[0]
    _require(leaf in loader.applied_migrations, "Current watershed migration is not applied.")
    executor = MigrationExecutor(connection)
    _require(
        not executor.migration_plan(executor.loader.graph.leaf_nodes()),
        "Database has pending migrations.",
    )
    return loader, leaf


def _migration_name(node):
    return f"{node[0]}.{node[1]}"


def _assert_application_release(release, loader, current_leaf):
    coordinates = (
        release.schema_version,
        release.data_contract,
        release.identity_contract,
        release.artifact_contract,
        release.fingerprint_version,
    )
    _require(coordinates == SUPPORTED_CONTRACTS, "Active release contracts are unsupported.")
    release_node = tuple(release.supported_migration.split(".", 1))
    _require(
        release_node in loader.graph.nodes,
        "Active release migration is unknown to application code.",
    )
    ancestors = loader.graph.forwards_plan(current_leaf)
    minimum_ancestors = loader.graph.forwards_plan(release_node)
    _require(
        release_node in ancestors
        and MINIMUM_APPLICATION_MIGRATION in minimum_ancestors,
        "Active release migration is outside the application compatibility range.",
    )


def verify_application_compatibility():
    loader, current_leaf = _migration_state()
    active = ActiveDataRelease.objects.select_related("release").get(singleton_id=1)
    if active.state == ActiveDataRelease.State.EMPTY:
        _require(
            active.release_id is None and active.manifest_sha256 is None,
            "EMPTY active-release state is incoherent.",
        )
    else:
        _require(
            active.release_id is not None
            and active.release.status == DataRelease.Status.ACTIVE
            and active.manifest_sha256 == active.release.manifest_sha256
            and active.data_contract == active.release.data_contract,
            "Active release pointer differs from its ledger.",
        )
        _assert_application_release(active.release, loader, current_leaf)
    return ApplicationCompatibility(
        active_state=active.state,
        active_release_id=active.release_id,
        migration=_migration_name(current_leaf),
    )


def _assert_plan_coordinates(release, plan, image_digest, git_commit):
    _require(plan.get("schema_version") == 1, "Deployment plan schema is unsupported.")
    _require(
        plan.get("data_contract") == release.data_contract
        and plan.get("identity_contract") == release.identity_contract
        and plan.get("fingerprint_version") == release.fingerprint_version,
        "Deployment plan contract coordinates differ from the target release.",
    )
    _require(
        plan.get("supported_migration") == release.supported_migration,
        "Deployment plan migration differs from the target release.",
    )
    _require(
        plan.get("materializer")
        == {"image_digest": image_digest, "git_commit": git_commit},
        "Deployment plan materializer coordinates differ from the running tool.",
    )
    _require(
        release.materializer_image_digest == image_digest
        and release.materializer_git_commit == git_commit,
        "Target release materializer coordinates differ from the running tool.",
    )
    target = plan.get("target")
    _require(
        isinstance(target, dict)
        and target.get("kind") == "RELEASE"
        and target.get("release_id") == release.release_id
        and target.get("manifest_sha256") == release.manifest_sha256
        and target.get("release_fingerprint") == release.release_fingerprint
        and target.get("domain_fingerprint") == release.domain_fingerprint,
        "Deployment plan target differs from the target release.",
    )


def _assert_active_base(active, attempt, plan, expected_base_manifest):
    base = plan.get("base")
    if active.state == ActiveDataRelease.State.EMPTY:
        _require(expected_base_manifest == "EMPTY", "Expected base does not name EMPTY.")
        _require(base == {"kind": "EMPTY"}, "Deployment plan base does not name EMPTY.")
        _require(
            attempt.previous_active_release_id is None,
            "Attempt unexpectedly names a populated predecessor.",
        )
        return "EMPTY"
    _require(
        expected_base_manifest == active.manifest_sha256,
        "Expected base manifest is stale.",
    )
    _require(
        attempt.previous_active_release_id == active.release_id,
        "Attempt predecessor differs from the active release.",
    )
    _require(
        isinstance(base, dict)
        and base.get("kind") == "RELEASE"
        and base.get("release_id") == active.release_id
        and base.get("manifest_sha256") == active.manifest_sha256
        and base.get("release_fingerprint") == active.release.release_fingerprint
        and base.get("domain_fingerprint") == active.release.domain_fingerprint,
        "Deployment plan base differs from the active release.",
    )
    return active.release_id


def _assert_artifacts(release):
    required = set(CORE_ARTIFACT_MEDIA_TYPES)
    total = 0
    for run_state in release.run_states.prefetch_related("artifacts").iterator(
        chunk_size=1000
    ):
        artifacts = {artifact.role: artifact for artifact in run_state.artifacts.all()}
        _require(
            set(artifacts) == required,
            "Target run artifact roles are incomplete or unexpected.",
        )
        _require(
            all(
                artifacts[role].media_type == CORE_ARTIFACT_MEDIA_TYPES[role]
                for role in required
            ),
            "Target run artifact media type differs from the materializer contract.",
        )
        total += len(artifacts)
    return total


def _assert_capabilities(attempt):
    rows = StagedRunCapability.objects.filter(attempt=attempt).select_related(
        "run_state",
        "watershed_identity",
    )
    count = 0
    for staged in rows.iterator(chunk_size=1000):
        capability = RunCapability(
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
        validate_runtime_configuration(capability)
        count += 1
    return count


@transaction.atomic
def verify_release_compatibility(
    release,
    attempt,
    plan,
    *,
    expected_base_manifest,
    materializer_image_digest,
    materializer_git_commit,
    application_git_commit,
):
    application = verify_application_compatibility()
    release = DataRelease.objects.get(pk=release.pk)
    attempt = DataReleaseAttempt.objects.select_for_update().get(pk=attempt.pk)
    active = ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    _require(attempt.release_id == release.release_id, "Attempt target differs from release.")
    _require(attempt.lease_active and not attempt.lease_expired, "Attempt lease is absent or expired.")
    _require(
        attempt.status in (DataReleaseAttempt.Status.STAGING, DataReleaseAttempt.Status.APPLYING),
        "Compatibility requires a staged or applying attempt.",
    )
    _require(
        attempt.application_git_commit == application_git_commit,
        "Attempt application Git commit differs from the deployed application.",
    )
    _require(
        (release.schema_version, release.data_contract, release.identity_contract,
         release.artifact_contract, release.fingerprint_version) == SUPPORTED_CONTRACTS,
        "Target release contracts are unsupported.",
    )
    _require(
        release.supported_migration == application.migration,
        "Target release migration differs from the applied schema.",
    )
    _require(
        not release.run_states.exclude(
            validation_status=DataRunState.ValidationStatus.VALIDATED
        ).exists(),
        "Target release contains an unvalidated run state.",
    )
    _assert_plan_coordinates(
        release,
        plan,
        materializer_image_digest,
        materializer_git_commit,
    )
    plan_sha256 = canonical_sha256(plan)
    _require(
        attempt.reviewed_plan_sha256 == plan_sha256
        and attempt.actual_plan_sha256 in (None, plan_sha256),
        "Attempt plan digest differs from the reviewed plan.",
    )
    active_base = _assert_active_base(active, attempt, plan, expected_base_manifest)
    state = DataReleaseStagingState.objects.select_for_update().get(attempt=attempt)
    _require(
        state.status == DataReleaseStagingState.Status.READY,
        "Compatibility requires READY staging.",
    )
    try:
        _assert_exact_staging(attempt, state)
    except EmptyBaseMutationError as error:
        raise DeploymentCompatibilityError(str(error)) from error
    artifact_rows = _assert_artifacts(release)
    try:
        capability_rows = _assert_capabilities(attempt)
    except RuntimeCapabilityError as error:
        raise DeploymentCompatibilityError(str(error)) from error
    return ReleaseCompatibility(
        release_id=release.release_id,
        active_base=active_base,
        migration=application.migration,
        artifact_rows=artifact_rows,
        capability_rows=capability_rows,
        plan_sha256=plan_sha256,
    )
