"""Supabase sync helpers for session and long-term memory."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .session_manager import load_session, save_session
from .settings import resolve_setting
from .workspace import longterm_jsonl_path


@dataclass
class SupabaseConfig:
    url: str
    service_key: str
    schema: str
    server_id: str


def load_config(server_id: str | None = None) -> SupabaseConfig:
    url = resolve_setting("SUPABASE_URL", "supabase_url")
    service_key = resolve_setting("SUPABASE_SERVICE_ROLE_KEY", "supabase_service_role_key")
    schema = resolve_setting("SUPABASE_SCHEMA", "supabase_schema", "public") or "public"
    resolved_server_id = server_id or resolve_setting("SUPABASE_SERVER_ID", "supabase_server_id", socket.gethostname())

    missing: list[str] = []
    if not url:
        missing.append("SUPABASE_URL")
    if not service_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return SupabaseConfig(url=url.rstrip("/"), service_key=service_key, schema=schema, server_id=resolved_server_id)


def _request_json(
    cfg: SupabaseConfig,
    method: str,
    path: str,
    query: dict[str, str] | None = None,
    payload: Any | None = None,
) -> Any:
    query_part = ""
    if query:
        query_part = "?" + urllib.parse.urlencode(query, doseq=True)

    url = f"{cfg.url}{path}{query_part}"
    data: bytes | None = None
    headers = {
        "apikey": cfg.service_key,
        "Authorization": f"Bearer {cfg.service_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": "return=representation",
        "Accept-Profile": cfg.schema,
        "Content-Profile": cfg.schema,
    }

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase request failed ({exc.code}): {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Supabase connection failed: {exc.reason}") from exc


def upsert_session(server_id: str | None = None) -> dict[str, Any]:
    cfg = load_config(server_id=server_id)
    session = load_session()

    row = {
        "server_id": cfg.server_id,
        "session_id": session.get("session_id"),
        "last_updated": session.get("last_updated"),
        "summary": session.get("summary", ""),
        "conversation": session.get("conversation", []),
        "snapshot": session,
    }

    result = _request_json(
        cfg,
        method="POST",
        path="/rest/v1/ai_sessions",
        query={"on_conflict": "server_id,session_id"},
        payload=[row],
    )
    return {"ok": True, "server_id": cfg.server_id, "session_id": row["session_id"], "result": result}


def pull_session(session_id: str | None = None, server_id: str | None = None) -> dict[str, Any]:
    cfg = load_config(server_id=server_id)
    local = load_session()
    resolved_session_id = session_id or local.get("session_id")

    rows = _request_json(
        cfg,
        method="GET",
        path="/rest/v1/ai_sessions",
        query={
            "server_id": f"eq.{cfg.server_id}",
            "session_id": f"eq.{resolved_session_id}",
            "select": "session_id,last_updated,summary,conversation,snapshot",
            "limit": "1",
        },
    )
    if not rows:
        return {"ok": False, "reason": "not_found", "server_id": cfg.server_id, "session_id": resolved_session_id}

    row = rows[0]
    snapshot = row.get("snapshot") or {}
    restored = {
        "session_id": row.get("session_id", resolved_session_id),
        "last_updated": row.get("last_updated", local.get("last_updated")),
        "summary": row.get("summary", ""),
        "conversation": row.get("conversation", []),
    }
    if isinstance(snapshot, dict):
        restored.update({k: v for k, v in snapshot.items() if k not in {"session_id", "summary", "conversation", "last_updated"}})

    save_session(restored)
    return {"ok": True, "server_id": cfg.server_id, "session_id": restored["session_id"]}


def _load_longterm_rows() -> list[dict[str, Any]]:
    path = longterm_jsonl_path()
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        text = str(obj.get("text", "")).strip()
        if not text:
            continue
        metadata = obj.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {"value": metadata}

        rows.append({
            "text": text,
            "metadata": metadata,
            "content_hash": sha256(text.encode("utf-8")).hexdigest(),
        })
    return rows


def push_longterm(server_id: str | None = None) -> dict[str, Any]:
    cfg = load_config(server_id=server_id)
    rows = _load_longterm_rows()

    payload = [
        {
            "server_id": cfg.server_id,
            "content_hash": row["content_hash"],
            "text": row["text"],
            "metadata": row["metadata"],
        }
        for row in rows
    ]

    if payload:
        _request_json(
            cfg,
            method="POST",
            path="/rest/v1/ai_longterm",
            query={"on_conflict": "server_id,content_hash"},
            payload=payload,
        )
    return {"ok": True, "server_id": cfg.server_id, "rows_pushed": len(payload)}


def pull_longterm(server_id: str | None = None) -> dict[str, Any]:
    cfg = load_config(server_id=server_id)
    rows = _request_json(
        cfg,
        method="GET",
        path="/rest/v1/ai_longterm",
        query={
            "server_id": f"eq.{cfg.server_id}",
            "select": "text,metadata",
            "order": "updated_at.desc",
            "limit": "5000",
        },
    )

    path = longterm_jsonl_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"text": row.get("text", ""), "metadata": row.get("metadata", {})}, ensure_ascii=False) for row in (rows or [])]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return {"ok": True, "server_id": cfg.server_id, "rows_pulled": len(lines)}


def supabase_status(server_id: str | None = None) -> dict[str, Any]:
    cfg = load_config(server_id=server_id)
    rows = _request_json(
        cfg,
        method="GET",
        path="/rest/v1/ai_sessions",
        query={
            "server_id": f"eq.{cfg.server_id}",
            "select": "session_id,last_updated",
            "order": "last_updated.desc",
            "limit": "5",
        },
    )
    return {"ok": True, "server_id": cfg.server_id, "schema": cfg.schema, "recent_sessions": rows or []}
