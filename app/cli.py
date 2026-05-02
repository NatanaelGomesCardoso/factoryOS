import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.evaluator import evaluate_signals
from app.capsule_execution_policy import policy_for_category, policy_for_run, policy_for_task
from app.codex_context_router import context_pack_for_run, context_pack_for_task
from app.codex_context_capsule import create_capsule, inspect_capsule, list_capsules
from app.codex_capsule_execution import (
    run_codex_capsule_apply,
    run_codex_capsule_diff,
    run_codex_capsule_export_plan,
    run_codex_capsule_run,
    run_codex_capsule_status,
)
from app.cheap_task_factory_e2e import run_cheap_task_factory_e2e
from app.capsule_cost_diagnosis import run_capsule_cost_diagnosis
from app.codex_cost_audit import run_codex_cost_audit
from app.codex_quiet_runner import compare_quiet_run_logs, run_codex_quiet_run
from app.expanded_long_run_rehearsal import run_expanded_long_run_rehearsal
from app.expanded_long_run_review_gate import run_expanded_long_run_review_gate
from app.codex_handoff import run_execute, run_handoff
from app.codex_profile import codex_plan_for_run, codex_plan_for_task, list_codex_profiles
from app.compact_execution_harness import (
    COMPACT_EXECUTION_BUDGETS,
    analyze_compact_exec_log,
    compact_exec_budget,
    compact_exec_report,
)
from app.artifact_intake import run_artifact_intake_plan, run_artifact_intake_register
from app.mvp_delivery_package import run_mvp_delivery_package_create
from app.no_diff_prompt import check_no_diff_prompt_contract, no_diff_prompt_contract_text
from app.memory_digest import create_memory_digest, latest_memory_digest, list_memory_digests
from app.mvp_evaluator import run_mvp_evaluate
from app.project_pilot_runbook import run_project_pilot_runbook_create
from app.output_budget import (
    DEFAULT_MAX_BYTES,
    MAX_TERMINAL_LINES,
    build_output_budget_report,
    check_output_budget,
    output_budget_contract_text,
)
from app.routing_contracts import (
    CODEX_PROFILE_HINT_VALUES,
    CONTEXT_POLICY_VALUES,
    FACTORY_CATEGORY_VALUES,
    LIVE_POLICY_VALUES,
    ROUTING_CONTRACT_VERSION_VALUES,
    routing_contract_validation_payload,
)
from app.execution_evaluator import evaluate_execution, execution_close_if_passed
from app.post_expansion_evaluator import (
    evaluate_post_expansion_canary_report,
    run_post_expansion_rollback_plan,
)
from app.long_run_planner import run_factory_long_run_plan
from app.long_run_rehearsal import run_factory_long_run_rehearsal
from app.maintenance_plan import run_factory_maintenance_plan
from app.controlled_loop import run_controlled_loop
from app.obsidian_sync import run_obsidian_project_sync
from app.report_retention import run_report_retention_audit, run_report_retention_cleanup_plan, run_report_retention_plan
from app.reversa_integration import (
    run_reversa_global_check,
    run_reversa_project_install,
    run_reversa_project_plan,
    run_reversa_project_sdd_intake,
    run_reversa_project_status,
)
from app.factory_start import run_factory_start
from app.factory_start import run_expanded_bounded_live_canary
from app.factory_queue import run_factory_queue_start
from app.factory_tick import run_factory_tick
from app.live_canary_review_gate import run_bounded_live_canary_review_gate
from app.live_canary import run_live_canary
from app.long_run_expansion_policy import run_long_run_expansion_policy
from app.local_task_router import route_task
from app.report_index import REPORT_KINDS, latest_report, list_reports
from app.state_hygiene import (
    factory_state_apply,
    factory_state_audit,
    factory_state_backfill_sprint_013,
    factory_state_plan,
)
from app.project_intake import run_project_intake_create
from app.mvp_apply_plan import run_mvp_apply_plan_create
from app.mvp_build_plan import run_mvp_build_plan_create
from app.mvp_capsule_build_canary import run_mvp_capsule_build_canary
from app.mvp_templates import get_template, list_templates, validate_template
from app.project_workspace import run_project_workspace_scaffold
from app.token_usage import parse_token_usage_log
from app.task_runner import (
    TaskRunnerError,
    evaluate_task,
    create_task,
    fail_task,
    finish_task,
    list_tasks,
    note_task,
    show_task,
    start_task,
)
from app.run_workspace import (
    create_run,
    fail_run,
    finish_run,
    prepare_run_workspace,
    run_workspace_sync_apply,
    run_workspace_sync_plan,
    run_workspace_readiness,
    list_runs,
    show_run,
    workspace_status,
)
from app.worktree_lifecycle import run_worktree_lifecycle_plan
from app.reuse_first import write_discovery
from app.help_center import check_help_docs, list_help_docs, print_json
from app.github_publish_plan import (
    run_github_backup_plan,
    run_github_publish_plan,
    run_github_release_checklist,
)


def cmd_route(args: argparse.Namespace) -> int:
    task = " ".join(args.task).strip()

    if not task:
        print("ERRO: informe uma tarefa para classificar.", file=sys.stderr)
        return 2

    decision = route_task(task)
    payload = asdict(decision)
    output = json.dumps(payload, ensure_ascii=False, indent=2)

    print(output)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")

    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    idea = " ".join(args.idea).strip()

    if not idea:
        print("ERRO: informe uma ideia para discovery.", file=sys.stderr)
        return 2

    out_path = write_discovery(idea=idea, out=args.out)

    print(json.dumps({
        "ok": True,
        "type": "reuse_first_discovery",
        "path": str(out_path),
        "next_step": "Cole este discovery no ChatGPT para pesquisa Reuse First antes de gerar PRD/SPEC/Codex."
    }, ensure_ascii=False, indent=2))

    return 0


def cmd_help_docs_list(args: argparse.Namespace) -> int:
    return print_json(list_help_docs())


def cmd_help_docs_check(args: argparse.Namespace) -> int:
    result = check_help_docs(dry_run=bool(args.dry_run))
    return print_json(result)


def cmd_output_budget_contract(args: argparse.Namespace) -> int:
    print(output_budget_contract_text(), end="")
    return 0


def cmd_no_diff_prompt_contract(args: argparse.Namespace) -> int:
    print(no_diff_prompt_contract_text(), end="")
    return 0


def cmd_no_diff_prompt_check(args: argparse.Namespace) -> int:
    try:
        result = check_no_diff_prompt_contract(args.prompt_file)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result)


def cmd_token_usage_parse(args: argparse.Namespace) -> int:
    try:
        result = parse_token_usage_log(args.log)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result)


def cmd_output_budget_check(args: argparse.Namespace) -> int:
    try:
        result = check_output_budget(args.log, max_lines=args.max_lines, max_bytes=args.max_bytes)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    result["log_path"] = str(Path(args.log))
    return _print_compact_json(result)


def cmd_codex_output_budget_report(args: argparse.Namespace) -> int:
    try:
        parser_result = parse_token_usage_log(args.log)
        report = build_output_budget_report(
            log_path=args.log,
            repo=Path(__file__).resolve().parents[1],
            parser_result=parser_result,
            max_lines=MAX_TERMINAL_LINES,
            max_bytes=DEFAULT_MAX_BYTES,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(report)


def cmd_codex_quiet_run(args: argparse.Namespace) -> int:
    dry_run = bool(args.dry_run)
    execute = bool(args.execute)
    if not dry_run and not execute:
        dry_run = True

    try:
        result = run_codex_quiet_run(
            prompt_file=args.prompt_file,
            cwd=args.cwd,
            model=args.model,
            reasoning=args.reasoning,
            sandbox=args.sandbox,
            approval=args.approval,
            label=args.label,
            allowed_paths=args.allowed_path or None,
            no_push=args.no_push,
            no_deploy=args.no_deploy,
            no_paid_api=args.no_paid_api,
            no_secrets=args.no_secrets,
            dry_run=dry_run,
            execute=execute,
            timeout_seconds=args.timeout_seconds,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    payload = dict(result)
    payload.pop("terminal_summary", None)
    return _print_compact_json(payload)


def cmd_codex_quiet_ab_report(args: argparse.Namespace) -> int:
    try:
        result = compare_quiet_run_logs(args.log_a, args.log_b)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result)


def cmd_codex_run_result_check(args: argparse.Namespace) -> int:
    json_path = Path(args.json)

    if not json_path.exists():
        print(f"ERRO: report inexistente: {json_path}", file=sys.stderr)
        return 2
    if not json_path.is_file():
        print(f"ERRO: report não aponta para arquivo: {json_path}", file=sys.stderr)
        return 2
    if json_path.is_symlink():
        print("ERRO: symlink não permitido no report.", file=sys.stderr)
        return 2

    content = json_path.read_text(encoding="utf-8")
    if not content.strip():
        print(f"ERRO: report vazio: {json_path}", file=sys.stderr)
        return 2

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        print(f"ERRO: JSON inválido em {json_path.name}: {exc.msg}", file=sys.stderr)
        return 2

    if not isinstance(payload, dict):
        print(f"ERRO: report JSON precisa ser um objeto: {json_path}", file=sys.stderr)
        return 2

    execution_status = payload.get("execution_status")
    if execution_status not in {"succeeded", "succeeded_with_budget_warnings", "failed", "timeout"}:
        if bool(payload.get("timeout", False)):
            execution_status = "timeout"
        elif payload.get("exit_code") not in (None, 0):
            execution_status = "failed"
        else:
            execution_status = "succeeded" if payload.get("error_type") is None else "failed"

    budget_status = payload.get("budget_status")
    if budget_status not in {"ok", "warn", "blocked"}:
        budget_status = payload.get("captured_log_status")
    if budget_status not in {"ok", "warn", "blocked"}:
        budget_status = payload.get("output_budget_check", {}).get("status", "ok")
    if budget_status not in {"ok", "warn", "blocked"}:
        budget_status = "blocked"

    budget_ok = payload.get("budget_ok")
    if budget_ok is None:
        budget_ok = budget_status != "blocked"

    timeout = bool(payload.get("timeout", False))
    exit_code = payload.get("exit_code")
    if timeout:
        derived_overall_status = "timeout"
    elif exit_code not in {None, 0}:
        derived_overall_status = "failed"
    elif execution_status == "succeeded" and budget_status in {"warn", "blocked"}:
        derived_overall_status = "succeeded_with_budget_warnings"
    elif execution_status == "succeeded" and budget_status == "ok":
        derived_overall_status = "succeeded"
    elif execution_status == "succeeded_with_budget_warnings":
        derived_overall_status = "succeeded_with_budget_warnings"
    else:
        derived_overall_status = execution_status

    summary = {
        "ok": derived_overall_status in {"succeeded", "succeeded_with_budget_warnings"},
        "json_ok": True,
        "execution_status": execution_status,
        "budget_status": budget_status,
        "report_ok": bool(payload.get("ok", False)),
        "budget_ok": bool(budget_ok),
        "overall_status": derived_overall_status,
        "timeout": timeout,
        "exit_code": exit_code,
        "error_type": payload.get("error_type"),
        "path": str(json_path),
    }

    _print_compact_json(summary)
    if derived_overall_status in {"succeeded", "succeeded_with_budget_warnings"}:
        return 0
    if derived_overall_status in {"failed", "timeout"}:
        return 1
    return 2


def cmd_compact_exec_budget(args: argparse.Namespace) -> int:
    return _print_compact_json(compact_exec_budget())


def cmd_compact_exec_check(args: argparse.Namespace) -> int:
    try:
        result = analyze_compact_exec_log(args.log, category=args.category, mode=args.mode)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result)


def cmd_compact_exec_report(args: argparse.Namespace) -> int:
    try:
        result = compact_exec_report(args.log, category=args.category, mode=args.mode)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result)


def cmd_memory_digest_create(args: argparse.Namespace) -> int:
    try:
        result = create_memory_digest(title=args.title, source_report=args.source_report, sprint=args.sprint)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result)


def cmd_memory_digest_latest(args: argparse.Namespace) -> int:
    return _print_compact_json(latest_memory_digest())


def cmd_memory_digest_list(args: argparse.Namespace) -> int:
    return _print_compact_json(list_memory_digests(limit=args.limit))


def cmd_evaluate(args: argparse.Namespace) -> int:
    signals = {
        "python_ok": args.python_ok,
        "json_ok": args.json_ok,
        "browser_ok": args.browser_ok,
        "security_ok": args.security_ok,
        "high_risk": args.high_risk,
        "git_clean": args.git_clean,
        "git_expected_dirty": args.git_expected_dirty,
        "notes": args.notes or "",
    }

    payload = evaluate_signals(signals)
    output = json.dumps(payload, ensure_ascii=False, indent=2)

    print(output)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")

    return 0


def cmd_task_evaluate(args: argparse.Namespace) -> int:
    try:
        report = evaluate_task(args.task_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _print_task_result(result: dict[str, object], out_path: str | None = None) -> int:
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)

    if out_path:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")

    return 0


def _print_compact_json(payload: dict[str, Any], out_path: str | None = None) -> int:
    output = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    print(output)

    if out_path:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")

    return 0


