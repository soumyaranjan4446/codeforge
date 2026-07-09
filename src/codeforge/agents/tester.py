"""Stage 3 — Tester: writes & runs initial test suite in sandbox."""
from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from ..llm import make_llm
from ..sandbox import SubprocessSandbox
from ..schemas import SwarmState, FailureSignature
from ..config import get_yaml_config

TESTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a meticulous test engineer. Write pytest tests for the given code.\n"
        "Cover: happy path, boundary values, error handling, and edge cases from the plan.\n"
        "Output a single fenced python code block. Import the module under test by filename "
        "(e.g. `from solution import *`)."
    )),
    ("user", (
        "## PUBLIC INTERFACE\n{iface}\n\n## SOURCE\n```python\n{code}\n```\n"
        "## EDGE CASES TO COVER\n{edge_cases}"
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

async def tester(state: SwarmState) -> dict:
    cfg = get_yaml_config().llm
    llm = make_llm(temperature=cfg.temperature_tester)

    # FIXED: Properly extract edge cases from planner output if present
    edge_cases = "Use your judgment."
    if "## EDGE_CASES" in state.plan:
        edge_cases = state.plan.split("## EDGE_CASES", 1)[1].strip()

    chain = TESTER_PROMPT | llm
    resp = await chain.ainvoke({
        "iface": state.public_interface,
        "code": state.source_code,
        "edge_cases": edge_cases,
    })
    text = resp.content if hasattr(resp, "content") else str(resp)
    tests_code = _extract_code(text)

    sandbox = SubprocessSandbox()
    results = sandbox.run_tests(
        source_code=state.source_code,
        tests_code=tests_code,
        source_path=state.source_path,
        tests_path=state.tests_path,
    )

    return {
        "tests_code": tests_code,
        "test_results": results,
        "history": state.history + [{"stage": "tester", "passed": sum(1 for r in results if r.passed), "total": len(results)}],
    }

def derive_signatures(state: SwarmState) -> list[FailureSignature]:
    sigs: list[FailureSignature] = []
    for r in state.test_results + state.adversarial_results:
        if r.passed:
            continue
        msg = (r.error_message or "")[:200]
        sigs.append(FailureSignature(
            test_name=r.name,
            error_type=r.error_type or "UnknownError",
            error_summary=msg.split("\n")[0][:120],
            code_module=state.source_path,
        ))
    return sigs