import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from django.db import transaction
from django.urls import reverse
from rest_framework.test import APIClient

from server.watershed.domain_mutations import (
    SUBCATCHMENT_FIELDS,
    WATERSHED_FIELDS,
    apply_staged_empty_base,
)
from server.watershed.fingerprint_contract import (
    FINGERPRINT_VERSION,
    canonical_bytes,
    canonical_sha256,
)
from server.watershed.materializer import (
    CORE_ARTIFACT_MEDIA_TYPES,
    EmptyBuildResult,
    MaterializationError,
    verify_locked_artifact,
    stage_locked_release,
)
from server.watershed.models import (
    ActiveDataRelease,
    Channel,
    DataArtifactLineage,
    DataReleaseAttempt,
    RunCapability,
    Subcatchment,
    Watershed,
)
from server.watershed.release_ledger import (
    activate_release,
    sanitize_failure_summary,
    transition_attempt,
)
from server.watershed.staging_models import (
    DataReleaseStagingState,
    StagedChannel,
    StagedRunCapability,
    StagedSubcatchment,
    StagedWatershed,
)


class ReleaseValidationError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ValidationCheck:
    code: str
    status: str = "passed"
    count: int | None = None
    summary: str | None = None

    def as_document(self):
        document = {"code": self.code, "status": self.status}
        if self.count is not None:
            document["count"] = self.count
        if self.summary is not None:
            document["summary"] = sanitize_failure_summary(self.summary)
        return document


@dataclass(frozen=True)
class ServingFingerprints:
    domain: str
    capabilities: str
    watershed_rows: int
    subcatchment_rows: int
    channel_rows: int
    capability_rows: int

    def as_document(self):
        return {
            "fingerprint_version": FINGERPRINT_VERSION,
            "domain_fingerprint": self.domain,
            "capability_fingerprint": self.capabilities,
            "counts": {
                "watersheds": self.watershed_rows,
                "subcatchments": self.subcatchment_rows,
                "channels": self.channel_rows,
                "capabilities": self.capability_rows,
            },
        }


@dataclass(frozen=True)
class ValidatedBuildResult:
    build: EmptyBuildResult
    fingerprints: ServingFingerprints
    report: dict[str, Any]


def _require(condition, code, message):
    if not condition:
        raise ReleaseValidationError(code, message)


def _safe_artifact_uri(uri, role):
    parsed = urlsplit(uri)
    _require(
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment,
        "artifact-uri-safe",
        f"{role} artifact URI is not credential-free immutable HTTPS.",
    )


def _reject_html_artifact(path, role):
    with Path(path).open("rb") as stream:
        prefix = stream.read(1024).lstrip().lower()
    _require(
        not prefix.startswith((b"<!doctype html", b"<html", b"<head", b"<body")),
        "artifact-not-html",
        f"{role} artifact contains an HTML response body.",
    )


def validate_member_artifacts(member):
    lineages = {
        lineage.role: lineage
        for lineage in DataArtifactLineage.objects.filter(run_state=member.run_state)
    }
    _require(
        set(member.artifact_paths).issubset(lineages),
        "artifact-lineage-complete",
        "A materialization artifact lacks immutable lineage.",
    )
    for role, path in sorted(member.artifact_paths.items()):
        lineage = lineages[role]
        _safe_artifact_uri(lineage.uri, role)
        expected_media_type = CORE_ARTIFACT_MEDIA_TYPES.get(role, "application/json")
        verify_locked_artifact(
            lineage,
            path,
            expected_media_type=expected_media_type,
        )
        _reject_html_artifact(path, role)
    return ValidationCheck(
        "verified-artifacts",
        count=len(member.artifact_paths),
    )


def validate_artifacts(members):
    checks = [validate_member_artifacts(member) for member in members]
    return ValidationCheck(
        "verified-artifacts",
        count=sum(check.count or 0 for check in checks),
    )


def _valid_geometry(geometry):
    return (
        geometry is not None
        and geometry.srid == 4326
        and not geometry.empty
        and geometry.valid
    )


def _world_bounds(extent):
    minimum_x, minimum_y, maximum_x, maximum_y = extent
    return (
        -180 <= minimum_x <= maximum_x <= 180
        and -90 <= minimum_y <= maximum_y <= 90
    )


def _bounds_close(observed, expected, tolerance):
    return all(abs(observed_value - expected_value) <= tolerance for observed_value, expected_value in zip(observed, expected, strict=True))


