from __future__ import annotations

import re
from typing import Optional


def contains_disallowed_solution_like_code(text: str, *, fn_name: Optional[str]) -> bool:
    """Conservative heuristic to catch obvious solution leaks.

    Intentionally imperfect: it teaches that *policy is enforced in code*.
    """

    code_blocks = re.findall(r"```(?:python)?\n([\s\S]*?)```", text)
    for block in code_blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) >= 12:
            return True
        if fn_name and re.search(rf"\bdef\s+{re.escape(fn_name)}\s*\(", block):
            return True

    if fn_name and re.search(rf"\bdef\s+{re.escape(fn_name)}\s*\(", text):
        return True

    return False
