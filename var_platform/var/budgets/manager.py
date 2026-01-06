from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .types import BudgetCategory, BudgetLimits, BudgetSnapshot


@dataclass(frozen=True)
class BudgetExceeded(RuntimeError):
    category: BudgetCategory
    used: int
    limit: int
    requested: int
    reason: str = "budget_exceeded"


class BudgetManager:
    """Central budget accounting.

    This is intentionally minimal and deterministic:
    - no floating point currency
    - no provider-specific token accounting
    - no "smart" budgeting logic

    Product layers can wrap this with cost models.
    """

    def __init__(self, *, limits: Optional[BudgetLimits] = None):
        self._limits = limits or BudgetLimits()
        self._used: Dict[BudgetCategory, int] = {}

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(limits=dict(self._limits.limits), used=dict(self._used))

    def used(self, category: BudgetCategory) -> int:
        return self._used.get(category, 0)

    def limit(self, category: BudgetCategory) -> Optional[int]:
        return self._limits.limit_for(category)

    def can_spend(self, category: BudgetCategory, amount: int) -> bool:
        if amount <= 0:
            return True
        lim = self.limit(category)
        if lim is None:
            return True
        return (self.used(category) + amount) <= lim

    def spend(self, category: BudgetCategory, amount: int, *, reason: str = "spend", details: Optional[Dict[str, Any]] = None) -> None:
        """Spend budget or raise BudgetExceeded."""
        if amount <= 0:
            return
        lim = self.limit(category)
        cur = self.used(category)
        if lim is not None and (cur + amount) > lim:
            raise BudgetExceeded(category=category, used=cur, limit=lim, requested=amount, reason=reason)
        self._used[category] = cur + amount
