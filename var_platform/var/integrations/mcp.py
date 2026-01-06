"""MCP adapter seam (optional / later).

MCP (Model Context Protocol) is an emerging interoperability layer for tool servers.

This repo intentionally keeps MCP out of the kernel by default:
- The kernel teaches typed tools, outcomes, orchestration, and verification.
- MCP becomes a *product-layer adapter* once students understand the core.

Two supported integration patterns (future work):
1) Export VAR tools as an MCP server (VAR as the tool host)
2) Consume MCP tools behind the existing Tool protocol (VAR as the orchestrator)

Keeping this module as a stub makes the seam explicit without adding dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MCPToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None


class MCPClient:
    def list_tools(self) -> list[MCPToolSpec]:
        raise NotImplementedError

    def call_tool(self, name: str, *, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
