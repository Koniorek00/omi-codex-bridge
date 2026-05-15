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
