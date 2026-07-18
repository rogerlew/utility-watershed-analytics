import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import pyarrow.parquet as parquet
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import transaction

from server.watershed.domain_mutations import (
    EmptyBaseApplyResult,
    apply_staged_empty_base,
)
from server.watershed.loaders.writers import (
    CHANNEL_MAPPING,
    HILLSLOPES_FIELD_MAP,
    LANDUSE_FIELD_MAP,
    SOILS_FIELD_MAP,
    SUBCATCHMENT_MAPPING,
    WATERSHED_FIELD_SOURCES,
    _extract_geometry,
    _get_feature_field,
)
from server.watershed.models import (
    DataArtifactLineage,
    DataReleaseAttempt,
    DataRunState,
)
from server.watershed.release_ledger import (
    activate_release,
    transition_attempt,
)
from server.watershed.staging import (
    LoadResult,
    SpaceBudget,
    heartbeat_staging,
    load_staging_model_rows,
    mark_staging_ready,
    open_staging,
)
from server.watershed.staging_models import (
    StagedChannel,
    StagedRunCapability,
    StagedSubcatchment,
    StagedWatershed,
)


class MaterializationError(RuntimeError):
    pass


class LockedArtifactError(MaterializationError):
    pass


CORE_ARTIFACT_MEDIA_TYPES = MappingProxyType(
    {
        "metadata": "application/json",
        "boundary": "application/geo+json",
        "subcatchments": "application/geo+json",
        "channels": "application/geo+json",
        "hillslopes": "application/vnd.apache.parquet",
        "soils": "application/vnd.apache.parquet",
        "landuse": "application/vnd.apache.parquet",
    }
)
PARQUET_FIELD_MAPS = MappingProxyType(
    {
        "hillslopes": HILLSLOPES_FIELD_MAP,
        "soils": SOILS_FIELD_MAP,
        "landuse": LANDUSE_FIELD_MAP,
    }
)
MAX_METADATA_BYTES = 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class CapabilityDeclaration:
    capability_type: str
    mode: str
    durable_base_uri: str
    index_role: str
    runtime_configuration: Mapping[str, Any]


@dataclass(frozen=True)
class MaterializationMember:
    run_state: DataRunState
    artifact_paths: Mapping[str, Path]
    capability: CapabilityDeclaration | None = None


@dataclass(frozen=True)
class VerifiedArtifact:
    lineage: DataArtifactLineage
    path: Path
    stat_signature: tuple[int, int, int, int]

    def assert_unchanged(self):
        current = self.path.stat(follow_symlinks=False)
        signature = (
            current.st_dev,
            current.st_ino,
            current.st_size,
            current.st_mtime_ns,
        )
        if signature != self.stat_signature or self.path.is_symlink():
            raise LockedArtifactError(f"Locked artifact changed while reading: {self.lineage.role}")


@dataclass(frozen=True)
class EmptyBuildResult:
    staging: LoadResult
    applied: EmptyBaseApplyResult