def _add_routing_contract_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--routing-contract-version",
        choices=sorted(ROUTING_CONTRACT_VERSION_VALUES),
        help="Versão do contrato explícito de roteamento"
    )
    parser.add_argument(
        "--factory-category",
        choices=sorted(FACTORY_CATEGORY_VALUES),
        help="Categoria explícita da factory"
    )
    parser.add_argument(
        "--codex-profile-hint",
        choices=sorted(CODEX_PROFILE_HINT_VALUES),
        help="Hint explícito de perfil Codex"
    )
    parser.add_argument(
        "--context-policy",
        choices=sorted(CONTEXT_POLICY_VALUES),
        help="Política explícita de contexto"
    )
    parser.add_argument(
        "--live-policy",
        choices=sorted(LIVE_POLICY_VALUES),
        help="Política explícita para live"
    )
    parser.add_argument("--max-context-chars-override", type=int, help="Override explícito do budget de contexto")
    parser.add_argument("--max-changed-files-override", type=int, help="Override explícito de arquivos alterados")
    parser.add_argument("--max-steps-override", type=int, help="Override explícito do máximo de steps")
    parser.add_argument("--target-minutes-override", type=int, help="Override explícito de duração alvo")
    parser.add_argument("--retention-policy", help="Política textual opcional de retenção")
    parser.add_argument("--worktree-policy", help="Política textual opcional de worktree")


def _routing_contract_kwargs_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "routing_contract_version": args.routing_contract_version,
        "factory_category": args.factory_category,
        "codex_profile_hint": args.codex_profile_hint,
        "context_policy": args.context_policy,
        "live_policy": args.live_policy,
        "max_context_chars_override": args.max_context_chars_override,
        "max_changed_files_override": args.max_changed_files_override,
        "max_steps_override": args.max_steps_override,
        "target_minutes_override": args.target_minutes_override,
        "retention_policy": args.retention_policy,
        "worktree_policy": args.worktree_policy,
    }


