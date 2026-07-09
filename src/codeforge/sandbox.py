"""Subprocess sandbox for safely executing generated code & tests."""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import uuid
from pathlib import Path
from .config import get_settings
from .schemas import TestResult

class SubprocessSandbox:
    def __init__(self, timeout: int | None = None):
        s = get_settings()
        self.timeout = timeout or s.sandbox_timeout

    def run_tests(self, source_code: str, tests_code: str, source_path: str = "solution.py", tests_path: str = "test_solution.py") -> list[TestResult]:
        workdir = Path(tempfile.mkdtemp(prefix=f"cf_{uuid.uuid4().hex[:8]}_"))
        try:
            (workdir / source_path).write_text(source_code)
            (workdir / tests_path).write_text(tests_code)

            pre = self._exec(
                [sys.executable, "-c", f"import ast; ast.parse(open(r'{workdir / source_path}').read())"],
                workdir,
            )
            if pre.returncode != 0:
                return [TestResult(
                    name="syntax_check", passed=False, error_type="SyntaxError",
                    error_message=pre.stderr, stderr=pre.stderr,
                )]

            report_path = workdir / "report.jsonl"
            cmd = [
                sys.executable, "-m", "pytest", str(workdir / tests_path),
                "-q", "--no-header", "--tb=short",
                f"--timeout={self.timeout}",
                f"--json-report", f"--json-report-file={report_path}",
            ]
            res = self._exec(cmd, workdir)
            return self._parse_report(report_path, res)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _exec(self, cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        if os.name == "posix":
            env["NO_PROXY"] = "*"
            env["no_proxy"] = "*"
        try:
            return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=self.timeout + 5)
        except subprocess.TimeoutExpired as e:
            return subprocess.CompletedProcess(cmd, returncode=124, stdout=e.stdout or "", stderr=f"TIMEOUT after {self.timeout}s\n{e.stderr or ''}")

    def _parse_report(self, report_path: Path, res: subprocess.CompletedProcess) -> list[TestResult]:
        import json
        results: list[TestResult] = []
        if not report_path.exists():
            results.append(TestResult(
                name="pytest_invocation", passed=False, error_type="PytestError",
                error_message=res.stderr[:2000], stdout=res.stdout, stderr=res.stderr,
            ))
            return results

        data = json.loads(report_path.read_text())
        for test in data.get("tests", []):
            outcome = test.get("outcome")
            name = test.get("nodeid", "unknown")
            tr = TestResult(name=name, passed=(outcome == "passed"))
            if outcome in ("failed", "error"):
                call = test.get("call", {})
                crash = call.get("crash")
                if crash is None:
                    crash = {}
                tr.error_type = crash.get("type", "UnknownError")
                tr.error_message = (crash.get("message") or "")[:500]

                # FIXED: Handle both string and list longrepr formats
                longrepr = call.get("longrepr", "")
                if isinstance(longrepr, str):
                    tr.traceback = longrepr[:3000]
                    # Fallback: extract error type/message from longrepr when
                    # crash is empty (e.g. plain assertion failures with no crash info)
                    if not tr.error_message and longrepr:
                        parts = longrepr.split(": ")
                        if len(parts) >= 3:
                            candidate_type = parts[-2].strip()
                            candidate_msg = parts[-1].strip()[:500]
                            if tr.error_type == "UnknownError":
                                tr.error_type = candidate_type
                            tr.error_message = candidate_msg
                elif isinstance(longrepr, list):
                    tr.traceback = "\n".join(
                        f.get("repr", "") if isinstance(f, dict) else str(f)
                        for f in longrepr
                    )[:3000]
            results.append(tr)
        return results

    def quick_eval(self, code: str) -> str:
        snippet = textwrap.dedent(code)
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(snippet)
            tmp = Path(f.name)
        try:
            res = self._exec([sys.executable, str(tmp)], tmp.parent)
            return res.stdout + ("\n" + res.stderr if res.returncode else "")
        finally:
            tmp.unlink(missing_ok=True)