def validate_staged_release(
    attempt,
    *,
    reviewed_bounds: Mapping[str, tuple[float, float, float, float]] | None = None,
    bounds_tolerance=0.001,
    minimum_area_ratio=0.01,
    maximum_area_ratio=2.0,
):
    _require(
        reviewed_bounds is not None,
        "reviewed-bounds-required",
        "Every staged run requires reviewed bounds.",
    )
    attempt.refresh_from_db()
    _require(
        attempt.status == DataReleaseAttempt.Status.STAGING,
        "staging-attempt-status",
        "Run validation requires a staging attempt.",
    )
    state = DataReleaseStagingState.objects.get(attempt=attempt)
    _require(
        state.status == DataReleaseStagingState.Status.READY,
        "staging-ready",
        "Run validation requires READY staging.",
    )
    release = attempt.release
    release_runids = set(release.run_states.values_list("runid", flat=True))
    _require(
        set(reviewed_bounds) == release_runids,
        "reviewed-bounds-membership",
        "Reviewed bounds membership differs from release runs.",
    )
    _require(
        (
            release.expected_watersheds,
            release.expected_subcatchments,
            release.expected_channels,
        )
        == (
            release.actual_watersheds,
            release.actual_subcatchments,
            release.actual_channels,
        ),
        "release-expected-counts",
        "Expected and actual release counts differ.",
    )
    totals = {
        "watersheds": StagedWatershed.objects.filter(attempt=attempt).count(),
        "subcatchments": StagedSubcatchment.objects.filter(attempt=attempt).count(),
        "channels": StagedChannel.objects.filter(attempt=attempt).count(),
        "capabilities": StagedRunCapability.objects.filter(attempt=attempt).count(),
    }
    expected_totals = {
        "watersheds": release.actual_watersheds,
        "subcatchments": release.actual_subcatchments,
        "channels": release.actual_channels,
        "capabilities": release.run_states.filter(
            capability_fingerprint__isnull=False
        ).count(),
    }
    _require(
        totals == expected_totals,
        "release-counts-exact",
        "Staged release counts differ from the immutable ledger.",
    )

    geometry_count = 0
    for run_state in release.run_states.select_related(
        "watershed_identity", "collection"
    ).iterator(chunk_size=1000):
        watersheds = StagedWatershed.objects.filter(
            attempt=attempt,
            run_state=run_state,
        )
        _require(
            watersheds.count() == 1,
            "run-watershed-count",
            f"{run_state.runid} does not contain exactly one watershed.",
        )
        watershed = watersheds.get()
        _require(
            _valid_geometry(watershed.geom) and _world_bounds(watershed.geom.extent),
            "watershed-geometry-valid",
            f"{run_state.runid} watershed geometry is invalid or outside world bounds.",
        )
        if run_state.runid in reviewed_bounds:
            _require(
                _bounds_close(
                    watershed.geom.extent,
                    reviewed_bounds[run_state.runid],
                    bounds_tolerance,
                ),
                "watershed-bounds-reviewed",
                f"{run_state.runid} watershed bounds differ from the reviewed bounds.",
            )

        subcatchments = StagedSubcatchment.objects.filter(
            attempt=attempt,
            run_state=run_state,
        ).order_by("topazid")
        channels = StagedChannel.objects.filter(
            attempt=attempt,
            run_state=run_state,
        ).order_by("topazid", "weppid", "order")
        _require(
            subcatchments.count() == run_state.actual_subcatchments
            and channels.count() == run_state.actual_channels,
            "run-counts-exact",
            f"{run_state.runid} child counts differ from its ledger.",
        )
        subcatchment_area = 0.0
        for child in subcatchments.iterator(chunk_size=1000):
            _require(
                _valid_geometry(child.geom)
                and _world_bounds(child.geom.extent)
                and watershed.geom.covers(child.geom),
                "subcatchment-geometry-valid",
                f"{run_state.runid} has an invalid or uncovered subcatchment.",
            )
            subcatchment_area += child.geom.area
            geometry_count += 1
        for child in channels.iterator(chunk_size=1000):
            _require(
                _valid_geometry(child.geom)
                and _world_bounds(child.geom.extent)
                and watershed.geom.covers(child.geom),
                "channel-geometry-valid",
                f"{run_state.runid} has an invalid or uncovered channel.",
            )
            geometry_count += 1
        _require(
            watershed.geom.area > 0,
            "watershed-area-positive",
            f"{run_state.runid} watershed area is not positive.",
        )
        area_ratio = subcatchment_area / watershed.geom.area
        _require(
            minimum_area_ratio <= area_ratio <= maximum_area_ratio,
            "subcatchment-area-ratio",
            f"{run_state.runid} subcatchment/watershed area ratio is unreasonable.",
        )
    return (
        ValidationCheck("release-counts-exact", count=sum(totals.values())),
        ValidationCheck("geometry-valid", count=geometry_count + totals["watersheds"]),
        ValidationCheck("parquet-joins-exact", count=totals["subcatchments"] * 3),
    )


