"""Stage 2 — Coder: implements the solution per plan & interface."""
from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from ..llm import make_llm
from ..schemas import SwarmState
from ..config import get_yaml_config

CODER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an expert {language} engineer. Implement ONLY the code that satisfies "
        "the plan and the public interface. Output a single fenced code block.\n"
        "Rules:\n"
        "- No explanations outside the code block.\n"
        "- Include the public interface exactly as specified.\n"
        "- Add inline comments for non-obvious logic only.\n"
        "- Prefer stdlib; do not invent third-party imports unless asked.\n"
    )),
    ("user", (
        "## PLAN\n{plan}\n\n## INTERFACE\n{iface}\n\n## SPEC\n{spec}\n"
    )),
])


def _extract_code(text: str) -> str:
    if "```" in text:
        parts = text.split("```")
        for i, p in enumerate(parts):
            if i % 2 == 1:  # inside fence
                if p.startswith("python"):
                    p = p[len("python"):]
                return p.strip()
    return text.strip()


async def coder(state: SwarmState) -> dict:
    cfg = get_yaml_config().llm
    llm = make_llm(temperature=cfg.temperature_coder)
    chain = CODER_PROMPT | llm
    resp = await chain.ainvoke({
        "plan": state.plan, "iface": state.public_interface,
        "spec": state.spec, "language": state.language,
    })
    text = resp.content if hasattr(resp, "content") else str(resp)
    code = _extract_code(text)
    return {
        "source_code": code,
        "history": state.history + [{"stage": "coder", "len": len(code)}],
    }