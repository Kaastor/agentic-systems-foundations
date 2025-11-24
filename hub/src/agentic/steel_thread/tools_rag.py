from __future__ import annotations

import math
from pathlib import Path
from typing import List

from pydantic import BaseModel

from agentic.core.tools import Tool, ToolMetadata
from .models import DocumentHit


class SearchDocsInput(BaseModel):
    query: str
    k: int = 3


class SearchDocsOutput(BaseModel):
    hits: List[DocumentHit]


def _tokenise(text: str) -> set[str]:
    return {
        tok.strip(".,:;!?()[]{}\"'").lower()
        for tok in text.split()
        if tok.strip()
    }


def _score(query_tokens: set[str], doc_text: str) -> float:
    tokens = _tokenise(doc_text)
    overlap = len(query_tokens & tokens)
    if not overlap:
        return 0.0
    return overlap / math.sqrt(len(tokens) + 1)


def build_rag_tool(docs_dir: Path) -> Tool:
    """Build a tiny keyword-based RAG search tool over ``docs_dir``."""

    docs: List[tuple[str, str, str]] = []
    for path in docs_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        title = path.stem.replace("_", " ").title()
        docs.append((path.name, title, text))

    def search_func(inp: SearchDocsInput) -> SearchDocsOutput:
        query_tokens = _tokenise(inp.query)
        scored: List[tuple[float, DocumentHit]] = []
        for filename, title, text in docs:
            score = _score(query_tokens, text)
            if score <= 0:
                continue
            snippet = text[:200].strip().replace("\n", " ")
            hit = DocumentHit(
                id=filename,
                title=title,
                snippet=snippet,
                score=score,
                path=str((docs_dir / filename).resolve()),
            )
            scored.append((score, hit))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        hits = [h for _, h in scored[: inp.k]]
        return SearchDocsOutput(hits=hits)

    rag_tool = Tool[SearchDocsInput, SearchDocsOutput](
        metadata=ToolMetadata(
            name="search_docs",
            description=(
                "Search local policy / context documents using a simple keyword-based RAG. "
                "Returns scored snippets from markdown files."
            ),
            is_write=False,
            dangerous=False,
            latency_class="medium",
            permissions=["docs:read"],
        ),
        input_model=SearchDocsInput,
        output_model=SearchDocsOutput,
        func=search_func,
    )
    return rag_tool
