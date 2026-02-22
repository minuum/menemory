"""tmux integration for SSH-resilient workspace sessions."""

from __future__ import annotations

import re
import shutil
import subprocess


def _run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], text=True, capture_output=True, check=False)


def tmux_available() -> bool:
    return shutil.which("tmux") is not None


def session_to_tmux_name(session_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", session_id.strip())
    return f"menemory-{normalized}"[:80]


def tmux_has_session(tmux_name: str) -> bool:
    proc = _run_tmux(["has-session", "-t", tmux_name])
    return proc.returncode == 0


def tmux_new_session(tmux_name: str, command: str | None = None) -> tuple[bool, str]:
    if tmux_has_session(tmux_name):
        return True, f"already_exists:{tmux_name}"

    args = ["new-session", "-d", "-s", tmux_name]
    if command:
        args.append(command)
    proc = _run_tmux(args)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "tmux new-session failed").strip()
    return True, f"created:{tmux_name}"


def tmux_list_sessions() -> list[str]:
    proc = _run_tmux(["list-sessions", "-F", "#{session_name}"])
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def tmux_attach_command(tmux_name: str) -> str:
    return f"tmux attach-session -t {tmux_name}"
