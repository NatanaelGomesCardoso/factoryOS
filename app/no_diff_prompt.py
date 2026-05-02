from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

NO_DIFF_PROMPT_CONTRACT_VERSION = "v0"
NO_DIFF_PROMPT_CONTRACT_MARKER = "no-diff-prompt-contract"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def no_diff_prompt_contract_lines(*, final_summary_max_lines: int = 20) -> list[str]:
    return [
        NO_DIFF_PROMPT_CONTRACT_MARKER,
        "",
        "- não imprimir diff;",
        "- não imprimir patch;",
        "- não imprimir conteúdo de arquivo;",
        "- não listar arquivos em excesso;",
        "- não repetir summary;",
        "- salvar evidências em reports;",
        f"- terminal final máximo de {final_summary_max_lines} linhas;",
        "- usar changed_files_count, report_path e validation_status;",
    ]


def no_diff_prompt_contract_text(*, final_summary_max_lines: int = 20) -> str:
    return "\n".join(no_diff_prompt_contract_lines(final_summary_max_lines=final_summary_max_lines)) + "\n"


def prompt_has_no_diff_contract(prompt_text: str) -> bool:
    lowered = prompt_text.lower()
    return NO_DIFF_PROMPT_CONTRACT_MARKER in lowered or "no diff prompt contract" in lowered


def check_no_diff_prompt_contract(prompt_file: str | Path, *, final_summary_max_lines: int = 20) -> dict[str, Any]:
    path = Path(prompt_file)
    if not path.exists():
        raise TaskRunnerError(f"prompt inexistente: {path}")
    if not path.is_file():
        raise TaskRunnerError(f"prompt não aponta para arquivo: {path}")
    if path.is_symlink():
        raise TaskRunnerError("symlink não permitido no prompt.")

    text = path.read_text(encoding="utf-8", errors="replace")
    has_contract = prompt_has_no_diff_contract(text)
    status = "ok" if has_contract else "warn"
    warnings = [] if has_contract else ["prompt_missing_no_diff_contract"]
    return {
        "ok": True,
        "prompt_file": str(path),
        "prompt_has_no_diff_contract": has_contract,
        "no_diff_prompt_contract_version": NO_DIFF_PROMPT_CONTRACT_VERSION,
        "final_summary_max_lines": final_summary_max_lines,
        "validation_status": status,
        "warnings": warnings,
        "generated_at": _now_iso(),
    }


def no_diff_prompt_contract_report_path(repo: Path | None = None) -> Path:
    base = (repo or Path.cwd()) / "reports" / "no-diff-prompt-contract"
    return base / f"{_timestamp()}.json"
