import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


COLLECTION_KEYS = (
    "gate-creek",
    "mill-creek",
    "nasa-roses",
    "victoria-ca",
)


def _accepted_assignment(runid):
    if runid == "aversive-forestry":
        return "gate-creek", "gate-creek"
    if runid in {"mdobre-invincible-scarab", "some-oligopoly"}:
        return "mill-creek", "mill-creek"
    if runid.startswith("batch;;nasa-roses-2026-sbs;;"):
        return "nasa-roses", None
    if runid.startswith("batch;;nasa-roses-202606-psbs;;"):
        return "nasa-roses", None
    if runid.startswith("batch;;victoria-ca-2026-sbs;;"):
        return "victoria-ca", None
    return None, None


def backfill_stable_identity(apps, schema_editor):
    database = schema_editor.connection.alias
    Watershed = apps.get_model("watershed", "Watershed")
    WatershedCollection = apps.get_model("watershed", "WatershedCollection")
    WatershedIdentity = apps.get_model("watershed", "WatershedIdentity")
    WatershedRunAlias = apps.get_model("watershed", "WatershedRunAlias")
    Subcatchment = apps.get_model("watershed", "Subcatchment")
    Channel = apps.get_model("watershed", "Channel")

    collections = {
        key: WatershedCollection.objects.using(database).get_or_create(key=key)[0]
        for key in COLLECTION_KEYS
    }
    assigned_watershed_keys = set()

    for watershed in Watershed.objects.using(database).order_by("runid").iterator():
        collection_key, watershed_key = _accepted_assignment(watershed.runid)
        if watershed_key in assigned_watershed_keys:
            raise RuntimeError(
                f"multiple current revisions claim accepted key {watershed_key!r}"
            )
        if watershed_key:
            assigned_watershed_keys.add(watershed_key)

        identity = WatershedIdentity.objects.using(database).create(
            watershed_key=watershed_key,
            collection=collections.get(collection_key),
            status="active",
        )
        WatershedRunAlias.objects.using(database).create(
            runid=watershed.runid,
            watershed_identity=identity,
            is_current=True,
        )
        Watershed.objects.using(database).filter(pk=watershed.pk).update(
            logical_watershed=identity
        )
        Subcatchment.objects.using(database).filter(watershed_id=watershed.pk).update(
            logical_watershed=identity
        )
        Channel.objects.using(database).filter(watershed_id=watershed.pk).update(
            logical_watershed=identity
        )


def reverse_stable_identity(apps, schema_editor):
    database = schema_editor.connection.alias
    Watershed = apps.get_model("watershed", "Watershed")
    WatershedCollection = apps.get_model("watershed", "WatershedCollection")
    WatershedIdentity = apps.get_model("watershed", "WatershedIdentity")
    WatershedRunAlias = apps.get_model("watershed", "WatershedRunAlias")
    Subcatchment = apps.get_model("watershed", "Subcatchment")
    Channel = apps.get_model("watershed", "Channel")

    linked_watersheds = list(
        Watershed.objects.using(database)
        .exclude(logical_watershed_id=None)
        .values_list("runid", "logical_watershed_id")
    )
    aliases = list(
        WatershedRunAlias.objects.using(database).values_list(
            "runid", "watershed_identity_id", "is_current"
        )
    )
    expected_aliases = {(runid, identity_id, True) for runid, identity_id in linked_watersheds}
    if set(aliases) != expected_aliases:
        raise RuntimeError(
            "stable identity is in use; rollback is closed, so restore the additive "
            "schema and roll forward"
        )
    if WatershedIdentity.objects.using(database).count() != len(linked_watersheds):
        raise RuntimeError(
            "stable identity is in use; rollback is closed, so restore the additive "
            "schema and roll forward"
        )

    Subcatchment.objects.using(database).update(logical_watershed=None)
    Channel.objects.using(database).update(logical_watershed=None)
    Watershed.objects.using(database).update(logical_watershed=None)
    WatershedRunAlias.objects.using(database).all().delete()
    WatershedIdentity.objects.using(database).all().delete()
    WatershedCollection.objects.using(database).filter(key__in=COLLECTION_KEYS).delete()
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class Migration(migrations.Migration):
    dependencies = [
        ("watershed", "0006_watershed_utility_metadata"),
    ]

    operations = [
        migrations.CreateModel(
            name="WatershedCollection",
            fields=[
                (
                    "key",
                    models.CharField(
                        max_length=96,
                        primary_key=True,
                        serialize=False,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Use a lowercase ASCII kebab-case stable key.",
                                regex="^[a-z0-9]+(?:-[a-z0-9]+)*$",
                            )
                        ],
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="WatershedIdentity",
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
                    "watershed_key",
                    models.CharField(
                        blank=True,
                        max_length=96,
                        null=True,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Use a lowercase ASCII kebab-case stable key.",
                                regex="^[a-z0-9]+(?:-[a-z0-9]+)*$",
                            )
                        ],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("retired", "Retired")],
                        default="active",
                        max_length=16,
                    ),
                ),
                (
                    "collection",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="watersheds",
                        to="watershed.watershedcollection",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="watershed",
            name="logical_watershed",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="current_watershed",
                to="watershed.watershedidentity",
            ),
        ),
        migrations.AddField(
            model_name="subcatchment",
            name="logical_watershed",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subcatchments",
                to="watershed.watershedidentity",
            ),
        ),
        migrations.AddField(
            model_name="channel",
            name="logical_watershed",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="channels",
                to="watershed.watershedidentity",
            ),
        ),
        migrations.CreateModel(
            name="WatershedRunAlias",
            fields=[
                (
                    "runid",
                    models.CharField(max_length=255, primary_key=True, serialize=False),
                ),
                ("is_current", models.BooleanField(default=False)),
                (
                    "watershed_identity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="run_aliases",
                        to="watershed.watershedidentity",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="watershedrunalias",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_current", True)),
                fields=("watershed_identity",),
                name="watershed_one_current_run_alias",
            ),
        ),
        migrations.RunPython(backfill_stable_identity, reverse_stable_identity),
    ]
