from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "generate_artifact_origin_caddy.py"
SPEC = importlib.util.spec_from_file_location("generate_artifact_origin_caddy", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ArtifactOriginConfigurationTests(unittest.TestCase):
    def build_fixture(self, root: Path):
        artifact_payload = b"PAR1fixture"
        artifact_digest = MODULE.sha256_bytes(artifact_payload)
        artifact_path = root / "objects" / "sha256" / artifact_digest[:2] / artifact_digest
        artifact_path.parent.mkdir(parents=True)
        artifact_path.write_bytes(artifact_payload)
        document = {
            "members": [
                {
                    "artifact": {
                        "bytes": len(artifact_payload),
                        "media_type": "application/vnd.apache.parquet",
                        "sha256": artifact_digest,
                        "uri": (
                            "https://firewisewatersheds.org/artifacts/v1/production/"
                            f"objects/sha256/{artifact_digest[:2]}/{artifact_digest}"
                        ),
                    }
                }
            ]
        }
        manifest_payload = json.dumps(document, sort_keys=True).encode()
        manifest_digest = MODULE.sha256_bytes(manifest_payload)
        manifest_path = root / "objects" / "sha256" / manifest_digest[:2] / manifest_digest
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(manifest_payload)
        return manifest_path, manifest_digest, artifact_digest

    def test_render_restricts_origin_and_maps_content_type(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path, manifest_digest, artifact_digest = self.build_fixture(root)
            configuration = MODULE.render_configuration(
                manifest_path=manifest_path,
                expected_manifest_sha256=manifest_digest,
                artifact_root=root,
                listen_address="100.87.36.38:18080",
                allowed_ips=("100.74.181.119", "100.87.36.38"),
                public_path_prefix="/artifacts",
            )
            self.assertIn("http://:18080", configuration)
            self.assertIn("bind 100.87.36.38", configuration)
            self.assertIn("@denied not remote_ip 100.74.181.119 100.87.36.38", configuration)
            self.assertIn('Content-Type "application/vnd.apache.parquet"', configuration)
            self.assertIn(artifact_digest, configuration)

    def test_wrong_manifest_digest_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path, _, _ = self.build_fixture(root)
            with self.assertRaisesRegex(MODULE.ConfigurationError, "manifest SHA-256"):
                MODULE.render_configuration(
                    manifest_path=manifest_path,
                    expected_manifest_sha256="0" * 64,
                    artifact_root=root,
                    listen_address="100.87.36.38:18080",
                    allowed_ips=("100.74.181.119",),
                    public_path_prefix="/artifacts",
                )

    def test_missing_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path, manifest_digest, artifact_digest = self.build_fixture(root)
            artifact_path = root / "objects" / "sha256" / artifact_digest[:2] / artifact_digest
            artifact_path.unlink()
            with self.assertRaisesRegex(MODULE.ConfigurationError, artifact_digest):
                MODULE.render_configuration(
                    manifest_path=manifest_path,
                    expected_manifest_sha256=manifest_digest,
                    artifact_root=root,
                    listen_address="100.87.36.38:18080",
                    allowed_ips=("100.74.181.119",),
                    public_path_prefix="/artifacts",
                )


if __name__ == "__main__":
    unittest.main()
