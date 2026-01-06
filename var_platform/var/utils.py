from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from .types import SignatureSpec


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 30] + "\n...<truncated>...\n" + text[-20:]


def scan_forbidden_imports(code: str, forbidden_imports: Sequence[str]) -> List[str]:
    """Return a sorted list of forbidden imports used in the provided source code.

    This is a *static* AST scan. It does not attempt to resolve dynamic imports.
    """
    forbidden = {m.strip() for m in forbidden_imports if m.strip()}
    if not forbidden:
        return []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Syntax errors will be handled elsewhere. Here, treat as no imports found.
        return []

    found = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in forbidden:
                    found.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in forbidden:
                    found.add(top)

    return sorted(found)


@dataclass(frozen=True)
class FunctionSignature:
    name: str
    arg_names: Tuple[str, ...]
    has_varargs: bool
    has_varkw: bool


def extract_function_signature(code: str, function_name: str) -> Optional[FunctionSignature]:
    """Extract the first top-level function signature for `function_name`, if present."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            args = node.args
            arg_names = [a.arg for a in args.posonlyargs + args.args]
            if args.vararg:
                arg_names.append(args.vararg.arg)
            if args.kwarg:
                arg_names.append(args.kwarg.arg)
            return FunctionSignature(
                name=node.name,
                arg_names=tuple(arg_names),
                has_varargs=args.vararg is not None,
                has_varkw=args.kwarg is not None,
            )
    return None


def signature_matches(spec: SignatureSpec, sig: FunctionSignature) -> bool:
    """Check whether a parsed function signature matches the spec.

    This is intentionally strict for pedagogy:
    - positional arg count and names must match exactly
    - varargs/varkw are not allowed unless included explicitly (not supported in v0.1)
    """
    expected = [a.name for a in spec.args]
    return (
        sig.name == spec.name
        and list(sig.arg_names)[: len(expected)] == expected
        and not sig.has_varargs
        and not sig.has_varkw
        and len(sig.arg_names) == len(expected)
    )


def render_signature_stub(spec: SignatureSpec) -> str:
    args = ", ".join([a.name for a in spec.args])
    return f"def {spec.name}({args}):"



def safe_format(template: str, variables: dict) -> str:
    """Deterministic prompt formatting.

    Uses Python's str.format_map; raises KeyError if a variable is missing.
    """
    class _Missing(dict):
        def __missing__(self, key):
            raise KeyError(key)
    return template.format_map(_Missing(**variables))
