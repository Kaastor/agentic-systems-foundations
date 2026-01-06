"""Budgets: first-class limits for spend, time, and calls.

Budgets are intentionally separate from loop bounds (max_steps / max_attempts).

Loop bounds answer: *how many times may the agent try?*
Budgets answer: *how much resource may the agent spend while trying?*
"""

from .manager import BudgetExceeded, BudgetManager
from .types import BudgetCategory, BudgetLimits, BudgetSnapshot

__all__ = [
    "BudgetCategory",
    "BudgetLimits",
    "BudgetSnapshot",
    "BudgetManager",
    "BudgetExceeded",
]
