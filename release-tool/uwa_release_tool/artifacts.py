from __future__ import annotations

import hashlib
import os
import stat
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


DEFAULT_CHUNK_SIZE = 1024 * 1024


class ArtifactError(RuntimeError):
    pass


class ArtifactInputError(ArtifactError):
    pass


class ArtifactNotFound(ArtifactError):
    pass


class ArtifactIntegrityError(ArtifactError):
    pass


class ArtifactConflictError(ArtifactError):
    pass


class ArtifactPermissionError(ArtifactError):
    pass


class ArtifactTransferError(ArtifactError):
    pass


@dataclass(frozen=True)
class PublishResult:
    digest: str
    byte_count: int
    path: Path
    published: bool


@dataclass(frozen=True)
class FetchResult:
    digest: str
    byte_count: int
    path: Path
    cache_hit: bool
    recovered_corruption: bool


@dataclass(frozen=True)
class CleanupResult:
    digests: tuple[str, ...]
    entry_count: int
    byte_count: int
    dry_run: bool


ProgressCallback = Callable[[str, int], None]


def validate_digest(digest: str) -> str:
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ArtifactInputError("digest must be 64 lowercase hexadecimal characters")
    return digest


def sha256_path(path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> tuple[str, int]:
    digest = hashlib.sha256()
    byte_count = 0
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(chunk_size), b""):
                digest.update(chunk)
                byte_count += len(chunk)
    except PermissionError as error:
        raise ArtifactPermissionError("artifact bytes cannot be read") from error
    except OSError as error:
        raise ArtifactInputError("artifact bytes cannot be read") from error
    return digest.hexdigest(), byte_count


def ensure_private_directory(path: Path) -> None:
    missing = []
    candidate = path
    while not candidate.exists():
        missing.append(candidate)
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    if candidate.is_symlink() or not candidate.is_dir():
        raise ArtifactInputError("artifact directory ancestry is not a real directory")
    try:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        for created in reversed(missing):
            created.chmod(0o700)
        path.chmod(0o700)
    except PermissionError as error:
        raise ArtifactPermissionError("artifact directory cannot be created") from error
    except OSError as error:
        raise ArtifactInputError("artifact directory cannot be created") from error


