from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from uwa_release_tool import cli  # noqa: E402


class ReleaseToolCliTests(unittest.TestCase):
    def invoke(self, *arguments: str, handlers=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = cli.run(arguments, stdout=stdout, stderr=stderr, handlers=handlers)
        output_events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        error_events = [json.loads(line) for line in stderr.getvalue().splitlines()]
        return exit_code, output_events, error_events

    def test_status_reports_all_commands_and_exit_codes(self):
        exit_code, output, errors = self.invoke("status")
        self.assertEqual(exit_code, cli.ExitCode.OK)
        self.assertFalse(errors)
        self.assertEqual(output[-1]["commands"]["prepare"], True)
        self.assertEqual(output[-1]["commands"]["validate"], True)
        self.assertEqual(output[-1]["commands"]["apply"], False)
        self.assertEqual(output[-1]["exit_codes"]["20"], "command_unavailable")

    def test_validate_verified_read_only_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            content = b'{"release_id":"fixture"}\n'
            path.write_bytes(content)
            path.chmod(0o444)
            digest = hashlib.sha256(content).hexdigest()
            exit_code, output, errors = self.invoke(
                "validate",
                "--input",
                str(path),
                "--sha256",
                digest,
                "--require-read-only",
            )
        self.assertEqual(exit_code, cli.ExitCode.OK)
        self.assertFalse(errors)
        self.assertEqual(output[-1]["input_sha256"], digest)
        self.assertEqual(output[-1]["byte_count"], len(content))

    def test_wrong_digest_is_integrity_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            path.write_text("{}\n", encoding="utf-8")
            exit_code, _, errors = self.invoke(
                "validate", "--input", str(path), "--sha256", "0" * 64
            )
        self.assertEqual(exit_code, cli.ExitCode.INTEGRITY)
        self.assertEqual(errors[-1]["error_code"], "sha256_mismatch")

    def test_missing_input_is_input_error(self):
        exit_code, _, errors = self.invoke("validate", "--input", "/missing/input.json")
        self.assertEqual(exit_code, cli.ExitCode.INPUT)
        self.assertEqual(errors[-1]["error_code"], "input_missing")

    def test_writable_input_is_rejected_when_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            path.write_text("{}\n", encoding="utf-8")
            path.chmod(0o644)
            exit_code, _, errors = self.invoke(
                "validate", "--input", str(path), "--require-read-only"
            )
        self.assertEqual(exit_code, cli.ExitCode.INPUT)
        self.assertEqual(errors[-1]["error_code"], "input_not_read_only")

    def test_malformed_json_is_contract_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            path.write_text("not-json", encoding="utf-8")
            exit_code, _, errors = self.invoke("validate", "--input", str(path))
        self.assertEqual(exit_code, cli.ExitCode.CONTRACT)
        self.assertEqual(errors[-1]["error_code"], "invalid_json")

    def test_non_object_json_is_contract_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            path.write_text("[]\n", encoding="utf-8")
            exit_code, _, errors = self.invoke("validate", "--input", str(path))
        self.assertEqual(exit_code, cli.ExitCode.CONTRACT)
        self.assertEqual(errors[-1]["error_code"], "invalid_json_root")

    def test_successor_commands_are_fatal_and_distinct(self):
        for command in {"plan", "build", "apply", "rollback", "recover"}:
            with self.subTest(command=command):
                exit_code, _, errors = self.invoke(command)
                self.assertEqual(exit_code, cli.ExitCode.COMMAND_UNAVAILABLE)
                self.assertEqual(errors[-1]["error_code"], "command_unavailable")

    def test_prepare_replays_verified_inputs_and_writes_new_outputs(self):
        from test_sources import ARTIFACT_BASE, batch_descriptor, batch_mapping, MappingFetcher
        from uwa_release_tool import artifacts, sources

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = batch_descriptor()
            descriptor_path = root / "descriptor.json"
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
            store = root / "store"
            first_client = artifacts.ArtifactClient(store, root / "first-cache")
            first = sources.prepare_sources(
                descriptor,
                client=first_client,
                artifact_base_uri=ARTIFACT_BASE,
                fetcher=MappingFetcher(batch_mapping(descriptor)),
            )
            receipt_path = root / "input-receipt.json"
            receipt_path.write_bytes(first.receipt_bytes)
            index_path = root / "output" / "index.json"
            output_receipt = root / "output" / "receipt.json"
            exit_code, output, errors = self.invoke(
                "prepare",
                "--descriptor",
                str(descriptor_path),
                "--store-namespace",
                str(store),
                "--cache-root",
                str(root / "replay-cache"),
                "--artifact-base-uri",
                ARTIFACT_BASE,
                "--output-index",
                str(index_path),
                "--output-receipt",
                str(output_receipt),
                "--replay-receipt",
                str(receipt_path),
            )
            self.assertEqual(exit_code, cli.ExitCode.OK)
            self.assertFalse(errors)
            self.assertTrue(output[-1]["replayed"])
            self.assertEqual(index_path.read_bytes(), first.index_bytes)
            self.assertEqual(output_receipt.read_bytes(), first.receipt_bytes)

    def test_prepare_routes_rhessys_descriptor_and_replay(self):
        from test_rhessys import ARTIFACT_BASE, MappingFetcher, fixture
        from uwa_release_tool import artifacts, rhessys

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor, mapping = fixture()
            descriptor_path = root / "descriptor.json"
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
            store = root / "store"
            first = rhessys.prepare_capability(
                descriptor,
                client=artifacts.ArtifactClient(store, root / "first-cache"),
                artifact_base_uri=ARTIFACT_BASE,
                fetcher=MappingFetcher(mapping),
            )
            receipt_path = root / "input-receipt.json"
            receipt_path.write_bytes(first.receipt_bytes)
            index_path = root / "output" / "index.json"
            output_receipt = root / "output" / "receipt.json"
            exit_code, output, errors = self.invoke(
                "prepare",
                "--descriptor",
                str(descriptor_path),
                "--store-namespace",
                str(store),
                "--cache-root",
                str(root / "replay-cache"),
                "--artifact-base-uri",
                ARTIFACT_BASE,
                "--output-index",
                str(index_path),
                "--output-receipt",
                str(output_receipt),
                "--replay-receipt",
                str(receipt_path),
            )
            self.assertEqual(exit_code, cli.ExitCode.OK)
            self.assertFalse(errors)
            self.assertTrue(output[-1]["replayed"])
            self.assertEqual(index_path.read_bytes(), first.index_bytes)
            self.assertEqual(output_receipt.read_bytes(), first.receipt_bytes)

    def test_unknown_command_is_structured_usage_error(self):
        exit_code, output, errors = self.invoke("unknown")
        self.assertEqual(exit_code, cli.ExitCode.USAGE)
        self.assertFalse(output)
        self.assertEqual(errors[-1]["error_code"], "usage_error")

    def test_invalid_sha_is_structured_usage_error(self):
        exit_code, _, errors = self.invoke(
            "validate", "--input", "/unused", "--sha256", "ABC"
        )
        self.assertEqual(exit_code, cli.ExitCode.USAGE)
        self.assertEqual(errors[-1]["error_code"], "usage_error")

    def test_internal_error_is_contained(self):
        def fail(_arguments):
            raise RuntimeError("sensitive internal detail")

        handlers = dict(cli.COMMAND_HANDLERS)
        handlers["status"] = fail
        exit_code, _, errors = self.invoke("status", handlers=handlers)
        self.assertEqual(exit_code, cli.ExitCode.INTERNAL)
        self.assertEqual(errors[-1]["error_code"], "internal_error")
        self.assertNotIn("sensitive internal detail", json.dumps(errors))

    def test_event_envelope_is_stable(self):
        _, output, _ = self.invoke("status")
        for event in output:
            self.assertEqual(event["schema_version"], 1)
            self.assertEqual(event["tool"], "data-release")
            self.assertEqual(event["tool_version"], "0.1.0")
            self.assertEqual(event["command"], "status")


if __name__ == "__main__":
    unittest.main()
