from __future__ import annotations

import concurrent.futures
import hashlib
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from uwa_release_tool import artifacts  # noqa: E402


class ArtifactClientTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = self.root / "store"
        self.cache = self.root / "cache"
        self.store.mkdir(mode=0o700)
        self.client = artifacts.ArtifactClient(self.store, self.cache, chunk_size=7)

    def tearDown(self):
        self.temporary.cleanup()

    def source(self, name: str, content: bytes) -> Path:
        path = self.root / name
        path.write_bytes(content)
        return path

    def test_publish_and_fetch_streaming(self):
        source = self.source("source", b"streaming-content" * 20)
        published = self.client.publish(source)
        fetched = self.client.fetch(published.digest)
        self.assertTrue(published.published)
        self.assertFalse(fetched.cache_hit)
        self.assertEqual(fetched.path.read_bytes(), source.read_bytes())
        self.assertEqual(self.client.fetch(published.digest).cache_hit, True)

    def test_created_store_and_cache_directories_are_private(self):
        published = self.client.publish(self.source("source", b"private-tree"))
        fetched = self.client.fetch(published.digest)
        for path in [
            self.store / ".partial",
            self.store / "objects",
            self.store / "objects" / "sha256",
            published.path.parent,
            self.cache,
            fetched.path.parent,
        ]:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(published.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(fetched.path.stat().st_mode), 0o600)

    def test_publish_is_idempotent(self):
        source = self.source("source", b"same")
        first = self.client.publish(source)
        second = self.client.publish(source)
        self.assertTrue(first.published)
        self.assertFalse(second.published)
        self.assertEqual(first.path, second.path)

    def test_wrong_expected_checksum_leaves_no_object_or_partial(self):
        source = self.source("source", b"wrong-checksum")
        with self.assertRaises(artifacts.ArtifactIntegrityError):
            self.client.publish(source, expected_sha256="0" * 64)
        self.assertFalse(self.client.object_root.exists())
        self.assertEqual(list((self.store / ".partial").iterdir()), [])

    def test_interrupted_publish_leaves_no_object_or_partial(self):
        def interrupt(_operation: str, _byte_count: int) -> None:
            raise RuntimeError("stop")

        client = artifacts.ArtifactClient(self.store, self.cache, chunk_size=2, progress=interrupt)
        with self.assertRaises(artifacts.ArtifactTransferError):
            client.publish(self.source("source", b"interrupted"))
        self.assertFalse(client.object_root.exists())
        self.assertEqual(list((self.store / ".partial").iterdir()), [])

    def test_interrupted_fetch_leaves_no_cache_or_partial(self):
        published = self.client.publish(self.source("source", b"interrupted-fetch"))

        def interrupt(operation: str, _byte_count: int) -> None:
            if operation == "fetch":
                raise RuntimeError("stop")

        client = artifacts.ArtifactClient(
            self.store,
            self.root / "interrupted-cache",
            chunk_size=2,
            progress=interrupt,
        )
        with self.assertRaises(artifacts.ArtifactTransferError):
            client.fetch(published.digest)
        self.assertFalse(client.cache_path(published.digest).exists())
        self.assertEqual(list(client.cache_path(published.digest).parent.glob("*.partial")), [])

    def test_stored_wrong_bytes_fail_without_cache_promotion(self):
        expected = hashlib.sha256(b"expected").hexdigest()
        object_path = self.client.object_path(expected)
        object_path.parent.mkdir(parents=True)
        object_path.write_bytes(b"wrong")
        with self.assertRaises(artifacts.ArtifactIntegrityError):
            self.client.fetch(expected)
        self.assertFalse(self.client.cache_path(expected).exists())

    def test_corrupt_cache_is_replaced_atomically(self):
        published = self.client.publish(self.source("source", b"correct"))
        cached = self.client.fetch(published.digest)
        cached.path.write_bytes(b"corrupt")
        recovered = self.client.fetch(published.digest)
        self.assertTrue(recovered.recovered_corruption)
        self.assertEqual(recovered.path.read_bytes(), b"correct")
        self.assertEqual(list(recovered.path.parent.glob("*.corrupt")), [])

    def test_concurrent_fetches_return_verified_bytes(self):
        content = b"concurrent" * 1000
        published = self.client.publish(self.source("source", content))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: self.client.fetch(published.digest), range(16)))
        self.assertTrue(all(result.path.read_bytes() == content for result in results))
        self.assertEqual(list(results[0].path.parent.glob("*.partial")), [])

    def test_missing_object_is_distinct(self):
        with self.assertRaises(artifacts.ArtifactNotFound):
            self.client.fetch("0" * 64)

    def test_permission_denial_is_distinct(self):
        published = self.client.publish(self.source("source", b"private"))
        published.path.chmod(0)
        try:
            with self.assertRaises(artifacts.ArtifactPermissionError):
                self.client.fetch(published.digest)
        finally:
            published.path.chmod(0o600)

    def test_existing_store_conflict_is_rejected(self):
        source = self.source("source", b"expected")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        destination = self.client.object_path(digest)
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"different")
        with self.assertRaises(artifacts.ArtifactConflictError):
            self.client.publish(source)
        self.assertEqual(destination.read_bytes(), b"different")

    def test_test_and_production_namespaces_are_isolated(self):
        published = self.client.publish(self.source("source", b"test-only"))
        production = artifacts.ArtifactClient(self.root / "production", self.root / "prod-cache")
        (self.root / "production").mkdir()
        with self.assertRaises(artifacts.ArtifactNotFound):
            production.fetch(published.digest)

    def test_store_has_no_delete_api(self):
        self.assertFalse(hasattr(self.client, "delete"))
        self.assertFalse(hasattr(self.client, "cleanup_store"))

    def test_cleanup_is_bounded_and_protects_retained_and_leased(self):
        records = [
            self.client.publish(self.source(f"source-{index}", f"content-{index}".encode()))
            for index in range(4)
        ]
        for index, record in enumerate(records):
            cached = self.client.fetch(record.digest).path
            os.utime(cached, ns=(index + 1, index + 1))
        preview = self.client.cleanup_cache(
            retained_digests=[records[0].digest],
            leased_digests=[records[1].digest],
            max_entries=1,
            max_bytes=100,
            dry_run=True,
        )
        self.assertEqual(preview.digests, (records[2].digest,))
        self.assertTrue(self.client.cache_path(records[2].digest).exists())
        removed = self.client.cleanup_cache(
            retained_digests=[records[0].digest],
            leased_digests=[records[1].digest],
            max_entries=1,
            max_bytes=100,
        )
        self.assertEqual(removed.digests, preview.digests)
        self.assertFalse(self.client.cache_path(records[2].digest).exists())
        self.assertTrue(self.client.cache_path(records[0].digest).exists())
        self.assertTrue(self.client.cache_path(records[1].digest).exists())
        self.assertTrue(self.client.object_path(records[2].digest).exists())

    def test_cleanup_does_not_follow_prefix_symlink(self):
        outside = self.root / "outside"
        outside.mkdir()
        outside_file = outside / ("a" * 64)
        outside_file.write_bytes(b"outside")
        self.cache.mkdir()
        (self.cache / "aa").symlink_to(outside, target_is_directory=True)
        result = self.client.cleanup_cache(max_entries=10, max_bytes=1000)
        self.assertEqual(result.entry_count, 0)
        self.assertTrue(outside_file.exists())

    def test_symlink_source_is_rejected(self):
        source = self.source("source", b"source")
        link = self.root / "link"
        link.symlink_to(source)
        with self.assertRaises(artifacts.ArtifactInputError):
            self.client.publish(link)


if __name__ == "__main__":
    unittest.main()
