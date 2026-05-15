from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from omi_codex_bridge.config import BridgeConfig
from omi_codex_bridge import phone


def make_config(tmp_path: Path, android_serial: str | None = None) -> BridgeConfig:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return BridgeConfig(
        token="test-token",
        runtime_dir=tmp_path / "runtime",
        database_path=tmp_path / "runtime" / "bridge.db",
        default_workspace=workspace,
        allowed_workspaces=[workspace],
        autorun=False,
        runner_mode="mock",
        codex_timeout_seconds=30,
        android_serial=android_serial,
    )


def test_parse_devices_classifies_usb_and_remote() -> None:
    devices = phone._parse_devices(
        "\n".join(
            [
                "List of devices attached",
                "RZCXB128SKH device product:r12sxeea model:SM_S721B",
                "100.125.32.101:50708 device product:r12sxeea model:SM_S721B",
                "offline-1 offline",
            ]
        )
    )

    assert devices[0]["transport"] == "usb"
    assert devices[1]["transport"] == "remote"
    assert devices[2]["state"] == "offline"


def test_select_adb_target_prefers_usb(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(phone, "_adb_path", lambda: "adb")
    monkeypatch.setattr(
        phone,
        "_run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="100.125.32.101:50708 device\nRZCXB128SKH device\n",
            returncode=0,
            stderr="",
        ),
    )

    prefix, metadata = phone.select_adb_target(make_config(tmp_path))

    assert prefix == ["adb", "-s", "RZCXB128SKH"]
    assert metadata["target"]["transport"] == "usb"


def test_select_adb_target_respects_configured_serial(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(phone, "_adb_path", lambda: "adb")
    monkeypatch.setattr(
        phone,
        "_run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="100.125.32.101:50708 device\nRZCXB128SKH device\n",
            returncode=0,
            stderr="",
        ),
    )

    prefix, metadata = phone.select_adb_target(make_config(tmp_path, android_serial="100.125.32.101:50708"))

    assert prefix == ["adb", "-s", "100.125.32.101:50708"]
    assert metadata["target"]["transport"] == "remote"


def test_post_phone_notification_dry_run_does_not_require_adb(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OMI_ANDROID_DRY_RUN", "1")
    monkeypatch.setattr(phone, "_adb_path", lambda: None)

    result = phone.post_phone_notification(make_config(tmp_path), "uid-1", "Codex", "Hello phone")

    assert result == {"result": "Shown on Android: Codex", "message": "Hello phone", "delivery": "dry_run"}


def test_android_status_marks_guarded_phone_not_quiet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(phone, "_adb_path", lambda: "adb")
    monkeypatch.setattr(
        phone,
        "_run",
        lambda *args, **kwargs: SimpleNamespace(stdout="RZCXB128SKH device\n", returncode=0, stderr=""),
    )
    monkeypatch.setattr(phone, "_device_power", lambda adb_prefix: {"stay_on": False, "stay_on_while_plugged_in": 0})
    monkeypatch.setattr(
        phone,
        "_wake_guard_tasks",
        lambda: {"available": True, "wake_guards_disabled": False, "tasks": []},
    )

    status = phone.android_status(make_config(tmp_path))

    assert status["available"] is True
    assert status["quiet_ready"] is False