def require_regular_file(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ArtifactNotFound("artifact file does not exist") from error
    except PermissionError as error:
        raise ArtifactPermissionError("artifact file cannot be inspected") from error
    except OSError as error:
        raise ArtifactInputError("artifact file cannot be inspected") from error
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise ArtifactInputError("artifact input must be a regular file")


class ArtifactClient:
    def __init__(
        self,
        store_namespace: Path,
        cache_root: Path,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        progress: ProgressCallback | None = None,
    ):
        if chunk_size <= 0:
            raise ArtifactInputError("chunk size must be positive")
        self.store_namespace = Path(store_namespace)
        self.cache_root = Path(cache_root)
        self.chunk_size = chunk_size
        self.progress = progress

    @property
    def object_root(self) -> Path:
        return self.store_namespace / "objects" / "sha256"

    def object_path(self, digest: str) -> Path:
        digest = validate_digest(digest)
        return self.object_root / digest[:2] / digest

    def cache_path(self, digest: str) -> Path:
        digest = validate_digest(digest)
        return self.cache_root / digest[:2] / digest

    def _copy_stream(self, source: BinaryIO, target: BinaryIO, operation: str) -> tuple[str, int]:
        digest = hashlib.sha256()
        byte_count = 0
        while True:
            chunk = source.read(self.chunk_size)
            if not chunk:
                break
            target.write(chunk)
            digest.update(chunk)
            byte_count += len(chunk)
            if self.progress is not None:
                self.progress(operation, byte_count)
        target.flush()
        os.fsync(target.fileno())
        return digest.hexdigest(), byte_count

    def publish(self, source: Path, *, expected_sha256: str | None = None) -> PublishResult:
        source = Path(source)
        require_regular_file(source)
        if expected_sha256 is not None:
            expected_sha256 = validate_digest(expected_sha256)

        partial_root = self.store_namespace / ".partial"
        ensure_private_directory(partial_root)
        temporary = partial_root / f"publish-{uuid.uuid4().hex}.partial"
        digest = ""
        byte_count = 0
        try:
            try:
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with source.open("rb") as source_stream, os.fdopen(descriptor, "wb") as target_stream:
                    digest, byte_count = self._copy_stream(source_stream, target_stream, "publish")
            except PermissionError as error:
                raise ArtifactPermissionError("artifact publication is not permitted") from error
            except OSError as error:
                raise ArtifactTransferError("artifact publication failed") from error
            except Exception as error:
                if isinstance(error, ArtifactError):
                    raise
                raise ArtifactTransferError("artifact publication was interrupted") from error

            if expected_sha256 is not None and digest != expected_sha256:
                raise ArtifactIntegrityError("source SHA-256 differs from the expected digest")

            destination = self.object_path(digest)
            ensure_private_directory(destination.parent)
            if destination.exists():
                observed_digest, observed_size = sha256_path(destination, self.chunk_size)
                if observed_digest != digest or observed_size != byte_count:
                    raise ArtifactConflictError("existing artifact does not match its content key")
                return PublishResult(digest, byte_count, destination, False)

            try:
                os.link(temporary, destination)
                destination.chmod(0o600)
                published = True
            except FileExistsError:
                observed_digest, observed_size = sha256_path(destination, self.chunk_size)
                if observed_digest != digest or observed_size != byte_count:
                    raise ArtifactConflictError("concurrent artifact conflicts with its content key")
                published = False
            except PermissionError as error:
                raise ArtifactPermissionError("artifact promotion is not permitted") from error
            except OSError as error:
                raise ArtifactTransferError("artifact promotion failed") from error
            return PublishResult(digest, byte_count, destination, published)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def _valid_cache_hit(self, path: Path, digest: str) -> tuple[bool, int]:
        if not path.exists() or path.is_symlink() or not path.is_file():
            return False, 0
        observed_digest, byte_count = sha256_path(path, self.chunk_size)
        return observed_digest == digest, byte_count

    def fetch(self, digest: str) -> FetchResult:
        digest = validate_digest(digest)
        source = self.object_path(digest)
        require_regular_file(source)
        destination = self.cache_path(digest)
        ensure_private_directory(destination.parent)

        valid_hit, byte_count = self._valid_cache_hit(destination, digest)
        if valid_hit:
            return FetchResult(digest, byte_count, destination, True, False)

        quarantine: Path | None = None
        if destination.exists():
            quarantine = destination.parent / f".{digest}.{uuid.uuid4().hex}.corrupt"
            try:
                os.replace(destination, quarantine)
            except PermissionError as error:
                raise ArtifactPermissionError("corrupt cache entry cannot be quarantined") from error
            except OSError as error:
                raise ArtifactTransferError("corrupt cache entry cannot be quarantined") from error

        temporary = destination.parent / f".{digest}.{uuid.uuid4().hex}.partial"
        try:
            try:
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with source.open("rb") as source_stream, os.fdopen(descriptor, "wb") as target_stream:
                    observed_digest, byte_count = self._copy_stream(source_stream, target_stream, "fetch")
            except PermissionError as error:
                raise ArtifactPermissionError("artifact fetch is not permitted") from error
            except OSError as error:
                raise ArtifactTransferError("artifact fetch failed") from error
            except Exception as error:
                if isinstance(error, ArtifactError):
                    raise
                raise ArtifactTransferError("artifact fetch was interrupted") from error

            if observed_digest != digest:
                raise ArtifactIntegrityError("stored artifact does not match its content key")
            try:
                os.replace(temporary, destination)
                destination.chmod(0o600)
            except PermissionError as error:
                raise ArtifactPermissionError("cache promotion is not permitted") from error
            except OSError as error:
                raise ArtifactTransferError("cache promotion failed") from error
            for corrupt_path in destination.parent.glob(f".{digest}.*.corrupt"):
                corrupt_path.unlink(missing_ok=True)
            return FetchResult(digest, byte_count, destination, False, quarantine is not None)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def cleanup_cache(
        self,
        *,
        retained_digests: Iterable[str] = (),
        leased_digests: Iterable[str] = (),
        max_entries: int,
        max_bytes: int,
        dry_run: bool = False,
    ) -> CleanupResult:
        if max_entries < 0 or max_bytes < 0:
            raise ArtifactInputError("cleanup limits cannot be negative")
        protected = {
            validate_digest(digest) for digest in [*retained_digests, *leased_digests]
        }
        candidates: list[tuple[int, str, Path, int]] = []
        if self.cache_root.exists():
            if self.cache_root.is_symlink() or not self.cache_root.is_dir():
                raise ArtifactInputError("cache root is not a real directory")
            for prefix in self.cache_root.iterdir():
                if prefix.is_symlink() or not prefix.is_dir() or len(prefix.name) != 2:
                    continue
                for path in prefix.iterdir():
                    if path.is_symlink() or not path.is_file():
                        continue
                    try:
                        digest = validate_digest(path.name)
                    except ArtifactInputError:
                        continue
                    if digest in protected or digest[:2] != prefix.name:
                        continue
                    metadata = path.stat()
                    candidates.append((metadata.st_mtime_ns, digest, path, metadata.st_size))

        selected: list[tuple[str, Path, int]] = []
        selected_bytes = 0
        for _, digest, path, byte_count in sorted(candidates):
            if len(selected) >= max_entries:
                break
            if selected_bytes + byte_count > max_bytes:
                continue
            selected.append((digest, path, byte_count))
            selected_bytes += byte_count

        if not dry_run:
            for _, path, _ in selected:
                try:
                    path.unlink()
                except FileNotFoundError:
                    continue
                except PermissionError as error:
                    raise ArtifactPermissionError("cache cleanup is not permitted") from error
                except OSError as error:
                    raise ArtifactTransferError("cache cleanup failed") from error

        return CleanupResult(
            tuple(digest for digest, _, _ in selected),
            len(selected),
            selected_bytes,
            dry_run,
        )
