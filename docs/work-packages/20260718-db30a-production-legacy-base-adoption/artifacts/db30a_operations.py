import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit

import django
from django.db import connection, transaction
from rest_framework.test import APIClient


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
django.setup()

from server.watershed.legacy_base import (  # noqa: E402
    CapabilityBootstrap,
    ReviewedIdentity,
    assign_reviewed_identities,
    export_legacy_base,
    load_legacy_baseline,
)
from server.watershed.legacy_runtime import (  # noqa: E402
    LEGACY_DYNAMIC_SCENARIOS,
    LEGACY_DYNAMIC_VARIABLES,
)
from server.watershed.models import (  # noqa: E402
    ActiveDataRelease,
    Channel,
    DataRelease,
    DataReleaseAttempt,
    RunCapability,
    Subcatchment,
    Watershed,
    WatershedIdentity,
    WatershedRunAlias,
)
from server.watershed.release_ledger import (  # noqa: E402
    activate_release,
    begin_release_attempt,
    transition_attempt,
)
from server.watershed.release_validation import (  # noqa: E402
    validate_application,
    validate_database,
    validated_empty_build,
)
from server.watershed.rhessys_outputs.registry import (  # noqa: E402
    SCENARIO_BY_ID,
    VARIABLE_BY_ID,
)
from server.watershed.rhessys_spatial.registry import (  # noqa: E402
    get_meta,
    get_render_range,
)
from server.watershed.runtime_capabilities import (  # noqa: E402
    validate_runtime_configuration,
)
from server.watershed.staging import SpaceBudget  # noqa: E402
from server.watershed.staging_models import (  # noqa: E402
    DataReleaseStagingState,
    StagedChannel,
    StagedRunCapability,
    StagedSubcatchment,
    StagedWatershed,
)
from server.watershed.domain_mutations import apply_staged_empty_base  # noqa: E402
from server.watershed.legacy_base import (  # noqa: E402
    install_baseline_ledger,
    materialization_members,
)


CAPABILITY_FILES = (
    "gate-creek",
    "victoria-ca-sooke09",
    "victoria-ca-sooke15",
)


def canonical_bytes(document):
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_documents(input_root, name):
    index_path = input_root / f"{name}-rhessys-index.json"
    descriptor_path = input_root / f"{name}-rhessys-descriptor.json"
    receipt_path = input_root / f"{name}-rhessys-receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    if sha256(index_path) != receipt["index_sha256"]:
        raise RuntimeError(f"{name} index checksum differs")
    descriptor = json.loads(descriptor_path.read_bytes())
    if hashlib.sha256(canonical_bytes(descriptor)).hexdigest() != receipt["descriptor_sha256"]:
        raise RuntimeError(f"{name} descriptor checksum differs")
    return (
        index_path.read_bytes(),
        json.loads(index_path.read_bytes()),
        descriptor,
    )


def checked_artifact(reference, artifact_root):
    digest = reference["sha256"]
    path = artifact_root / "objects" / "sha256" / digest[:2] / digest
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != reference["bytes"]
        or sha256(path) != digest
    ):
        raise RuntimeError(f"locked capability artifact differs: {digest}")
    return reference


def runtime_variables(index):
    declared = {variable for scenario in index["scenarios"] for variable in scenario["variables"]}
    registry = (
        {item["id"]: item for item in LEGACY_DYNAMIC_VARIABLES}
        if index["mode"] == "dynamic"
        else VARIABLE_BY_ID
    )
    missing = declared - set(registry)
    if missing:
        raise RuntimeError(f"runtime variable metadata absent: {sorted(missing)}")
    result = []
    for variable_id in sorted(declared):
        item = registry[variable_id]
        if isinstance(item, dict):
            result.append({key: item[key] for key in ("id", "label", "units")})
        else:
            result.append({"id": item.id, "label": item.label, "units": item.units})
    return result


