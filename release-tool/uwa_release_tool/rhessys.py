from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .artifacts import ArtifactClient, PublishResult
from .sources import fetch_https


KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
CREATED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
PARQUET_TYPES = {
    0: "BOOLEAN",
    1: "INT32",
    2: "INT64",
    3: "INT96",
    4: "FLOAT",
    5: "DOUBLE",
    6: "BYTE_ARRAY",
    7: "FIXED_LEN_BYTE_ARRAY",
}


class RhessysError(RuntimeError):
    pass


class RhessysDescriptorError(RhessysError):
    pass


class RhessysFetchError(RhessysError):
    pass


class RhessysIntegrityError(RhessysError):
    pass


class RhessysFormatError(RhessysError):
    pass


@dataclass(frozen=True)
class AssetRequest:
    family: str
    key: str
    url: str
    sha256: str
    byte_count: int

    @property
    def receipt_key(self) -> tuple[str, str, str]:
        return self.family, self.key, self.url


@dataclass(frozen=True)
class PreparedRhessys:
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


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, separators=(",", ":"), sort_keys=True) + "\n").encode()


def _exact(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise RhessysDescriptorError(f"{label} has missing or unexpected fields")


def _string(value: Any, label: str, maximum: int = 255) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise RhessysDescriptorError(f"{label} must be a non-empty bounded string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise RhessysDescriptorError(f"{label} contains control characters")
    return value


def _key(value: Any, label: str) -> str:
    result = _string(value, label, 96)
    if not KEY_PATTERN.fullmatch(result):
        raise RhessysDescriptorError(f"{label} is not canonical")
    return result


def _name(value: Any, label: str) -> str:
    result = _string(value, label, 64)
    if not NAME_PATTERN.fullmatch(result):
        raise RhessysDescriptorError(f"{label} is invalid")
    return result


def _column_name(value: Any, label: str) -> str:
    return _string(value, label, 255)


def _scenario_key(value: Any, label: str) -> str:
    result = _string(value, label, 96)
    if not re.fullmatch(r"^[A-Za-z_][A-Za-z0-9_-]{0,95}$", result):
        raise RhessysDescriptorError(f"{label} is invalid")
    return result


def _sha256(value: Any, label: str) -> str:
    result = _string(value, label, 64)
    if not SHA256_PATTERN.fullmatch(result):
        raise RhessysDescriptorError(f"{label} is invalid")
    return result


def _https(value: Any, label: str) -> str:
    result = _string(value, label, 2048)
    parsed = urlparse(result)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RhessysDescriptorError(f"{label} must be a credential-free HTTPS URI")
    return result


def _positive_integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise RhessysDescriptorError(f"{label} must be a positive integer")
    return value


def _number(value: Any, label: str) -> float | int:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise RhessysDescriptorError(f"{label} must be finite")
    return value


def _asset_source(value: dict[str, Any], label: str) -> dict[str, Any]:
    return {
        "source_url": _https(value["source_url"], f"{label} source_url"),
        "source_sha256": _sha256(value["source_sha256"], f"{label} source_sha256"),
        "source_bytes": _positive_integer(value["source_bytes"], f"{label} source_bytes"),
    }


def _raster_metadata(value: dict[str, Any], label: str) -> dict[str, Any]:
    crs = _string(value["crs"], f"{label} crs", 16)
    if not re.fullmatch(r"EPSG:[0-9]{4,6}", crs):
        raise RhessysDescriptorError(f"{label} crs is invalid")
    bounds = value["bounds"]
    if not isinstance(bounds, list) or len(bounds) != 4:
        raise RhessysDescriptorError(f"{label} bounds must contain four numbers")
    bounds = [_number(item, f"{label} bounds") for item in bounds]
    if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        raise RhessysDescriptorError(f"{label} bounds are reversed")
    dimensions = value["dimensions"]
    if not isinstance(dimensions, list) or len(dimensions) != 2:
        raise RhessysDescriptorError(f"{label} dimensions must contain two integers")
    dimensions = [
        _positive_integer(item, f"{label} dimensions") for item in dimensions
    ]
    nodata = value["nodata"]
    if nodata is not None:
        nodata = _number(nodata, f"{label} nodata")
    return {
        "crs": crs,
        "bounds": bounds,
        "dimensions": dimensions,
        "bands": _positive_integer(value["bands"], f"{label} bands"),
        "nodata": nodata,
    }


def validate_descriptor(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RhessysDescriptorError("descriptor root must be an object")
    _exact(
        value,
        {
            "schema_version",
            "kind",
            "collection_key",
            "watershed_key",
            "runid",
            "source_revision",
            "created_at",
            "mode",
            "geometry_revision",
            "scenarios",
            "spatial_inputs",
            "parquets",
            "geometries",
            "geotiffs",
        },
        "descriptor",
    )
    if value["schema_version"] != 1 or value["kind"] != "rhessys-capability":
        raise RhessysDescriptorError("descriptor schema_version or kind is unsupported")
    mode = value["mode"]
    if mode not in {"dynamic", "precomputed", "both"}:
        raise RhessysDescriptorError("mode is unsupported")
    created_at = _string(value["created_at"], "created_at")
    if not CREATED_AT_PATTERN.fullmatch(created_at):
        raise RhessysDescriptorError("created_at must be a whole-second UTC timestamp")

    raw_scenarios = value["scenarios"]
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise RhessysDescriptorError("scenarios must be a non-empty array")
    scenarios = []
    for raw in raw_scenarios:
        if not isinstance(raw, dict):
            raise RhessysDescriptorError("scenario must be an object")
        _exact(raw, {"key", "variables"}, "scenario")
        variables = raw["variables"]
        if not isinstance(variables, list) or not variables:
            raise RhessysDescriptorError("scenario variables must be non-empty")
        variables = [_name(item, "scenario variable") for item in variables]
        if len(variables) != len(set(variables)):
            raise RhessysDescriptorError("scenario variables must be unique")
        scenarios.append(
            {"key": _scenario_key(raw["key"], "scenario key"), "variables": variables}
        )
    if len({item["key"] for item in scenarios}) != len(scenarios):
        raise RhessysDescriptorError("scenario keys must be unique")

    raw_spatial = value["spatial_inputs"]
    if not isinstance(raw_spatial, list):
        raise RhessysDescriptorError("spatial_inputs must be an array")
    spatial_inputs = []
    raster_fields = {"crs", "bounds", "dimensions", "bands", "nodata"}
    source_fields = {"source_url", "source_sha256", "source_bytes", "geometry_revision"}
    for raw in raw_spatial:
        if not isinstance(raw, dict):
            raise RhessysDescriptorError("spatial input must be an object")
        _exact(raw, {"role", "required_for_activation"} | source_fields | raster_fields, "spatial input")
        spatial_inputs.append(
            {
                "role": _key(raw["role"], "spatial role"),
                **_asset_source(raw, "spatial input"),
                "geometry_revision": _sha256(raw["geometry_revision"], "spatial geometry_revision"),
                **_raster_metadata(raw, "spatial input"),
                "required_for_activation": _boolean(raw["required_for_activation"], "spatial required flag"),
            }
        )
    if len({item["role"] for item in spatial_inputs}) != len(spatial_inputs):
        raise RhessysDescriptorError("spatial input roles must be unique")

    raw_parquets = value["parquets"]
    if not isinstance(raw_parquets, list):
        raise RhessysDescriptorError("parquets must be an array")
    parquets = []
    for raw in raw_parquets:
        if not isinstance(raw, dict):
            raise RhessysDescriptorError("parquet must be an object")
        _exact(
            raw,
            {
                "role",
                "dataset_key",
                "scenario",
                "source_url",
                "source_sha256",
                "source_bytes",
                "geometry_revision",
                "spatial_id_field",
                "columns",
                "variables",
                "year_range",
                "required_for_activation",
            },
            "parquet",
        )
        role = raw["role"]
        if role not in {"basin", "hillslope", "patch"}:
            raise RhessysDescriptorError("parquet role is unsupported")
        scenario = _scenario_key(raw["scenario"], "parquet scenario")
        if scenario not in {item["key"] for item in scenarios}:
            raise RhessysDescriptorError("parquet scenario is undeclared")
        raw_columns = raw["columns"]
        if not isinstance(raw_columns, list) or not raw_columns:
            raise RhessysDescriptorError("parquet columns must be non-empty")
        columns = []
        for column in raw_columns:
            if not isinstance(column, dict):
                raise RhessysDescriptorError("parquet column must be an object")
            _exact(column, {"name", "physical_type"}, "parquet column")
            physical_type = _string(column["physical_type"], "parquet physical_type", 32)
            if physical_type not in PARQUET_TYPES.values():
                raise RhessysDescriptorError("parquet physical_type is unsupported")
            columns.append(
                {
                    "name": _column_name(column["name"], "parquet column name"),
                    "physical_type": physical_type,
                }
            )
        column_names = [column["name"] for column in columns]
        if len(column_names) != len(set(column_names)):
            raise RhessysDescriptorError("parquet column names must be unique")
        raw_variables = raw["variables"]
        if not isinstance(raw_variables, list) or not raw_variables:
            raise RhessysDescriptorError("parquet variables must be non-empty")
        variables = []
        for variable in raw_variables:
            if not isinstance(variable, dict):
                raise RhessysDescriptorError("parquet variable must be an object")
            _exact(variable, {"name", "units"}, "parquet variable")
            variables.append(
                {
                    "name": _name(variable["name"], "parquet variable name"),
                    "units": _string(variable["units"], "parquet variable units", 64),
                }
            )
        variable_names = [variable["name"] for variable in variables]
        spatial_id = _name(raw["spatial_id_field"], "spatial_id_field")
        if len(variable_names) != len(set(variable_names)):
            raise RhessysDescriptorError("parquet variables must be unique")
        if not {spatial_id, "year", *variable_names}.issubset(column_names):
            raise RhessysDescriptorError("parquet schema lacks an identity, year, or variable column")
        years = raw["year_range"]
        if (
            not isinstance(years, list)
            or len(years) != 2
            or any(not isinstance(year, int) or isinstance(year, bool) for year in years)
            or not 1800 <= years[0] <= years[1] <= 3000
        ):
            raise RhessysDescriptorError("parquet year_range is invalid")
        parquets.append(
            {
                "dataset_key": _key(raw["dataset_key"], "parquet dataset_key"),
                "scenario": scenario,
                "role": role,
                **_asset_source(raw, "parquet"),
                "geometry_revision": _sha256(raw["geometry_revision"], "parquet geometry_revision"),
                "spatial_id_field": spatial_id,
                "columns": columns,
                "variables": variables,
                "year_range": years,
                "required_for_activation": _boolean(raw["required_for_activation"], "parquet required flag"),
            }
        )
    if len({item["dataset_key"] for item in parquets}) != len(parquets):
        raise RhessysDescriptorError("parquet dataset keys must be unique")
    parquet_coordinates = [
        (item["scenario"], item["role"], variable["name"])
        for item in parquets
        for variable in item["variables"]
    ]
    if len(parquet_coordinates) != len(set(parquet_coordinates)):
        raise RhessysDescriptorError("parquet query coordinates overlap")
    scenario_variables = {item["key"]: set(item["variables"]) for item in scenarios}
    if any(
        not {variable["name"] for variable in item["variables"]}.issubset(
            scenario_variables[item["scenario"]]
        )
        for item in parquets
    ):
        raise RhessysDescriptorError("parquet variable is absent from its scenario")

    raw_geometries = value["geometries"]
    if not isinstance(raw_geometries, list):
        raise RhessysDescriptorError("geometries must be an array")
    geometries = []
    scenario_keys = {item["key"] for item in scenarios}
    for raw in raw_geometries:
        if not isinstance(raw, dict):
            raise RhessysDescriptorError("geometry must be an object")
        _exact(
            raw,
            {
                "scale",
                "scenarios",
                "source_url",
                "source_sha256",
                "source_bytes",
                "geometry_revision",
                "source_crs",
                "required_for_activation",
            },
            "geometry",
        )
        if raw["scale"] not in {"hillslope", "patch"}:
            raise RhessysDescriptorError("geometry scale is unsupported")
        geometry_scenarios = raw["scenarios"]
        if not isinstance(geometry_scenarios, list) or not geometry_scenarios:
            raise RhessysDescriptorError("geometry scenarios must be non-empty")
        geometry_scenarios = [
            _scenario_key(item, "geometry scenario") for item in geometry_scenarios
        ]
        if len(geometry_scenarios) != len(set(geometry_scenarios)):
            raise RhessysDescriptorError("geometry scenarios must be unique")
        if not set(geometry_scenarios).issubset(scenario_keys):
            raise RhessysDescriptorError("geometry scenario is undeclared")
        source_crs = _string(raw["source_crs"], "geometry source_crs", 16)
        if not re.fullmatch(r"EPSG:[0-9]{4,6}", source_crs):
            raise RhessysDescriptorError("geometry source_crs is invalid")
        geometries.append(
            {
                "scale": raw["scale"],
                "scenarios": geometry_scenarios,
                **_asset_source(raw, "geometry"),
                "geometry_revision": _sha256(
                    raw["geometry_revision"], "geometry geometry_revision"
                ),
                "source_crs": source_crs,
                "required_for_activation": _boolean(
                    raw["required_for_activation"], "geometry required flag"
                ),
            }
        )
    geometry_coordinates = [
        (item["scale"], scenario)
        for item in geometries
        for scenario in item["scenarios"]
    ]
    if len(geometry_coordinates) != len(set(geometry_coordinates)):
        raise RhessysDescriptorError("geometry query coordinates overlap")

    raw_geotiffs = value["geotiffs"]
    if not isinstance(raw_geotiffs, list):
        raise RhessysDescriptorError("geotiffs must be an array")
    geotiffs = []
    for raw in raw_geotiffs:
        if not isinstance(raw, dict):
            raise RhessysDescriptorError("geotiff must be an object")
        _exact(
            raw,
            {"scenario", "variable", "required_for_activation"} | source_fields | raster_fields,
            "geotiff",
        )
        geotiffs.append(
            {
                "scenario": _scenario_key(raw["scenario"], "geotiff scenario"),
                "variable": _name(raw["variable"], "geotiff variable"),
                **_asset_source(raw, "geotiff"),
                "geometry_revision": _sha256(raw["geometry_revision"], "geotiff geometry_revision"),
                **_raster_metadata(raw, "geotiff"),
                "required_for_activation": _boolean(raw["required_for_activation"], "geotiff required flag"),
            }
        )
    pairs = [(item["scenario"], item["variable"]) for item in geotiffs]
    if len(pairs) != len(set(pairs)):
        raise RhessysDescriptorError("geotiff scenario and variable pairs must be unique")
    expected_pairs = {
        (scenario["key"], variable)
        for scenario in scenarios
        for variable in scenario["variables"]
    }
    if mode in {"precomputed", "both"} and set(pairs) != expected_pairs:
        raise RhessysDescriptorError("precomputed geotiffs do not exactly cover declared scenarios")
    if mode in {"dynamic", "both"} and (
        not spatial_inputs or not parquets or not geometries
    ):
        raise RhessysDescriptorError(
            "dynamic mode requires spatial inputs, parquets, and geometries"
        )
    parquet_variables = {
        variable["name"]
        for parquet in parquets
        for variable in parquet["variables"]
    }
    if mode in {"dynamic", "both"} and not {
        variable for scenario in scenarios for variable in scenario["variables"]
    }.issubset(parquet_variables):
        raise RhessysDescriptorError("dynamic scenarios declare a variable absent from Parquet")
    if mode == "dynamic" and geotiffs:
        raise RhessysDescriptorError("dynamic mode cannot declare precomputed geotiffs")
    required_geometry = {
        (item["role"], item["scenario"])
        for item in parquets
        if item["role"] in {"hillslope", "patch"}
    }
    if mode in {"dynamic", "both"} and not required_geometry.issubset(
        set(geometry_coordinates)
    ):
        raise RhessysDescriptorError("dynamic query geometry is undeclared")
    if mode == "precomputed" and (spatial_inputs or parquets or geometries):
        raise RhessysDescriptorError("precomputed mode cannot declare dynamic assets")

    geometry_revision = _sha256(value["geometry_revision"], "geometry_revision")
    if any(
        asset["geometry_revision"] != geometry_revision
        for asset in [*spatial_inputs, *parquets, *geometries, *geotiffs]
    ):
        raise RhessysDescriptorError("RHESSys asset geometry revision differs from the capability")

    return {
        "schema_version": 1,
        "kind": "rhessys-capability",
        "collection_key": _key(value["collection_key"], "collection_key"),
        "watershed_key": _key(value["watershed_key"], "watershed_key"),
        "runid": _string(value["runid"], "runid"),
        "source_revision": _string(value["source_revision"], "source_revision"),
        "created_at": created_at,
        "mode": mode,
        "geometry_revision": geometry_revision,
        "scenarios": scenarios,
        "spatial_inputs": spatial_inputs,
        "parquets": parquets,
        "geometries": geometries,
        "geotiffs": geotiffs,
    }


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise RhessysDescriptorError(f"{label} must be boolean")
    return value


class _CompactReader:
    def __init__(self, content: bytes):
        self.content = content
        self.offset = 0

    def byte(self) -> int:
        if self.offset >= len(self.content):
            raise RhessysFormatError("Parquet footer ended unexpectedly")
        value = self.content[self.offset]
        self.offset += 1
        return value

    def take(self, length: int) -> bytes:
        if length < 0 or self.offset + length > len(self.content):
            raise RhessysFormatError("Parquet footer boundary is invalid")
        value = self.content[self.offset : self.offset + length]
        self.offset += length
        return value

    def varint(self) -> int:
        result = 0
        for shift in range(0, 70, 7):
            value = self.byte()
            result |= (value & 0x7F) << shift
            if not value & 0x80:
                return result
        raise RhessysFormatError("Parquet footer integer is too large")

    def integer(self) -> int:
        value = self.varint()
        return (value >> 1) ^ -(value & 1)

    def binary(self) -> bytes:
        return self.take(self.varint())

    def field(self, previous: int) -> tuple[int, int, bool | None]:
        header = self.byte()
        compact_type = header & 0x0F
        if compact_type == 0:
            return 0, 0, None
        delta = header >> 4
        field_id = previous + delta if delta else self.integer()
        boolean = True if compact_type == 1 else False if compact_type == 2 else None
        return field_id, compact_type, boolean

    def list_header(self) -> tuple[int, int]:
        header = self.byte()
        size = header >> 4
        compact_type = header & 0x0F
        if size == 15:
            size = self.varint()
        if size > 1_000_000:
            raise RhessysFormatError("Parquet footer collection is unbounded")
        return size, compact_type

    def skip(self, compact_type: int, boolean: bool | None = None) -> None:
        if compact_type in {1, 2}:
            return
        if compact_type == 3:
            self.byte()
        elif compact_type in {4, 5, 6}:
            self.integer()
        elif compact_type == 7:
            self.take(8)
        elif compact_type == 8:
            self.binary()
        elif compact_type in {9, 10}:
            size, item_type = self.list_header()
            for _ in range(size):
                self.skip(item_type)
        elif compact_type == 11:
            size = self.varint()
            if size:
                types = self.byte()
                for _ in range(size):
                    self.skip(types >> 4)
                    self.skip(types & 0x0F)
        elif compact_type == 12:
            previous = 0
            while True:
                field_id, child_type, child_boolean = self.field(previous)
                if child_type == 0:
                    break
                previous = field_id
                self.skip(child_type, child_boolean)
        else:
            raise RhessysFormatError("Parquet footer contains an unknown compact type")


def inspect_parquet(content: bytes) -> dict[str, Any]:
    if len(content) < 13 or content[:4] != b"PAR1" or content[-4:] != b"PAR1":
        raise RhessysFormatError("Parquet asset is not a complete envelope")
    footer_length = int.from_bytes(content[-8:-4], "little")
    footer_start = len(content) - 8 - footer_length
    if footer_length <= 0 or footer_start <= 4:
        raise RhessysFormatError("Parquet footer boundary is invalid")
    reader = _CompactReader(content[footer_start : footer_start + footer_length])
    previous = 0
    schema: list[dict[str, Any]] | None = None
    row_count: int | None = None
    while True:
        field_id, compact_type, boolean = reader.field(previous)
        if compact_type == 0:
            break
        previous = field_id
        if field_id == 2 and compact_type == 9:
            size, item_type = reader.list_header()
            if item_type != 12 or not size:
                raise RhessysFormatError("Parquet schema list is invalid")
            schema = [_read_schema_element(reader) for _ in range(size)]
        elif field_id == 3 and compact_type == 6:
            row_count = reader.integer()
        else:
            reader.skip(compact_type, boolean)
    if reader.offset != len(reader.content) or schema is None or row_count is None or row_count <= 0:
        raise RhessysFormatError("Parquet metadata is incomplete")
    columns = []
    for element in schema[1:]:
        if element["type"] is not None:
            columns.append(
                {
                    "name": element["name"],
                    "physical_type": PARQUET_TYPES.get(element["type"], "UNKNOWN"),
                }
            )
    if not columns or len({column["name"] for column in columns}) != len(columns):
        raise RhessysFormatError("Parquet leaf schema is empty or ambiguous")
    body = content[4:footer_start]
    if not body:
        raise RhessysFormatError("Parquet has no representative data bytes")
    return {"columns": columns, "row_count": row_count, "sample_bytes_read": min(2, len(body))}


def _read_schema_element(reader: _CompactReader) -> dict[str, Any]:
    previous = 0
    name = None
    physical_type = None
    while True:
        field_id, compact_type, boolean = reader.field(previous)
        if compact_type == 0:
            break
        previous = field_id
        if field_id == 1 and compact_type == 5:
            physical_type = reader.integer()
        elif field_id == 4 and compact_type == 8:
            try:
                name = reader.binary().decode("utf-8")
            except UnicodeDecodeError as error:
                raise RhessysFormatError("Parquet column name is not UTF-8") from error
        else:
            reader.skip(compact_type, boolean)
    if not name or len(name) > 255 or any(
        ord(character) < 32 or ord(character) == 127 for character in name
    ):
        raise RhessysFormatError("Parquet schema element name is invalid")
    return {"name": name, "type": physical_type}


def inspect_geotiff(content: bytes) -> dict[str, Any]:
    if len(content) < 16 or content[:2] not in {b"II", b"MM"}:
        raise RhessysFormatError("GeoTIFF byte order marker is invalid")
    endian = "<" if content[:2] == b"II" else ">"
    if struct.unpack_from(f"{endian}H", content, 2)[0] != 42:
        raise RhessysFormatError("GeoTIFF magic is invalid")
    ifd_offset = struct.unpack_from(f"{endian}I", content, 4)[0]
    if ifd_offset + 2 > len(content):
        raise RhessysFormatError("GeoTIFF IFD offset is invalid")
    count = struct.unpack_from(f"{endian}H", content, ifd_offset)[0]
    if count == 0 or count > 256 or ifd_offset + 2 + count * 12 + 4 > len(content):
        raise RhessysFormatError("GeoTIFF IFD is invalid")
    tags = {}
    required_tags = {
        256,
        257,
        273,
        277,
        279,
        324,
        325,
        33550,
        33922,
        34264,
        34735,
        42113,
    }
    for index in range(count):
        offset = ifd_offset + 2 + index * 12
        tag, value_type, value_count = struct.unpack_from(f"{endian}HHI", content, offset)
        if tag in required_tags:
            tags[tag] = _tiff_values(
                content, endian, value_type, value_count, offset + 8
            )
    try:
        width = int(tags[256][0])
        height = int(tags[257][0])
        bands = int(tags.get(277, [1])[0])
        geokeys = [int(item) for item in tags[34735]]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise RhessysFormatError("GeoTIFF lacks required structural tags") from error
    if width <= 0 or height <= 0 or bands <= 0 or len(geokeys) < 4:
        raise RhessysFormatError("GeoTIFF structural metadata is invalid")
    crs_code = None
    key_count = geokeys[3]
    if len(geokeys) < 4 + key_count * 4:
        raise RhessysFormatError("GeoTIFF key directory is truncated")
    for index in range(key_count):
        key_id, location, count_value, value = geokeys[4 + index * 4 : 8 + index * 4]
        if key_id in {2048, 3072} and location == 0 and count_value == 1:
            crs_code = value
    if crs_code is None:
        raise RhessysFormatError("GeoTIFF has no direct EPSG key")
    scale = tags.get(33550)
    tie = tags.get(33922)
    transform = tags.get(34264)
    if scale is not None and tie is not None and len(scale) >= 2 and len(tie) >= 6:
        origin_x = float(tie[3]) - float(tie[0]) * float(scale[0])
        origin_y = float(tie[4]) + float(tie[1]) * float(scale[1])
        bounds = [
            origin_x,
            origin_y - height * float(scale[1]),
            origin_x + width * float(scale[0]),
            origin_y,
        ]
    elif transform is not None and len(transform) == 16:
        matrix = [float(item) for item in transform]
        if any(
            not math.isfinite(item) for item in matrix
        ) or not (
            matrix[1] == matrix[2] == matrix[4] == matrix[6] == 0
            and matrix[0] > 0
            and matrix[5] < 0
            and matrix[15] == 1
        ):
            raise RhessysFormatError(
                "GeoTIFF transformation is not a supported axis-aligned grid"
            )
        x_values = [matrix[3], matrix[3] + width * matrix[0]]
        y_values = [matrix[7], matrix[7] + height * matrix[5]]
        bounds = [min(x_values), min(y_values), max(x_values), max(y_values)]
    else:
        raise RhessysFormatError("GeoTIFF lacks supported georeferencing tags")
    offsets = tags.get(273) or tags.get(324)
    byte_counts = tags.get(279) or tags.get(325)
    if not offsets or not byte_counts or len(offsets) != len(byte_counts):
        raise RhessysFormatError("GeoTIFF has no readable strip or tile")
    sample_offset = int(offsets[0])
    sample_count = int(byte_counts[0])
    if sample_count <= 0 or sample_offset < 0 or sample_offset + sample_count > len(content):
        raise RhessysFormatError("GeoTIFF sample range is invalid")
    nodata = None
    if 42113 in tags:
        try:
            raw_nodata = tags[42113][0].rstrip("\x00")
            nodata = float(raw_nodata)
            if math.isnan(nodata):
                nodata = None
        except (AttributeError, ValueError) as error:
            raise RhessysFormatError("GeoTIFF nodata value is invalid") from error
    return {
        "crs": f"EPSG:{crs_code}",
        "bounds": bounds,
        "dimensions": [width, height],
        "bands": bands,
        "nodata": nodata,
        "sample_bytes_read": 1,
    }


def _tiff_values(content: bytes, endian: str, value_type: int, count: int, field_offset: int) -> list[Any]:
    formats = {2: ("s", 1), 3: ("H", 2), 4: ("I", 4), 12: ("d", 8)}
    if value_type not in formats or count <= 0 or count > 1_000_000:
        raise RhessysFormatError("GeoTIFF tag type or count is unsupported")
    code, width = formats[value_type]
    length = width * count
    if length <= 4:
        start = field_offset
    else:
        start = struct.unpack_from(f"{endian}I", content, field_offset)[0]
    if start < 0 or start + length > len(content):
        raise RhessysFormatError("GeoTIFF tag payload is out of bounds")
    if value_type == 2:
        return [content[start : start + length].decode("ascii")]
    return list(struct.unpack_from(f"{endian}{count}{code}", content, start))


def _requests(descriptor: dict[str, Any]) -> list[AssetRequest]:
    requests = []
    for family, assets in (
        ("spatial-input", descriptor["spatial_inputs"]),
        ("parquet", descriptor["parquets"]),
        ("geometry", descriptor["geometries"]),
        ("geotiff", descriptor["geotiffs"]),
    ):
        for asset in assets:
            key = (
                asset.get("dataset_key")
                or asset.get("role")
                or (
                    f'{asset["scale"]}:{",".join(asset["scenarios"])}'
                    if family == "geometry"
                    else f'{asset["scenario"]}:{asset["variable"]}'
                )
            )
            requests.append(
                AssetRequest(family, key, asset["source_url"], asset["source_sha256"], asset["source_bytes"])
            )
    return requests


def _artifact_uri(base_uri: str, digest: str) -> str:
    return f"{base_uri.rstrip('/')}/objects/sha256/{digest[:2]}/{digest}"


def _reference(base_uri: str, result: PublishResult, media_type: str) -> dict[str, Any]:
    return {
        "uri": _artifact_uri(base_uri, result.digest),
        "sha256": result.digest,
        "bytes": result.byte_count,
        "media_type": media_type,
        "verified": True,
    }


def _publish_verified(client: ArtifactClient, path: Path) -> PublishResult:
    result = client.publish(path)
    fetched = client.fetch(result.digest)
    if fetched.byte_count != result.byte_count:
        raise RhessysIntegrityError("published asset byte count changed during verification")
    return result


def _publish_bytes(client: ArtifactClient, root: Path, name: str, content: bytes) -> PublishResult:
    path = root / name
    path.write_bytes(content)
    return _publish_verified(client, path)


def _same_raster(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    return (
        expected["crs"] == observed["crs"]
        and expected["dimensions"] == observed["dimensions"]
        and expected["bands"] == observed["bands"]
        and expected["nodata"] == observed["nodata"]
        and all(math.isclose(float(left), float(right), rel_tol=0, abs_tol=1e-9) for left, right in zip(expected["bounds"], observed["bounds"], strict=True))
    )


def inspect_geometry(content: bytes) -> dict[str, int]:
    try:
        document = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RhessysFormatError("geometry is not valid UTF-8 GeoJSON") from error
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise RhessysFormatError("geometry must be a GeoJSON FeatureCollection")
    features = document.get("features")
    if not isinstance(features, list) or not features:
        raise RhessysFormatError("geometry FeatureCollection must be non-empty")

    coordinate_count = 0

    def inspect_coordinates(value: Any) -> None:
        nonlocal coordinate_count
        if not isinstance(value, list) or not value:
            raise RhessysFormatError("geometry coordinates are empty or invalid")
        if isinstance(value[0], (int, float)) and not isinstance(value[0], bool):
            if len(value) < 2 or any(
                not isinstance(item, (int, float))
                or isinstance(item, bool)
                or not math.isfinite(item)
                for item in value[:2]
            ):
                raise RhessysFormatError("geometry coordinate is invalid")
            coordinate_count += 1
            return
        for child in value:
            inspect_coordinates(child)

    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise RhessysFormatError("geometry feature is invalid")
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or "coordinates" not in geometry:
            raise RhessysFormatError("geometry feature lacks geometry")
        inspect_coordinates(geometry["coordinates"])
    return {"feature_count": len(features), "coordinate_count": coordinate_count}


def removed_capabilities(previous: list[str], current: list[str]) -> list[str]:
    if len(previous) != len(set(previous)) or len(current) != len(set(current)):
        raise RhessysDescriptorError("capability sets must contain unique watershed keys")
    for key in [*previous, *current]:
        _key(key, "capability watershed key")
    return sorted(set(previous) - set(current))


def prepare_capability(
    value: Any,
    *,
    client: ArtifactClient,
    artifact_base_uri: str,
    replay_receipt: Any = None,
    fetcher: Fetcher = fetch_https,
) -> PreparedRhessys:
    descriptor = validate_descriptor(value)
    base_uri = _https(artifact_base_uri, "artifact_base_uri")
    descriptor_sha256 = hashlib.sha256(canonical_json(descriptor)).hexdigest()
    requests = _requests(descriptor)
    with tempfile.TemporaryDirectory(prefix="uwa-rhessys-") as temporary:
        root = Path(temporary)
        paths: dict[tuple[str, str, str], Path] = {}
        replayed = replay_receipt is not None
        if replayed:
            if not isinstance(replay_receipt, dict) or replay_receipt.get("descriptor_sha256") != descriptor_sha256:
                raise RhessysIntegrityError("replay receipt belongs to a different RHESSys descriptor")
            records = replay_receipt.get("sources")
            if not isinstance(records, list):
                raise RhessysDescriptorError("replay receipt source list is invalid")
            by_key = {(item.get("family"), item.get("key"), item.get("url")): item for item in records if isinstance(item, dict)}
            if set(by_key) != {request.receipt_key for request in requests}:
                raise RhessysIntegrityError("replay receipt sources differ from the RHESSys descriptor")
            for index, request in enumerate(requests):
                record = by_key[request.receipt_key]
                if record.get("sha256") != request.sha256 or record.get("bytes") != request.byte_count:
                    raise RhessysIntegrityError("replay receipt source identity differs")
                fetched = client.fetch(request.sha256)
                path = root / f"input-{index}"
                path.write_bytes(fetched.path.read_bytes())
                paths[request.receipt_key] = path
        else:
            for index, request in enumerate(requests):
                path = root / f"input-{index}"
                try:
                    fetcher(request.url, path, {})
                except RhessysError:
                    raise
                except Exception as error:
                    path.unlink(missing_ok=True)
                    raise RhessysFetchError("required RHESSys source could not be fetched") from error
                paths[request.receipt_key] = path

        published: dict[tuple[str, str, str], PublishResult] = {}
        source_records = []
        inspections = {}
        by_request = {request.receipt_key: request for request in requests}
        for key, path in paths.items():
            request = by_request[key]
            try:
                content = path.read_bytes()
            except OSError as error:
                raise RhessysFetchError("required RHESSys source is unreadable") from error
            if len(content) != request.byte_count or hashlib.sha256(content).hexdigest() != request.sha256:
                raise RhessysIntegrityError("RHESSys source size or SHA-256 differs")
            if request.family == "parquet":
                inspections[key] = inspect_parquet(content)
            elif request.family == "geometry":
                inspections[key] = inspect_geometry(content)
            else:
                inspections[key] = inspect_geotiff(content)
            published[key] = _publish_verified(client, path)
            source_records.append(
                {
                    "family": request.family,
                    "key": request.key,
                    "url": request.url,
                    "sha256": request.sha256,
                    "bytes": request.byte_count,
                }
            )

        spatial_index = []
        for asset in descriptor["spatial_inputs"]:
            key = ("spatial-input", asset["role"], asset["source_url"])
            if not _same_raster(asset, inspections[key]):
                raise RhessysFormatError("spatial input metadata differs from its declaration")
            spatial_index.append(
                {
                    "role": asset["role"],
                    "artifact": _reference(base_uri, published[key], "image/tiff"),
                    "required_for_activation": asset["required_for_activation"],
                }
            )
        parquet_index = []
        for asset in descriptor["parquets"]:
            key = ("parquet", asset["dataset_key"], asset["source_url"])
            if inspections[key]["columns"] != asset["columns"]:
                raise RhessysFormatError("Parquet physical schema differs from its declaration")
            parquet_index.append(
                {
                    "dataset_key": asset["dataset_key"],
                    "scenario": asset["scenario"],
                    "role": asset["role"],
                    "artifact": _reference(base_uri, published[key], "application/vnd.apache.parquet"),
                    "spatial_id_field": asset["spatial_id_field"],
                    "columns": asset["columns"],
                    "variables": asset["variables"],
                    "year_range": asset["year_range"],
                    "required_for_activation": asset["required_for_activation"],
                }
            )
        geometry_index = []
        for asset in descriptor["geometries"]:
            asset_key = f'{asset["scale"]}:{",".join(asset["scenarios"])}'
            key = ("geometry", asset_key, asset["source_url"])
            geometry_index.append(
                {
                    "scale": asset["scale"],
                    "scenarios": asset["scenarios"],
                    "artifact": _reference(
                        base_uri, published[key], "application/geo+json"
                    ),
                    "source_crs": asset["source_crs"],
                    "feature_count": inspections[key]["feature_count"],
                    "required_for_activation": asset["required_for_activation"],
                }
            )
        geotiff_index = []
        for asset in descriptor["geotiffs"]:
            asset_key = f'{asset["scenario"]}:{asset["variable"]}'
            key = ("geotiff", asset_key, asset["source_url"])
            if not _same_raster(asset, inspections[key]):
                raise RhessysFormatError("GeoTIFF metadata differs from its declaration")
            geotiff_index.append(
                {
                    "artifact": _reference(base_uri, published[key], "image/tiff"),
                    "scenario": asset["scenario"],
                    "variable": asset["variable"],
                    "crs": asset["crs"],
                    "bounds": asset["bounds"],
                    "dimensions": asset["dimensions"],
                    "bands": asset["bands"],
                    "nodata": asset["nodata"],
                    "required_for_activation": asset["required_for_activation"],
                }
            )
        index = {
            "schema_version": 1,
            "collection_key": descriptor["collection_key"],
            "watershed_key": descriptor["watershed_key"],
            "runid": descriptor["runid"],
            "mode": descriptor["mode"],
            "durable_base_uri": base_uri.rstrip("/") + "/",
            "geometry_revision": descriptor["geometry_revision"],
            "scenarios": descriptor["scenarios"],
            "spatial_inputs": spatial_index,
            "parquets": parquet_index,
            "geometries": geometry_index,
            "geotiffs": geotiff_index,
        }
        index_bytes = canonical_json(index)
        index_artifact = _publish_bytes(client, root, "rhessys-capability-index.json", index_bytes)
        if replayed and replay_receipt.get("index_sha256") != index_artifact.digest:
            raise RhessysIntegrityError("replay did not reproduce the RHESSys index")
        receipt = {
            "schema_version": 1,
            "kind": "rhessys-capability-receipt",
            "descriptor_sha256": descriptor_sha256,
            "index_sha256": index_artifact.digest,
            "sources": source_records,
        }
        receipt_bytes = canonical_json(receipt)
        receipt_artifact = _publish_bytes(client, root, "rhessys-source-receipt.json", receipt_bytes)
        return PreparedRhessys(
            index=index,
            receipt=receipt,
            index_bytes=index_bytes,
            receipt_bytes=receipt_bytes,
            index_artifact=index_artifact,
            receipt_artifact=receipt_artifact,
            source_count=len(source_records),
            member_count=1,
            replayed=replayed,
        )
