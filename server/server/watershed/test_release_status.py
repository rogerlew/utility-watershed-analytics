from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from server.watershed.models import ActiveDataRelease, DataRelease
from server.watershed.test_release_ledger import create_identity, create_release


class PublicReleaseStatusTests(TestCase):
    def test_empty_status_is_bounded(self):
        response = self.client.get(reverse("release-status"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(
            response.json(),
            {
                "schema_version": 1,
                "state": "EMPTY",
                "active_release": None,
            },
        )

    def test_active_status_matches_ledger_without_private_details(self):
        collection, identity = create_identity("db27-status")
        release, _, _ = create_release(27, collection, identity)
        activated_at = timezone.now()
        DataRelease.objects.filter(pk=release.pk).update(
            status=DataRelease.Status.ACTIVE,
            first_activated_at=activated_at,
        )
        ActiveDataRelease.objects.filter(singleton_id=1).update(
            state=ActiveDataRelease.State.ACTIVE,
            release=release,
            manifest_sha256=release.manifest_sha256,
            data_contract=release.data_contract,
            activated_at=activated_at,
        )

        response = self.client.get(reverse("release-status"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        document = response.json()
        self.assertEqual(document["state"], "ACTIVE")
        self.assertEqual(
            document["active_release"],
            {
                "release_id": release.release_id,
                "manifest_sha256": release.manifest_sha256,
                "data_contract": 1,
                "activated_at": activated_at.isoformat().replace("+00:00", "Z"),
                "counts": {
                    "watersheds": 1,
                    "subcatchments": 2,
                    "channels": 3,
                    "capabilities": 1,
                },
            },
        )
        serialized = response.content.decode()
        for forbidden in (
            "attempt",
            "failure",
            "backup",
            "credential",
            "filesystem",
            "lease_owner",
        ):
            self.assertNotIn(forbidden, serialized)
