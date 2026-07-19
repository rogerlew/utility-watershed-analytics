#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit


class ConfigurationError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def collect_artifacts(document: object) -> dict[str, dict[str, object]]:
    artifacts: dict[str, dict[str, object]] = {}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            required = {"uri", "sha256", "bytes", "media_type"}
            if required.issubset(value):
                digest = value["sha256"]
                if not isinstance(digest, str):
                    raise ConfigurationError("artifact digest is not a string")
                artifact = {key: value[key] for key in sorted(required)}
                existing = artifacts.get(digest)
                if existing is not None and existing != artifact:
                    raise ConfigurationError(
                        f"artifact metadata conflicts for digest {digest}"
                    )
                artifacts[digest] = artifact
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)
    return artifacts


def artifact_origin_path(uri: str, public_path_prefix: str) -> str:
    parsed = urlsplit(uri)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ConfigurationError(f"unsupported artifact URI: {uri}")
    if not parsed.path.startswith(public_path_prefix + "/"):
        raise ConfigurationError(f"artifact URI is outside the public prefix: {uri}")
    path = parsed.path[len(public_path_prefix) :]
    if not path.startswith("/v1/production/objects/sha256/"):
        raise ConfigurationError(f"artifact URI has an unexpected object path: {uri}")
    return path


def render_configuration(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    artifact_root: Path,
    listen_address: str,
    allowed_ips: tuple[str, ...],
    public_path_prefix: str,
) -> str:
    listen_host, separator, listen_port = listen_address.rpartition(":")
    if not separator or not listen_port.isdigit():
        raise ConfigurationError("listen address must be an IPv4 address and port")
    try:
        parsed_listen_host = ipaddress.ip_address(listen_host)
    except ValueError as error:
        raise ConfigurationError("listen address has an invalid host") from error
    if parsed_listen_host.version != 4:
        raise ConfigurationError("listen address must use IPv4")
    manifest_payload = manifest_path.read_bytes()
    observed_manifest_sha256 = sha256_bytes(manifest_payload)
    if observed_manifest_sha256 != expected_manifest_sha256:
        raise ConfigurationError("manifest SHA-256 differs from the reviewed value")
    document = json.loads(manifest_payload)
    artifacts = collect_artifacts(document)
    artifacts[expected_manifest_sha256] = {
        "bytes": len(manifest_payload),
        "media_type": "application/json",
        "sha256": expected_manifest_sha256,
            "uri": (
                "https://firewisewatersheds.org"
                f"{public_path_prefix}/v1/production/objects/sha256/"
                f"{expected_manifest_sha256[:2]}/{expected_manifest_sha256}"
            ),
    }
    paths_by_media_type: dict[str, list[str]] = defaultdict(list)
    expected_media_types = {
        "application/geo+json",
        "application/json",
        "application/vnd.apache.parquet",
        "image/tiff",
    }
    for digest, artifact in sorted(artifacts.items()):
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ConfigurationError(f"invalid artifact digest: {digest}")
        uri = artifact["uri"]
        media_type = artifact["media_type"]
        byte_size = artifact["bytes"]
        if not isinstance(uri, str) or not isinstance(media_type, str):
            raise ConfigurationError(f"invalid artifact metadata for digest {digest}")
        if media_type not in expected_media_types:
            raise ConfigurationError(f"unsupported artifact media type: {media_type}")
        origin_path = artifact_origin_path(uri, public_path_prefix)
        expected_suffix = f"/objects/sha256/{digest[:2]}/{digest}"
        if not origin_path.endswith(expected_suffix):
            raise ConfigurationError(f"artifact URI does not match digest {digest}")
        local_path = artifact_root / origin_path.removeprefix("/v1/production/")
        if not local_path.is_file() or local_path.stat().st_size != byte_size:
            raise ConfigurationError(f"artifact file differs for digest {digest}")
        paths_by_media_type[media_type].append(origin_path)

    lines = [
        "{",
        "\tadmin off",
        "\tauto_https off",
        "}",
        "",
        f"http://:{listen_port} {{",
        f"\tbind {listen_host}",
        "\t@denied not remote_ip " + " ".join(allowed_ips),
        '\trespond @denied "Forbidden" 403',
        "",
        "\troot * /srv",
    ]
    for matcher_number, (media_type, paths) in enumerate(
        sorted(paths_by_media_type.items()), start=1
    ):
        matcher = f"media_{matcher_number}"
        lines.append(f"\t@{matcher} path " + " ".join(paths))
        lines.append(f'\theader @{matcher} Content-Type "{media_type}"')
        lines.append("")
    lines.extend(
        [
            "\theader {",
            '\t\tCache-Control "public, max-age=31536000, immutable"',
            '\t\tX-Content-Type-Options "nosniff"',
            "\t}",
            "\tfile_server",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def write_atomic(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    try:
        with temporary_path.open("x", encoding="utf-8") as stream:
            os.chmod(temporary_path, 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--listen-address", required=True)
    parser.add_argument("--allowed-ip", action="append", required=True)
    parser.add_argument("--public-path-prefix", default="/artifacts")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    configuration = render_configuration(
        manifest_path=arguments.manifest,
        expected_manifest_sha256=arguments.expected_manifest_sha256,
        artifact_root=arguments.artifact_root,
        listen_address=arguments.listen_address,
        allowed_ips=tuple(arguments.allowed_ip),
        public_path_prefix=arguments.public_path_prefix.rstrip("/"),
    )
    write_atomic(arguments.output, configuration)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
