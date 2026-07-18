from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from collections.abc import Callable, Sequence
from enum import IntEnum
from pathlib import Path
from typing import Any, TextIO

from . import artifacts, rhessys, sources

__version__ = "0.1.0"


COMMANDS = (
    "prepare",
    "validate",
    "plan",
    "build",
    "apply",
    "rollback",
    "recover",
    "status",
)


class ExitCode(IntEnum):
    OK = 0
    USAGE = 2
    INPUT = 10
    INTEGRITY = 11
    CONTRACT = 12
    COMMAND_UNAVAILABLE = 20
    STATE_CONFLICT = 30
    MUTATION_REFUSED = 40
    INTERNAL = 70


EXIT_CODE_NAMES = {code.value: code.name.lower() for code in ExitCode}


class CommandError(RuntimeError):
    def __init__(self, exit_code: ExitCode, error_code: str, message: str):
        super().__init__(message)
        self.exit_code = exit_code
        self.error_code = error_code


class StructuredArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CommandError(ExitCode.USAGE, "usage_error", message)


def emit(
    stream: TextIO,
    *,
    event: str,
    level: str,
    command: str,
    **fields: Any,
) -> None:
    document = {
        "schema_version": 1,
        "tool": "data-release",
        "tool_version": __version__,
        "event": event,
        "level": level,
        "command": command,
        **fields,
    }
    stream.write(json.dumps(document, separators=(",", ":"), sort_keys=True) + "\n")
    stream.flush()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def expected_sha256(value: str) -> str:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise argparse.ArgumentTypeError("SHA-256 must be 64 lowercase hexadecimal characters")
    return value


def build_parser() -> StructuredArgumentParser:
    parser = StructuredArgumentParser(prog="data-release")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in COMMANDS:
        command_parser = subparsers.add_parser(command)
        if command == "prepare":
            command_parser.add_argument("--descriptor", required=True, type=Path)
            command_parser.add_argument("--store-namespace", required=True, type=Path)
            command_parser.add_argument("--cache-root", required=True, type=Path)
            command_parser.add_argument("--artifact-base-uri", required=True)
            command_parser.add_argument("--output-index", required=True, type=Path)
            command_parser.add_argument("--output-receipt", required=True, type=Path)
            command_parser.add_argument("--replay-receipt", type=Path)
        elif command == "validate":
            command_parser.add_argument("--input", required=True, type=Path)
            command_parser.add_argument("--sha256", type=expected_sha256)
            command_parser.add_argument("--require-read-only", action="store_true")
    return parser


def require_regular_input(path: Path, require_read_only: bool) -> bytes:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise CommandError(ExitCode.INPUT, "input_missing", "input file does not exist") from error
    except OSError as error:
        raise CommandError(ExitCode.INPUT, "input_unreadable", "input file cannot be inspected") from error

    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise CommandError(ExitCode.INPUT, "input_not_regular", "input must be a regular file")
    if require_read_only and metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise CommandError(ExitCode.INPUT, "input_not_read_only", "input has a writable mode")
    try:
        return path.read_bytes()
    except OSError as error:
        raise CommandError(ExitCode.INPUT, "input_unreadable", "input file cannot be read") from error


