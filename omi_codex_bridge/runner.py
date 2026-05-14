from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from .config import BridgeConfig
from .models import utc_now_iso
from .obsidian import ObsidianExporter
from .storage import BridgeStorage


class Runner(Protocol):
    def run(self, job_id: str) -> dict:
        ...


class CodexRunner:
    def __init__(self, storage: BridgeStorage, config: BridgeConfig) -> None:
        self.storage = storage
        self.config = config
        self.obsidian = ObsidianExporter(config)

    def build_prompt(self, job: dict) -> str:
        memory_index = self.config.runtime_dir / "OMI_AGENT_MAP.md"
        obsidian_index = Path(r"F:\programy\Obsidian\Codex Vault\Codex\Codex\Vibe Coding\omi-codex-bridge\index.md")
        return (
            "You were started by an Omi voice/chat command through the local Omi Codex Bridge.\n"
            "Work only in the configured workspace. Keep changes focused on the user request.\n"
            "Before editing, read the local Omi bridge map if it exists, then verify facts from source files.\n"
            f"Local Omi bridge map: {memory_index}\n"
            f"Obsidian project memory index: {obsidian_index}\n"
            "If you create durable setup knowledge, update the map or Obsidian-ready notes without storing secrets.\n"
            "Run relevant checks when practical, then summarize changed files and verification.\n\n"
            f"User request:\n{job['prompt']}\n"
        )

    def build_command(self, job: dict, last_message_path: Path) -> list[str]:
        codex_path = shutil.which("codex")
        if not codex_path:
            raise RuntimeError("codex CLI was not found on PATH.")
        return [
            codex_path,
            "exec",
            "-c",
            'approval_policy="never"',
            "-C",
            job["workspace"],
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "--output-last-message",
            str(last_message_path),
            "-",
        ]

    def run(self, job_id: str) -> dict:
        job = self.storage.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        if job["status"] not in {"pending", "failed"}:
            return job

        job_dir = self.config.runtime_dir / "jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = job_dir / "codex-output.txt"
        last_message_path = job_dir / "codex-last-message.txt"
        prompt = self.build_prompt(job)
        command = self.build_command(job, last_message_path)

        running_job = self.storage.update_job(
            job_id,
            status="running",
            started_at=utc_now_iso(),
            command_json=command,
            output_path=str(stdout_path),
            last_message_path=str(last_message_path),
            error=None,
        )
        self.storage.add_event(job_id, "job.running", "Codex CLI started.")
        self._export_job(running_job)

        try:
            process = subprocess.run(
                command,
                input=prompt,
                text=True,
                cwd=job["workspace"],
                capture_output=True,
                timeout=self.config.codex_timeout_seconds,
            )
            stdout_path.write_text(process.stdout + ("\n\nSTDERR:\n" + process.stderr if process.stderr else ""), encoding="utf-8")
            status = "succeeded" if process.returncode == 0 else "failed"
            updated = self.storage.update_job(
                job_id,
                status=status,
                exit_code=process.returncode,
                finished_at=utc_now_iso(),
                error=None if process.returncode == 0 else process.stderr[-2000:],
            )
            self.storage.add_event(job_id, f"job.{status}", f"Codex finished with exit code {process.returncode}.")
            self._export_job(updated)
            return updated
        except Exception as exc:
            updated = self.storage.update_job(job_id, status="failed", finished_at=utc_now_iso(), error=str(exc))
            self.storage.add_event(job_id, "job.failed", str(exc))
            self._export_job(updated)
            return updated

    def _export_job(self, job: dict) -> None:
        try:
            self.obsidian.export_job(job)
        except Exception as exc:
            self.storage.add_event(job["id"], "obsidian.export_failed", str(exc))


class MockRunner:
    def __init__(self, storage: BridgeStorage, config: BridgeConfig) -> None:
        self.storage = storage
        self.config = config
        self.obsidian = ObsidianExporter(config)

    def run(self, job_id: str) -> dict:
        job = self.storage.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        job_dir = self.config.runtime_dir / "jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        output_path = job_dir / "mock-codex-output.txt"
        output_path.write_text(f"Mock Codex completed request:\n{job['prompt']}\n", encoding="utf-8")
        self.storage.add_event(job_id, "job.running", "Mock runner started.")
        updated = self.storage.update_job(
            job_id,
            status="succeeded",
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            exit_code=0,
            output_path=str(output_path),
            command_json=["mock-codex"],
        )
        self.storage.add_event(job_id, "job.succeeded", "Mock runner completed.")
        try:
            self.obsidian.export_job(updated)
        except Exception as exc:
            self.storage.add_event(job_id, "obsidian.export_failed", str(exc))
        return updated
