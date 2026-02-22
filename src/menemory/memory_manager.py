"""Memory block builder for prompt composition."""

from __future__ import annotations

import json
from typing import Any

from .session_manager import load_session
from .workspace import core_memory_path, longterm_jsonl_path


def load_core_memory() -> str:
    path = core_memory_path()
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def format_conversation(conversation: list[dict[str, Any]]) -> str:
    if not conversation:
        return "(empty)"

    lines: list[str] = []
    for msg in conversation:
        role = str(msg.get("role", "unknown")).upper()
        content = str(msg.get("content", "")).strip()
        lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def _search_longterm_jsonl(user_input: str, limit: int = 4) -> list[str]:
    path = longterm_jsonl_path()
    if not path.exists():
        return []

    tokens = [t for t in user_input.lower().split() if len(t) > 1]
    if not tokens:
        return []

    scored: list[tuple[int, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        text = str(row.get("text", ""))
        lowered = text.lower()
        score = sum(1 for token in tokens if token in lowered)
        if score > 0:
            scored.append((score, text))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:limit]]


def search_longterm(user_input: str, limit: int = 4) -> str:
    matches = _search_longterm_jsonl(user_input=user_input, limit=limit)
    if not matches:
        return "(no relevant long-term memory found)"

    return "\n".join(f"- {item}" for item in matches)


def build_memory_block(user_input: str) -> str:
    core = load_core_memory()
    session = load_session()
    longterm = search_longterm(user_input=user_input)

    return "\n\n".join(
        [
            "### CORE MEMORY\n" + (core or "(empty)"),
            "### SESSION SUMMARY\n" + (session.get("summary") or "(empty)"),
            "### RECENT CONVERSATION\n" + format_conversation(session.get("conversation", [])),
            "### LONG-TERM MEMORY\n" + longterm,
        ]
    )
