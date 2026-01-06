from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, SecretStr


SCHEMA_VERSION = "v0.2"


def utc_now() -> datetime:
    """UTC timestamp helper used across traces and artifacts."""

    return datetime.now(timezone.utc)


def _json_default(x: Any) -> Any:
    """Best-effort JSON default for stable hashing.

    Hashes are used for replay keys and loop detection, so we want hashing to be:
    - stable across runs
    - robust to enums / pydantic models / SecretStr
    """

    if isinstance(x, SecretStr):
        return x.get_secret_value()
    if isinstance(x, Enum):
        return x.value
    if isinstance(x, BaseModel):
        # Use python mode to preserve SecretStr objects until _json_default sees them.
        return x.model_dump(mode="python")
    return repr(x)


def stable_hash(obj: Any) -> str:
    """Compute a stable SHA-256 hash for JSON-serializable content."""

    payload = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
