from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Dict, Any

import requests
from pydantic import BaseModel, ValidationError

from agentic.core.state import AgentState, Plan, PlanStep
from agentic.core.tools import ToolMetadata
from agentic.llm.base import LLM
from agentic.llm.stubs import RuleBasedLLM


class _PlanStepJSON(BaseModel):
    id: str
    description: str
    tool_name: str | None = None


class _PlanJSON(BaseModel):
    steps: List[_PlanStepJSON]


@dataclass
class GroqLLM(LLM):
    """LLM implementation that talks to Groq's OpenAI-compatible API.

    This class keeps the integration deliberately small and explicit. It uses
    the `/chat/completions` endpoint and asks the model to emit JSON that we
    parse into the :class:`Plan` structure used by the rest of the system.
    """

    api_key: str
    model: str
    base_url: str = "https://api.groq.com/openai/v1"
    timeout_seconds: int = 20

    def make_plan(self, user_message: str, tools: List[ToolMetadata]) -> Plan:
        try:
            raw = self._chat_completion(self._build_planner_messages(user_message, tools), temperature=0.2)
            content = raw["choices"][0]["message"]["content"]
            data = json.loads(content)
            plan_json = _PlanJSON.model_validate(data)
            steps: List[PlanStep] = []
            known_tools = {t.name for t in tools}
            for s in plan_json.steps:
                tool_name = s.tool_name
                if tool_name is not None and tool_name not in known_tools:
                    tool_name = None
                steps.append(
                    PlanStep(
                        id=s.id,
                        description=s.description,
                        tool_name=tool_name,
                    )
                )
            if not steps:
                raise ValueError("Model returned an empty plan.")
            return Plan(steps=steps, current_index=0)
        except (requests.RequestException, ValidationError, json.JSONDecodeError, KeyError, ValueError):
            # Fall back to local deterministic planner so the rest of the
            # system still works even if the network or model misbehaves.
            fallback = RuleBasedLLM()
            return fallback.make_plan(user_message, tools)

    def summarize_run(self, state: AgentState) -> str:
        try:
            raw = self._chat_completion(self._build_summary_messages(state), temperature=0.2)
            return raw["choices"][0]["message"]["content"].strip()
        except (requests.RequestException, KeyError, json.JSONDecodeError):
            return RuleBasedLLM().summarize_run(state)

    # ---- helpers ----------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout_seconds)
        resp.raise_for_status()
        return resp.json()

    def _build_planner_messages(self, user_message: str, tools: List[ToolMetadata]) -> List[Dict[str, str]]:
        tool_lines = []
        for t in tools:
            kind = "WRITE" if t.is_write else "READ"
            danger = "DANGEROUS" if t.dangerous else "safe"
            tool_lines.append(f"- {t.name} ({kind}, {danger}): {t.description}")
        tool_block = "\n".join(tool_lines)
        allowed_tool_names = ", ".join(sorted(t.name for t in tools))

        system = (
            "You are a planning component in an email triage and calendar scheduling agent. "
            "Your job is to output a small JSON plan describing concrete steps using the "
            "available tools. The agent will later execute one tool per step. "
            "Respond with VALID JSON only, using this schema:\n\n"
            "{\"steps\": [ {\"id\": \"short_id\", \"description\": \"what the step does\", "
            "\"tool_name\": \"one of: " + allowed_tool_names + " or null\"} ] }\n\n"
            "Rules:\n"
            "- Use each tool at most once unless it clearly needs repetition.\n"
            "- Prefer simple, linear plans (1-5 steps).\n"
            "- If a tool is not needed, omit it entirely.\n"
            "- If scheduling is not requested, you can skip calendar tools.\n"
            "- Do not add commentary or prose, only output JSON."
        )

        user = (
            "Available tools are:\n"
            f"{tool_block}\n\n"
            "User request:\n"
            f"{user_message}\n\n"
            "Produce a JSON plan in the schema described by the system message."
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _build_summary_messages(self, state: AgentState) -> List[Dict[str, str]]:
        if state.plan:
            parts = []
            for step in state.plan.steps:
                parts.append(
                    f"- [{step.status.value}] {step.id}: {step.description} (tool={step.tool_name})"
                )
            plan_desc = "\n".join(parts)
        else:
            plan_desc = "<no plan>"

        tools_used = ", ".join({c.tool_name for c in state.tool_calls}) if state.tool_calls else "none"

        system = (
            "You are a summariser for an email triage and scheduling agent. "
            "Write a short, clear summary suitable for showing to the end user. "
            "Explain what actions were taken and any follow-ups they should expect."
        )

        user = (
            f"User message: {state.user_message}\n\n"
            f"Final status: {state.status.value}\n\n"
            f"Tools used: {tools_used}\n\n"
            "Plan steps:\n"
            f"{plan_desc}"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