def cmd_task_create(args: argparse.Namespace) -> int:
    try:
        result = create_task(
            title=args.title,
            description=args.description,
            risk=args.risk,
            executor=args.executor,
            routing_contract=_routing_contract_kwargs_from_args(args),
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_task_list(args: argparse.Namespace) -> int:
    try:
        result = list_tasks()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_task_show(args: argparse.Namespace) -> int:
    try:
        result = show_task(args.task_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_task_note(args: argparse.Namespace) -> int:
    note_text = " ".join(args.note).strip()

    try:
        result = note_task(args.task_id, note_text)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_create(args: argparse.Namespace) -> int:
    try:
        result = create_run(args.task_id, routing_contract=_routing_contract_kwargs_from_args(args))
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_routing_contract_validate(args: argparse.Namespace) -> int:
    if bool(args.task_id) == bool(args.run_id):
        print("ERRO: informe exatamente um de --task-id ou --run-id.", file=sys.stderr)
        return 2

    try:
        if args.task_id:
            task = show_task(args.task_id)["task"]
            result = routing_contract_validation_payload(task=task)
            result["task_id"] = args.task_id
        else:
            run = show_run(args.run_id)["run"]
            task = show_task(str(run["task_id"]))["task"]
            result = routing_contract_validation_payload(task=task, run=run)
            result["run_id"] = args.run_id
            result["task_id"] = str(run["task_id"])
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_list(args: argparse.Namespace) -> int:
    try:
        result = list_runs()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_show(args: argparse.Namespace) -> int:
    try:
        result = show_run(args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_finish(args: argparse.Namespace) -> int:
    try:
        result = finish_run(args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_fail(args: argparse.Namespace) -> int:
    try:
        result = fail_run(args.run_id, args.reason)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_workspace_prepare(args: argparse.Namespace) -> int:
    try:
        result = prepare_run_workspace(args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_workspace_status(args: argparse.Namespace) -> int:
    try:
        result = workspace_status(args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_workspace_readiness(args: argparse.Namespace) -> int:
    try:
        result = run_workspace_readiness(args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_workspace_sync_plan(args: argparse.Namespace) -> int:
    try:
        result = run_workspace_sync_plan(args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_workspace_sync_apply(args: argparse.Namespace) -> int:
    try:
        result = run_workspace_sync_apply(args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_run_handoff(args: argparse.Namespace) -> int:
    try:
        result = run_handoff(args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_capsule_execution_policy(args: argparse.Namespace) -> int:
    if sum(bool(value) for value in (args.task_id, args.run_id, args.category)) != 1:
        print("ERRO: informe exatamente um de --task-id, --run-id ou --category.", file=sys.stderr)
        return 2

    try:
        if args.task_id:
            result = policy_for_task(args.task_id)
        elif args.run_id:
            result = policy_for_run(args.run_id)
        else:
            result = policy_for_category(args.category)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_run_execute(args: argparse.Namespace) -> int:
    if args.live and args.dry_run:
        print("ERRO: --dry-run e --live são mutuamente exclusivos.", file=sys.stderr)
        return 2

    try:
        result = run_execute(args.run_id, live=args.live)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_codex_profile_list(args: argparse.Namespace) -> int:
    return _print_task_result(list_codex_profiles(), args.out)


def cmd_codex_plan(args: argparse.Namespace) -> int:
    if bool(args.task_id) == bool(args.run_id):
        print("ERRO: informe exatamente um de --task-id ou --run-id.", file=sys.stderr)
        return 2

    try:
        if args.task_id:
            result = codex_plan_for_task(args.task_id)
        else:
            result = codex_plan_for_run(args.run_id, live=args.live, max_steps=args.max_steps)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_codex_context(args: argparse.Namespace) -> int:
    if bool(args.task_id) == bool(args.run_id):
        print("ERRO: informe exatamente um de --task-id ou --run-id.", file=sys.stderr)
        return 2

    try:
        if args.task_id:
            result = context_pack_for_task(args.task_id)
        else:
            result = context_pack_for_run(args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_codex_capsule_create(args: argparse.Namespace) -> int:
    try:
        result = create_capsule(
            label=args.label,
            source_root=args.source_root,
            include_paths=args.include,
            use_latest_digest=args.use_latest_digest,
            max_context_bytes=args.max_context_bytes,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_codex_capsule_list(args: argparse.Namespace) -> int:
    try:
        result = list_capsules(limit=args.limit)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_codex_capsule_inspect(args: argparse.Namespace) -> int:
    try:
        result = inspect_capsule(args.capsule)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_codex_capsule_run(args: argparse.Namespace) -> int:
    try:
        result = run_codex_capsule_run(
            capsule=args.capsule,
            prompt_file=args.prompt_file,
            label=args.label,
            model=args.model,
            reasoning=args.reasoning,
            sandbox=args.sandbox,
            execute=args.execute,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_codex_capsule_diff(args: argparse.Namespace) -> int:
    try:
        result = run_codex_capsule_diff(capsule=args.capsule)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_codex_capsule_export_plan(args: argparse.Namespace) -> int:
    try:
        result = run_codex_capsule_export_plan(capsule=args.capsule, source_root=args.source_root)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_codex_capsule_apply(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: codex-capsule-apply aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_codex_capsule_apply(
            capsule=args.capsule,
            source_root=args.source_root,
            dry_run=True,
            export_plan=args.export_plan,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_codex_capsule_status(args: argparse.Namespace) -> int:
    try:
        result = run_codex_capsule_status(
            execution_report=args.execution_report,
            export_plan=args.export_plan,
            diff_report=args.diff_report,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_cheap_task_factory_e2e(args: argparse.Namespace) -> int:
    if args.dry_run and args.execute_canary:
        print("ERRO: --dry-run e --execute-canary são mutuamente exclusivos.", file=sys.stderr)
        return 2

    try:
        result = run_cheap_task_factory_e2e(
            category=args.category,
            label=args.label,
            dry_run=args.dry_run,
            execute_canary=args.execute_canary,
            capsule_mode=args.capsule_mode,
            max_prompt_bytes=args.max_prompt_bytes,
            max_capsule_bytes=args.max_capsule_bytes,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_capsule_cost_diagnose(args: argparse.Namespace) -> int:
    try:
        result = run_capsule_cost_diagnosis(e2e_report=args.e2e_report)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_codex_cost_audit(args: argparse.Namespace) -> int:
    try:
        result = run_codex_cost_audit(timeout_seconds=args.timeout_seconds)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_factory_tick(args: argparse.Namespace) -> int:
    if args.live:
        print("ERRO: live mode is out of scope for Factory Tick V0", file=sys.stderr)
        return 2

    try:
        result = run_factory_tick(args.run_id, dry_run=True, live=False)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_factory_loop(args: argparse.Namespace) -> int:
    if args.live:
        print("ERRO: live mode continua bloqueado no Controlled Execution Loop V1", file=sys.stderr)
        return 2

    if args.dry_run and args.live:
        print("ERRO: --dry-run e --live são mutuamente exclusivos.", file=sys.stderr)
        return 2

    try:
        result = run_controlled_loop(
            run_id=args.run_id,
            max_steps=args.max_steps,
            dry_run=True,
            live=False,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_factory_start(args: argparse.Namespace) -> int:
    if args.dry_run and args.live:
        print("ERRO: --dry-run e --live são mutuamente exclusivos.", file=sys.stderr)
        return 2

    selected_modes = [flag for flag in (args.dry_run, args.live, args.plan_only) if flag]
    if len(selected_modes) != 1:
        print("ERRO: informe exatamente um de --dry-run, --live ou --plan-only.", file=sys.stderr)
        return 2

    try:
        result = run_factory_start(
            run_id=args.run_id,
            max_steps=args.max_steps,
            target_minutes=args.target_minutes,
            dry_run=args.dry_run,
            live=args.live,
            plan_only=args.plan_only,
            cost_aware=args.cost_aware,
            canary=args.canary,
            evaluate=args.evaluate,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_factory_queue_start(args: argparse.Namespace) -> int:
    if args.dry_run and args.plan_only:
        print("ERRO: --dry-run e --plan-only sao mutuamente exclusivos.", file=sys.stderr)
        return 2
    if not args.dry_run and not args.plan_only:
        print("ERRO: informe --dry-run ou --plan-only.", file=sys.stderr)
        return 2
    if not args.cost_aware:
        print("ERRO: factory-queue-start exige --cost-aware nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_factory_queue_start(
            dry_run=args.dry_run,
            plan_only=args.plan_only,
            max_tasks=args.max_tasks,
            max_steps_per_task=args.max_steps_per_task,
            cost_aware=args.cost_aware,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_project_intake_create(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: project-intake-create aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_project_intake_create(
            project_name=args.name,
            project_kind=args.kind,
            from_template=args.from_template,
            dry_run=True,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_reversa_global_check(args: argparse.Namespace) -> int:
    return _print_compact_json(run_reversa_global_check(), args.out)


def cmd_reversa_project_plan(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: reversa-project-plan exige --dry-run nesta sprint.", file=sys.stderr)
        return 2
    try:
        result = run_reversa_project_plan(target=args.target, dry_run=True)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    return _print_compact_json(result, args.out)


def cmd_reversa_project_install(args: argparse.Namespace) -> int:
    try:
        result = run_reversa_project_install(target=args.target, dry_run=bool(args.dry_run))
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    return _print_compact_json(result, args.out)


def cmd_reversa_project_status(args: argparse.Namespace) -> int:
    try:
        result = run_reversa_project_status(target=args.target)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    return _print_compact_json(result, args.out)


def cmd_reversa_project_sdd_intake(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: reversa-project-sdd-intake exige --dry-run nesta sprint.", file=sys.stderr)
        return 2
    try:
        result = run_reversa_project_sdd_intake(target=args.target, dry_run=True)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    return _print_compact_json(result, args.out)


def cmd_artifact_intake_plan(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: artifact-intake-plan aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_artifact_intake_plan(
            project_name=args.project,
            source=args.source,
            dry_run=True,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_artifact_intake_register(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: artifact-intake-register aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_artifact_intake_register(
            project_name=args.project,
            source=args.source,
            dry_run=True,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_mvp_template_list(args: argparse.Namespace) -> int:
    payload = {
        "ok": True,
        "template_registry_version": "v0",
        "templates": [template.to_dict() for template in list_templates()],
    }
    return _print_compact_json(payload, args.out)


def cmd_mvp_template_show(args: argparse.Namespace) -> int:
    try:
        template = get_template(args.template)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json({
        "ok": True,
        "template_registry_version": "v0",
        "template": template.to_dict(),
    }, args.out)


def cmd_mvp_template_validate(args: argparse.Namespace) -> int:
    try:
        result = validate_template(args.template)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_mvp_build_plan_create(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: mvp-build-plan-create aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_mvp_build_plan_create(
            project_name=args.project,
            from_intake=args.from_intake,
            dry_run=True,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_mvp_evaluate(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: mvp-evaluate aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_mvp_evaluate(
            project_name=args.project,
            workspace=args.workspace,
            dry_run=True,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_mvp_capsule_build_canary(args: argparse.Namespace) -> int:
    if args.dry_run and args.execute_canary:
        print("ERRO: --dry-run e --execute-canary são mutuamente exclusivos.", file=sys.stderr)
        return 2
    if not args.dry_run and not args.execute_canary:
        print("ERRO: informe --dry-run ou --execute-canary.", file=sys.stderr)
        return 2

    try:
        result = run_mvp_capsule_build_canary(
            build_plan=args.build_plan,
            dry_run=args.dry_run,
            execute_canary=args.execute_canary,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_mvp_apply_plan_create(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: mvp-apply-plan-create aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_mvp_apply_plan_create(
            canary_report=args.canary_report,
            dry_run=True,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_project_workspace_scaffold(args: argparse.Namespace) -> int:
    try:
        result = run_project_workspace_scaffold(
            project_name=args.project,
            kind=args.kind,
            from_template=args.from_template,
            dry_run=args.dry_run,
            create_workspace=args.create_workspace,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_mvp_delivery_package_create(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: mvp-delivery-package-create aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_mvp_delivery_package_create(
            project_name=args.project,
            workspace=args.workspace,
            dry_run=True,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_project_pilot_runbook_create(args: argparse.Namespace) -> int:
    try:
        result = run_project_pilot_runbook_create(
            project_name=args.project,
            dry_run=args.dry_run,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_obsidian_project_sync(args: argparse.Namespace) -> int:
    dry_run = bool(args.dry_run)
    write = bool(args.write)
    if dry_run and write:
        print("ERRO: --dry-run e --write são mutuamente exclusivos.", file=sys.stderr)
        return 2
    if not dry_run and not write:
        dry_run = True

    try:
        result = run_obsidian_project_sync(
            project_name=args.project,
            dry_run=dry_run,
            write=write,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_factoryos_v1_readiness_gate(args: argparse.Namespace) -> int:
    from app.v1_readiness_gate import run_factoryos_v1_readiness_gate

    try:
        result = run_factoryos_v1_readiness_gate(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_factoryos_v1_audit(args: argparse.Namespace) -> int:
    from app.v1_audit import run_factoryos_v1_audit

    try:
        result = run_factoryos_v1_audit(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_factoryos_v1_security_review(args: argparse.Namespace) -> int:
    from app.v1_security_review import run_factoryos_v1_security_review

    try:
        result = run_factoryos_v1_security_review(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_factoryos_v1_reliability_check(args: argparse.Namespace) -> int:
    from app.v1_reliability import run_factoryos_v1_reliability_check

    try:
        result = run_factoryos_v1_reliability_check(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_factoryos_v1_polish_check(args: argparse.Namespace) -> int:
    from app.v1_polish import run_factoryos_v1_polish_check

    try:
        result = run_factoryos_v1_polish_check(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_factoryos_v1_readiness_closure(args: argparse.Namespace) -> int:
    from app.v1_closure import run_factoryos_v1_readiness_closure

    try:
        result = run_factoryos_v1_readiness_closure(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_factoryos_v1_technical_freeze(args: argparse.Namespace) -> int:
    from app.v1_technical_freeze import run_factoryos_v1_technical_freeze

    try:
        result = run_factoryos_v1_technical_freeze(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_release_packaging_strategy(args: argparse.Namespace) -> int:
    from app.release_packaging import run_release_packaging_strategy

    try:
        result = run_release_packaging_strategy(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_clean_public_export_plan(args: argparse.Namespace) -> int:
    from app.clean_export import run_clean_public_export_plan

    try:
        result = run_clean_public_export_plan(dry_run=args.dry_run, export_path=args.export_path)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_clean_public_export_create(args: argparse.Namespace) -> int:
    from app.clean_export import run_clean_public_export_create

    try:
        result = run_clean_public_export_create(dry_run=args.dry_run, export_path=args.export_path)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_clean_public_export_validate(args: argparse.Namespace) -> int:
    from app.clean_export import run_clean_public_export_validate

    try:
        result = run_clean_public_export_validate(dry_run=args.dry_run, export_path=args.export_path)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_public_repo_readiness_gate(args: argparse.Namespace) -> int:
    from app.public_repo_readiness import run_public_repo_readiness_gate

    try:
        result = run_public_repo_readiness_gate(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_public_export_leak_review(args: argparse.Namespace) -> int:
    from app.clean_export import run_public_export_leak_review

    try:
        result = run_public_export_leak_review(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_github_backup_plan(args: argparse.Namespace) -> int:
    try:
        result = run_github_backup_plan(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_github_publish_plan(args: argparse.Namespace) -> int:
    try:
        result = run_github_publish_plan(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_github_release_checklist(args: argparse.Namespace) -> int:
    try:
        result = run_github_release_checklist(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_bounded_live_canary_review(args: argparse.Namespace) -> int:
    if bool(args.run_id) == bool(args.report):
        print("ERRO: informe exatamente um de --run-id ou --report.", file=sys.stderr)
        return 2

    try:
        result = run_bounded_live_canary_review_gate(run_id=args.run_id, report=args.report)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_long_run_expansion_policy(args: argparse.Namespace) -> int:
    try:
        result = run_long_run_expansion_policy(
            run_id=args.run_id,
            target_minutes=args.target_minutes,
            max_steps=args.max_steps,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_expanded_long_run_rehearsal(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: expanded-long-run-rehearsal aceita somente --dry-run.", file=sys.stderr)
        return 2

    try:
        result = run_expanded_long_run_rehearsal(
            run_id=args.run_id,
            target_minutes=args.target_minutes,
            max_steps=args.max_steps,
            dry_run=True,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_expanded_long_run_review(args: argparse.Namespace) -> int:
    try:
        result = run_expanded_long_run_review_gate(run_id=args.run_id, report=args.report)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_factory_long_run_plan(args: argparse.Namespace) -> int:
    try:
        result = run_factory_long_run_plan(
            run_id=args.run_id,
            target_minutes=args.target_minutes,
            max_steps=args.max_steps,
            live=args.live,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_factory_long_run_rehearsal(args: argparse.Namespace) -> int:
    try:
        result = run_factory_long_run_rehearsal(
            run_id=args.run_id,
            target_minutes=args.target_minutes,
            max_steps=args.max_steps,
            dry_run=args.dry_run,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_report_retention_plan(args: argparse.Namespace) -> int:
    try:
        result = run_report_retention_cleanup_plan()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    return _print_task_result(result, args.out)


def cmd_report_retention_audit(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: report-retention-audit aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2
    try:
        result = run_report_retention_audit()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    return _print_task_result(result, args.out)


def cmd_report_retention_cleanup_plan(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: report-retention-cleanup-plan aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2
    try:
        result = run_report_retention_cleanup_plan()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    return _print_task_result(result, args.out)


def cmd_worktree_lifecycle_plan(args: argparse.Namespace) -> int:
    try:
        result = run_worktree_lifecycle_plan()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    return _print_task_result(result, args.out)


def cmd_factory_maintenance_plan(args: argparse.Namespace) -> int:
    try:
        result = run_factory_maintenance_plan()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    return _print_task_result(result, args.out)


def cmd_factory_live_canary(args: argparse.Namespace) -> int:
    if args.dry_run and args.live:
        print("ERRO: --dry-run e --live são mutuamente exclusivos.", file=sys.stderr)
        return 2

    if not args.dry_run and not args.live:
        print("ERRO: informe --dry-run ou --live.", file=sys.stderr)
        return 2

    try:
        result = run_live_canary(args.run_id, live=args.live)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_expanded_bounded_live_canary(args: argparse.Namespace) -> int:
    required_flags = {
        "--bounded": args.bounded,
        "--canary": args.canary,
        "--cost-aware": args.cost_aware,
        "--no-push": args.no_push,
        "--no-deploy": args.no_deploy,
        "--no-paid-api": args.no_paid_api,
        "--no-secrets": args.no_secrets,
    }
    missing = [flag for flag, enabled in required_flags.items() if not enabled]
    if missing:
        print(f"ERRO: flags obrigatórias ausentes: {' '.join(missing)}.", file=sys.stderr)
        return 2

    try:
        result = run_expanded_bounded_live_canary(
            args.run_id,
            max_steps=args.max_steps,
            target_minutes=args.max_minutes,
            bounded=args.bounded,
            canary=args.canary,
            cost_aware=args.cost_aware,
            no_push=args.no_push,
            no_deploy=args.no_deploy,
            no_paid_api=args.no_paid_api,
            no_secrets=args.no_secrets,
        )
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_post_expansion_evaluate(args: argparse.Namespace) -> int:
    try:
        result = evaluate_post_expansion_canary_report(report_path=args.report)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_post_expansion_rollback_plan(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print("ERRO: post-expansion-rollback-plan aceita somente --dry-run.", file=sys.stderr)
        return 2

    try:
        result = run_post_expansion_rollback_plan(report=args.report, dry_run=True)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_execution_evaluate(args: argparse.Namespace) -> int:
    try:
        if args.run_id is not None:
            result = evaluate_execution(run_id=args.run_id)
        else:
            result = evaluate_execution(report_path=args.report)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_execution_close_if_passed(args: argparse.Namespace) -> int:
    try:
        result = execution_close_if_passed(run_id=args.run_id, dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_deep_hygiene_audit(args: argparse.Namespace) -> int:
    try:
        from app.deep_hygiene_audit import run_deep_hygiene_audit

        result = run_deep_hygiene_audit(dry_run=args.dry_run, include_external=args.include_external)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_cleanup_plan(args: argparse.Namespace) -> int:
    try:
        from app.deep_hygiene_cleanup import run_cleanup_plan

        result = run_cleanup_plan(audit_report=args.audit_report, dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_cleanup_apply(args: argparse.Namespace) -> int:
    try:
        from app.deep_hygiene_cleanup import run_cleanup_apply

        result = run_cleanup_apply(cleanup_plan=args.cleanup_plan, dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_cleanup_validate(args: argparse.Namespace) -> int:
    try:
        from app.deep_hygiene_cleanup import run_cleanup_validate

        result = run_cleanup_validate(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_extended_cheap_run_plan(args: argparse.Namespace) -> int:
    try:
        from app.extended_cheap_run import run_extended_cheap_run_plan

        result = run_extended_cheap_run_plan(max_minutes=args.max_minutes, dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_extended_cheap_run_rehearsal(args: argparse.Namespace) -> int:
    try:
        from app.extended_cheap_run import run_extended_cheap_run_rehearsal

        result = run_extended_cheap_run_rehearsal(max_minutes=args.max_minutes, max_tasks=args.max_tasks, dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_extended_cheap_run_gate(args: argparse.Namespace) -> int:
    try:
        from app.extended_cheap_run import run_extended_cheap_run_gate

        result = run_extended_cheap_run_gate(dry_run=args.dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_panel_ux_audit(args: argparse.Namespace) -> int:
    from app.panel_ux_audit import run_panel_ux_audit

    if not args.dry_run:
        print("ERRO: panel-ux-audit aceita somente --dry-run nesta sprint.", file=sys.stderr)
        return 2

    try:
        result = run_panel_ux_audit(dry_run=True)
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_panel_usability_check(args: argparse.Namespace) -> int:
    from app.panel_usability import run_panel_usability_check

    if not args.dry_run:
        print("ERRO: panel-usability-check aceita somente --dry-run.", file=sys.stderr)
        return 2

    try:
        result = run_panel_usability_check(dry_run=True)
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_panel_project_flow_check(args: argparse.Namespace) -> int:
    from app.panel_project_flow import run_panel_project_flow_check

    if not args.dry_run:
        print("ERRO: panel-project-flow-check aceita somente --dry-run.", file=sys.stderr)
        return 2

    try:
        result = run_panel_project_flow_check(dry_run=True)
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_panel_final_visual_qa(args: argparse.Namespace) -> int:
    from app.panel_visual_qa import run_panel_final_visual_qa

    if not args.dry_run:
        print("ERRO: panel-final-visual-qa aceita somente --dry-run.", file=sys.stderr)
        return 2

    try:
        result = run_panel_final_visual_qa(dry_run=True)
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_compact_json(result, args.out)


def cmd_report_latest(args: argparse.Namespace) -> int:
    try:
        result = latest_report(args.kind, run_id=args.run_id)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    payload = {
        "ok": True,
        "kind": args.kind,
        "run_id": args.run_id,
        "report": None if result is None else {
            "kind": result.kind,
            "relative_path": result.relative_path,
            "view_path": result.view_path,
            "filename": result.filename,
            "timestamp": result.timestamp,
            "run_id": result.run_id,
        },
    }
    return _print_task_result(payload, args.out)


def cmd_report_list(args: argparse.Namespace) -> int:
    try:
        results = list_reports(args.kind, run_id=args.run_id, limit=args.limit)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    payload = {
        "ok": True,
        "kind": args.kind,
        "run_id": args.run_id,
        "reports": [
            {
                "kind": item.kind,
                "relative_path": item.relative_path,
                "view_path": item.view_path,
                "filename": item.filename,
                "timestamp": item.timestamp,
                "run_id": item.run_id,
            }
            for item in results
        ],
    }
    return _print_task_result(payload, args.out)


def cmd_factory_state_audit(args: argparse.Namespace) -> int:
    try:
        result = factory_state_audit()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_factory_state_plan(args: argparse.Namespace) -> int:
    try:
        result = factory_state_plan()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_factory_state_apply(args: argparse.Namespace) -> int:
    dry_run = not args.execute
    try:
        result = factory_state_apply(dry_run=dry_run)
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def cmd_factory_state_backfill_sprint_013(args: argparse.Namespace) -> int:
    try:
        result = factory_state_backfill_sprint_013()
    except TaskRunnerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    return _print_task_result(result, args.out)


def _task_transition_command(action: str, transition) -> callable:
    def _runner(args: argparse.Namespace) -> int:
        try:
            result = transition(args.task_id)
        except TaskRunnerError as exc:
            print(f"ERRO: {exc}", file=sys.stderr)
            return 2

        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    _runner.__name__ = f"cmd_{action}"
    return _runner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="factoryos",
        description="FactoryOS CLI local"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    route_parser = subparsers.add_parser(
        "route",
        help="Classifica uma tarefa e decide se precisa de Codex"
    )
    route_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a decisão em JSON"
    )
    route_parser.add_argument(
        "task",
        nargs="+",
        help="Texto da tarefa para classificar"
    )
    route_parser.set_defaults(func=cmd_route)

    discover_parser = subparsers.add_parser(
        "discover",
        help="Cria um arquivo de Reuse First Discovery para pesquisa pelo ChatGPT"
    )
    discover_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar o Markdown de discovery"
    )
    discover_parser.add_argument(
        "idea",
        nargs="+",
        help="Ideia que será avaliada na etapa Reuse First"
    )
    discover_parser.set_defaults(func=cmd_discover)

    help_docs_list_parser = subparsers.add_parser(
        "help-docs-list",
        help="Lista os documentos publicados no Help Center local"
    )
    help_docs_list_parser.set_defaults(func=cmd_help_docs_list)

    help_docs_check_parser = subparsers.add_parser(
        "help-docs-check",
        help="Valida README, docs, slugs, Mermaid e rotas de Ajuda"
    )
    help_docs_check_parser.add_argument("--dry-run", action="store_true", required=True)
    help_docs_check_parser.set_defaults(func=cmd_help_docs_check)

    output_budget_contract_parser = subparsers.add_parser(
        "output-budget-contract",
        help="Imprime o contrato compacto de output e stdout"
    )
    output_budget_contract_parser.set_defaults(func=cmd_output_budget_contract)

    no_diff_prompt_contract_parser = subparsers.add_parser(
        "no-diff-prompt-contract",
        help="Imprime o contrato padrão para evitar narrativa de diff/patch"
    )
    no_diff_prompt_contract_parser.set_defaults(func=cmd_no_diff_prompt_contract)

    no_diff_prompt_check_parser = subparsers.add_parser(
        "no-diff-prompt-check",
        help="Verifica se um prompt contém o contrato no-diff"
    )
    no_diff_prompt_check_parser.add_argument(
        "--prompt-file",
        required=True,
        help="Caminho do prompt a ser analisado",
    )
    no_diff_prompt_check_parser.set_defaults(func=cmd_no_diff_prompt_check)

    token_usage_parse_parser = subparsers.add_parser(
        "token-usage-parse",
        help="Lê um log e extrai métricas de token usage"
    )
    token_usage_parse_parser.add_argument(
        "--log",
        required=True,
        help="Caminho do log a ser analisado"
    )
    token_usage_parse_parser.set_defaults(func=cmd_token_usage_parse)

    output_budget_check_parser = subparsers.add_parser(
        "output-budget-check",
        help="Verifica linhas e bytes de um log contra um budget local"
    )
    output_budget_check_parser.add_argument(
        "--log",
        required=True,
        help="Caminho do log a ser analisado"
    )
    output_budget_check_parser.add_argument(
        "--max-lines",
        type=int,
        required=True,
        help="Limite máximo de linhas"
    )
    output_budget_check_parser.add_argument(
        "--max-bytes",
        type=int,
        required=True,
        help="Limite máximo de bytes"
    )
    output_budget_check_parser.set_defaults(func=cmd_output_budget_check)

    codex_output_budget_report_parser = subparsers.add_parser(
        "codex-output-budget-report",
        help="Gera um report local de budget de saída do Codex"
    )
    codex_output_budget_report_parser.add_argument(
        "--log",
        required=True,
        help="Caminho do log a ser analisado"
    )
    codex_output_budget_report_parser.set_defaults(func=cmd_codex_output_budget_report)

    codex_quiet_run_parser = subparsers.add_parser(
        "codex-quiet-run",
        help="Executa Codex em modo silencioso capturando stdout/stderr em arquivo"
    )
    codex_quiet_run_parser.add_argument("--prompt-file", required=True, help="Arquivo de prompt")
    codex_quiet_run_parser.add_argument("--cwd", required=True, help="Diretório de execução")
    codex_quiet_run_parser.add_argument("--model", required=True, help="Modelo do Codex")
    codex_quiet_run_parser.add_argument("--reasoning", required=True, help="Reasoning effort")
    codex_quiet_run_parser.add_argument("--sandbox", required=True, help="Sandbox mode")
    codex_quiet_run_parser.add_argument("--approval", required=True, help="Approval policy")
    codex_quiet_run_parser.add_argument("--label", required=True, help="Label curta para o report")
    codex_quiet_run_parser.add_argument(
        "--allowed-path",
        action="append",
        default=[],
        help="Caminho permitido para mudanças; pode ser informado várias vezes",
    )
    codex_quiet_run_parser.add_argument(
        "--no-push",
        action="store_true",
        default=None,
        help="Marca explicitamente que o prompt não deve fazer push",
    )
    codex_quiet_run_parser.add_argument(
        "--no-deploy",
        action="store_true",
        default=None,
        help="Marca explicitamente que o prompt não deve fazer deploy",
    )
    codex_quiet_run_parser.add_argument(
        "--no-paid-api",
        action="store_true",
        default=None,
        help="Marca explicitamente que o prompt não deve usar API paga",
    )
    codex_quiet_run_parser.add_argument(
        "--no-secrets",
        action="store_true",
        default=None,
        help="Marca explicitamente que o prompt não deve tocar em segredos",
    )
    codex_quiet_run_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=600,
        help="Timeout máximo para a execução quiet do Codex",
    )
    codex_quiet_run_mode = codex_quiet_run_parser.add_mutually_exclusive_group()
    codex_quiet_run_mode.add_argument("--dry-run", action="store_true", help="Monta o comando sem executar")
    codex_quiet_run_mode.add_argument("--execute", action="store_true", help="Executa o comando silencioso")
    codex_quiet_run_parser.set_defaults(func=cmd_codex_quiet_run)

    codex_quiet_ab_report_parser = subparsers.add_parser(
        "codex-quiet-ab-report",
        help="Compara dois logs silenciosos e calcula a economia"
    )
    codex_quiet_ab_report_parser.add_argument("--log-a", required=True, help="Log de referência")
    codex_quiet_ab_report_parser.add_argument("--log-b", required=True, help="Log comparado")
    codex_quiet_ab_report_parser.set_defaults(func=cmd_codex_quiet_ab_report)

    codex_run_result_check_parser = subparsers.add_parser(
        "codex-run-result-check",
        help="Valida um report JSON do quiet runner e imprime um resumo compacto",
    )
    codex_run_result_check_parser.add_argument(
        "--json",
        required=True,
        help="Caminho do report JSON a validar",
    )
    codex_run_result_check_parser.set_defaults(func=cmd_codex_run_result_check)

    compact_exec_budget_parser = subparsers.add_parser(
        "compact-exec-budget",
        help="Mostra budgets compactos por categoria"
    )
    compact_exec_budget_parser.set_defaults(func=cmd_compact_exec_budget)

    compact_exec_check_parser = subparsers.add_parser(
        "compact-exec-check",
        help="Verifica se um log cabe no budget compacto"
    )
    compact_exec_check_parser.add_argument("--log", required=True, help="Log a ser analisado")
    compact_exec_check_parser.add_argument(
        "--category",
        required=True,
        choices=sorted(COMPACT_EXECUTION_BUDGETS),
        help="Categoria do budget compacto",
    )
    compact_exec_check_parser.add_argument(
        "--mode",
        choices=["terminal", "captured"],
        default="terminal",
        help="Modo de análise do log",
    )
    compact_exec_check_parser.set_defaults(func=cmd_compact_exec_check)

    compact_exec_report_parser = subparsers.add_parser(
        "compact-exec-report",
        help="Gera report consolidado de execução compacta"
    )
    compact_exec_report_parser.add_argument("--log", required=True, help="Log a ser analisado")
    compact_exec_report_parser.add_argument(
        "--category",
        required=True,
        choices=sorted(COMPACT_EXECUTION_BUDGETS),
        help="Categoria do budget compacto",
    )
    compact_exec_report_parser.add_argument(
        "--mode",
        choices=["terminal", "captured"],
        default="terminal",
        help="Modo de análise do log",
    )
    compact_exec_report_parser.set_defaults(func=cmd_compact_exec_report)

    memory_digest_create_parser = subparsers.add_parser(
        "memory-digest-create",
        help="Cria um digest curto de memória a partir de um report fonte"
    )
    memory_digest_create_parser.add_argument(
        "--title",
        required=True,
        help="Título do digest"
    )
    memory_digest_create_parser.add_argument(
        "--source-report",
        required=True,
        help="Caminho do report fonte"
    )
    memory_digest_create_parser.add_argument(
        "--sprint",
        required=True,
        help="Número da sprint"
    )
    memory_digest_create_parser.set_defaults(func=cmd_memory_digest_create)

    memory_digest_latest_parser = subparsers.add_parser(
        "memory-digest-latest",
        help="Mostra o digest de memória mais recente"
    )
    memory_digest_latest_parser.set_defaults(func=cmd_memory_digest_latest)

    memory_digest_list_parser = subparsers.add_parser(
        "memory-digest-list",
        help="Lista digests de memória de forma compacta"
    )
    memory_digest_list_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Número máximo de digests retornados"
    )
    memory_digest_list_parser.set_defaults(func=cmd_memory_digest_list)

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Classifica sinais de validação local e retorna uma decisão padronizada"
    )
    evaluate_parser.add_argument(
        "--python-ok",
        default="true",
        choices=["true", "false"],
        help="Se a validação Python passou"
    )
    evaluate_parser.add_argument(
        "--json-ok",
        default="true",
        choices=["true", "false"],
        help="Se a validação JSON passou"
    )
    evaluate_parser.add_argument(
        "--browser-ok",
        default="true",
        choices=["true", "false"],
        help="Se a validação visual/browser passou"
    )
    evaluate_parser.add_argument(
        "--security-ok",
        default="true",
        choices=["true", "false"],
        help="Se a validação de segurança passou"
    )
    evaluate_parser.add_argument(
        "--high-risk",
        default="false",
        choices=["true", "false"],
        help="Se a tarefa ou resultado é de alto risco"
    )
    evaluate_parser.add_argument(
        "--git-clean",
        default="true",
        choices=["true", "false"],
        help="Se o Git está limpo"
    )
    evaluate_parser.add_argument(
        "--git-expected-dirty",
        default="false",
        choices=["true", "false"],
        help="Se a sujeira no Git é esperada"
    )
    evaluate_parser.add_argument(
        "--notes",
        default="",
        help="Notas opcionais sobre a avaliação"
    )
    evaluate_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a avaliação em JSON"
    )
    evaluate_parser.set_defaults(func=cmd_evaluate)

    task_create_parser = subparsers.add_parser(
        "task-create",
        help="Cria uma task local em tasks/pending"
    )
    task_create_parser.add_argument(
        "title",
        help="Título legível da task"
    )
    task_create_parser.add_argument(
        "--description",
        required=True,
        help="Descrição da task"
    )
    task_create_parser.add_argument(
        "--risk",
        default="medium",
        choices=["low", "medium", "high"],
        help="Nível de risco"
    )
    task_create_parser.add_argument(
        "--executor",
        default="manual",
        choices=["manual", "local", "codex"],
        help="Executor previsto"
    )
    task_create_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    _add_routing_contract_arguments(task_create_parser)
    task_create_parser.set_defaults(func=cmd_task_create)

    task_list_parser = subparsers.add_parser(
        "task-list",
        help="Lista tasks locais agrupadas por status"
    )
    task_list_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    task_list_parser.set_defaults(func=cmd_task_list)

    task_show_parser = subparsers.add_parser(
        "task-show",
        help="Mostra uma task local em qualquer status"
    )
    task_show_parser.add_argument("task_id", help="Id da task")
    task_show_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    task_show_parser.set_defaults(func=cmd_task_show)

    task_evaluate_parser = subparsers.add_parser(
        "task-evaluate",
        help="Avalia uma task local e gera um report JSON fixo"
    )
    task_evaluate_parser.add_argument("task_id", help="Id da task")
    task_evaluate_parser.set_defaults(func=cmd_task_evaluate)

    task_note_parser = subparsers.add_parser(
        "task-note",
        help="Adiciona uma nota a uma task local sem alterar o status"
    )
    task_note_parser.add_argument("task_id", help="Id da task")
    task_note_parser.add_argument(
        "note",
        nargs="+",
        help="Texto da nota"
    )
    task_note_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    task_note_parser.set_defaults(func=cmd_task_note)

    task_start_parser = subparsers.add_parser(
        "task-start",
        help="Move uma task de pending para running"
    )
    task_start_parser.add_argument("task_id", help="Id da task")
    task_start_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    task_start_parser.set_defaults(func=_task_transition_command("task_start", start_task))

    task_finish_parser = subparsers.add_parser(
        "task-finish",
        help="Move uma task de running para done"
    )
    task_finish_parser.add_argument("task_id", help="Id da task")
    task_finish_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    task_finish_parser.set_defaults(func=_task_transition_command("task_finish", finish_task))

    task_fail_parser = subparsers.add_parser(
        "task-fail",
        help="Move uma task de pending ou running para failed"
    )
    task_fail_parser.add_argument("task_id", help="Id da task")
    task_fail_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    task_fail_parser.set_defaults(func=_task_transition_command("task_fail", fail_task))

    factory_state_audit_parser = subparsers.add_parser(
        "factory-state-audit",
        help="Audita tasks e runs running antigas e gera um report de higiene"
    )
    factory_state_audit_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_state_audit_parser.set_defaults(func=cmd_factory_state_audit)

    factory_state_plan_parser = subparsers.add_parser(
        "factory-state-plan",
        help="Gera um plano conservador de fechamento para tasks e runs antigas"
    )
    factory_state_plan_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_state_plan_parser.set_defaults(func=cmd_factory_state_plan)

    factory_state_apply_parser = subparsers.add_parser(
        "factory-state-apply",
        help="Aplica ou simula o plano de higiene de state"
    )
    factory_state_mode = factory_state_apply_parser.add_mutually_exclusive_group()
    factory_state_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa o plano sem mutar nada"
    )
    factory_state_mode.add_argument(
        "--execute",
        action="store_true",
        help="Fecha apenas itens safe_to_close"
    )
    factory_state_apply_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_state_apply_parser.set_defaults(func=cmd_factory_state_apply)

    factory_state_backfill_parser = subparsers.add_parser(
        "factory-state-backfill-sprint-013",
        help="Audita e fecha a Sprint 013 apenas se a prova local for suficiente"
    )
    factory_state_backfill_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_state_backfill_parser.set_defaults(func=cmd_factory_state_backfill_sprint_013)

    run_create_parser = subparsers.add_parser(
        "run-create",
        help="Cria uma run local isolada para uma task existente"
    )
    run_create_parser.add_argument("task_id", help="Id da task base")
    run_create_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    _add_routing_contract_arguments(run_create_parser)
    run_create_parser.set_defaults(func=cmd_run_create)

    routing_contract_validate_parser = subparsers.add_parser(
        "routing-contract-validate",
        help="Valida routing contract explícito de uma task ou run com fallback heurístico"
    )
    routing_contract_validate_parser.add_argument("--task-id", help="Id da task")
    routing_contract_validate_parser.add_argument("--run-id", help="Id da run")
    routing_contract_validate_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    routing_contract_validate_parser.set_defaults(func=cmd_routing_contract_validate)

    run_list_parser = subparsers.add_parser(
        "run-list",
        help="Lista runs locais agrupadas por status"
    )
    run_list_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_list_parser.set_defaults(func=cmd_run_list)

    run_show_parser = subparsers.add_parser(
        "run-show",
        help="Mostra uma run local em qualquer status"
    )
    run_show_parser.add_argument("run_id", help="Id da run")
    run_show_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_show_parser.set_defaults(func=cmd_run_show)

    run_finish_parser = subparsers.add_parser(
        "run-finish",
        help="Move uma run de running para done"
    )
    run_finish_parser.add_argument("run_id", help="Id da run")
    run_finish_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_finish_parser.set_defaults(func=cmd_run_finish)

    run_fail_parser = subparsers.add_parser(
        "run-fail",
        help="Move uma run de running para failed"
    )
    run_fail_parser.add_argument("run_id", help="Id da run")
    run_fail_parser.add_argument(
        "--reason",
        required=True,
        help="Motivo do encerramento em falha"
    )
    run_fail_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_fail_parser.set_defaults(func=cmd_run_fail)

    run_workspace_prepare_parser = subparsers.add_parser(
        "run-workspace-prepare",
        help="Cria ou reaproveita um git worktree isolado para a run"
    )
    run_workspace_prepare_parser.add_argument("run_id", help="Id da run")
    run_workspace_prepare_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_workspace_prepare_parser.set_defaults(func=cmd_run_workspace_prepare)

    run_workspace_status_parser = subparsers.add_parser(
        "run-workspace-status",
        help="Mostra o estado do workspace isolado da run"
    )
    run_workspace_status_parser.add_argument("run_id", help="Id da run")
    run_workspace_status_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_workspace_status_parser.set_defaults(func=cmd_run_workspace_status)

    run_workspace_readiness_parser = subparsers.add_parser(
        "run-workspace-readiness",
        help="Avalia se o workspace isolado da run está pronto para live futura"
    )
    run_workspace_readiness_parser.add_argument("run_id", help="Id da run")
    run_workspace_readiness_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_workspace_readiness_parser.set_defaults(func=cmd_run_workspace_readiness)

    run_workspace_sync_plan_parser = subparsers.add_parser(
        "run-workspace-sync-plan",
        help="Gera um plano local seguro de sincronização fast-forward para a run"
    )
    run_workspace_sync_plan_parser.add_argument("run_id", help="Id da run")
    run_workspace_sync_plan_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_workspace_sync_plan_parser.set_defaults(func=cmd_run_workspace_sync_plan)

    run_workspace_sync_apply_parser = subparsers.add_parser(
        "run-workspace-sync-apply",
        help="Aplica fast-forward seguro no worktree da run quando o plano permitir"
    )
    run_workspace_sync_apply_parser.add_argument("run_id", help="Id da run")
    run_workspace_sync_apply_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_workspace_sync_apply_parser.set_defaults(func=cmd_run_workspace_sync_apply)

    run_handoff_parser = subparsers.add_parser(
        "run-handoff",
        help="Gera prompt e report local de handoff sem executar Codex"
    )
    run_handoff_parser.add_argument("run_id", help="Id da run")
    run_handoff_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_handoff_parser.set_defaults(func=cmd_run_handoff)

    run_execute_parser = subparsers.add_parser(
        "run-execute",
        help="Prepara o handoff e faz dry-run por padrão; live exige variável de ambiente"
    )
    run_execute_parser.add_argument("run_id", help="Id da run")
    run_execute_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Força a simulação segura padrão"
    )
    run_execute_parser.add_argument(
        "--live",
        action="store_true",
        help="Executa o Codex apenas se FACTORYOS_ENABLE_LIVE_CODEX=1 estiver definido"
    )
    run_execute_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    run_execute_parser.set_defaults(func=cmd_run_execute)

    codex_profile_list_parser = subparsers.add_parser(
        "codex-profile-list",
        help="Lista perfis Codex locais e seus budgets sem alterar config global"
    )
    codex_profile_list_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_profile_list_parser.set_defaults(func=cmd_codex_profile_list)

    codex_plan_parser = subparsers.add_parser(
        "codex-plan",
        help="Gera plano local de perfil/budget Codex para task ou run"
    )
    target = codex_plan_parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--task-id", help="Id da task")
    target.add_argument("--run-id", help="Id da run")
    codex_plan_parser.add_argument(
        "--live",
        action="store_true",
        help="Avalia o gate como execução live futura, sem executar Codex"
    )
    codex_plan_parser.add_argument(
        "--max-steps",
        type=int,
        default=1,
        help="Quantidade planejada de steps para classificação de risco"
    )
    codex_plan_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_plan_parser.set_defaults(func=cmd_codex_plan)

    codex_context_parser = subparsers.add_parser(
        "codex-context",
        help="Gera context pack compacto para task ou run sem executar Codex"
    )
    context_target = codex_context_parser.add_mutually_exclusive_group(required=True)
    context_target.add_argument("--task-id", help="Id da task")
    context_target.add_argument("--run-id", help="Id da run")
    codex_context_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_context_parser.set_defaults(func=cmd_codex_context)

    codex_capsule_create_parser = subparsers.add_parser(
        "codex-capsule-create",
        help="Cria uma cápsula Git mínima com arquivos incluídos e manifest"
    )
    codex_capsule_create_parser.add_argument("--label", required=True, help="Rótulo curto da cápsula")
    codex_capsule_create_parser.add_argument("--source-root", required=True, help="Root do source para copiar")
    codex_capsule_create_parser.add_argument(
        "--include",
        action="append",
        default=[],
        required=True,
        help="Arquivo a incluir na cápsula; pode repetir",
    )
    codex_capsule_create_parser.add_argument(
        "--use-latest-digest",
        action="store_true",
        help="Copia o digest de memória mais recente se existir",
    )
    codex_capsule_create_parser.add_argument(
        "--max-context-bytes",
        type=int,
        required=True,
        help="Teto total de bytes permitido para a cápsula",
    )
    codex_capsule_create_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_capsule_create_parser.set_defaults(func=cmd_codex_capsule_create)

    codex_capsule_list_parser = subparsers.add_parser(
        "codex-capsule-list",
        help="Lista cápsulas recentes em formato compacto"
    )
    codex_capsule_list_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Quantidade máxima de cápsulas listadas",
    )
    codex_capsule_list_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_capsule_list_parser.set_defaults(func=cmd_codex_capsule_list)

    codex_capsule_inspect_parser = subparsers.add_parser(
        "codex-capsule-inspect",
        help="Inspeciona uma cápsula e devolve métricas compactas"
    )
    codex_capsule_inspect_parser.add_argument("--capsule", required=True, help="Caminho da cápsula")
    codex_capsule_inspect_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_capsule_inspect_parser.set_defaults(func=cmd_codex_capsule_inspect)

    codex_capsule_run_parser = subparsers.add_parser(
        "codex-capsule-run",
        help="Executa Codex dentro da cápsula usando quiet runner"
    )
    codex_capsule_run_parser.add_argument("--capsule", required=True, help="Caminho da cápsula")
    codex_capsule_run_parser.add_argument("--prompt-file", required=True, help="Prompt markdown para execução")
    codex_capsule_run_parser.add_argument("--label", required=True, help="Rótulo da execução")
    codex_capsule_run_parser.add_argument("--model", required=True, help="Modelo Codex")
    codex_capsule_run_parser.add_argument("--reasoning", required=True, help="Reasoning effort")
    codex_capsule_run_parser.add_argument(
        "--sandbox",
        required=True,
        choices=["read-only", "workspace-write", "danger-full-access"],
        help="Modo de sandbox",
    )
    codex_capsule_run_parser.add_argument(
        "--execute",
        action="store_true",
        help="Executa de fato o Codex dentro da cápsula",
    )
    codex_capsule_run_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_capsule_run_parser.set_defaults(func=cmd_codex_capsule_run)

    codex_capsule_diff_parser = subparsers.add_parser(
        "codex-capsule-diff",
        help="Salva diff da cápsula e devolve apenas contadores"
    )
    codex_capsule_diff_parser.add_argument("--capsule", required=True, help="Caminho da cápsula")
    codex_capsule_diff_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_capsule_diff_parser.set_defaults(func=cmd_codex_capsule_diff)

    codex_capsule_export_plan_parser = subparsers.add_parser(
        "codex-capsule-export-plan",
        help="Compara cápsula com source-root e gera plano de exportação"
    )
    codex_capsule_export_plan_parser.add_argument("--capsule", required=True, help="Caminho da cápsula")
    codex_capsule_export_plan_parser.add_argument("--source-root", required=True, help="Root original do source")
    codex_capsule_export_plan_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_capsule_export_plan_parser.set_defaults(func=cmd_codex_capsule_export_plan)

    codex_capsule_apply_parser = subparsers.add_parser(
        "codex-capsule-apply",
        help="Faz apenas dry-run do gate de aplicação da cápsula"
    )
    codex_capsule_apply_parser.add_argument("--capsule", required=True, help="Caminho da cápsula")
    codex_capsule_apply_parser.add_argument("--source-root", required=True, help="Root original do source")
    codex_capsule_apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Obrigatório nesta sprint; não aplica mudanças reais",
    )
    codex_capsule_apply_parser.add_argument(
        "--export-plan",
        help="Plano de exportação já gerado; quando omitido, o comando cria um plano novo",
    )
    codex_capsule_apply_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_capsule_apply_parser.set_defaults(func=cmd_codex_capsule_apply)

    capsule_cost_diagnose_parser = subparsers.add_parser(
        "capsule-cost-diagnose",
        help="Diagnostica a causa raiz de custo alto em uma execução E2E de cápsula",
    )
    capsule_cost_diagnose_parser.add_argument(
        "--e2e-report",
        required=True,
        help="Report E2E base a diagnosticar",
    )
    capsule_cost_diagnose_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON",
    )
    capsule_cost_diagnose_parser.set_defaults(func=cmd_capsule_cost_diagnose)

    capsule_run_status_parser = subparsers.add_parser(
        "capsule-run-status",
        help="Normaliza a decisão final de uma execução de cápsula"
    )
    capsule_run_status_parser.add_argument("--execution-report", required=True, help="Report bruto da execução da cápsula")
    capsule_run_status_parser.add_argument("--export-plan", required=True, help="Report do export-plan da cápsula")
    capsule_run_status_parser.add_argument("--diff-report", required=True, help="Report do diff da cápsula")
    capsule_run_status_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    capsule_run_status_parser.set_defaults(func=cmd_codex_capsule_status)

    cheap_task_factory_e2e_parser = subparsers.add_parser(
        "cheap-task-factory-e2e",
        help="Executa o gate ponta a ponta de task barata via cápsula"
    )
    cheap_task_factory_e2e_parser.add_argument(
        "--category",
        required=True,
        choices=["docs_only", "code_small"],
        help="Categoria barata a validar",
    )
    cheap_task_factory_e2e_parser.add_argument("--label", required=True, help="Rótulo curto do canário")
    cheap_task_factory_e2e_parser.add_argument(
        "--capsule-mode",
        default="standard",
        choices=["standard", "ultra_slim", "ultra_slim_min"],
        help="Modo de montagem da cápsula",
    )
    cheap_task_factory_e2e_parser.add_argument(
        "--max-prompt-bytes",
        type=int,
        help="Teto opcional para prompt efetivo",
    )
    cheap_task_factory_e2e_parser.add_argument(
        "--max-capsule-bytes",
        type=int,
        help="Teto opcional para bytes totais da cápsula",
    )
    cheap_task_factory_e2e_mode = cheap_task_factory_e2e_parser.add_mutually_exclusive_group(required=True)
    cheap_task_factory_e2e_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Gera somente o plano sem executar a cápsula",
    )
    cheap_task_factory_e2e_mode.add_argument(
        "--execute-canary",
        action="store_true",
        help="Executa o canário pequeno dentro da cápsula",
    )
    cheap_task_factory_e2e_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    cheap_task_factory_e2e_parser.set_defaults(func=cmd_cheap_task_factory_e2e)


    capsule_execution_policy_parser = subparsers.add_parser(
        "capsule-execution-policy",
        help="Decide o executor econômico para tarefas simples, médias ou de revisão pesada"
    )
    capsule_execution_policy_target = capsule_execution_policy_parser.add_mutually_exclusive_group(required=False)
    capsule_execution_policy_target.add_argument("--task-id", help="Id da task a avaliar")
    capsule_execution_policy_target.add_argument("--run-id", help="Id da run a avaliar")
    capsule_execution_policy_target.add_argument(
        "--category",
        choices=[
            "docs_only",
            "code_small",
            "code_medium",
            "factory_start",
            "live_canary",
            "security_review",
            "heavy_review_only",
        ],
        help="Categoria explícita para decisão da policy",
    )
    capsule_execution_policy_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    capsule_execution_policy_parser.set_defaults(func=cmd_capsule_execution_policy)

    codex_cost_audit_parser = subparsers.add_parser(
        "codex-cost-audit",
        help="Mede custo do Codex no caminho global e no caminho FactoryOS forçado leve"
    )
    codex_cost_audit_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=240,
        help="Timeout por teste curto do Codex"
    )
    codex_cost_audit_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    codex_cost_audit_parser.set_defaults(func=cmd_codex_cost_audit)

    factory_tick_parser = subparsers.add_parser(
        "factory-tick",
        help="Executa um tick unico e auditavel com dry-run primeiro"
    )
    factory_tick_parser.add_argument(
        "--run-id",
        required=True,
        help="Id da run"
    )
    factory_tick_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa o tick em modo dry-run seguro"
    )
    factory_tick_parser.add_argument(
        "--live",
        action="store_true",
        help="Bloqueado nesta sprint"
    )
    factory_tick_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_tick_parser.set_defaults(func=cmd_factory_tick)

    factory_live_canary_parser = subparsers.add_parser(
        "factory-live-canary",
        help="Prepara e executa o canário live único da Sprint 016"
    )
    factory_live_canary_parser.add_argument(
        "--run-id",
        required=True,
        help="Id da run canary"
    )
    live_mode = factory_live_canary_parser.add_mutually_exclusive_group(required=True)
    live_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepara o canário sem executar o Codex live"
    )
    live_mode.add_argument(
        "--live",
        action="store_true",
        help="Executa o Codex live uma única vez"
    )
    factory_live_canary_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_live_canary_parser.set_defaults(func=cmd_factory_live_canary)

    controlled_loop_parser = subparsers.add_parser(
        "factory-loop",
        help="Executa um loop controlado local e síncrono em dry-run"
    )
    controlled_loop_parser.add_argument(
        "--run-id",
        help="Id da run; quando omitido, seleciona automaticamente uma run running"
    )
    controlled_loop_parser.add_argument(
        "--max-steps",
        type=int,
        default=1,
        help="Limite pequeno de passos para o loop"
    )
    controlled_loop_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa o loop em modo seco"
    )
    controlled_loop_parser.add_argument(
        "--live",
        action="store_true",
        help="Bloqueado nesta sprint"
    )
    controlled_loop_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    controlled_loop_parser.set_defaults(func=cmd_factory_loop)

    factory_start_parser = subparsers.add_parser(
        "factory-start",
        help="Executa um factory-start explícito e limitado"
    )
    factory_start_parser.add_argument(
        "--run-id",
        help="Id explícito da run"
    )
    factory_start_parser.add_argument(
        "--max-steps",
        type=int,
        default=1,
        help="Limite pequeno de passos para o factory-start"
    )
    factory_start_parser.add_argument(
        "--target-minutes",
        type=int,
        default=30,
        help="Duração alvo usada pelo modo cost-aware/plan-only"
    )
    factory_start_parser.add_argument(
        "--canary",
        action="store_true",
        help="Exige o modo canário bounded para live"
    )
    factory_start_parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Gera execution evaluation após o factory-start"
    )
    factory_start_parser.add_argument(
        "--cost-aware",
        action="store_true",
        help="Ativa a camada cost-aware do FactoryOS"
    )
    factory_start_mode = factory_start_parser.add_mutually_exclusive_group(required=False)
    factory_start_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa o factory-start em dry-run"
    )
    factory_start_mode.add_argument(
        "--live",
        action="store_true",
        help="Bloqueado nesta sprint"
    )
    factory_start_mode.add_argument(
        "--plan-only",
        action="store_true",
        help="Gera somente o plano cost-aware sem executar o dry-run"
    )
    factory_start_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_start_parser.set_defaults(func=cmd_factory_start)

    factory_queue_start_parser = subparsers.add_parser(
        "factory-queue-start",
        help="Planeja uma fila curta de tasks com routing cost-aware"
    )
    factory_queue_start_mode = factory_queue_start_parser.add_mutually_exclusive_group(required=False)
    factory_queue_start_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa o planejamento da fila em modo seco"
    )
    factory_queue_start_mode.add_argument(
        "--plan-only",
        action="store_true",
        help="Gera apenas o plano da fila sem simular execução"
    )
    factory_queue_start_parser.add_argument(
        "--max-tasks",
        type=int,
        default=3,
        help="Quantidade máxima de tasks na fila"
    )
    factory_queue_start_parser.add_argument(
        "--max-steps-per-task",
        type=int,
        default=1,
        help="Limite de steps planejados por task"
    )
    factory_queue_start_parser.add_argument(
        "--cost-aware",
        action="store_true",
        help="Ativa o planejamento cost-aware da fila"
    )
    factory_queue_start_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_queue_start_parser.set_defaults(func=cmd_factory_queue_start)

    project_intake_create_parser = subparsers.add_parser(
        "project-intake-create",
        help="Cria o intake minimo de um projeto MVP a partir de PRD/SPEC/sprints"
    )
    project_intake_create_parser.add_argument(
        "--name",
        required=True,
        help="Nome do projeto"
    )
    project_intake_create_parser.add_argument(
        "--kind",
        required=True,
        help="Tipo do projeto"
    )
    project_intake_create_parser.add_argument(
        "--from-template",
        dest="from_template",
        default="simple-web-mvp",
        help="Template de intake a utilizar"
    )
    project_intake_create_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Obrigatorio nesta sprint; cria apenas plano local"
    )
    project_intake_create_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    project_intake_create_parser.set_defaults(func=cmd_project_intake_create)

    reversa_global_check_parser = subparsers.add_parser(
        "reversa-global-check",
        help="Verifica Node, npm e Reversa sem instalar nada",
    )
    reversa_global_check_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    reversa_global_check_parser.set_defaults(func=cmd_reversa_global_check)

    reversa_project_plan_parser = subparsers.add_parser(
        "reversa-project-plan",
        help="Planeja instalação Reversa em projeto alvo sem executar install",
    )
    reversa_project_plan_parser.add_argument("--target", required=True, help="Projeto alvo dentro de <CODE_ROOT>")
    reversa_project_plan_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    reversa_project_plan_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    reversa_project_plan_parser.set_defaults(func=cmd_reversa_project_plan)

    reversa_project_install_parser = subparsers.add_parser(
        "reversa-project-install",
        help="Ensaia instalação Reversa; live install bloqueado no V0",
    )
    reversa_project_install_parser.add_argument("--target", required=True, help="Projeto alvo dentro de <CODE_ROOT>")
    reversa_project_install_parser.add_argument("--dry-run", action="store_true", help="Executa somente plano seguro")
    reversa_project_install_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    reversa_project_install_parser.set_defaults(func=cmd_reversa_project_install)

    reversa_project_status_parser = subparsers.add_parser(
        "reversa-project-status",
        help="Lê estado Reversa do projeto alvo sem stack trace em ausência de arquivos",
    )
    reversa_project_status_parser.add_argument("--target", required=True, help="Projeto alvo dentro de <CODE_ROOT>")
    reversa_project_status_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    reversa_project_status_parser.set_defaults(func=cmd_reversa_project_status)

    reversa_project_sdd_intake_parser = subparsers.add_parser(
        "reversa-project-sdd-intake",
        help="Classifica artefatos de _reversa_sdd/ sem copiar nada",
    )
    reversa_project_sdd_intake_parser.add_argument("--target", required=True, help="Projeto alvo dentro de <CODE_ROOT>")
    reversa_project_sdd_intake_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    reversa_project_sdd_intake_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    reversa_project_sdd_intake_parser.set_defaults(func=cmd_reversa_project_sdd_intake)

    artifact_intake_plan_parser = subparsers.add_parser(
        "artifact-intake-plan",
        help="Planeja a entrada controlada de artefatos e assets",
    )
    artifact_intake_plan_parser.add_argument("--project", required=True, help="Nome do projeto")
    artifact_intake_plan_parser.add_argument("--source", required=True, help="Caminho da fonte")
    artifact_intake_plan_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    artifact_intake_plan_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    artifact_intake_plan_parser.set_defaults(func=cmd_artifact_intake_plan)

    artifact_intake_register_parser = subparsers.add_parser(
        "artifact-intake-register",
        help="Registra o plano de artefatos e assets em dry-run",
    )
    artifact_intake_register_parser.add_argument("--project", required=True, help="Nome do projeto")
    artifact_intake_register_parser.add_argument("--source", required=True, help="Caminho da fonte")
    artifact_intake_register_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    artifact_intake_register_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    artifact_intake_register_parser.set_defaults(func=cmd_artifact_intake_register)

    mvp_template_list_parser = subparsers.add_parser(
        "mvp-template-list",
        help="Lista os templates MVP reutilizáveis V0",
    )
    mvp_template_list_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    mvp_template_list_parser.set_defaults(func=cmd_mvp_template_list)

    mvp_template_show_parser = subparsers.add_parser(
        "mvp-template-show",
        help="Exibe um template MVP específico",
    )
    mvp_template_show_parser.add_argument("--template", required=True, help="Nome do template")
    mvp_template_show_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    mvp_template_show_parser.set_defaults(func=cmd_mvp_template_show)

    mvp_template_validate_parser = subparsers.add_parser(
        "mvp-template-validate",
        help="Valida a estrutura de um template MVP",
    )
    mvp_template_validate_parser.add_argument("--template", required=True, help="Nome do template")
    mvp_template_validate_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    mvp_template_validate_parser.set_defaults(func=cmd_mvp_template_validate)

    mvp_build_plan_create_parser = subparsers.add_parser(
        "mvp-build-plan-create",
        help="Cria um plano dry-run de build a partir de um intake",
    )
    mvp_build_plan_create_parser.add_argument("--project", required=True, help="Nome do projeto")
    mvp_build_plan_create_parser.add_argument("--from-intake", required=True, help="Report de project-intake")
    mvp_build_plan_create_parser.add_argument("--dry-run", action="store_true", help="Obrigatorio nesta sprint")
    mvp_build_plan_create_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    mvp_build_plan_create_parser.set_defaults(func=cmd_mvp_build_plan_create)

    mvp_capsule_build_canary_parser = subparsers.add_parser(
        "mvp-capsule-build-canary",
        help="Executa ou planeja um canary pequeno de build em cápsula",
    )
    mvp_capsule_build_canary_parser.add_argument("--build-plan", required=True, help="Report de build plan")
    mvp_capsule_build_canary_parser.add_argument("--dry-run", action="store_true", help="Planeja sem executar")
    mvp_capsule_build_canary_parser.add_argument(
        "--execute-canary",
        action="store_true",
        help="Executa o canary na cápsula",
    )
    mvp_capsule_build_canary_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    mvp_capsule_build_canary_parser.set_defaults(func=cmd_mvp_capsule_build_canary)

    mvp_apply_plan_create_parser = subparsers.add_parser(
        "mvp-apply-plan-create",
        help="Cria um plano de aplicação com gate humano",
    )
    mvp_apply_plan_create_parser.add_argument("--canary-report", required=True, help="Report de canary")
    mvp_apply_plan_create_parser.add_argument("--dry-run", action="store_true", help="Obrigatorio nesta sprint")
    mvp_apply_plan_create_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    mvp_apply_plan_create_parser.set_defaults(func=cmd_mvp_apply_plan_create)

    project_workspace_scaffold_parser = subparsers.add_parser(
        "project-workspace-scaffold",
        help="Prepara um workspace local controlado para projeto real",
    )
    project_workspace_scaffold_parser.add_argument("--project", required=True, help="Nome do projeto")
    project_workspace_scaffold_parser.add_argument("--kind", required=True, help="Tipo do projeto")
    project_workspace_scaffold_parser.add_argument(
        "--from-template",
        default="simple-web-mvp",
        help="Template de workspace a utilizar",
    )
    project_workspace_scaffold_parser.add_argument("--dry-run", action="store_true", help="Planeja sem criar")
    project_workspace_scaffold_parser.add_argument(
        "--create-workspace",
        action="store_true",
        help="Cria o workspace local controlado",
    )
    project_workspace_scaffold_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    project_workspace_scaffold_parser.set_defaults(func=cmd_project_workspace_scaffold)

    mvp_delivery_package_create_parser = subparsers.add_parser(
        "mvp-delivery-package-create",
        help="Gera um pacote local de entrega do MVP em dry-run",
    )
    mvp_delivery_package_create_parser.add_argument("--project", required=True, help="Nome do projeto")
    mvp_delivery_package_create_parser.add_argument("--workspace", required=True, help="Caminho do workspace")
    mvp_delivery_package_create_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    mvp_delivery_package_create_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    mvp_delivery_package_create_parser.set_defaults(func=cmd_mvp_delivery_package_create)

    project_pilot_runbook_create_parser = subparsers.add_parser(
        "project-pilot-runbook-create",
        help="Cria o runbook operacional do primeiro projeto piloto em dry-run",
    )
    project_pilot_runbook_create_parser.add_argument("--project", required=True, help="Nome do projeto")
    project_pilot_runbook_create_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    project_pilot_runbook_create_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    project_pilot_runbook_create_parser.set_defaults(func=cmd_project_pilot_runbook_create)

    obsidian_project_sync_parser = subparsers.add_parser(
        "obsidian-project-sync",
        help="Sincroniza a memória curta do projeto para Obsidian",
    )
    obsidian_project_sync_parser.add_argument("--project", required=True, help="Nome do projeto")
    obsidian_project_sync_parser.add_argument("--dry-run", action="store_true", help="Planeja sem escrever")
    obsidian_project_sync_parser.add_argument("--write", action="store_true", help="Escreve a nota permitida")
    obsidian_project_sync_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    obsidian_project_sync_parser.set_defaults(func=cmd_obsidian_project_sync)

    factoryos_v1_readiness_gate_parser = subparsers.add_parser(
        "factoryos-v1-readiness-gate",
        help="Verifica a prontidão V1 do FactoryOS em dry-run",
    )
    factoryos_v1_readiness_gate_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    factoryos_v1_readiness_gate_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    factoryos_v1_readiness_gate_parser.set_defaults(func=cmd_factoryos_v1_readiness_gate)

    factoryos_v1_audit_parser = subparsers.add_parser(
        "factoryos-v1-audit",
        help="Audita consistência V1 do FactoryOS em dry-run",
    )
    factoryos_v1_audit_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    factoryos_v1_audit_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    factoryos_v1_audit_parser.set_defaults(func=cmd_factoryos_v1_audit)

    factoryos_v1_security_review_parser = subparsers.add_parser(
        "factoryos-v1-security-review",
        help="Revê contratos de segurança e safety V1 em dry-run",
    )
    factoryos_v1_security_review_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    factoryos_v1_security_review_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    factoryos_v1_security_review_parser.set_defaults(func=cmd_factoryos_v1_security_review)

    factoryos_v1_reliability_check_parser = subparsers.add_parser(
        "factoryos-v1-reliability-check",
        help="Verifica confiabilidade operacional V1 em dry-run",
    )
    factoryos_v1_reliability_check_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    factoryos_v1_reliability_check_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    factoryos_v1_reliability_check_parser.set_defaults(func=cmd_factoryos_v1_reliability_check)

    factoryos_v1_polish_check_parser = subparsers.add_parser(
        "factoryos-v1-polish-check",
        help="Executa a lapidação técnica final V1 em dry-run",
    )
    factoryos_v1_polish_check_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    factoryos_v1_polish_check_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    factoryos_v1_polish_check_parser.set_defaults(func=cmd_factoryos_v1_polish_check)

    factoryos_v1_readiness_closure_parser = subparsers.add_parser(
        "factoryos-v1-readiness-closure",
        help="Fecha formalmente a prontidão V1 antes do technical freeze",
    )
    factoryos_v1_readiness_closure_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    factoryos_v1_readiness_closure_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    factoryos_v1_readiness_closure_parser.set_defaults(func=cmd_factoryos_v1_readiness_closure)

    factoryos_v1_technical_freeze_parser = subparsers.add_parser(
        "factoryos-v1-technical-freeze",
        help="Registra o technical freeze V1 em dry-run",
    )
    factoryos_v1_technical_freeze_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    factoryos_v1_technical_freeze_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    factoryos_v1_technical_freeze_parser.set_defaults(func=cmd_factoryos_v1_technical_freeze)

    release_packaging_strategy_parser = subparsers.add_parser(
        "release-packaging-strategy",
        help="Define a estrategia segura de backup e release limpo em dry-run",
    )
    release_packaging_strategy_parser.add_argument("--dry-run", action="store_true", required=True)
    release_packaging_strategy_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    release_packaging_strategy_parser.set_defaults(func=cmd_release_packaging_strategy)

    clean_public_export_plan_parser = subparsers.add_parser(
        "clean-public-export-plan",
        help="Planeja export publico limpo sem criar diretorio",
    )
    clean_public_export_plan_parser.add_argument("--dry-run", action="store_true", required=True)
    clean_public_export_plan_parser.add_argument("--export-path", default="<FACTORYOS_CLEAN_EXPORT>")
    clean_public_export_plan_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    clean_public_export_plan_parser.set_defaults(func=cmd_clean_public_export_plan)

    clean_public_export_create_parser = subparsers.add_parser(
        "clean-public-export-create",
        help="Cria ou simula export publico limpo sem remoto",
    )
    clean_public_export_create_parser.add_argument("--dry-run", action="store_true")
    clean_public_export_create_parser.add_argument("--export-path", default="<FACTORYOS_CLEAN_EXPORT>")
    clean_public_export_create_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    clean_public_export_create_parser.set_defaults(func=cmd_clean_public_export_create)

    clean_public_export_validate_parser = subparsers.add_parser(
        "clean-public-export-validate",
        help="Valida export publico limpo sem liberar publicacao",
    )
    clean_public_export_validate_parser.add_argument("--dry-run", action="store_true", required=True)
    clean_public_export_validate_parser.add_argument("--export-path", default="<FACTORYOS_CLEAN_EXPORT>")
    clean_public_export_validate_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    clean_public_export_validate_parser.set_defaults(func=cmd_clean_public_export_validate)

    public_repo_readiness_gate_parser = subparsers.add_parser(
        "public-repo-readiness-gate",
        help="Gate final de prontidao do repo publico sem push",
    )
    public_repo_readiness_gate_parser.add_argument("--dry-run", action="store_true", required=True)
    public_repo_readiness_gate_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    public_repo_readiness_gate_parser.set_defaults(func=cmd_public_repo_readiness_gate)

    public_export_leak_review_parser = subparsers.add_parser(
        "public-export-leak-review",
        help="Revisa achados redigidos do export publico sem liberar push",
    )
    public_export_leak_review_parser.add_argument("--dry-run", action="store_true", required=True)
    public_export_leak_review_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    public_export_leak_review_parser.set_defaults(func=cmd_public_export_leak_review)

    github_backup_plan_parser = subparsers.add_parser(
        "github-backup-plan",
        help="Gera plano de branch/tag local de backup sem executar Git",
    )
    github_backup_plan_parser.add_argument("--dry-run", action="store_true", required=True)
    github_backup_plan_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    github_backup_plan_parser.set_defaults(func=cmd_github_backup_plan)

    github_publish_plan_parser = subparsers.add_parser(
        "github-publish-plan",
        help="Gera plano de publicacao GitHub sem criar remoto ou push",
    )
    github_publish_plan_parser.add_argument("--dry-run", action="store_true", required=True)
    github_publish_plan_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    github_publish_plan_parser.set_defaults(func=cmd_github_publish_plan)

    github_release_checklist_parser = subparsers.add_parser(
        "github-release-checklist",
        help="Checklist final de release GitHub em dry-run com safe_to_push=false",
    )
    github_release_checklist_parser.add_argument("--dry-run", action="store_true", required=True)
    github_release_checklist_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    github_release_checklist_parser.set_defaults(func=cmd_github_release_checklist)

    mvp_evaluate_parser = subparsers.add_parser(
        "mvp-evaluate",
        help="Avalia um workspace MVP com checks estruturados",
    )
    mvp_evaluate_parser.add_argument("--project", required=True, help="Nome do projeto")
    mvp_evaluate_parser.add_argument("--workspace", required=True, help="Caminho do workspace")
    mvp_evaluate_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    mvp_evaluate_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    mvp_evaluate_parser.set_defaults(func=cmd_mvp_evaluate)

    bounded_live_canary_review_parser = subparsers.add_parser(
        "bounded-live-canary-review",
        help="Revê o bounded live canary da Sprint 035 e decide se pode avançar para política de expansão"
    )
    bounded_live_canary_review_target = bounded_live_canary_review_parser.add_mutually_exclusive_group(required=False)
    bounded_live_canary_review_target.add_argument("--run-id", help="Id da run do bounded live canary")
    bounded_live_canary_review_target.add_argument(
        "--report",
        help="Caminho relativo para um report em reports/bounded-long-run-live-canary/"
    )
    bounded_live_canary_review_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    bounded_live_canary_review_parser.set_defaults(func=cmd_bounded_live_canary_review)

    factory_long_run_plan_parser = subparsers.add_parser(
        "factory-long-run-plan",
        help="Gera um plano dry-run para rodada longa sem executar live"
    )
    factory_long_run_plan_parser.add_argument(
        "--run-id",
        help="Id explícito da run"
    )
    factory_long_run_plan_parser.add_argument(
        "--target-minutes",
        type=int,
        default=30,
        help="Duração alvo entre 15 e 60 minutos"
    )
    factory_long_run_plan_parser.add_argument(
        "--max-steps",
        type=int,
        default=6,
        help="Máximo de steps entre 1 e 6"
    )
    factory_long_run_plan_parser.add_argument(
        "--live",
        action="store_true",
        help="Bloqueado nesta sprint; preservado apenas para mensagem explícita"
    )
    factory_long_run_plan_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_long_run_plan_parser.set_defaults(func=cmd_factory_long_run_plan)

    factory_long_run_rehearsal_parser = subparsers.add_parser(
        "factory-long-run-rehearsal",
        help="Executa o rehearsal controlado de rodada longa em dry-run"
    )
    factory_long_run_rehearsal_parser.add_argument(
        "--run-id",
        required=True,
        help="Id explícito da run"
    )
    factory_long_run_rehearsal_parser.add_argument(
        "--target-minutes",
        type=int,
        default=30,
        help="Duração alvo entre 15 e 60 minutos"
    )
    factory_long_run_rehearsal_parser.add_argument(
        "--max-steps",
        type=int,
        default=6,
        help="Máximo de steps entre 1 e 6"
    )
    factory_long_run_rehearsal_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Obrigatório nesta sprint; rehearsal live é bloqueado"
    )
    factory_long_run_rehearsal_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_long_run_rehearsal_parser.set_defaults(func=cmd_factory_long_run_rehearsal)

    long_run_expansion_policy_parser = subparsers.add_parser(
        "long-run-expansion-policy",
        help="Gera a política de expansão futura do long run live sem executar live"
    )
    long_run_expansion_policy_parser.add_argument("--run-id", required=True, help="Id da run")
    long_run_expansion_policy_parser.add_argument(
        "--target-minutes",
        type=int,
        required=True,
        help="Duração alvo do próximo gate"
    )
    long_run_expansion_policy_parser.add_argument(
        "--max-steps",
        type=int,
        required=True,
        help="Número máximo de steps do próximo gate"
    )
    long_run_expansion_policy_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    long_run_expansion_policy_parser.set_defaults(func=cmd_long_run_expansion_policy)

    expanded_long_run_rehearsal_parser = subparsers.add_parser(
        "expanded-long-run-rehearsal",
        help="Executa o rehearsal expandido 30m/6 steps em dry-run"
    )
    expanded_long_run_rehearsal_parser.add_argument("--run-id", required=True, help="Id da run")
    expanded_long_run_rehearsal_parser.add_argument(
        "--target-minutes",
        type=int,
        default=30,
        help="Duração alvo do rehearsal expandido"
    )
    expanded_long_run_rehearsal_parser.add_argument(
        "--max-steps",
        type=int,
        default=6,
        help="Máximo de steps do rehearsal expandido"
    )
    expanded_long_run_rehearsal_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Obrigatório nesta sprint; live é bloqueado"
    )
    expanded_long_run_rehearsal_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    expanded_long_run_rehearsal_parser.set_defaults(func=cmd_expanded_long_run_rehearsal)

    expanded_long_run_review_parser = subparsers.add_parser(
        "expanded-long-run-review",
        help="Revisa formalmente o rehearsal expandido 30m/6 steps"
    )
    expanded_long_run_review_target = expanded_long_run_review_parser.add_mutually_exclusive_group(required=True)
    expanded_long_run_review_target.add_argument("--run-id", help="Id da run")
    expanded_long_run_review_target.add_argument(
        "--report",
        help="Caminho relativo para um report em reports/expanded-long-run-reviews/"
    )
    expanded_long_run_review_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    expanded_long_run_review_parser.set_defaults(func=cmd_expanded_long_run_review)

    expanded_bounded_live_canary_parser = subparsers.add_parser(
        "expanded-bounded-live-canary",
        help="Executa o canário live expandido 30m/6 steps em worktree isolado"
    )
    expanded_bounded_live_canary_parser.add_argument("--run-id", required=True, help="Id da run")
    expanded_bounded_live_canary_parser.add_argument(
        "--max-steps",
        type=int,
        default=6,
        help="Máximo de steps do canário expandido"
    )
    expanded_bounded_live_canary_parser.add_argument(
        "--max-minutes",
        type=int,
        default=30,
        help="Máximo de minutos do canário expandido"
    )
    expanded_bounded_live_canary_parser.add_argument(
        "--bounded",
        action="store_true",
        help="Confirma o modo bounded"
    )
    expanded_bounded_live_canary_parser.add_argument(
        "--canary",
        action="store_true",
        help="Confirma o modo canário"
    )
    expanded_bounded_live_canary_parser.add_argument(
        "--cost-aware",
        action="store_true",
        help="Confirma a camada cost-aware"
    )
    expanded_bounded_live_canary_parser.add_argument(
        "--no-push",
        action="store_true",
        help="Confirma que push está bloqueado"
    )
    expanded_bounded_live_canary_parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="Confirma que deploy está bloqueado"
    )
    expanded_bounded_live_canary_parser.add_argument(
        "--no-paid-api",
        action="store_true",
        help="Confirma que API paga está bloqueada"
    )
    expanded_bounded_live_canary_parser.add_argument(
        "--no-secrets",
        action="store_true",
        help="Confirma que secrets estão bloqueados"
    )
    expanded_bounded_live_canary_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    expanded_bounded_live_canary_parser.set_defaults(func=cmd_expanded_bounded_live_canary)

    post_expansion_evaluate_parser = subparsers.add_parser(
        "post-expansion-evaluate",
        help="Avalia formalmente o canário expandido da Sprint 057"
    )
    post_expansion_evaluate_parser.add_argument(
        "--report",
        required=True,
        help="Caminho relativo para um report em reports/expanded-bounded-live-canary/"
    )
    post_expansion_evaluate_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    post_expansion_evaluate_parser.set_defaults(func=cmd_post_expansion_evaluate)

    post_expansion_rollback_parser = subparsers.add_parser(
        "post-expansion-rollback-plan",
        help="Gera plano de rollback/recovery em dry-run para o canário expandido"
    )
    post_expansion_rollback_parser.add_argument(
        "--report",
        required=True,
        help="Caminho relativo para um report em reports/expanded-bounded-live-canary/"
    )
    post_expansion_rollback_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Obrigatório; plano apenas, sem aplicar rollback"
    )
    post_expansion_rollback_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    post_expansion_rollback_parser.set_defaults(func=cmd_post_expansion_rollback_plan)

    report_retention_plan_parser = subparsers.add_parser(
        "report-retention-plan",
        help="Gera plano read-only de retenção de reports"
    )
    report_retention_plan_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    report_retention_plan_parser.set_defaults(func=cmd_report_retention_plan)

    report_retention_audit_parser = subparsers.add_parser(
        "report-retention-audit",
        help="Audita reports e sugere retenção em dry-run",
    )
    report_retention_audit_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    report_retention_audit_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    report_retention_audit_parser.set_defaults(func=cmd_report_retention_audit)

    report_retention_cleanup_plan_parser = subparsers.add_parser(
        "report-retention-cleanup-plan",
        help="Gera plano de limpeza segura em dry-run",
    )
    report_retention_cleanup_plan_parser.add_argument("--dry-run", action="store_true", help="Obrigatório nesta sprint")
    report_retention_cleanup_plan_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    report_retention_cleanup_plan_parser.set_defaults(func=cmd_report_retention_cleanup_plan)

    worktree_lifecycle_plan_parser = subparsers.add_parser(
        "worktree-lifecycle-plan",
        help="Gera plano read-only de lifecycle dos worktrees"
    )
    worktree_lifecycle_plan_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    worktree_lifecycle_plan_parser.set_defaults(func=cmd_worktree_lifecycle_plan)

    factory_maintenance_plan_parser = subparsers.add_parser(
        "factory-maintenance-plan",
        help="Combina retenção de reports, lifecycle de worktrees e state hygiene"
    )
    factory_maintenance_plan_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    factory_maintenance_plan_parser.set_defaults(func=cmd_factory_maintenance_plan)

    report_latest_parser = subparsers.add_parser(
        "report-latest",
        help="Mostra o report JSON mais recente e válido por tipo"
    )
    report_latest_parser.add_argument("kind", choices=sorted(REPORT_KINDS))
    report_latest_parser.add_argument(
        "--run-id",
        help="Filtra o report pela run"
    )
    report_latest_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    report_latest_parser.set_defaults(func=cmd_report_latest)

    report_list_parser = subparsers.add_parser(
        "report-list",
        help="Lista reports JSON válidos por tipo"
    )
    report_list_parser.add_argument("kind", choices=sorted(REPORT_KINDS))
    report_list_parser.add_argument(
        "--run-id",
        help="Filtra os reports pela run"
    )
    report_list_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Limite de resultados"
    )
    report_list_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    report_list_parser.set_defaults(func=cmd_report_list)

    execution_evaluate_parser = subparsers.add_parser(
        "execution-evaluate",
        help="Avalia um report existente e gera uma decisão estruturada"
    )
    execution_evaluate_target = execution_evaluate_parser.add_mutually_exclusive_group(required=True)
    execution_evaluate_target.add_argument(
        "--run-id",
        help="Id da run a ser avaliada"
    )
    execution_evaluate_target.add_argument(
        "--report",
        help="Caminho relativo para um report dentro de reports/"
    )
    execution_evaluate_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    execution_evaluate_parser.set_defaults(func=cmd_execution_evaluate)

    execution_close_parser = subparsers.add_parser(
        "execution-close-if-passed",
        help="Fecha run e task apenas se a avaliação tiver passado"
    )
    execution_close_parser.add_argument(
        "--run-id",
        required=True,
        help="Id da run"
    )
    execution_close_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Avalia sem fechar run/task"
    )
    execution_close_parser.add_argument(
        "--out",
        help="Caminho opcional para salvar a saída em JSON"
    )
    execution_close_parser.set_defaults(func=cmd_execution_close_if_passed)

    deep_hygiene_audit_parser = subparsers.add_parser(
        "deep-hygiene-audit",
        help="Audita higiene profunda e artefatos externos sem apagar arquivos"
    )
    deep_hygiene_audit_parser.add_argument("--dry-run", action="store_true", required=True)
    deep_hygiene_audit_parser.add_argument("--include-external", action="store_true")
    deep_hygiene_audit_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    deep_hygiene_audit_parser.set_defaults(func=cmd_deep_hygiene_audit)

    cleanup_plan_parser = subparsers.add_parser(
        "cleanup-plan",
        help="Gera plano conservador de limpeza a partir de auditoria"
    )
    cleanup_plan_parser.add_argument("--audit-report", required=True)
    cleanup_plan_parser.add_argument("--dry-run", action="store_true", required=True)
    cleanup_plan_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    cleanup_plan_parser.set_defaults(func=cmd_cleanup_plan)

    cleanup_apply_parser = subparsers.add_parser(
        "cleanup-apply",
        help="Aplica plano de limpeza somente quando explicitamente seguro"
    )
    cleanup_apply_parser.add_argument("--cleanup-plan", required=True)
    cleanup_apply_parser.add_argument("--dry-run", action="store_true")
    cleanup_apply_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    cleanup_apply_parser.set_defaults(func=cmd_cleanup_apply)

    cleanup_validate_parser = subparsers.add_parser(
        "cleanup-validate",
        help="Valida fluxo de cleanup em fixture sintética controlada"
    )
    cleanup_validate_parser.add_argument("--dry-run", action="store_true", required=True)
    cleanup_validate_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    cleanup_validate_parser.set_defaults(func=cmd_cleanup_validate)

    extended_cheap_run_plan_parser = subparsers.add_parser(
        "extended-cheap-run-plan",
        help="Planeja run leve/barata estendida sem liberar execução live"
    )
    extended_cheap_run_plan_parser.add_argument("--max-minutes", type=int, default=60)
    extended_cheap_run_plan_parser.add_argument("--dry-run", action="store_true", required=True)
    extended_cheap_run_plan_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    extended_cheap_run_plan_parser.set_defaults(func=cmd_extended_cheap_run_plan)

    extended_cheap_run_rehearsal_parser = subparsers.add_parser(
        "extended-cheap-run-rehearsal",
        help="Ensaiar política de run leve/barata task-by-task sem execução live"
    )
    extended_cheap_run_rehearsal_parser.add_argument("--max-minutes", type=int, default=60)
    extended_cheap_run_rehearsal_parser.add_argument("--max-tasks", type=int, default=10)
    extended_cheap_run_rehearsal_parser.add_argument("--dry-run", action="store_true", required=True)
    extended_cheap_run_rehearsal_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    extended_cheap_run_rehearsal_parser.set_defaults(func=cmd_extended_cheap_run_rehearsal)

    extended_cheap_run_gate_parser = subparsers.add_parser(
        "extended-cheap-run-gate",
        help="Gate V0 que mantém execução live bloqueada até nova autorização"
    )
    extended_cheap_run_gate_parser.add_argument("--dry-run", action="store_true", required=True)
    extended_cheap_run_gate_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    extended_cheap_run_gate_parser.set_defaults(func=cmd_extended_cheap_run_gate)

    panel_ux_audit_parser = subparsers.add_parser(
        "panel-ux-audit",
        help="Audita UX visual do painel local em dry-run",
    )
    panel_ux_audit_parser.add_argument("--dry-run", action="store_true", required=True)
    panel_ux_audit_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    panel_ux_audit_parser.set_defaults(func=cmd_panel_ux_audit)

    panel_usability_parser = subparsers.add_parser(
        "panel-usability-check",
        help="Verifica polimento de interacao e usabilidade do painel em dry-run",
    )
    panel_usability_parser.add_argument("--dry-run", action="store_true", required=True)
    panel_usability_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    panel_usability_parser.set_defaults(func=cmd_panel_usability_check)

    panel_project_flow_parser = subparsers.add_parser(
        "panel-project-flow-check",
        help="Verifica UX do fluxo de projeto/MVP do painel em dry-run",
    )
    panel_project_flow_parser.add_argument("--dry-run", action="store_true", required=True)
    panel_project_flow_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    panel_project_flow_parser.set_defaults(func=cmd_panel_project_flow_check)

    panel_final_visual_qa_parser = subparsers.add_parser(
        "panel-final-visual-qa",
        help="Roda QA visual/estrutural final do painel em dry-run",
    )
    panel_final_visual_qa_parser.add_argument("--dry-run", action="store_true", required=True)
    panel_final_visual_qa_parser.add_argument("--out", help="Caminho opcional para salvar a saída em JSON")
    panel_final_visual_qa_parser.set_defaults(func=cmd_panel_final_visual_qa)

    return parser


def main() -> int:
    alias_to_command = {
        "factoryos-deep-hygiene-audit": "deep-hygiene-audit",
        "factoryos-cleanup-plan": "cleanup-plan",
        "factoryos-cleanup-apply": "cleanup-apply",
        "factoryos-cleanup-validate": "cleanup-validate",
        "factory-extended-cheap-run-plan": "extended-cheap-run-plan",
        "factory-extended-cheap-run-rehearsal": "extended-cheap-run-rehearsal",
        "factory-extended-cheap-run-gate": "extended-cheap-run-gate",
        "release-packaging-strategy": "release-packaging-strategy",
        "clean-public-export-plan": "clean-public-export-plan",
        "clean-public-export-create": "clean-public-export-create",
        "clean-public-export-validate": "clean-public-export-validate",
        "public-repo-readiness-gate": "public-repo-readiness-gate",
        "public-export-leak-review": "public-export-leak-review",
        "github-backup-plan": "github-backup-plan",
        "github-publish-plan": "github-publish-plan",
        "github-release-checklist": "github-release-checklist",
        "panel-ux-audit": "panel-ux-audit",
    }
    invoked_as = Path(sys.argv[0]).name
    if invoked_as in alias_to_command:
        sys.argv.insert(1, alias_to_command[invoked_as])
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
