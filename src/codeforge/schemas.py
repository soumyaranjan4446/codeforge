"""Pydantic models shared across the swarm."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


class TestResult(BaseModel):
    name: str
    passed: bool
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0


class FailureSignature(BaseModel):
    """Embedding key derived from a failing test."""
    test_name: str
    error_type: str
    error_summary: str
    code_module: str

    def to_text(self) -> str:
        return (
            f"Module: {self.code_module}\n"
            f"Test: {self.test_name}\n"
            f"Error: {self.error_type}: {self.error_summary}"
        )


class PatchRecord(BaseModel):
    """A historical bug-resolution stored in Qdrant."""
    id: str
    signature: FailureSignature
    original_code: str
    patched_code: str
    diff: str
    tests_passed_after: bool
    created_at: datetime
    tags: list[str] = Field(default_factory=list)


class MetricResult(BaseModel):
    name: str
    score: float
    reason: str
    passed: bool


class SwarmState(BaseModel):
    """LangGraph state — flows through all 6 stages."""
    # Inputs
    task_id: str
    spec: str
    language: str = "python"

    # Planner outputs
    plan: str = ""
    public_interface: str = ""        # function/class signatures expected

    # Coder outputs
    source_code: str = ""
    source_path: str = "solution.py"

    # Tester outputs
    tests_code: str = ""
    tests_path: str = "test_solution.py"
    test_results: list[TestResult] = Field(default_factory=list)

    # Adversarial outputs
    adversarial_tests_code: str = ""
    adversarial_results: list[TestResult] = Field(default_factory=list)
    metric_results: list[MetricResult] = Field(default_factory=list)

    # Fixer
    current_patch: str | None = None
    retrieved_contexts: list[PatchRecord] = Field(default_factory=list)
    healing_loop: int = 0
    history: list[dict] = Field(default_factory=list)

    # Evaluator
    verdict: Literal["pass", "fail", "escalate"] = "fail"
    escalate_reason: str = ""

    # Bookkeeping
    started_at: datetime = Field(default_factory=datetime.utcnow)