def _stat_signature(stat_result):
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def verify_locked_artifact(lineage, path, *, expected_media_type=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise LockedArtifactError(f"Locked artifact is not an ordinary file: {lineage.role}")
    if expected_media_type and lineage.media_type != expected_media_type:
        raise LockedArtifactError(f"Locked artifact media type differs: {lineage.role}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        stat_result = os.fstat(descriptor)
        if stat_result.st_size != lineage.byte_size:
            raise LockedArtifactError(f"Locked artifact byte size differs: {lineage.role}")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, HASH_CHUNK_BYTES):
            digest.update(chunk)
    finally:
        os.close(descriptor)
    if digest.hexdigest() != lineage.sha256:
        raise LockedArtifactError(f"Locked artifact checksum differs: {lineage.role}")
    return VerifiedArtifact(lineage, path, _stat_signature(stat_result))


def _read_metadata(artifact, run_state):
    if artifact.lineage.byte_size > MAX_METADATA_BYTES:
        raise MaterializationError("Metadata artifact exceeds the bounded limit.")
    try:
        with artifact.path.open("rb") as stream:
            document = json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MaterializationError("Metadata artifact is not valid JSON.") from error
    required = {
        "schema_version",
        "collection_key",
        "source_revision",
        "watershed_key",
        "runid",
        "display_name",
        "aliases",
        "source_properties",
    }
    if not isinstance(document, dict) or set(document) != required:
        raise MaterializationError("Metadata artifact has missing or unexpected fields.")
    identity = run_state.watershed_identity
    if (
        document["schema_version"] != 1
        or document["collection_key"] != run_state.collection_id
        or document["watershed_key"] != identity.watershed_key
        or document["runid"] != run_state.runid
        or not isinstance(document["source_properties"], dict)
        or not isinstance(document["aliases"], list)
        or set(document["aliases"])
        != set(
            run_state.watershed_identity.run_aliases.exclude(
                runid=run_state.runid
            ).values_list("runid", flat=True)
        )
    ):
        raise MaterializationError("Metadata identity differs from the release ledger.")
    metadata = {}
    properties = document["source_properties"]
    for model_field, source_fields in WATERSHED_FIELD_SOURCES.items():
        if model_field in {"runid", "geom"}:
            continue
        value = next(
            (properties[field] for field in source_fields if properties.get(field) is not None),
            None,
        )
        if value is not None:
            metadata[model_field] = value
    metadata.setdefault("srcname", document["display_name"])
    artifact.assert_unchanged()
    return metadata


def _open_single_layer(artifact):
    try:
        source = DataSource(str(artifact.path))
    except Exception as error:
        raise MaterializationError(f"GeoJSON artifact cannot be opened: {artifact.lineage.role}") from error
    if len(source) != 1:
        raise MaterializationError(f"GeoJSON artifact must contain one layer: {artifact.lineage.role}")
    return source, source[0]


def _normalized_geometry(feature, role):
    try:
        geometry = _extract_geometry(feature)
    except Exception as error:
        raise MaterializationError(f"{role} geometry cannot be normalized.") from error
    if isinstance(geometry, Polygon):
        geometry = MultiPolygon(geometry)
    if not isinstance(geometry, MultiPolygon) or geometry.empty or not geometry.valid:
        raise MaterializationError(f"{role} geometry must be a valid non-empty multipolygon.")
    geometry.srid = 4326
    return geometry


def _watershed_record(member, metadata, artifact):
    source, layer = _open_single_layer(artifact)
    features = iter(layer)
    try:
        feature = next(features)
    except StopIteration as error:
        raise MaterializationError("Boundary artifact is empty.") from error
    geometry = _normalized_geometry(feature, "boundary")
    try:
        next(features)
    except StopIteration:
        pass
    else:
        raise MaterializationError("Boundary artifact must contain exactly one feature.")
    artifact.assert_unchanged()
    del source
    return {
        "run_state": member.run_state,
        "watershed_identity": member.run_state.watershed_identity,
        "source_fingerprint": member.run_state.run_fingerprint,
        "runid": member.run_state.runid,
        "geom": geometry,
        "metadata": metadata,
    }


def _integer_feature_field(feature, field_name, role):
    value = _get_feature_field(feature, field_name)
    if isinstance(value, bool):
        raise MaterializationError(f"{role} {field_name} must be an integer.")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise MaterializationError(f"{role} {field_name} must be an integer.") from error
    if isinstance(value, float) and not value.is_integer():
        raise MaterializationError(f"{role} {field_name} must be an integer.")
    return result


def _child_records(member, artifact, *, model):
    source, layer = _open_single_layer(artifact)
    role = artifact.lineage.role
    mapping = SUBCATCHMENT_MAPPING if model is StagedSubcatchment else CHANNEL_MAPPING
    for feature in layer:
        values = {
            target: _integer_feature_field(feature, source_field, role)
            for target, source_field in mapping.items()
        }
        yield {
            "run_state": member.run_state,
            "watershed_identity": member.run_state.watershed_identity,
            "source_fingerprint": (
                member.run_state.subcatchment_fingerprint
                if model is StagedSubcatchment
                else member.run_state.channel_fingerprint
            ),
            **values,
            "geom": _normalized_geometry(feature, role),
            "attributes": {},
        }
    artifact.assert_unchanged()
    del source


def _json_value(value, converter, role, field):
    if value is None:
        return None
    try:
        converted = converter(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise MaterializationError(f"{role} field {field} has an invalid value.") from error
    if isinstance(converted, float) and not math.isfinite(converted):
        raise MaterializationError(f"{role} field {field} must be finite.")
    return converted


def _apply_parquet_attributes(
    attempt,
    member,
    artifact,
    *,
    field_map,
    batch_size,
    lease_extension,
):
    role = artifact.lineage.role
    try:
        parquet_file = parquet.ParquetFile(artifact.path)
    except Exception as error:
        raise MaterializationError(f"{role} artifact is not valid Parquet.") from error
    names = set(parquet_file.schema_arrow.names)
    topaz_candidates = (
        "TopazID",
        "topaz_id",
        "topazid",
        "TOPAZID",
        "Topaz_ID",
        "topaz_ID",
    )
    topaz_field = next((name for name in topaz_candidates if name in names), None)
    if topaz_field is None:
        raise MaterializationError(f"{role} artifact lacks a Topaz join field.")
    selected_fields = [
        source_field for _, source_field, _ in field_map if source_field in names
    ]
    previous_topazid = None
    row_count = 0
    maximum_batch = 0
    for record_batch in parquet_file.iter_batches(
        batch_size=batch_size,
        columns=[topaz_field, *selected_fields],
    ):
        records = record_batch.to_pylist()
        maximum_batch = max(maximum_batch, len(records))
        values_by_topazid = {}
        for record in records:
            topazid = _json_value(record[topaz_field], int, role, topaz_field)
            if topazid is None or (
                previous_topazid is not None and topazid <= previous_topazid
            ):
                raise MaterializationError(
                    f"{role} Topaz identities must be non-null and strictly increasing."
                )
            previous_topazid = topazid
            values_by_topazid[topazid] = {
                model_field: converted
                for model_field, source_field, converter in field_map
                if source_field in record
                and (converted := _json_value(
                    record[source_field], converter, role, source_field
                ))
                is not None
            }
        heartbeat_staging(attempt.pk, attempt.lease_owner, lease_extension)
        with transaction.atomic():
            staged_rows = list(
                StagedSubcatchment.objects.select_for_update().filter(
                    attempt=attempt,
                    run_state=member.run_state,
                    topazid__in=values_by_topazid,
                )
            )
            if len(staged_rows) != len(values_by_topazid):
                raise MaterializationError(f"{role} Topaz join differs from staged geometry.")
            for staged in staged_rows:
                staged.attributes = {
                    **staged.attributes,
                    **values_by_topazid[staged.topazid],
                }
                staged.full_clean(validate_unique=False, validate_constraints=False)
            StagedSubcatchment.objects.bulk_update(
                staged_rows,
                ("attributes",),
                batch_size=batch_size,
            )
        row_count += len(records)
    if row_count != member.run_state.actual_subcatchments:
        raise MaterializationError(f"{role} row count differs from the release ledger.")
    artifact.assert_unchanged()
    return maximum_batch


def _capability_record(member, declaration, artifact):
    run_state = member.run_state
    if run_state.capability_fingerprint is None:
        raise MaterializationError("An undeclared run cannot stage a capability.")
    configuration = dict(declaration.runtime_configuration)
    if (
        configuration.get("index_uri") != artifact.lineage.uri
        or configuration.get("index_sha256") != artifact.lineage.sha256
    ):
        raise MaterializationError("Capability configuration differs from its locked index.")
    return {
        "run_state": run_state,
        "watershed_identity": run_state.watershed_identity,
        "source_fingerprint": run_state.capability_fingerprint,
        "capability_type": declaration.capability_type,
        "mode": declaration.mode,
        "durable_base_uri": declaration.durable_base_uri,
        "index_uri": artifact.lineage.uri,
        "index_sha256": artifact.lineage.sha256,
        "capability_fingerprint": run_state.capability_fingerprint,
        "runtime_configuration": configuration,
    }


def _verify_member(member):
    run_state = member.run_state
    if run_state.validation_status != DataRunState.ValidationStatus.VALIDATED:
        raise MaterializationError("Only validated run states may be materialized.")
    lineages = {
        lineage.role: lineage
        for lineage in DataArtifactLineage.objects.filter(run_state=run_state)
    }
    required_roles = set(CORE_ARTIFACT_MEDIA_TYPES)
    if member.capability is not None:
        required_roles.add(member.capability.index_role)
    if set(member.artifact_paths) != required_roles:
        raise MaterializationError("Materialization paths differ from required artifact roles.")
    if not required_roles.issubset(lineages):
        raise MaterializationError("Required artifact lineage is absent.")
    if (run_state.capability_fingerprint is None) != (member.capability is None):
        raise MaterializationError("Capability declaration differs from the run ledger.")
    verified = {}
    for role in sorted(required_roles):
        expected_media_type = CORE_ARTIFACT_MEDIA_TYPES.get(role, "application/json")
        verified[role] = verify_locked_artifact(
            lineages[role],
            member.artifact_paths[role],
            expected_media_type=expected_media_type,
        )
    return verified


def _fail_attempt(attempt, phase, error):
    attempt.refresh_from_db()
    if attempt.status in {
        DataReleaseAttempt.Status.PLANNING,
        DataReleaseAttempt.Status.STAGING,
        DataReleaseAttempt.Status.APPLYING,
    }:
        transition_attempt(
            attempt,
            DataReleaseAttempt.Status.FAILED,
            failure_phase=phase,
            failure_summary=str(error) or type(error).__name__,
        )


def stage_locked_release(
    attempt,
    members,
    *,
    budget,
    observed_available_bytes,
    batch_size=1000,
    lease_extension=timedelta(minutes=30),
):
    if batch_size < 1:
        raise ValueError("Batch size must be positive.")
    try:
        attempt = DataReleaseAttempt.objects.select_related("release").get(pk=attempt.pk)
        if attempt.status != DataReleaseAttempt.Status.STAGING:
            raise MaterializationError("Materialization requires a staging attempt.")
        members = sorted(members, key=lambda member: member.run_state.runid)
        run_state_ids = {member.run_state.pk for member in members}
        expected_run_state_ids = set(
            attempt.release.run_states.values_list("pk", flat=True)
        )
        if run_state_ids != expected_run_state_ids or len(members) != len(run_state_ids):
            raise MaterializationError("Materialization membership differs from the release ledger.")
        if any(member.run_state.release_id != attempt.release_id for member in members):
            raise MaterializationError("Materialization member belongs to another release.")

        verified_members = [(member, _verify_member(member)) for member in members]
        locked_bytes = sum(
            artifact.lineage.byte_size
            for _, artifacts in verified_members
            for artifact in artifacts.values()
        )
        if budget.artifact_bytes != locked_bytes:
            raise MaterializationError("Space budget artifact bytes differ from locked inputs.")
        open_staging(
            attempt,
            budget=budget,
            observed_available_bytes=observed_available_bytes,
        )

        totals = {
            "watershed_rows": 0,
            "subcatchment_rows": 0,
            "channel_rows": 0,
            "capability_rows": 0,
        }
        maximum_batch = 0
        for member, artifacts in verified_members:
            metadata = _read_metadata(artifacts["metadata"], member.run_state)
            loaded, observed = load_staging_model_rows(
                attempt,
                model=StagedWatershed,
                records=[_watershed_record(member, metadata, artifacts["boundary"])],
                batch_size=batch_size,
                lease_extension=lease_extension,
            )
            totals["watershed_rows"] += loaded
            maximum_batch = max(maximum_batch, observed)

            for model, role, counter in (
                (StagedSubcatchment, "subcatchments", "subcatchment_rows"),
                (StagedChannel, "channels", "channel_rows"),
            ):
                loaded, observed = load_staging_model_rows(
                    attempt,
                    model=model,
                    records=_child_records(member, artifacts[role], model=model),
                    batch_size=batch_size,
                    lease_extension=lease_extension,
                )
                expected = (
                    member.run_state.actual_subcatchments
                    if model is StagedSubcatchment
                    else member.run_state.actual_channels
                )
                if loaded != expected:
                    raise MaterializationError(f"{role} count differs from the release ledger.")
                totals[counter] += loaded
                maximum_batch = max(maximum_batch, observed)

            for role, field_map in PARQUET_FIELD_MAPS.items():
                observed = _apply_parquet_attributes(
                    attempt,
                    member,
                    artifacts[role],
                    field_map=field_map,
                    batch_size=batch_size,
                    lease_extension=lease_extension,
                )
                maximum_batch = max(maximum_batch, observed)

            if member.capability is not None:
                capability_artifact = artifacts[member.capability.index_role]
                loaded, observed = load_staging_model_rows(
                    attempt,
                    model=StagedRunCapability,
                    records=[
                        _capability_record(
                            member,
                            member.capability,
                            capability_artifact,
                        )
                    ],
                    batch_size=batch_size,
                    lease_extension=lease_extension,
                )
                capability_artifact.assert_unchanged()
                totals["capability_rows"] += loaded
                maximum_batch = max(maximum_batch, observed)

        expected_totals = {
            "watershed_rows": attempt.release.actual_watersheds,
            "subcatchment_rows": attempt.release.actual_subcatchments,
            "channel_rows": attempt.release.actual_channels,
            "capability_rows": attempt.release.run_states.filter(
                capability_fingerprint__isnull=False
            ).count(),
        }
        if totals != expected_totals:
            raise MaterializationError("Staged release totals differ from the ledger.")
        mark_staging_ready(attempt)
        return LoadResult(maximum_batch_rows=maximum_batch, **totals)
    except Exception as error:
        _fail_attempt(attempt, "materialize", error)
        if isinstance(error, MaterializationError):
            raise
        raise MaterializationError(str(error) or type(error).__name__) from error


def build_and_activate_empty_release(
    attempt,
    members,
    *,
    budget: SpaceBudget,
    observed_available_bytes,
    actual_plan_sha256,
    batch_size=1000,
):
    staging_result = stage_locked_release(
        attempt,
        members,
        budget=budget,
        observed_available_bytes=observed_available_bytes,
        batch_size=batch_size,
    )
    attempt = transition_attempt(
        attempt,
        DataReleaseAttempt.Status.APPLYING,
        actual_plan_sha256=actual_plan_sha256,
    )
    try:
        with transaction.atomic():
            applied_result = apply_staged_empty_base(attempt, batch_size=batch_size)
            activate_release(attempt)
    except Exception as error:
        _fail_attempt(attempt, "empty-apply", error)
        if isinstance(error, MaterializationError):
            raise
        raise MaterializationError(str(error) or type(error).__name__) from error
    return EmptyBuildResult(staging=staging_result, applied=applied_result)
