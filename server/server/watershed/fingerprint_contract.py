import hashlib
import json
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any


FINGERPRINT_VERSION = 1


class FingerprintError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise FingerprintError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_float=Decimal,
        object_pairs_hook=unique_object,
    )


def canonical_decimal(value: Decimal | int) -> str:
    decimal_value = value if isinstance(value, Decimal) else Decimal(value)
    if not decimal_value.is_finite():
        raise FingerprintError("non-finite numbers are not canonical")
    if decimal_value == 0:
        return "0"
    rendered = format(decimal_value.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, float):
        raise FingerprintError("binary floating-point values are prohibited")
    if isinstance(value, (int, Decimal)):
        return canonical_decimal(value)
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [canonical_value(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise FingerprintError("object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise FingerprintError(
                    f"object key normalization collision: {normalized_key}"
                )
            normalized[normalized_key] = canonical_value(item)
        return normalized
    raise FingerprintError(f"unsupported canonical type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    normalized = canonical_value(value)
    rendered = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{rendered}\n".encode()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
