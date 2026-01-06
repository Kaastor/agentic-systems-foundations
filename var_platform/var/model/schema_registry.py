from __future__ import annotations

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, TypeAdapter


class ModelSchemaRegistry:
    """Registry for model output schemas.

    This keeps *parsing + validation* a deterministic, testable step.
    Tools can reference schema names instead of carrying large schema dicts.
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, TypeAdapter[Any]] = {}

    def register_model(self, name: str, model: Type[BaseModel]) -> None:
        self._adapters[name] = TypeAdapter(model)

    def register_adapter(self, name: str, adapter: TypeAdapter[Any]) -> None:
        self._adapters[name] = adapter

    def has(self, name: str) -> bool:
        return name in self._adapters

    def validate(self, name: str, value: Any) -> Any:
        if name not in self._adapters:
            raise KeyError(f"Unknown output_schema_ref: {name}")
        return self._adapters[name].validate_python(value)

    def maybe_validate(self, name: str, value: Any) -> Optional[Any]:
        if name not in self._adapters:
            return None
        return self._adapters[name].validate_python(value)