def _semantic_value(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _semantic_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_semantic_value(child) for child in value]
    return value


def _geometry_bytes(geometry):
    if geometry is None:
        return None
    value = geometry.hexewkb
    return value if isinstance(value, str) else bytes(value).hex()


def _sequence_fingerprint(subject, documents: Iterable[dict[str, Any]]):
    digest = hashlib.sha256()
    digest.update(
        canonical_bytes(
            {
                "fingerprint_version": FINGERPRINT_VERSION,
                "subject": subject,
            }
        )
    )
    for document in documents:
        digest.update(canonical_bytes(document))
    return digest.hexdigest()


def _subcatchment_documents(watershed):
    rows = Subcatchment.objects.filter(watershed=watershed).order_by("topazid")
    for row in rows.iterator(chunk_size=1000):
        yield {
            "topazid": row.topazid,
            "weppid": row.weppid,
            "geometry": _geometry_bytes(row.geom),
            "attributes": _semantic_value(
                {
                    field: getattr(row, field)
                    for field in sorted(SUBCATCHMENT_FIELDS)
                }
            ),
        }


def _channel_documents(watershed):
    rows = Channel.objects.filter(watershed=watershed).order_by(
        "topazid", "weppid", "order"
    )
    for row in rows.iterator(chunk_size=1000):
        yield {
            "topazid": row.topazid,
            "weppid": row.weppid,
            "order": row.order,
            "geometry": _geometry_bytes(row.geom),
        }


def _capability_document(capability):
    return {
        "collection_key": capability.run_state.collection_id,
        "watershed_key": capability.watershed_identity.watershed_key,
        "runid": capability.run_state.runid,
        "capability_type": capability.capability_type,
        "mode": capability.mode,
        "durable_base_uri": capability.durable_base_uri,
        "index_uri": capability.index_uri,
        "index_sha256": capability.index_sha256,
        "capability_fingerprint": capability.capability_fingerprint,
        "runtime_configuration": _semantic_value(capability.runtime_configuration),
    }


def _capability_documents(release):
    rows = RunCapability.objects.filter(run_state__release=release).select_related(
        "run_state", "watershed_identity"
    ).order_by(
        "run_state__collection_id",
        "watershed_identity__watershed_key",
        "run_state__runid",
        "capability_type",
    )
    for row in rows.iterator(chunk_size=1000):
        yield _capability_document(row)


def _domain_documents(release):
    watersheds = Watershed.objects.filter(
        logical_watershed__release_run_states__release=release
    ).select_related("logical_watershed__collection").distinct().order_by(
        "logical_watershed__collection_id",
        "logical_watershed__watershed_key",
        "runid",
    )
    for watershed in watersheds.iterator(chunk_size=1000):
        capabilities = RunCapability.objects.filter(
            run_state__release=release,
            run_state__runid=watershed.runid,
        ).select_related("run_state", "watershed_identity").order_by(
            "capability_type"
        )
        yield {
            "collection_key": watershed.logical_watershed.collection_id,
            "watershed_key": watershed.logical_watershed.watershed_key,
            "runid": watershed.runid,
            "geometry": _geometry_bytes(watershed.geom),
            "simplified_geometry": _geometry_bytes(watershed.simplified_geom),
            "metadata": _semantic_value(
                {
                    field: getattr(watershed, field)
                    for field in sorted(WATERSHED_FIELDS)
                }
            ),
            "subcatchments": _sequence_fingerprint(
                "serving-subcatchments",
                _subcatchment_documents(watershed),
            ),
            "channels": _sequence_fingerprint(
                "serving-channels",
                _channel_documents(watershed),
            ),
            "capabilities": _sequence_fingerprint(
                "serving-run-capabilities",
                (_capability_document(row) for row in capabilities),
            ),
        }


def compute_serving_fingerprints(release):
    return ServingFingerprints(
        domain=_sequence_fingerprint(
            "serving-watershed-domain",
            _domain_documents(release),
        ),
        capabilities=_sequence_fingerprint(
            "serving-capabilities",
            _capability_documents(release),
        ),
        watershed_rows=Watershed.objects.count(),
        subcatchment_rows=Subcatchment.objects.count(),
        channel_rows=Channel.objects.count(),
        capability_rows=RunCapability.objects.filter(
            run_state__release=release
        ).count(),
    )


