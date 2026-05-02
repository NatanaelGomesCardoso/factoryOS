from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import web
from app.mvp_evaluator import run_mvp_evaluate
from app.mvp_templates import list_templates, validate_template
from app.project_workspace import discover_project_workspaces, run_project_workspace_scaffold


def test_template_registry_has_three_templates() -> None:
    template_ids = [template.template_id for template in list_templates()]
    assert template_ids == ["dashboard-saas-mvp", "landing-page-mvp", "simple-web-mvp"]


def test_template_validation_passes_for_v0_registry() -> None:
    for template_id in ("simple-web-mvp", "landing-page-mvp", "dashboard-saas-mvp"):
        result = validate_template(template_id)
        assert result["ok"] is True
        assert result["final_decision"] == "passed"
        assert result["template"]["template_id"] == template_id


def test_workspace_scaffold_creates_split_structure(tmp_path: Path) -> None:
    report = run_project_workspace_scaffold(
        project_name="demo-simple-web-mvp-safe-split",
        kind="web",
        from_template="simple-web-mvp",
        dry_run=False,
        create_workspace=True,
        repo=tmp_path,
    )

    workspace = tmp_path / report["workspace_relative_path"]
    assert workspace.is_dir()
    assert (workspace / "backend").is_dir()
    assert (workspace / "frontend").is_dir()
    assert (workspace / "docs").is_dir()
    assert (workspace / "reports").is_dir()
    assert (workspace / "README.md").is_file()
    assert (workspace / "PROJECT_STATE.md").is_file()
    assert (workspace / "backend" / "README.md").is_file()
    assert (workspace / "frontend" / "README.md").is_file()
    assert report["no_push"] is True
    assert report["no_deploy"] is True
    assert report["no_paid_api"] is True
    assert report["no_secrets"] is True


def test_evaluator_passes_on_scaffold_workspace(tmp_path: Path) -> None:
    run_project_workspace_scaffold(
        project_name="demo-simple-web-mvp-safe-split",
        kind="web",
        from_template="simple-web-mvp",
        dry_run=False,
        create_workspace=True,
        repo=tmp_path,
    )

    report = run_mvp_evaluate(
        project_name="demo-simple-web-mvp-safe-split",
        workspace=tmp_path / "workspaces/projects/demo-simple-web-mvp-safe-split",
        dry_run=True,
        repo=tmp_path,
    )

    assert report["final_decision"] == "passed"
    assert report["failed_checks"] == []
    assert (tmp_path / report["report_path"]).is_file()


def test_panel_lists_projects_and_viewer_blocks_traversal(tmp_path: Path, monkeypatch) -> None:
    run_project_workspace_scaffold(
        project_name="demo-simple-web-mvp-safe-split",
        kind="web",
        from_template="simple-web-mvp",
        dry_run=False,
        create_workspace=True,
        repo=tmp_path,
    )
    monkeypatch.setattr(web, "repo_root", lambda: tmp_path)

    client = TestClient(web.create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "Projetos detectados" in response.text
    assert "demo-simple-web-mvp-safe-split" in response.text

    blocked = client.get("/view/docs/..%2FREADME.md")
    assert blocked.status_code in {400, 404}


def test_discover_project_workspaces_returns_metadata(tmp_path: Path) -> None:
    run_project_workspace_scaffold(
        project_name="demo-simple-web-mvp-safe-split",
        kind="web",
        from_template="simple-web-mvp",
        dry_run=False,
        create_workspace=True,
        repo=tmp_path,
    )

    projects = discover_project_workspaces(tmp_path)
    assert len(projects) == 1
    assert projects[0]["project_name"] == "demo-simple-web-mvp-safe-split"
    assert projects[0]["latest_reports"]["intake"] is None
