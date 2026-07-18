import uuid

from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator


stable_key_validator = RegexValidator(
    regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    message="Use a lowercase ASCII kebab-case stable key.",
)
sha256_validator = RegexValidator(
    regex=r"^[a-f0-9]{64}$",
    message="Use a lowercase SHA-256 digest.",
)
release_id_validator = RegexValidator(
    regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\.[1-9][0-9]*$",
    message="Use the version-1 YYYY-MM-DD.N release ID.",
)
git_commit_validator = RegexValidator(regex=r"^[a-f0-9]{40}$")
image_digest_validator = RegexValidator(regex=r"^sha256:[a-f0-9]{64}$")
https_validator = URLValidator(schemes=("https",))


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


class DataRelease(models.Model):
    class Status(models.TextChoices):
        VALIDATED = "validated", "Validated"
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"

    release_id = models.CharField(
        primary_key=True,
        max_length=32,
        validators=[release_id_validator],
    )
    manifest_sha256 = models.CharField(
        max_length=64,
        unique=True,
        validators=[sha256_validator],
    )
    release_fingerprint = models.CharField(
        max_length=64,
        validators=[sha256_validator],
    )
    domain_fingerprint = models.CharField(
        max_length=64,
        validators=[sha256_validator],
    )
    schema_version = models.PositiveSmallIntegerField(default=1)
    data_contract = models.PositiveSmallIntegerField(default=1)
    identity_contract = models.PositiveSmallIntegerField(default=1)
    artifact_contract = models.PositiveSmallIntegerField(default=1)
    fingerprint_version = models.PositiveSmallIntegerField(default=1)
    supported_migration = models.CharField(max_length=128)
    materializer_image_digest = models.CharField(
        max_length=71,
        validators=[image_digest_validator],
    )
    materializer_git_commit = models.CharField(
        max_length=40,
        validators=[git_commit_validator],
    )
    previous_release = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="successor_releases",
    )
    expected_watersheds = models.PositiveIntegerField()
    expected_subcatchments = models.PositiveIntegerField()
    expected_channels = models.PositiveIntegerField()
    actual_watersheds = models.PositiveIntegerField()
    actual_subcatchments = models.PositiveIntegerField()
    actual_channels = models.PositiveIntegerField()
    validation_summary = models.JSONField(default=dict)
    created_at = models.DateTimeField()
    first_activated_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.VALIDATED,
    )

    immutable_fields = (
        "manifest_sha256",
        "release_fingerprint",
        "domain_fingerprint",
        "schema_version",
        "data_contract",
        "identity_contract",
        "artifact_contract",
        "fingerprint_version",
        "supported_migration",
        "materializer_image_digest",
        "materializer_git_commit",
        "previous_release_id",
        "expected_watersheds",
        "expected_subcatchments",
        "expected_channels",
        "actual_watersheds",
        "actual_subcatchments",
        "actual_channels",
        "validation_summary",
        "created_at",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    schema_version=1,
                    data_contract=1,
                    identity_contract=1,
                    artifact_contract=1,
                    fingerprint_version=1,
                ),
                name="release_supported_contracts",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("validated", "active", "superseded")
                ),
                name="release_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    manifest_sha256__regex=r"^[a-f0-9]{64}$",
                    release_fingerprint__regex=r"^[a-f0-9]{64}$",
                    domain_fingerprint__regex=r"^[a-f0-9]{64}$",
                    materializer_image_digest__regex=r"^sha256:[a-f0-9]{64}$",
                    materializer_git_commit__regex=r"^[a-f0-9]{40}$",
                ),
                name="release_coordinates_format",
            ),
            models.UniqueConstraint(
                fields=("status",),
                condition=models.Q(status="active"),
                name="release_one_active_status",
            ),
        ]

    def clean(self):
        super().clean()
        if self.previous_release_id == self.release_id:
            raise ValidationError("A release cannot be its own predecessor.")

    def save(self, *args, **kwargs):
        if not self._state.adding:
            lifecycle_fields = ("status", "first_activated_at")
            original = type(self).objects.values(
                *self.immutable_fields,
                *lifecycle_fields,
            ).get(pk=self.pk)
            changed = [
                field
                for field in self.immutable_fields
                if original[field] != getattr(self, field)
            ]
            if changed:
                raise ValidationError(
                    f"Immutable release fields changed: {', '.join(changed)}"
                )
            lifecycle_changed = any(
                original[field] != getattr(self, field) for field in lifecycle_fields
            )
            if lifecycle_changed and not getattr(
                self, "_allow_lifecycle_change", False
            ):
                raise ValidationError(
                    "Release lifecycle changes require the activation helper."
                )
        self.full_clean()
        super().save(*args, **kwargs)


