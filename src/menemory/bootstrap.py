"""Bootstrap helpers for Menemory init flows."""

from __future__ import annotations

import os
from pathlib import Path


def default_skills_root() -> Path:
    explicit = os.environ.get("MENEMORY_SKILLS_DIR")
    if explicit and explicit.strip():
        return Path(explicit).expanduser().resolve()

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home and codex_home.strip():
        return (Path(codex_home).expanduser().resolve() / "skills").resolve()

    return (Path.home() / ".codex" / "skills").resolve()


def _skill_header(name: str, description: str) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "---\n\n"
    )


def _skill_openai_yaml(name: str, short_description: str, default_prompt: str) -> str:
    return (
        "version: 1\n"
        "interface:\n"
        f"  display_name: {name}\n"
        f"  short_description: {short_description}\n"
        f"  default_prompt: {default_prompt}\n"
    )


def _skill_catalog() -> dict[str, dict[str, object]]:
    return {
        "menemory-bootstrap": {
            "description": "Install Menemory globally, set PATH/alias, and verify command availability.",
            "body": (
                "# Menemory Bootstrap\n\n"
                "## Workflow\n\n"
                "1. Verify local executable: `./menemory --help`\n"
                "2. Install globally (`pip install --user .` or symlink)\n"
                "3. Ensure PATH has `~/.local/bin`\n"
                "4. Rehash and verify: `hash -r && menemory --help`\n"
            ),
            "scripts": {
                "install_global.sh": (
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    "ROOT_DIR=\"${1:-$(pwd)}\"\n"
                    "cd \"$ROOT_DIR\"\n"
                    "python3 -m pip install --user --no-build-isolation .\n"
                    "echo 'export PATH=\"$HOME/.local/bin:$PATH\"'\n"
                    "echo 'Run: source ~/.bashrc && hash -r && menemory --help'\n"
                )
            },
            "prompt": "Help me install menemory globally and verify command availability.",
        },
        "menemory-ops-check": {
            "description": "Run local health checks, gitignore hygiene checks, and backup readiness checks.",
            "body": (
                "# Menemory Ops Check\n\n"
                "## Workflow\n\n"
                "1. `menemory where`\n"
                "2. `menemory status`\n"
                "3. Verify runtime ignore rules in `.gitignore`\n"
                "4. Verify Supabase env readiness\n"
            ),
            "scripts": {
                "ops_check.sh": (
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    "menemory where\n"
                    "menemory status\n"
                    "if [ -n \"${SUPABASE_URL:-}\" ] && [ -n \"${SUPABASE_SERVICE_ROLE_KEY:-}\" ]; then\n"
                    "  echo \"OK: Supabase env configured\"\n"
                    "else\n"
                    "  echo \"WARN: Supabase env missing\"\n"
                    "fi\n"
                )
            },
            "prompt": "Run menemory operational checks and summarize pass/fail results.",
        },
        "menemory-session-capture": {
            "description": "Save current conversation into local Menemory and optionally back up to Supabase.",
            "body": (
                "# Menemory Session Capture\n\n"
                "## Workflow\n\n"
                "1. `menemory start --session-id <id>`\n"
                "2. Add compact user/assistant summaries with `menemory add`\n"
                "3. Confirm with `menemory status`\n"
                "4. Optional backup: `menemory backup push`\n"
            ),
            "scripts": {
                "capture_to_menemory.sh": (
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    "SESSION_ID=\"${1:-dev-$(date +%F)}\"\n"
                    "USER_SUMMARY=\"${2:-사용자 요청 요약}\"\n"
                    "ASSIST_SUMMARY=\"${3:-수행 결과 요약}\"\n"
                    "menemory start --session-id \"$SESSION_ID\"\n"
                    "menemory add --role user --content \"$USER_SUMMARY\"\n"
                    "menemory add --role assistant --content \"$ASSIST_SUMMARY\"\n"
                    "menemory status\n"
                )
            },
            "prompt": "Capture this chat into menemory session and show final status.",
        },
        "menemory-session-recovery": {
            "description": "Recover Menemory context after SSH disconnects, crashes, or migration.",
            "body": (
                "# Menemory Session Recovery\n\n"
                "## Workflow\n\n"
                "1. `menemory where` and `menemory status`\n"
                "2. `menemory resume` (or `--attach`)\n"
                "3. Verify with `menemory show`\n"
                "4. Optional cloud restore: `menemory backup pull --session-id <id>`\n"
            ),
            "scripts": {
                "recover_now.sh": (
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    "menemory where\n"
                    "menemory status\n"
                    "menemory resume\n"
                    "menemory show\n"
                )
            },
            "prompt": "Recover menemory session context after a disconnect.",
        },
        "menemory-supabase-backup": {
            "description": "Back up or restore Menemory data with Supabase while keeping local as source of truth.",
            "body": (
                "# Menemory Supabase Backup\n\n"
                "## Workflow\n\n"
                "1. Confirm local state: `menemory status`\n"
                "2. Check env keys: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`\n"
                "3. Backup: `menemory backup push`\n"
                "4. Restore: `menemory backup pull --session-id <id>`\n"
            ),
            "scripts": {
                "backup_cycle.sh": (
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    "menemory status\n"
                    "menemory backup push\n"
                    "echo \"Backup done\"\n"
                )
            },
            "prompt": "Run a menemory backup/restore readiness check for Supabase.",
        },
        "menemory-start-guide": {
            "description": "Guide first-time command order for menemory from start through status checks.",
            "body": (
                "# Menemory Start Guide\n\n"
                "## Recommended Order\n\n"
                "1. `menemory --help`\n"
                "2. `menemory start --session-id dev-YYYY-MM-DD`\n"
                "3. `menemory ask \"...\" --cmd \"codex\"`\n"
                "4. `menemory status`\n"
                "5. `menemory where`\n"
            ),
            "scripts": {
                "start_guide.sh": (
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    "SESSION_ID=\"${1:-dev-$(date +%F)}\"\n"
                    "menemory start --session-id \"$SESSION_ID\"\n"
                    "menemory status\n"
                    "menemory where\n"
                )
            },
            "prompt": "Teach me the first-run menemory command order.",
        },
    }


