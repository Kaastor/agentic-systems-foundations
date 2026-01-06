from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelProvider(str, Enum):
    mock = "mock"
    openai = "openai"


class DecodingParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    max_tokens: int = Field(default=512, ge=1, le=4096)


class ModelRequest(BaseModel):
    """A structured model invocation request.

    NOTE: Tools should *produce* a ModelRequest; the model boundary executes it.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_id: str
    prompt_version: str
    variables: Dict[str, Any] = Field(default_factory=dict)

    # Either:
    # - text_only=True (free-form text)
    # - or provide a schema reference for structured outputs.
    #
    # `output_schema` is kept for backwards compatibility and as a teaching seam;
    # prefer `output_schema_ref` which plugs into a registry and can be validated
    # deterministically.
    text_only: bool = False
    output_schema_ref: Optional[str] = None
    output_schema: Optional[Dict[str, Any]] = None

    decoding: DecodingParams = Field(default_factory=DecodingParams)

    safety_policy_ref: str = "default"


class ModelResponse(BaseModel):
    """The normalized response from a provider."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    parsed: Optional[Any] = None  # parsed output if schema-driven
    provider: str
    model: str
    usage: Dict[str, Any] = Field(default_factory=dict)
