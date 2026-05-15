from __future__ import annotations

from omi_codex_bridge.config import BridgeConfig


def test_from_env_reads_runtime_token_file_and_keeps_phone_status_on(tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    token_file = runtime / "current-token.txt"
    token_file.write_text("omi-codex-test-token-1234567890", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    monkeypatch.delenv("OMI_CODEX_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("OMI_CODEX_PHONE_STATUS_UPDATES", raising=False)
    monkeypatch.setenv("OMI_CODEX_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("OMI_CODEX_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("OMI_CODEX_WORKSPACE", str(workspace))
    monkeypatch.setenv("OMI_CODEX_ALLOWED_WORKSPACES", str(workspace))

    config = BridgeConfig.from_env()

    assert config.token == "omi-codex-test-token-1234567890"
    assert config.using_default_token is False
    assert config.phone_status_updates is True


def test_from_env_reads_trusted_uids_and_autorun_flag_files(tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "current-token.txt").write_text("omi-codex-test-token-1234567890", encoding="utf-8")
    (runtime / "trusted-uids.txt").write_text("# owner only\nreal-user\nreal-user\nsecond-user\n", encoding="utf-8")
    (runtime / "autorun.enabled").write_text("enabled", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    monkeypatch.delenv("OMI_CODEX_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("OMI_CODEX_AUTORUN", raising=False)
    monkeypatch.delenv("OMI_CODEX_TRUSTED_UIDS", raising=False)
    monkeypatch.setenv("OMI_CODEX_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("OMI_CODEX_WORKSPACE", str(workspace))
    monkeypatch.setenv("OMI_CODEX_ALLOWED_WORKSPACES", str(workspace))

    config = BridgeConfig.from_env()

    assert config.autorun is True
    assert config.trusted_uids == ("real-user", "second-user")
    assert config.can_autorun("real-user") is True
    assert config.can_autorun("other-user") is False
