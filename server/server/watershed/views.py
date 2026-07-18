from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import CharField, F, OuterRef, Subquery, Value
from django.db.models.functions import Cast, Coalesce, Concat
from server.watershed.models import (
    Channel,
    Subcatchment,
    Watershed,
    WatershedRunAlias,
)
from server.watershed.geojson import geojson_response, geojson_feature_response
from server.watershed.identity import resolve_runid, resolve_watershed_key
from server.watershed.runtime_capabilities import capability_summary
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from server.watershed.schema_serializers import (
    WatershedFeatureCollectionSerializer,
    WatershedFeatureSerializer,
    SubcatchmentFeatureCollectionSerializer,
    ChannelFeatureCollectionSerializer,
    NotFoundSerializer,
    SchemaPlaceholderSerializer,
)


class WatershedViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides read-only access to watersheds.
    """
    _properties = (
        'pws_name',
        'county_nam',
        'shape_area',
        'srcname',
        'srctype',
        'owner_type',
        'pop_group',
        'treat_type',
        'huc10_utility_count',
        'huc10_pws_names',
    )
    serializer_class = SchemaPlaceholderSerializer

    @staticmethod
    def _with_identity_properties(queryset):
        current_runid = WatershedRunAlias.objects.filter(
            watershed_identity_id=OuterRef('logical_watershed_id'),
            is_current=True,
        ).values('runid')[:1]
        return queryset.annotate(
            watershed_key=F('logical_watershed__watershed_key'),
            current_runid=Coalesce(
                Subquery(current_runid, output_field=CharField()),
                F('runid'),
            ),
        )

    # No logic changes, only decorating for documentation
    @extend_schema(
        operation_id='watershed_list',
        summary='List watersheds',
        parameters=[
            OpenApiParameter(name='simplified_geom', description='Use simplified geometry', required=False, type=bool),
        ],
        responses={
            200: OpenApiResponse(response=WatershedFeatureCollectionSerializer, description='GeoJSON FeatureCollection of watersheds'),
        },
    )
    def list(self, request, *args, **kwargs):
        """Gets all the available watersheds with the original or simplified geometries (depending on simplified_geom query parameter)"""
        simplified = request.query_params.get('simplified_geom', '').lower() == 'true'
        geo_field = 'simplified_geom' if simplified else 'geom'
        return geojson_response(
            Watershed.objects.all(),
            geo_field=geo_field,
            id_field='runid',
            properties=self._properties,
        )
    
    # No logic changes, only decorating for documentation
    @extend_schema(
        operation_id='watershed_retrieve',
        summary='Retrieve watershed',
        parameters=[
            OpenApiParameter(name='simplified_geom', description='Use simplified geometry', required=False, type=bool),
        ],
        responses={
            200: OpenApiResponse(response=WatershedFeatureSerializer, description='GeoJSON Feature for the requested watershed'),
            404: OpenApiResponse(response=NotFoundSerializer, description='Watershed was not found'),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        """Gets the specified watershed with the original or simplified geometries (depending on simplified_geom query parameter)"""
        simplified = request.query_params.get('simplified_geom', '').lower() == 'true'
        geo_field = 'simplified_geom' if simplified else 'geom'
        watershed = resolve_runid(kwargs['pk'])
        queryset = self._with_identity_properties(
            Watershed.objects.filter(pk=watershed.pk)
        ).annotate(
            route_id=Value(kwargs['pk'], output_field=CharField()),
        )
        return geojson_feature_response(
            queryset,
            geo_field=geo_field,
            id_field='route_id',
            properties=self._properties + ('watershed_key', 'current_runid'),
        )


class WatershedByKeyDetailView(APIView):
    def get(self, request, watershed_key):
        simplified = request.query_params.get('simplified_geom', '').lower() == 'true'
        geo_field = 'simplified_geom' if simplified else 'geom'
        watershed = resolve_watershed_key(watershed_key)
        queryset = WatershedViewSet._with_identity_properties(
            Watershed.objects.filter(pk=watershed.pk)
        ).annotate(
            stable_id=Value(watershed_key, output_field=CharField())
        )
        return geojson_feature_response(
            queryset,
            geo_field=geo_field,
            id_field='stable_id',
            properties=WatershedViewSet._properties
            + ('watershed_key', 'current_runid'),
        )


class WatershedCapabilityView(APIView):
    def get(self, request, runid):
        return Response(capability_summary(runid))

class WatershedSubcatchmentListView(APIView):
    """
    Provides read-only access to collections of subcatchment instances belonging to the watershed specified through URL parameter.
    """
    @extend_schema(
        operation_id='watershed_subcatchments_list',
        summary='List watershed subcatchments',
        responses={
            200: OpenApiResponse(response=SubcatchmentFeatureCollectionSerializer, description='GeoJSON FeatureCollection of subcatchments'),
        },
    )
    def get(self, request, runid):
        try:
            watershed = resolve_runid(runid)
        except NotFound:
            qs = Subcatchment.objects.none()
        else:
            qs = Subcatchment.objects.filter(watershed=watershed)
        return geojson_response(
            qs,
            geo_field='geom',
            properties=(
                'topazid',
                'weppid',
                'slope_scalar',
                'length',
                'width',
                'aspect',
                'hillslope_area',
                'simple_texture',
            ),
        )


class WatershedSubcatchmentByKeyListView(APIView):
    def get(self, request, watershed_key):
        watershed = resolve_watershed_key(watershed_key)
        stable_id = Concat(
            Value(f"subcatchment:{watershed_key}:"),
            Cast('topazid', output_field=CharField()),
            output_field=CharField(),
        )
        queryset = Subcatchment.objects.filter(watershed=watershed).annotate(
            stable_id=stable_id
        )
        return geojson_response(
            queryset,
            geo_field='geom',
            id_field='stable_id',
            properties=(
                'topazid',
                'weppid',
                'slope_scalar',
                'length',
                'width',
                'aspect',
                'hillslope_area',
                'simple_texture',
            ),
        )
    
class WatershedChannelListView(APIView):
    """
    Provides read-only access to collections of channel instances belonging to the watershed specified through URL parameter.
    """
    @extend_schema(
        operation_id='watershed_channels_list',
        summary='List watershed channels',
        responses={
            200: OpenApiResponse(response=ChannelFeatureCollectionSerializer, description='GeoJSON FeatureCollection of channels'),
        },
    )
    def get(self, request, runid):
        try:
            watershed = resolve_runid(runid)
        except NotFound:
            qs = Channel.objects.none()
        else:
            qs = Channel.objects.filter(watershed=watershed)
        return geojson_response(
            qs,
            geo_field='geom',
            properties=(
                'topazid',
                'weppid',
                'order',
            ),
        )


class WatershedChannelByKeyListView(APIView):
    def get(self, request, watershed_key):
        watershed = resolve_watershed_key(watershed_key)
        stable_id = Concat(
            Value(f"channel:{watershed_key}:"),
            Cast('topazid', output_field=CharField()),
            Value(':'),
            Cast('weppid', output_field=CharField()),
            Value(':'),
            Cast('order', output_field=CharField()),
            output_field=CharField(),
        )
        queryset = Channel.objects.filter(watershed=watershed).annotate(
            stable_id=stable_id
        )
        return geojson_response(
            queryset,
            geo_field='geom',
            id_field='stable_id',
            properties=('topazid', 'weppid', 'order'),
        )
