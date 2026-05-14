from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _split_paths(value: str) -> list[Path]:
    return [Path(item).expanduser().resolve() for item in value.split(";") if item.strip()]


@dataclass(frozen=True)
class BridgeConfig:
    token: str
    runtime_dir: Path
    database_path: Path
    default_workspace: Path
    allowed_workspaces: list[Path]
    autorun: bool
    runner_mode: str
    codex_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        runtime_dir = Path(os.getenv("OMI_CODEX_RUNTIME_DIR", Path(__file__).resolve().parents[1] / "runtime")).resolve()
        default_workspace = Path(os.getenv("OMI_CODEX_WORKSPACE", Path(__file__).resolve().parents[2])).resolve()
        allowed_raw = os.getenv("OMI_CODEX_ALLOWED_WORKSPACES", str(default_workspace))
        allowed = _split_paths(allowed_raw)
        if not allowed:
            allowed = [default_workspace]
        return cls(
            token=os.getenv("OMI_CODEX_BRIDGE_TOKEN", "dev-token-change-me"),
            runtime_dir=runtime_dir,
            database_path=runtime_dir / "bridge.db",
            default_workspace=default_workspace,
            allowed_workspaces=allowed,
            autorun=os.getenv("OMI_CODEX_AUTORUN", "0").strip().lower() in {"1", "true", "yes", "on"},
            runner_mode=os.getenv("OMI_CODEX_RUNNER", "codex").strip().lower(),
            codex_timeout_seconds=int(os.getenv("OMI_CODEX_TIMEOUT_SECONDS", "1800")),
        )

    @property
    def using_default_token(self) -> bool:
        return self.token == "dev-token-change-me"

    def normalize_workspace(self, workspace: str | None) -> Path:
        candidate = Path(workspace).expanduser().resolve() if workspace else self.default_workspace
        for allowed in self.allowed_workspaces:
            if candidate == allowed or allowed in candidate.parents:
                return candidate
        allowed_text = "; ".join(str(path) for path in self.allowed_workspaces)
        raise ValueError(f"Workspace {candidate} is outside allowed workspaces: {allowed_text}")

