from __future__ import annotations

import secrets
import shutil
import threading
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from .config import BridgeConfig
from .dashboard import render_dashboard
from .models import (
    CancelCodexJobRequest,
    CheckBridgeStatusRequest,
    GetCodexJobOutputRequest,
    GetCodexJobRequest,
    ListCodexJobsRequest,
    OpenDesktopFileRequest,
    QuickCodexTaskRequest,
    RetryCodexJobRequest,
    RunCodexJobRequest,
    RunNextCodexJobRequest,
    ShowOnAndroidRequest,
    StartCodexTaskRequest,
    TranscriptSegment,
)
from .parser import dedupe_key, extract_codex_prompt
from .obsidian import ObsidianExporter
from .runner import CodexRunner, MockRunner, Runner
from .storage import BridgeStorage


DESKTOP_OPEN_RE = re.compile(
    r"\b(?:open|show|otw[oó]rz|otworz|otworzy[lł]|poka[zż])\b.*\b(?:desktop|pulpit|pulpitu)\b|"
    r"\b(?:desktop|pulpit|pulpitu)\b.*\b(?:file|plik|pliku)\b",
    flags=re.IGNORECASE,
)

QUICK_TASK_TEMPLATES = {
    "build": "Build or create the requested thing. Keep it working end to end and verify it.",
    "create": "Create the requested file, component, script, document, or small project. Keep it focused and usable.",
    "fix": "Find and fix the bug or broken behavior. Verify the fix with the most relevant check.",
    "test": "Run or add relevant tests/checks for the request, then report the result.",
    "review": "Review the target for bugs, risks, missing tests, and concrete next fixes. Findings first.",
    "setup": "Set up the requested integration, app, plugin, repo, or local connection. Verify it works.",
    "android": "Work on the Android/phone side of the request using the available ADB/Omi bridge setup.",
    "obsidian": "Create or update the requested Obsidian/project-memory files without storing secrets.",
    "research": "Research the requested technical topic from authoritative sources and apply it to this workspace if useful.",
}


