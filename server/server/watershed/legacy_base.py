import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Mapping

import pyarrow as arrow
import pyarrow.parquet as parquet
from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader

from server.watershed.fingerprint_contract import canonical_sha256
from server.watershed.loaders.writers import (
    HILLSLOPES_FIELD_MAP,
    LANDUSE_FIELD_MAP,
    SOILS_FIELD_MAP,
    WATERSHED_FIELD_SOURCES,
)
from server.watershed.materializer import (
    CORE_ARTIFACT_MEDIA_TYPES,
    CapabilityDeclaration,
    MaterializationMember,
)
from server.watershed.models import (
    ActiveDataRelease,
    Channel,
    DataArtifactLineage,
    DataRelease,
    DataReleaseAttempt,
    DataRunState,
    RunCapability,
    Subcatchment,
    Watershed,
    WatershedCollection,
    WatershedIdentity,
    WatershedRunAlias,
)
from server.watershed.release_ledger import (
    activate_release,
    begin_release_attempt,
    transition_attempt,
)
from server.watershed.release_validation import (
    ServingFingerprints,
    _channel_documents,
    _geometry_bytes,
    _semantic_value,
    _sequence_fingerprint,
    _subcatchment_documents,
    compute_serving_fingerprints,
)
from server.watershed.runtime_capabilities import validate_runtime_configuration


class LegacyBaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReviewedIdentity:
    runid: str
    collection_key: str
    watershed_key: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapabilityBootstrap:
    runid: str
    capability_type: str
    mode: str
    durable_base_uri: str
    index_role: str
    index_content: bytes
    runtime_configuration: Mapping[str, Any]
    runtime_artifacts: Mapping[str, tuple[bytes, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class LegacyBaseline:
    root: Path
    document: Mapping[str, Any]
    manifest_sha256: str

    def artifact_path(self, digest):
        return self.root / "objects" / "sha256" / digest[:2] / digest


STABLE_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _require(condition, message):
    if not condition:
        raise LegacyBaseError(message)


@transaction.atomic
def assign_reviewed_identities(assignments):
    assignments = tuple(assignments)
    by_runid = {assignment.runid: assignment for assignment in assignments}
    _require(len(by_runid) == len(assignments), "Reviewed run IDs are duplicated.")
    runids = set(Watershed.objects.values_list("runid", flat=True))
    _require(runids and set(by_runid) == runids, "Reviewed identity membership differs from serving rows.")
    _require(
        len({item.watershed_key for item in assignments}) == len(assignments),
        "Reviewed watershed keys are duplicated.",
    )
    for assignment in assignments:
        _require(
            STABLE_KEY.fullmatch(assignment.collection_key)
            and STABLE_KEY.fullmatch(assignment.watershed_key),
            "Reviewed identity contains an invalid stable key.",
        )
        watershed = Watershed.objects.select_for_update().get(runid=assignment.runid)
        collection, _ = WatershedCollection.objects.get_or_create(
            key=assignment.collection_key
        )
        identity = WatershedIdentity.objects.filter(
            watershed_key=assignment.watershed_key
        ).first()
        if identity is None:
            identity = WatershedIdentity.objects.create(
                watershed_key=assignment.watershed_key,
                collection=collection,
            )
        _require(
            identity.collection_id == collection.pk
            and watershed.logical_watershed_id in {None, identity.pk},
            "Reviewed identity conflicts with existing identity state.",
        )
        expected_aliases = {assignment.runid, *assignment.aliases}
        conflicts = WatershedRunAlias.objects.filter(runid__in=expected_aliases).exclude(
            watershed_identity=identity
        )
        _require(not conflicts.exists(), "Reviewed alias belongs to another identity.")
        current_aliases = set(
            WatershedRunAlias.objects.filter(watershed_identity=identity).values_list(
                "runid", flat=True
            )
        )
        _require(
            not current_aliases or current_aliases == expected_aliases,
            "Existing aliases differ from the reviewed assignment.",
        )
        for alias in sorted(expected_aliases):
            WatershedRunAlias.objects.get_or_create(
                runid=alias,
                defaults={
                    "watershed_identity": identity,
                    "is_current": alias == assignment.runid,
                },
            )
        WatershedRunAlias.objects.filter(watershed_identity=identity).update(
            is_current=False
        )
        WatershedRunAlias.objects.filter(runid=assignment.runid).update(is_current=True)
        if watershed.logical_watershed_id is None:
            Watershed.objects.filter(pk=watershed.pk).update(logical_watershed=identity)
        Subcatchment.objects.filter(watershed=watershed).update(
            logical_watershed=identity
        )
        Channel.objects.filter(watershed=watershed).update(logical_watershed=identity)


def _json_bytes(document):
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_legacy_baseline(root, manifest_sha256):
    root = Path(root)
    _require(
        re.fullmatch(r"[a-f0-9]{64}", manifest_sha256),
        "Baseline manifest digest is invalid.",
    )
    path = root / "objects" / "sha256" / manifest_sha256[:2] / manifest_sha256
    _require(path.is_file() and not path.is_symlink(), "Baseline manifest is absent.")
    content = path.read_bytes()
    _require(
        hashlib.sha256(content).hexdigest() == manifest_sha256,
        "Baseline manifest checksum differs.",
    )
    try:
        document = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LegacyBaseError("Baseline manifest is not valid JSON.") from error
    _require(isinstance(document, dict), "Baseline manifest root is invalid.")
    return LegacyBaseline(root=root, document=document, manifest_sha256=manifest_sha256)


def _feature_collection(rows, properties):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    **properties(row),
                    "DB21A_GeometryEWKB": (
                        row.geom.hexewkb
                        if isinstance(row.geom.hexewkb, str)
                        else bytes(row.geom.hexewkb).hex()
                    ),
                },
                "geometry": json.loads(row.geom.geojson),
            }
            for row in rows
        ],
    }


