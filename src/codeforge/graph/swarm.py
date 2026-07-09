"""The 6-stage LangGraph swarm with up to 5 healing loops."""
from __future__ import annotations
from langgraph.graph import StateGraph, END
from ..schemas import SwarmState
from ..agents.planner import planner
from ..agents.coder import coder
from ..agents.tester import tester
from ..agents.adversarial_tester import adversarial_tester
from ..agents.fixer import fixer
from ..agents.evaluator import evaluator
from .state import GraphState


async def _planner_node(gs: GraphState) -> GraphState:
    s: SwarmState = gs["state"]
    print(f"[Planner] Decomposing spec...", flush=True)
    delta = await planner(s)
    s = s.model_copy(update=delta)
    return {"state": s}


async def _coder_node(gs: GraphState) -> GraphState:
    s = gs["state"]
    print(f"[Coder] Generating code...", flush=True)
    delta = await coder(s)
    s = s.model_copy(update=delta)
    return {"state": s}


async def _tester_node(gs: GraphState) -> GraphState:
    s = gs["state"]
    print(f"[Tester] Writing & running tests...", flush=True)
    delta = await tester(s)
    s = s.model_copy(update=delta)
    return {"state": s}


async def _adversarial_node(gs: GraphState) -> GraphState:
    s = gs["state"]
    print(f"[Adversarial] Red-team testing...", flush=True)
    delta = await adversarial_tester(s)
    s = s.model_copy(update=delta)
    return {"state": s}


async def _fixer_node(gs: GraphState) -> GraphState:
    s = gs["state"]
    print(f"[Fixer] Healing (loop {s.healing_loop + 1})...", flush=True)
    delta = await fixer(s)
    s = s.model_copy(update=delta)
    return {"state": s}


async def _evaluator_node(gs: GraphState) -> GraphState:
    s = gs["state"]
    verdict = s.verdict
    print(f"[Evaluator] Verdict: {verdict}", flush=True)
    delta = await evaluator(s)
    s = s.model_copy(update=delta)
    return {"state": s}


def _route_after_eval(gs: GraphState) -> str:
    verdict = gs["state"].verdict
    if verdict == "pass":
        return "end"
    if verdict == "escalate":
        return "end"
    return "fixer"   # "fail" → heal


def build_swarm():
    g = StateGraph(GraphState)

    g.add_node("planner", _planner_node)
    g.add_node("coder", _coder_node)
    g.add_node("tester", _tester_node)
    g.add_node("adversarial_tester", _adversarial_node)
    g.add_node("fixer", _fixer_node)
    g.add_node("evaluator", _evaluator_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "coder")
    g.add_edge("coder", "tester")
    g.add_edge("tester", "adversarial_tester")
    g.add_edge("adversarial_tester", "evaluator")
    g.add_conditional_edges(
        "evaluator",
        _route_after_eval,
        {"fixer": "fixer", "end": END},
    )
    g.add_edge("fixer", "tester")  # healing loop

    return g.compile()


# Singleton
_swarm = None


def get_swarm():
    global _swarm
    if _swarm is None:
        _swarm = build_swarm()
    return _swarm