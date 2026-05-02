from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cli import cmd_codex_run_result_check
from app.codex_quiet_runner import run_codex_quiet_run


NO_DIFF_CONTRACT_PROMPT = """# sprint de teste

no-diff-prompt-contract
Nao imprimir diff, patch ou conteudo de arquivo no terminal.
Registrar detalhes apenas em reports/proofs.
"""


class QuietRunnerStatusContractTest(unittest.TestCase):
    def _repo_with_prompt(self, tmp: str) -> tuple[Path, Path, Path]:
        repo = Path(tmp)
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
        prompt_file = repo / "prompt.md"
        prompt_file.write_text(NO_DIFF_CONTRACT_PROMPT, encoding="utf-8")
        cwd_dir = repo / "workspace"
        cwd_dir.mkdir(parents=True, exist_ok=True)
        return repo, prompt_file, cwd_dir

    def test_exit_code_zero_with_blocked_captured_log_is_budget_warning_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, prompt_file, cwd_dir = self._repo_with_prompt(tmp)
            fake_command = [
                sys.executable,
                "-c",
                "for i in range(501): print('log line %03d' % i)",
            ]

            with patch.dict(os.environ, {"FACTORYOS_ENABLE_QUIET_CODEX": "1"}, clear=False):
                with patch("app.codex_quiet_runner.build_quiet_codex_command", return_value=fake_command):
                    report = run_codex_quiet_run(
                        prompt_file=prompt_file,
                        cwd=cwd_dir,
                        model="fake-model",
                        reasoning="low",
                        sandbox="read-only",
                        approval="never",
                        label="budget-blocked-success",
                        dry_run=False,
                        execute=True,
                        repo=repo,
                        timeout_seconds=10,
                    )

            self.assertTrue(report["ok"])
            self.assertEqual(report["execution_status"], "succeeded")
            self.assertEqual(report["captured_log_status"], "blocked")
            self.assertEqual(report["budget_status"], "blocked")
            self.assertFalse(report["budget_ok"])
            self.assertEqual(report["overall_status"], "succeeded_with_budget_warnings")
            self.assertFalse(report["timeout"])
            self.assertEqual(report["exit_code"], 0)

            stdout_buffer = io.StringIO()
            with redirect_stdout(stdout_buffer):
                exit_code = cmd_codex_run_result_check(argparse.Namespace(json=str(repo / report["report_path"])))

            self.assertEqual(exit_code, 0)
            summary = json.loads(stdout_buffer.getvalue())
            self.assertTrue(summary["json_ok"])
            self.assertEqual(summary["execution_status"], "succeeded")
            self.assertEqual(summary["budget_status"], "blocked")
            self.assertEqual(summary["overall_status"], "succeeded_with_budget_warnings")
            self.assertFalse(summary["budget_ok"])

    def test_result_check_succeeded_with_budget_warning_returns_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "warning.json"
            path.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "execution_status": "succeeded_with_budget_warnings",
                        "budget_status": "blocked",
                        "overall_status": "succeeded_with_budget_warnings",
                        "timeout": False,
                        "exit_code": 0,
                    }
                ),
                encoding="utf-8",
            )

            stdout_buffer = io.StringIO()
            with redirect_stdout(stdout_buffer):
                exit_code = cmd_codex_run_result_check(argparse.Namespace(json=str(path)))

            self.assertEqual(exit_code, 0)
            summary = json.loads(stdout_buffer.getvalue())
            self.assertTrue(summary["json_ok"])
            self.assertEqual(summary["execution_status"], "succeeded_with_budget_warnings")

    def test_result_check_timeout_returns_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "timeout.json"
            path.write_text(
                json.dumps(
                    {
                        "ok": False,
                        "execution_status": "timeout",
                        "budget_status": "ok",
                        "overall_status": "timeout",
                        "timeout": True,
                        "exit_code": 124,
                    }
                ),
                encoding="utf-8",
            )

            stdout_buffer = io.StringIO()
            with redirect_stdout(stdout_buffer):
                exit_code = cmd_codex_run_result_check(argparse.Namespace(json=str(path)))

            self.assertEqual(exit_code, 1)
            summary = json.loads(stdout_buffer.getvalue())
            self.assertTrue(summary["json_ok"])
            self.assertEqual(summary["execution_status"], "timeout")

    def test_result_check_invalid_json_returns_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text("{invalid", encoding="utf-8")

            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = cmd_codex_run_result_check(argparse.Namespace(json=str(path)))

            self.assertEqual(exit_code, 2)
            self.assertEqual(stdout_buffer.getvalue(), "")
            self.assertIn("JSON inválido", stderr_buffer.getvalue())


    def test_result_check_succeeded_warn_budget_returns_warning_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "warn-budget-success.json"
            report_path.write_text(
                json.dumps(
                    {
                        "ok": False,
                        "execution_status": "succeeded",
                        "budget_status": "warn",
                        "budget_ok": False,
                        "overall_status": "failed",
                        "timeout": False,
                        "exit_code": 0,
                        "warnings": ["budget status warn"],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_codex_run_result_check(argparse.Namespace(json=str(report_path)))

            self.assertEqual(code, 0)
            summary = json.loads(stdout.getvalue())
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["budget_status"], "warn")
            self.assertEqual(summary["overall_status"], "succeeded_with_budget_warnings")

    def test_result_check_succeeded_blocked_budget_returns_warning_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "blocked-budget-success.json"
            report_path.write_text(
                json.dumps(
                    {
                        "ok": False,
                        "execution_status": "succeeded",
                        "budget_status": "blocked",
                        "budget_ok": False,
                        "overall_status": "failed",
                        "timeout": False,
                        "exit_code": 0,
                        "warnings": ["budget status blocked"],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_codex_run_result_check(argparse.Namespace(json=str(report_path)))

            self.assertEqual(code, 0)
            summary = json.loads(stdout.getvalue())
            self.assertTrue(summary["ok"])
            self.assertFalse(summary["budget_ok"])
            self.assertEqual(summary["budget_status"], "blocked")
            self.assertEqual(summary["overall_status"], "succeeded_with_budget_warnings")

if __name__ == "__main__":
    unittest.main(verbosity=2)
