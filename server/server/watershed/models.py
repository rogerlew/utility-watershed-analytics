import uuid

from django.contrib.gis.db import models
from django.core.validators import RegexValidator


stable_key_validator = RegexValidator(
    regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    message="Use a lowercase ASCII kebab-case stable key.",
)


class WatershedCollection(models.Model):
    key = models.CharField(
        primary_key=True,
        max_length=96,
        validators=[stable_key_validator],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(key__regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
                name="collection_key_format",
            ),
        ]


class WatershedIdentity(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    watershed_key = models.CharField(
        max_length=96,
        null=True,
        blank=True,
        unique=True,
        validators=[stable_key_validator],
    )
    collection = models.ForeignKey(
        WatershedCollection,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="watersheds",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(watershed_key__isnull=True)
                    | models.Q(
                        watershed_key__regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
                    )
                ),
                name="watershed_key_format",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("active", "retired")),
                name="watershed_identity_status_valid",
            ),
        ]


class WatershedRunAlias(models.Model):
    runid = models.CharField(primary_key=True, max_length=255)
    watershed_identity = models.ForeignKey(
        WatershedIdentity,
        on_delete=models.PROTECT,
        related_name="run_aliases",
    )
    is_current = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("watershed_identity",),
                condition=models.Q(is_current=True),
                name="watershed_one_current_run_alias",
            ),
        ]

# Represents an individual watershed - the watershed properties and its geometry.
# This is an auto-generated Django model module created by ogrinspect. 
class Watershed(models.Model):
    pws_id = models.CharField(max_length=9, null=True, blank=True)
    srcname = models.CharField(max_length=255, null=True, blank=True)
    pws_name = models.CharField(max_length=255, null=True, blank=True)
    county_nam = models.CharField(max_length=64, null=True, blank=True)
    state = models.CharField(max_length=6, null=True, blank=True)
    huc10_id = models.CharField(max_length=12, null=True, blank=True)
    huc10_name = models.CharField(max_length=128, null=True, blank=True)
    wws_code = models.CharField(max_length=32, null=True, blank=True)
    srctype = models.CharField(max_length=32, null=True, blank=True)
    shape_leng = models.FloatField(null=True, blank=True)
    shape_area = models.FloatField(null=True, blank=True)
    area_km2 = models.FloatField(null=True, blank=True)  # victoria-ca batch
    # Utility metadata (nasa-roses batch, from merged utility data)
    owner_type = models.CharField(max_length=64, null=True, blank=True)   # OwnerType
    pop_group = models.CharField(max_length=64, null=True, blank=True)    # PopGroup – customers served range
    treat_type = models.CharField(max_length=255, null=True, blank=True)  # TreatType – treatment processes
    conn_group = models.CharField(max_length=64, null=True, blank=True)   # ConnGroup – connection group range
    # HUC10-level aggregates: all utilities sharing the same HUC10 boundary
    huc10_pws_names = models.TextField(null=True, blank=True)    # semicolon-delimited names
    huc10_owner_types = models.TextField(null=True, blank=True)
    huc10_pop_groups = models.TextField(null=True, blank=True)
    huc10_treat_types = models.TextField(null=True, blank=True)
    huc10_utility_count = models.IntegerField(null=True, blank=True)
    runid = models.CharField(primary_key=True, max_length=255)
    logical_watershed = models.OneToOneField(
        WatershedIdentity,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="current_watershed",
    )
    geom = models.MultiPolygonField(srid=4326)
    simplified_geom = models.MultiPolygonField(srid=4326, null=True, blank=True)

# This is based on an auto-generated Django model module created by ogrinspect.
class Subcatchment(models.Model):
    watershed = models.ForeignKey(to=Watershed, on_delete=models.CASCADE)
    logical_watershed = models.ForeignKey(
        WatershedIdentity,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="subcatchments",
    )
    topazid = models.IntegerField()
    weppid = models.IntegerField()
    geom = models.MultiPolygonField(srid=4326)
    
    # Hillslope data fields
    slope_scalar = models.FloatField(null=True, blank=True)
    length = models.FloatField(null=True, blank=True)
    width = models.FloatField(null=True, blank=True)
    direction = models.FloatField(null=True, blank=True)
    aspect = models.FloatField(null=True, blank=True)
    hillslope_area = models.IntegerField(null=True, blank=True)
    elevation = models.FloatField(null=True, blank=True)
    centroid_px = models.IntegerField(null=True, blank=True)
    centroid_py = models.IntegerField(null=True, blank=True)
    centroid_lon = models.FloatField(null=True, blank=True)
    centroid_lat = models.FloatField(null=True, blank=True)
    
    # Soil data fields
    mukey = models.CharField(max_length=255, null=True, blank=True)
    soil_fname = models.CharField(max_length=255, null=True, blank=True)
    soils_dir = models.CharField(max_length=255, null=True, blank=True)
    soil_build_date = models.CharField(max_length=255, null=True, blank=True)
    soil_desc = models.TextField(null=True, blank=True)
    soil_color = models.CharField(max_length=50, null=True, blank=True)
    soil_area = models.FloatField(null=True, blank=True)
    soil_pct_coverage = models.FloatField(null=True, blank=True)
    clay = models.FloatField(null=True, blank=True)
    sand = models.FloatField(null=True, blank=True)
    avke = models.FloatField(null=True, blank=True)
    bd = models.FloatField(null=True, blank=True)
    simple_texture = models.CharField(max_length=100, null=True, blank=True)
    soil_depth = models.FloatField(null=True, blank=True)
    rock = models.FloatField(null=True, blank=True)
    
    # Land use data fields
    landuse_key = models.IntegerField(null=True, blank=True)
    landuse_map = models.CharField(max_length=100, null=True, blank=True)
    man_fn = models.CharField(max_length=255, null=True, blank=True)
    man_dir = models.CharField(max_length=255, null=True, blank=True)
    landuse_desc = models.TextField(null=True, blank=True)
    landuse_color = models.CharField(max_length=50, null=True, blank=True)
    landuse_area = models.FloatField(null=True, blank=True)
    landuse_pct_coverage = models.FloatField(null=True, blank=True)
    cancov = models.FloatField(null=True, blank=True)
    inrcov = models.FloatField(null=True, blank=True)
    rilcov = models.FloatField(null=True, blank=True)
    cancov_override = models.FloatField(null=True, blank=True)
    inrcov_override = models.FloatField(null=True, blank=True)
    rilcov_override = models.FloatField(null=True, blank=True)
    disturbed_class = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("watershed", "topazid"),
                name="subcatchment_run_topaz_uniq",
            ),
            models.UniqueConstraint(
                fields=("logical_watershed", "topazid"),
                condition=models.Q(logical_watershed__isnull=False),
                name="subcatchment_logical_topaz_uniq",
            ),
        ]

# This is based on an auto-generated Django model module created by ogrinspect.
class Channel(models.Model):
    watershed = models.ForeignKey(to=Watershed, on_delete=models.CASCADE)
    logical_watershed = models.ForeignKey(
        WatershedIdentity,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="channels",
    )
    topazid = models.IntegerField()
    weppid = models.IntegerField()
    order = models.IntegerField()
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("watershed", "topazid", "weppid", "order"),
                name="channel_run_topaz_wepp_order_uniq",
            ),
            models.UniqueConstraint(
                fields=("logical_watershed", "topazid", "weppid", "order"),
                condition=models.Q(logical_watershed__isnull=False),
                name="channel_logical_topaz_wepp_order_uniq",
            ),
        ]
