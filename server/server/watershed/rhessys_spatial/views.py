"""
API views for RHESSys spatial input raster data.

Two endpoints:
  GET /api/watershed/<runid>/rhessys/spatial-inputs/
      → list of available GeoTIFFs with metadata (discovery + registry)

  GET /api/watershed/<runid>/rhessys/spatial-inputs/<filename>/tiles/<z>/<x>/<y>.png
      → 256×256 PNG tile with colormap applied
"""

from __future__ import annotations

import rasterio.errors
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from rio_tiler.errors import TileOutsideBounds

from server.watershed.models import RunCapability
from server.watershed.runtime_capabilities import resolve_capability
from .discovery import discover_spatial_inputs, get_download_url
from .schema_serializers import RhessysSpatialListResponseSerializer
from .registry import get_meta, get_render_range
from .tile import get_tile_png
from .colormap import (
    get_continuous_legend_stops,
    get_categorical_legend,
)


class RhessysSpatialListView(APIView):
    """Discover available RHESSys spatial input GeoTIFFs for a watershed.

    Probes the WEPPcloud file browser for the given runid and returns
    metadata for every .tif file found.  Returns an empty list (200) if
    the watershed has no RHESSys data.
    """

    @extend_schema(
        operation_id='watershed_rhessys_spatial_inputs_retrieve',
        summary='List RHESSys spatial inputs',
        responses={
            200: OpenApiResponse(response=RhessysSpatialListResponseSerializer, description='List of available RHESSys spatial input layers'),
        },
    )
    def get(self, request, runid: str):
        capability = resolve_capability(runid, RunCapability.CapabilityType.RHESSYS)
        if not capability.available or capability.mode not in {
            RunCapability.Mode.DYNAMIC,
            RunCapability.Mode.BOTH,
        }:
            return Response({"files": [], "capability": {"available": False}})
        if capability.source == "materialized":
            files = []
            for item in capability.configuration["spatial_inputs"]:
                render = item["render"]
                files.append(
                    {
                        "filename": item["filename"],
                        "name": item["title"],
                        **render,
                    }
                )
        else:
            files = discover_spatial_inputs(runid)
        if files is None:
            return Response({"files": [], "capability": {"available": True}})

        for f in files:
            if f["type"] == "categorical" and f.get("unique_values"):
                f["legend"] = get_categorical_legend(f["unique_values"])
            elif f["type"] == "stream":
                f["legend"] = [{"value": 1, "hex": "#00FFFF"}]
            elif f["type"] == "continuous" and f.get("min") is not None:
                f["legend"] = get_continuous_legend_stops(
                    f["min"], f["max"], reversed=f.get("reversed", False),
                )
            else:
                f["legend"] = None

        return Response(
            {
                "files": files,
                "capability": {
                    "available": True,
                    "source": capability.source,
                    "mode": capability.mode,
                    "geometry_revision": capability.geometry_revision,
                },
            }
        )


class RhessysSpatialTileView(APIView):
    """Return a 256×256 PNG map tile for a RHESSys spatial input GeoTIFF.

    URL params:
        runid: Watershed run identifier.
        filename: GeoTIFF filename (e.g. ``wbt_slope.tif``). Must be present
            in the static registry; unknown filenames return 404.
        z, x, y: Web Mercator tile coordinates.
    """

    @extend_schema(
        operation_id='watershed_rhessys_spatial_inputs_tiles_png_retrieve',
        summary='Get RHESSys spatial input tile PNG',
        responses={
            (200, 'image/png'): OpenApiResponse(response=OpenApiTypes.BINARY, description='256x256 PNG tile'),
        },
    )
    def get(self, request, runid: str, filename: str, z: int, x: int, y: int):
        capability = resolve_capability(runid, RunCapability.CapabilityType.RHESSYS)
        if not capability.available or capability.mode not in {
            RunCapability.Mode.DYNAMIC,
            RunCapability.Mode.BOTH,
        }:
            raise NotFound("RHESSys spatial input is not enabled for this watershed.")
        if capability.source == "materialized":
            item = next(
                (
                    candidate
                    for candidate in capability.configuration["spatial_inputs"]
                    if candidate["filename"] == filename
                ),
                None,
            )
            if item is None:
                raise NotFound("RHESSys spatial input is not declared.")
            tif_url = item["artifact"]["uri"]
            render = item["render"]
            kwargs = dict(
                data_type=render["type"],
                min_val=render["min"] if render["min"] is not None else 0.0,
                max_val=render["max"] if render["max"] is not None else 1.0,
                unique_values=render["unique_values"],
                reversed_colormap=render["reversed"],
            )
        else:
            tif_url = get_download_url(runid, filename)
            meta = get_meta(filename)
            if not meta:
                raise NotFound(
                    "RHESSys spatial input is not registered in the legend registry."
                )
            lo, hi = get_render_range(meta)
            kwargs = dict(
                data_type=meta.data_type,
                min_val=lo,
                max_val=hi,
                unique_values=meta.unique_values,
                reversed_colormap=meta.reversed_colormap,
            )

        try:
            png_bytes = get_tile_png(tif_url, z, x, y, **kwargs)
        except TileOutsideBounds:
            raise NotFound("Tile is outside the bounds of this raster.")
        except rasterio.errors.RasterioIOError:
            raise NotFound(
                "RHESSys spatial input not found or not available for this watershed."
            )

        return HttpResponse(png_bytes, content_type="image/png")
