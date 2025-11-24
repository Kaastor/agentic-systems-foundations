from __future__ import annotations

from typing import Any, Dict, Generic, List, Type, TypeVar

from pydantic import BaseModel, Field

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class ToolMetadata(BaseModel):
    """Description of a tool that the LLM can see (Module 1 / 2)."""

    name: str
    description: str
    is_write: bool = False
    dangerous: bool = False

    # Very small "manifest" extras for teaching:
    # - latency_class: rough sense of how slow the tool is.
    # - permissions: which capabilities are needed to call it.
    latency_class: str = "unknown"
    permissions: List[str] = Field(default_factory=list)


class Tool(Generic[InputT, OutputT]):
    """A small, typed wrapper around a Python function."""

    def __init__(
        self,
        metadata: ToolMetadata,
        input_model: Type[InputT],
        output_model: Type[OutputT],
        func: Any,
    ) -> None:
        self.metadata = metadata
        self.input_model = input_model
        self.output_model = output_model
        self.func = func

    def __call__(self, raw_input: Dict[str, Any]) -> OutputT:
        # Pydantic-based input validation lives here (Module 1).
        model_input = self.input_model(**raw_input)
        return self.func(model_input)


class ToolRegistry:
    """Holds all tools available to an agent."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool[Any, Any]] = {}

    def register(self, tool: Tool[Any, Any]) -> None:
        if tool.metadata.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.metadata.name}")
        self._tools[tool.metadata.name] = tool

    def get(self, name: str) -> Tool[Any, Any]:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def list_metadata(self) -> List[ToolMetadata]:
        return [t.metadata for t in self._tools.values()]

    def as_llm_spec(self) -> List[Dict[str, Any]]:
        """Very lightweight spec for use in prompts / function-calling."""
        specs: List[Dict[str, Any]] = []
        for tool in self._tools.values():
            specs.append(
                {
                    "name": tool.metadata.name,
                    "description": tool.metadata.description,
                    "is_write": tool.metadata.is_write,
                    "dangerous": tool.metadata.dangerous,
                    "latency_class": tool.metadata.latency_class,
                    "permissions": tool.metadata.permissions,
                    "input_schema": tool.input_model.model_json_schema(),
                    "output_schema": tool.output_model.model_json_schema(),
                }
            )
        return specs
