"""Session persistence and crash-safe rotation for Menemory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .workspace import active_session_path, archive_dir, backup_session_path, ensure_workspace_layout

MAX_CONVERSATION_TURNS = 20
KEEP_RECENT_TURNS = 10


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _default_session(session_id: str | None = None) -> dict[str, Any]:
    return {
        "session_id": session_id or datetime.now(timezone.utc).strftime("%Y-%m-%d-default"),
        "last_updated": utc_now_iso(),
        "conversation": [],
        "summary": "",
    }


def load_session() -> dict[str, Any]:
    ensure_workspace_layout()
    active_path = active_session_path()
    backup_path = backup_session_path()

    if not active_path.exists():
        session = _default_session()
        _atomic_write_json(active_path, session)
        return session

    try:
        return json.loads(active_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        if backup_path.exists():
            recovered = json.loads(backup_path.read_text(encoding="utf-8"))
            _atomic_write_json(active_path, recovered)
            return recovered

        session = _default_session()
        _atomic_write_json(active_path, session)
        return session


def save_session(session: dict[str, Any]) -> None:
    ensure_workspace_layout()
    active_path = active_session_path()
    backup_path = backup_session_path()

    session["last_updated"] = utc_now_iso()

    if active_path.exists():
        backup_path.write_text(active_path.read_text(encoding="utf-8"), encoding="utf-8")

    _atomic_write_json(active_path, session)


def _compress_messages(messages: list[dict[str, str]], max_chars_per_item: int = 220) -> str:
    lines: list[str] = []
    for item in messages:
        role = item.get("role", "unknown")
        content = (item.get("content", "") or "").strip().replace("\n", " ")
        if len(content) > max_chars_per_item:
            content = content[:max_chars_per_item] + "..."
        lines.append(f"- {role}: {content}")
    return "\n".join(lines)


def summarize_and_prune(session: dict[str, Any]) -> dict[str, Any]:
    conversation = session.get("conversation", [])
    if len(conversation) <= MAX_CONVERSATION_TURNS:
        return session

    old_messages = conversation[:-KEEP_RECENT_TURNS]
    recent_messages = conversation[-KEEP_RECENT_TURNS:]

    compressed = _compress_messages(old_messages)
    current_summary = (session.get("summary") or "").strip()

    if current_summary:
        session["summary"] = f"{current_summary}\n\n[Auto summary @ {utc_now_iso()}]\n{compressed}"
    else:
        session["summary"] = f"[Auto summary @ {utc_now_iso()}]\n{compressed}"

    session["conversation"] = recent_messages

    archive_file = archive_dir() / f"{session.get('session_id', 'session')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    _atomic_write_json(archive_file, session)
    return session


def add_message(role: str, content: str) -> dict[str, Any]:
    role = role.strip().lower()
    if role not in {"user", "assistant", "system"}:
        raise ValueError("role must be one of: user, assistant, system")

    session = load_session()
    session.setdefault("conversation", [])
    session.setdefault("summary", "")

    session["conversation"].append({"role": role, "content": content})
    session = summarize_and_prune(session)
    save_session(session)
    return session


def init_session(session_id: str | None = None, overwrite: bool = False) -> dict[str, Any]:
    ensure_workspace_layout()
    if active_session_path().exists() and not overwrite:
        return load_session()

    session = _default_session(session_id=session_id)
    save_session(session)
    return session
