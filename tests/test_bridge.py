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


def make_config(tmp_path: Path, autorun: bool = False) -> BridgeConfig:
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
    )


def make_client(tmp_path: Path, autorun: bool = False) -> TestClient:
    config = make_config(tmp_path, autorun=autorun)
    storage = BridgeStorage(":memory:")
    runner = MockRunner(storage, config)
    return TestClient(create_app(config=config, storage=storage, runner=runner))


def test_trigger_parser_extracts_voice_prompt() -> None:
    assert extract_codex_prompt("Hey Omi Codex build a todo app") == "build a todo app"
    assert extract_codex_prompt("Please tell Codex to fix the failing tests") == "fix the failing tests"
    assert extract_codex_prompt("Ask Codex to write exactly: done.") == "write exactly: done."
    assert extract_codex_prompt("normal meeting transcript") is None


def test_tokenized_routes_protect_jobs(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    assert client.get("/health").json()["status"] == "healthy"
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
    assert first["message"].startswith("Codex job job-1 queued")
    assert second["job_id"] == "job-1"
    jobs = client.get("/omi/test-token/api/jobs").json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["prompt"] == "build a dashboard for this project"


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
    assert {
        "start_codex_task",
        "run_codex_job",
        "run_next_codex_job",
        "list_codex_jobs",
        "get_codex_job",
        "get_codex_job_output",
        "cancel_codex_job",
        "retry_codex_job",
        "check_bridge_status",
    }.issubset(names)


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
    assert response["message"].startswith("Codex job job-1 queued from memory")
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