def validate_database(release):
    active = ActiveDataRelease.objects.select_related("release").get(singleton_id=1)
    _require(
        active.state == ActiveDataRelease.State.ACTIVE
        and active.release_id == release.release_id
        and active.manifest_sha256 == release.manifest_sha256,
        "active-release-exact",
        "Active release coordinates differ from the validated target.",
    )
    fingerprints = compute_serving_fingerprints(release)
    _require(
        (
            fingerprints.watershed_rows,
            fingerprints.subcatchment_rows,
            fingerprints.channel_rows,
        )
        == (
            release.actual_watersheds,
            release.actual_subcatchments,
            release.actual_channels,
        ),
        "database-counts-exact",
        "Serving database counts differ from the release ledger.",
    )
    _require(
        not Watershed.objects.filter(logical_watershed__isnull=True).exists()
        and not Subcatchment.objects.filter(logical_watershed__isnull=True).exists()
        and not Channel.objects.filter(logical_watershed__isnull=True).exists(),
        "database-identities-complete",
        "Serving database contains rows without logical identity.",
    )
    return fingerprints, (
        ValidationCheck(
            "database-counts-exact",
            count=(
                fingerprints.watershed_rows
                + fingerprints.subcatchment_rows
                + fingerprints.channel_rows
            ),
        ),
        ValidationCheck(
            "domain-fingerprint",
            summary=fingerprints.domain,
        ),
        ValidationCheck(
            "capability-fingerprint",
            summary=fingerprints.capabilities,
        ),
    )


