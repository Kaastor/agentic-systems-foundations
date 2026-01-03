from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from pydantic import BaseModel

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
    if isinstance(value, str):
        return {"sha256": stable_hash(value), "len": len(value)}
    try:
        return {"sha256": stable_hash(value)}
    except Exception:
        return {"sha256": stable_hash(repr(value))}


def to_jsonable(obj: Any) -> Any:
    """Convert common objects into JSON-serializable structures."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Mapping):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    # Fallback: repr
    return repr(obj)


def redact_jsonable(
    payload: Any,
    *,
    max_str_chars: int = 4000,
    sensitive_keys: Sequence[str] = tuple(SENSITIVE_KEYS),
    drop_error_debug: bool = True,
) -> Any:
    """Redact secrets and truncate noisy strings in a JSON-like payload."""
    sensitive = set(sensitive_keys)

    def _walk(x: Any) -> Any:
        if x is None:
            return None
        if isinstance(x, str):
            return truncate_text(x, max_str_chars)
        if isinstance(x, (int, float, bool)):
            return x
        if isinstance(x, list):
            return [_walk(v) for v in x]
        if isinstance(x, dict):
            out: Dict[str, Any] = {}
            for k, v in x.items():
                ks = str(k)
                if ks in sensitive:
                    out[ks] = {"__redacted__": True, **_hash_and_length(v)}
                    continue
                if drop_error_debug and ks == "debug" and isinstance(v, dict):
                    # ToolError.debug is meant for server-side logs.
                    out[ks] = {"__dropped__": True}
                    continue
                out[ks] = _walk(v)
            return out
        return repr(x)

    return _walk(payload)
