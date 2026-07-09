"""Stage 5 — Fixer: repairs code using RAG-retrieved historical patches."""
from __future__ import annotations
import difflib
from datetime import datetime
import uuid
from langchain_core.prompts import ChatPromptTemplate
from ..llm import make_llm
from ..schemas import SwarmState, PatchRecord, FailureSignature
from ..memory.qdrant_store import BugMemory
from ..config import get_yaml_config, get_settings
from .tester import derive_signatures

FIXER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a senior bug-fixing agent. You receive:\n"
        "- The current source code\n"
        "- Failing test names + error messages\n"
        "- Up to {k} historically successful patches for SIMILAR failures (from memory)\n\n"
        "Apply a MINIMAL, SURGICAL fix. Do not rewrite working code.\n"
        "Do not modify tests. Output ONLY a fenced python code block with the full patched source.\n"
        "Prefer the strategy used in the most similar historical patch when applicable.\n"
    )),
    ("user", (
        "## CURRENT SOURCE\n```python\n{code}\n```\n\n"
        "## FAILURES\n{failures}\n\n"
        "## HISTORICAL PATCHES (RAG)\n{rag}\n"
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

def _format_failures(state: SwarmState) -> str:
    lines = []
    for r in state.test_results + state.adversarial_results:
        if r.passed:
            continue
        lines.append(f"- [{r.name}] {r.error_type}: {(r.error_message or '')[:200]}")
    return "\n".join(lines) or "- (none)"

def _format_rag(records: list[PatchRecord]) -> str:
    if not records:
        return "(no similar historical patches found)"
    out = []
    for i, r in enumerate(records, 1):
        out.append(f"### Patch #{i} (similarity match)\nFailure: {r.signature.error_type}: {r.signature.error_summary}\n```diff\n{r.diff[:1500]}\n```\n")
    return "\n".join(out)

async def fixer(state: SwarmState) -> dict:
    cfg = get_yaml_config()
    memory = BugMemory()
    
    # Extract target failures BEFORE applying the fix
    target_sigs = derive_signatures(state)
    retrieved: list[PatchRecord] = []
    if target_sigs:
        retrieved = memory.retrieve(target_sigs[0], top_k=cfg.memory.top_k)

    llm = make_llm(temperature=cfg.llm.temperature_fixer)
    chain = FIXER_PROMPT | llm
    resp = await chain.ainvoke({
        "code": state.source_code,
        "failures": _format_failures(state),
        "rag": _format_rag(retrieved),
        "k": len(retrieved),
    })
    text = resp.content if hasattr(resp, "content") else str(resp)
    new_code = _extract_code(text)

    diff = "".join(difflib.unified_diff(
        state.source_code.splitlines(keepends=True),
        new_code.splitlines(keepends=True),
        lineterm="",
    ))

    return {
        "source_code": new_code,
        "current_patch": diff,
        "retrieved_contexts": retrieved,
        "healing_loop": state.healing_loop + 1,
        "history": state.history + [{
            "stage": "fixer",
            "loop": state.healing_loop + 1,
            "rag_hits": len(retrieved),
            "source_before": state.source_code,
            "tests_before": state.tests_code,
            "diff_lines": diff.count("\n@@"),
            "target_failures": [s.model_dump() for s in target_sigs]  # FIXED: Save targets for evaluator
        }],
    }

def commit_to_memory(state: SwarmState, signatures: list[FailureSignature], passed: bool) -> None:
    """Called by Evaluator after a successful fix to store the resolution."""
    if not state.current_patch or not state.history or not signatures:
        return
        
    original = state.source_code
    for h in reversed(state.history):
        if h.get("stage") == "fixer" and h.get("source_before"):
            original = h["source_before"]
            break
            
    record = PatchRecord(
        id=str(uuid.uuid4()),
        signature=signatures[0],
        original_code=original,
        patched_code=state.source_code,
        diff=state.current_patch,
        tests_passed_after=passed,
        created_at=datetime.utcnow(),
        tags=[f"loop_{state.healing_loop}"],
    )
    BugMemory().store(signatures[0], record)