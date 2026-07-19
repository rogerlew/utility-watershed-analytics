from django.contrib.gis.db import models
from django.core.exceptions import ValidationError

from server.watershed.models import (
    DataReleaseAttempt,
    DataRunState,
    WatershedIdentity,
    https_validator,
    sha256_validator,
)
from server.watershed.release_ledger import validate_public_configuration


def required_space_expression():
    return (
        models.F("artifact_bytes")
        + models.F("staging_bytes")
        + models.F("index_bytes")
        + models.F("backup_bytes")
        + models.F("wal_bytes")
        + models.F("margin_bytes")
    )


class DataReleaseStagingState(models.Model):
    class Status(models.TextChoices):
        SPACE_REJECTED = "SPACE_REJECTED", "Space rejected"
        LOADING = "LOADING", "Loading"
        READY = "READY", "Ready"
        CLEANUP_PENDING = "CLEANUP_PENDING", "Cleanup pending"
        CLEANED = "CLEANED", "Cleaned"

    attempt = models.OneToOneField(
        DataReleaseAttempt,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="staging_state",
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    artifact_bytes = models.PositiveBigIntegerField()
    staging_bytes = models.PositiveBigIntegerField()
    index_bytes = models.PositiveBigIntegerField()
    backup_bytes = models.PositiveBigIntegerField()
    wal_bytes = models.PositiveBigIntegerField()
    margin_bytes = models.PositiveBigIntegerField()
    available_bytes = models.PositiveBigIntegerField()
    watershed_rows = models.PositiveBigIntegerField(default=0)
    subcatchment_rows = models.PositiveBigIntegerField(default=0)
    channel_rows = models.PositiveBigIntegerField(default=0)
    capability_rows = models.PositiveBigIntegerField(default=0)
    retention_until = models.DateTimeField()
    cleanup_attempts = models.PositiveIntegerField(default=0)
    last_cleanup_error = models.CharField(max_length=512, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "SPACE_REJECTED",
                        "LOADING",
                        "READY",
                        "CLEANUP_PENDING",
                        "CLEANED",
                    )
                ),
                name="staging_state_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="SPACE_REJECTED",
                        available_bytes__lt=required_space_expression(),
                    )
                    | (
                        ~models.Q(status="SPACE_REJECTED")
                        & models.Q(available_bytes__gte=required_space_expression())
                    )
                ),
                name="staging_state_space_outcome",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status__in=("LOADING", "READY", "CLEANUP_PENDING"))
                    | models.Q(
                        watershed_rows=0,
                        subcatchment_rows=0,
                        channel_rows=0,
                        capability_rows=0,
                    )
                ),
                name="staging_state_terminal_counts_zero",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="CLEANUP_PENDING",
                        last_cleanup_error__isnull=False,
                    )
                    | models.Q(last_cleanup_error__isnull=True)
                ),
                name="staging_state_cleanup_error_coherent",
            ),
        ]

    @property
    def required_bytes(self):
        return sum(
            (
                self.artifact_bytes,
                self.staging_bytes,
                self.index_bytes,
                self.backup_bytes,
                self.wal_bytes,
                self.margin_bytes,
            )
        )

    def save(self, *args, **kwargs):
        if self.last_cleanup_error:
            from server.watershed.release_ledger import sanitize_failure_summary

            self.last_cleanup_error = sanitize_failure_summary(
                self.last_cleanup_error
            )
        self.full_clean(validate_constraints=False)
        super().save(*args, **kwargs)