class ActiveDataRelease(models.Model):
    class State(models.TextChoices):
        EMPTY = "EMPTY", "Empty"
        ACTIVE = "ACTIVE", "Active"

    singleton_id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    state = models.CharField(
        max_length=8,
        choices=State.choices,
        default=State.EMPTY,
    )
    release = models.OneToOneField(
        DataRelease,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="active_pointer",
    )
    manifest_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[sha256_validator],
    )
    data_contract = models.PositiveSmallIntegerField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(singleton_id=1),
                name="active_release_singleton_id",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        state="EMPTY",
                        release__isnull=True,
                        manifest_sha256__isnull=True,
                        data_contract__isnull=True,
                        activated_at__isnull=True,
                    )
                    | models.Q(
                        state="ACTIVE",
                        release__isnull=False,
                        manifest_sha256__isnull=False,
                        data_contract__isnull=False,
                        activated_at__isnull=False,
                    )
                ),
                name="active_release_state_coherent",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(manifest_sha256__isnull=True)
                    | models.Q(manifest_sha256__regex=r"^[a-f0-9]{64}$")
                ),
                name="active_release_manifest_format",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            original = type(self).objects.values(
                "state",
                "release_id",
                "manifest_sha256",
                "data_contract",
                "activated_at",
            ).get(pk=self.pk)
            changed = any(
                original[field] != getattr(self, field)
                for field in original
            )
            if changed and not getattr(self, "_allow_activation_change", False):
                raise ValidationError(
                    "Active release changes require the activation helper."
                )
        self.full_clean()
        super().save(*args, **kwargs)


