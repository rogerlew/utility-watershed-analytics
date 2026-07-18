import json

from django.contrib.gis.geos import GEOSGeometry
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from server.watershed.identity import IdentityConflict, activate_run_alias
from server.watershed.identity_validation import build_stable_identity_report
from server.watershed.models import (
    Channel,
    Subcatchment,
    Watershed,
    WatershedCollection,
    WatershedIdentity,
    WatershedRunAlias,
)


GEOMETRY = "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"


def create_identity_fixture(runid="legacy-run", watershed_key="stable-watershed"):
    collection = WatershedCollection.objects.create(key="stable-collection")
    identity = WatershedIdentity.objects.create(
        watershed_key=watershed_key,
        collection=collection,
    )
    watershed = Watershed.objects.create(
        runid=runid,
        logical_watershed=identity,
        srcname="Stable watershed",
        geom=GEOSGeometry(GEOMETRY),
    )
    WatershedRunAlias.objects.create(
        runid=runid,
        watershed_identity=identity,
        is_current=True,
    )
    subcatchment = Subcatchment.objects.create(
        watershed=watershed,
        logical_watershed=identity,
        topazid=11,
        weppid=22,
        geom=GEOSGeometry(GEOMETRY),
    )
    channel = Channel.objects.create(
        watershed=watershed,
        logical_watershed=identity,
        topazid=31,
        weppid=32,
        order=1,
        geom=GEOSGeometry(GEOMETRY),
    )
    return identity, watershed, subcatchment, channel


class StableIdentityRouteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        (
            cls.identity,
            cls.watershed,
            cls.subcatchment,
            cls.channel,
        ) = create_identity_fixture()

    def test_stable_key_routes_use_stable_feature_ids(self):
        detail = self.client.get(reverse("watershed-by-key", args=["stable-watershed"]))
        subcatchments = self.client.get(
            reverse("watershed-subcatchments-by-key", args=["stable-watershed"])
        )
        channels = self.client.get(
            reverse("watershed-channels-by-key", args=["stable-watershed"])
        )

        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        detail_payload = json.loads(detail.content)
        self.assertEqual(detail_payload["id"], "stable-watershed")
        self.assertEqual(detail_payload["properties"]["watershed_key"], "stable-watershed")
        self.assertEqual(detail_payload["properties"]["current_runid"], "legacy-run")
        self.assertEqual(
            json.loads(subcatchments.content)["features"][0]["id"],
            "subcatchment:stable-watershed:11",
        )
        self.assertEqual(
            json.loads(channels.content)["features"][0]["id"],
            "channel:stable-watershed:31:32:1",
        )

    def test_run_replacement_preserves_rows_and_both_alias_routes(self):
        subcatchment_id = self.subcatchment.pk
        channel_id = self.channel.pk
        activate_run_alias(self.identity, "successor-run")

        old_detail = self.client.get(reverse("watershed-detail", args=["legacy-run"]))
        new_detail = self.client.get(reverse("watershed-detail", args=["successor-run"]))
        old_children = self.client.get(
            reverse("watershed-subcatchments", args=["legacy-run"])
        )
        new_children = self.client.get(
            reverse("watershed-subcatchments", args=["successor-run"])
        )

        self.assertEqual(json.loads(old_detail.content)["id"], "legacy-run")
        self.assertEqual(json.loads(new_detail.content)["id"], "successor-run")
        self.assertEqual(
            json.loads(old_detail.content)["properties"]["current_runid"],
            "successor-run",
        )
        self.assertEqual(
            json.loads(old_children.content)["features"][0]["id"], subcatchment_id
        )
        self.assertEqual(
            json.loads(new_children.content)["features"][0]["id"], subcatchment_id
        )
        self.assertEqual(Subcatchment.objects.get().pk, subcatchment_id)
        self.assertEqual(Channel.objects.get().pk, channel_id)
        self.assertTrue(
            WatershedRunAlias.objects.get(runid="successor-run").is_current
        )
        self.assertFalse(WatershedRunAlias.objects.get(runid="legacy-run").is_current)

    def test_retired_alias_is_gone_and_unknown_key_is_not_found(self):
        self.identity.status = WatershedIdentity.Status.RETIRED
        self.identity.save(update_fields=("status",))
        WatershedRunAlias.objects.filter(watershed_identity=self.identity).update(
            is_current=False
        )

        retired = self.client.get(reverse("watershed-detail", args=["legacy-run"]))
        unknown = self.client.get(reverse("watershed-by-key", args=["never-known"]))

        self.assertEqual(retired.status_code, status.HTTP_410_GONE)
        self.assertEqual(unknown.status_code, status.HTTP_404_NOT_FOUND)


class StableIdentityConstraintTests(TestCase):
    def test_duplicate_watershed_key_is_rejected(self):
        WatershedIdentity.objects.create(watershed_key="same-key")
        with self.assertRaises(IntegrityError), transaction.atomic():
            WatershedIdentity.objects.create(watershed_key="same-key")

    def test_run_alias_cannot_move_between_identities(self):
        first = WatershedIdentity.objects.create(watershed_key="first")
        second = WatershedIdentity.objects.create(watershed_key="second")
        WatershedRunAlias.objects.create(
            runid="permanent-run",
            watershed_identity=first,
            is_current=True,
        )

        with self.assertRaises(IdentityConflict):
            activate_run_alias(second, "permanent-run")

        self.assertEqual(
            WatershedRunAlias.objects.get(runid="permanent-run").watershed_identity,
            first,
        )

    def test_only_one_current_alias_is_allowed(self):
        identity = WatershedIdentity.objects.create(watershed_key="one-current")
        WatershedRunAlias.objects.create(
            runid="first-run",
            watershed_identity=identity,
            is_current=True,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            WatershedRunAlias.objects.create(
                runid="second-run",
                watershed_identity=identity,
                is_current=True,
            )


class StableIdentityValidationTests(TestCase):
    def test_complete_fixture_passes(self):
        create_identity_fixture()
        report = build_stable_identity_report()
        self.assertEqual(report["status"], "passed")
        call_command("validate_watershed_identity", "--fail-on-violations")

    def test_incomplete_dual_link_fails(self):
        identity, watershed, _, _ = create_identity_fixture()
        Subcatchment.objects.create(
            watershed=watershed,
            logical_watershed=None,
            topazid=99,
            weppid=99,
            geom=GEOSGeometry(GEOMETRY),
        )
        Channel.objects.create(
            watershed=watershed,
            logical_watershed=WatershedIdentity.objects.create(),
            topazid=99,
            weppid=99,
            order=1,
            geom=GEOSGeometry(GEOMETRY),
        )

        report = build_stable_identity_report()

        self.assertEqual(report["status"], "failed")
        self.assertEqual(
            report["violations"]["subcatchments_without_logical_identity"], 1
        )
        self.assertEqual(report["violations"]["channel_identity_mismatches"], 1)
        self.assertEqual(identity.current_watershed, watershed)