def create_app(
    config: BridgeConfig | None = None,
    storage: BridgeStorage | None = None,
    runner: Runner | None = None,
) -> FastAPI:
    config = config or BridgeConfig.from_env()
    config.runtime_dir.mkdir(parents=True, exist_ok=True)
    storage = storage or BridgeStorage(config.database_path)
    runner = runner or (MockRunner(storage, config) if config.runner_mode == "mock" else CodexRunner(storage, config))
    obsidian = ObsidianExporter(config)

    app = FastAPI(title="Omi Codex Bridge", version="0.1.0")
    app.state.config = config
    app.state.storage = storage
    app.state.runner = runner
    app.state.obsidian = obsidian

    try:
        obsidian.ensure_home()
    except Exception as exc:
        storage.add_event(None, "obsidian.export_failed", str(exc))

    def check_token(token: str) -> None:
        if not secrets.compare_digest(token, config.token):
            raise HTTPException(status_code=404, detail="Not found")

    def maybe_run(job_id: str) -> None:
        thread = threading.Thread(target=runner.run, args=(job_id,), daemon=True)
        thread.start()

    def health_payload() -> dict[str, Any]:
        return {
            "status": "healthy",
            "service": "omi-codex-bridge",
            "runner_mode": config.runner_mode,
            "autorun": config.autorun,
            "default_workspace": str(config.default_workspace),
            "allowed_workspaces": [str(path) for path in config.allowed_workspaces],
            "using_default_token": config.using_default_token,
            "codex_cli_found": shutil.which("codex") is not None,
            "queue_counts": storage.status_counts(),
            "obsidian": obsidian.status(),
            "omi_notifications": {
                "mode": config.omi_notification_mode,
                "api_configured": bool(config.omi_app_id and config.omi_app_secret),
                "chat_messages_enabled": config.omi_chat_messages_enabled,
                "chat_messages_target": config.omi_chat_messages_target,
                "chat_messages_notify": config.omi_chat_messages_notify,
            },
            "tailscale_expected": "Use Tailscale Funnel for Omi cloud webhooks; Serve is tailnet-only.",
        }

    def export_job_note(job: dict[str, Any]) -> str | None:
        try:
            path = obsidian.export_job(job)
            if path:
                storage.add_event(job["id"], "obsidian.job_saved", path)
            return path
        except Exception as exc:
            storage.add_event(job["id"], "obsidian.export_failed", str(exc))
            return None

    def export_memory_note(
        *,
        uid: str,
        memory_id: str,
        body: dict[str, Any],
        candidates: list[str],
        prompt: str | None,
        job: dict[str, Any] | None,
    ) -> str | None:
        try:
            path = obsidian.export_memory(
                uid=uid,
                memory_id=memory_id,
                memory=body,
                candidates=candidates,
                prompt=prompt,
                job=job,
            )
            if path:
                storage.add_event(job["id"] if job else None, "obsidian.memory_saved", path)
            return path
        except Exception as exc:
            storage.add_event(job["id"] if job else None, "obsidian.export_failed", str(exc))
            return None

    def export_realtime_note(
        *,
        uid: str,
        session_id: str,
        segments: list[TranscriptSegment],
        transcript: str,
        prompt: str,
        job: dict[str, Any],
        inserted: bool,
    ) -> str | None:
        try:
            path = obsidian.export_realtime(
                uid=uid,
                session_id=session_id,
                segments=segments,
                transcript=transcript,
                prompt=prompt,
                job=job,
                inserted=inserted,
            )
            if path:
                storage.add_event(job["id"], "obsidian.realtime_saved", path)
            return path
        except Exception as exc:
            storage.add_event(job["id"], "obsidian.export_failed", str(exc))
            return None

    def export_payload_note(*, kind: str, uid: str, body: dict[str, Any], title: str | None = None) -> str | None:
        try:
            path = obsidian.export_payload(kind=kind, uid=uid, payload=body, title=title)
            if path:
                storage.add_event(None, f"obsidian.{kind}_saved", path)
            return path
        except Exception as exc:
            storage.add_event(None, "obsidian.export_failed", str(exc))
            return None

    def job_brief(job: dict[str, Any]) -> str:
        prompt = " ".join(job["prompt"].split())
        if len(prompt) > 180:
            prompt = prompt[:177] + "..."
        return f"{job['id']} is {job['status']} from {job['source']}. Workspace: {job['workspace']}. Prompt: {prompt}"

    def job_detail(job: dict[str, Any]) -> str:
        prompt = " ".join(job["prompt"].split())
        if len(prompt) > 1200:
            prompt = prompt[:1197] + "..."
        return f"{job['id']} is {job['status']} from {job['source']}. Workspace: {job['workspace']}. Prompt: {prompt}"

    def read_job_output(job: dict[str, Any], max_chars: int = 4000) -> tuple[str, str | None]:
        limit = max(200, min(max_chars, 20000))
        for key in ("last_message_path", "output_path"):
            value = job.get(key)
            if not value:
                continue
            path = Path(value)
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                if len(text) > limit:
                    text = text[-limit:]
                    text = f"[last {limit} chars]\n{text}"
                return text, str(path)
        return "", None

    def schedule_existing_job(job_id: str, background: BackgroundTasks) -> dict[str, str]:
        job = storage.get_job(job_id)
        if not job:
            return {"error": f"Job {job_id} was not found."}
        if job["status"] == "running":
            return {"result": f"Codex job {job['id']} is already running."}
        if job["status"] == "cancelled":
            return {"error": f"Codex job {job['id']} is cancelled. Retry it to create a new job."}
        if job["status"] == "succeeded":
            return {"result": f"Codex job {job['id']} already succeeded. Use retry_codex_job if you want another run."}
        background.add_task(maybe_run, job["id"])
        return {"result": f"Codex job {job['id']} started."}

    def memory_candidate_texts(memory: dict[str, Any]) -> list[str]:
        structured = memory.get("structured") if isinstance(memory.get("structured"), dict) else {}
        action_items = structured.get("action_items") if isinstance(structured, dict) else []
        action_texts = [
            str(item.get("description", ""))
            for item in action_items
            if isinstance(item, dict) and item.get("description")
        ]
        transcript_segments = memory.get("transcript_segments") or memory.get("segments") or []
        transcript = " ".join(
            str(segment.get("text", ""))
            for segment in transcript_segments
            if isinstance(segment, dict) and segment.get("text")
        )
        parts = [
            transcript,
            *action_texts,
            str(structured.get("overview", "")) if isinstance(structured, dict) else "",
            str(structured.get("title", "")) if isinstance(structured, dict) else "",
        ]
        return [part.strip() for part in parts if part and part.strip()]

    def memory_text(memory: dict[str, Any]) -> str:
        return " ".join(memory_candidate_texts(memory))

    def desktop_path() -> Path:
        override = os.getenv("OMI_CODEX_DESKTOP_DIR")
        if override:
            return Path(override).expanduser().resolve()
        candidates = [
            Path.home() / "Desktop",
            Path.home() / "OneDrive" / "Desktop",
            Path.home() / "Pulpit",
            Path.home() / "OneDrive" / "Pulpit",
        ]
        return next((path for path in candidates if path.exists()), candidates[0])

    def is_desktop_open_request(prompt: str) -> bool:
        return bool(DESKTOP_OPEN_RE.search(prompt))

    def choose_desktop_file(query: str | None, create_demo_if_needed: bool = True) -> Path:
        desktop = desktop_path()
        desktop.mkdir(parents=True, exist_ok=True)
        normalized_query = " ".join((query or "").lower().split())
        vague = not normalized_query or any(word in normalized_query for word in ("jakis", "jakiś", "obojetne", "obojętne", "any", "random"))
        demo = desktop / "omi-codex-open-test.txt"
        if vague:
            if create_demo_if_needed and not demo.exists():
                demo.write_text("Omi Codex Bridge open-file smoke test.\n", encoding="utf-8")
            if demo.exists():
                return demo

        files = [path for path in desktop.iterdir() if path.is_file() and not path.name.startswith(".")]
        if normalized_query:
            words = [
                word
                for word in re.split(r"[^0-9a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ._-]+", normalized_query)
                if len(word) >= 3 and word not in {"plik", "pliku", "file", "desktop", "pulpit", "pulpitu", "otworz", "otwórz"}
            ]
            matches = [
                path
                for path in files
                if any(word.lower() in path.name.lower() for word in words)
            ]
            if matches:
                return sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)[0]

        if files:
            return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[0]
        if create_demo_if_needed:
            demo.write_text("Omi Codex Bridge open-file smoke test.\n", encoding="utf-8")
            return demo
        raise HTTPException(status_code=404, detail=f"No file found on desktop: {desktop}")

    def open_local_file(path: Path) -> None:
        if os.getenv("OMI_CODEX_DISABLE_OPEN", "").strip().lower() in {"1", "true", "yes", "on"}:
            return
        if not hasattr(os, "startfile"):
            raise HTTPException(status_code=501, detail="Opening local files is only supported on Windows.")
        os.startfile(str(path))  # type: ignore[attr-defined]

    def open_desktop_file(query: str | None, create_demo_if_needed: bool = True) -> dict[str, str]:
        path = choose_desktop_file(query, create_demo_if_needed)
        open_local_file(path)
        return {"result": f"Opened desktop file on this PC: {path.name}", "path": str(path)}

    def adb_prefix() -> list[str]:
        adb = shutil.which("adb")
        if not adb:
            raise HTTPException(status_code=503, detail="adb was not found on PATH.")
        serial = os.getenv("OMI_ANDROID_SERIAL", "").strip()
        if serial:
            return [adb, "-s", serial]
        devices = subprocess.run([adb, "devices", "-l"], text=True, capture_output=True, timeout=10)
        lines = [line for line in devices.stdout.splitlines() if "\tdevice" in line]
        if not lines:
            raise HTTPException(status_code=503, detail="No authorized Android device found.")
        usb = next((line for line in lines if not line.split()[0].count(".")), lines[0])
        return [adb, "-s", usb.split()[0]]

    def send_omi_notification(uid: str, message: str) -> dict[str, str]:
        if not config.omi_app_id or not config.omi_app_secret:
            raise HTTPException(status_code=503, detail="Omi app notification credentials are not configured.")
        url = f"{config.omi_api_base_url}/v2/integrations/{config.omi_app_id}/notification"
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    url,
                    params={"uid": uid, "message": message},
                    headers={"Authorization": f"Bearer {config.omi_app_secret}", "Content-Type": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Omi notification API is temporarily unreachable.") from exc
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail="Omi notification API rejected the request.")
        return {"result": "Sent through Omi notification API.", "delivery": "omi_api"}

    def show_on_android(uid: str, title: str, message: str, expand_notifications: bool = True) -> dict[str, str]:
        clean_title = " ".join((title or "Codex").split())[:80]
        clean_message = " ".join(message.split())[:2000]
        if len(clean_message) < 1:
            raise HTTPException(status_code=400, detail="Message is empty.")
        if os.getenv("OMI_ANDROID_DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"}:
            return {"result": f"Shown on Android: {clean_title}", "message": clean_message, "delivery": "dry_run"}
        omi_message = f"{clean_title}: {clean_message}" if clean_title else clean_message
        if config.omi_notification_mode in {"auto", "omi"} and config.omi_app_id and config.omi_app_secret:
            try:
                sent = send_omi_notification(uid, omi_message)
                return {"result": f"Shown through Omi: {clean_title}", "message": clean_message, **sent}
            except HTTPException as exc:
                if config.omi_notification_mode == "omi":
                    raise
                omi_warning = str(exc.detail)
            else:
                omi_warning = ""
        else:
            omi_warning = ""
        if config.omi_notification_mode == "omi":
            raise HTTPException(status_code=503, detail="Omi notification mode is enabled, but OMI_APP_ID/OMI_APP_SECRET are missing.")
        adb = adb_prefix()
        tag = "omi-codex"
        notification_command = " ".join(
            [
                "cmd",
                "notification",
                "post",
                "-S",
                "bigtext",
                "-t",
                shlex.quote(clean_title),
                shlex.quote(tag),
                shlex.quote(clean_message),
            ]
        )
        subprocess.run(
            [*adb, "shell", notification_command],
            text=True,
            capture_output=True,
            timeout=15,
            check=True,
        )
        if expand_notifications:
            subprocess.run([*adb, "shell", "cmd", "statusbar", "expand-notifications"], text=True, capture_output=True, timeout=10)
        response = {"result": f"Shown on Android: {clean_title}", "message": clean_message, "delivery": "adb"}
        if omi_warning:
            response["omi_warning"] = omi_warning
        return response

    def quick_prompt(task_type: str, details: str) -> str:
        normalized_type = re.sub(r"[^a-zA-Z0-9_-]+", "", task_type.strip().lower()) or "create"
        instruction = QUICK_TASK_TEMPLATES.get(normalized_type, QUICK_TASK_TEMPLATES["create"])
        return f"{instruction}\n\nUser details:\n{details.strip()}"

    def transcript_segments_from_body(body: Any) -> list[Any]:
        if isinstance(body, list):
            return body
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Expected transcript segment list or object with segments.")
        for key in ("segments", "transcript_segments"):
            value = body.get(key)
            if isinstance(value, list):
                return value
        transcript = body.get("transcript")
        if isinstance(transcript, list):
            return transcript
        if isinstance(transcript, str) and transcript.strip():
            return [{"text": transcript, "is_user": True}]
        text = body.get("text")
        if isinstance(text, str) and text.strip():
            return [body]
        return []

    def transcript_text_for_prompt(segments: list[TranscriptSegment]) -> str:
        user_text = " ".join(segment.text.strip() for segment in segments if segment.is_user and segment.text.strip())
        all_text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        return user_text or all_text

    @app.get("/", response_class=HTMLResponse)
    async def root() -> str:
        return """
        <!doctype html><title>Omi Codex Bridge</title>
        <body style="font-family: system-ui; padding: 32px">
          <h1>Omi Codex Bridge</h1>
          <p>Open the tokenized dashboard path:</p>
          <pre>/omi/YOUR_BRIDGE_TOKEN</pre>
        </body>
        """

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return health_payload()

    @app.get("/omi/{token}", response_class=HTMLResponse)
    async def dashboard(token: str) -> str:
        check_token(token)
        return render_dashboard(token, str(config.default_workspace), config.using_default_token)

    @app.get("/omi/{token}/setup-completed")
    async def setup_completed(token: str) -> dict[str, bool]:
        check_token(token)
        ready = not config.using_default_token and shutil.which("codex") is not None
        return {"is_setup_completed": ready}

    @app.get("/omi/{token}/.well-known/omi-tools.json")
    async def tools_manifest(token: str) -> dict[str, Any]:
        check_token(token)
        base = f"/omi/{token}"
        return {
            "tools": [
                {
                    "name": "ask_codex",
                    "description": (
                        "Primary tool for talking to Codex on the user's Windows PC. Use this whenever the user says Codex, Kodex, Kodeks, "
                        "agent, computer, assistant, you, do ciebie, or asks Omi to tell/ask Codex to build, fix, install, research, open files, "
                        "set up apps, control the local workspace, or continue coding work. This queues the request for the local Codex bridge."
                    ),
                    "endpoint": f"{base}/tools/start_codex_task",
                    "method": "POST",
                    "parameters": {
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": (
                                    "The user's full natural-language request for Codex. Preserve intent, paths, app names, and Polish or English wording."
                                ),
                            },
                            "workspace": {"type": "string", "description": "Optional local workspace path. Usually omit it."},
                            "run_immediately": {
                                "type": "boolean",
                                "description": "Set true only if the user clearly says to run/start now. The bridge may still queue for safety.",
                            },
                        },
                        "required": ["prompt"],
                    },
                    "auth_required": False,
                    "status_message": "Sending this to Codex on the PC...",
                },
                {
                    "name": "start_codex_task",
                    "description": (
                        "Queue a Codex coding task on the user's local machine. Use this when the user asks Codex, the assistant, or 'you' to build, "
                        "fix, refactor, test, research code, manage files, set up integrations, or operate the configured PC workspace."
                    ),
                    "endpoint": f"{base}/tools/start_codex_task",
                    "method": "POST",
                    "parameters": {
                        "properties": {
                            "prompt": {"type": "string", "description": "The complete request for Codex, not a summary."},
                            "workspace": {"type": "string", "description": "Optional local workspace path. Defaults to the configured workspace."},
                            "run_immediately": {"type": "boolean", "description": "Whether to run immediately. The bridge may still queue if autorun is disabled."},
                        },
                        "required": ["prompt"],
                    },
                    "auth_required": False,
                    "status_message": "Queuing this for Codex...",
                },
                {
                    "name": "open_desktop_file",
                    "description": (
                        "Open a file from the user's Windows Desktop on this PC. Use this when the user asks Codex/Omi/you to open, show, "
                        "or display a desktop/pulpit file now. If the user says any file is fine, omit query."
                    ),
                    "endpoint": f"{base}/tools/open_desktop_file",
                    "method": "POST",
                    "parameters": {
                        "properties": {
                            "query": {"type": "string", "description": "Optional file name or words to match on the Desktop."},
                            "create_demo_if_needed": {
                                "type": "boolean",
                                "description": "When true and no specific file is requested, create/open a harmless test text file.",
                            },
                        },
                        "required": [],
                    },
                    "auth_required": False,
                    "status_message": "Opening a desktop file on the PC...",
                },
                {
                    "name": "show_on_android",
                    "description": (
                        "Show a short message on the user's phone. Uses Omi's official notification API when app credentials are configured, "
                        "otherwise falls back to the connected Android device over ADB. Use this when the user asks to send, display, show, or push text/status/result to the phone."
                    ),
                    "endpoint": f"{base}/tools/show_on_android",
                    "method": "POST",
                    "parameters": {
                        "properties": {
                            "title": {"type": "string", "description": "Notification title. Defaults to Codex."},
                            "message": {"type": "string", "description": "Text to show on the Android phone."},
                            "expand_notifications": {"type": "boolean", "description": "Whether to open the notification shade after posting."},
                        },
                        "required": ["message"],
                    },
                    "auth_required": False,
                    "status_message": "Showing this on Android...",
                },
                {
                    "name": "quick_codex_task",
                    "description": (
                        "Fast preset for common Codex work. Use this for normal requests like build/create/fix/test/review/setup/android/obsidian/research "
                        "when the user wants Codex to do work but did not need a custom tool."
                    ),
                    "endpoint": f"{base}/tools/quick_codex_task",
                    "method": "POST",
                    "parameters": {
                        "properties": {
                            "task_type": {
                                "type": "string",
                                "description": "One of build, create, fix, test, review, setup, android, obsidian, research.",
                            },
                            "details": {"type": "string", "description": "The user's exact request/details."},
                            "workspace": {"type": "string", "description": "Optional local workspace path. Usually omit."},
                            "run_immediately": {"type": "boolean", "description": "Set true only if user clearly says to run now."},
                        },
                        "required": ["task_type", "details"],
                    },
                    "auth_required": False,
                    "status_message": "Preparing a Codex preset task...",
                },
                {
                    "name": "run_codex_job",
                    "description": "Run a queued Codex bridge job by id after the user explicitly approves it.",
                    "endpoint": f"{base}/tools/run_codex_job",
                    "method": "POST",
                    "parameters": {
                        "properties": {"job_id": {"type": "string", "description": "Job id such as job-1"}},
                        "required": ["job_id"],
                    },
                    "auth_required": False,
                    "status_message": "Starting queued Codex job...",
                },
                {
                    "name": "run_next_codex_job",
                    "description": "Run the oldest pending Codex bridge job. Use this when the user says to approve, start, or run the next queued Codex task without naming a job id.",
                    "endpoint": f"{base}/tools/run_next_codex_job",
                    "method": "POST",
                    "parameters": {
                        "properties": {
                            "status": {"type": "string", "description": "Queue status to select from. Defaults to pending."}
                        },
                        "required": [],
                    },
                    "auth_required": False,
                    "status_message": "Starting the next Codex job...",
                },
                {
                    "name": "list_codex_jobs",
                    "description": "List recent Codex bridge jobs and their statuses. Use this when the user asks what Codex is doing, what is queued, running, failed, or completed.",
                    "endpoint": f"{base}/tools/list_codex_jobs",
                    "method": "POST",
                    "parameters": {
                        "properties": {
                            "status": {"type": "string", "description": "Optional status filter: pending, running, succeeded, failed, or cancelled."},
                            "limit": {"type": "integer", "description": "Maximum number of jobs to return."},
                        },
                        "required": [],
                    },
                    "auth_required": False,
                    "status_message": "Checking Codex jobs...",
                },
                {
                    "name": "get_codex_job",
                    "description": "Read the status of a queued or completed Codex bridge job.",
                    "endpoint": f"{base}/tools/get_codex_job",
                    "method": "POST",
                    "parameters": {
                        "properties": {"job_id": {"type": "string", "description": "Job id such as job-1"}},
                        "required": ["job_id"],
                    },
                    "auth_required": False,
                    "status_message": "Checking Codex job...",
                },
                {
                    "name": "get_codex_job_output",
                    "description": "Read the final message or output log from a Codex bridge job. Use this when the user asks what Codex changed, what happened, or why a job failed.",
                    "endpoint": f"{base}/tools/get_codex_job_output",
                    "method": "POST",
                    "parameters": {
                        "properties": {
                            "job_id": {"type": "string", "description": "Job id such as job-1"},
                            "max_chars": {"type": "integer", "description": "Maximum characters of output to return."},
                        },
                        "required": ["job_id"],
                    },
                    "auth_required": False,
                    "status_message": "Reading Codex output...",
                },
                {
                    "name": "cancel_codex_job",
                    "description": "Cancel a pending Codex bridge job before it runs. Use this when the user wants to stop or remove a queued request.",
                    "endpoint": f"{base}/tools/cancel_codex_job",
                    "method": "POST",
                    "parameters": {
                        "properties": {"job_id": {"type": "string", "description": "Job id such as job-1"}},
                        "required": ["job_id"],
                    },
                    "auth_required": False,
                    "status_message": "Cancelling Codex job...",
                },
                {
                    "name": "retry_codex_job",
                    "description": "Create a fresh retry of a failed, cancelled, or completed Codex bridge job using the same prompt and workspace.",
                    "endpoint": f"{base}/tools/retry_codex_job",
                    "method": "POST",
                    "parameters": {
                        "properties": {
                            "job_id": {"type": "string", "description": "Job id such as job-1"},
                            "run_immediately": {"type": "boolean", "description": "Whether to run the retry immediately when bridge autorun is enabled."},
                        },
                        "required": ["job_id"],
                    },
                    "auth_required": False,
                    "status_message": "Retrying Codex job...",
                },
                {
                    "name": "check_bridge_status",
                    "description": "Check whether the local PC bridge, Codex CLI, cloud tunnel, queue, and safety settings are healthy. Use this if the user asks whether you are connected or working.",
                    "endpoint": f"{base}/tools/check_bridge_status",
                    "method": "POST",
                    "parameters": {"properties": {}, "required": []},
                    "auth_required": False,
                    "status_message": "Checking bridge status...",
                },
            ],
            "chat_messages": {
                "enabled": config.omi_chat_messages_enabled,
                "target": config.omi_chat_messages_target,
                "notify": config.omi_chat_messages_notify,
            },
        }

    @app.post("/omi/{token}/tools/start_codex_task")
    async def start_codex_task(token: str, payload: StartCodexTaskRequest, background: BackgroundTasks) -> dict[str, str]:
        check_token(token)
        try:
            workspace = str(config.normalize_workspace(payload.workspace))
        except ValueError as exc:
            return {"error": str(exc)}
        job, inserted = storage.create_job(payload.uid, "omi-chat-tool", payload.prompt, workspace)
        note_path = export_job_note(job)
        if inserted and payload.run_immediately and config.autorun:
            background.add_task(maybe_run, job["id"])
        status = "queued" if inserted else "already queued"
        run_hint = " It will run after approval from the bridge dashboard." if not config.autorun else ""
        response = {"result": f"Sent to Codex on the PC as {job['id']}: {status}.{run_hint}"}
        if note_path:
            response["obsidian_note"] = note_path
        return response

    @app.post("/omi/{token}/tools/open_desktop_file")
    async def open_desktop_file_tool(token: str, payload: OpenDesktopFileRequest) -> dict[str, str]:
        check_token(token)
        return open_desktop_file(payload.query, payload.create_demo_if_needed)

    @app.post("/omi/{token}/tools/show_on_android")
    async def show_on_android_tool(token: str, payload: ShowOnAndroidRequest) -> dict[str, str]:
        check_token(token)
        return show_on_android(payload.uid, payload.title, payload.message, payload.expand_notifications)

    @app.post("/omi/{token}/tools/quick_codex_task")
    async def quick_codex_task(token: str, payload: QuickCodexTaskRequest, background: BackgroundTasks) -> dict[str, str]:
        check_token(token)
        try:
            workspace = str(config.normalize_workspace(payload.workspace))
        except ValueError as exc:
            return {"error": str(exc)}
        prompt = quick_prompt(payload.task_type, payload.details)
        job, inserted = storage.create_job(payload.uid, f"omi-quick-{payload.task_type}", prompt, workspace)
        note_path = export_job_note(job)
        if inserted and payload.run_immediately and config.autorun:
            background.add_task(maybe_run, job["id"])
        status = "queued" if inserted else "already queued"
        response = {"result": f"Quick Codex task {job['id']} {status}: {payload.task_type}"}
        if note_path:
            response["obsidian_note"] = note_path
        return response

    @app.post("/omi/{token}/tools/run_codex_job")
    async def run_codex_job_tool(token: str, payload: RunCodexJobRequest, background: BackgroundTasks) -> dict[str, str]:
        check_token(token)
        return schedule_existing_job(payload.job_id, background)

    @app.post("/omi/{token}/tools/run_next_codex_job")
    async def run_next_codex_job_tool(token: str, payload: RunNextCodexJobRequest, background: BackgroundTasks) -> dict[str, str]:
        check_token(token)
        status = payload.status or "pending"
        job = storage.first_job_with_status(status)
        if not job:
            return {"result": f"No {status} Codex jobs are waiting."}
        return schedule_existing_job(job["id"], background)

    @app.post("/omi/{token}/tools/list_codex_jobs")
    async def list_codex_jobs_tool(token: str, payload: ListCodexJobsRequest) -> dict[str, str]:
        check_token(token)
        jobs = storage.list_jobs(payload.limit, payload.status)
        if not jobs:
            suffix = f" with status {payload.status}" if payload.status else ""
            return {"result": f"No Codex jobs{suffix}."}
        lines = [job_brief(job) for job in jobs]
        return {"result": "\n".join(lines)}

    @app.post("/omi/{token}/tools/get_codex_job")
    async def get_codex_job_tool(token: str, payload: GetCodexJobRequest) -> dict[str, str]:
        check_token(token)
        job = storage.get_job(payload.job_id)
        if not job:
            return {"error": f"Job {payload.job_id} was not found."}
        events = storage.list_events(job["id"], 5)
        output, output_path = read_job_output(job, 1200)
        event_text = "; ".join(f"{event['kind']}: {event['message']}" for event in reversed(events))
        output_hint = f" Output from {output_path}: {output[:1200]}" if output else ""
        return {"result": f"{job_detail(job)} Exit code: {job['exit_code']}. Events: {event_text or 'none yet'}.{output_hint}"}

    @app.post("/omi/{token}/tools/get_codex_job_output")
    async def get_codex_job_output_tool(token: str, payload: GetCodexJobOutputRequest) -> dict[str, str]:
        check_token(token)
        job = storage.get_job(payload.job_id)
        if not job:
            return {"error": f"Job {payload.job_id} was not found."}
        output, output_path = read_job_output(job, payload.max_chars)
        if not output:
            return {"result": f"No output is available yet for {job['id']}."}
        return {"result": f"Output for {job['id']} from {output_path}:\n{output}"}

    @app.post("/omi/{token}/tools/cancel_codex_job")
    async def cancel_codex_job_tool(token: str, payload: CancelCodexJobRequest) -> dict[str, str]:
        check_token(token)
        try:
            job = storage.cancel_job(payload.job_id)
        except KeyError:
            return {"error": f"Job {payload.job_id} was not found."}
        except ValueError as exc:
            return {"error": str(exc)}
        export_job_note(job)
        return {"result": f"Codex job {job['id']} is {job['status']}."}

    @app.post("/omi/{token}/tools/retry_codex_job")
    async def retry_codex_job_tool(token: str, payload: RetryCodexJobRequest, background: BackgroundTasks) -> dict[str, str]:
        check_token(token)
        try:
            job = storage.retry_job(payload.job_id)
        except KeyError:
            return {"error": f"Job {payload.job_id} was not found."}
        except ValueError as exc:
            return {"error": str(exc)}
        note_path = export_job_note(job)
        if payload.run_immediately and config.autorun:
            background.add_task(maybe_run, job["id"])
        run_hint = " It will run after approval from the bridge dashboard." if not config.autorun else ""
        response = {"result": f"Retry queued as Codex job {job['id']}.{run_hint}"}
        if note_path:
            response["obsidian_note"] = note_path
        return response

    @app.post("/omi/{token}/tools/check_bridge_status")
    async def check_bridge_status_tool(token: str, payload: CheckBridgeStatusRequest) -> dict[str, str]:
        check_token(token)
        status = health_payload()
        counts = ", ".join(f"{key}: {value}" for key, value in sorted(status["queue_counts"].items())) or "none"
        token_warning = " Default token is still active." if status["using_default_token"] else ""
        codex_state = "found" if status["codex_cli_found"] else "not found"
        obsidian_state = "on" if status["obsidian"]["active"] else "off"
        omi_notify = status["omi_notifications"]
        omi_notify_state = "api" if omi_notify["api_configured"] else "adb fallback"
        return {
            "result": (
                f"Omi Codex Bridge is {status['status']}. Codex CLI: {codex_state}. "
                f"Runner: {status['runner_mode']}. Autorun: {status['autorun']}. "
                f"Obsidian export: {obsidian_state}. Phone notify: {omi_notify_state}. Queue counts: {counts}.{token_warning}"
            )
        }

    @app.post("/omi/{token}/webhooks/realtime")
    async def realtime_webhook(
        token: str,
        request: Request,
        background: BackgroundTasks,
        uid: str = Query(...),
        session_id: str | None = Query(None),
    ) -> dict[str, Any]:
        check_token(token)
        body = await request.json()
        raw_segments = transcript_segments_from_body(body)
        active_session_id = session_id or (body.get("session_id") if isinstance(body, dict) else None) or f"{uid}-default"

        segments = [TranscriptSegment.model_validate(segment) for segment in raw_segments]
        transcript = transcript_text_for_prompt(segments)
        prompt = extract_codex_prompt(transcript)
        if not prompt:
            return {"session_id": active_session_id, "message": "", "accepted_segments": len(segments)}
        if is_desktop_open_request(prompt):
            opened = open_desktop_file(prompt)
            return {
                "session_id": active_session_id,
                "accepted_segments": len(segments),
                "message": opened["result"],
                "action": "open_desktop_file",
                "path": opened["path"],
            }

        workspace = str(config.default_workspace)
        key = dedupe_key(uid, active_session_id, prompt)
        job, inserted = storage.create_job(
            uid,
            "omi-realtime",
            prompt,
            workspace,
            dedupe_key=key,
            session_id=active_session_id,
            transcript_context=transcript,
        )
        job_note_path = export_job_note(job)
        realtime_note_path = export_realtime_note(
            uid=uid,
            session_id=active_session_id,
            segments=segments,
            transcript=transcript,
            prompt=prompt,
            job=job,
            inserted=inserted,
        )
        if inserted and config.autorun:
            background.add_task(maybe_run, job["id"])
        action = "queued" if inserted else "already queued"
        response = {
            "session_id": active_session_id,
            "accepted_segments": len(segments),
            "message": f"Sent to Codex on this PC as {job['id']}: {action}. Open the bridge dashboard or say run next Codex job.",
            "job_id": job["id"],
            "status": job["status"],
        }
        if realtime_note_path:
            response["obsidian_note"] = realtime_note_path
        if job_note_path:
            response["obsidian_job_note"] = job_note_path
        return response

    @app.post("/omi/{token}/webhooks/memory")
    async def memory_webhook(
        token: str,
        request: Request,
        background: BackgroundTasks,
        uid: str = Query(...),
    ) -> dict[str, Any]:
        check_token(token)
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Expected an Omi memory object.")

        candidates = memory_candidate_texts(body)
        text = " ".join(candidates)
        prompt = next((candidate_prompt for candidate in candidates if (candidate_prompt := extract_codex_prompt(candidate))), None)
        memory_id = str(body.get("id") or body.get("memory_id") or "memory")
        if not prompt:
            note_path = export_memory_note(
                uid=uid,
                memory_id=memory_id,
                body=body,
                candidates=candidates,
                prompt=None,
                job=None,
            )
            response = {"memory_id": memory_id, "message": "", "accepted": True}
            if note_path:
                response["obsidian_note"] = note_path
            return response

        workspace = str(config.default_workspace)
        key = dedupe_key(uid, memory_id, prompt)
        job, inserted = storage.create_job(
            uid,
            "omi-memory",
            prompt,
            workspace,
            dedupe_key=key,
            transcript_context=text,
        )
        job_note_path = export_job_note(job)
        memory_note_path = export_memory_note(
            uid=uid,
            memory_id=memory_id,
            body=body,
            candidates=candidates,
            prompt=prompt,
            job=job,
        )
        if inserted and config.autorun:
            background.add_task(maybe_run, job["id"])
        action = "queued" if inserted else "already queued"
        response = {
            "memory_id": memory_id,
            "message": f"Sent memory request to Codex on this PC as {job['id']}: {action}.",
            "job_id": job["id"],
            "status": job["status"],
        }
        if memory_note_path:
            response["obsidian_note"] = memory_note_path
        if job_note_path:
            response["obsidian_job_note"] = job_note_path
        return response

    @app.post("/omi/{token}/webhooks/day-summary")
    async def day_summary_webhook(token: str, request: Request, uid: str = Query(...)) -> dict[str, Any]:
        check_token(token)
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Expected an Omi day summary object.")
        title = str(body.get("title") or body.get("date") or body.get("id") or "Day summary")
        note_path = export_payload_note(kind="day-summary", uid=uid, body=body, title=title)
        response = {"accepted": True, "message": "Day summary saved for Obsidian." if note_path else ""}
        if note_path:
            response["obsidian_note"] = note_path
        return response

    @app.get("/omi/{token}/api/jobs")
    async def api_jobs(token: str, limit: int = Query(50), status: str | None = Query(None)) -> dict[str, Any]:
        check_token(token)
        return {"jobs": storage.list_jobs(limit, status)}

    @app.post("/omi/{token}/api/jobs")
    async def api_create_job(token: str, payload: dict[str, Any]) -> dict[str, Any]:
        check_token(token)
        uid = str(payload.get("uid") or "dashboard")
        prompt = str(payload.get("prompt") or "").strip()
        if len(prompt) < 6:
            raise HTTPException(status_code=400, detail="Prompt is too short.")
        try:
            workspace = str(config.normalize_workspace(payload.get("workspace")))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        job, inserted = storage.create_job(uid, str(payload.get("source") or "dashboard"), prompt, workspace)
        note_path = export_job_note(job)
        response = {"job": job, "inserted": inserted}
        if note_path:
            response["obsidian_note"] = note_path
        return response

    @app.post("/omi/{token}/api/jobs/{job_id}/run")
    async def api_run_job(token: str, job_id: str, background: BackgroundTasks) -> dict[str, Any]:
        check_token(token)
        job = storage.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        result = schedule_existing_job(job_id, background)
        return {"status": "started" if "result" in result and "started" in result["result"] else job["status"], "job": job, "message": result}

    @app.get("/omi/{token}/api/jobs/{job_id}")
    async def api_get_job(token: str, job_id: str) -> dict[str, Any]:
        check_token(token)
        job = storage.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        return {"job": job, "events": storage.list_events(job_id)}

    @app.get("/omi/{token}/api/jobs/{job_id}/output")
    async def api_get_job_output(token: str, job_id: str, max_chars: int = Query(12000)) -> dict[str, Any]:
        check_token(token)
        job = storage.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        output, output_path = read_job_output(job, max_chars)
        return {"job_id": job["id"], "output_path": output_path, "output": output}

    @app.post("/omi/{token}/api/jobs/{job_id}/cancel")
    async def api_cancel_job(token: str, job_id: str) -> dict[str, Any]:
        check_token(token)
        try:
            job = storage.cancel_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        note_path = export_job_note(job)
        response = {"job": job}
        if note_path:
            response["obsidian_note"] = note_path
        return response

    @app.post("/omi/{token}/api/jobs/{job_id}/retry")
    async def api_retry_job(token: str, job_id: str, background: BackgroundTasks, run: bool = Query(False)) -> dict[str, Any]:
        check_token(token)
        try:
            job = storage.retry_job(job_id, source="dashboard-retry")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        note_path = export_job_note(job)
        if run and config.autorun:
            background.add_task(maybe_run, job["id"])
        response = {"job": job}
        if note_path:
            response["obsidian_note"] = note_path
        return response

    @app.get("/omi/{token}/api/events")
    async def api_events(token: str) -> dict[str, Any]:
        check_token(token)
        return {"events": storage.list_events()}

    @app.delete("/omi/{token}/api/reset")
    async def api_reset(token: str) -> dict[str, str]:
        check_token(token)
        storage.reset()
        return {"status": "reset"}

    return app


app = create_app()
