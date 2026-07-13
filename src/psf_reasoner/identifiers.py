"""Deterministic report-local identifiers."""

from hashlib import sha256


def make_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    digest = sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"
