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
        for command in {"prepare", "plan", "build", "apply", "rollback", "recover"}:
            with self.subTest(command=command):
                exit_code, _, errors = self.invoke(command)
                self.assertEqual(exit_code, cli.ExitCode.COMMAND_UNAVAILABLE)
                self.assertEqual(errors[-1]["error_code"], "command_unavailable")

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
