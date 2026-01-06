from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from typing import Any, Optional

from ..budgets.manager import BudgetExceeded, BudgetManager
from ..budgets.types import BudgetCategory
from ..types import Outcome, OutcomeKind, ToolError, ToolErrorCode
from ..research.redaction import to_jsonable
from ..utils import safe_format
from .types import ModelRequest, ModelResponse, ModelProvider
from .prompt_registry import PromptRegistry
from .schema_registry import ModelSchemaRegistry
from ..tools.base import Tool, ToolResult


class ModelProviderClient:
    """Provider adapter interface."""

    provider: ModelProvider = ModelProvider.mock

    def complete(self, *, rendered_prompt: str, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError


class MockProvider(ModelProviderClient):
    provider = ModelProvider.mock

    def complete(self, *, rendered_prompt: str, request: ModelRequest) -> ModelResponse:
        # Deterministic, boring: echoes the prompt tail.
        tail = rendered_prompt[-200:]
        return ModelResponse(
            text=f"[MOCK_MODEL_OUTPUT]\n{tail}",
            parsed=None,
            provider=self.provider.value,
            model="mock-echo",
            usage={"note": "mock provider; no token accounting"},
        )


@dataclass(frozen=True)
class ModelToolConfig:
    provider: ModelProvider = ModelProvider.mock
    model_name: str = "mock-echo"


class ModelCompleteTool(Tool):
    """A single typed boundary for LLM calls.

    - resolves prompt_id/version via PromptRegistry
    - renders prompt deterministically (no hidden string concatenation)
    - normalizes provider responses
    - uses ToolResult for boundary errors and Outcome for schema/policy outcome
    """

    name = "model.complete"
    version = "model-tool-v1"

    def __init__(
        self,
        *,
        prompt_registry: PromptRegistry,
        schema_registry: Optional[ModelSchemaRegistry] = None,
        provider_client: Optional[ModelProviderClient] = None,
        config: Optional[ModelToolConfig] = None,
        budgets: Optional[BudgetManager] = None,
    ):
        self._prompts = prompt_registry
        self._schemas = schema_registry or ModelSchemaRegistry()
        self._provider = provider_client or MockProvider()
        self._config = config or ModelToolConfig()
        self._budgets = budgets

    def run(self, *, request: ModelRequest) -> ToolResult[Outcome[ModelResponse]]:
        try:
            tpl = self._prompts.get(request.prompt_id, request.prompt_version)
        except KeyError as e:
            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.ValidationError,
                    retryable=False,
                    safe_message=str(e),
                    debug={"prompt_id": request.prompt_id, "prompt_version": request.prompt_version},
                )
            )

        # Deterministic rendering with explicit variables.
        try:
            rendered = safe_format(tpl.template, request.variables)
        except Exception as e:
            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.ValidationError,
                    retryable=False,
                    safe_message="Prompt rendering failed (missing variable or invalid template).",
                    debug={"error": repr(e), "prompt_id": tpl.prompt_id, "version": tpl.version},
                )
            )

        # Execute provider call (still through the Tool protocol so record/replay works).
        try:
            resp = self._provider.complete(rendered_prompt=rendered, request=request)
        except Exception as e:
            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.TransientError,
                    retryable=True,
                    safe_message="Model provider call failed.",
                    debug={"error": repr(e), "provider": self._provider.provider.value},
                )
            )

        # Budget: model token accounting is provider-specific.
        # We keep this best-effort; providers should normalize keys.
        if self._budgets is not None:
            try:
                total = int(resp.usage.get("total_tokens", 0) or 0)
                inp = int(resp.usage.get("input_tokens", 0) or 0)
                out = int(resp.usage.get("output_tokens", 0) or 0)
                if total > 0:
                    self._budgets.spend(BudgetCategory.model_total_tokens, total, reason="model_tokens")
                if inp > 0:
                    self._budgets.spend(BudgetCategory.model_input_tokens, inp, reason="model_tokens")
                if out > 0:
                    self._budgets.spend(BudgetCategory.model_output_tokens, out, reason="model_tokens")
            except BudgetExceeded as e:
                return ToolResult.failure(
                    ToolError(
                        code=ToolErrorCode.BudgetExceeded,
                        retryable=False,
                        safe_message=f"Budget exceeded: {e.category.value}",
                        debug={"category": e.category.value, "used": e.used, "limit": e.limit, "requested": e.requested},
                    )
                )

        # Schema enforcement hook.
        if (request.output_schema or request.output_schema_ref) and request.text_only:
            return ToolResult.success(
                Outcome.fail(
                    kind=OutcomeKind.Invalid,
                    value=None,
                    reason="invalid_request",
                    details={"message": "Cannot set both output_schema and text_only."},
                )
            )

        # Structured outputs:
        # - parse as JSON
        # - if output_schema_ref is present, validate via registry
        # - else accept raw JSON payload (teaching seam)
        if request.output_schema or request.output_schema_ref:
            try:
                payload = json.loads(resp.text)
            except Exception as e:
                return ToolResult.success(
                    Outcome.fail(
                        kind=OutcomeKind.Invalid,
                        value=resp,
                        reason="schema_mismatch",
                        details={"message": "Model output was not valid JSON.", "error": repr(e)},
                    )
                )

            parsed_obj: Any = payload
            if request.output_schema_ref:
                try:
                    parsed_obj = self._schemas.validate(request.output_schema_ref, payload)
                except Exception as e:
                    return ToolResult.success(
                        Outcome.fail(
                            kind=OutcomeKind.Invalid,
                            value=resp,
                            reason="schema_mismatch",
                            details={"message": "Model output failed schema validation.", "schema_ref": request.output_schema_ref, "error": repr(e)},
                        )
                    )

            resp = resp.model_copy(update={"parsed": parsed_obj})

        rendered_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        return ToolResult.success(
            Outcome.ok(
                resp,
                details={
                    "prompt_hash": tpl.template_hash,
                    "rendered_prompt_hash": rendered_hash,
                    "prompt_id": tpl.prompt_id,
                    "prompt_version": tpl.version,
                },
            )
        )
