from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cli import cmd_codex_run_result_check
from app.codex_quiet_runner import run_codex_quiet_run


class CodexQuietRunnerTimeoutContractTest(unittest.TestCase):
    def test_timeout_writes_valid_json_and_result_check_accepts_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)

            prompt_file = repo / "prompt.md"
            prompt_file.write_text("# prompt de teste\n", encoding="utf-8")

            cwd_dir = repo / "workspace"
            cwd_dir.mkdir(parents=True, exist_ok=True)

            fake_command = [
                sys.executable,
                "-c",
                "import time; time.sleep(2)",
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
                        label="timeout-contract",
                        dry_run=False,
                        execute=True,
                        repo=repo,
                        timeout_seconds=1,
                    )

            self.assertFalse(report["ok"])
            self.assertTrue(report["timeout"])
            self.assertEqual(report["exit_code"], 124)
            self.assertEqual(report["overall_status"], "timeout")
            self.assertEqual(report["error_type"], "timeout")
            self.assertEqual(report["timeout_seconds"], 1)

            report_path = repo / report["report_path"]
            self.assertTrue(report_path.exists())

            with report_path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            self.assertTrue(loaded["timeout"])
            self.assertEqual(loaded["exit_code"], 124)
            self.assertEqual(loaded["overall_status"], "timeout")

            stdout_buffer = io.StringIO()
            with redirect_stdout(stdout_buffer):
                exit_code = cmd_codex_run_result_check(argparse.Namespace(json=str(report_path)))

            self.assertEqual(exit_code, 0)
            summary = json.loads(stdout_buffer.getvalue())
            self.assertTrue(summary["json_ok"])
            self.assertFalse(summary["report_ok"])
            self.assertEqual(summary["overall_status"], "timeout")
            self.assertTrue(summary["timeout"])

            self.assertTrue((repo / report["stdout_log_path"]).exists())
            self.assertTrue((repo / report["stderr_log_path"]).exists())
            self.assertTrue((repo / report["combined_log_path"]).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
