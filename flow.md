codeforge/
├── pyproject.toml
├── .env.example
├── README.md
├── config/
│   └── settings.yaml
├── src/codeforge/
│   ├── __init__.py
│   ├── config.py
│   ├── schemas.py
│   ├── llm.py
│   ├── sandbox.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── qdrant_store.py
│   │   └── embedder.py
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── ast_diff.py
│   │   ├── patch_efficiency.py
│   │   └── sycophancy.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── planner.py
│   │   ├── coder.py
│   │   ├── tester.py
│   │   ├── adversarial_tester.py
│   │   ├── fixer.py
│   │   └── evaluator.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   └── swarm.py
│   └── cli.py
└── tests/
    └── test_sandbox.py