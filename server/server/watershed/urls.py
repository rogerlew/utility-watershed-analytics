from rest_framework import routers
from django.urls import path, include
from server.watershed.views import (
    WatershedByKeyDetailView,
    WatershedChannelByKeyListView,
    WatershedChannelListView,
    WatershedCapabilityView,
    WatershedSubcatchmentByKeyListView,
    WatershedSubcatchmentListView,
    WatershedViewSet,
)
from server.watershed.sbs_raster.views import SbsColormapView, SbsRasterDownloadView, SbsRasterTileView
from server.watershed.rhessys_spatial.views import RhessysSpatialListView, RhessysSpatialTileView
from server.watershed.rhessys_outputs.views import RhessysOutputListView, RhessysOutputTileView, RhessysOutputGeometryView, RhessysOutputQueryView

# Use router to automatically manage API endpoints based on registered viewsets
router = routers.DefaultRouter()
router.register('', WatershedViewSet, basename='watershed')

# Make router routes accessible to project URL configuration
urlpatterns = [
    path(
        'by-key/<str:watershed_key>/',
        WatershedByKeyDetailView.as_view(),
        name='watershed-by-key',
    ),
    path(
        'by-key/<str:watershed_key>/subcatchments',
        WatershedSubcatchmentByKeyListView.as_view(),
        name='watershed-subcatchments-by-key',
    ),
    path(
        'by-key/<str:watershed_key>/channels',
        WatershedChannelByKeyListView.as_view(),
        name='watershed-channels-by-key',
    ),
    path('', include(router.urls)),
    path('<str:runid>/subcatchments', WatershedSubcatchmentListView.as_view(), name='watershed-subcatchments'),
    path('<str:runid>/channels', WatershedChannelListView.as_view(), name='watershed-channels'),
    path('<str:runid>/capabilities', WatershedCapabilityView.as_view(), name='watershed-capabilities'),
    path('sbs/colormap', SbsColormapView.as_view(), name='sbs-colormap'),
    path('<str:runid>/sbs/tiles/<int:z>/<int:x>/<int:y>.png', SbsRasterTileView.as_view(), name='sbs-tile'),
    path('<str:runid>/sbs/download', SbsRasterDownloadView.as_view(), name='sbs-download'),
    path('<str:runid>/rhessys/spatial-inputs', RhessysSpatialListView.as_view(), name='rhessys-spatial-list'),
    path(
        '<str:runid>/rhessys/spatial-inputs/<str:filename>/tiles/<int:z>/<int:x>/<int:y>.png',
        RhessysSpatialTileView.as_view(),
        name='rhessys-spatial-tile',
    ),
    path('<str:runid>/rhessys/outputs', RhessysOutputListView.as_view(), name='rhessys-outputs-list'),
    path('<str:runid>/rhessys/query', RhessysOutputQueryView.as_view(), name='rhessys-query'),
    path(
        '<str:runid>/rhessys/outputs/<str:scenario>/<str:variable>/tiles/<int:z>/<int:x>/<int:y>.png',
        RhessysOutputTileView.as_view(),
        name='rhessys-outputs-tile',
    ),
    path(
        '<str:runid>/rhessys/outputs/geometry/<str:scale>',
        RhessysOutputGeometryView.as_view(),
        name='rhessys-outputs-geometry',
    ),
]
