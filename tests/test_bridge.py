from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from omi_codex_bridge.config import BridgeConfig
from omi_codex_bridge.main import create_app
from omi_codex_bridge.parser import extract_codex_prompt
from omi_codex_bridge.runner import MockRunner
from omi_codex_bridge.runner import CodexRunner
from omi_codex_bridge.storage import BridgeStorage


def make_config(
    tmp_path: Path,
    autorun: bool = False,
    phone_status_updates: bool = False,
    trusted_uids: tuple[str, ...] = (),
    autorun_requires_trusted_uid: bool = True,
) -> BridgeConfig:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return BridgeConfig(
        token="test-token",
        runtime_dir=tmp_path / "runtime",
        database_path=tmp_path / "runtime" / "bridge.db",
        default_workspace=workspace,
        allowed_workspaces=[workspace],
        autorun=autorun,
        runner_mode="mock",
        codex_timeout_seconds=30,
        phone_status_updates=phone_status_updates,
        trusted_uids=trusted_uids,
        autorun_requires_trusted_uid=autorun_requires_trusted_uid,
    )


def make_client(
    tmp_path: Path,
    autorun: bool = False,
    phone_status_updates: bool = False,
    trusted_uids: tuple[str, ...] = (),
    autorun_requires_trusted_uid: bool = True,
) -> TestClient:
    config = make_config(
        tmp_path,
        autorun=autorun,
        phone_status_updates=phone_status_updates,
        trusted_uids=trusted_uids,
        autorun_requires_trusted_uid=autorun_requires_trusted_uid,
    )
    storage = BridgeStorage(":memory:")
    runner = MockRunner(storage, config)
    return TestClient(create_app(config=config, storage=storage, runner=runner))


def test_trigger_parser_extracts_voice_prompt() -> None:
    assert extract_codex_prompt("Hey Omi Codex build a todo app") == "build a todo app"
    assert extract_codex_prompt("Please tell Codex to fix the failing tests") == "fix the failing tests"
    assert extract_codex_prompt("Ask Codex to write exactly: done.") == "write exactly: done."
    assert extract_codex_prompt("Codex fix the failing tests") == "fix the failing tests"
    assert extract_codex_prompt("Hej Omi kodeks napraw aplikację") == "napraw aplikację"
    assert extract_codex_prompt("Poproś kodeks żeby sprawdził połączenie z Obsidianem") == "sprawdził połączenie z Obsidianem"
    assert extract_codex_prompt("Kodeks proszę połącz telefon z mostem") == "połącz telefon z mostem"
    assert extract_codex_prompt("Omi to jest do ciebie popraw bridge") == "popraw bridge"
    assert extract_codex_prompt("Powiedz Codexowi żeby uruchomił testy") == "uruchomił testy"
    assert extract_codex_prompt("Hej Omi powiedz Codex zeby otworzyl plik z pulpitu") == "otworzyl plik z pulpitu"
    assert extract_codex_prompt("normal meeting transcript") is None