class DataReleaseAttempt(models.Model):
    class ActorKind(models.TextChoices):
        OPERATOR = "operator", "Operator"
        WORKFLOW = "workflow", "Workflow"

    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        STAGING = "staging", "Staging"
        APPLYING = "applying", "Applying"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        ROLLED_BACK = "rolled_back", "Rolled back"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    release = models.ForeignKey(
        DataRelease,
        on_delete=models.PROTECT,
        related_name="attempts",
    )
    previous_active_release = models.ForeignKey(
        DataRelease,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="successor_attempts",
    )
    actor_kind = models.CharField(max_length=16, choices=ActorKind.choices)
    actor_identifier = models.CharField(max_length=255)
    target_environment = models.CharField(max_length=32)
    application_git_commit = models.CharField(
        max_length=40,
        validators=[git_commit_validator],
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PLANNING,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reviewed_plan_sha256 = models.CharField(
        max_length=64,
        validators=[sha256_validator],
    )
    actual_plan_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[sha256_validator],
    )
    lease_owner = models.CharField(max_length=255)
    lease_heartbeat_at = models.DateTimeField()
    lease_expires_at = models.DateTimeField()
    lease_active = models.BooleanField(default=True)
    backup_artifact_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[sha256_validator],
    )
    failure_phase = models.CharField(max_length=64, null=True, blank=True)
    failure_summary = models.CharField(max_length=512, null=True, blank=True)
    deployment_report_uri = models.CharField(
        max_length=2048,
        null=True,
        blank=True,
        validators=[https_validator],
    )
    deployment_report_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[sha256_validator],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(actor_kind__in=("operator", "workflow")),
                name="attempt_actor_kind_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "planning",
                        "staging",
                        "applying",
                        "succeeded",
                        "failed",
                        "rolled_back",
                    )
                ),
                name="attempt_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(lease_expires_at__gt=models.F("lease_heartbeat_at")),
                name="attempt_lease_window_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        deployment_report_uri__isnull=True,
                        deployment_report_sha256__isnull=True,
                    )
                    | models.Q(
                        deployment_report_uri__startswith="https://",
                        deployment_report_sha256__regex=r"^[a-f0-9]{64}$",
                    )
                ),
                name="attempt_report_reference_coherent",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=("planning", "staging", "applying"),
                        completed_at__isnull=True,
                    )
                    | models.Q(
                        status__in=("succeeded", "failed", "rolled_back"),
                        completed_at__isnull=False,
                        lease_active=False,
                    )
                ),
                name="attempt_terminal_state_coherent",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="failed",
                        failure_phase__isnull=False,
                        failure_summary__isnull=False,
                    )
                    | ~models.Q(status="failed")
                ),
                name="attempt_failure_details_present",
            ),
            models.UniqueConstraint(
                fields=("lease_active",),
                condition=models.Q(lease_active=True),
                name="attempt_one_active_lease",
            ),
        ]

    @property
    def lease_expired(self):
        from django.utils import timezone

        return self.lease_active and self.lease_expires_at <= timezone.now()

    def save(self, *args, **kwargs):
        from server.watershed.release_ledger import sanitize_failure_summary

        if self.failure_summary:
            self.failure_summary = sanitize_failure_summary(self.failure_summary)
        self.full_clean()
        super().save(*args, **kwargs)


