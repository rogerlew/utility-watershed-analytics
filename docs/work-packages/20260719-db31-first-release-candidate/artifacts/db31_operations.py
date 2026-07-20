#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile


PUBLIC_BASE_URI = "https://firewisewatersheds.org/artifacts/v1/production"
CORE_ROLES = (
    "metadata",
    "boundary",
    "subcatchments",
    "channels",
    "hillslopes",
    "soils",
    "landuse",
)
BATCH_SIZE = 5000


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(content):
    return hashlib.sha256(content).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(document):
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def semantic_value(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: semantic_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [semantic_value(child) for child in value]
    return value


def load_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def write_new(path, content):
    path = Path(path)
    require(not path.exists() and not path.is_symlink(), f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def publish_content(root, content, media_type="application/json"):
    root = Path(root)
    require(not root.is_symlink(), "artifact root may not be a symlink")
    digest = sha256_bytes(content)
    destination = root / "objects" / "sha256" / digest[:2] / digest
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destination.parent, 0o700)
    if destination.exists():
        require(
            destination.is_file()
            and not destination.is_symlink()
            and destination.stat().st_size == len(content)
            and sha256_file(destination) == digest,
            f"content-addressed object conflicts: {digest}",
        )
        return artifact_reference(digest, len(content), media_type)
    with NamedTemporaryFile(
        dir=destination.parent,
        prefix=".db31-partial-",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.chmod(temporary, 0o600)
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return artifact_reference(digest, len(content), media_type)


def artifact_reference(digest, byte_size, media_type):
    return {
        "uri": f"{PUBLIC_BASE_URI}/objects/sha256/{digest[:2]}/{digest}",
        "sha256": digest,
        "bytes": byte_size,
        "media_type": media_type,
        "verified": True,
    }


def checked_reference(reference, artifact_root):
    required = {"uri", "sha256", "bytes", "media_type", "verified"}
    require(required <= set(reference), "artifact reference is incomplete")
    digest = reference["sha256"]
    require(
        reference["verified"] is True
        and reference["uri"]
        == f"{PUBLIC_BASE_URI}/objects/sha256/{digest[:2]}/{digest}",
        f"artifact reference coordinate differs: {digest}",
    )
    path = Path(artifact_root) / "objects" / "sha256" / digest[:2] / digest
    require(
        path.is_file()
        and not path.is_symlink()
        and path.stat().st_size == reference["bytes"]
        and sha256_file(path) == digest,
        f"artifact bytes differ: {digest}",
    )
    return path


def artifact_references(document):
    references = []

    def visit(value):
        if isinstance(value, dict):
            if {"uri", "sha256", "bytes", "media_type", "verified"} <= set(value):
                references.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)
    return references


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    require(specification is not None and specification.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def validation_modules(repository_root):
    scripts = Path(repository_root) / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import release_fingerprints
    import validate_release_schemas

    return release_fingerprints, validate_release_schemas


def validate_document(schema_module, schema_name, document):
    validator = schema_module.build_validators()[schema_name]
    errors = list(validator.iter_errors(document))
    require(
        not errors,
        f"{schema_name} validation failed: {errors[0].message if errors else ''}",
    )
    schema_module.validate_semantics(schema_name, document)


def canonicalize_parquet(reference, artifact_root):
    import pyarrow.compute as compute
    import pyarrow.parquet as parquet

    source = checked_reference(reference, artifact_root)
    table = parquet.read_table(source)
    topaz_candidates = (
        "TopazID",
        "topaz_id",
        "topazid",
        "TOPAZID",
        "Topaz_ID",
        "topaz_ID",
    )
    topaz_field = next(
        (name for name in topaz_candidates if name in table.schema.names),
        None,
    )
    require(topaz_field is not None, "Parquet artifact lacks a Topaz join field")
    topaz_values = table[topaz_field].to_pylist()
    require(
        all(value is not None for value in topaz_values),
        "Parquet Topaz identities contain nulls",
    )
    integer_values = [int(value) for value in topaz_values]
    require(
        len(integer_values) == len(set(integer_values)),
        "Parquet Topaz identities are duplicated",
    )
    if integer_values == sorted(integer_values):
        return reference, False

    order = compute.sort_indices(table, sort_keys=[(topaz_field, "ascending")])
    canonical = table.take(order)
    with NamedTemporaryFile(prefix="db31-parquet-", suffix=".parquet") as stream:
        parquet.write_table(canonical, stream.name)
        content = Path(stream.name).read_bytes()
    canonical_reference = publish_content(
        artifact_root,
        content,
        "application/vnd.apache.parquet",
    )
    canonical_path = checked_reference(canonical_reference, artifact_root)
    canonical_values = parquet.read_table(
        canonical_path,
        columns=[topaz_field],
    )[topaz_field].to_pylist()
    require(
        [int(value) for value in canonical_values] == sorted(integer_values),
        "canonical Parquet Topaz order differs",
    )
    return canonical_reference, True


def canonicalize_boundary(member, artifact_root, reviewed):
    from django.contrib.gis.geos import (
        GEOSGeometry,
        GeometryCollection,
        MultiPolygon,
        Polygon,
    )

    reference = member["artifacts"]["boundary"]
    source = checked_reference(reference, artifact_root)
    document = load_json(source)
    require(
        document.get("type") == "FeatureCollection"
        and len(document.get("features", [])) == 1,
        f"{member['watershed_key']} boundary structure differs",
    )
    source_geometry = GEOSGeometry(
        json.dumps(document["features"][0]["geometry"])
    )
    children = []
    subcatchment_area = 0.0
    for role in ("subcatchments", "channels"):
        child_document = load_json(
            checked_reference(member["artifacts"][role], artifact_root)
        )
        require(
            child_document.get("type") == "FeatureCollection"
            and child_document.get("features"),
            f"{member['watershed_key']} {role} structure differs",
        )
        for feature in child_document["features"]:
            child = GEOSGeometry(json.dumps(feature["geometry"]))
            children.append(child)
            if role == "subcatchments":
                subcatchment_area += child.area
    distance = reviewed["canonicalization"]["boundary_hull_buffer_degrees"]
    geometry = GeometryCollection(*children).convex_hull.buffer(distance)
    if isinstance(geometry, Polygon):
        geometry = MultiPolygon(geometry)
    require(
        isinstance(geometry, MultiPolygon)
        and not geometry.empty
        and geometry.valid,
        f"{member['watershed_key']} canonical boundary is invalid",
    )
    require(
        all(geometry.covers(child) for child in children),
        f"{member['watershed_key']} canonical boundary does not cover its children",
    )
    area_ratio = subcatchment_area / geometry.area
    require(
        0.01 <= area_ratio <= 2.0,
        f"{member['watershed_key']} canonical boundary area ratio differs",
    )
    document["features"][0]["geometry"] = json.loads(geometry.geojson)
    content = canonical_json_bytes(document)
    canonical_reference = publish_content(
        artifact_root,
        content,
        "application/geo+json",
    )
    checked_reference(canonical_reference, artifact_root)
    member["expected"]["bounds"] = list(geometry.extent)
    return canonical_reference, {
        "watershed_key": member["watershed_key"],
        "role": "boundary",
        "operation": "child-convex-hull-buffer",
        "buffer_degrees": distance,
        "source_bounds": list(source_geometry.extent),
        "canonical_bounds": list(geometry.extent),
        "subcatchment_area_ratio": area_ratio,
        "source_sha256": reference["sha256"],
        "canonical_sha256": canonical_reference["sha256"],
    }


def prepare(args):
    repository = Path(args.repository_root)
    artifact_root = Path(args.artifact_root)
    output = Path(args.output_directory)
    reviewed = load_json(args.reviewed_target)
    fingerprints, schemas = validation_modules(repository)
    require(reviewed["schema_version"] == 1, "reviewed target schema differs")
    require(reviewed["release_id"] == "2026-07-19.31", "target release ID differs")

    collections = []
    target_members = []
    aliases = {}
    verified_references = []
    parquet_transformations = []
    boundary_transformations = []
    for reviewed_index in reviewed["member_indexes"]:
        index_path = repository / reviewed_index["index_path"]
        receipt = load_json(repository / reviewed_index["receipt_path"])
        content = index_path.read_bytes()
        require(sha256_bytes(content) == reviewed_index["index_sha256"], "member index hash differs")
        require(receipt["index_sha256"] == reviewed_index["index_sha256"], "member receipt differs")
        index = json.loads(content)
        validate_document(schemas, "batch-member-index.schema.json", index)
        members = index["members"]
        for member in members:
            require(set(member["artifacts"]) == set(CORE_ROLES), "ordinary artifact roles differ")
            canonical_boundary, boundary_transformation = canonicalize_boundary(
                member,
                artifact_root,
                reviewed,
            )
            member["artifacts"]["boundary"] = canonical_boundary
            boundary_transformations.append(boundary_transformation)
            for role, reference in list(member["artifacts"].items()):
                checked_reference(reference, artifact_root)
                verified_references.append(reference)
                if role in {"hillslopes", "soils", "landuse"}:
                    canonical_reference, changed = canonicalize_parquet(
                        reference,
                        artifact_root,
                    )
                    member["artifacts"][role] = canonical_reference
                    if changed:
                        parquet_transformations.append(
                            {
                                "watershed_key": member["watershed_key"],
                                "role": role,
                                "source_sha256": reference["sha256"],
                                "canonical_sha256": canonical_reference["sha256"],
                            }
                        )
            target_members.append({**member, "collection_key": index["collection_key"]})
            for runid in [member["runid"], *member["aliases"]]:
                require(runid not in aliases, f"run alias is duplicated: {runid}")
                aliases[runid] = member["watershed_key"]
        normalized_content = canonical_json_bytes(index)
        validate_document(
            schemas,
            "batch-member-index.schema.json",
            json.loads(normalized_content),
        )
        index_reference = publish_content(artifact_root, normalized_content)
        source = {
            "kind": "standalone" if index["expected_member_count"] == 1 else "batch",
            "source_revision": index["source_revision"],
        }
        if "authentication" in index:
            source["authentication"] = index["authentication"]
        collections.append(
            {
                "collection_key": index["collection_key"],
                "display_name": reviewed_index["display_name"],
                "source": source,
                "member_index": index_reference,
                "expected_member_count": len(members),
                "watershed_keys": [member["watershed_key"] for member in members],
            }
        )

    keys = [member["watershed_key"] for member in target_members]
    runids = [member["runid"] for member in target_members]
    require(len(keys) == len(set(keys)) == 129, "target stable-key membership differs")
    require(len(runids) == len(set(runids)) == 129, "target run membership differs")
    require([item["collection_key"] for item in collections] == [
        "gate-creek",
        "victoria-ca",
        "mill-creek",
        "nasa-roses",
        "bremerton",
    ], "target collection order differs")
    by_key = {member["watershed_key"]: member for member in target_members}
    require(by_key["mill-creek"]["runid"] == "some-oligopoly", "Mill Creek run differs")
    require("Bremerton04" not in {member["display_name"] for member in target_members}, "Bremerton04 is included")

    base_path = (
        artifact_root
        / "objects"
        / "sha256"
        / reviewed["base_manifest_sha256"][:2]
        / reviewed["base_manifest_sha256"]
    )
    require(sha256_file(base_path) == reviewed["base_manifest_sha256"], "base manifest differs")
    base = load_json(base_path)
    base_by_key = {member["watershed_key"]: member for member in base["members"]}
    additions = sorted(set(by_key) - set(base_by_key))
    removals = sorted(set(base_by_key) - set(by_key))
    replacements = sorted(
        key for key in set(base_by_key) & set(by_key)
        if base_by_key[key]["runid"] != by_key[key]["runid"]
    )
    require(additions == ["bremerton-01", "bremerton-02", "bremerton-03"], "target additions differ")
    require(not removals, "target unexpectedly removes a stable watershed")
    require(len(replacements) == 94 and "mill-creek" in replacements, "target replacements differ")
    require(
        all(
            base_by_key[key]["runid"] in by_key[key]["aliases"]
            for key in replacements
        ),
        "a replaced current run is not retained as an alias",
    )

    capability_keys = []
    capability_references = []
    for reviewed_index in reviewed["capability_indexes"]:
        path = repository / reviewed_index["index_path"]
        receipt = load_json(repository / reviewed_index["receipt_path"])
        content = path.read_bytes()
        require(sha256_bytes(content) == reviewed_index["index_sha256"], "capability index hash differs")
        require(receipt["index_sha256"] == reviewed_index["index_sha256"], "capability receipt differs")
        index = json.loads(content)
        validate_document(schemas, "rhessys-capability-index.schema.json", index)
        require(index["watershed_key"] == reviewed_index["watershed_key"], "capability watershed differs")
        publish_content(artifact_root, content)
        for reference in artifact_references(index):
            checked_reference(reference, artifact_root)
            capability_references.append(reference)
        capability_keys.append(index["watershed_key"])
    require(capability_keys == [
        "gate-creek",
        "victoria-ca-sooke09",
        "victoria-ca-sooke15",
    ], "capability set differs")
    require("mill-creek" not in capability_keys, "Mill Creek capability was inferred")

    created_at = reviewed["created_at"]
    canonicalization_document = {
        "schema_version": 1,
        "release_id": reviewed["release_id"],
        "tool": "pyarrow",
        "version": reviewed["canonicalization"]["pyarrow_version"],
        "sort_key": reviewed["canonicalization"]["sort_key"],
        "geometry_tool": "GEOS",
        "geometry_version": reviewed["canonicalization"]["geos_version"],
        "boundary_operation": reviewed["canonicalization"]["boundary_operation"],
        "transformed_count": len(parquet_transformations) + len(boundary_transformations),
        "parquet_transformations": parquet_transformations,
        "boundary_transformations": boundary_transformations,
    }
    canonicalization_content = canonical_json_bytes(canonicalization_document)
    canonicalization_reference = publish_content(
        artifact_root,
        canonicalization_content,
    )
    report = {
        "schema_version": 1,
        "report_id": "db31-source-validation",
        "subject": {"type": "release", "id": reviewed["release_id"]},
        "validator": {
            "git_commit": args.validator_git_commit,
            "image_digest": reviewed["validator_image_digest"],
        },
        "started_at": created_at,
        "completed_at": created_at,
        "status": "passed",
        "checks": [
            {"code": "member-indexes", "status": "passed", "count": len(collections)},
            {"code": "target-members", "status": "passed", "count": len(target_members)},
            {"code": "ordinary-artifacts", "status": "passed", "count": len(verified_references)},
            {
                "code": "canonical-target-artifacts",
                "status": "passed",
                "count": len(parquet_transformations) + len(boundary_transformations),
                "summary": f"source-to-target mapping sha256 {canonicalization_reference['sha256']}",
            },
            {"code": "capability-indexes", "status": "passed", "count": len(capability_keys)},
            {"code": "capability-artifacts", "status": "passed", "count": len(capability_references)},
            {"code": "stable-additions", "status": "passed", "count": len(additions)},
            {"code": "run-replacements", "status": "passed", "count": len(replacements)},
            {"code": "stable-removals", "status": "passed", "count": len(removals)},
            {"code": "upstream-fetches", "status": "passed", "count": 0},
        ],
        "summary": "Accepted DB28-DB30 local inputs were verified exactly; unsorted Parquet inputs were deterministically ordered into new immutable target objects without upstream access.",
    }
    validate_document(schemas, "validation-report.schema.json", report)
    report_content = canonical_json_bytes(report)
    report_reference = publish_content(artifact_root, report_content)

    manifest = {
        "schema_version": 1,
        "release_id": reviewed["release_id"],
        "created_at": created_at,
        "compatibility": {
            "schema_version": 1,
            "data_contract": 1,
            "identity_contract": 1,
            "artifact_contract": 1,
            "supported_migrations": {
                "minimum": reviewed["supported_migration"],
                "maximum": reviewed["supported_migration"],
            },
            "materializer": reviewed["materializer"],
            "toolchain": {"postgres": "17.5", "postgis": "3.5.2", "gdal": "3.12.0"},
        },
        "collections": collections,
        "expected_removals": [],
        "lineage": [],
        "validation_report": report_reference,
    }
    validate_document(schemas, "release-manifest.schema.json", manifest)
    manifest_content = canonical_json_bytes(manifest)
    manifest_reference = publish_content(artifact_root, manifest_content)
    require(
        fingerprints.fingerprint_document("release", manifest)
        == fingerprints.fingerprint_document("release", json.loads(manifest_content)),
        "release fingerprint is not canonical",
    )
    write_new(output / "target-canonicalization.json", canonicalization_content)
    write_new(output / "source-validation-report.json", report_content)
    write_new(output / "target-release-manifest.json", manifest_content)
    print(json.dumps({
        "status": "prepared",
        "release_id": reviewed["release_id"],
        "manifest_sha256": manifest_reference["sha256"],
        "release_fingerprint": fingerprints.fingerprint_document("release", manifest),
        "source_validation_sha256": report_reference["sha256"],
        "members": len(target_members),
        "capabilities": len(capability_keys),
        "ordinary_references": len(verified_references),
        "canonical_parquet_artifacts": len(parquet_transformations),
        "canonical_boundary_artifacts": len(boundary_transformations),
        "target_canonicalization_sha256": canonicalization_reference["sha256"],
        "capability_references": len(capability_references),
        "additions": additions,
        "replacements": len(replacements),
        "removals": removals,
    }, sort_keys=True))


def setup_django(repository_root):
    server_root = Path(repository_root) / "server"
    if str(server_root) not in sys.path:
        sys.path.insert(0, str(server_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
    import django

    django.setup()


def replace_index_markers(value, index_reference):
    if isinstance(value, dict):
        return {key: replace_index_markers(child, index_reference) for key, child in value.items()}
    if isinstance(value, list):
        return [replace_index_markers(child, index_reference) for child in value]
    if value == "$INDEX_URI":
        return index_reference["uri"]
    if value == "$INDEX_SHA256":
        return index_reference["sha256"]
    return value


def capability_bootstraps(repository, artifact_root):
    operations = load_module(
        "db30a_operations",
        Path(repository)
        / "docs/work-packages/20260718-db30a-production-legacy-base-adoption/artifacts/db30a_operations.py",
    )
    values = operations.capability_bootstraps(
        Path(repository) / "data-releases/locked-inputs/db28",
        Path(artifact_root),
    )
    return {value.runid: value for value in values}


def target_inputs(manifest_path, artifact_root):
    manifest = load_json(manifest_path)
    indexes = []
    for collection in manifest["collections"]:
        index = load_json(checked_reference(collection["member_index"], artifact_root))
        require(
            index["collection_key"] == collection["collection_key"],
            "target index collection differs",
        )
        indexes.append(index)
    return indexes


def materialized_child_count(reference, artifact_root, role):
    from django.contrib.gis.gdal import DataSource
    from server.watershed.loaders.writers import (
        CHANNEL_MAPPING,
        SUBCATCHMENT_MAPPING,
        _get_feature_field,
    )

    mapping = SUBCATCHMENT_MAPPING if role == "subcatchments" else CHANNEL_MAPPING
    path = checked_reference(reference, artifact_root)
    source = DataSource(str(path))
    require(len(source) == 1, f"{role} artifact layer count differs")
    identities = set()
    for feature in source[0]:
        values = tuple(int(_get_feature_field(feature, field)) for field in mapping.values())
        identities.add(values)
    del source
    return len(identities)


def target_ledger(
    repository,
    reviewed,
    manifest_path,
    artifact_root,
    domain_fingerprint,
    *,
    previous_release=None,
    manage_aliases=True,
):
    from server.watershed.fingerprint_contract import canonical_sha256
    from server.watershed.materializer import CapabilityDeclaration, MaterializationMember
    from server.watershed.models import (
        DataArtifactLineage,
        DataRelease,
        DataRunState,
        WatershedCollection,
        WatershedIdentity,
        WatershedRunAlias,
    )

    manifest = load_json(manifest_path)
    manifest_sha256 = sha256_file(manifest_path)
    fingerprints, _schemas = validation_modules(repository)
    release_fingerprint = fingerprints.fingerprint_document("release", manifest)
    indexes = target_inputs(manifest_path, artifact_root)
    child_counts = {
        member["runid"]: {
            role: materialized_child_count(
                member["artifacts"][role],
                artifact_root,
                role,
            )
            for role in ("subcatchments", "channels")
        }
        for index in indexes
        for member in index["members"]
    }
    totals = {
        "watersheds": sum(index["expected_member_count"] for index in indexes),
        "subcatchments": sum(value["subcatchments"] for value in child_counts.values()),
        "channels": sum(value["channels"] for value in child_counts.values()),
    }
    release = DataRelease.objects.create(
        release_id=reviewed["release_id"],
        manifest_sha256=manifest_sha256,
        release_fingerprint=release_fingerprint,
        domain_fingerprint=domain_fingerprint,
        supported_migration=reviewed["supported_migration"],
        materializer_image_digest=reviewed["materializer"]["image_digest"],
        materializer_git_commit=reviewed["materializer"]["git_commit"],
        previous_release=previous_release,
        expected_watersheds=totals["watersheds"],
        expected_subcatchments=totals["subcatchments"],
        expected_channels=totals["channels"],
        actual_watersheds=totals["watersheds"],
        actual_subcatchments=totals["subcatchments"],
        actual_channels=totals["channels"],
        validation_summary={"db31_source_validation": manifest["validation_report"]["sha256"]},
        created_at=datetime.fromisoformat(reviewed["created_at"].replace("Z", "+00:00")),
    )
    bootstraps = capability_bootstraps(repository, artifact_root)
    members = []
    reviewed_bounds = {}
    used_capabilities = set()
    for index in indexes:
        collection, _created = WatershedCollection.objects.get_or_create(key=index["collection_key"])
        for member in index["members"]:
            identity = WatershedIdentity.objects.filter(watershed_key=member["watershed_key"]).first()
            if identity is None:
                identity = WatershedIdentity.objects.create(
                    watershed_key=member["watershed_key"],
                    collection=collection,
                )
            require(identity.collection_id == collection.pk, "target identity collection differs")
            desired_aliases = [member["runid"], *member["aliases"]]
            for runid in desired_aliases:
                alias, created = WatershedRunAlias.objects.get_or_create(
                    runid=runid,
                    defaults={"watershed_identity": identity, "is_current": False},
                )
                require(alias.watershed_identity_id == identity.pk, "target alias identity differs")
            if manage_aliases:
                require(
                    set(identity.run_aliases.values_list("runid", flat=True)) == set(desired_aliases),
                    "target aliases differ",
                )
                identity.run_aliases.update(is_current=False)
                identity.run_aliases.filter(runid=member["runid"]).update(is_current=True)

            references = dict(member["artifacts"])
            bootstrap = bootstraps.get(member["runid"])
            capability = None
            capability_document = None
            if bootstrap is not None:
                used_capabilities.add(member["runid"])
                index_digest = sha256_bytes(bootstrap.index_content)
                index_reference = artifact_reference(
                    index_digest,
                    len(bootstrap.index_content),
                    "application/json",
                )
                checked_reference(index_reference, artifact_root)
                references[bootstrap.index_role] = index_reference
                configuration = replace_index_markers(
                    bootstrap.runtime_configuration,
                    index_reference,
                )
                capability_fingerprint = canonical_sha256(
                    semantic_value({
                        "capability_type": bootstrap.capability_type,
                        "mode": bootstrap.mode,
                        "durable_base_uri": bootstrap.durable_base_uri,
                        "index_uri": index_reference["uri"],
                        "index_sha256": index_reference["sha256"],
                        "runtime_configuration": configuration,
                    })
                )
                capability_document = {
                    "capability_type": bootstrap.capability_type,
                    "mode": bootstrap.mode,
                    "durable_base_uri": bootstrap.durable_base_uri,
                    "index_role": bootstrap.index_role,
                    "index_uri": index_reference["uri"],
                    "index_sha256": index_reference["sha256"],
                    "capability_fingerprint": capability_fingerprint,
                    "runtime_configuration": configuration,
                }
                capability = CapabilityDeclaration(
                    capability_type=bootstrap.capability_type,
                    mode=bootstrap.mode,
                    durable_base_uri=bootstrap.durable_base_uri,
                    index_role=bootstrap.index_role,
                    runtime_configuration=configuration,
                )
            artifact_hashes = {role: reference["sha256"] for role, reference in references.items()}
            run_fingerprint = canonical_sha256(
                semantic_value({
                    "collection_key": index["collection_key"],
                    "watershed_key": member["watershed_key"],
                    "runid": member["runid"],
                    "artifacts": artifact_hashes,
                    "capability": capability_document,
                })
            )
            run_state = DataRunState.objects.create(
                release=release,
                collection=collection,
                watershed_identity=identity,
                runid=member["runid"],
                run_fingerprint=run_fingerprint,
                metadata_fingerprint=references["metadata"]["sha256"],
                geometry_fingerprint=references["boundary"]["sha256"],
                subcatchment_fingerprint=references["subcatchments"]["sha256"],
                channel_fingerprint=references["channels"]["sha256"],
                hillslope_fingerprint=references["hillslopes"]["sha256"],
                soil_fingerprint=references["soils"]["sha256"],
                landuse_fingerprint=references["landuse"]["sha256"],
                capability_fingerprint=(
                    capability_document["capability_fingerprint"]
                    if capability_document
                    else None
                ),
                actual_subcatchments=child_counts[member["runid"]]["subcatchments"],
                actual_channels=child_counts[member["runid"]]["channels"],
            )
            artifact_paths = {}
            for role, reference in references.items():
                DataArtifactLineage.objects.create(
                    run_state=run_state,
                    role=role,
                    uri=reference["uri"],
                    sha256=reference["sha256"],
                    byte_size=reference["bytes"],
                    media_type=reference["media_type"],
                )
                if role in CORE_ROLES or (capability and role == capability.index_role):
                    artifact_paths[role] = checked_reference(reference, artifact_root)
            members.append(
                MaterializationMember(
                    run_state=run_state,
                    artifact_paths=artifact_paths,
                    capability=capability,
                )
            )
            reviewed_bounds[member["runid"]] = tuple(member["expected"]["bounds"])
    require(used_capabilities == set(bootstraps), "target capability bootstrap membership differs")
    return release, members, reviewed_bounds, totals


def space_budget(members):
    from server.watershed.staging import SpaceBudget

    artifact_bytes = sum(
        path.stat().st_size
        for member in members
        for path in member.artifact_paths.values()
    )
    return SpaceBudget(
        artifact_bytes=artifact_bytes,
        staging_bytes=artifact_bytes * 2,
        index_bytes=artifact_bytes,
        backup_bytes=0,
        wal_bytes=artifact_bytes,
        margin_bytes=artifact_bytes,
    )


def capability_checks(repository, reviewed):
    from django.urls import reverse
    from rest_framework.test import APIClient
    from server.watershed.models import RunCapability, Watershed

    client = APIClient(HTTP_HOST="firewisewatersheds.org")
    gate_runid = "aversive-forestry"
    gate_catalog = client.get(reverse("rhessys-outputs-list", args=[gate_runid]))
    require(gate_catalog.status_code == 200, "Gate RHESSYS catalog failed")
    require(gate_catalog.data["capability"]["source"] == "materialized", "Gate capability is not materialized")
    gate_query = client.post(
        reverse("rhessys-query", args=[gate_runid]),
        {
            "kind": "choropleth",
            "scenario": "S1",
            "variable": "streamflow",
            "spatial_scale": "hillslope",
            "year": 2000,
        },
        format="json",
    )
    require(gate_query.status_code == 200 and len(gate_query.data["rows"]) == 173, "Gate query differs")
    sooke = {}
    for name in ("Sooke09", "Sooke15"):
        runid = f"batch;;victoria-ca-2026-sbs;;{name}"
        catalog = client.get(reverse("rhessys-outputs-list", args=[runid]))
        tile = client.get(
            reverse(
                "rhessys-outputs-tile",
                args=[runid, "baseline", "streamflow", 0, 0, 0],
            )
        )
        require(
            catalog.status_code == 200
            and catalog.data["capability"]["source"] == "materialized"
            and tile.status_code == 200
            and bytes(tile.content).startswith(b"\x89PNG\r\n\x1a\n"),
            f"{name} capability check failed",
        )
        sooke[name] = {
            "scenarios": len(catalog.data["scenarios"]),
            "tile_bytes": len(tile.content),
        }
    mill = client.get(reverse("watershed-capabilities", args=["some-oligopoly"]))
    require(
        mill.status_code == 200
        and mill.data["rhessys"]["available"] is False
        and mill.data["rhessys"]["source"] == "none",
        "Mill Creek RHESSYS was inferred",
    )
    base_manifest = load_json(
        Path(args_global.artifact_root)
        / "objects"
        / "sha256"
        / reviewed["base_manifest_sha256"][:2]
        / reviewed["base_manifest_sha256"]
    )
    target_runids = set(Watershed.objects.values_list("runid", flat=True))
    former = sorted(
        member["runid"]
        for member in base_manifest["members"]
        if member["runid"] not in target_runids
    )
    require(len(former) == 94, "former run replacement count differs")
    require(RunCapability.objects.count() == 3, "target capability count differs")
    return {
        "gate_rows": len(gate_query.data["rows"]),
        "sooke": sooke,
        "mill_rhessys": "absent",
        "former_runs_absent": len(former),
        "bremerton04": "absent",
    }


def build_target(args):
    setup_django(args.repository_root)
    from django.conf import settings
    from server.watershed.models import DataReleaseAttempt
    from server.watershed.release_ledger import begin_release_attempt, transition_attempt
    from server.watershed.release_validation import validated_empty_build

    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]
    reviewed = load_json(args.reviewed_target)
    release, members, bounds, totals = target_ledger(
        args.repository_root,
        reviewed,
        args.manifest,
        args.artifact_root,
        args.expected_domain_fingerprint,
    )
    attempt = begin_release_attempt(
        release=release,
        actor_kind=DataReleaseAttempt.ActorKind.OPERATOR,
        actor_identifier=f"roger-db31-{args.build_label}",
        target_environment="forest1-isolated-clean-build",
        application_git_commit=reviewed["materializer"]["git_commit"],
        reviewed_plan_sha256=args.plan_sha256,
        lease_owner=f"roger-db31-{args.build_label}",
    )
    attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
    budget = space_budget(members)
    result = validated_empty_build(
        attempt,
        members,
        budget=budget,
        observed_available_bytes=shutil.disk_usage(args.artifact_root).free,
        actual_plan_sha256=args.plan_sha256,
        validator_git_commit=args.validator_git_commit,
        validator_image_digest=reviewed["validator_image_digest"],
        reviewed_bounds=bounds,
        batch_size=BATCH_SIZE,
    )
    if args.expected_domain_fingerprint != "0" * 64:
        require(
            result.fingerprints.domain == args.expected_domain_fingerprint,
            "clean-build domain fingerprint differs from the reviewed value",
        )
    checks = capability_checks(args.repository_root, reviewed)
    document = {
        "schema_version": 1,
        "build_label": args.build_label,
        "release_id": release.release_id,
        "manifest_sha256": release.manifest_sha256,
        "release_fingerprint": release.release_fingerprint,
        "plan_sha256": args.plan_sha256,
        "fingerprints": result.fingerprints.as_document(),
        "expected_counts": totals,
        "validation_report": result.report,
        "capability_checks": checks,
        "budget_required_bytes": budget.required_bytes,
        "upstream_fetches": 0,
    }
    write_new(args.output, canonical_json_bytes(document))
    print(json.dumps({
        "status": "built",
        "build_label": args.build_label,
        "manifest_sha256": release.manifest_sha256,
        "domain_fingerprint": result.fingerprints.domain,
        "capability_fingerprint": result.fingerprints.capabilities,
        "counts": result.fingerprints.as_document()["counts"],
        "report_status": result.report["status"],
        "capability_checks": checks,
    }, sort_keys=True))


def activate_legacy_base(reviewed, artifact_root):
    from django.db import transaction
    from server.watershed.domain_mutations import apply_staged_empty_base
    from server.watershed.legacy_base import (
        install_baseline_ledger,
        load_legacy_baseline,
        materialization_members,
    )
    from server.watershed.materializer import stage_locked_release
    from server.watershed.models import DataReleaseAttempt
    from server.watershed.release_ledger import (
        activate_release,
        begin_release_attempt,
        transition_attempt,
    )
    from server.watershed.release_validation import compute_serving_fingerprints

    baseline = load_legacy_baseline(artifact_root, reviewed["base_manifest_sha256"])
    release = install_baseline_ledger(baseline)
    members = materialization_members(baseline, release)
    plan_sha = hashlib.sha256(
        f"db31-plan-base:{baseline.manifest_sha256}".encode()
    ).hexdigest()
    attempt = begin_release_attempt(
        release=release,
        actor_kind=DataReleaseAttempt.ActorKind.OPERATOR,
        actor_identifier="roger-db31-plan-base",
        target_environment="forest1-isolated-plan-base",
        application_git_commit=reviewed["materializer"]["git_commit"],
        reviewed_plan_sha256=plan_sha,
        lease_owner="roger-db31-plan-base",
    )
    attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
    budget = space_budget(members)
    stage_locked_release(
        attempt,
        members,
        budget=budget,
        observed_available_bytes=shutil.disk_usage(artifact_root).free,
        batch_size=BATCH_SIZE,
    )
    attempt = transition_attempt(
        attempt,
        DataReleaseAttempt.Status.APPLYING,
        actual_plan_sha256=plan_sha,
    )
    with transaction.atomic():
        apply_staged_empty_base(attempt, batch_size=BATCH_SIZE)
        activate_release(attempt)
    observed = compute_serving_fingerprints(release)
    require(
        release.manifest_sha256 == reviewed["base_manifest_sha256"]
        and observed.domain == baseline.document["domain_fingerprint"]
        and observed.capabilities == baseline.document["capability_fingerprint"],
        "materialized DB30A base differs",
    )
    return release, observed.domain


def generate_plans(args):
    setup_django(args.repository_root)
    from server.watershed.planner import plan_bytes, plan_empty_build, plan_exact_inverse, plan_forward

    reviewed = load_json(args.reviewed_target)
    base, base_domain_fingerprint = activate_legacy_base(
        reviewed,
        args.artifact_root,
    )
    target, _members, _bounds, _totals = target_ledger(
        args.repository_root,
        reviewed,
        args.manifest,
        args.artifact_root,
        args.expected_domain_fingerprint,
        previous_release=base,
        manage_aliases=False,
    )
    forward = plan_forward(base, target)
    plans = {
        "forward.json": forward,
        "exact-inverse.json": plan_exact_inverse(forward),
        "empty-build.json": plan_empty_build(target),
    }
    output = Path(args.output_directory)
    for name, document in plans.items():
        content = plan_bytes(document)
        path = output / name
        if path.exists():
            require(path.read_bytes() == content, f"existing {name} differs")
        else:
            write_new(path, content)
    operations = {}
    for action in forward["actions"]:
        operations[action["operation"]] = operations.get(action["operation"], 0) + 1
    require(operations == {"add": 3, "change": 126}, "forward action distribution differs")
    print(json.dumps({
        "status": "planned",
        "base_manifest_sha256": base.manifest_sha256,
        "base_domain_fingerprint": base_domain_fingerprint,
        "target_manifest_sha256": target.manifest_sha256,
        "target_domain_fingerprint": target.domain_fingerprint,
        "operations": operations,
        "row_delta": forward["expected_row_delta"],
        "plan_sha256": {
            name: sha256_bytes(plan_bytes(document))
            for name, document in plans.items()
        },
    }, sort_keys=True))


def generate_empty_plan(args):
    setup_django(args.repository_root)
    from server.watershed.planner import plan_bytes, plan_empty_build

    reviewed = load_json(args.reviewed_target)
    target, _members, _bounds, _totals = target_ledger(
        args.repository_root,
        reviewed,
        args.manifest,
        args.artifact_root,
        args.expected_domain_fingerprint,
    )
    content = plan_bytes(plan_empty_build(target))
    write_new(args.output, content)
    print(json.dumps({
        "status": "empty-plan",
        "target_manifest_sha256": target.manifest_sha256,
        "target_domain_fingerprint": target.domain_fingerprint,
        "plan_sha256": sha256_bytes(content),
    }, sort_keys=True))


def publish_files(args):
    references = {}
    for value in args.input:
        path = Path(value)
        reference = publish_content(args.artifact_root, path.read_bytes())
        references[path.name] = reference
    print(json.dumps({"status": "published", "references": references}, sort_keys=True))


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--repository-root", required=True)
    prepare_parser.add_argument("--reviewed-target", required=True)
    prepare_parser.add_argument("--artifact-root", required=True)
    prepare_parser.add_argument("--output-directory", required=True)
    prepare_parser.add_argument("--validator-git-commit", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--repository-root", required=True)
    build_parser.add_argument("--reviewed-target", required=True)
    build_parser.add_argument("--artifact-root", required=True)
    build_parser.add_argument("--manifest", required=True)
    build_parser.add_argument("--expected-domain-fingerprint", required=True)
    build_parser.add_argument("--plan-sha256", required=True)
    build_parser.add_argument("--validator-git-commit", required=True)
    build_parser.add_argument("--build-label", required=True)
    build_parser.add_argument("--output", required=True)

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--repository-root", required=True)
    plan_parser.add_argument("--reviewed-target", required=True)
    plan_parser.add_argument("--artifact-root", required=True)
    plan_parser.add_argument("--manifest", required=True)
    plan_parser.add_argument("--expected-domain-fingerprint", required=True)
    plan_parser.add_argument("--output-directory", required=True)

    empty_plan_parser = subparsers.add_parser("empty-plan")
    empty_plan_parser.add_argument("--repository-root", required=True)
    empty_plan_parser.add_argument("--reviewed-target", required=True)
    empty_plan_parser.add_argument("--artifact-root", required=True)
    empty_plan_parser.add_argument("--manifest", required=True)
    empty_plan_parser.add_argument("--expected-domain-fingerprint", required=True)
    empty_plan_parser.add_argument("--output", required=True)

    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--artifact-root", required=True)
    publish_parser.add_argument("--input", action="append", required=True)
    return parser.parse_args()


def main():
    global args_global
    args_global = parse_args()
    if args_global.action == "prepare":
        prepare(args_global)
    elif args_global.action == "build":
        build_target(args_global)
    elif args_global.action == "plan":
        generate_plans(args_global)
    elif args_global.action == "empty-plan":
        generate_empty_plan(args_global)
    else:
        publish_files(args_global)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
