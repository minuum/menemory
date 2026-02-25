"""Session persistence and crash-safe rotation for Menemory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .workspace import (
    active_session_path,
    archive_dir,
    backup_session_path,
    ensure_workspace_layout,
    session_history_path,
)

MAX_CONVERSATION_TURNS = 20
KEEP_RECENT_TURNS = 10


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False))
        handle.write("\n")


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


def append_history_turn(session_id: str, role: str, content: str) -> None:
    ensure_workspace_layout()
    entry = {
        "timestamp": utc_now_iso(),
        "session_id": session_id,
        "role": role,
        "content": content,
    }
    _append_jsonl(session_history_path(session_id), entry)


def _resolve_session_id(session_id: str | None = None) -> str:
    if session_id and session_id.strip():
        return session_id.strip()

    session = load_session()
    resolved = str(session.get("session_id", "")).strip()
    if resolved:
        return resolved
    return datetime.now(timezone.utc).strftime("%Y-%m-%d-default")


def read_history(session_id: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    resolved = _resolve_session_id(session_id=session_id)
    path = session_history_path(resolved)
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if limit is not None and limit >= 0:
        return rows[-limit:]
    return rows


def history_turn_count(session_id: str | None = None) -> int:
    resolved = _resolve_session_id(session_id=session_id)
    path = session_history_path(resolved)
    if not path.exists():
        return 0

    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


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
    session.setdefault("session_id", datetime.now(timezone.utc).strftime("%Y-%m-%d-default"))

    session["conversation"].append({"role": role, "content": content})
    session = summarize_and_prune(session)
    save_session(session)
    append_history_turn(session_id=str(session["session_id"]), role=role, content=content)
    return session


def init_session(session_id: str | None = None, overwrite: bool = False) -> dict[str, Any]:
    ensure_workspace_layout()
    if active_session_path().exists() and not overwrite:
        return load_session()

    session = _default_session(session_id=session_id)
    save_session(session)
    return session
