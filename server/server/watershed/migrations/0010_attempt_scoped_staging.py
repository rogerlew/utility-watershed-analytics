import django.contrib.gis.db.models.fields
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


SHA256_VALIDATOR = django.core.validators.RegexValidator(
    message="Use a lowercase SHA-256 digest.",
    regex="^[a-f0-9]{64}$",
)
HTTPS_VALIDATOR = django.core.validators.URLValidator(schemes=("https",))


def required_space_expression():
    return (
        models.F("artifact_bytes")
        + models.F("staging_bytes")
        + models.F("index_bytes")
        + models.F("backup_bytes")
        + models.F("wal_bytes")
        + models.F("margin_bytes")
    )


def staged_base_fields():
    return [
        (
            "id",
            models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name="ID",
            ),
        ),
        (
            "source_fingerprint",
            models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
        ),
        (
            "validation_status",
            models.CharField(
                choices=[
                    ("staged", "Staged"),
                    ("validated", "Validated"),
                    ("rejected", "Rejected"),
                ],
                default="staged",
                max_length=16,
            ),
        ),
        (
            "attempt",
            models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="watershed.datareleaseattempt",
            ),
        ),
        (
            "run_state",
            models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="watershed.datarunstate",
            ),
        ),
        (
            "watershed_identity",
            models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="watershed.watershedidentity",
            ),
        ),
    ]


class Migration(migrations.Migration):
    dependencies = [
        ("watershed", "0009_release_ledger_capabilities"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataReleaseStagingState",
            fields=[
                (
                    "attempt",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="staging_state",
                        serialize=False,
                        to="watershed.datareleaseattempt",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("SPACE_REJECTED", "Space rejected"),
                            ("LOADING", "Loading"),
                            ("READY", "Ready"),
                            ("CLEANUP_PENDING", "Cleanup pending"),
                            ("CLEANED", "Cleaned"),
                        ],
                        max_length=20,
                    ),
                ),
                ("artifact_bytes", models.PositiveBigIntegerField()),
                ("staging_bytes", models.PositiveBigIntegerField()),
                ("index_bytes", models.PositiveBigIntegerField()),
                ("backup_bytes", models.PositiveBigIntegerField()),
                ("wal_bytes", models.PositiveBigIntegerField()),
                ("margin_bytes", models.PositiveBigIntegerField()),
                ("available_bytes", models.PositiveBigIntegerField()),
                ("watershed_rows", models.PositiveBigIntegerField(default=0)),
                ("subcatchment_rows", models.PositiveBigIntegerField(default=0)),
                ("channel_rows", models.PositiveBigIntegerField(default=0)),
                ("capability_rows", models.PositiveBigIntegerField(default=0)),
                ("retention_until", models.DateTimeField()),
                ("cleanup_attempts", models.PositiveIntegerField(default=0)),
                (
                    "last_cleanup_error",
                    models.CharField(blank=True, max_length=512, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
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
                                & models.Q(
                                    available_bytes__gte=required_space_expression()
                                )
                            )
                        ),
                        name="staging_state_space_outcome",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                status__in=(
                                    "LOADING",
                                    "READY",
                                    "CLEANUP_PENDING",
                                )
                            )
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
            },
        ),
        migrations.CreateModel(
            name="StagedChannel",
            fields=staged_base_fields()
            + [
                ("topazid", models.IntegerField()),
                ("weppid", models.IntegerField()),
                ("order", models.IntegerField()),
                (
                    "geom",
                    django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326),
                ),
                ("attributes", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=("attempt", "watershed_identity"),
                        name="stage_channel_attempt_ws_idx",
                    )
                ],
                "constraints": [
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
                            validation_status__in=(
                                "staged",
                                "validated",
                                "rejected",
                            )
                        ),
                        name="stage_channel_validation_status",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            source_fingerprint__regex="^[a-f0-9]{64}$"
                        ),
                        name="stage_channel_source_hash",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="StagedRunCapability",
            fields=staged_base_fields()
            + [
                (
                    "capability_type",
                    models.CharField(
                        choices=[("rhessys", "RHESSys")],
                        default="rhessys",
                        max_length=32,
                    ),
                ),
                (
                    "mode",
                    models.CharField(
                        choices=[
                            ("dynamic", "Dynamic"),
                            ("precomputed", "Precomputed"),
                            ("both", "Both"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "durable_base_uri",
                    models.CharField(max_length=2048, validators=[HTTPS_VALIDATOR]),
                ),
                (
                    "index_uri",
                    models.CharField(max_length=2048, validators=[HTTPS_VALIDATOR]),
                ),
                (
                    "index_sha256",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "capability_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                ("runtime_configuration", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=("attempt", "watershed_identity"),
                        name="stage_cap_attempt_ws_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=(
                            "attempt",
                            "watershed_identity",
                            "capability_type",
                        ),
                        name="stage_cap_attempt_type_uniq",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(capability_type="rhessys"),
                        name="stage_cap_type_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            mode__in=("dynamic", "precomputed", "both")
                        ),
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
                            source_fingerprint__regex="^[a-f0-9]{64}$",
                            index_sha256__regex="^[a-f0-9]{64}$",
                            capability_fingerprint__regex="^[a-f0-9]{64}$",
                        ),
                        name="stage_cap_hashes_format",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            validation_status__in=(
                                "staged",
                                "validated",
                                "rejected",
                            )
                        ),
                        name="stage_cap_validation_status",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="StagedSubcatchment",
            fields=staged_base_fields()
            + [
                ("topazid", models.IntegerField()),
                ("weppid", models.IntegerField()),
                (
                    "geom",
                    django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326),
                ),
                ("attributes", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=("attempt", "watershed_identity"),
                        name="stage_sub_attempt_ws_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("attempt", "watershed_identity", "topazid"),
                        name="stage_sub_attempt_topaz_uniq",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            validation_status__in=(
                                "staged",
                                "validated",
                                "rejected",
                            )
                        ),
                        name="stage_sub_validation_status",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            source_fingerprint__regex="^[a-f0-9]{64}$"
                        ),
                        name="stage_sub_source_hash",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="StagedWatershed",
            fields=staged_base_fields()
            + [
                ("runid", models.CharField(max_length=255)),
                (
                    "geom",
                    django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326),
                ),
                (
                    "simplified_geom",
                    django.contrib.gis.db.models.fields.MultiPolygonField(
                        blank=True,
                        null=True,
                        srid=4326,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=("attempt", "validation_status"),
                        name="stage_ws_attempt_status_idx",
                    )
                ],
                "constraints": [
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
                            validation_status__in=(
                                "staged",
                                "validated",
                                "rejected",
                            )
                        ),
                        name="stage_ws_validation_status",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            source_fingerprint__regex="^[a-f0-9]{64}$"
                        ),
                        name="stage_ws_source_hash",
                    ),
                ],
            },
        ),
    ]
