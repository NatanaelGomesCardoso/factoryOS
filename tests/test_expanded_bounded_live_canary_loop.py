from __future__ import annotations

from pathlib import Path

import pytest

import app.post_expansion_evaluator as post_expansion_evaluator
from app import factory_start
from app.task_runner import TaskRunnerError


def _base_validation(repo: Path) -> dict[str, object]:
    return {
        "run": {"task_id": "task-1", "workspace_path": "workspaces/runs/run-1"},
        "workspace": {"branch": "run-1", "workspace_head": "workspace-head"},
        "readiness": {"status": "ready", "main_head": "master-head", "workspace_head": "workspace-head"},
        "sync_plan": {"status": "already_current"},
        "review_gate": {"report_path": "reports/expanded-long-run-reviews/gate.json"},
        "rehearsal": {"report_path": "reports/expanded-long-run-rehearsals/rehearsal.json"},
        "cost_audit": {"report_path": "reports/cost-audits/audit.json", "status": "ideal"},
        "blockers": [],
        "warnings": [],
        "max_steps": 6,
        "target_minutes": 30,
        "workspace_path": "workspaces/runs/run-1",
        "workspace_branch": "run-1",
        "readiness_status": "ready",
        "sync_plan_status": "already_current",
    }


def test_expanded_bounded_live_canary_isolates_attempt_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path
    workspace_path = repo / "workspaces" / "runs" / "run-1"
    workspace_path.mkdir(parents=True)
    old_attempt_dir = repo / "reports" / "expanded-bounded-live-canary" / "attempts" / "old-attempt"
    old_attempt_dir.mkdir(parents=True)
    for index in range(1, 7):
        (old_attempt_dir / f"step-{index}.txt").write_text(f"old-{index}\n", encoding="utf-8")

    monkeypatch.setattr(factory_start, "validate_expanded_bounded_live_canary_request", lambda *args, **kwargs: _base_validation(repo))
    monkeypatch.setattr(factory_start, "_normalize_expanded_canary_validation", lambda validation, **kwargs: validation)
    monkeypatch.setattr(factory_start, "_git", lambda *args, **kwargs: "master-head")
    monkeypatch.setattr(factory_start, "_git_optional", lambda *args, **kwargs: "workspace-head")
    monkeypatch.setattr(factory_start, "workspace_status", lambda *args, **kwargs: {"workspace": {"workspace_head": "workspace-head", "branch": "run-1"}})
    monkeypatch.setattr(factory_start, "_write_json_atomic", lambda *args, **kwargs: None)
    monkeypatch.setattr(factory_start, "_build_expanded_bounded_live_canary_command", lambda *args, **kwargs: ["codex"])
    monkeypatch.setattr(factory_start, "_expanded_bounded_live_canary_report_path", lambda *args, **kwargs: repo / "reports" / "expanded-bounded-live-canary" / "report.json")
    iso_values = iter([
        "2026-05-02T00:00:00-03:00",
        "2026-05-02T00:00:01-03:00",
        "2026-05-02T00:00:02-03:00",
        "2026-05-02T00:00:03-03:00",
        "2026-05-02T00:00:04-03:00",
        "2026-05-02T00:00:05-03:00",
        "2026-05-02T00:00:06-03:00",
        "2026-05-02T00:00:07-03:00",
        "2026-05-02T00:00:08-03:00",
        "2026-05-02T00:00:09-03:00",
    ])
    monkeypatch.setattr(factory_start, "_now_iso", lambda: next(iso_values))
    monkeypatch.setattr(factory_start.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(
        post_expansion_evaluator,
        "evaluate_post_expansion_canary_report",
        lambda **kwargs: {"report_path": kwargs["report_path"], "decision": "passed"},
    )

    calls: list[int] = []
    written_files: list[str] = []

    def fake_step(*, step: int, allowed_file: str, **kwargs):
        calls.append(step)
        step_path = repo / allowed_file
        step_path.parent.mkdir(parents=True, exist_ok=True)
        step_path.write_text(f"new-{step}\n", encoding="utf-8")
        written_files.append(step_path.relative_to(repo).as_posix())
        return (
            {
                "step": step,
                "status": "passed",
                "decision": "passed",
                "executed_live": True,
                "attempt_id": "attempt-new",
                "allowed_file": allowed_file,
                "expected_step_file": allowed_file,
                "changed_files": [allowed_file],
                "codex_exit_code": 0,
                "stdout_path": allowed_file,
                "stderr_path": allowed_file,
                "workspace_head_before": "workspace-head",
                "workspace_head_after": "workspace-head",
                "started_at": "2026-05-02T00:00:00-03:00",
                "finished_at": "2026-05-02T00:00:00-03:00",
                "reason": "",
            },
            f"stdout-{step}",
            f"stderr-{step}",
        )

    monkeypatch.setattr(factory_start, "_run_expanded_bounded_live_canary_step", fake_step)
    monkeypatch.setattr(factory_start, "_current_changed_files", lambda *args, **kwargs: [*written_files, *(f"reports/expanded-bounded-live-canary/attempts/old-attempt/step-{index}.txt" for index in range(1, 7))])

    report = factory_start.run_expanded_bounded_live_canary(
        "run-1",
        max_steps=6,
        target_minutes=30,
        bounded=True,
        canary=True,
        cost_aware=True,
        no_push=True,
        no_deploy=True,
        no_paid_api=True,
        no_secrets=True,
        repo=repo,
    )

    assert calls == [1, 2, 3, 4, 5, 6]
    assert report["steps_completed"] == 6
    assert report["codex_exit_codes"] == [0, 0, 0, 0, 0, 0]
    assert report["attempt_id"]
    assert report["allowed_files"] == [
        f"reports/expanded-bounded-live-canary/attempts/{report['attempt_id']}/step-{index}.txt"
        for index in range(1, 7)
    ]
    assert report["disallowed_files"] == []
    assert all(path.startswith(f"reports/expanded-bounded-live-canary/attempts/{report['attempt_id']}/") for path in report["changed_files"])
    assert not any(path.startswith("reports/expanded-bounded-live-canary/attempts/old-attempt/") for path in report["changed_files"])


def test_expanded_bounded_live_canary_blocks_max_steps_seven() -> None:
    with pytest.raises(TaskRunnerError):
        factory_start._validate_expanded_bounded_live_canary_max_steps(7)


def test_expanded_bounded_live_canary_blocks_missing_safety_flags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path
    monkeypatch.setattr(factory_start, "_expanded_bounded_live_canary_gate_result", lambda *args, **kwargs: {"max_steps": 6, "target_minutes": 30})

    with pytest.raises(TaskRunnerError, match="--no-push"):
        factory_start.validate_expanded_bounded_live_canary_request(
            "run-1",
            max_steps=6,
            target_minutes=30,
            bounded=True,
            canary=True,
            cost_aware=True,
            no_push=False,
            no_deploy=True,
            no_paid_api=True,
            no_secrets=True,
            repo=repo,
        )