def ensure_default_skills(skills_root: Path, overwrite: bool = False) -> dict[str, object]:
    catalog = _skill_catalog()
    skills_root.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, str]] = []

    for name, spec in catalog.items():
        try:
            description = str(spec["description"])
            body = str(spec["body"])
            scripts = dict(spec.get("scripts", {}))
            prompt = str(spec.get("prompt", "Guide me through this menemory workflow."))

            skill_dir = skills_root / name
            scripts_dir = skill_dir / "scripts"
            refs_dir = skill_dir / "references"
            agents_dir = skill_dir / "agents"
            skill_dir.mkdir(parents=True, exist_ok=True)
            scripts_dir.mkdir(parents=True, exist_ok=True)
            refs_dir.mkdir(parents=True, exist_ok=True)
            agents_dir.mkdir(parents=True, exist_ok=True)

            existed_before = (skill_dir / "SKILL.md").exists()

            files_to_write: dict[Path, str] = {
                skill_dir / "SKILL.md": _skill_header(name=name, description=description) + body,
                agents_dir / "openai.yaml": _skill_openai_yaml(
                    name=name.replace("-", " ").title(),
                    short_description=description,
                    default_prompt=prompt,
                ),
                refs_dir / "quickstart.md": (
                    f"# {name}\n\n"
                    "This skill was generated by `menemory init`.\n"
                    "Edit this file with team-specific examples.\n"
                ),
            }

            for script_name, script_content in scripts.items():
                files_to_write[scripts_dir / script_name] = str(script_content)

            if existed_before and not overwrite:
                skipped.append(name)
                continue

            for file_path, content in files_to_write.items():
                file_path.write_text(content, encoding="utf-8")
                if file_path.parent.name == "scripts":
                    file_path.chmod(0o755)

            if existed_before:
                updated.append(name)
            else:
                created.append(name)
        except OSError as exc:
            errors.append({"skill": name, "error": str(exc)})

    return {
        "skills_root": str(skills_root),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "ok": not errors,
    }
