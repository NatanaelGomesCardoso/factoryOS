from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.reversa_integration import (
    REPORT_FIELDS,
    run_reversa_project_install,
    run_reversa_project_plan,
    run_reversa_project_sdd_intake,
    run_reversa_project_status,
)
from app.task_runner import TaskRunnerError


FIXTURE = Path("<CODE_ROOT>/_factoryos_reversa_test_fixture_sdd_dirty")


def _prepare_git_fixture() -> Path:
    if FIXTURE.exists():
        shutil.rmtree(FIXTURE)
    FIXTURE.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=FIXTURE, check=True)
    (FIXTURE / "README.md").write_text("# Fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=FIXTURE, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.invalid", "-c", "user.name=Test", "commit", "-qm", "init"],
        cwd=FIXTURE,
        check=True,
    )
    return FIXTURE


def _cleanup_fixture() -> None:
    if FIXTURE.exists():
        shutil.rmtree(FIXTURE)


def _assert_report_contract(report: dict[str, object]) -> None:
    for field in REPORT_FIELDS:
        assert field in report
    assert report["no_push"] is True
    assert report["no_deploy"] is True
    assert report["no_paid_api"] is True
    assert report["no_secrets"] is True


def test_reversa_project_plan_blocks_protected_and_outside_targets(tmp_path: Path) -> None:
    factoryos = run_reversa_project_plan(target="<FACTORYOS_ROOT>", dry_run=True, repo=tmp_path)
    harness = run_reversa_project_plan(target="<HARNESS_ROOT>", dry_run=True, repo=tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_report = run_reversa_project_plan(target=outside, dry_run=True, repo=tmp_path)

    assert factoryos["target_allowed"] is False
    assert factoryos["blocked_reason"] == "protected_factoryos_default"
    assert harness["target_allowed"] is False
    assert harness["blocked_reason"] == "protected_harness"
    assert outside_report["target_allowed"] is False
    assert outside_report["blocked_reason"] == "outside_code_root"
    _assert_report_contract(factoryos)
    _assert_report_contract(harness)
    _assert_report_contract(outside_report)


def test_reversa_dry_run_install_status_and_sdd_intake(tmp_path: Path) -> None:
    target = _prepare_git_fixture()
    try:
        sdd = target / "_reversa_sdd"
        sdd.mkdir()
        (sdd / "inventory.md").write_text("# Inventory\n", encoding="utf-8")

        dirty_plan = run_reversa_project_plan(target=target, dry_run=True, repo=tmp_path)
        dirty_install = run_reversa_project_install(target=target, dry_run=True, repo=tmp_path)
        dirty_intake = run_reversa_project_sdd_intake(target=target, dry_run=True, repo=tmp_path)

        assert dirty_plan["ok"] is False
        assert dirty_plan["blocked_reason"] == "git_not_clean"
        assert dirty_install["ok"] is False
        assert dirty_install["blocked_reason"] == "git_not_clean"
        assert dirty_intake["ok"] is True
        assert dirty_intake["git_clean"] is False
        assert dirty_intake["dirty_reversa_artifacts_allowed"] is True
        assert dirty_intake["allowed_dirty_paths"] == ["_reversa_sdd/inventory.md"]
        assert dirty_intake["blocked_reason"] is None
        assert dirty_intake["safe_to_execute"] is True
        assert dirty_intake["human_review_required"] is True

        (target / "notes.txt").write_text("blocked\n", encoding="utf-8")

        blocked_intake = run_reversa_project_sdd_intake(target=target, dry_run=True, repo=tmp_path)

        plan = run_reversa_project_plan(target=target, dry_run=True, repo=tmp_path)
        install = run_reversa_project_install(target=target, dry_run=True, repo=tmp_path)
        status = run_reversa_project_status(target=target, repo=tmp_path)
        intake = blocked_intake

        assert plan["ok"] is False
        assert plan["blocked_reason"] == "git_not_clean"
        assert install["ok"] is False
        assert install["blocked_reason"] == "git_not_clean"
        assert install["install_executed"] is False
        assert status["sdd_detected"] is True
        assert intake["ok"] is False
        assert intake["blocked_reason"] == "git_not_clean_non_reversa_changes"
        assert intake["dirty_reversa_artifacts_allowed"] is False
        _assert_report_contract(plan)
        _assert_report_contract(install)
        _assert_report_contract(status)
        _assert_report_contract(intake)
    finally:
        _cleanup_fixture()


def test_reversa_live_install_is_disabled() -> None:
    try:
        run_reversa_project_install(target="<FACTORYOS_ROOT>", dry_run=False)
    except TaskRunnerError as exc:
        assert "live install not enabled in V0" in str(exc)
    else:
        raise AssertionError("live install should be blocked")


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_reversa_project_plan_blocks_protected_and_outside_targets(tmp_path)
        test_reversa_dry_run_install_status_and_sdd_intake(tmp_path)
    test_reversa_live_install_is_disabled()