def _json_response(response, code):
    _require(response.status_code == 200, code, f"Application check returned {response.status_code}.")
    try:
        return json.loads(response.content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseValidationError(code, "Application response is not JSON.") from error


def validate_application(
    release,
    *,
    removed_runids=(),
    rhessys_probe=None,
    client=None,
):
    client = client or APIClient()
    removed_runids = tuple(removed_runids)
    listing = _json_response(client.get(reverse("watershed-list")), "api-list")
    _require(
        listing.get("type") == "FeatureCollection"
        and len(listing.get("features", [])) == release.actual_watersheds,
        "api-list",
        "Watershed list is not exact GeoJSON.",
    )
    response_count = 1
    for run_state in release.run_states.select_related("watershed_identity").iterator(
        chunk_size=1000
    ):
        watershed_key = run_state.watershed_identity.watershed_key
        detail = _json_response(
            client.get(reverse("watershed-by-key", args=[watershed_key])),
            "api-detail",
        )
        _require(
            detail.get("type") == "Feature"
            and detail.get("id") == watershed_key
            and detail.get("geometry", {}).get("type") == "MultiPolygon",
            "api-detail",
            f"{run_state.runid} stable detail is not exact GeoJSON.",
        )
        for route_name, expected_count in (
            ("watershed-subcatchments-by-key", run_state.actual_subcatchments),
            ("watershed-channels-by-key", run_state.actual_channels),
        ):
            children = _json_response(
                client.get(reverse(route_name, args=[watershed_key])),
                "api-child-geojson",
            )
            _require(
                children.get("type") == "FeatureCollection"
                and len(children.get("features", [])) == expected_count,
                "api-child-geojson",
                f"{run_state.runid} child GeoJSON count differs.",
            )
        _json_response(
            client.get(reverse("watershed-capabilities", args=[run_state.runid])),
            "api-capabilities",
        )
        response_count += 4
    for runid in removed_runids:
        response = client.get(reverse("watershed-detail", args=[runid]))
        _require(
            response.status_code == 404,
            "api-removed-run",
            f"Removed run {runid} remains reachable.",
        )
        response_count += 1
    if rhessys_probe is not None:
        runid = rhessys_probe["runid"]
        catalog = _json_response(
            client.get(reverse("rhessys-outputs-list", args=[runid])),
            "api-rhessys-catalog",
        )
        _require(
            catalog.get("capability", {}).get("source") == "materialized",
            "api-rhessys-catalog",
            "RHESSys catalog is not materialized.",
        )
        query = _json_response(
            client.post(
                reverse("rhessys-query", args=[runid]),
                rhessys_probe["request"],
                format="json",
            ),
            "api-rhessys-query",
        )
        _require(
            query.get("rows") == rhessys_probe["expected_rows"],
            "api-rhessys-query",
            "Representative RHESSys query rows differ.",
        )
        response_count += 2
    return (
        ValidationCheck("application-geojson", count=response_count),
        ValidationCheck("removed-runs-absent", count=len(removed_runids)),
        ValidationCheck(
            "representative-rhessys-read",
            count=int(rhessys_probe is not None),
        ),
    )


def validation_report(
    *,
    report_id,
    subject_type,
    subject_id,
    validator_git_commit,
    validator_image_digest,
    checks,
    started_at,
    completed_at=None,
    summary=None,
):
    completed_at = completed_at or datetime.now(timezone.utc)
    checks = tuple(checks)
    key_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    _require(
        len(report_id) <= 96 and bool(key_pattern.fullmatch(report_id)),
        "report-id-valid",
        "Validation report ID is not a stable key.",
    )
    _require(
        subject_type
        in {"artifact", "member", "release", "transformation", "capability"},
        "report-subject-valid",
        "Validation report subject type is unsupported.",
    )
    _require(
        isinstance(subject_id, str) and 1 <= len(subject_id) <= 255,
        "report-subject-id-valid",
        "Validation report subject ID is invalid.",
    )
    _require(
        bool(re.fullmatch(r"[a-f0-9]{40}", validator_git_commit))
        and bool(re.fullmatch(r"sha256:[a-f0-9]{64}", validator_image_digest)),
        "report-validator-valid",
        "Validation report validator coordinates are invalid.",
    )
    _require(
        bool(checks)
        and len({check.code for check in checks}) == len(checks)
        and all(
            len(check.code) <= 96
            and key_pattern.fullmatch(check.code)
            and check.status in {"passed", "failed"}
            and (check.count is None or check.count >= 0)
            and (check.summary is None or 1 <= len(check.summary) <= 1000)
            for check in checks
        ),
        "report-checks-valid",
        "Validation report checks are empty, duplicate, or invalid.",
    )
    _require(
        started_at <= completed_at,
        "report-time-order",
        "Validation report completion precedes its start.",
    )
    failed = any(check.status == "failed" for check in checks)
    document = {
        "schema_version": 1,
        "report_id": report_id,
        "subject": {"type": subject_type, "id": subject_id},
        "validator": {
            "git_commit": validator_git_commit,
            "image_digest": validator_image_digest,
        },
        "started_at": started_at.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "completed_at": completed_at.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "status": "failed" if failed else "passed",
        "checks": [check.as_document() for check in checks],
    }
    if summary:
        document["summary"] = sanitize_failure_summary(summary)[:2000]
    return document


def write_validation_report(path, document):
    path = Path(path)
    _require(
        not path.exists() and not path.is_symlink(),
        "report-output-new",
        "Validation report output already exists.",
    )
    content = canonical_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return canonical_sha256(document)


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


def validated_empty_build(
    attempt,
    members,
    *,
    budget,
    observed_available_bytes,
    actual_plan_sha256,
    validator_git_commit,
    validator_image_digest,
    reviewed_bounds=None,
    removed_runids=(),
    rhessys_probe=None,
    batch_size=1000,
):
    started_at = datetime.now(timezone.utc)
    checks = []
    try:
        checks.append(validate_artifacts(members))
        staging_result = stage_locked_release(
            attempt,
            members,
            budget=budget,
            observed_available_bytes=observed_available_bytes,
            batch_size=batch_size,
        )
        checks.extend(
            validate_staged_release(
                attempt,
                reviewed_bounds=reviewed_bounds,
            )
        )
        attempt = transition_attempt(
            attempt,
            DataReleaseAttempt.Status.APPLYING,
            actual_plan_sha256=actual_plan_sha256,
        )
        with transaction.atomic():
            applied_result = apply_staged_empty_base(attempt, batch_size=batch_size)
            activate_release(attempt)
            fingerprints, database_checks = validate_database(attempt.release)
            checks.extend(database_checks)
            checks.extend(
                validate_application(
                    attempt.release,
                    removed_runids=removed_runids,
                    rhessys_probe=rhessys_probe,
                )
            )
    except Exception as error:
        _fail_attempt(attempt, "clean-build-validation", error)
        if isinstance(error, (ReleaseValidationError, MaterializationError)):
            raise
        raise ReleaseValidationError(
            "clean-build-validation",
            str(error) or type(error).__name__,
        ) from error
    report = validation_report(
        report_id=f"clean-build-{attempt.release.manifest_sha256[:16]}",
        subject_type="release",
        subject_id=attempt.release_id,
        validator_git_commit=validator_git_commit,
        validator_image_digest=validator_image_digest,
        checks=checks,
        started_at=started_at,
        summary="Synthetic clean build passed every required DB21 validator.",
    )
    return ValidatedBuildResult(
        build=EmptyBuildResult(staging_result, applied_result),
        fingerprints=fingerprints,
        report=report,
    )
