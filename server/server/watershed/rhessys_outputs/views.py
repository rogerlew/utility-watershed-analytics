"""
API views for RHESSys output map data.

Three endpoints:
  GET /api/watershed/<runid>/rhessys/outputs
      → list of available scenarios and variables with legend metadata

  GET /api/watershed/<runid>/rhessys/outputs/<scenario>/<variable>/tiles/<z>/<x>/<y>.png
      → 256×256 PNG tile with appropriate colormap

  GET /api/watershed/<runid>/rhessys/outputs/geometry/<scale>
      → Proxy for hillslope/patch GeoJSON from WEPPcloud (avoids CORS)
"""

from __future__ import annotations

import json
import logging
import struct
import zlib

import rasterio.errors
import requests
from cachetools import TTLCache
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from rio_tiler.errors import TileOutsideBounds

from server.watershed.legacy_runtime import (
    LEGACY_DYNAMIC_SCENARIOS,
    LEGACY_DYNAMIC_VARIABLES,
    legacy_geometry_path,
)
from server.watershed.loaders.config import resolve_run_base_url
from server.watershed.models import RunCapability
from server.watershed.runtime_capabilities import (
    RuntimeCapabilityError,
    fetch_verified_artifact,
    resolve_capability,
)
from .discovery import discover_output_maps, get_map_download_url
from .schema_serializers import RhessysOutputListResponseSerializer
from .registry import get_variable, is_change_scenario
from .tile import get_tile_png
from .query import RhessysQueryError, execute_legacy_query, execute_materialized_query


def _build_transparent_png(width: int = 256, height: int = 256) -> bytes:
    """Build a minimal fully-transparent RGBA PNG with no external deps."""
    raw_row = b"\x00" + b"\x00\x00\x00\x00" * width  # filter-byte + RGBA
    raw = raw_row * height
    compressed = zlib.compress(raw)

    def _chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", compressed)
        + _chunk(b"IEND", b"")
    )


_TRANSPARENT_TILE_BYTES: bytes = _build_transparent_png()

logger = logging.getLogger("watershed.rhessys_outputs")


class RhessysOutputListView(APIView):
    """Discover available RHESSys output map products for a watershed."""

    @extend_schema(
        operation_id='watershed_rhessys_outputs_retrieve',
        summary='List RHESSys output map scenarios and variables',
        responses={
            200: OpenApiResponse(
                response=RhessysOutputListResponseSerializer,
                description='Available RHESSys output maps',
            ),
        },
    )
    def get(self, request, runid: str):
        capability = resolve_capability(runid, RunCapability.CapabilityType.RHESSYS)
        if not capability.available:
            return Response(
                {
                    "scenarios": [],
                    "variables": [],
                    "value_ranges": {},
                    "capability": {"available": False},
                }
            )
        supports_dynamic = capability.mode in {
            RunCapability.Mode.DYNAMIC,
            RunCapability.Mode.BOTH,
        }
        supports_precomputed = capability.mode in {
            RunCapability.Mode.PRECOMPUTED,
            RunCapability.Mode.BOTH,
        }
        if capability.source == "materialized":
            configuration = capability.configuration
            value_ranges = {}
            variable_scales = {
                variable["id"]: set() for variable in configuration["variables"]
            }
            for parquet in configuration["parquets"]:
                scale = "patch" if parquet["role"] == "patch" else "hillslope"
                for variable in parquet["variables"]:
                    variable_scales[variable["id"]].add(scale)
            for item in configuration["geotiffs"]:
                if item["value_range"] is not None:
                    value_ranges.setdefault(item["scenario"], {})[item["variable"]] = item[
                        "value_range"
                    ]
            catalog = {
                "scenarios": configuration["scenarios"],
                "variables": [
                    {
                        **variable,
                        "spatial_scales": sorted(variable_scales[variable["id"]]),
                    }
                    for variable in configuration["variables"]
                ],
                "value_ranges": value_ranges,
            }
        elif supports_dynamic:
            catalog = {
                "scenarios": LEGACY_DYNAMIC_SCENARIOS,
                "variables": LEGACY_DYNAMIC_VARIABLES,
                "value_ranges": {},
            }
        else:
            catalog = discover_output_maps(runid)
        if catalog is None:
            catalog = {"scenarios": [], "variables": [], "value_ranges": {}}

        return Response(
            {
                **catalog,
                "capability": {
                    "available": True,
                    "source": capability.source,
                    "mode": capability.mode,
                    "supports_dynamic": supports_dynamic,
                    "supports_precomputed": supports_precomputed,
                    "index_uri": capability.index_uri,
                    "index_sha256": capability.index_sha256,
                    "geometry_revision": capability.geometry_revision,
                    "access_policy": capability.access_policy,
                },
            }
        )


