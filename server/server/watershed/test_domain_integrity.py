from datetime import timedelta

import pandas as pd
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.sessions.models import Session
from django.db import IntegrityError, connection, models, transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from server.watershed.domain_ownership import (
    persistent_identity_table_names,
    rebuild_delete_order,
    reconciled_table_names,
)
from server.watershed.loaders.writers import DjangoDataWriter, JoinIdentityError
from server.watershed.models import (
    Channel,
    Subcatchment,
    Watershed,
    WatershedCollection,
    WatershedIdentity,
    WatershedRunAlias,
)


GEOMETRY = "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"


def create_domain_fixture(suffix="fixture"):
    collection = WatershedCollection.objects.create(key=f"integrity-{suffix}")
    identity = WatershedIdentity.objects.create(
        watershed_key=f"integrity-watershed-{suffix}",
        collection=collection,
    )
    watershed = Watershed.objects.create(
        runid=f"integrity-run-{suffix}",
        logical_watershed=identity,
        geom=GEOSGeometry(GEOMETRY),
    )
    alias = WatershedRunAlias.objects.create(
        runid=watershed.runid,
        watershed_identity=identity,
        is_current=True,
    )
    subcatchment = Subcatchment.objects.create(
        watershed=watershed,
        logical_watershed=identity,
        topazid=1,
        weppid=10,
        geom=GEOSGeometry(GEOMETRY),
    )
    channel = Channel.objects.create(
        watershed=watershed,
        logical_watershed=identity,
        topazid=2,
        weppid=20,
        order=1,
        geom=GEOSGeometry(GEOMETRY),
    )
    return collection, identity, watershed, alias, subcatchment, channel


