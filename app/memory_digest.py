from __future__ import annotations

import json
import re
import secrets
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError
from app.token_usage import parse_token_usage_text

MEMORY_DIGEST_VERSION = "v0"
MEMORY_DIGEST_DIR = "memory/digests"
MAX_DIGEST_JSON_BYTES = 20 * 1024
MAX_DIGEST_MD_LINES = 150


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


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            handle.write(content)
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _safe_relative(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()


def _load_text(path: Path) -> str:
    if not path.exists():
        raise TaskRunnerError(f"arquivo inexistente: {path}")
    if not path.is_file():
        raise TaskRunnerError(f"arquivo não aponta para arquivo: {path}")
    if path.is_symlink():
        raise TaskRunnerError("symlink não permitido no arquivo de origem.")
    return path.read_text(encoding="utf-8", errors="replace")


def _git_head(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _git_log(repo: Path, limit: int = 3) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline", f"-{limit}"],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _extract_report_paths(text: str) -> list[str]:
    matches = re.findall(r"(reports/[A-Za-z0-9_.\-/]+)", text)
    result: list[str] = []
    for match in matches:
        normalized = match.strip().rstrip(").,;")
        if normalized not in result:
            result.append(normalized)
    return result[:10]


def _extract_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
    collected: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            cleaned = line.strip()
            if cleaned and cleaned not in collected:
                collected.append(cleaned[:220])
    return collected[:10]


def _truncate(text: str, limit: int) -> str:
    cleaned = " ".join(part.strip() for part in text.splitlines() if part.strip())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 3, 0)].rstrip() + "..."


