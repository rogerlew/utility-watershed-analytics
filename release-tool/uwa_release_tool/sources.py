from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote, urlparse

from . import enrichment
from .artifacts import ArtifactClient, PublishResult


SOURCE_ROLES = (
    "boundary",
    "subcatchments",
    "channels",
    "hillslopes",
    "soils",
    "landuse",
)
BATCH_TEMPLATE_ROLES = SOURCE_ROLES[1:]
GEOJSON_ROLES = {"boundary", "subcatchments", "channels"}
PARQUET_ROLES = {"hillslopes", "soils", "landuse"}
MEDIA_TYPES = {
    "metadata": "application/json",
    "boundary": "application/geo+json",
    "subcatchments": "application/geo+json",
    "channels": "application/geo+json",
    "hillslopes": "application/vnd.apache.parquet",
    "soils": "application/vnd.apache.parquet",
    "landuse": "application/vnd.apache.parquet",
}
KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CREATED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SECRET_KEY_PATTERN = re.compile(r"password|passwd|secret|token|credential|private.?key", re.I)
DEFAULT_CHUNK_SIZE = 1024 * 1024


class SourcePreparationError(RuntimeError):
    pass


class SourceDescriptorError(SourcePreparationError):
    pass


class SourceFetchError(SourcePreparationError):
    pass


class SourceIntegrityError(SourcePreparationError):
    pass


class SourceFormatError(SourcePreparationError):
    pass


class SourceMembershipError(SourcePreparationError):
    pass


@dataclass(frozen=True)
class SourceRequest:
    role: str
    runid: str | None
    url: str

    @property
    def key(self) -> tuple[str, str, str]:
        return self.role, self.runid or "", self.url


@dataclass(frozen=True)
class PreparedSources:
    index: dict[str, Any]
    receipt: dict[str, Any]
    index_bytes: bytes
    receipt_bytes: bytes
    index_artifact: PublishResult
    receipt_artifact: PublishResult
    source_count: int
    member_count: int
    replayed: bool


Fetcher = Callable[[str, Path, dict[str, str]], None]


def canonical_json(document: Any) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _require_exact_keys(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] = frozenset(),
    label: str,
) -> None:
    missing = required - value.keys()
    unexpected = value.keys() - required - optional
    if missing or unexpected:
        raise SourceDescriptorError(f"{label} has missing or unexpected fields")