class DomainConstraintTests(TestCase):
    def test_stable_key_and_status_checks_are_database_enforced(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            WatershedCollection.objects.create(key="Invalid Collection")
        with self.assertRaises(IntegrityError), transaction.atomic():
            WatershedIdentity.objects.create(watershed_key="Invalid Watershed")
        with self.assertRaises(IntegrityError), transaction.atomic():
            WatershedIdentity.objects.create(status="unknown")

    def test_duplicate_subcatchment_and_channel_keys_are_rejected(self):
        _, identity, watershed, _, _, _ = create_domain_fixture()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subcatchment.objects.create(
                watershed=watershed,
                logical_watershed=identity,
                topazid=1,
                weppid=11,
                geom=GEOSGeometry(GEOMETRY),
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Channel.objects.create(
                watershed=watershed,
                logical_watershed=identity,
                topazid=2,
                weppid=20,
                order=1,
                geom=GEOSGeometry(GEOMETRY),
            )

    def test_legacy_and_logical_unique_constraints_exist(self):
        with connection.cursor() as cursor:
            subcatchment_constraints = connection.introspection.get_constraints(
                cursor, Subcatchment._meta.db_table
            )
            channel_constraints = connection.introspection.get_constraints(
                cursor, Channel._meta.db_table
            )
        self.assertTrue(subcatchment_constraints["subcatchment_run_topaz_uniq"]["unique"])
        self.assertTrue(
            subcatchment_constraints["subcatchment_logical_topaz_uniq"]["unique"]
        )
        self.assertTrue(
            channel_constraints["channel_run_topaz_wepp_order_uniq"]["unique"]
        )
        self.assertTrue(
            channel_constraints["channel_logical_topaz_wepp_order_uniq"]["unique"]
        )

    def test_old_and_logical_foreign_key_orphans_are_rejected(self):
        _, identity, watershed, _, _, _ = create_domain_fixture()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subcatchment.objects.create(
                watershed_id="missing-run",
                logical_watershed=identity,
                topazid=50,
                weppid=50,
                geom=GEOSGeometry(GEOMETRY),
            )
            connection.check_constraints()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Channel.objects.create(
                watershed=watershed,
                logical_watershed_id="00000000-0000-0000-0000-000000000000",
                topazid=60,
                weppid=60,
                order=1,
                geom=GEOSGeometry(GEOMETRY),
            )
            connection.check_constraints()


class DomainOwnershipTests(TestCase):
    def test_exact_rebuild_and_identity_table_sets(self):
        self.assertEqual(
            reconciled_table_names(),
            frozenset(
                {
                    "watershed_watershed",
                    "watershed_subcatchment",
                    "watershed_channel",
                }
            ),
        )
        self.assertEqual(
            rebuild_delete_order(),
            (
                "watershed_channel",
                "watershed_subcatchment",
                "watershed_watershed",
            ),
        )
        self.assertEqual(
            persistent_identity_table_names(),
            frozenset(
                {
                    "watershed_watershedcollection",
                    "watershed_watershedidentity",
                    "watershed_watershedrunalias",
                }
            ),
        )

    def test_model_deletion_policies_match_contract(self):
        self.assertIs(
            Subcatchment._meta.get_field("watershed").remote_field.on_delete,
            models.CASCADE,
        )
        self.assertIs(
            Channel._meta.get_field("watershed").remote_field.on_delete,
            models.CASCADE,
        )
        for model in (Watershed, Subcatchment, Channel, WatershedRunAlias):
            field_name = (
                "watershed_identity" if model is WatershedRunAlias else "logical_watershed"
            )
            self.assertIs(
                model._meta.get_field(field_name).remote_field.on_delete,
                models.PROTECT,
            )

    def test_bounded_rebuild_preserves_identity_auth_and_sessions(self):
        collection, identity, _, alias, _, _ = create_domain_fixture()
        user = get_user_model().objects.create_user(username="db14-operator")
        session = Session.objects.create(
            session_key="db14-session",
            session_data="e30:fixture",
            expire_date=timezone.now() + timedelta(hours=1),
        )

        for model in (Channel, Subcatchment, Watershed):
            model.objects.all().delete()

        self.assertTrue(WatershedCollection.objects.filter(pk=collection.pk).exists())
        self.assertTrue(WatershedIdentity.objects.filter(pk=identity.pk).exists())
        self.assertTrue(WatershedRunAlias.objects.filter(pk=alias.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertTrue(Session.objects.filter(pk=session.pk).exists())

    def test_orm_cascade_preserves_identity_and_raw_parent_delete_is_restricted(self):
        _, identity, watershed, _, subcatchment, channel = create_domain_fixture()
        watershed.delete()
        self.assertFalse(Subcatchment.objects.filter(pk=subcatchment.pk).exists())
        self.assertFalse(Channel.objects.filter(pk=channel.pk).exists())
        self.assertTrue(WatershedIdentity.objects.filter(pk=identity.pk).exists())

        _, _, watershed, _, _, _ = create_domain_fixture("raw-delete")
        with self.assertRaises(IntegrityError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM watershed_watershed WHERE runid = %s",
                    [watershed.pk],
                )
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class ParquetJoinIdentityTests(SimpleTestCase):
    def setUp(self):
        self.writer = object.__new__(DjangoDataWriter)

    def test_all_accepted_topaz_spellings_index_cleanly(self):
        for column in (
            "TopazID",
            "topaz_id",
            "topazid",
            "TOPAZID",
            "Topaz_ID",
            "topaz_ID",
        ):
            with self.subTest(column=column):
                indexed = self.writer._validated_topaz_index(
                    pd.DataFrame({column: [1, 2], "value": [10, 20]}),
                    "soils",
                )
                self.assertEqual(list(indexed.index), [1, 2])

    def test_missing_null_and_duplicate_join_identities_fail(self):
        fixtures = (
            ("hillslopes", pd.DataFrame({"other": [1]}), "missing"),
            ("soils", pd.DataFrame({"TopazID": [1, None]}), "null_rows=1"),
            ("landuse", pd.DataFrame({"TopazID": [1, 1]}), "duplicate_rows=2"),
        )
        for artifact_name, dataframe, message in fixtures:
            with self.subTest(artifact_name=artifact_name):
                with self.assertRaisesRegex(JoinIdentityError, message):
                    self.writer._validated_topaz_index(dataframe, artifact_name)
