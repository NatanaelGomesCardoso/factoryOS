from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from app.artifact_intake import run_artifact_intake_plan, run_artifact_intake_register
from app.mvp_delivery_package import run_mvp_delivery_package_create
from app.obsidian_sync import run_obsidian_project_sync
from app.project_workspace import run_project_workspace_scaffold
from app.report_retention import run_report_retention_audit, run_report_retention_cleanup_plan
from app.task_runner import TaskRunnerError


class OperationalSprints069to072Test(unittest.TestCase):
    def test_artifact_intake_plan_and_register_accept_safe_sample(self) -> None:
        with tempfile_directory() as repo:
            safe_source = Path("<TMP_DIR>/factoryos-artifact-intake-sample.txt")
            safe_source.write_text("brief prompt for safe intake\n", encoding="utf-8")

            plan = run_artifact_intake_plan(
                project_name="FactoryOS",
                source=safe_source,
                dry_run=True,
                repo=repo,
            )
            register = run_artifact_intake_register(
                project_name="FactoryOS",
                source=safe_source,
                dry_run=True,
                repo=repo,
            )

            self.assertTrue(plan["ok"])
            self.assertEqual(plan["accepted_count"], 1)
            self.assertEqual(plan["accepted_items"][0]["kind"], "document")
            self.assertTrue(register["registration_requested"])
            self.assertTrue((repo / plan["report_path"]).is_file())
            self.assertTrue((repo / register["report_path"]).is_file())

    def test_artifact_intake_blocks_traversal_and_dangerous_extensions(self) -> None:
        with tempfile_directory() as repo:
            dangerous_source = Path("<TMP_DIR>/factoryos-artifact-intake-sample.exe")
            dangerous_source.write_text("binary placeholder\n", encoding="utf-8")

            with self.assertRaises(TaskRunnerError):
                run_artifact_intake_plan(
                    project_name="FactoryOS",
                    source="../traversal.txt",
                    dry_run=True,
                    repo=repo,
                )

            with self.assertRaises(TaskRunnerError):
                run_artifact_intake_register(
                    project_name="FactoryOS",
                    source=dangerous_source,
                    dry_run=True,
                    repo=repo,
                )

    def test_mvp_delivery_package_dry_run_filters_workspace(self) -> None:
        with tempfile_directory() as repo:
            run_project_workspace_scaffold(
                project_name="demo-simple-web-mvp-safe-split",
                kind="web",
                from_template="simple-web-mvp",
                dry_run=False,
                create_workspace=True,
                repo=repo,
            )
            workspace = repo / "workspaces/projects/demo-simple-web-mvp-safe-split"
            (workspace / ".env").write_text("SECRET=1\n", encoding="utf-8")
            (workspace / ".venv/bin").mkdir(parents=True, exist_ok=True)
            (workspace / ".venv/bin/python").write_text("python\n", encoding="utf-8")
            (workspace / "node_modules/pkg").mkdir(parents=True, exist_ok=True)
            (workspace / "node_modules/pkg/index.js").write_text("console.log(1)\n", encoding="utf-8")
            (workspace / "backend/__pycache__").mkdir(parents=True, exist_ok=True)
            (workspace / "backend/__pycache__/x.pyc").write_bytes(b"\x00\x01")

            report = run_mvp_delivery_package_create(
                project_name="demo-simple-web-mvp-safe-split",
                workspace=workspace,
                dry_run=True,
                repo=repo,
            )

            self.assertTrue(report["ok"])
            self.assertTrue(report["dry_run"])
            self.assertFalse(report["package_created"])
            self.assertTrue(report["human_review_required"])
            self.assertIn("README.md", report["included_files"])
            self.assertIn("PROJECT_STATE.md", report["included_files"])
            self.assertTrue(any(item["path"] == ".env" for item in report["excluded_items"]))
            self.assertTrue(any(item["path"].startswith("node_modules/") for item in report["excluded_items"]))
            self.assertTrue(any(item["path"].startswith(".venv/") for item in report["excluded_items"]))
            self.assertTrue((repo / report["report_path"]).is_file())

    def test_obsidian_sync_dry_run_and_write(self) -> None:
        with tempfile_directory() as repo:
            run_project_workspace_scaffold(
                project_name="FactoryOS",
                kind="web",
                from_template="simple-web-mvp",
                dry_run=False,
                create_workspace=True,
                repo=repo,
            )
            vault_root = repo / "vault" / "10-Projetos" / "FactoryOS"
            dry_run_report = run_obsidian_project_sync(
                project_name="FactoryOS",
                dry_run=True,
                write=False,
                repo=repo,
                vault_root=vault_root,
            )
            write_report = run_obsidian_project_sync(
                project_name="FactoryOS",
                dry_run=False,
                write=True,
                repo=repo,
                vault_root=vault_root,
            )

            note_path = vault_root / "FactoryOS - Estado atual.md"
            self.assertTrue(dry_run_report["dry_run"])
            self.assertFalse(dry_run_report["written"])
            self.assertTrue(write_report["written"])
            self.assertTrue(note_path.is_file())
            self.assertNotIn("token", note_path.read_text(encoding="utf-8").lower())
            self.assertTrue((repo / dry_run_report["report_path"]).is_file())
            self.assertTrue((repo / write_report["report_path"]).is_file())

    def test_report_retention_audit_and_cleanup_plan(self) -> None:
        with tempfile_directory() as repo:
            old_large = repo / "reports" / "artifact-intakes" / "20240101-000000-old.json"
            old_large.parent.mkdir(parents=True, exist_ok=True)
            old_large.write_text(json.dumps({"payload": "x" * 70000}), encoding="utf-8")
            old_mtime = 1_700_000_000
            os.utime(old_large, (old_mtime, old_mtime))

            fresh_small = repo / "reports" / "mvp-delivery-packages" / "20260501-000000-fresh.json"
            fresh_small.parent.mkdir(parents=True, exist_ok=True)
            fresh_small.write_text(json.dumps({"ok": True}), encoding="utf-8")

            audit = run_report_retention_audit(repo=repo)
            cleanup = run_report_retention_cleanup_plan(repo=repo)

            self.assertTrue(audit["ok"])
            self.assertFalse(audit["safe_to_apply"])
            self.assertTrue(audit["human_review_required"])
            self.assertTrue(cleanup["ok"])
            self.assertFalse(cleanup["safe_to_apply"])
            self.assertTrue(cleanup["human_review_required"])
            self.assertTrue(
                any(item["action"] == "delete_candidate" for category in cleanup["categories"] for item in category["items"])
            )
            self.assertTrue(old_large.is_file())
            self.assertTrue(fresh_small.is_file())
            self.assertTrue((repo / audit["report_path"]).is_file())
            self.assertTrue((repo / cleanup["report_path"]).is_file())


class tempfile_directory:
    def __enter__(self) -> Path:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.__enter__())
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        self._tmp.__exit__(exc_type, exc, tb)
