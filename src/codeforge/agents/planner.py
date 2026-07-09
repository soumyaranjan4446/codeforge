"""Stage 1 — Planner: decomposes spec into plan + public interface."""
from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from ..llm import make_llm
from ..schemas import SwarmState
from ..config import get_yaml_config

PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a senior software architect. Given a coding spec, produce:\n"
        "1. A concise step-by-step plan.\n"
        "2. The exact public interface (function/class signatures with types & docstrings) "
        "that the solution MUST export.\n"
        "3. A list of edge cases the tests should cover.\n\n"
        "Respond in this exact format:\n"
        "## PLAN\n<plan>\n## INTERFACE\n<python signatures>\n## EDGE_CASES\n- ...\n"
    )),
    ("user", "SPEC:\n{spec}\n\nLanguage: {language}"),
])


async def planner(state: SwarmState) -> dict:
    cfg = get_yaml_config().llm
    llm = make_llm(temperature=cfg.temperature_coder)
    chain = PLANNER_PROMPT | llm
    resp = await chain.ainvoke({"spec": state.spec, "language": state.language})
    text = resp.content if hasattr(resp, "content") else str(resp)

    plan = ""
    iface = ""
    if "## PLAN" in text:
        plan = text.split("## PLAN", 1)[1].split("##", 1)[0].strip()
    if "## INTERFACE" in text:
        iface = text.split("## INTERFACE", 1)[1].split("##", 1)[0].strip()

    return {
        "plan": plan,
        "public_interface": iface,
        "history": state.history + [{"stage": "planner", "ok": bool(plan)}],
    }