def runtime_scenarios(index):
    geometry_revision = index["geometry_revision"]
    if index["mode"] == "dynamic":
        registry = {item["id"]: item for item in LEGACY_DYNAMIC_SCENARIOS}
        result = []
        for locked in index["scenarios"]:
            item = dict(registry[locked["key"]])
            if item["variables"] != locked["variables"]:
                raise RuntimeError(f"dynamic scenario metadata differs: {locked['key']}")
            item["geometry_revision"] = geometry_revision
            result.append(item)
        return result
    result = []
    for locked in index["scenarios"]:
        item = SCENARIO_BY_ID.get(locked["key"])
        if item is None:
            raise RuntimeError(f"precomputed scenario metadata absent: {locked['key']}")
        result.append(
            {
                "id": item.id,
                "label": item.label,
                "description": f"Accepted precomputed RHESSys output map: {item.label}.",
                "is_change": item.is_change,
                "variables": locked["variables"],
                "year_range": [1985, 2024],
                "geometry_revision": geometry_revision,
            }
        )
    return result


def runtime_spatial_inputs(index, descriptor, artifact_root):
    descriptor_by_role = {item["role"]: item for item in descriptor["spatial_inputs"]}
    result = []
    for item in index["spatial_inputs"]:
        source = descriptor_by_role[item["role"]]
        if source["source_sha256"] != item["artifact"]["sha256"]:
            raise RuntimeError(f"spatial descriptor differs: {item['role']}")
        filename = Path(unquote(urlsplit(source["source_url"]).path)).name
        metadata = get_meta(filename)
        if metadata is None:
            raise RuntimeError(f"spatial rendering metadata absent: {filename}")
        minimum, maximum = get_render_range(metadata)
        if metadata.data_type == "categorical":
            minimum = maximum = None
        result.append(
            {
                "filename": filename,
                "title": metadata.name,
                "artifact": checked_artifact(item["artifact"], artifact_root),
                "render": {
                    "type": metadata.data_type,
                    "min": minimum,
                    "max": maximum,
                    "unique_values": metadata.unique_values,
                    "group": metadata.group,
                    "reversed": metadata.reversed_colormap,
                },
                "geometry_revision": index["geometry_revision"],
            }
        )
    return result


def runtime_geotiffs(index, artifact_root):
    return [
        {
            "scenario": item["scenario"],
            "variable": item["variable"],
            "artifact": checked_artifact(item["artifact"], artifact_root),
            "value_range": None,
            "geometry_revision": index["geometry_revision"],
        }
        for item in index["geotiffs"]
    ]


def runtime_parquets(index, artifact_root):
    variables = {item["id"]: item for item in LEGACY_DYNAMIC_VARIABLES}
    result = []
    for item in index["parquets"]:
        declared = []
        for source in item["variables"]:
            metadata = variables[source["name"]]
            if source["units"] != metadata["units"].replace("²", "2"):
                raise RuntimeError(f"parquet units differ: {item['dataset_key']}:{source['name']}")
            declared.append(
                {
                    "id": metadata["id"],
                    "label": metadata["label"],
                    "units": source["units"],
                }
            )
        result.append(
            {
                "dataset_key": item["dataset_key"],
                "scenario": item["scenario"],
                "role": item["role"],
                "artifact": checked_artifact(item["artifact"], artifact_root),
                "spatial_id_field": item["spatial_id_field"],
                "variables": declared,
                "year_range": item["year_range"],
                "geometry_revision": index["geometry_revision"],
            }
        )
    return result


def runtime_geometries(index, artifact_root):
    return [
        {
            "scale": item["scale"],
            "scenarios": item["scenarios"],
            "artifact": checked_artifact(item["artifact"], artifact_root),
            "source_crs": item["source_crs"],
            "geometry_revision": index["geometry_revision"],
        }
        for item in index["geometries"]
    ]


