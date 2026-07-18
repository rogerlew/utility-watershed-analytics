from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "verify_release_tool_image.py"
SPEC = importlib.util.spec_from_file_location("verify_release_tool_image", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReleaseToolImageVerifierTests(unittest.TestCase):
    def test_clean_members_pass(self):
        names = [
            "opt/release-tool/uwa_release_tool/cli.py",
            "usr/local/bin/python3",
        ]
        self.assertEqual(MODULE.prohibited_member_names(names), [])

    def test_environment_file_fails(self):
        self.assertEqual(MODULE.prohibited_member_names(["work/.env"]), ["/work/.env"])

    def test_release_manifest_fails(self):
        self.assertEqual(
            MODULE.prohibited_member_names(["inputs/release-manifest.json"]),
            ["/inputs/release-manifest.json"],
        )

    def test_source_tree_fails(self):
        self.assertEqual(
            MODULE.prohibited_member_names(["data-releases/releases/example.json"]),
            ["/data-releases/releases/example.json"],
        )


if __name__ == "__main__":
    unittest.main()
