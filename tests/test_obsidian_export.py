from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from omi_codex_bridge.config import BridgeConfig
from omi_codex_bridge.main import create_app
from omi_codex_bridge.runner import MockRunner
from omi_codex_bridge.storage import BridgeStorage


def make_obsidian_client(tmp_path: Path) -> tuple[TestClient, Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    config = BridgeConfig(
        token="test-token",
        runtime_dir=tmp_path / "runtime",
        database_path=tmp_path / "runtime" / "bridge.db",
        default_workspace=workspace,
        allowed_workspaces=[workspace],
        autorun=False,
        runner_mode="mock",
        codex_timeout_seconds=30,
        obsidian_enabled=True,
        obsidian_vault_path=vault,
        obsidian_root="Codex/Omi Test",
    )
    storage = BridgeStorage(":memory:")
    runner = MockRunner(storage, config)
    return TestClient(create_app(config=config, storage=storage, runner=runner)), vault


def test_memory_webhook_writes_memory_and_job_notes(tmp_path: Path) -> None:
    client, vault = make_obsidian_client(tmp_path)
    payload = {
        "id": "memory-obsidian-1",
        "secret_token": "do-not-store-this",
        "structured": {
            "title": "Bridge memory",
            "overview": "Please ask Codex to add Obsidian export",
            "action_items": [{"description": "Codex add Obsidian export"}],
        },
    }

    response = client.post("/omi/test-token/webhooks/memory", params={"uid": "u1"}, json=payload).json()

    memory_note = vault / response["obsidian_note"]
    job_note = vault / response["obsidian_job_note"]
    assert memory_note.is_file()
    assert job_note.is_file()
    memory_text = memory_note.read_text(encoding="utf-8")
    assert "Codex add Obsidian export" in memory_text
    assert "do-not-store-this" not in memory_text
    assert "[redacted]" in memory_text
    assert "job-1" in job_note.read_text(encoding="utf-8")


def test_realtime_webhook_writes_trigger_capture(tmp_path: Path) -> None:
    client, vault = make_obsidian_client(tmp_path)
    payload = [{"text": "Hey Omi Codex write the Obsidian tests", "is_user": True, "start": 1, "end": 2}]

    response = client.post("/omi/test-token/webhooks/realtime", params={"uid": "u1", "session_id": "s1"}, json=payload).json()

    note = vault / response["obsidian_note"]
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    assert "write the Obsidian tests" in text
    assert "job-1" in text


def test_day_summary_webhook_writes_event_note(tmp_path: Path) -> None:
    client, vault = make_obsidian_client(tmp_path)
    payload = {"id": "summary-1", "date": "2026-05-14", "summary": "Finished Obsidian bridge wiring."}

    response = client.post("/omi/test-token/webhooks/day-summary", params={"uid": "u1"}, json=payload).json()

    note = vault / response["obsidian_note"]
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    assert "Finished Obsidian bridge wiring." in text


def test_mock_runner_updates_job_note_status(tmp_path: Path) -> None:
    client, vault = make_obsidian_client(tmp_path)
    created = client.post("/omi/test-token/api/jobs", json={"uid": "u1", "prompt": "write docs"}).json()
    note = vault / created["obsidian_note"]
    assert "pending" in note.read_text(encoding="utf-8")

    client.post("/omi/test-token/api/jobs/job-1/run")
    for _ in range(20):
        text = note.read_text(encoding="utf-8")
        if "succeeded" in text:
            break
        time.sleep(0.05)

    assert "succeeded" in note.read_text(encoding="utf-8")