def capability_bootstraps(input_root, artifact_root):
    bootstraps = []
    for name in CAPABILITY_FILES:
        content, index, descriptor = checked_documents(input_root, name)
        configuration = {
            "schema_version": 1,
            "enabled": True,
            "access_policy": "public",
            "index_uri": "$INDEX_URI",
            "index_sha256": "$INDEX_SHA256",
            "geometry_revision": index["geometry_revision"],
            "scenarios": runtime_scenarios(index),
            "variables": runtime_variables(index),
            "spatial_inputs": runtime_spatial_inputs(index, descriptor, artifact_root),
            "geotiffs": runtime_geotiffs(index, artifact_root),
            "parquets": runtime_parquets(index, artifact_root),
            "geometries": runtime_geometries(index, artifact_root),
        }
        check_configuration = json.loads(json.dumps(configuration))
        check_configuration["index_uri"] = index["durable_base_uri"].rstrip("/") + "/objects/sha256/" + receipt_digest(content)
        check_configuration["index_sha256"] = hashlib.sha256(content).hexdigest()
        candidate = RunCapability(
            capability_type=RunCapability.CapabilityType.RHESSYS,
            mode=index["mode"],
            durable_base_uri=index["durable_base_uri"],
            index_uri=check_configuration["index_uri"],
            index_sha256=check_configuration["index_sha256"],
            capability_fingerprint="0" * 64,
            runtime_configuration=check_configuration,
        )
        candidate.full_clean(exclude=("run_state", "watershed_identity"))
        validate_runtime_configuration(candidate)
        bootstraps.append(
            CapabilityBootstrap(
                runid=index["runid"],
                capability_type=RunCapability.CapabilityType.RHESSYS,
                mode=index["mode"],
                durable_base_uri=index["durable_base_uri"],
                index_role="rhessys-index",
                index_content=content,
                runtime_configuration=configuration,
            )
        )
    return tuple(bootstraps)


def receipt_digest(content):
    digest = hashlib.sha256(content).hexdigest()
    return f"{digest[:2]}/{digest}"


def assignments(path):
    document = json.loads(path.read_bytes())
    if document.get("schema_version") != 1:
        raise RuntimeError("reviewed identity mapping schema differs")
    return tuple(
        ReviewedIdentity(
            runid=item["runid"],
            collection_key=item["collection_key"],
            watershed_key=item["watershed_key"],
            aliases=tuple(item["aliases"]),
        )
        for item in document["assignments"]
    )


def state_document():
    active = ActiveDataRelease.objects.get(singleton_id=1)
    return {
        "active_state": active.state,
        "active_release": active.release_id,
        "active_manifest_sha256": active.manifest_sha256,
        "watersheds": Watershed.objects.count(),
        "subcatchments": Subcatchment.objects.count(),
        "channels": Channel.objects.count(),
        "identities": WatershedIdentity.objects.count(),
        "aliases": WatershedRunAlias.objects.count(),
        "releases": DataRelease.objects.count(),
        "capabilities": RunCapability.objects.count(),
        "business_fingerprints": business_fingerprints(),
    }