def _require_string(value: Any, label: str, *, maximum: int = 255) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise SourceDescriptorError(f"{label} must be a non-empty bounded string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise SourceDescriptorError(f"{label} contains control characters")
    return value


def _safe_https_uri(value: Any, label: str) -> str:
    uri = _require_string(value, label, maximum=2048)
    parsed = urlparse(uri)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise SourceDescriptorError(f"{label} must be a credential-free HTTPS URI")
    return uri


def _member_descriptor(value: Any, *, standalone: bool) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceDescriptorError("each member must be an object")
    required = {"watershed_key", "runid", "display_name", "aliases"}
    if standalone:
        required.add("sources")
    _require_exact_keys(value, required=required, label="member")
    watershed_key = _require_string(value["watershed_key"], "watershed_key", maximum=96)
    if not KEY_PATTERN.fullmatch(watershed_key):
        raise SourceDescriptorError("watershed_key is not canonical")
    runid = _require_string(value["runid"], "runid")
    display_name = _require_string(value["display_name"], "display_name")
    aliases = value["aliases"]
    if not isinstance(aliases, list):
        raise SourceDescriptorError("aliases must be a string array")
    aliases = [_require_string(alias, "alias") for alias in aliases]
    if len(aliases) != len(set(aliases)) or runid in aliases:
        raise SourceDescriptorError("aliases must be unique and differ from runid")
    member = {
        "watershed_key": watershed_key,
        "runid": runid,
        "display_name": display_name,
        "aliases": aliases,
    }
    if standalone:
        sources = value["sources"]
        if not isinstance(sources, dict):
            raise SourceDescriptorError("standalone sources must be an object")
        _require_exact_keys(sources, required=set(SOURCE_ROLES), label="standalone sources")
        member["sources"] = {
            role: _safe_https_uri(sources[role], f"source {role}") for role in SOURCE_ROLES
        }
    return member


def _enrichment_descriptor(value: Any, collection_key: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceDescriptorError("enrichment must be an object")
    _require_exact_keys(
        value,
        required={
            "type",
            "source_url",
            "source_sha256",
            "source_bytes",
            "code_git_commit",
            "validator_image_digest",
        },
        label="enrichment",
    )
    if value["type"] != "nasa-202606-wws-code":
        raise SourceDescriptorError("enrichment type is unsupported")
    if collection_key != "nasa-roses" or any(
        not member["runid"].startswith(enrichment.TARGET_RUNID_PREFIX) for member in members
    ):
        raise SourceDescriptorError("NASA enrichment requires the NASA 202606 collection")
    source_sha256 = _require_string(value["source_sha256"], "source_sha256", maximum=64)
    if not re.fullmatch(r"[a-f0-9]{64}", source_sha256):
        raise SourceDescriptorError("enrichment source_sha256 is invalid")
    source_bytes = value["source_bytes"]
    if not isinstance(source_bytes, int) or isinstance(source_bytes, bool) or source_bytes <= 0:
        raise SourceDescriptorError("enrichment source_bytes must be positive")
    code_git_commit = _require_string(value["code_git_commit"], "code_git_commit", maximum=40)
    if not re.fullmatch(r"[a-f0-9]{40}", code_git_commit):
        raise SourceDescriptorError("enrichment code_git_commit is invalid")
    validator_image_digest = _require_string(
        value["validator_image_digest"],
        "validator_image_digest",
        maximum=71,
    )
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", validator_image_digest):
        raise SourceDescriptorError("enrichment validator_image_digest is invalid")
    return {
        "type": "nasa-202606-wws-code",
        "source_url": _safe_https_uri(value["source_url"], "enrichment source_url"),
        "source_sha256": source_sha256,
        "source_bytes": source_bytes,
        "code_git_commit": code_git_commit,
        "validator_image_digest": validator_image_digest,
    }


def validate_descriptor(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceDescriptorError("descriptor root must be an object")
    common = {
        "schema_version",
        "kind",
        "collection_key",
        "source_revision",
        "created_at",
        "members",
    }
    optional = {"authentication"}
    kind = value.get("kind")
    if kind == "batch":
        required = common | {"master_url", "source_templates"}
        optional.add("enrichment")
    elif kind == "standalone":
        required = common
    else:
        raise SourceDescriptorError("kind must be batch or standalone")
    _require_exact_keys(value, required=required, optional=optional, label="descriptor")
    if value["schema_version"] != 1:
        raise SourceDescriptorError("schema_version must be 1")
    collection_key = _require_string(value["collection_key"], "collection_key", maximum=96)
    if not KEY_PATTERN.fullmatch(collection_key):
        raise SourceDescriptorError("collection_key is not canonical")
    source_revision = _require_string(value["source_revision"], "source_revision")
    created_at = _require_string(value["created_at"], "created_at")
    if not CREATED_AT_PATTERN.fullmatch(created_at):
        raise SourceDescriptorError("created_at must be a whole-second UTC timestamp")
    raw_members = value["members"]
    if not isinstance(raw_members, list) or not raw_members:
        raise SourceDescriptorError("members must be a non-empty array")
    members = [_member_descriptor(member, standalone=kind == "standalone") for member in raw_members]
    runids = [member["runid"] for member in members]
    keys = [member["watershed_key"] for member in members]
    if len(runids) != len(set(runids)):
        raise SourceDescriptorError("member runids must be unique")
    if len(keys) != len(set(keys)):
        raise SourceDescriptorError("member watershed keys must be unique")
    if kind == "standalone" and len(members) != 1:
        raise SourceDescriptorError("standalone preparation requires exactly one member")

    descriptor = {
        "schema_version": 1,
        "kind": kind,
        "collection_key": collection_key,
        "source_revision": source_revision,
        "created_at": created_at,
        "members": members,
    }
    if kind == "batch":
        descriptor["master_url"] = _safe_https_uri(value["master_url"], "master_url")
        templates = value["source_templates"]
        if not isinstance(templates, dict):
            raise SourceDescriptorError("source_templates must be an object")
        _require_exact_keys(
            templates,
            required=set(BATCH_TEMPLATE_ROLES),
            label="source_templates",
        )
        normalized_templates = {}
        for role in BATCH_TEMPLATE_ROLES:
            template = _require_string(templates[role], f"source template {role}", maximum=2048)
            if template.count("{runid}") != 1:
                raise SourceDescriptorError("each source template must contain {runid} exactly once")
            normalized_templates[role] = template
        descriptor["source_templates"] = normalized_templates
        if "enrichment" in value:
            descriptor["enrichment"] = _enrichment_descriptor(
                value["enrichment"],
                collection_key,
                members,
            )
    if "authentication" in value:
        authentication = value["authentication"]
        if not isinstance(authentication, dict):
            raise SourceDescriptorError("authentication must be an object")
        _require_exact_keys(authentication, required={"secret_ref"}, label="authentication")
        secret_ref = _require_string(authentication["secret_ref"], "secret_ref", maximum=128)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", secret_ref):
            raise SourceDescriptorError("secret_ref is not an environment-style name")
        descriptor["authentication"] = {"secret_ref": secret_ref}
    return descriptor


def descriptor_digest(descriptor: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(descriptor))


def source_requests(descriptor: dict[str, Any]) -> list[SourceRequest]:
    requests = []
    if descriptor["kind"] == "batch":
        requests.append(SourceRequest("master", None, descriptor["master_url"]))
        if "enrichment" in descriptor:
            requests.append(
                SourceRequest("enrichment", None, descriptor["enrichment"]["source_url"])
            )
        for member in descriptor["members"]:
            escaped_runid = quote(member["runid"], safe=";-._~")
            for role in BATCH_TEMPLATE_ROLES:
                uri = descriptor["source_templates"][role].replace("{runid}", escaped_runid)
                requests.append(SourceRequest(role, member["runid"], _safe_https_uri(uri, role)))
    else:
        member = descriptor["members"][0]
        requests.extend(
            SourceRequest(role, member["runid"], member["sources"][role])
            for role in SOURCE_ROLES
        )
    return requests


def _stream_response(response: BinaryIO, destination: Path, *, chunk_size: int) -> None:
    declared_value = response.headers.get("Content-Length")  # type: ignore[attr-defined]
    declared = None
    if declared_value is not None:
        try:
            declared = int(declared_value)
        except ValueError as error:
            raise SourceIntegrityError("source declared an invalid content length") from error
        if declared < 0:
            raise SourceIntegrityError("source declared an invalid content length")
    byte_count = 0
    with destination.open("xb") as output:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            output.write(chunk)
            byte_count += len(chunk)
        output.flush()
        os.fsync(output.fileno())
    if declared is not None and byte_count != declared:
        destination.unlink(missing_ok=True)
        raise SourceIntegrityError("source transfer ended before its declared length")


def fetch_https(
    url: str,
    destination: Path,
    headers: dict[str, str],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> None:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status = getattr(response, "status", 200)
            if status < 200 or status >= 300:
                raise SourceFetchError("required source returned a non-success status")
            _stream_response(response, destination, chunk_size=chunk_size)
    except SourcePreparationError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        destination.unlink(missing_ok=True)
        raise SourceFetchError("required source could not be fetched") from error


def _reject_secret_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY_PATTERN.search(str(key)):
                raise SourceFormatError("source document contains a prohibited credential field")
            _reject_secret_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secret_keys(child)


def _coordinate_pairs(value: Any) -> Iterable[tuple[float, float]]:
    if not isinstance(value, list) or not value:
        raise SourceFormatError("GeoJSON coordinates must be non-empty arrays")
    if len(value) >= 2 and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
        longitude = float(value[0])
        latitude = float(value[1])
        if not math.isfinite(longitude) or not math.isfinite(latitude):
            raise SourceFormatError("GeoJSON coordinates must be finite")
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise SourceFormatError("GeoJSON coordinates are outside WGS84 bounds")
        yield longitude, latitude
        return
    for child in value:
        yield from _coordinate_pairs(child)


def _geometry_pairs(geometry: Any) -> list[tuple[float, float]]:
    if not isinstance(geometry, dict):
        raise SourceFormatError("GeoJSON feature geometry must be an object")
    geometry_type = geometry.get("type")
    if geometry_type == "GeometryCollection":
        geometries = geometry.get("geometries")
        if not isinstance(geometries, list) or not geometries:
            raise SourceFormatError("GeoJSON geometry collection must be non-empty")
        return [pair for child in geometries for pair in _geometry_pairs(child)]
    if geometry_type not in {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    }:
        raise SourceFormatError("GeoJSON geometry type is unsupported")
    return list(_coordinate_pairs(geometry.get("coordinates")))


def parse_feature_collection(content: bytes, *, label: str) -> tuple[dict[str, Any], list[tuple[float, float]]]:
    def reject_constant(_value: str) -> None:
        raise ValueError("non-finite JSON number")

    try:
        document = json.loads(content, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise SourceFormatError(f"{label} is not valid UTF-8 GeoJSON") from error
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise SourceFormatError(f"{label} must be a GeoJSON FeatureCollection")
    _reject_secret_keys(document)
    features = document.get("features")
    if not isinstance(features, list) or not features:
        raise SourceFormatError(f"{label} has no features")
    pairs = []
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise SourceFormatError(f"{label} contains a malformed feature")
        if not isinstance(feature.get("properties"), dict):
            raise SourceFormatError(f"{label} feature properties must be an object")
        pairs.extend(_geometry_pairs(feature.get("geometry")))
    return document, pairs


def validate_parquet(content: bytes, *, label: str) -> None:
    if len(content) < 13 or content[:4] != b"PAR1" or content[-4:] != b"PAR1":
        raise SourceFormatError(f"{label} is not a complete Parquet envelope")
    footer_length = int.from_bytes(content[-8:-4], "little")
    if footer_length <= 0 or footer_length > len(content) - 12:
        raise SourceFormatError(f"{label} has an invalid Parquet footer boundary")


def _bounds(pairs: Iterable[tuple[float, float]]) -> list[float]:
    coordinates = list(pairs)
    if not coordinates:
        raise SourceFormatError("GeoJSON geometry has no coordinates")
    longitudes = [pair[0] for pair in coordinates]
    latitudes = [pair[1] for pair in coordinates]
    return [min(longitudes), min(latitudes), max(longitudes), max(latitudes)]


def _batch_features(
    master: dict[str, Any],
    members: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_runid = {}
    for feature in master["features"]:
        runid = feature["properties"].get("runid")
        if not isinstance(runid, str) or not runid:
            raise SourceMembershipError("batch master feature is missing runid")
        if runid in by_runid:
            raise SourceMembershipError("batch master contains a duplicate runid")
        by_runid[runid] = feature
    expected = {member["runid"] for member in members}
    if set(by_runid) != expected:
        raise SourceMembershipError("batch membership differs from the reviewed member map")
    return by_runid


def _artifact_uri(base_uri: str, digest: str) -> str:
    return f"{base_uri.rstrip('/')}/objects/sha256/{digest[:2]}/{digest}"


def _artifact_reference(base_uri: str, published: PublishResult, media_type: str) -> dict[str, Any]:
    return {
        "uri": _artifact_uri(base_uri, published.digest),
        "sha256": published.digest,
        "bytes": published.byte_count,
        "media_type": media_type,
        "verified": True,
    }


def _publish_verified(client: ArtifactClient, path: Path) -> PublishResult:
    published = client.publish(path)
    fetched = client.fetch(published.digest)
    if fetched.byte_count != published.byte_count:
        raise SourceIntegrityError("published artifact verification changed its byte count")
    return published


def _publish_bytes(client: ArtifactClient, root: Path, name: str, content: bytes) -> PublishResult:
    path = root / name
    path.write_bytes(content)
    return _publish_verified(client, path)


def _load_replay_sources(
    requests: list[SourceRequest],
    receipt: Any,
    client: ArtifactClient,
    root: Path,
    expected_descriptor_digest: str,
) -> dict[tuple[str, str, str], Path]:
    if not isinstance(receipt, dict) or receipt.get("schema_version") != 1:
        raise SourceDescriptorError("replay receipt is invalid")
    if receipt.get("descriptor_sha256") != expected_descriptor_digest:
        raise SourceIntegrityError("replay receipt belongs to a different descriptor")
    records = receipt.get("sources")
    if not isinstance(records, list):
        raise SourceDescriptorError("replay receipt source list is invalid")
    by_key = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            "role",
            "runid",
            "url",
            "sha256",
            "bytes",
            "media_type",
        }:
            raise SourceDescriptorError("replay receipt source record is invalid")
        key = (record["role"], record["runid"] or "", record["url"])
        if key in by_key:
            raise SourceDescriptorError("replay receipt has duplicate sources")
        by_key[key] = record
    if set(by_key) != {request.key for request in requests}:
        raise SourceIntegrityError("replay receipt sources differ from the descriptor")
    loaded = {}
    for index, request in enumerate(requests):
        record = by_key[request.key]
        fetched = client.fetch(record["sha256"])
        if fetched.byte_count != record["bytes"]:
            raise SourceIntegrityError("replayed source byte count differs from its receipt")
        path = root / f"input-{index}"
        path.write_bytes(fetched.path.read_bytes())
        loaded[request.key] = path
    return loaded


def _fetch_sources(
    requests: list[SourceRequest],
    root: Path,
    headers: dict[str, str],
    fetcher: Fetcher,
) -> dict[tuple[str, str, str], Path]:
    loaded = {}
    for index, request in enumerate(requests):
        path = root / f"input-{index}"
        try:
            fetcher(request.url, path, headers)
        except SourcePreparationError:
            raise
        except Exception as error:
            path.unlink(missing_ok=True)
            raise SourceFetchError("required source could not be fetched") from error
        if path.is_symlink() or not path.is_file():
            raise SourceFetchError("required source fetch produced no regular file")
        loaded[request.key] = path
    return loaded


def _source_media_type(role: str) -> str:
    if role in {"master", "enrichment"} or role in GEOJSON_ROLES:
        return "application/geo+json"
    return "application/vnd.apache.parquet"


def _publish_enrichment_artifacts(
    *,
    client: ArtifactClient,
    root: Path,
    artifact_base_uri: str,
    descriptor: dict[str, Any],
    requests: list[SourceRequest],
    published_sources: dict[tuple[str, str, str], PublishResult],
    target_document: dict[str, Any],
    source_document: dict[str, Any],
    result: enrichment.NasaEnrichmentResult,
) -> dict[str, Any]:
    master_request = next(request for request in requests if request.role == "master")
    enrichment_request = next(request for request in requests if request.role == "enrichment")
    target_artifact = published_sources[master_request.key]
    source_artifact = published_sources[enrichment_request.key]
    enriched_artifact = _publish_bytes(
        client,
        root,
        "nasa-202606-enriched-master.geojson",
        canonical_json(result.document),
    )
    if enriched_artifact.digest in {target_artifact.digest, source_artifact.digest}:
        raise SourceIntegrityError("enrichment output reuses an input artifact")
    target_count = len(target_document["features"])
    source_runid_count = sum(
        "runid" in feature["properties"] for feature in source_document["features"]
    )
    enrichment_config = descriptor["enrichment"]
    validation_report = {
        "schema_version": 1,
        "report_id": "nasa-202606-enrichment",
        "subject": {"type": "transformation", "id": enrichment.TRANSFORMATION_KEY},
        "validator": {
            "git_commit": enrichment_config["code_git_commit"],
            "image_digest": enrichment_config["validator_image_digest"],
        },
        "started_at": descriptor["created_at"],
        "completed_at": descriptor["created_at"],
        "status": "passed",
        "checks": [
            {"code": "matched", "status": "passed", "count": result.matched},
            {
                "code": "target-unmatched",
                "status": "passed",
                "count": result.target_unmatched,
            },
            {
                "code": "source-unmatched",
                "status": "passed",
                "count": result.source_unmatched,
            },
            {
                "code": "duplicate-join-key",
                "status": "passed",
                "count": result.duplicate,
            },
            {"code": "preserved-membership", "status": "passed", "count": target_count},
            {"code": "preserved-runids", "status": "passed", "count": target_count},
            {"code": "preserved-geometry", "status": "passed", "count": target_count},
            {
                "code": "source-runids-ignored",
                "status": "passed",
                "count": source_runid_count,
            },
            {
                "code": "source-geometry-ignored",
                "status": "passed",
                "count": len(source_document["features"]),
            },
            {
                "code": "source-runid-differences",
                "status": "passed",
                "count": result.source_runid_differences,
            },
            {
                "code": "source-geometry-differences",
                "status": "passed",
                "count": result.source_geometry_differences,
            },
        ],
        "summary": "NASA 202606 WWS_Code enrichment preserved target authority.",
    }
    report_artifact = _publish_bytes(
        client,
        root,
        "nasa-202606-validation-report.json",
        canonical_json(validation_report),
    )
    lineage = {
        "schema_version": 1,
        "transformation_key": enrichment.TRANSFORMATION_KEY,
        "name": enrichment.TRANSFORMATION_NAME,
        "version": enrichment.TRANSFORMATION_VERSION,
        "code_git_commit": enrichment_config["code_git_commit"],
        "configuration_sha256": enrichment.configuration_sha256(),
        "join_keys": [enrichment.JOIN_KEY],
        "inputs": [
            _artifact_reference(
                artifact_base_uri,
                target_artifact,
                "application/geo+json",
            ),
            _artifact_reference(
                artifact_base_uri,
                source_artifact,
                "application/geo+json",
            ),
        ],
        "output": _artifact_reference(
            artifact_base_uri,
            enriched_artifact,
            "application/geo+json",
        ),
        "field_decisions": enrichment.lineage_field_decisions(
            target_artifact.digest,
            source_artifact.digest,
        ),
        "counts": {
            "matched": result.matched,
            "unmatched": result.unmatched,
            "duplicate": result.duplicate,
        },
        "validation_report": _artifact_reference(
            artifact_base_uri,
            report_artifact,
            "application/json",
        ),
    }
    lineage_artifact = _publish_bytes(
        client,
        root,
        "nasa-202606-transformation-lineage.json",
        canonical_json(lineage),
    )
    return _artifact_reference(
        artifact_base_uri,
        lineage_artifact,
        "application/json",
    )


def prepare_sources(
    raw_descriptor: Any,
    *,
    client: ArtifactClient,
    artifact_base_uri: str,
    fetcher: Fetcher = fetch_https,
    replay_receipt: Any | None = None,
) -> PreparedSources:
    descriptor = validate_descriptor(raw_descriptor)
    artifact_base_uri = _safe_https_uri(artifact_base_uri, "artifact_base_uri").rstrip("/")
    digest = descriptor_digest(descriptor)
    requests = source_requests(descriptor)
    headers = {}
    authentication = descriptor.get("authentication")
    if authentication is not None and replay_receipt is None:
        secret_value = os.environ.get(authentication["secret_ref"])
        if not secret_value:
            raise SourceFetchError("required source authentication is unavailable")
        headers["Authorization"] = f"Bearer {secret_value}"

    with tempfile.TemporaryDirectory(prefix="uwa-db17-prepare-") as temporary:
        root = Path(temporary)
        if replay_receipt is None:
            paths = _fetch_sources(requests, root, headers, fetcher)
        else:
            paths = _load_replay_sources(requests, replay_receipt, client, root, digest)

        master_features = None
        target_master_document = None
        enrichment_source_document = None
        enrichment_result = None
        if descriptor["kind"] == "batch":
            master_request = next(request for request in requests if request.role == "master")
            target_master_document, _ = parse_feature_collection(
                paths[master_request.key].read_bytes(),
                label="batch master",
            )
            master_document = target_master_document
            if "enrichment" in descriptor:
                enrichment_request = next(
                    request for request in requests if request.role == "enrichment"
                )
                enrichment_content = paths[enrichment_request.key].read_bytes()
                enrichment_config = descriptor["enrichment"]
                if len(enrichment_content) != enrichment_config["source_bytes"]:
                    raise SourceIntegrityError("enrichment source byte count differs")
                if sha256_bytes(enrichment_content) != enrichment_config["source_sha256"]:
                    raise SourceIntegrityError("enrichment source SHA-256 differs")
                enrichment_source_document, _ = parse_feature_collection(
                    enrichment_content,
                    label="NASA enrichment source",
                )
                try:
                    enrichment_result = enrichment.enrich_nasa_202606(
                        target_master_document,
                        enrichment_source_document,
                    )
                except enrichment.NasaEnrichmentError as error:
                    raise SourceFormatError(f"NASA enrichment failed: {error.code}") from error
                master_document = enrichment_result.document
            master_features = _batch_features(master_document, descriptor["members"])

        parsed_geojson = {}
        for request in requests:
            content = paths[request.key].read_bytes()
            if request.role in {"master", "enrichment"}:
                continue
            if request.role in GEOJSON_ROLES:
                parsed_geojson[request.key] = parse_feature_collection(
                    content,
                    label=request.role,
                )
            elif request.role in PARQUET_ROLES:
                validate_parquet(content, label=request.role)

        source_records = []
        published_sources = {}
        for request in requests:
            published = _publish_verified(client, paths[request.key])
            published_sources[request.key] = published
            source_records.append(
                {
                    "role": request.role,
                    "runid": request.runid,
                    "url": request.url,
                    "sha256": published.digest,
                    "bytes": published.byte_count,
                    "media_type": _source_media_type(request.role),
                }
            )

        transformation_lineage_reference = None
        if enrichment_result is not None:
            transformation_lineage_reference = _publish_enrichment_artifacts(
                client=client,
                root=root,
                artifact_base_uri=artifact_base_uri,
                descriptor=descriptor,
                requests=requests,
                published_sources=published_sources,
                target_document=target_master_document,
                source_document=enrichment_source_document,
                result=enrichment_result,
            )

        index_members = []
        for member_index, member in enumerate(descriptor["members"]):
            runid = member["runid"]
            if descriptor["kind"] == "batch":
                feature = master_features[runid]  # type: ignore[index]
                boundary_document = {"type": "FeatureCollection", "features": [feature]}
                boundary_bytes = canonical_json(boundary_document)
                boundary_pairs = _geometry_pairs(feature["geometry"])
                source_properties = feature["properties"]
            else:
                boundary_request = next(
                    request
                    for request in requests
                    if request.runid == runid and request.role == "boundary"
                )
                boundary_document, boundary_pairs = parsed_geojson[boundary_request.key]
                if len(boundary_document["features"]) != 1:
                    raise SourceFormatError("standalone boundary must contain exactly one feature")
                boundary_bytes = paths[boundary_request.key].read_bytes()
                source_properties = boundary_document["features"][0]["properties"]

            metadata = {
                "schema_version": 1,
                "collection_key": descriptor["collection_key"],
                "source_revision": descriptor["source_revision"],
                "watershed_key": member["watershed_key"],
                "runid": runid,
                "display_name": member["display_name"],
                "aliases": member["aliases"],
                "source_properties": source_properties,
            }
            metadata_artifact = _publish_bytes(
                client,
                root,
                f"metadata-{member_index}.json",
                canonical_json(metadata),
            )
            if descriptor["kind"] == "batch":
                boundary_artifact = _publish_bytes(
                    client,
                    root,
                    f"boundary-{member_index}.geojson",
                    boundary_bytes,
                )
            else:
                boundary_request = next(
                    request
                    for request in requests
                    if request.runid == runid and request.role == "boundary"
                )
                boundary_artifact = published_sources[boundary_request.key]

            artifacts = {
                "metadata": _artifact_reference(
                    artifact_base_uri, metadata_artifact, MEDIA_TYPES["metadata"]
                ),
                "boundary": _artifact_reference(
                    artifact_base_uri, boundary_artifact, MEDIA_TYPES["boundary"]
                ),
            }
            counts = {}
            for role in BATCH_TEMPLATE_ROLES:
                request = next(
                    candidate
                    for candidate in requests
                    if candidate.runid == runid and candidate.role == role
                )
                artifacts[role] = _artifact_reference(
                    artifact_base_uri,
                    published_sources[request.key],
                    MEDIA_TYPES[role],
                )
                if role in {"subcatchments", "channels"}:
                    document, _ = parsed_geojson[request.key]
                    counts[role] = len(document["features"])

            index_member = {
                "watershed_key": member["watershed_key"],
                "runid": runid,
                "display_name": member["display_name"],
                "aliases": member["aliases"],
                "artifacts": artifacts,
                "expected": {
                    "watersheds": 1,
                    "subcatchments": counts["subcatchments"],
                    "channels": counts["channels"],
                    "bounds": _bounds(boundary_pairs),
                },
            }
            if transformation_lineage_reference is not None:
                index_member["transformation_lineage"] = transformation_lineage_reference
            index_members.append(index_member)

        index = {
            "schema_version": 1,
            "collection_key": descriptor["collection_key"],
            "source_revision": descriptor["source_revision"],
            "created_at": descriptor["created_at"],
            "expected_member_count": len(index_members),
            "members": index_members,
        }
        if authentication is not None:
            index["authentication"] = authentication
        index_bytes = canonical_json(index)
        index_artifact = _publish_bytes(client, root, "batch-member-index.json", index_bytes)
        if replay_receipt is not None and replay_receipt.get("index_sha256") != index_artifact.digest:
            raise SourceIntegrityError("replayed inputs did not reproduce the exact member index")

        receipt = {
            "schema_version": 1,
            "descriptor_sha256": digest,
            "index_sha256": index_artifact.digest,
            "sources": source_records,
        }
        receipt_bytes = canonical_json(receipt)
        receipt_artifact = _publish_bytes(client, root, "source-receipt.json", receipt_bytes)
        return PreparedSources(
            index=index,
            receipt=receipt,
            index_bytes=index_bytes,
            receipt_bytes=receipt_bytes,
            index_artifact=index_artifact,
            receipt_artifact=receipt_artifact,
            source_count=len(source_records),
            member_count=len(index_members),
            replayed=replay_receipt is not None,
        )
