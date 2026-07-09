"""Smoke test for the subprocess sandbox."""
from codeforge.sandbox import SubprocessSandbox


def test_sandbox_passes():
    src = "def add(a, b):\n    return a + b\n"
    tests = "from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    results = SubprocessSandbox().run_tests(src, tests)
    assert results and results[0].passed


def test_sandbox_catches_failure():
    src = "def add(a, b):\n    return a - b\n"
    tests = "from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    results = SubprocessSandbox().run_tests(src, tests)
    assert results and not results[0].passed
    assert results[0].error_type == "AssertionError"