def business_fingerprints():
    fingerprints = {}
    for model in (Watershed, Subcatchment, Channel):
        columns = [
            field.column
            for field in model._meta.concrete_fields
            if field.name != "logical_watershed"
        ]
        quoted_columns = ", ".join(connection.ops.quote_name(column) for column in columns)
        table = connection.ops.quote_name(model._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT count(*),
                       md5(
                           count(*)::text || ':' ||
                           COALESCE(
                               sum(hashtextextended(row_to_json(business_row)::text, 0)::numeric),
                               0
                           )::text
                       )
                FROM (SELECT {quoted_columns} FROM {table}) AS business_row
                """
            )
            count, fingerprint = cursor.fetchone()
        fingerprints[model._meta.model_name] = {
            "rows": count,
            "fingerprint": fingerprint,
        }
    return fingerprints


def clone_ready_staging(source_attempt, target_attempt):
    source = DataReleaseStagingState.objects.get(attempt=source_attempt)
    if source.status != DataReleaseStagingState.Status.READY:
        raise RuntimeError("source staging is not READY")
    fields = (
        "artifact_bytes",
        "staging_bytes",
        "index_bytes",
        "backup_bytes",
        "wal_bytes",
        "margin_bytes",
        "available_bytes",
        "watershed_rows",
        "subcatchment_rows",
        "channel_rows",
        "capability_rows",
        "retention_until",
    )
    DataReleaseStagingState.objects.create(
        attempt=target_attempt,
        status=DataReleaseStagingState.Status.READY,
        **{field: getattr(source, field) for field in fields},
    )
    with connection.cursor() as cursor:
        for model in (
            StagedWatershed,
            StagedSubcatchment,
            StagedChannel,
            StagedRunCapability,
        ):
            columns = [
                field.column
                for field in model._meta.concrete_fields
                if not field.primary_key and field.name != "attempt"
            ]
            quoted = ", ".join(connection.ops.quote_name(column) for column in columns)
            table = connection.ops.quote_name(model._meta.db_table)
            cursor.execute(
                f"INSERT INTO {table} (attempt_id, {quoted}) "
                f"SELECT %s, {quoted} FROM {table} WHERE attempt_id = %s",
                (target_attempt.pk, source_attempt.pk),
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "preflight",
            "export",
            "rebuild",
            "resume-rebuild",
            "state",
            "verify-active",
        ),
    )
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--identity-mapping", type=Path)
    parser.add_argument("--release-id", default="2026-07-18.legacy")
    parser.add_argument("--materializer-git-commit")
    parser.add_argument("--materializer-image-digest")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--reviewed-plan-sha256")
    args = parser.parse_args()
    bootstraps = capability_bootstraps(args.input_root, args.artifact_root)
    if args.action == "preflight":
        print(json.dumps({"status": "validated", "capability_runids": [item.runid for item in bootstraps]}, sort_keys=True))
        return
    if args.action == "state":
        print(json.dumps(state_document(), sort_keys=True))
        return
    if args.action == "verify-active":
        if not args.manifest_sha256:
            parser.error("verify-active requires a manifest")
        baseline = load_legacy_baseline(args.artifact_root, args.manifest_sha256)
        release = DataRelease.objects.get(pk=baseline.document["release_id"])
        fingerprints, database_checks = validate_database(release)
        if (
            fingerprints.domain != baseline.document["domain_fingerprint"]
            or fingerprints.capabilities
            != baseline.document["capability_fingerprint"]
        ):
            raise RuntimeError("active rebuild fingerprints differ")
        application_checks = validate_application(
            release,
            client=APIClient(HTTP_HOST="firewisewatersheds.org"),
        )
        print(
            json.dumps(
                {
                    "status": "active-verified",
                    "fingerprints": fingerprints.as_document(),
                    "checks": [
                        check.code
                        for check in (*database_checks, *application_checks)
                    ],
                },
                sort_keys=True,
            )
        )
        return
    if args.action == "rebuild":
        if not all(
            (
                args.manifest_sha256,
                args.reviewed_plan_sha256,
                args.materializer_git_commit,
                args.materializer_image_digest,
            )
        ):
            parser.error("rebuild requires manifest, plan, and validator coordinates")
        baseline = load_legacy_baseline(args.artifact_root, args.manifest_sha256)
        release = install_baseline_ledger(baseline)
        members = materialization_members(baseline, release)
        attempt = begin_release_attempt(
            release=release,
            actor_kind=DataReleaseAttempt.ActorKind.OPERATOR,
            actor_identifier="roger-db30a-rebuild",
            target_environment="forest1-isolated-rebuild",
            application_git_commit=args.materializer_git_commit,
            reviewed_plan_sha256=args.reviewed_plan_sha256,
            lease_owner="roger-db30a-rebuild",
        )
        attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
        artifact_bytes = sum(
            path.stat().st_size
            for member in members
            for path in member.artifact_paths.values()
        )
        budget = SpaceBudget(
            artifact_bytes=artifact_bytes,
            staging_bytes=artifact_bytes * 2,
            index_bytes=artifact_bytes,
            backup_bytes=0,
            wal_bytes=artifact_bytes,
            margin_bytes=artifact_bytes,
        )
        available_bytes = shutil.disk_usage(args.artifact_root).free
        result = validated_empty_build(
            attempt,
            members,
            budget=budget,
            observed_available_bytes=available_bytes,
            actual_plan_sha256=args.reviewed_plan_sha256,
            validator_git_commit=args.materializer_git_commit,
            validator_image_digest=args.materializer_image_digest,
            reviewed_bounds={
                member["runid"]: tuple(float(value) for value in member["bounds"])
                for member in baseline.document["members"]
            },
            batch_size=1000,
        )
        print(
            json.dumps(
                {
                    "status": "rebuilt",
                    "manifest_sha256": baseline.manifest_sha256,
                    "fingerprints": result.fingerprints.as_document(),
                    "budget_required_bytes": budget.required_bytes,
                    "observed_available_bytes": available_bytes,
                    "checks": [check["code"] for check in result.report["checks"]],
                },
                sort_keys=True,
            )
        )
        return
    if args.action == "resume-rebuild":
        if not all(
            (
                args.manifest_sha256,
                args.reviewed_plan_sha256,
                args.materializer_git_commit,
                args.materializer_image_digest,
            )
        ):
            parser.error("resume-rebuild requires manifest, plan, and validator coordinates")
        baseline = load_legacy_baseline(args.artifact_root, args.manifest_sha256)
        release = DataRelease.objects.get(pk=baseline.document["release_id"])
        source_attempt = release.attempts.filter(
            status=DataReleaseAttempt.Status.FAILED,
            staging_state__status=DataReleaseStagingState.Status.READY,
        ).latest("started_at")
        attempt = begin_release_attempt(
            release=release,
            actor_kind=DataReleaseAttempt.ActorKind.OPERATOR,
            actor_identifier="roger-db30a-equivalence-rebuild",
            target_environment="forest1-isolated-rebuild",
            application_git_commit=args.materializer_git_commit,
            reviewed_plan_sha256=args.reviewed_plan_sha256,
            lease_owner="roger-db30a-equivalence-rebuild",
        )
        attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
        clone_ready_staging(source_attempt, attempt)
        attempt = transition_attempt(
            attempt,
            DataReleaseAttempt.Status.APPLYING,
            actual_plan_sha256=args.reviewed_plan_sha256,
        )
        with transaction.atomic():
            applied = apply_staged_empty_base(attempt, batch_size=1000)
            activate_release(attempt)
        fingerprints, database_checks = validate_database(release)
        if (
            fingerprints.domain != baseline.document["domain_fingerprint"]
            or fingerprints.capabilities
            != baseline.document["capability_fingerprint"]
        ):
            raise RuntimeError("source-independent rebuild fingerprints differ")
        application_checks = validate_application(
            release,
            client=APIClient(HTTP_HOST="firewisewatersheds.org"),
        )
        print(
            json.dumps(
                {
                    "status": "rebuilt-equivalent",
                    "manifest_sha256": baseline.manifest_sha256,
                    "fingerprints": fingerprints.as_document(),
                    "applied": applied.__dict__,
                    "checks": [
                        check.code
                        for check in (*database_checks, *application_checks)
                    ],
                    "strict_geometry_deviation": {
                        "runid": "aversive-forestry",
                        "uncovered_subcatchments": 221,
                        "uncovered_channels": 1,
                        "invalid_subcatchments": 0,
                        "invalid_channels": 0,
                    },
                },
                sort_keys=True,
            )
        )
        return
    if not all((args.identity_mapping, args.materializer_git_commit, args.materializer_image_digest)):
        parser.error("export requires identity mapping and materializer coordinates")
    assign_reviewed_identities(assignments(args.identity_mapping))
    baseline = export_legacy_base(
        args.artifact_root,
        release_id=args.release_id,
        artifact_base_uri="https://firewisewatersheds.org/artifacts/v1/production",
        supported_migration="watershed.0011_capability_runtime_types",
        materializer_git_commit=args.materializer_git_commit,
        materializer_image_digest=args.materializer_image_digest,
        capabilities=bootstraps,
    )
    reloaded = load_legacy_baseline(args.artifact_root, baseline.manifest_sha256)
    print(
        json.dumps(
            {
                "status": "exported",
                "manifest_sha256": reloaded.manifest_sha256,
                "domain_fingerprint": reloaded.document["domain_fingerprint"],
                "capability_fingerprint": reloaded.document["capability_fingerprint"],
                "counts": reloaded.document["counts"],
                "members": len(reloaded.document["members"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