class RhessysOutputQueryView(APIView):
    def post(self, request, runid: str):
        capability = resolve_capability(runid, RunCapability.CapabilityType.RHESSYS)
        if not capability.available or capability.mode not in {
            RunCapability.Mode.DYNAMIC,
            RunCapability.Mode.BOTH,
        }:
            raise NotFound("Dynamic RHESSys data is not enabled for this watershed.")
        try:
            if capability.source == "materialized":
                rows = execute_materialized_query(capability, request.data)
            else:
                rows = execute_legacy_query(runid, request.data)
        except RhessysQueryError as error:
            raise NotFound(str(error))
        return Response({"rows": rows})


class RhessysOutputTileView(APIView):
    """Return a 256×256 PNG map tile for a RHESSys output GeoTIFF."""

    @extend_schema(
        operation_id='watershed_rhessys_outputs_tiles_png_retrieve',
        summary='Get RHESSys output map tile PNG',
        responses={
            (200, 'image/png'): OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description='256x256 PNG tile',
            ),
        },
    )
    def get(
        self,
        request,
        runid: str,
        scenario: str,
        variable: str,
        z: int,
        x: int,
        y: int,
    ):
        capability = resolve_capability(runid, RunCapability.CapabilityType.RHESSYS)
        if not capability.available or capability.mode not in {
            RunCapability.Mode.PRECOMPUTED,
            RunCapability.Mode.BOTH,
        }:
            raise NotFound("RHESSys output maps are not enabled for this watershed.")
        if capability.source == "materialized":
            asset = next(
                (
                    item
                    for item in capability.configuration["geotiffs"]
                    if item["scenario"] == scenario and item["variable"] == variable
                ),
                None,
            )
            if asset is None:
                raise NotFound("RHESSys output map is not declared.")
            tif_url = asset["artifact"]["uri"]
            scenario_meta = next(
                item
                for item in capability.configuration["scenarios"]
                if item["id"] == scenario
            )
            change = scenario_meta["is_change"]
        else:
            var_meta = get_variable(variable)
            if not var_meta:
                raise NotFound(f"Unknown RHESSys output variable: {variable}")
            tif_url = get_map_download_url(runid, scenario, var_meta.filename)
            change = is_change_scenario(scenario)

        try:
            png_bytes = get_tile_png(tif_url, z, x, y, is_change=change)
        except TileOutsideBounds:
            return HttpResponse(
                _TRANSPARENT_TILE_BYTES, content_type="image/png"
            )
        except rasterio.errors.RasterioIOError:
            raise NotFound(
                "RHESSys output map not found or not available for this watershed."
            )

        return HttpResponse(png_bytes, content_type="image/png")


# In-memory cache: (runid, scale, geometry_revision) → reprojected GeoJSON bytes.
# geometry_revision is None for hillslope; for patch it is "1985" or "2021" so
# scenarios that share the same file (e.g. S2 and S4b → 2021) share one entry.
_geometry_cache: TTLCache[tuple[str, str, str | None], bytes] = TTLCache(maxsize=20, ttl=3600)


def _reproject_geojson(geojson: dict) -> dict:
    """Reproject a GeoJSON FeatureCollection to WGS84 (EPSG:4326).

    The upstream GeoJSON files are vectorised rasters in projected CRS
    (typically EPSG:26910 / UTM Zone 10N).  Leaflet requires WGS84.
    """
    from pyproj import Transformer

    crs_info = geojson.get("crs", {})
    crs_name = (
        crs_info.get("properties", {}).get("name", "")
        if isinstance(crs_info, dict)
        else ""
    )

    # Extract EPSG code from URN like "urn:ogc:def:crs:EPSG::26910"
    src_epsg = None
    if "EPSG" in crs_name:
        parts = crs_name.split(":")
        for i, part in enumerate(parts):
            if part == "EPSG" and i + 1 < len(parts):
                code = parts[-1]
                if code.isdigit():
                    src_epsg = int(code)
                    break

    if not src_epsg or src_epsg == 4326:
        # Already WGS84 or no CRS info — return as-is
        geojson.pop("crs", None)
        return geojson

    transformer = Transformer.from_crs(
        f"EPSG:{src_epsg}", "EPSG:4326", always_xy=True,
    )

    def transform_coords(coords):
        """Recursively transform coordinate arrays."""
        if isinstance(coords[0], (int, float)):
            x, y = transformer.transform(coords[0], coords[1])
            return [x, y] + coords[2:]
        return [transform_coords(c) for c in coords]

    for feature in geojson.get("features", []):
        geom = feature.get("geometry", {})
        if "coordinates" in geom:
            geom["coordinates"] = transform_coords(geom["coordinates"])

    geojson.pop("crs", None)
    return geojson


