import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


SHA256_VALIDATOR = django.core.validators.RegexValidator(
    message="Use a lowercase SHA-256 digest.",
    regex="^[a-f0-9]{64}$",
)
KEY_VALIDATOR = django.core.validators.RegexValidator(
    message="Use a lowercase ASCII kebab-case stable key.",
    regex="^[a-z0-9]+(?:-[a-z0-9]+)*$",
)
HTTPS_VALIDATOR = django.core.validators.URLValidator(schemes=("https",))


def create_empty_active_release(apps, schema_editor):
    ActiveDataRelease = apps.get_model("watershed", "ActiveDataRelease")
    ActiveDataRelease.objects.create(singleton_id=1, state="EMPTY")


def remove_active_release(apps, schema_editor):
    ActiveDataRelease = apps.get_model("watershed", "ActiveDataRelease")
    ActiveDataRelease.objects.filter(singleton_id=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("watershed", "0008_domain_integrity_constraints"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataRelease",
            fields=[
                (
                    "release_id",
                    models.CharField(
                        max_length=32,
                        primary_key=True,
                        serialize=False,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Use the version-1 YYYY-MM-DD.N release ID.",
                                regex="^[0-9]{4}-[0-9]{2}-[0-9]{2}\\.[1-9][0-9]*$",
                            )
                        ],
                    ),
                ),
                (
                    "manifest_sha256",
                    models.CharField(
                        max_length=64,
                        unique=True,
                        validators=[SHA256_VALIDATOR],
                    ),
                ),
                (
                    "release_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "domain_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                ("schema_version", models.PositiveSmallIntegerField(default=1)),
                ("data_contract", models.PositiveSmallIntegerField(default=1)),
                ("identity_contract", models.PositiveSmallIntegerField(default=1)),
                ("artifact_contract", models.PositiveSmallIntegerField(default=1)),
                (
                    "fingerprint_version",
                    models.PositiveSmallIntegerField(default=1),
                ),
                ("supported_migration", models.CharField(max_length=128)),
                (
                    "materializer_image_digest",
                    models.CharField(
                        max_length=71,
                        validators=[
                            django.core.validators.RegexValidator(
                                regex="^sha256:[a-f0-9]{64}$"
                            )
                        ],
                    ),
                ),
                (
                    "materializer_git_commit",
                    models.CharField(
                        max_length=40,
                        validators=[
                            django.core.validators.RegexValidator(
                                regex="^[a-f0-9]{40}$"
                            )
                        ],
                    ),
                ),
                ("expected_watersheds", models.PositiveIntegerField()),
                ("expected_subcatchments", models.PositiveIntegerField()),
                ("expected_channels", models.PositiveIntegerField()),
                ("actual_watersheds", models.PositiveIntegerField()),
                ("actual_subcatchments", models.PositiveIntegerField()),
                ("actual_channels", models.PositiveIntegerField()),
                ("validation_summary", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField()),
                ("first_activated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("validated", "Validated"),
                            ("active", "Active"),
                            ("superseded", "Superseded"),
                        ],
                        default="validated",
                        max_length=16,
                    ),
                ),
                (
                    "previous_release",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="successor_releases",
                        to="watershed.datarelease",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            artifact_contract=1,
                            data_contract=1,
                            fingerprint_version=1,
                            identity_contract=1,
                            schema_version=1,
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
                            domain_fingerprint__regex="^[a-f0-9]{64}$",
                            manifest_sha256__regex="^[a-f0-9]{64}$",
                            materializer_git_commit__regex="^[a-f0-9]{40}$",
                            materializer_image_digest__regex="^sha256:[a-f0-9]{64}$",
                            release_fingerprint__regex="^[a-f0-9]{64}$",
                        ),
                        name="release_coordinates_format",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(status="active"),
                        fields=("status",),
                        name="release_one_active_status",
                    ),
                ]
            },
        ),
        migrations.CreateModel(
            name="ActiveDataRelease",
            fields=[
                (
                    "singleton_id",
                    models.PositiveSmallIntegerField(
                        default=1,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[("EMPTY", "Empty"), ("ACTIVE", "Active")],
                        default="EMPTY",
                        max_length=8,
                    ),
                ),
                (
                    "manifest_sha256",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        validators=[SHA256_VALIDATOR],
                    ),
                ),
                (
                    "data_contract",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "release",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="active_pointer",
                        to="watershed.datarelease",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(singleton_id=1),
                        name="active_release_singleton_id",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                activated_at__isnull=True,
                                data_contract__isnull=True,
                                manifest_sha256__isnull=True,
                                release__isnull=True,
                                state="EMPTY",
                            )
                            | models.Q(
                                activated_at__isnull=False,
                                data_contract__isnull=False,
                                manifest_sha256__isnull=False,
                                release__isnull=False,
                                state="ACTIVE",
                            )
                        ),
                        name="active_release_state_coherent",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(manifest_sha256__isnull=True)
                            | models.Q(
                                manifest_sha256__regex="^[a-f0-9]{64}$"
                            )
                        ),
                        name="active_release_manifest_format",
                    ),
                ]
            },
        ),
        migrations.CreateModel(
            name="DataReleaseAttempt",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "actor_kind",
                    models.CharField(
                        choices=[("operator", "Operator"), ("workflow", "Workflow")],
                        max_length=16,
                    ),
                ),
                ("actor_identifier", models.CharField(max_length=255)),
                ("target_environment", models.CharField(max_length=32)),
                (
                    "application_git_commit",
                    models.CharField(
                        max_length=40,
                        validators=[
                            django.core.validators.RegexValidator(
                                regex="^[a-f0-9]{40}$"
                            )
                        ],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("planning", "Planning"),
                            ("staging", "Staging"),
                            ("applying", "Applying"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("rolled_back", "Rolled back"),
                        ],
                        default="planning",
                        max_length=16,
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("validated_at", models.DateTimeField(blank=True, null=True)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "reviewed_plan_sha256",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "actual_plan_sha256",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        validators=[SHA256_VALIDATOR],
                    ),
                ),
                ("lease_owner", models.CharField(max_length=255)),
                ("lease_heartbeat_at", models.DateTimeField()),
                ("lease_expires_at", models.DateTimeField()),
                ("lease_active", models.BooleanField(default=True)),
                (
                    "backup_artifact_sha256",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        validators=[SHA256_VALIDATOR],
                    ),
                ),
                (
                    "failure_phase",
                    models.CharField(blank=True, max_length=64, null=True),
                ),
                (
                    "failure_summary",
                    models.CharField(blank=True, max_length=512, null=True),
                ),
                (
                    "deployment_report_uri",
                    models.CharField(
                        blank=True,
                        max_length=2048,
                        null=True,
                        validators=[HTTPS_VALIDATOR],
                    ),
                ),
                (
                    "deployment_report_sha256",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        validators=[SHA256_VALIDATOR],
                    ),
                ),
                (
                    "previous_active_release",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="successor_attempts",
                        to="watershed.datarelease",
                    ),
                ),
                (
                    "release",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="attempts",
                        to="watershed.datarelease",
                    ),
                ),
            ],
            options={
                "constraints": [
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
                        condition=models.Q(
                            lease_expires_at__gt=models.F("lease_heartbeat_at")
                        ),
                        name="attempt_lease_window_valid",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                deployment_report_sha256__isnull=True,
                                deployment_report_uri__isnull=True,
                            )
                            | models.Q(
                                deployment_report_sha256__regex="^[a-f0-9]{64}$",
                                deployment_report_uri__startswith="https://",
                            )
                        ),
                        name="attempt_report_reference_coherent",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                completed_at__isnull=True,
                                status__in=("planning", "staging", "applying"),
                            )
                            | models.Q(
                                completed_at__isnull=False,
                                lease_active=False,
                                status__in=("succeeded", "failed", "rolled_back"),
                            )
                        ),
                        name="attempt_terminal_state_coherent",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                failure_phase__isnull=False,
                                failure_summary__isnull=False,
                                status="failed",
                            )
                            | ~models.Q(status="failed")
                        ),
                        name="attempt_failure_details_present",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(lease_active=True),
                        fields=("lease_active",),
                        name="attempt_one_active_lease",
                    ),
                ]
            },
        ),
        migrations.CreateModel(
            name="DataRunState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("runid", models.CharField(max_length=255)),
                (
                    "run_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "metadata_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "geometry_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "subcatchment_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "channel_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "hillslope_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "soil_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "landuse_fingerprint",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                (
                    "transformation_lineage_fingerprint",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        validators=[SHA256_VALIDATOR],
                    ),
                ),
                (
                    "capability_fingerprint",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        validators=[SHA256_VALIDATOR],
                    ),
                ),
                ("actual_watersheds", models.PositiveIntegerField(default=1)),
                ("actual_subcatchments", models.PositiveIntegerField()),
                ("actual_channels", models.PositiveIntegerField()),
                (
                    "validation_status",
                    models.CharField(
                        choices=[
                            ("validated", "Validated"),
                            ("rejected", "Rejected"),
                        ],
                        default="validated",
                        max_length=16,
                    ),
                ),
                (
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="release_run_states",
                        to="watershed.watershedcollection",
                    ),
                ),
                (
                    "release",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="run_states",
                        to="watershed.datarelease",
                    ),
                ),
                (
                    "watershed_identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="release_run_states",
                        to="watershed.watershedidentity",
                    ),
                ),
            ],
            options={
                "constraints": [
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
                        condition=models.Q(
                            validation_status__in=("validated", "rejected")
                        ),
                        name="run_state_validation_status_valid",
                    ),
                ]
            },
        ),
        migrations.CreateModel(
            name="DataArtifactLineage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("role", models.CharField(max_length=64, validators=[KEY_VALIDATOR])),
                ("uri", models.CharField(max_length=2048, validators=[HTTPS_VALIDATOR])),
                (
                    "sha256",
                    models.CharField(max_length=64, validators=[SHA256_VALIDATOR]),
                ),
                ("byte_size", models.PositiveBigIntegerField()),
                ("media_type", models.CharField(max_length=255)),
                (
                    "run_state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="artifacts",
                        to="watershed.datarunstate",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("run_state", "role"),
                        name="artifact_run_role_uniq",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(uri__startswith="https://"),
                        name="artifact_uri_https",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(sha256__regex="^[a-f0-9]{64}$"),
                        name="artifact_sha256_format",
                    ),
                ]
            },
        ),
        migrations.CreateModel(
            name="RunCapability",
            fields=[
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
                ("runtime_configuration", models.JSONField(default=dict)),
                (
                    "run_state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="capabilities",
                        to="watershed.datarunstate",
                    ),
                ),
                (
                    "watershed_identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="release_capabilities",
                        to="watershed.watershedidentity",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("run_state", "capability_type"),
                        name="capability_run_type_uniq",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(capability_type="rhessys"),
                        name="capability_type_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            mode__in=("dynamic", "precomputed", "both")
                        ),
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
                            capability_fingerprint__regex="^[a-f0-9]{64}$",
                            index_sha256__regex="^[a-f0-9]{64}$",
                        ),
                        name="capability_hashes_format",
                    ),
                ]
            },
        ),
        migrations.RunPython(create_empty_active_release, remove_active_release),
    ]
