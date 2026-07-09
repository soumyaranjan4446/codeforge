"""Stage 4 — Adversarial Tester: writes breaking tests + evaluates with deepeval metrics."""
from __future__ import annotations
import ast
from langchain_core.prompts import ChatPromptTemplate
from ..llm import make_llm
from ..sandbox import SubprocessSandbox
from ..schemas import SwarmState, MetricResult
from ..config import get_yaml_config
from ..metrics import ASTDiffMetric, PatchEfficiencyMetric, SycophancyMetric

ADV_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a red-team QA engineer. Your goal is to BREAK the implementation.\n"
        "Write adversarial pytest tests that probe:\n"
        "- Off-by-one & boundary errors\n"
        "- Type confusion / unexpected inputs (None, NaN, empty, huge)\n"
        "- Concurrency / mutation side effects\n"
        "- Specification ambiguities\n"
        "- Resource leaks\n\n"
        "Be ruthless but fair — only assert on contract violations, not implementation details.\n"
        "Output a single fenced python code block."
    )),
    ("user", (
        "## SPEC\n{spec}\n\n## SOURCE\n```python\n{code}\n```\n"
        "## KNOWN PASSING TESTS\n{tests}"
    )),
])

def _extract_code(text: str) -> str:
    if "```" in text:
        for i, p in enumerate(text.split("```")):
            if i % 2 == 1:
                if p.startswith("python"):
                    p = p[len("python"):]
                return p.strip()
    return text.strip()

async def adversarial_tester(state: SwarmState) -> dict:
    cfg = get_yaml_config()
    llm = make_llm(temperature=cfg.llm.temperature_adversarial)
    
    chain = ADV_PROMPT | llm
    resp = await chain.ainvoke({
        "spec": state.spec,
        "code": state.source_code,
        "tests": state.tests_code[:2000],
    })
    text = resp.content if hasattr(resp, "content") else str(resp)
    adv_tests = _extract_code(text)

    sandbox = SubprocessSandbox()
    adv_results = sandbox.run_tests(
        source_code=state.source_code,
        tests_code=adv_tests,
        source_path=state.source_path,
        tests_path="test_adversarial.py",
    )

    metric_results: list[MetricResult] = []

    # AST-diff sycophancy check on most recent substantive patch (if any)
    if state.history:
        prev_source = None
        prev_tests = None
        for h in reversed(state.history):
            if h.get("stage") == "fixer" and h.get("source_before") and h.get("diff_lines", 0) > 0:
                prev_source = h["source_before"]
                prev_tests = h.get("tests_before")
                break
        if prev_source:
            # FIXED: Properly access typed config objects
            ast_metric = ASTDiffMetric(trivial_threshold=cfg.metrics.ast_diff.trivial_change_threshold)
            score, reason, passed = ast_metric.measure(prev_source, state.source_code)
            metric_results.append(MetricResult(name="ast_diff_sycophancy", score=score, reason=reason, passed=passed))

            pe_metric = PatchEfficiencyMetric(max_lines_per_fix=cfg.metrics.patch_efficiency.max_lines_per_fix)
            # FIXED: Clean calculation of currently passing tests
            fixed = max(1, len([r for r in state.test_results if r.passed]))
            score, reason, passed = pe_metric.measure(prev_source, state.source_code, fixed)
            metric_results.append(MetricResult(name="patch_efficiency", score=score, reason=reason, passed=passed))

            syc_metric = SycophancyMetric(test_only_threshold=cfg.metrics.sycophancy.test_only_change_threshold)
            tests_before = prev_tests or state.tests_code
            # The fixer never touches tests (only outputs source_code), so test code
            # identity is the correct baseline — avoids false flags when the tester
            # regenerates different tests in a later loop.
            score, reason, passed = syc_metric.measure(prev_source, state.source_code, tests_before, tests_before)
            metric_results.append(MetricResult(name="sycophancy", score=score, reason=reason, passed=passed))

    # Static checks on the adversarial tests themselves
    try:
        tree = ast.parse(adv_tests)
        n_asserts = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Assert))
        if n_asserts < 3:
            metric_results.append(MetricResult(name="adversarial_coverage", score=0.3, reason=f"Only {n_asserts} asserts — adversarial suite too weak.", passed=False))
        else:
            metric_results.append(MetricResult(name="adversarial_coverage", score=min(1.0, n_asserts / 8), reason=f"{n_asserts} adversarial asserts.", passed=True))
    except SyntaxError:
        metric_results.append(MetricResult(name="adversarial_coverage", score=0.0, reason="Adversarial tests have syntax errors.", passed=False))

    return {
        "adversarial_tests_code": adv_tests,
        "adversarial_results": adv_results,
        "metric_results": metric_results,
        "history": state.history + [{
            "stage": "adversarial_tester",
            "adv_passed": sum(1 for r in adv_results if r.passed),
            "adv_total": len(adv_results),
            "metrics": [m.name for m in metric_results],
        }],
    }