def _json_size_bytes(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")) + 1


def _build_digest_payload(
    *,
    repo: Path,
    title: str,
    sprint: str,
    source_report: Path,
    source_text: str,
) -> dict[str, Any]:
    token_summary = parse_token_usage_text(source_text)
    commits = _git_log(repo, limit=4)
    decision = "Feature concluída com validação local e contrato compacto."
    summary = _truncate(source_text, 500)
    risks = _extract_keywords(source_text, ("risk", "risco", "warning", "warn", "blocked", "pendência"))
    next_step = _extract_keywords(source_text, ("next", "próximo", "proximo", "follow", "step"))
    report_paths = _extract_report_paths(source_text)
    key_files = report_paths[:5]
    md_lines = [
        f"# {title}",
        "",
        f"- digest_version: `{MEMORY_DIGEST_VERSION}`",
        f"- sprint: `{sprint}`",
        f"- created_at: `{_now_iso()}`",
        f"- source_report: `{_safe_relative(repo, source_report)}`",
        "",
        "## Decision",
        decision,
        "",
        "## Summary",
        summary or "Sem resumo textual extraível.",
        "",
        "## Commits",
        *([f"- {item}" for item in commits] if commits else ["- nenhum commit encontrado"]),
        "",
        "## Key Files",
        *([f"- {item}" for item in key_files] if key_files else ["- nenhum arquivo extraído"]),
        "",
        "## Main Reports",
        *([f"- {item}" for item in report_paths] if report_paths else ["- nenhum report extraído"]),
        "",
        "## Risks",
        *([f"- {item}" for item in risks] if risks else ["- nenhum risco explícito extraído"]),
        "",
        "## Next Step",
        _truncate(" | ".join(next_step), 240) or "Manter o digest como fonte curta e não expandir por padrão.",
        "",
        "## Token Summary",
        json.dumps(token_summary, ensure_ascii=False, sort_keys=True),
    ]
    md_text = "\n".join(md_lines).strip() + "\n"
    if len(md_text.splitlines()) > MAX_DIGEST_MD_LINES:
        md_text = "\n".join(md_text.splitlines()[:MAX_DIGEST_MD_LINES]).rstrip() + "\n"

    payload = {
        "ok": True,
        "digest_version": MEMORY_DIGEST_VERSION,
        "title": title,
        "sprint": sprint,
        "created_at": _now_iso(),
        "source_reports": [_safe_relative(repo, source_report)],
        "commits": commits,
        "decision": decision,
        "summary": summary,
        "key_files": key_files,
        "main_reports": report_paths,
        "risks": risks,
        "next_step": _truncate(" | ".join(next_step), 240) or "Manter o digest curto e preferir este digest no context router.",
        "token_summary": token_summary,
        "do_not_expand_by_default": True,
    }
    if _json_size_bytes(payload) > MAX_DIGEST_JSON_BYTES:
        payload["warnings"] = ["digest_json_size_above_recommended_limit"]
    return payload, md_text


def create_memory_digest(
    *,
    title: str,
    source_report: str | Path,
    sprint: str | int,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = (repo or Path(__file__).resolve().parents[1]).resolve()
    source_path = Path(source_report)
    if not source_path.is_absolute():
        source_path = repo / source_path
    source_path = source_path.resolve()
    if source_path.is_symlink():
        raise TaskRunnerError("symlink não permitido no source_report.")
    if not source_path.exists():
        raise TaskRunnerError(f"source_report inexistente: {source_path}")
    if not source_path.is_relative_to(repo):
        raise TaskRunnerError("source_report precisa ficar dentro do repo.")

    normalized_title = title.strip()
    normalized_sprint = f"{int(str(sprint).strip()):03d}"
    source_text = _load_text(source_path)
    timestamp = _timestamp()
    payload, md_text = _build_digest_payload(
        repo=repo,
        title=normalized_title,
        sprint=normalized_sprint,
        source_report=source_path,
        source_text=source_text,
    )
    json_path = repo / MEMORY_DIGEST_DIR / f"{timestamp}-sprint-{normalized_sprint}.json"
    md_path = repo / MEMORY_DIGEST_DIR / f"{timestamp}-sprint-{normalized_sprint}.md"
    payload["digest_path_json"] = _safe_relative(repo, json_path)
    payload["digest_path_md"] = _safe_relative(repo, md_path)
    payload["source_reports"] = [_safe_relative(repo, source_path)]
    _write_json_atomic(json_path, payload)
    _write_text_atomic(md_path, md_text)
    return payload


def latest_memory_digest(repo: Path | None = None) -> dict[str, Any]:
    repo = (repo or Path(__file__).resolve().parents[1]).resolve()
    digest_dir = repo / MEMORY_DIGEST_DIR
    if not digest_dir.exists():
        return {
            "ok": False,
            "available": False,
            "digest_path_json": "",
            "digest_path_md": "",
            "title": "",
            "created_at": "",
            "sprint": "",
            "commits": [],
            "next_step": "",
            "warnings": ["memory_digest_missing"],
        }

    candidates = sorted(
        (path for path in digest_dir.glob("*.json") if path.is_file() and not path.is_symlink()),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        digest_path_json = str(payload.get("digest_path_json", "")).strip() or _safe_relative(repo, path)
        digest_path_md = str(payload.get("digest_path_md", "")).strip() or path.with_suffix(".md").relative_to(repo).as_posix()
        title = str(payload.get("title", "")).strip()
        created_at = str(payload.get("created_at", "")).strip()
        sprint = str(payload.get("sprint", "")).strip()
        summary = str(payload.get("summary", "")).strip()
        if not title or not created_at or not sprint:
            continue
        return {
            "ok": True,
            "available": True,
            "digest_path_json": digest_path_json,
            "digest_path_md": digest_path_md,
            "title": title,
            "created_at": created_at,
            "sprint": sprint,
            "summary": summary,
            "commits": [str(item) for item in payload.get("commits", []) if str(item).strip()],
            "next_step": str(payload.get("next_step", "")).strip(),
            "warnings": [str(item) for item in payload.get("warnings", []) if str(item).strip()],
        }

    return {
        "ok": False,
        "available": False,
        "digest_path_json": "",
        "digest_path_md": "",
        "title": "",
        "created_at": "",
        "sprint": "",
        "summary": "",
        "commits": [],
        "next_step": "",
        "warnings": ["memory_digest_missing"],
    }


def list_memory_digests(repo: Path | None = None, *, limit: int = 5) -> dict[str, Any]:
    repo = (repo or Path(__file__).resolve().parents[1]).resolve()
    digest_dir = repo / MEMORY_DIGEST_DIR
    entries: list[dict[str, Any]] = []
    if digest_dir.exists():
        for path in sorted(
            (item for item in digest_dir.glob("*.json") if item.is_file() and not item.is_symlink()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            entries.append(
                {
                    "digest_path_json": _safe_relative(repo, path),
                    "digest_path_md": str(payload.get("digest_path_md", "")).strip() or path.with_suffix(".md").relative_to(repo).as_posix(),
                    "title": str(payload.get("title", "")).strip(),
                    "created_at": str(payload.get("created_at", "")).strip(),
                    "sprint": str(payload.get("sprint", "")).strip(),
                    "summary": str(payload.get("summary", "")).strip(),
                    "next_step": str(payload.get("next_step", "")).strip(),
                }
            )

    return {
        "ok": True,
        "count": len(entries),
        "limit": limit,
        "items": entries[: max(limit, 0)],
    }