def _parquet_bytes(children, field_map):
    columns = {"TopazID": [child.topazid for child in children]}
    for model_field, source_field, _converter in field_map:
        columns[source_field] = [getattr(child, model_field) for child in children]
    sink = arrow.BufferOutputStream()
    parquet.write_table(arrow.table(columns), sink)
    return sink.getvalue().to_pybytes()


def _publish(root, content):
    digest = hashlib.sha256(content).hexdigest()
    destination = root / "objects" / "sha256" / digest[:2] / digest
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.exists():
        _require(destination.read_bytes() == content, "Content-addressed artifact conflicts with existing bytes.")
        return digest, destination
    with NamedTemporaryFile(dir=destination.parent, prefix=".partial-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.chmod(temporary, 0o600)
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return digest, destination


def _artifact(root, base_uri, content, media_type):
    digest, _path = _publish(root, content)
    return {
        "uri": f"{base_uri.rstrip('/')}/objects/sha256/{digest[:2]}/{digest}",
        "sha256": digest,
        "bytes": len(content),
        "media_type": media_type,
    }


def _replace_markers(value, *, index_uri, index_sha256, runtime_artifacts):
    if isinstance(value, dict):
        return {
            key: _replace_markers(
                child,
                index_uri=index_uri,
                index_sha256=index_sha256,
                runtime_artifacts=runtime_artifacts,
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_markers(
                child,
                index_uri=index_uri,
                index_sha256=index_sha256,
                runtime_artifacts=runtime_artifacts,
            )
            for child in value
        ]
    if value == "$INDEX_URI":
        return index_uri
    if value == "$INDEX_SHA256":
        return index_sha256
    if isinstance(value, str) and value.startswith("$ARTIFACT_"):
        coordinate, separator, key = value.partition(":")
        _require(separator and key in runtime_artifacts, "Runtime artifact marker is invalid.")
        reference = runtime_artifacts[key]
        field_name = {
            "$ARTIFACT_URI": "uri",
            "$ARTIFACT_SHA256": "sha256",
            "$ARTIFACT_BYTES": "bytes",
        }.get(coordinate)
        _require(field_name is not None, "Runtime artifact marker is unsupported.")
        return reference[field_name]
    return value


def _legacy_fingerprints(capability_documents):
    capability_documents = sorted(
        capability_documents,
        key=lambda item: (
            item["collection_key"],
            item["watershed_key"],
            item["runid"],
            item["capability_type"],
        ),
    )
    by_runid = {}
    for document in capability_documents:
        by_runid.setdefault(document["runid"], []).append(document)

    def domain_documents():
        watersheds = Watershed.objects.select_related(
            "logical_watershed__collection"
        ).order_by(
            "logical_watershed__collection_id",
            "logical_watershed__watershed_key",
            "runid",
        )
        for watershed in watersheds.iterator(chunk_size=1000):
            yield {
                "collection_key": watershed.logical_watershed.collection_id,
                "watershed_key": watershed.logical_watershed.watershed_key,
                "runid": watershed.runid,
                "geometry": _geometry_bytes(watershed.geom),
                "simplified_geometry": _geometry_bytes(watershed.simplified_geom),
                "metadata": _semantic_value(
                    {
                        field: getattr(watershed, field)
                        for field in sorted(
                            set(WATERSHED_FIELD_SOURCES) - {"runid", "geom"}
                        )
                    }
                ),
                "subcatchments": _sequence_fingerprint(
                    "serving-subcatchments", _subcatchment_documents(watershed)
                ),
                "channels": _sequence_fingerprint(
                    "serving-channels", _channel_documents(watershed)
                ),
                "capabilities": _sequence_fingerprint(
                    "serving-run-capabilities", by_runid.get(watershed.runid, ())
                ),
            }

    return ServingFingerprints(
        domain=_sequence_fingerprint("serving-watershed-domain", domain_documents()),
        capabilities=_sequence_fingerprint(
            "serving-capabilities", capability_documents
        ),
        watershed_rows=Watershed.objects.count(),
        subcatchment_rows=Subcatchment.objects.count(),
        channel_rows=Channel.objects.count(),
        capability_rows=len(capability_documents),
    )


def export_legacy_base(
    root,
    *,
    release_id,
    artifact_base_uri,
    supported_migration,
    materializer_git_commit,
    materializer_image_digest,
    capabilities=(),
):
    capabilities = tuple(capabilities)
    root = Path(root)
    _require(not root.is_symlink(), "Export root may not be a symlink.")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    watersheds = list(
        Watershed.objects.select_related("logical_watershed__collection").order_by(
            "logical_watershed__collection_id",
            "logical_watershed__watershed_key",
            "runid",
        )
    )
    _require(watersheds, "Legacy export requires populated serving rows.")
    _require(
        all(watershed.logical_watershed_id for watershed in watersheds),
        "Legacy export requires reviewed stable identities.",
    )
    capability_templates = {item.runid: item for item in capabilities}
    _require(
        len(capability_templates) == len(capabilities)
        and set(capability_templates).issubset({row.runid for row in watersheds}),
        "Capability bootstrap membership is invalid.",
    )
    members = []
    capability_documents = []
    for watershed in watersheds:
        identity = watershed.logical_watershed
        aliases = sorted(
            identity.run_aliases.exclude(runid=watershed.runid).values_list(
                "runid", flat=True
            )
        )
        source_properties = {
            sources[0]: getattr(watershed, model_field)
            for model_field, sources in WATERSHED_FIELD_SOURCES.items()
            if model_field not in {"runid", "geom"}
            and getattr(watershed, model_field) is not None
        }
        contents = {
            "metadata": _json_bytes(
                {
                    "schema_version": 1,
                    "collection_key": identity.collection_id,
                    "source_revision": "legacy-export-v1",
                    "watershed_key": identity.watershed_key,
                    "runid": watershed.runid,
                    "display_name": watershed.srcname,
                    "aliases": aliases,
                    "source_properties": source_properties,
                }
            ),
            "boundary": _json_bytes(
                _feature_collection(
                    [watershed],
                    lambda row: {
                        "DB21A_SimplifiedEWKB": (
                            (
                                row.simplified_geom.hexewkb
                                if isinstance(row.simplified_geom.hexewkb, str)
                                else bytes(row.simplified_geom.hexewkb).hex()
                            )
                            if row.simplified_geom
                            else None
                        )
                    },
                )
            ),
        }
        subcatchments = list(
            Subcatchment.objects.filter(watershed=watershed).order_by("topazid")
        )
        channels = list(
            Channel.objects.filter(watershed=watershed).order_by(
                "topazid", "weppid", "order"
            )
        )
        contents["subcatchments"] = _json_bytes(
            _feature_collection(
                subcatchments,
                lambda row: {"TopazID": row.topazid, "WeppID": row.weppid},
            )
        )
        contents["channels"] = _json_bytes(
            _feature_collection(
                channels,
                lambda row: {
                    "TopazID": row.topazid,
                    "WeppID": row.weppid,
                    "Order": row.order,
                },
            )
        )
        contents["hillslopes"] = _parquet_bytes(subcatchments, HILLSLOPES_FIELD_MAP)
        contents["soils"] = _parquet_bytes(subcatchments, SOILS_FIELD_MAP)
        contents["landuse"] = _parquet_bytes(subcatchments, LANDUSE_FIELD_MAP)
        artifacts = {
            role: _artifact(
                root,
                artifact_base_uri,
                content,
                CORE_ARTIFACT_MEDIA_TYPES[role],
            )
            for role, content in contents.items()
        }
        capability = None
        template = capability_templates.get(watershed.runid)
        if template:
            index = _artifact(
                root,
                artifact_base_uri,
                template.index_content,
                "application/json",
            )
            artifacts[template.index_role] = index
            runtime_artifacts = {}
            for key, (content, media_type) in sorted(template.runtime_artifacts.items()):
                _require(STABLE_KEY.fullmatch(key), "Runtime artifact key is invalid.")
                reference = _artifact(
                    root,
                    artifact_base_uri,
                    content,
                    media_type,
                )
                runtime_artifacts[key] = reference
                artifacts[f"capability-{key}"] = reference
            configuration = _replace_markers(
                template.runtime_configuration,
                index_uri=index["uri"],
                index_sha256=index["sha256"],
                runtime_artifacts=runtime_artifacts,
            )
            capability_fingerprint = canonical_sha256(
                {
                    "capability_type": template.capability_type,
                    "mode": template.mode,
                    "durable_base_uri": template.durable_base_uri,
                    "index_uri": index["uri"],
                    "index_sha256": index["sha256"],
                    "runtime_configuration": configuration,
                }
            )
            capability = {
                "capability_type": template.capability_type,
                "mode": template.mode,
                "durable_base_uri": template.durable_base_uri,
                "index_role": template.index_role,
                "index_uri": index["uri"],
                "index_sha256": index["sha256"],
                "capability_fingerprint": capability_fingerprint,
                "runtime_configuration": configuration,
            }
            capability_documents.append(
                {
                    "collection_key": identity.collection_id,
                    "watershed_key": identity.watershed_key,
                    "runid": watershed.runid,
                    **{key: value for key, value in capability.items() if key != "index_role"},
                }
            )
        fingerprints = {role: value["sha256"] for role, value in artifacts.items()}
        members.append(
            {
                "collection_key": identity.collection_id,
                "watershed_key": identity.watershed_key,
                "runid": watershed.runid,
                "aliases": aliases,
                "counts": {
                    "watersheds": 1,
                    "subcatchments": len(subcatchments),
                    "channels": len(channels),
                },
                "bounds": [str(value) for value in watershed.geom.extent],
                "artifacts": artifacts,
                "fingerprints": {
                    "run": canonical_sha256(
                        {
                            "collection_key": identity.collection_id,
                            "watershed_key": identity.watershed_key,
                            "runid": watershed.runid,
                            "artifacts": fingerprints,
                            "capability": capability,
                        }
                    ),
                    "metadata": artifacts["metadata"]["sha256"],
                    "geometry": artifacts["boundary"]["sha256"],
                    "subcatchments": artifacts["subcatchments"]["sha256"],
                    "channels": artifacts["channels"]["sha256"],
                    "hillslopes": artifacts["hillslopes"]["sha256"],
                    "soils": artifacts["soils"]["sha256"],
                    "landuse": artifacts["landuse"]["sha256"],
                },
                "capability": capability,
            }
        )
    serving = _legacy_fingerprints(capability_documents)
    document = {
        "schema_version": 1,
        "release_id": release_id,
        "contracts": {
            "data": 1,
            "identity": 1,
            "artifact": 1,
            "fingerprint": 1,
        },
        "supported_migration": supported_migration,
        "materializer": {
            "git_commit": materializer_git_commit,
            "image_digest": materializer_image_digest,
        },
        "counts": serving.as_document()["counts"],
        "domain_fingerprint": serving.domain,
        "capability_fingerprint": serving.capabilities,
        "members": members,
    }
    manifest_content = _json_bytes(document)
    manifest_sha256 = hashlib.sha256(manifest_content).hexdigest()
    published_sha256, _path = _publish(root, manifest_content)
    _require(published_sha256 == manifest_sha256, "Baseline manifest publication differs.")
    return LegacyBaseline(root=root, document=document, manifest_sha256=manifest_sha256)


def _verify_supported_migration(name):
    parts = name.split(".", 1)
    _require(len(parts) == 2, "Supported migration coordinate is invalid.")
    loader = MigrationLoader(connection)
    _require(tuple(parts) in loader.applied_migrations, "Supported migration is not applied.")
    _require(tuple(parts) in loader.graph.leaf_nodes(parts[0]), "Supported migration is not the current leaf.")


def _verify_baseline(baseline):
    _require(
        hashlib.sha256(_json_bytes(baseline.document)).hexdigest()
        == baseline.manifest_sha256,
        "Baseline manifest checksum differs.",
    )
    _verify_supported_migration(baseline.document["supported_migration"])
    for member in baseline.document["members"]:
        for reference in member["artifacts"].values():
            path = baseline.artifact_path(reference["sha256"])
            _require(path.is_file() and not path.is_symlink(), "Baseline artifact is absent.")
            _require(
                path.stat().st_size == reference["bytes"]
                and hashlib.sha256(path.read_bytes()).hexdigest() == reference["sha256"],
                "Baseline artifact bytes differ.",
            )


def _identity_for_member(member, create_identities):
    identity = WatershedIdentity.objects.filter(
        watershed_key=member["watershed_key"]
    ).first()
    if identity is None and create_identities:
        collection, _ = WatershedCollection.objects.get_or_create(
            key=member["collection_key"]
        )
        identity = WatershedIdentity.objects.create(
            watershed_key=member["watershed_key"], collection=collection
        )
        for alias in [member["runid"], *member["aliases"]]:
            WatershedRunAlias.objects.create(
                runid=alias,
                watershed_identity=identity,
                is_current=alias == member["runid"],
            )
    _require(
        identity is not None
        and identity.collection_id == member["collection_key"]
        and set(identity.run_aliases.values_list("runid", flat=True))
        == {member["runid"], *member["aliases"]}
        and identity.run_aliases.filter(
            runid=member["runid"], is_current=True
        ).exists(),
        "Baseline identity state differs.",
    )
    return identity


def _create_ledger(baseline, *, create_identities, include_capabilities):
    document = baseline.document
    _require(not DataRelease.objects.filter(pk=document["release_id"]).exists(), "Baseline release already exists.")
    counts = document["counts"]
    release = DataRelease.objects.create(
        release_id=document["release_id"],
        manifest_sha256=baseline.manifest_sha256,
        release_fingerprint=canonical_sha256({"members": document["members"]}),
        domain_fingerprint=document["domain_fingerprint"],
        supported_migration=document["supported_migration"],
        materializer_image_digest=document["materializer"]["image_digest"],
        materializer_git_commit=document["materializer"]["git_commit"],
        expected_watersheds=counts["watersheds"],
        expected_subcatchments=counts["subcatchments"],
        expected_channels=counts["channels"],
        actual_watersheds=counts["watersheds"],
        actual_subcatchments=counts["subcatchments"],
        actual_channels=counts["channels"],
        validation_summary={"legacy_baseline": True},
        created_at=datetime.now(timezone.utc),
    )
    for member in document["members"]:
        identity = _identity_for_member(member, create_identities)
        fingerprints = member["fingerprints"]
        capability = member["capability"]
        run_state = DataRunState.objects.create(
            release=release,
            collection=identity.collection,
            watershed_identity=identity,
            runid=member["runid"],
            run_fingerprint=fingerprints["run"],
            metadata_fingerprint=fingerprints["metadata"],
            geometry_fingerprint=fingerprints["geometry"],
            subcatchment_fingerprint=fingerprints["subcatchments"],
            channel_fingerprint=fingerprints["channels"],
            hillslope_fingerprint=fingerprints["hillslopes"],
            soil_fingerprint=fingerprints["soils"],
            landuse_fingerprint=fingerprints["landuse"],
            capability_fingerprint=(
                capability["capability_fingerprint"] if capability else None
            ),
            actual_subcatchments=member["counts"]["subcatchments"],
            actual_channels=member["counts"]["channels"],
        )
        for role, reference in member["artifacts"].items():
            DataArtifactLineage.objects.create(
                run_state=run_state,
                role=role,
                uri=reference["uri"],
                sha256=reference["sha256"],
                byte_size=reference["bytes"],
                media_type=reference["media_type"],
            )
        if capability and include_capabilities:
            row = RunCapability(
                run_state=run_state,
                watershed_identity=identity,
                capability_type=capability["capability_type"],
                mode=capability["mode"],
                durable_base_uri=capability["durable_base_uri"],
                index_uri=capability["index_uri"],
                index_sha256=capability["index_sha256"],
                capability_fingerprint=capability["capability_fingerprint"],
                runtime_configuration=capability["runtime_configuration"],
            )
            try:
                row.full_clean()
                validate_runtime_configuration(row)
                row.save()
            except Exception as error:
                raise LegacyBaseError(
                    "Capability bootstrap is invalid."
                ) from error
    return release


@transaction.atomic
def install_baseline_ledger(baseline):
    _verify_baseline(baseline)
    active = ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    _require(active.state == ActiveDataRelease.State.EMPTY, "Ledger install requires EMPTY.")
    _require(not Watershed.objects.exists(), "Ledger install requires an empty serving domain.")
    return _create_ledger(
        baseline, create_identities=True, include_capabilities=False
    )


def materialization_members(baseline, release):
    members = []
    by_runid = {member["runid"]: member for member in baseline.document["members"]}
    for run_state in release.run_states.order_by("runid"):
        member = by_runid[run_state.runid]
        capability = member["capability"]
        declaration = None
        if capability:
            declaration = CapabilityDeclaration(
                capability_type=capability["capability_type"],
                mode=capability["mode"],
                durable_base_uri=capability["durable_base_uri"],
                index_role=capability["index_role"],
                runtime_configuration=capability["runtime_configuration"],
            )
        members.append(
            MaterializationMember(
                run_state=run_state,
                artifact_paths={
                    role: baseline.artifact_path(reference["sha256"])
                    for role, reference in member["artifacts"].items()
                    if role in CORE_ARTIFACT_MEDIA_TYPES
                    or (capability and role == capability["index_role"])
                },
                capability=declaration,
            )
        )
    return members


@transaction.atomic
def adopt_legacy_base(
    baseline,
    *,
    actor_identifier,
    application_git_commit,
    reviewed_plan_sha256,
):
    _verify_baseline(baseline)
    active = ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    _require(
        active.state == ActiveDataRelease.State.EMPTY
        and active.release_id is None
        and Watershed.objects.exists(),
        "Adoption requires EMPTY with populated serving rows.",
    )
    _require(not DataRelease.objects.exists(), "Adoption requires an unmanaged ledger.")
    serving_runids = set(Watershed.objects.values_list("runid", flat=True))
    baseline_runids = {member["runid"] for member in baseline.document["members"]}
    _require(serving_runids == baseline_runids, "Serving membership differs from the baseline.")
    release = _create_ledger(
        baseline, create_identities=False, include_capabilities=True
    )
    fingerprints = compute_serving_fingerprints(release)
    _require(
        fingerprints.domain == baseline.document["domain_fingerprint"]
        and fingerprints.capabilities
        == baseline.document["capability_fingerprint"],
        "Serving fingerprints differ from the reviewed baseline.",
    )
    attempt = begin_release_attempt(
        release=release,
        actor_kind=DataReleaseAttempt.ActorKind.OPERATOR,
        actor_identifier=actor_identifier,
        target_environment="legacy-adoption",
        application_git_commit=application_git_commit,
        reviewed_plan_sha256=reviewed_plan_sha256,
        lease_owner=actor_identifier,
        lease_duration=timedelta(minutes=30),
    )
    attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
    attempt = transition_attempt(
        attempt,
        DataReleaseAttempt.Status.APPLYING,
        actual_plan_sha256=reviewed_plan_sha256,
    )
    activate_release(attempt)
    return release


@transaction.atomic
def rollback_legacy_adoption(baseline):
    _verify_baseline(baseline)
    active = ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    _require(
        active.state == ActiveDataRelease.State.ACTIVE
        and active.release_id == baseline.document["release_id"]
        and active.manifest_sha256 == baseline.manifest_sha256,
        "Rollback requires the exact adopted baseline.",
    )
    release = DataRelease.objects.select_for_update().get(pk=active.release_id)
    fingerprints = compute_serving_fingerprints(release)
    _require(
        fingerprints.domain == baseline.document["domain_fingerprint"]
        and fingerprints.capabilities
        == baseline.document["capability_fingerprint"],
        "Adopted serving fingerprints changed.",
    )
    expected = {
        (member["runid"], member["capability"]["capability_type"])
        for member in baseline.document["members"]
        if member["capability"]
    }
    capabilities = RunCapability.objects.filter(run_state__release=release)
    observed = set(capabilities.values_list("run_state__runid", "capability_type"))
    _require(observed == expected, "Capability bootstrap rows differ from the baseline.")
    capabilities.delete()
    active.state = ActiveDataRelease.State.EMPTY
    active.release = None
    active.manifest_sha256 = None
    active.data_contract = None
    active.activated_at = None
    active._allow_activation_change = True
    active.save()
    release.status = DataRelease.Status.VALIDATED
    release._allow_lifecycle_change = True
    release.save(update_fields=("status",))
    attempt = release.attempts.filter(
        status=DataReleaseAttempt.Status.SUCCEEDED
    ).order_by("-completed_at").first()
    _require(attempt is not None, "Adoption attempt is absent.")
    transition_attempt(attempt, DataReleaseAttempt.Status.ROLLED_BACK)
    return release
