from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Mapping, Sequence

from pydantic import BaseModel, SecretStr

from ..types import stable_hash


SENSITIVE_KEYS = {
    "reference_solution",
    "hidden_tests",
    "learner_code",
}


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 30] + "\n...<truncated>...\n" + text[-20:]


def _hash_and_length(value: Any) -> Dict[str, Any]:
    """Return a stable digest + a lightweight size hint.

    Used to keep logs publishable without losing reproducibility hooks.
    """
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    if isinstance(value, str):
        return {"sha256": stable_hash(value), "len": len(value)}
    try:
        return {"sha256": stable_hash(value)}
    except Exception:
        return {"sha256": stable_hash(repr(value))}


def to_jsonable(obj: Any, *, reveal_secrets: bool = False) -> Any:
    """Convert common objects into JSON-serializable structures.

    IMPORTANT: reveal_secrets=True is intended ONLY for local, private artifacts
    required for deterministic replay (e.g. FileRunStore full capture).
    """
    if obj is None:
        return None
    if isinstance(obj, SecretStr):
        return obj.get_secret_value() if reveal_secrets else str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, BaseModel):
        # Use python mode so SecretStr objects survive until we process them.
        return to_jsonable(obj.model_dump(mode="python"), reveal_secrets=reveal_secrets)
    if isinstance(obj, Mapping):
        return {str(k): to_jsonable(v, reveal_secrets=reveal_secrets) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v, reveal_secrets=reveal_secrets) for v in obj]
    # Fallback: repr
    return repr(obj)


def redact_jsonable(
    payload: Any,
    *,
    max_str_chars: int = 4000,
    sensitive_keys: Sequence[str] = tuple(SENSITIVE_KEYS),
    drop_error_debug: bool = True,
) -> Any:
    """Redact sensitive payload fields, preserving hashes for reproducibility."""
    if payload is None:
        return None

    if isinstance(payload, SecretStr):
        return _hash_and_length(payload.get_secret_value())

    if isinstance(payload, str):
        return truncate_text(payload, max_str_chars)

    if isinstance(payload, Mapping):
        out: Dict[str, Any] = {}
        for k, v in payload.items():
            ks = str(k)
            if ks in sensitive_keys:
                out[ks] = _hash_and_length(v)
                continue
            if ks == "debug" and drop_error_debug:
                # Drop error debug by default in publishable logs
                out[ks] = "<dropped>"
                continue
            out[ks] = redact_jsonable(v, max_str_chars=max_str_chars, sensitive_keys=sensitive_keys, drop_error_debug=drop_error_debug)
        return out

    if isinstance(payload, list):
        return [redact_jsonable(v, max_str_chars=max_str_chars, sensitive_keys=sensitive_keys, drop_error_debug=drop_error_debug) for v in payload]

    return payload