def validate_command(arguments: argparse.Namespace) -> dict[str, Any]:
    content = require_regular_input(arguments.input, arguments.require_read_only)
    digest = sha256_bytes(content)
    if arguments.sha256 is not None and digest != arguments.sha256:
        raise CommandError(
            ExitCode.INTEGRITY,
            "sha256_mismatch",
            "input SHA-256 differs from the expected digest",
        )
    try:
        document = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CommandError(ExitCode.CONTRACT, "invalid_json", "input is not valid UTF-8 JSON") from error
    if not isinstance(document, dict):
        raise CommandError(ExitCode.CONTRACT, "invalid_json_root", "input JSON root must be an object")
    return {
        "byte_count": len(content),
        "input_sha256": digest,
        "read_only_required": arguments.require_read_only,
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    content = require_regular_input(path, False)
    try:
        document = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CommandError(ExitCode.CONTRACT, "invalid_json", "input is not valid UTF-8 JSON") from error
    if not isinstance(document, dict):
        raise CommandError(ExitCode.CONTRACT, "invalid_json_root", "input JSON root must be an object")
    return document


def _write_new_file(path: Path, content: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise CommandError(ExitCode.STATE_CONFLICT, "output_exists", "output path already exists")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o644)
            os.link(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    except CommandError:
        raise
    except FileExistsError as error:
        raise CommandError(ExitCode.STATE_CONFLICT, "output_exists", "output path already exists") from error
    except OSError as error:
        raise CommandError(ExitCode.INPUT, "output_unwritable", "output file cannot be written") from error


def prepare_command(arguments: argparse.Namespace) -> dict[str, Any]:
    descriptor = _read_json_object(arguments.descriptor)
    receipt = (
        _read_json_object(arguments.replay_receipt)
        if arguments.replay_receipt is not None
        else None
    )
    client = artifacts.ArtifactClient(arguments.store_namespace, arguments.cache_root)
    try:
        if descriptor.get("kind") == "rhessys-capability":
            result = rhessys.prepare_capability(
                descriptor,
                client=client,
                artifact_base_uri=arguments.artifact_base_uri,
                replay_receipt=receipt,
            )
        else:
            result = sources.prepare_sources(
                descriptor,
                client=client,
                artifact_base_uri=arguments.artifact_base_uri,
                replay_receipt=receipt,
            )
    except rhessys.RhessysDescriptorError as error:
        raise CommandError(ExitCode.CONTRACT, "rhessys_descriptor_invalid", str(error)) from error
    except rhessys.RhessysFormatError as error:
        raise CommandError(ExitCode.CONTRACT, "rhessys_format_invalid", str(error)) from error
    except rhessys.RhessysIntegrityError as error:
        raise CommandError(ExitCode.INTEGRITY, "rhessys_integrity_failed", str(error)) from error
    except rhessys.RhessysFetchError as error:
        raise CommandError(ExitCode.INPUT, "rhessys_fetch_failed", str(error)) from error
    except sources.SourceDescriptorError as error:
        raise CommandError(ExitCode.CONTRACT, "source_descriptor_invalid", str(error)) from error
    except sources.SourceMembershipError as error:
        raise CommandError(ExitCode.CONTRACT, "source_membership_invalid", str(error)) from error
    except sources.SourceFormatError as error:
        raise CommandError(ExitCode.CONTRACT, "source_format_invalid", str(error)) from error
    except sources.SourceIntegrityError as error:
        raise CommandError(ExitCode.INTEGRITY, "source_integrity_failed", str(error)) from error
    except sources.SourceFetchError as error:
        raise CommandError(ExitCode.INPUT, "source_fetch_failed", str(error)) from error
    except artifacts.ArtifactIntegrityError as error:
        raise CommandError(ExitCode.INTEGRITY, "artifact_integrity_failed", str(error)) from error
    except artifacts.ArtifactError as error:
        raise CommandError(ExitCode.INPUT, "artifact_operation_failed", str(error)) from error
    _write_new_file(arguments.output_index, result.index_bytes)
    try:
        _write_new_file(arguments.output_receipt, result.receipt_bytes)
    except CommandError:
        arguments.output_index.unlink(missing_ok=True)
        raise
    return {
        "index_sha256": result.index_artifact.digest,
        "receipt_sha256": result.receipt_artifact.digest,
        "member_count": result.member_count,
        "source_count": result.source_count,
        "replayed": result.replayed,
    }


def status_command(arguments: argparse.Namespace) -> dict[str, Any]:
    del arguments
    availability = {command: command in {"prepare", "validate", "status"} for command in COMMANDS}
    return {
        "commands": availability,
        "exit_codes": {str(code): name for code, name in sorted(EXIT_CODE_NAMES.items())},
    }


def unavailable_command(arguments: argparse.Namespace) -> dict[str, Any]:
    raise CommandError(
        ExitCode.COMMAND_UNAVAILABLE,
        "command_unavailable",
        f"{arguments.command} is reserved for a successor package",
    )


CommandHandler = Callable[[argparse.Namespace], dict[str, Any]]
COMMAND_HANDLERS: dict[str, CommandHandler] = {
    command: unavailable_command for command in COMMANDS
}
COMMAND_HANDLERS.update(
    {"prepare": prepare_command, "validate": validate_command, "status": status_command}
)


def command_hint(arguments: Sequence[str]) -> str:
    return next((value for value in arguments if value in COMMANDS), "unknown")


def run(
    arguments: Sequence[str],
    *,
    stdout: TextIO,
    stderr: TextIO,
    handlers: dict[str, CommandHandler] | None = None,
) -> int:
    command = command_hint(arguments)
    try:
        parsed = build_parser().parse_args(list(arguments))
        command = parsed.command
        emit(stdout, event="command.start", level="info", command=command)
        result = (handlers or COMMAND_HANDLERS)[command](parsed)
        emit(
            stdout,
            event="command.result",
            level="info",
            command=command,
            status="ok",
            exit_code=ExitCode.OK,
            **result,
        )
        return ExitCode.OK
    except CommandError as error:
        emit(
            stderr,
            event="command.error",
            level="error",
            command=command,
            status="failed",
            exit_code=error.exit_code,
            exit_name=EXIT_CODE_NAMES[error.exit_code],
            error_code=error.error_code,
            message=str(error),
        )
        return error.exit_code
    except Exception:
        emit(
            stderr,
            event="command.error",
            level="error",
            command=command,
            status="failed",
            exit_code=ExitCode.INTERNAL,
            exit_name=EXIT_CODE_NAMES[ExitCode.INTERNAL],
            error_code="internal_error",
            message="unexpected internal error",
        )
        return ExitCode.INTERNAL


def main(arguments: Sequence[str] | None = None) -> int:
    return run(
        sys.argv[1:] if arguments is None else arguments,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
