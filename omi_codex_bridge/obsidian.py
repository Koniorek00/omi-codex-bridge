from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from .config import BridgeConfig
from .models import TranscriptSegment, utc_now_iso


SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|authorization|cookie|api[_-]?key|oauth)", re.IGNORECASE)
SECRET_VALUE_RE = re.compile(
    r"(?i)\b(bearer\s+[a-z0-9._~+/=-]+|sk-[a-z0-9_-]+|xox[baprs]-[a-z0-9-]+)\b"
)


def _safe_slug(value: str, fallback: str = "item", max_length: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip(".-_").lower()
    return (slug or fallback)[:max_length].strip(".-_") or fallback


def _clip(value: str, limit: int = 12000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n...[clipped {len(value) - limit} chars]"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            result[key_text] = "[redacted]" if SENSITIVE_KEY_RE.search(key_text) else _redact(item)
        return result
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _clip(SECRET_VALUE_RE.sub("[redacted]", value))
    return value


def _json_block(value: Any) -> str:
    redacted = _redact(value)
    return "````json\n" + json.dumps(redacted, ensure_ascii=False, indent=2, default=str) + "\n````"


def _yaml_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _frontmatter(fields: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_yaml_string(item)}")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {_yaml_string(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


class ObsidianExporter:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self._lock = Lock()

    @property
    def active(self) -> bool:
        return self.config.obsidian_enabled and self.config.obsidian_vault_path is not None

    @property
    def vault_path(self) -> Path | None:
        return self.config.obsidian_vault_path

    @property
    def root_dir(self) -> Path | None:
        if not self.active or self.vault_path is None:
            return None
        return self.vault_path.joinpath(*self.config.obsidian_root.replace("\\", "/").split("/"))

    def _vault_link(self, relative_path: str, label: str) -> str:
        root = self.config.obsidian_root.strip("/\\").replace("\\", "/")
        clean_path = relative_path.strip("/\\")
        path = f"{root}/{clean_path}"
        return f"[[{path}|{label}]]"

    def status(self) -> dict[str, Any]:
        root = self.root_dir
        return {
            "enabled": self.config.obsidian_enabled,
            "active": self.active,
            "vault_path": str(self.vault_path) if self.vault_path else None,
            "root": self.config.obsidian_root,
            "root_path": str(root) if root else None,
            "root_exists": root.exists() if root else False,
        }

    def ensure_home(self) -> str | None:
        if not self.active:
            return None
        content = _frontmatter(
            {
                "type": "omi-obsidian-index",
                "source": "omi-codex-bridge",
                "status": "active",
                "updated": utc_now_iso(),
                "tags": ["omi", "obsidian", "codex-bridge"],
            }
        )
        content += (
            "# Omi Codex Bridge\n\n"
            "This folder is written by the local Omi Codex Bridge. Omi memories, realtime triggers, chat-tool requests, "
            "and Codex jobs are saved here as separate Markdown notes.\n\n"
            "## Folders\n"
            "- [[Memories]] stores completed Omi memories received by the memory webhook.\n"
            "- [[Realtime]] stores realtime transcript trigger captures.\n"
            "- [[Jobs]] stores queued and completed Codex bridge jobs.\n\n"
            "- [[Events]] stores other Omi payloads such as day summaries.\n\n"
            "## Safety\n"
            "Obvious tokens, cookies, passwords, API keys, and authorization values are redacted before raw payloads are written.\n"
        )
        return self._write("index.md", content)

    def export_job(self, job: dict[str, Any]) -> str | None:
        if not self.active:
            return None
        self.ensure_home()
        content = _frontmatter(
            {
                "type": "omi-codex-job",
                "source": job.get("source"),
                "job_id": job.get("id"),
                "uid": job.get("uid"),
                "status": job.get("status"),
                "session_id": job.get("session_id"),
                "created": job.get("created_at"),
                "updated": job.get("updated_at"),
                "tags": ["omi", "codex-job"],
            }
        )
        content += (
            f"# {job.get('id', 'Codex Job')}\n\n"
            f"- Status: `{job.get('status')}`\n"
            f"- Source: `{job.get('source')}`\n"
            f"- Workspace: `{job.get('workspace')}`\n"
            f"- Created: `{job.get('created_at')}`\n"
            f"- Updated: `{job.get('updated_at')}`\n"
            f"- Started: `{job.get('started_at')}`\n"
            f"- Finished: `{job.get('finished_at')}`\n"
            f"- Exit code: `{job.get('exit_code')}`\n\n"
            "## Prompt\n"
            f"{_clip(str(job.get('prompt') or '').strip())}\n\n"
        )
        transcript = str(job.get("transcript_context") or "").strip()
        if transcript:
            content += "## Omi Context\n" + _clip(transcript) + "\n\n"
        content += (
            "## Runtime Files\n"
            f"- Output: `{job.get('output_path')}`\n"
            f"- Last message: `{job.get('last_message_path')}`\n\n"
        )
        error = str(job.get("error") or "").strip()
        if error:
            content += "## Error\n```text\n" + _clip(error) + "\n```\n\n"
        return self._write(f"Jobs/{_safe_slug(str(job.get('id') or 'job'))}.md", content)

    def export_memory(
        self,
        *,
        uid: str,
        memory_id: str,
        memory: dict[str, Any],
        candidates: list[str],
        prompt: str | None,
        job: dict[str, Any] | None,
    ) -> str | None:
        if not self.active:
            return None
        self.ensure_home()
        now = datetime.now(timezone.utc)
        structured = memory.get("structured") if isinstance(memory.get("structured"), dict) else {}
        title = str(structured.get("title") or memory.get("title") or memory_id)
        filename = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{_safe_slug(memory_id)}.md"
        content = _frontmatter(
            {
                "type": "omi-memory",
                "source": "omi-codex-bridge",
                "uid": uid,
                "memory_id": memory_id,
                "job_id": job.get("id") if job else None,
                "created": utc_now_iso(),
                "tags": ["omi", "memory"],
            }
        )
        content += f"# {title}\n\n"
        overview = str(structured.get("overview") or memory.get("overview") or "").strip()
        if overview:
            content += "## Overview\n" + _clip(overview) + "\n\n"
        action_items = structured.get("action_items") if isinstance(structured, dict) else []
        if isinstance(action_items, list) and action_items:
            content += "## Action Items\n"
            for item in action_items:
                if isinstance(item, dict):
                    text = str(item.get("description") or item.get("text") or item)
                else:
                    text = str(item)
                content += f"- {_clip(text, 1000)}\n"
            content += "\n"
        if prompt:
            content += "## Codex Prompt Extracted\n" + _clip(prompt) + "\n\n"
        if job:
            job_id = str(job.get("id"))
            content += f"## Codex Job\n{self._vault_link(f'Jobs/{_safe_slug(job_id)}.md', job_id)}\n\n"
        if candidates:
            content += "## Candidate Texts\n"
            for candidate in candidates:
                content += f"- {_clip(candidate, 2000)}\n"
            content += "\n"
        content += "## Raw Payload\n" + _json_block(memory) + "\n"
        return self._write(f"Memories/{now.strftime('%Y-%m-%d')}/{filename}", content)

    def export_realtime(
        self,
        *,
        uid: str,
        session_id: str,
        segments: list[TranscriptSegment],
        transcript: str,
        prompt: str,
        job: dict[str, Any],
        inserted: bool,
    ) -> str | None:
        if not self.active:
            return None
        self.ensure_home()
        now = datetime.now(timezone.utc)
        filename = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{_safe_slug(session_id)}-{_safe_slug(str(job.get('id')))}.md"
        content = _frontmatter(
            {
                "type": "omi-realtime-trigger",
                "source": "omi-codex-bridge",
                "uid": uid,
                "session_id": session_id,
                "job_id": job.get("id"),
                "inserted": inserted,
                "created": utc_now_iso(),
                "tags": ["omi", "realtime", "codex-job"],
            }
        )
        content += (
            f"# Realtime {session_id}\n\n"
            f"- Job: {self._vault_link(f'Jobs/{_safe_slug(str(job.get('id')))}.md', str(job.get('id')))}\n"
            f"- Queue action: `{'queued' if inserted else 'already queued'}`\n"
            f"- Accepted segments: `{len(segments)}`\n\n"
            "## Codex Prompt Extracted\n"
            f"{_clip(prompt)}\n\n"
            "## Transcript Used For Prompt\n"
            f"{_clip(transcript)}\n\n"
            "## Segments\n"
        )
        for segment in segments:
            who = "user" if segment.is_user else "speaker"
            content += f"- `{segment.start:.2f}-{segment.end:.2f}` {who} `{segment.speaker}`: {_clip(segment.text, 1200)}\n"
        return self._write(f"Realtime/{now.strftime('%Y-%m-%d')}/{filename}", content)

    def export_payload(
        self,
        *,
        kind: str,
        uid: str,
        payload: dict[str, Any],
        title: str | None = None,
    ) -> str | None:
        if not self.active:
            return None
        self.ensure_home()
        now = datetime.now(timezone.utc)
        kind_slug = _safe_slug(kind)
        item_id = str(payload.get("id") or payload.get("summary_id") or payload.get("memory_id") or kind_slug)
        filename = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{_safe_slug(item_id)}.md"
        note_title = title or str(payload.get("title") or payload.get("date") or item_id)
        content = _frontmatter(
            {
                "type": f"omi-{kind_slug}",
                "source": "omi-codex-bridge",
                "uid": uid,
                "item_id": item_id,
                "created": utc_now_iso(),
                "tags": ["omi", kind_slug],
            }
        )
        content += f"# {note_title}\n\n"
        for key in ("overview", "summary", "text", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                content += f"## {key.replace('_', ' ').title()}\n{_clip(value.strip())}\n\n"
        content += "## Raw Payload\n" + _json_block(payload) + "\n"
        return self._write(f"Events/{kind_slug}/{now.strftime('%Y-%m-%d')}/{filename}", content)

    def _write(self, relative_path: str, content: str) -> str:
        if not self.active or self.vault_path is None:
            raise RuntimeError("Obsidian export is not configured.")
        root = self.root_dir
        if root is None:
            raise RuntimeError("Obsidian export root is not configured.")
        target = root / relative_path
        resolved_vault = self.vault_path.resolve()
        resolved_target = target.resolve()
        if resolved_target != resolved_vault and resolved_vault not in resolved_target.parents:
            raise ValueError(f"Refusing to write outside Obsidian vault: {target}")
        with self._lock:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return str(target.relative_to(self.vault_path)).replace("\\", "/")
