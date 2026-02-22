"""Local settings helpers for Menemory."""

from __future__ import annotations

import json
import os
import socket
import subprocess
from pathlib import Path
from typing import Any

from .workspace import workspace_root


def settings_path() -> Path:
    return workspace_root() / "config.json"


def load_settings() -> dict[str, Any]:
    path = settings_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def save_settings(payload: dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_value(*values: str | None) -> str | None:
    for value in values:
        if value is None:
            continue
        if str(value).strip():
            return str(value).strip()
    return None


def resolve_setting(env_key: str, settings_key: str, default: str | None = None) -> str | None:
    settings = load_settings()
    return resolve_value(os.environ.get(env_key), settings.get(settings_key), default)


def _git_config(key: str) -> str | None:
    proc = subprocess.run(["git", "config", "--get", key], check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    value = (proc.stdout or "").strip()
    return value or None


def suggested_user_name() -> str:
    return resolve_value(_git_config("user.name"), os.environ.get("USER"), "unknown-user") or "unknown-user"


def suggested_user_email() -> str:
    return resolve_value(_git_config("user.email"), os.environ.get("EMAIL"), "") or ""


def suggested_server_id() -> str:
    return resolve_value(os.environ.get("SUPABASE_SERVER_ID"), socket.gethostname(), "default-server") or "default-server"


def mask_secret(value: str | None, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep:
        return "*" * len(value)
    return "*" * (len(value) - keep) + value[-keep:]
