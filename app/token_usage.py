from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

TOKEN_USAGE_PARSER_VERSION = "v0"
_TOKEN_FIELDS = {
    "tokens_used",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "total_tokens",
}


def _normalize_number(raw: str) -> int | None:
    cleaned = raw.replace(",", "").replace(" ", "").replace("_", "")
    if not cleaned.isdigit():
        return None
    return int(cleaned)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _walk_json(value: Any, found: dict[str, int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = _normalize_key(str(key))
            if normalized_key in _TOKEN_FIELDS and isinstance(item, int):
                found[normalized_key] = item
            elif normalized_key in _TOKEN_FIELDS and isinstance(item, str):
                parsed = _normalize_number(item)
                if parsed is not None:
                    found[normalized_key] = parsed
            _walk_json(item, found)
    elif isinstance(value, list):
        for item in value:
            _walk_json(item, found)


def _search_pattern(text: str, patterns: tuple[str, ...]) -> int | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            parsed = _normalize_number(match.group(1))
            if parsed is not None:
                return parsed
    return None


def _parse_from_json_lines(text: str) -> tuple[dict[str, int], list[str]]:
    found: dict[str, int] = {}
    warnings: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            warnings.append("json_line_malformed")
            continue
        if isinstance(event, dict):
            _walk_json(event, found)
    return found, warnings


def parse_token_usage_text(text: str) -> dict[str, Any]:
    found, warnings = _parse_from_json_lines(text)

    if "tokens_used" not in found:
        value = _search_pattern(
            text,
            (
                r"tokens\s+used\s*[:=]?\s*\n\s*([0-9][0-9,._ ]*)",
                r"tokens\s+used\s*[:=]?\s*([0-9][0-9,._ ]*)",
            ),
        )
        if value is not None:
            found["tokens_used"] = value

    for field, patterns in {
        "input_tokens": (
            r"input\s+tokens\s*[:=]?\s*\n\s*([0-9][0-9,._ ]*)",
            r"input\s+tokens\s*[:=]?\s*([0-9][0-9,._ ]*)",
        ),
        "cached_input_tokens": (
            r"cached\s+input\s+tokens\s*[:=]?\s*\n\s*([0-9][0-9,._ ]*)",
            r"cached\s+input\s+tokens\s*[:=]?\s*([0-9][0-9,._ ]*)",
        ),
        "output_tokens": (
            r"output\s+tokens\s*[:=]?\s*\n\s*([0-9][0-9,._ ]*)",
            r"output\s+tokens\s*[:=]?\s*([0-9][0-9,._ ]*)",
        ),
        "total_tokens": (
            r"total[_\s]+tokens\s*[:=]?\s*\n\s*([0-9][0-9,._ ]*)",
            r"total[_\s]+tokens\s*[:=]?\s*([0-9][0-9,._ ]*)",
        ),
    }.items():
        if field not in found:
            value = _search_pattern(text, patterns)
            if value is not None:
                found[field] = value

    if "total_tokens" not in found:
        if "tokens_used" in found:
            found["total_tokens"] = found["tokens_used"]
        elif {"input_tokens", "cached_input_tokens", "output_tokens"}.issubset(found):
            found["total_tokens"] = (
                found["input_tokens"] + found["cached_input_tokens"] + found["output_tokens"]
            )

    if "tokens_used" not in found:
        if "total_tokens" in found:
            found["tokens_used"] = found["total_tokens"]
        elif {"input_tokens", "cached_input_tokens", "output_tokens"}.issubset(found):
            found["tokens_used"] = (
                found["input_tokens"] + found["cached_input_tokens"] + found["output_tokens"]
            )

    if not found:
        warnings.append("token_fields_missing")

    return {
        "ok": True,
        "tokens_used": found.get("tokens_used"),
        "input_tokens": found.get("input_tokens"),
        "cached_input_tokens": found.get("cached_input_tokens"),
        "output_tokens": found.get("output_tokens"),
        "total_tokens": found.get("total_tokens"),
        "parser_version": TOKEN_USAGE_PARSER_VERSION,
        "warnings": warnings,
    }


def parse_token_usage_log(log_path: str | Path) -> dict[str, Any]:
    path = Path(log_path)
    if not path.exists():
        raise TaskRunnerError(f"log inexistente: {path}")
    if not path.is_file():
        raise TaskRunnerError(f"log não aponta para arquivo: {path}")
    if path.is_symlink():
        raise TaskRunnerError("symlink não permitido no log.")

    text = path.read_text(encoding="utf-8", errors="replace")
    payload = parse_token_usage_text(text)
    payload["log_path"] = str(path)
    return payload
