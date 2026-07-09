<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/LangGraph-✓-purple" alt="LangGraph">
  <img src="https://img.shields.io/badge/Qdrant-✓-blue" alt="Qdrant">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

<h1 align="center">⚒️ CodeForge</h1>

<p align="center">
  <em>An autonomous 6-stage coding swarm powered by LangGraph, Qdrant, LLMs & deepeval-style metrics.</em>
</p>

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Stages](#stages)
- [Memory (Qdrant)](#memory-qdrant)
- [Quick Start](#quick-start)
- [Example](#example)
- [Requirements](#requirements)
- [Project Map](#project-map)

---

## 🏗 Architecture

```
┌──────────┐    ┌────────┐    ┌─────────┐    ┌───────────────────┐
│ Planner  │ →  │ Coder  │ →  │ Tester  │ →  │ Adversarial Tester│
└──────────┘    └────────┘    └─────────┘    └────────┬──────────┘
                                                       │
                                                       ↓
                                              ┌───────────┐
                                          ←── │ Evaluator  │ → END (pass / escalate)
                                         /    └───────────┘
                              ┌────────┐
                              │ Fixer  │
                              └────────┘
```

**Healing loop:** `Tester → Adversarial → Evaluator → Fixer → Tester`  
_Up to 5 iterations, then human escalation._

---

## 🧠 How It Works

CodeForge is an autonomous agent swarm that:

1. **Plans** — decomposes a natural-language spec into a structured plan
2. **Codes** — implements the solution against the defined interface
3. **Tests** — writes & runs `pytest` tests in an isolated sandbox
4. **Attacks** — red-team QA writes adversarial tests to break the solution
5. **Fixes** — surgically repairs using RAG-retrieved historical patches from Qdrant
6. **Evaluates** — decides pass / fail / escalate, stores successful fixes back to memory

---

## 🔬 Stages

| Stage | Agent | Responsibility |
|-------|-------|---------------|
| **1** | **Planner** | Decomposes spec → plan + public interface + edge cases |
| **2** | **Coder** | Implements solution against the planned interface |
| **3** | **Tester** | Writes & runs pytest in an isolated subprocess sandbox |
| **4** | **Adversarial Tester** | Red-team QA writes breaking tests + runs custom metrics |
| **5** | **Fixer** | Surgical repair using RAG-retrieved historical patches |
| **6** | **Evaluator** | Pass / fail / escalate verdict + stores to Qdrant |

### 📊 Custom Metrics

| Metric | Description |
|--------|-------------|
| **ASTDiffMetric** | Detects cosmetic/sycophantic patches via AST structural diffing |
| **PatchEfficiencyMetric** | Lines-changed per test-fixed ratio |
| **SycophancyMetric** | Flags test-only edits that appease tests without fixing source |

---

## 💾 Memory (Qdrant)

Every failed test produces a **FailureSignature**:

```
Module: solution.py
Test:   test_add.py::test_add
Error:  AssertionError: assert 4 == 5
```

This signature is embedded (`BAAI/bge-small-en`) and used to retrieve **top-k similar historical patches**. On a successful fix, the `(signature, original, patched, diff)` tuple is stored for future RAG.

---

## ⚡ Quick Start

```bash
# 1. Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# 2. Install
pip install -e .

# 3. Configure
cp .env.example .env   # fill in DEEPSEEK_API_KEY

# 4. Run
codeforge run --spec "Implement a thread-safe LRU cache with TTL support" --save out.json

# 5. Inspect memory
codeforge memory-stats
```

---

## 🎯 Example

```
codeforge run --spec-file specs/lru_cache.md
```

```
🚀 Launching
┌────────────────────────────────────┐
│ CodeForge Swarm                    │
│ Task: a3f9c2b1   Lang: python      │
└────────────────────────────────────┘

Test Results
├─ test_basic                PASS
├─ test_ttl_expiry           PASS
├─ test_concurrent_eviction  PASS
├─ test_zero_ttl             PASS

DeepEval Metrics
├─ ast_diff_sycophancy      0.85  ✓
├─ patch_efficiency         0.92  ✓
├─ sycophancy               1.00  ✓
├─ adversarial_coverage     1.00  ✓

Result: PASS ✅  (2 healing loops)
```

---

## 📦 Requirements

- **Python** ≥ 3.11
- **Qdrant** (local or cloud)
- **DeepSeek** or **Qwen** API key
- **pytest**, **pytest-timeout**, **pytest-json-report** (auto-installed into sandbox venv)

---

## 🗺 Project Map

```
codeforge/
├── src/codeforge/
│   ├── agents/
│   │   ├── adversarial_tester.py   # Red-team QA
│   │   ├── coder.py                # Code implementation
│   │   ├── evaluator.py            # Pass/fail/escalate
│   │   ├── fixer.py                # Surgical repair + RAG
│   │   ├── planner.py              # Spec decomposition
│   │   └── tester.py               # pytest runner
│   ├── graph/
│   │   ├── state.py                # Swarm state
│   │   └── swarm.py                # LangGraph orchestration
│   ├── memory/
│   │   ├── embedder.py             # BGE embeddings
│   │   └── qdrant_store.py         # Vector store
│   ├── metrics/
│   │   ├── ast_diff.py             # AST structural diffing
│   │   ├── patch_efficiency.py     # Lines-changed ratio
│   │   └── sycophancy.py           # Test-only edit detection
│   ├── cli.py                      # CLI entrypoint
│   ├── config.py                   # Configuration
│   ├── llm.py                      # LLM client
│   ├── sandbox.py                  # Subprocess isolation
│   └── schemas.py                  # Data models
├── tests/
└── config/
```

---

<p align="center">
  <sub>Built with ❤️ using LangGraph, Qdrant & open-source LLMs</sub>
</p>