class StagedRow(models.Model):
    class ValidationStatus(models.TextChoices):
        STAGED = "staged", "Staged"
        VALIDATED = "validated", "Validated"
        REJECTED = "rejected", "Rejected"

    attempt = models.ForeignKey(DataReleaseAttempt, on_delete=models.CASCADE)
    run_state = models.ForeignKey(DataRunState, on_delete=models.PROTECT)
    watershed_identity = models.ForeignKey(
        WatershedIdentity,
        on_delete=models.PROTECT,
    )
    source_fingerprint = models.CharField(
        max_length=64,
        validators=[sha256_validator],
    )
    validation_status = models.CharField(
        max_length=16,
        choices=ValidationStatus.choices,
        default=ValidationStatus.STAGED,
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.attempt_id and self.run_state_id:
            if self.attempt.release_id != self.run_state.release_id:
                raise ValidationError("Staging attempt and run release must match.")
            if self.attempt.status != DataReleaseAttempt.Status.STAGING:
                raise ValidationError("Rows may be staged only during staging.")
            if not self.attempt.lease_active:
                raise ValidationError("Rows require an active attempt lease.")
        if self.run_state_id and self.watershed_identity_id:
            if self.run_state.watershed_identity_id != self.watershed_identity_id:
                raise ValidationError(
                    "Staging watershed must match its release run state."
                )


class StagedWatershed(StagedRow):
    runid = models.CharField(max_length=255)
    geom = models.MultiPolygonField(srid=4326)
    simplified_geom = models.MultiPolygonField(srid=4326, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("attempt", "watershed_identity"),
                name="stage_ws_attempt_identity_uniq",
            ),
            models.UniqueConstraint(
                fields=("attempt", "runid"),
                name="stage_ws_attempt_runid_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    validation_status__in=("staged", "validated", "rejected")
                ),
                name="stage_ws_validation_status",
            ),
            models.CheckConstraint(
                condition=models.Q(source_fingerprint__regex=r"^[a-f0-9]{64}$"),
                name="stage_ws_source_hash",
            ),
        ]
        indexes = [
            models.Index(
                fields=("attempt", "validation_status"),
                name="stage_ws_attempt_status_idx",
            ),
        ]

    def clean(self):
        super().clean()
        validate_public_configuration(self.metadata, "metadata")
        if self.run_state_id and self.runid != self.run_state.runid:
            raise ValidationError("Staged run ID must match its release run state.")


class StagedSubcatchment(StagedRow):
    topazid = models.IntegerField()
    weppid = models.IntegerField()
    geom = models.MultiPolygonField(srid=4326)
    attributes = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("attempt", "watershed_identity", "topazid"),
                name="stage_sub_attempt_topaz_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    validation_status__in=("staged", "validated", "rejected")
                ),
                name="stage_sub_validation_status",
            ),
            models.CheckConstraint(
                condition=models.Q(source_fingerprint__regex=r"^[a-f0-9]{64}$"),
                name="stage_sub_source_hash",
            ),
        ]
        indexes = [
            models.Index(
                fields=("attempt", "watershed_identity"),
                name="stage_sub_attempt_ws_idx",
            ),
        ]

    def clean(self):
        super().clean()
        validate_public_configuration(self.attributes, "attributes")


class StagedChannel(StagedRow):
    topazid = models.IntegerField()
    weppid = models.IntegerField()
    order = models.IntegerField()
    geom = models.MultiPolygonField(srid=4326)
    attributes = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "attempt",
                    "watershed_identity",
                    "topazid",
                    "weppid",
                    "order",
                ),
                name="stage_channel_attempt_key_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    validation_status__in=("staged", "validated", "rejected")
                ),
                name="stage_channel_validation_status",
            ),
            models.CheckConstraint(
                condition=models.Q(source_fingerprint__regex=r"^[a-f0-9]{64}$"),
                name="stage_channel_source_hash",
            ),
        ]
        indexes = [
            models.Index(
                fields=("attempt", "watershed_identity"),
                name="stage_channel_attempt_ws_idx",
            ),
        ]

    def clean(self):
        super().clean()
        validate_public_configuration(self.attributes, "attributes")


class StagedRunCapability(StagedRow):
    class CapabilityType(models.TextChoices):
        RHESSYS = "rhessys", "RHESSys"
        SBS = "sbs", "Soil burn severity"

    class Mode(models.TextChoices):
        DYNAMIC = "dynamic", "Dynamic"
        PRECOMPUTED = "precomputed", "Precomputed"
        BOTH = "both", "Both"

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
    runtime_configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("attempt", "watershed_identity", "capability_type"),
                name="stage_cap_attempt_type_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(capability_type__in=("rhessys", "sbs")),
                name="stage_cap_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(mode__in=("dynamic", "precomputed", "both")),
                name="stage_cap_mode_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    durable_base_uri__startswith="https://",
                    index_uri__startswith="https://",
                ),
                name="stage_cap_uris_https",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    source_fingerprint__regex=r"^[a-f0-9]{64}$",
                    index_sha256__regex=r"^[a-f0-9]{64}$",
                    capability_fingerprint__regex=r"^[a-f0-9]{64}$",
                ),
                name="stage_cap_hashes_format",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    validation_status__in=("staged", "validated", "rejected")
                ),
                name="stage_cap_validation_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=("attempt", "watershed_identity"),
                name="stage_cap_attempt_ws_idx",
            ),
        ]

    def clean(self):
        super().clean()
        validate_public_configuration(
            self.runtime_configuration,
            "runtime_configuration",
        )
        if self.run_state_id:
            if self.run_state.capability_fingerprint != self.capability_fingerprint:
                raise ValidationError(
                    "Staged capability fingerprint must match its run state."
                )
