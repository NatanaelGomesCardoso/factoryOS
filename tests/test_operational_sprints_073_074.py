from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.project_pilot_runbook import run_project_pilot_runbook_create
from app.project_workspace import run_project_workspace_scaffold
from app.v1_readiness_gate import run_factoryos_v1_readiness_gate


def _seed_report(repo: Path, kind: str, project_name: str, *, timestamp: str = "20260502-010101") -> Path:
    path = repo / "reports" / kind / f"{timestamp}-{kind}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "project_name": project_name,
        "created_at": "2026-05-02T01:01:01+00:00",
        "finished_at": "2026-05-02T01:01:01+00:00",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


class OperationalSprints073074Test(unittest.TestCase):
    def test_project_pilot_runbook_create_emits_safe_dry_run_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)

            report = run_project_pilot_runbook_create(
                project_name="demo-simple-web-mvp-safe-split",
                dry_run=True,
                repo=repo,
            )

            self.assertTrue(report["ok"])
            self.assertTrue(report["dry_run"])
            self.assertTrue(report["human_review_required"])
            self.assertTrue(report["no_push"])
            self.assertTrue(report["no_deploy"])
            self.assertTrue(report["no_paid_api"])
            self.assertTrue(report["no_secrets"])
            self.assertGreaterEqual(len(report["steps"]), 10)
            self.assertTrue((repo / report["report_path"]).is_file())
            self.assertIn("project intake", report["runbook"]["approval_points"])

    def test_factoryos_v1_readiness_gate_accepts_seeded_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)

            run_project_workspace_scaffold(
                project_name="demo-simple-web-mvp-safe-split",
                kind="web",
                from_template="simple-web-mvp",
                dry_run=False,
                create_workspace=True,
                repo=repo,
            )
            run_project_pilot_runbook_create(
                project_name="FactoryOS",
                dry_run=True,
                repo=repo,
            )

            _seed_report(repo, "project-intakes", "demo-simple-web-mvp-safe-split")
            _seed_report(repo, "mvp-build-plans", "demo-simple-web-mvp-safe-split")
            _seed_report(repo, "mvp-capsule-build-canaries", "demo-simple-web-mvp-safe-split")
            _seed_report(repo, "mvp-apply-plans", "demo-simple-web-mvp-safe-split")

            report = run_factoryos_v1_readiness_gate(dry_run=True, repo=repo)

            self.assertTrue(report["ok"])
            self.assertTrue(report["dry_run"])
            self.assertIn(report["readiness_decision"], {"ready_for_audit", "needs_review"})
            self.assertTrue(report["no_push"])
            self.assertTrue(report["no_deploy"])
            self.assertTrue(report["no_paid_api"])
            self.assertTrue(report["no_secrets"])
            self.assertTrue(report["command_checks"]["ok"])
            self.assertTrue(report["report_checks"]["ok"])
            self.assertTrue(report["workspace_checks"]["workspace_exists"])
            self.assertTrue(report["support_checks"]["delivery_package"]["ok"])
            self.assertTrue(report["support_checks"]["obsidian"]["ok"])
            self.assertTrue(report["support_checks"]["quiet_runner"]["ok"])
            self.assertTrue(report["panel_check"]["ok"])
            self.assertTrue(report["git_diff_check"]["ok"])
            self.assertTrue((repo / report["report_path"]).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
