"""PatchEfficiency — lines changed per test fixed."""
from __future__ import annotations
import difflib
from deepeval.metrics import BaseMetric


class PatchEfficiencyMetric(BaseMetric):
    def __init__(self, max_lines_per_fix: int = 40, **kwargs):
        super().__init__(**kwargs)
        self.max_lines_per_fix = max_lines_per_fix

    def measure(self, *args, **kwargs) -> tuple[float, str, bool]:
        if len(args) >= 3 and isinstance(args[0], str) and isinstance(args[1], str) and isinstance(args[2], int):
            original, patched, tests_fixed = args[0], args[1], args[2]
        else:
            raise TypeError("PatchEfficiencyMetric.measure() requires (original: str, patched: str, tests_fixed: int)")

        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            n=1,
        ))
        added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
        total = added + removed

        if tests_fixed == 0:
            score, reason, passed = 0.0, f"0 tests fixed; {total} lines churned.", False
        else:
            ratio = total / max(1, tests_fixed)
            if ratio > self.max_lines_per_fix:
                score, reason, passed = 0.3, f"Inefficient: {total} lines for {tests_fixed} fixes (ratio={ratio:.1f}).", False
            elif total == 0:
                score, reason, passed = 0.0, "No changes made.", False
            else:
                score = min(1.0, 1.0 / (1.0 + ratio / 10))
                reason, passed = f"{total} lines for {tests_fixed} fixes (ratio={ratio:.1f}).", True

        self.score = score
        self.success = passed
        self.reason = reason
        return score, reason, passed

    async def a_measure(self, *args, **kwargs) -> float:
        score, _, _ = self.measure(*args, **kwargs)
        return score

    def is_successful(self) -> bool:
        return bool(self.success)

    @property
    def __name__(self):
        return "PatchEfficiencyMetric"