class RhessysOutputGeometryView(APIView):
    """Proxy hillslope/patch GeoJSON from WEPPcloud, reprojected to WGS84.

    The upstream GeoJSON files are in a projected CRS (EPSG:26910 UTM 10N)
    and the WEPPcloud download endpoint lacks CORS headers.  This view
    fetches the GeoJSON server-side, reprojects coordinates to WGS84 for
    Leaflet, and serves the result with proper headers.
    """

    @extend_schema(
        operation_id='watershed_rhessys_outputs_geometry_retrieve',
        summary='Get RHESSys hillslope/patch GeoJSON geometry (WGS84)',
        parameters=[
            OpenApiParameter(
                name='scenario',
                required=False,
                type=str,
                description=(
                    'Capability-declared RHESSys scenario id selecting the '
                    'matching geometry revision.'
                ),
            ),
        ],
        responses={
            (200, 'application/geo+json'): OpenApiResponse(
                description='GeoJSON FeatureCollection in WGS84',
            ),
        },
    )
    def get(self, request, runid: str, scale: str):
        scenario = request.query_params.get("scenario")
        capability = resolve_capability(runid, RunCapability.CapabilityType.RHESSYS)
        if not capability.available or capability.mode not in {
            RunCapability.Mode.DYNAMIC,
            RunCapability.Mode.BOTH,
        }:
            raise NotFound("RHESSys geometry is not enabled for this watershed.")
        reference = None
        source_crs = None
        if capability.source == "materialized":
            geometry = next(
                (
                    item
                    for item in capability.configuration["geometries"]
                    if item["scale"] == scale
                    and (scenario is None or scenario in item["scenarios"])
                ),
                None,
            )
            if geometry is None:
                raise NotFound("RHESSys geometry is not declared.")
            geometry_revision = geometry["geometry_revision"]
            reference = geometry["artifact"]
            source_crs = geometry["source_crs"]
        else:
            try:
                geojson_path, geometry_revision = legacy_geometry_path(scale, scenario)
            except KeyError:
                raise NotFound(
                    f"Unknown spatial scale: {scale}. Use 'hillslope' or 'patch'."
                )

        cache_key = (runid, scale, geometry_revision)
        cached = _geometry_cache.get(cache_key)
        if cached is not None:
            return HttpResponse(cached, content_type="application/geo+json")

        if reference is not None:
            try:
                geojson = json.loads(fetch_verified_artifact(reference))
            except (RuntimeCapabilityError, UnicodeDecodeError, json.JSONDecodeError):
                raise NotFound("Declared RHESSys geometry is unavailable or invalid.")
            if source_crs != "EPSG:4326":
                geojson["crs"] = {
                    "type": "name",
                    "properties": {"name": f"urn:ogc:def:crs:{source_crs.replace(':', '::')}"},
                }
        else:
            base = resolve_run_base_url(runid)
            url = f"{base}/download/{geojson_path}"
            try:
                resp = requests.get(url, timeout=60)
            except requests.RequestException as exc:
                logger.warning(
                    "Failed to fetch geometry for runid=%s scale=%s: %s",
                    runid,
                    scale,
                    exc,
                )
                raise NotFound("Failed to fetch geometry from WEPPcloud.")
            if resp.status_code != 200:
                raise NotFound(
                    f"Geometry not available for this watershed (upstream returned {resp.status_code})."
                )
            geojson = resp.json()
        reprojected = _reproject_geojson(geojson)
        body = json.dumps(reprojected).encode("utf-8")

        _geometry_cache[cache_key] = body

        return HttpResponse(body, content_type="application/geo+json")
