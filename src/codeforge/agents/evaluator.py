"""Stage 6 — Evaluator: gate-keeps pass / retry / escalate."""
from __future__ import annotations
import json
import urllib.request
from ..schemas import SwarmState, FailureSignature
from ..config import get_settings, get_yaml_config
from .fixer import commit_to_memory

def _all_pass(state: SwarmState) -> bool:
    tests = state.test_results + state.adversarial_results
    if not tests:
        return False
    return all(r.passed for r in tests)

def _metrics_pass(state: SwarmState) -> bool:
    if not state.metric_results:
        return True
    return all(m.passed for m in state.metric_results)

async def evaluator(state: SwarmState) -> dict:
    settings = get_settings()
    cfg = get_yaml_config().swarm
    max_loops = cfg.max_healing_loops

    passed = _all_pass(state) and _metrics_pass(state)

    if passed:
        # FIXED: Extract target failures from history, not from the now-passing state
        target_failures_dicts = []
        for h in reversed(state.history):
            if h.get("stage") == "fixer":
                target_failures_dicts = h.get("target_failures", [])
                break
                
        if target_failures_dicts and state.current_patch:
            sigs = [FailureSignature(**f) for f in target_failures_dicts]
            commit_to_memory(state, sigs, True)
            
        return {"verdict": "pass", "history": state.history + [{"stage": "evaluator", "verdict": "pass"}]}

    if state.healing_loop >= max_loops:
        reason = (
            f"Exceeded {max_loops} healing loops. "
            f"Failures: {sum(1 for r in state.test_results + state.adversarial_results if not r.passed)} "
            f"remaining. Metric flags: {[m.name for m in state.metric_results if not m.passed]}."
        )
        webhook = cfg.escalation.get("webhook", "") or settings.human_escalation_webhook
        if webhook:
            try:
                _notify_human(webhook, state, reason)
            except Exception:
                pass
        return {"verdict": "escalate", "escalate_reason": reason,
                "history": state.history + [{"stage": "evaluator", "verdict": "escalate"}]}

    return {"verdict": "fail",
            "history": state.history + [{"stage": "evaluator", "verdict": "fail", "loop": state.healing_loop}]}

def _notify_human(webhook: str, state: SwarmState, reason: str) -> None:
    payload = json.dumps({
        "text": (
            f"[CodeForge escalation]\n"
            f"Task: `{state.task_id}`\n"
            f"Loops: {state.healing_loop}\n"
            f"Reason: {reason}\n"
            f"Spec preview: {state.spec[:200]}"
        )
    }).encode()
    req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=5)