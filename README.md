CodeForge
A 6-stage autonomous coding swarm built with LangGraph, Qdrant, DeepSeek/Qwen, and deepeval-style metrics.

Architecture
        ┌─────────┐    ┌───────┐    ┌────────┐    ┌──────────────┐START → │ Planner │ →  │ Coder │ →  │ Tester │ →  │ Adversarial  │        └─────────┘    └───────┘    └────────┘    │   Tester     │                                     ↑            └──────┬───────┘                                     │                   ↓                                  ┌──────┐  ←──── ┌───────────┐                                  │Fixer │        │ Evaluator │ → END (pass / escalate)                                  └──────┘        └───────────┘
Healing loop: Tester → Adversarial → Evaluator → Fixer → Tester (up to 5 iterations, then human escalation).

Stages
Planner — Decomposes spec into plan + public interface + edge cases.
Coder — Implements the solution against the interface.
Tester — Writes & runs pytest in an isolated subprocess sandbox.
Adversarial Tester — Red-team QA writes breaking tests; runs custom deepeval metrics:
ASTDiffMetric — detects cosmetic/sycophantic patches via AST structural diffing.
PatchEfficiencyMetric — lines-changed per test-fixed ratio.
SycophancyMetric — flags test-only edits that appease tests without fixing source.
Fixer — Surgical repair using RAG-retrieved historical patches from Qdrant.
Evaluator — Decides pass / fail / escalate; stores successful resolutions back to Qdrant.
Memory (Qdrant)
Every failed test produces a FailureSignature:

Module: solution.pyTest: test_add.py::test_addError: AssertionError: assert 4 == 5
This signature is embedded (BAAI/bge-small-en) and used to retrieve top-k similar historical patches. On a successful fix, the (signature, original, patched, diff) tuple is stored for future RAG.

Quick Start
# 1. Start Qdrantdocker run -p 6333:6333 qdrant/qdrant# 2. Installpip install -e .# 3. Configurecp .env.example .env  # fill in DEEPSEEK_API_KEY# 4. Runcodeforge run --spec "Implement a thread-safe LRU cache with TTL support" --save out.json# 5. Inspect memorycodeforge memory-stats
Example
codeforge run --spec-file specs/lru_cache.md
Output:

🚀 Launching┌─────────────────────────────────────┐│ CodeForge Swarm                     ││ Task: a3f9c2b1  Lang: python        │└─────────────────────────────────────┘Test Results├─ test_solution.py::test_basic       PASS├─ test_solution.py::test_ttl_expiry  PASS├─ test_adversarial.py::test_concurrent_eviction  PASS├─ test_adversarial.py::test_zero_ttl  PASSDeepEval Metrics├─ ast_diff_sycophancy     0.85  ok├─ patch_efficiency        0.92  ok├─ sycophancy              1.00  ok├─ adversarial_coverage    1.00  okResult: PASS (2 healing loops)
Requirements
Python ≥ 3.11
Qdrant (local or cloud)
DeepSeek or Qwen API key
pytest, pytest-timeout, pytest-json-report (auto-installed into sandbox venv)
How it all fits together
Resume claim
Implementation
6-stage LangGraph swarm	graph/swarm.py — planner → coder → tester → adversarial_tester → evaluator, with conditional edge evaluator → fixer → tester for healing
Subprocess sandbox	sandbox.py — tempdir isolation, timeout, pytest --json-report parsing, no-network env
Up to 5 healing loops	evaluator.py checks state.healing_loop >= max_healing_loops → verdict="escalate"
Human escalation	_notify_human() posts to Slack/Discord webhook with failure summary
Semantic bug-resolution memory (Qdrant)	memory/qdrant_store.py — stores (FailureSignature embedding, original, patched, diff)
RAG injection into Fixer	agents/fixer.py — embeds current failure, retrieves top-k, formats as ## HISTORICAL PATCHES in prompt
Adversarial Tester	agents/adversarial_tester.py — red-team prompt + breaking tests
AST-diffing for sycophancy	metrics/ast_diff.py — compares AST node sequences, flags trivial-only changes
PatchEfficiency	metrics/patch_efficiency.py — lines-changed / tests-fixed ratio
DeepSeek/Qwen	llm.py — ChatOpenAI against either OpenAI-compatible endpoint

To run
docker run -d -p 6333:6333 qdrant/qdrant
pip install -e .
pip install pytest pytest-timeout pytest-json-report
cp .env.example .env  # add DEEPSEEK_API_KEY
codeforge run --spec "Implement a thread-safe LRU cache with TTL support and max_size parameter"