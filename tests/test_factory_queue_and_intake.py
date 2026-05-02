from __future__ import annotations

from pathlib import Path

from app.factory_queue import run_factory_queue_start
from app.project_intake import run_project_intake_create


def test_project_intake_create_writes_minimal_artifacts(tmp_path: Path) -> None:
    report = run_project_intake_create(
        project_name="demo-simple-web-mvp",
        project_kind="web",
        from_template="simple-web-mvp",
        dry_run=True,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["dry_run"] is True
    assert report["executed_live"] is False
    assert report["project_name"] == "demo-simple-web-mvp"
    assert report["generated_prd_path"]
    assert report["generated_spec_path"]
    assert report["generated_sprint_path"]
    assert (tmp_path / report["generated_prd_path"]).exists()
    assert (tmp_path / report["generated_spec_path"]).exists()
    assert (tmp_path / report["generated_sprint_path"]).exists()
    assert (tmp_path / report["report_path"]).exists()
    assert len(report["task_candidates"]) >= 1


def test_factory_queue_start_reads_latest_intake_report(tmp_path: Path) -> None:
    intake_report = run_project_intake_create(
        project_name="demo-simple-web-mvp",
        project_kind="web",
        from_template="simple-web-mvp",
        dry_run=True,
        repo=tmp_path,
    )

    report = run_factory_queue_start(
        dry_run=True,
        plan_only=False,
        max_tasks=3,
        max_steps_per_task=1,
        cost_aware=True,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["dry_run"] is True
    assert report["plan_only"] is False
    assert report["executed_live"] is False
    assert report["selected_count"] <= 3
    assert len(report["selected_tasks"]) <= 3
    assert report["capsule_recommended_count"] >= 1
    assert report["source_intake_report"] == intake_report["report_path"]
    assert (tmp_path / report["report_path"]).exists()