def test_tokenized_routes_protect_jobs(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    assert client.get("/health").json()["status"] == "healthy"
    assert client.get("/health/quick").json()["status"] == "healthy"
    assert client.get("/omi/wrong-token/api/jobs").status_code == 404
    assert client.get("/omi/test-token/api/jobs").json() == {"jobs": []}


def test_codex_prompt_points_jobs_to_memory_map(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    storage = BridgeStorage(":memory:")
    job, _ = storage.create_job("u1", "test", "make the bridge better", str(config.default_workspace))
    prompt = CodexRunner(storage, config).build_prompt(job)
    assert "Local Omi bridge map:" in prompt
    assert "Obsidian project memory index:" in prompt
    assert "make the bridge better" in prompt


def test_realtime_webhook_queues_job_and_dedupes(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    payload = [
        {
            "text": "Hey Omi Codex build a dashboard for this project",
            "speaker": "SPEAKER_00",
            "speakerId": 0,
            "is_user": True,
            "start": 0,
            "end": 4,
        }
    ]

    first = client.post("/omi/test-token/webhooks/realtime", params={"uid": "u1", "session_id": "s1"}, json=payload).json()
    second = client.post("/omi/test-token/webhooks/realtime", params={"uid": "u1", "session_id": "s1"}, json=payload).json()

    assert first["job_id"] == "job-1"
    assert first["message"].startswith("Sent to Codex on this PC as job-1")
    assert second["job_id"] == "job-1"
    jobs = client.get("/omi/test-token/api/jobs").json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["prompt"] == "build a dashboard for this project"


def test_realtime_webhook_accepts_loose_transcript_payloads(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post(
        "/omi/test-token/webhooks/realtime",
        params={"uid": "u1"},
        json={"transcript": "Omi to jest do ciebie popraw aplikację"},
    ).json()
    assert response["job_id"] == "job-1"
    job = client.get("/omi/test-token/api/jobs/job-1").json()["job"]
    assert job["prompt"] == "popraw aplikację"


def test_autorun_requires_trusted_uid_when_enabled(tmp_path: Path) -> None:
    client = make_client(tmp_path, autorun=True, trusted_uids=("owner",))
    response = client.post(
        "/omi/test-token/tools/start_codex_task",
        json={
            "uid": "stranger",
            "app_id": "omi_codex_bridge",
            "tool_name": "start_codex_task",
            "prompt": "Create trusted uid smoke test",
            "run_immediately": True,
        },
    ).json()

    assert "not trusted for autorun" in response["result"]
    job = client.get("/omi/test-token/api/jobs/job-1").json()["job"]
    assert job["status"] == "pending"


def test_autorun_starts_for_trusted_uid(tmp_path: Path) -> None:
    client = make_client(tmp_path, autorun=True, trusted_uids=("owner",))
    response = client.post(
        "/omi/test-token/tools/start_codex_task",
        json={
            "uid": "owner",
            "app_id": "omi_codex_bridge",
            "tool_name": "start_codex_task",
            "prompt": "Create trusted uid smoke test",
            "run_immediately": True,
        },
    ).json()

    assert "Started now" in response["result"]
    for _ in range(20):
        job = client.get("/omi/test-token/api/jobs/job-1").json()["job"]
        if job["status"] == "succeeded":
            break
        time.sleep(0.05)
    assert job["status"] == "succeeded"


def test_trusted_uid_still_queues_when_immediate_run_is_not_requested(tmp_path: Path) -> None:
    client = make_client(tmp_path, autorun=True, trusted_uids=("owner",))
    response = client.post(
        "/omi/test-token/tools/start_codex_task",
        json={
            "uid": "owner",
            "app_id": "omi_codex_bridge",
            "tool_name": "start_codex_task",
            "prompt": "Create trusted uid queued smoke test",
        },
    ).json()

    assert "Say run next Codex job" in response["result"]
    job = client.get("/omi/test-token/api/jobs/job-1").json()["job"]
    assert job["status"] == "pending"


def test_realtime_webhook_prefers_user_segments(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    payload = {
        "segments": [
            {"text": "someone said Codex build a random thing", "is_user": False},
            {"text": "Powiedz Codexowi żeby naprawił bridge", "is_user": True},
        ]
    }
    response = client.post("/omi/test-token/webhooks/realtime", params={"uid": "u1"}, json=payload).json()
    assert response["job_id"] == "job-1"
    job = client.get("/omi/test-token/api/jobs/job-1").json()["job"]
    assert job["prompt"] == "naprawił bridge"


def test_realtime_webhook_ignores_non_trigger_transcript(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    payload = [{"text": "We should discuss the roadmap", "is_user": True, "start": 0, "end": 2}]
    response = client.post("/omi/test-token/webhooks/realtime", params={"uid": "u1"}, json=payload).json()
    assert response["message"] == ""
    assert client.get("/omi/test-token/api/jobs").json()["jobs"] == []


def test_chat_tool_queues_job(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post(
        "/omi/test-token/tools/start_codex_task",
        json={
            "uid": "u1",
            "app_id": "omi_codex_bridge",
            "tool_name": "start_codex_task",
            "prompt": "Create a README section for the bridge",
        },
    ).json()
    assert "job-1" in response["result"]
    job = client.get("/omi/test-token/api/jobs/job-1").json()["job"]
    assert job["source"] == "omi-chat-tool"


def test_manifest_exposes_full_job_control_tools(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    manifest = client.get("/omi/test-token/.well-known/omi-tools.json").json()
    names = {tool["name"] for tool in manifest["tools"]}
    assert manifest["chat_messages"] == {"enabled": True, "target": "app", "notify": False}
    assert {
        "ask_codex",
        "start_codex_task",
        "open_desktop_file",
        "show_on_android",
        "check_phone_status",
        "quick_codex_task",
        "run_codex_job",
        "run_next_codex_job",
        "list_codex_jobs",
        "get_codex_job",
        "get_codex_job_output",
        "cancel_codex_job",
        "retry_codex_job",
        "check_bridge_status",
    }.issubset(names)


def test_open_desktop_file_tool_creates_safe_demo(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OMI_CODEX_DISABLE_OPEN", "1")
    monkeypatch.setenv("OMI_CODEX_DESKTOP_DIR", str(tmp_path / "Desktop"))
    client = make_client(tmp_path)
    response = client.post(
        "/omi/test-token/tools/open_desktop_file",
        json={"uid": "u1", "app_id": "omi_codex_bridge", "tool_name": "open_desktop_file"},
    ).json()
    assert response["result"].startswith("Opened desktop file on this PC")
    assert Path(response["path"]).name == "omi-codex-open-test.txt"


def test_realtime_desktop_open_runs_immediately(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OMI_CODEX_DISABLE_OPEN", "1")
    monkeypatch.setenv("OMI_CODEX_DESKTOP_DIR", str(tmp_path / "Desktop"))
    client = make_client(tmp_path)
    response = client.post(
        "/omi/test-token/webhooks/realtime",
        params={"uid": "u1"},
        json={"transcript": "Hej Omi powiedz Codex zeby otworzyl na moim komputerze teraz jakis plik z pulpitu obojetne"},
    ).json()
    assert response["action"] == "open_desktop_file"
    assert response["message"].startswith("Opened desktop file on this PC")
    assert client.get("/omi/test-token/api/jobs").json()["jobs"] == []


def test_realtime_show_android_runs_immediately(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OMI_ANDROID_DRY_RUN", "1")
    client = make_client(tmp_path)
    response = client.post(
        "/omi/test-token/webhooks/realtime",
        params={"uid": "u1"},
        json={"transcript": "Powiedz Codexowi zeby pokazal na telefonie: test z komputera"},
    ).json()
    assert response["action"] == "show_on_android"
    assert response["delivery"] == "dry_run"
    assert response["message"] == "Shown on Android: Codex"
    assert client.get("/omi/test-token/api/jobs").json()["jobs"] == []


def test_show_on_android_tool_dry_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OMI_ANDROID_DRY_RUN", "1")
    client = make_client(tmp_path)
    response = client.post(
        "/omi/test-token/tools/show_on_android",
        json={
            "uid": "u1",
            "app_id": "omi_codex_bridge",
            "tool_name": "show_on_android",
            "title": "Codex",
            "message": "Hello phone",
        },
    ).json()
    assert response["result"] == "Shown on Android: Codex"
    assert response["message"] == "Hello phone"
    assert response["delivery"] == "dry_run"


def test_check_phone_status_tool_reports_quiet_ready(tmp_path: Path, monkeypatch) -> None:
    def fake_android_status(config, include_power=True, include_guards=True):
        return {
            "adb_found": True,
            "available": True,
            "target": "usb-1",
            "transport": "usb",
            "quiet_ready": True,
            "power": {"wakefulness": "Dozing"},
            "wake_guards": {"wake_guards_disabled": True},
        }

    monkeypatch.setattr("omi_codex_bridge.main.android_status", fake_android_status)
    client = make_client(tmp_path)
    response = client.post(
        "/omi/test-token/tools/check_phone_status",
        json={"uid": "u1", "app_id": "omi_codex_bridge", "tool_name": "check_phone_status"},
    ).json()
    assert "Phone channel ready on usb-1" in response["result"]
    assert "Quiet mode: yes" in response["result"]


def test_known_uids_capture_non_job_tool_calls(tmp_path: Path, monkeypatch) -> None:
    def fake_android_status(config, include_power=True, include_guards=True):
        return {
            "adb_found": True,
            "available": True,
            "target": "usb-1",
            "transport": "usb",
            "quiet_ready": True,
            "power": {"wakefulness": "Dozing"},
            "wake_guards": {"wake_guards_disabled": True},
        }

    monkeypatch.setattr("omi_codex_bridge.main.android_status", fake_android_status)
    client = make_client(tmp_path)
    client.post(
        "/omi/test-token/tools/check_phone_status",
        json={"uid": "real-omi-user", "app_id": "omi_codex_bridge", "tool_name": "check_phone_status"},
    )

    known = client.get("/omi/test-token/api/known-uids").json()["known_uids"]

    assert known[0]["uid"] == "real-omi-user"
    assert "check_phone_status" in known[0]["sources"]


def test_known_uids_marks_trusted_uids(tmp_path: Path) -> None:
    client = make_client(tmp_path, trusted_uids=("real-omi-user",))
    client.post(
        "/omi/test-token/tools/list_codex_jobs",
        json={"uid": "real-omi-user", "app_id": "omi_codex_bridge", "tool_name": "list_codex_jobs", "limit": 5},
    )

    response = client.get("/omi/test-token/api/known-uids").json()

    assert response["trusted_uid_count"] == 1
    assert response["known_uids"][0]["uid"] == "real-omi-user"
    assert response["known_uids"][0]["trusted"] is True


def test_phone_status_updates_are_delivered_without_expanding_notifications(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OMI_ANDROID_DRY_RUN", "1")
    client = make_client(tmp_path, phone_status_updates=True)
    response = client.post(
        "/omi/test-token/tools/start_codex_task",
        json={
            "uid": "u1",
            "app_id": "omi_codex_bridge",
            "tool_name": "start_codex_task",
            "prompt": "Create a README section for phone status",
        },
    ).json()
    assert response["phone_status"] == "dry_run"
    events = client.get("/omi/test-token/api/events").json()["events"]
    assert any(event["kind"] == "phone.notified" for event in events)


def test_quick_codex_task_queues_template(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post(
        "/omi/test-token/tools/quick_codex_task",
        json={
            "uid": "u1",
            "app_id": "omi_codex_bridge",
            "tool_name": "quick_codex_task",
            "task_type": "fix",
            "details": "repair the bridge tests",
        },
    ).json()
    assert "job-1" in response["result"]
    job = client.get("/omi/test-token/api/jobs/job-1").json()["job"]
    assert job["source"] == "omi-quick-fix"
    assert "Find and fix" in job["prompt"]
    assert "repair the bridge tests" in job["prompt"]


def test_memory_webhook_queues_codex_command(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    payload = {
        "id": "memory-1",
        "structured": {
            "title": "Build request",
            "overview": "User said: ask Codex to add a backup script",
            "action_items": [{"description": "Codex create a backup script for the project"}],
        },
        "transcript_segments": [{"text": "Please ask Codex to add a backup script", "is_user": True}],
    }
    response = client.post("/omi/test-token/webhooks/memory", params={"uid": "u1"}, json=payload).json()
    assert response["job_id"] == "job-1"
    assert response["message"].startswith("Sent memory request to Codex on this PC as job-1")
    job = client.get("/omi/test-token/api/jobs/job-1").json()["job"]
    assert job["source"] == "omi-memory"
    assert job["prompt"] == "add a backup script"


def test_job_control_tools_list_cancel_retry_and_run_next(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.post("/omi/test-token/api/jobs", json={"uid": "u1", "prompt": "write tests", "source": "test"})
    listed = client.post(
        "/omi/test-token/tools/list_codex_jobs",
        json={"uid": "u1", "app_id": "omi_codex_bridge", "tool_name": "list_codex_jobs", "limit": 5},
    ).json()
    assert "job-1 is pending" in listed["result"]

    cancelled = client.post(
        "/omi/test-token/tools/cancel_codex_job",
        json={"uid": "u1", "app_id": "omi_codex_bridge", "tool_name": "cancel_codex_job", "job_id": "job-1"},
    ).json()
    assert "cancelled" in cancelled["result"]

    retry = client.post(
        "/omi/test-token/tools/retry_codex_job",
        json={"uid": "u1", "app_id": "omi_codex_bridge", "tool_name": "retry_codex_job", "job_id": "job-1"},
    ).json()
    assert "job-2" in retry["result"]

    run_next = client.post(
        "/omi/test-token/tools/run_next_codex_job",
        json={"uid": "u1", "app_id": "omi_codex_bridge", "tool_name": "run_next_codex_job"},
    ).json()
    assert "job-2 started" in run_next["result"]

    for _ in range(20):
        job = client.get("/omi/test-token/api/jobs/job-2").json()["job"]
        if job["status"] == "succeeded":
            break
        time.sleep(0.05)
    assert job["status"] == "succeeded"

    output = client.post(
        "/omi/test-token/tools/get_codex_job_output",
        json={"uid": "u1", "app_id": "omi_codex_bridge", "tool_name": "get_codex_job_output", "job_id": "job-2"},
    ).json()
    assert "Mock Codex completed request" in output["result"]


def test_rejects_workspace_outside_allowlist(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post(
        "/omi/test-token/api/jobs",
        json={"uid": "u1", "prompt": "do something", "workspace": str(tmp_path.parent)},
    )
    assert response.status_code == 400


def test_mock_runner_completes_job(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.post("/omi/test-token/api/jobs", json={"uid": "u1", "prompt": "write tests", "source": "test"})
    response = client.post("/omi/test-token/api/jobs/job-1/run").json()
    assert response["status"] == "started"

    for _ in range(20):
        job = client.get("/omi/test-token/api/jobs/job-1").json()["job"]
        if job["status"] == "succeeded":
            break
        time.sleep(0.05)

    assert job["status"] == "succeeded"
    assert job["output_path"].endswith("mock-codex-output.txt")
