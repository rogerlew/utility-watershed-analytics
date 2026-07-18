import rasterio.errors
import requests

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from rio_tiler.errors import TileOutsideBounds

from server.watershed.sbs_raster.color_map import ColorMode, get_colormap_metadata
from server.watershed.sbs_raster.schema_serializers import SbsColormapResponseSerializer
from server.watershed.sbs_raster.tile import get_tile_png
from server.watershed.loaders.config import resolve_run_base_url
from server.watershed.models import RunCapability
from server.watershed.runtime_capabilities import (
    RuntimeCapabilityError,
    fetch_verified_artifact,
    resolve_capability,
)


class SbsColormapView(APIView):
    """
    Returns SBS colormap metadata for the requested color mode.

    The backend is the single source of truth for all SBS color definitions.
    Both tile rendering and frontend legend/toggle consume this data so they
    always agree.

    Query params:
        mode (str): "legacy" (default) or "shift" (Okabe-Ito colorblind-safe).
    """

    @extend_schema(
        operation_id='watershed_sbs_colormap_retrieve',
        summary='Get SBS colormap metadata',
        parameters=[
            OpenApiParameter(
                name='mode',
                description='Color mode: "legacy" or "shift" (Okabe-Ito)',
                required=False,
                type=str,
                enum=[m.value for m in ColorMode],
            ),
        ],
        responses={
            200: OpenApiResponse(response=SbsColormapResponseSerializer, description='SBS color map metadata for the selected mode'),
        },
    )
    def get(self, request):
        raw_mode = request.query_params.get('mode', ColorMode.LEGACY.value)
        try:
            mode = ColorMode(raw_mode)
        except ValueError:
            mode = ColorMode.LEGACY

        return Response({
            'mode': mode.value,
            'entries': get_colormap_metadata(mode),
        })


class SbsRasterTileView(APIView):
    """
    Returns a 256×256 PNG map tile for the SBS raster at Web Mercator tile
    coords (z, x, y).

    Intended for use as a slippy-map TileLayer URL template, e.g.:
        /api/watershed/{runid}/sbs/tiles/{z}/{x}/{y}.png?mode=shift

    URL params:
        runid: Watershed run identifier.
        z, x, y: Web Mercator tile coordinates.

    Query params:
        mode (str): "legacy" (default) or "shift" (Okabe-Ito colorblind-safe).
    """

    @extend_schema(
        operation_id='watershed_sbs_tiles_png_retrieve',
        summary='Get SBS raster tile PNG',
        parameters=[
            OpenApiParameter(
                name='mode',
                description='Color mode: "legacy" or "shift" (Okabe-Ito)',
                required=False,
                type=str,
                enum=[m.value for m in ColorMode],
            ),
        ],
        responses={
            (200, 'image/png'): OpenApiResponse(response=OpenApiTypes.BINARY, description='256x256 PNG tile'),
        },
    )
    def get(self, request, runid: str, z: int, x: int, y: int):
        raw_mode = request.query_params.get('mode', ColorMode.LEGACY.value)
        try:
            mode = ColorMode(raw_mode)
        except ValueError:
            mode = ColorMode.LEGACY

        capability = resolve_capability(runid, RunCapability.CapabilityType.SBS)
        if not capability.available:
            raise NotFound("SBS raster is not enabled for this watershed.")
        if capability.source == "materialized":
            tif_url = capability.configuration["artifact"]["uri"]
        else:
            run_base = resolve_run_base_url(runid)
            tif_url = f"{run_base}/download/disturbed/sbs_4class.tif"

        try:
            png_bytes = get_tile_png(tif_url, z, x, y, mode)
        except TileOutsideBounds:
            raise NotFound("Tile is outside the bounds of this raster.")
        except rasterio.errors.RasterioIOError:
            raise NotFound("SBS raster data not found or not available for this watershed.")

        return HttpResponse(png_bytes, content_type='image/png')


class SbsRasterDownloadView(APIView):
    def get(self, request, runid: str):
        capability = resolve_capability(runid, RunCapability.CapabilityType.SBS)
        if not capability.available:
            raise NotFound("SBS raster is not enabled for this watershed.")
        if capability.source == "materialized":
            try:
                content = fetch_verified_artifact(capability.configuration["artifact"])
            except RuntimeCapabilityError:
                raise NotFound("Declared SBS raster is unavailable or invalid.")
            response = HttpResponse(content, content_type="image/tiff")
            response["Content-Disposition"] = 'attachment; filename="sbs_4class.tif"'
            return response
        run_base = resolve_run_base_url(runid)
        try:
            response = requests.get(
                f"{run_base}/download/disturbed/sbs_4class.tif",
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException:
            raise NotFound("Legacy SBS raster is unavailable.")
        result = HttpResponse(response.content, content_type="image/tiff")
        result["Content-Disposition"] = 'attachment; filename="sbs_4class.tif"'
        return result