class DataRunState(models.Model):
    class ValidationStatus(models.TextChoices):
        VALIDATED = "validated", "Validated"
        REJECTED = "rejected", "Rejected"

    release = models.ForeignKey(
        DataRelease,
        on_delete=models.PROTECT,
        related_name="run_states",
    )
    collection = models.ForeignKey(
        WatershedCollection,
        on_delete=models.PROTECT,
        related_name="release_run_states",
    )
    watershed_identity = models.ForeignKey(
        WatershedIdentity,
        on_delete=models.PROTECT,
        related_name="release_run_states",
    )
    runid = models.CharField(max_length=255)
    run_fingerprint = models.CharField(max_length=64, validators=[sha256_validator])
    metadata_fingerprint = models.CharField(
        max_length=64, validators=[sha256_validator]
    )
    geometry_fingerprint = models.CharField(
        max_length=64, validators=[sha256_validator]
    )
    subcatchment_fingerprint = models.CharField(
        max_length=64, validators=[sha256_validator]
    )
    channel_fingerprint = models.CharField(
        max_length=64, validators=[sha256_validator]
    )
    hillslope_fingerprint = models.CharField(
        max_length=64, validators=[sha256_validator]
    )
    soil_fingerprint = models.CharField(max_length=64, validators=[sha256_validator])
    landuse_fingerprint = models.CharField(
        max_length=64, validators=[sha256_validator]
    )
    transformation_lineage_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[sha256_validator],
    )
    capability_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[sha256_validator],
    )
    actual_watersheds = models.PositiveIntegerField(default=1)
    actual_subcatchments = models.PositiveIntegerField()
    actual_channels = models.PositiveIntegerField()
    validation_status = models.CharField(
        max_length=16,
        choices=ValidationStatus.choices,
        default=ValidationStatus.VALIDATED,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("release", "watershed_identity"),
                name="run_state_release_watershed_uniq",
            ),
            models.UniqueConstraint(
                fields=("release", "runid"),
                name="run_state_release_runid_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(actual_watersheds=1),
                name="run_state_one_watershed",
            ),
            models.CheckConstraint(
                condition=models.Q(validation_status__in=("validated", "rejected")),
                name="run_state_validation_status_valid",
            ),
        ]

    def clean(self):
        super().clean()
        if self.watershed_identity_id and self.collection_id:
            identity_collection_id = self.watershed_identity.collection_id
            if identity_collection_id != self.collection_id:
                raise ValidationError(
                    "Run collection must match the logical watershed collection."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DataArtifactLineage(models.Model):
    run_state = models.ForeignKey(
        DataRunState,
        on_delete=models.PROTECT,
        related_name="artifacts",
    )
    role = models.CharField(max_length=64, validators=[stable_key_validator])
    uri = models.CharField(max_length=2048, validators=[https_validator])
    sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    byte_size = models.PositiveBigIntegerField()
    media_type = models.CharField(max_length=255)

    immutable_fields = ("run_state_id", "role", "uri", "sha256", "byte_size", "media_type")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("run_state", "role"),
                name="artifact_run_role_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(uri__startswith="https://"),
                name="artifact_uri_https",
            ),
            models.CheckConstraint(
                condition=models.Q(sha256__regex=r"^[a-f0-9]{64}$"),
                name="artifact_sha256_format",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            original = type(self).objects.values(*self.immutable_fields).get(pk=self.pk)
            if any(
                original[field] != getattr(self, field)
                for field in self.immutable_fields
            ):
                raise ValidationError("Artifact lineage is immutable.")
        self.full_clean()
        super().save(*args, **kwargs)


class RunCapabilityQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(
            run_state__release__active_pointer__state=ActiveDataRelease.State.ACTIVE
        )


class RunCapability(models.Model):
    class CapabilityType(models.TextChoices):
        RHESSYS = "rhessys", "RHESSys"

    class Mode(models.TextChoices):
        DYNAMIC = "dynamic", "Dynamic"
        PRECOMPUTED = "precomputed", "Precomputed"
        BOTH = "both", "Both"

    run_state = models.ForeignKey(
        DataRunState,
        on_delete=models.PROTECT,
        related_name="capabilities",
    )
    watershed_identity = models.ForeignKey(
        WatershedIdentity,
        on_delete=models.PROTECT,
        related_name="release_capabilities",
    )
    capability_type = models.CharField(
        max_length=32,
        choices=CapabilityType.choices,
        default=CapabilityType.RHESSYS,
    )
    mode = models.CharField(max_length=16, choices=Mode.choices)
    durable_base_uri = models.CharField(max_length=2048, validators=[https_validator])
    index_uri = models.CharField(max_length=2048, validators=[https_validator])
    index_sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    capability_fingerprint = models.CharField(
        max_length=64,
        validators=[sha256_validator],
    )
    runtime_configuration = models.JSONField(default=dict)

    objects = RunCapabilityQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("run_state", "capability_type"),
                name="capability_run_type_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(capability_type="rhessys"),
                name="capability_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(mode__in=("dynamic", "precomputed", "both")),
                name="capability_mode_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    durable_base_uri__startswith="https://",
                    index_uri__startswith="https://",
                ),
                name="capability_uris_https",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    index_sha256__regex=r"^[a-f0-9]{64}$",
                    capability_fingerprint__regex=r"^[a-f0-9]{64}$",
                ),
                name="capability_hashes_format",
            ),
        ]

    def clean(self):
        from server.watershed.release_ledger import validate_public_configuration

        super().clean()
        validate_public_configuration(self.runtime_configuration)
        if self.run_state_id and self.watershed_identity_id:
            if self.run_state.watershed_identity_id != self.watershed_identity_id:
                raise ValidationError(
                    "Capability watershed must match its release run state."
                )
            if self.run_state.capability_fingerprint != self.capability_fingerprint:
                raise ValidationError(
                    "Capability fingerprint must match its release run state."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


from server.watershed.staging_models import (  # noqa: E402, F401
    DataReleaseStagingState,
    StagedChannel,
    StagedRunCapability,
    StagedSubcatchment,
    StagedWatershed,
)
