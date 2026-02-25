"""Workspace path helpers for Menemory."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_CORE_MEMORY = """# Master Core Memory

이 파일은 Menemory 프롬프트에 항상 포함되는 핵심 메모리입니다.

- 프로젝트의 장기 목표
- 개발 철학
- 금지 규칙
- 일관되게 유지할 아키텍처 원칙
"""

_GITIGNORE_MARKER = "# Menemory runtime state (auto-managed)"


def workspace_root() -> Path:
    env_home = os.environ.get("MENEMORY_HOME")
    if env_home and env_home.strip():
        return Path(env_home).expanduser().resolve()
    return (Path.cwd() / ".menemory").resolve()


def core_memory_path() -> Path:
    return workspace_root() / "core" / "master_memory.md"


def sessions_dir() -> Path:
    return workspace_root() / "sessions"


def archive_dir() -> Path:
    return sessions_dir() / "archive"


def history_dir() -> Path:
    return sessions_dir() / "history"


def session_history_path(session_id: str) -> Path:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in session_id.strip())
    normalized = normalized or "default"
    return history_dir() / f"{normalized}.jsonl"


def active_session_path() -> Path:
    return sessions_dir() / "active_session.json"


def backup_session_path() -> Path:
    return sessions_dir() / "active_session.backup.json"


def longterm_jsonl_path() -> Path:
    return workspace_root() / "longterm" / "memory.jsonl"


def chroma_db_dir() -> Path:
    return workspace_root() / "longterm" / "chroma_db"


def _find_git_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _gitignore_rules_for(menemory_home: Path, git_root: Path) -> list[str]:
    try:
        rel = menemory_home.resolve().relative_to(git_root.resolve())
    except ValueError:
        return []

    base = rel.as_posix().rstrip("/")
    if not base:
        return []

    return [
        f"{base}/sessions/",
        f"{base}/longterm/chroma_db/",
        f"{base}/longterm/memory.jsonl",
    ]


def ensure_gitignore_rules() -> bool:
    if os.environ.get("MENEMORY_AUTO_GITIGNORE", "1").strip().lower() in {"0", "false", "off", "no"}:
        return False

    git_root = _find_git_root(Path.cwd())
    if git_root is None:
        return False

    rules = _gitignore_rules_for(workspace_root(), git_root)
    if not rules:
        return False

    gitignore_path = git_root / ".gitignore"
    existing_lines: list[str] = []
    if gitignore_path.exists():
        existing_lines = gitignore_path.read_text(encoding="utf-8").splitlines()

    missing = [rule for rule in rules if rule not in existing_lines]
    if not missing:
        return False

    out = existing_lines[:]
    if out and out[-1].strip():
        out.append("")
    out.append(_GITIGNORE_MARKER)
    out.extend(missing)
    out.append("")
    gitignore_path.write_text("\n".join(out), encoding="utf-8")
    return True


def ensure_workspace_layout() -> None:
    (workspace_root() / "core").mkdir(parents=True, exist_ok=True)
    archive_dir().mkdir(parents=True, exist_ok=True)
    history_dir().mkdir(parents=True, exist_ok=True)
    chroma_db_dir().mkdir(parents=True, exist_ok=True)

    core_path = core_memory_path()
    if not core_path.exists():
        core_path.write_text(DEFAULT_CORE_MEMORY, encoding="utf-8")

    ensure_gitignore_rules()
