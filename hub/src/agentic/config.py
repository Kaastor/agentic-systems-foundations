from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Simple configuration object.

    The goal here is *not* to be fancy, but to show that even tiny agents
    benefit from a central place for paths and knobs. Specializations can
    extend this model.
    """

    # For this teaching repo we assume you run from the project root,
    # so the data lives under src/agentic/steel_thread/data.
    project_root: Path = Field(default_factory=lambda: Path.cwd())
    data_dir: Path = Field(
        default_factory=lambda: Path.cwd() / "src" / "agentic" / "steel_thread" / "data"
    )
    runs_dir: Path = Field(default_factory=lambda: Path.cwd() / "runs")

    # Bound on how many state-machine steps a single run may take. Exposed as
    # an env var so we can talk about "depth limits" (Module 9).
    max_steps: int = Field(
        default_factory=lambda: int(os.getenv("AGENTIC_MAX_STEPS", "20"))
    )

    # Coarse mode selector: "fast" vs "smart". In a real system this might
    # pick different models or decoding configs.
    mode: str = Field(default_factory=lambda: os.getenv("AGENTIC_MODE", "fast"))

    # Which LLM backend to use: "stub" for fully local, "groq" for live calls.
    llm_backend: str = Field(
        default_factory=lambda: os.getenv("AGENTIC_LLM_BACKEND", "stub")
    )

    # Groq configuration (only used when llm_backend == "groq").
    groq_api_key: str | None = Field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    groq_model: str = Field(
        default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    )
    groq_base_url: str = Field(
        default_factory=lambda: os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    )

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
