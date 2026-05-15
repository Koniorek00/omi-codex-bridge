from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _split_paths(value: str) -> list[Path]:
    return [Path(item).expanduser().resolve() for item in value.split(";") if item.strip()]


def _split_values(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.replace(";", ",").split(",") if item.strip())


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
    obsidian_enabled: bool = False
    obsidian_vault_path: Path | None = None
    obsidian_root: str = "Codex/Omi Codex Bridge"
    omi_app_id: str | None = None
    omi_app_secret: str | None = None
    omi_api_base_url: str = "https://api.omi.me"
    omi_notification_mode: str = "auto"
    omi_chat_messages_enabled: bool = True
    omi_chat_messages_target: str = "app"
    omi_chat_messages_notify: bool = False
    phone_status_updates: bool = False
    trusted_uids: tuple[str, ...] = ()
    autorun_requires_trusted_uid: bool = True
    android_serial: str | None = None
    android_expand_notifications: bool = False
    android_sleep_after_notify: bool = True

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        runtime_dir = Path(os.getenv("OMI_CODEX_RUNTIME_DIR", Path(__file__).resolve().parents[1] / "runtime")).resolve()
        default_workspace = Path(os.getenv("OMI_CODEX_WORKSPACE", Path(__file__).resolve().parents[2])).resolve()
        obsidian_vault_raw = os.getenv("OMI_OBSIDIAN_VAULT_PATH", r"F:\programy\Obsidian\Codex Vault\Codex").strip()
        obsidian_vault = Path(obsidian_vault_raw).expanduser().resolve() if obsidian_vault_raw else None
        default_allowed = [default_workspace]
        if len(default_workspace.parents) > 1:
            default_allowed.insert(0, default_workspace.parents[1])
        default_allowed.extend(
            path
            for path in (
                Path.home() / ".codex" / "skills",
                Path.home() / ".agents" / "skills",
                obsidian_vault,
            )
            if path is not None
        )
        allowed_raw = os.getenv("OMI_CODEX_ALLOWED_WORKSPACES", ";".join(str(path) for path in default_allowed))
        allowed = _split_paths(allowed_raw)
        if not allowed:
            allowed = [default_workspace]
        token = os.getenv("OMI_CODEX_BRIDGE_TOKEN", "").strip()
        if not token:
            token_file_raw = os.getenv("OMI_CODEX_TOKEN_FILE", str(runtime_dir / "current-token.txt")).strip()
            token_file = Path(token_file_raw).expanduser()
            if not token_file.is_absolute():
                token_file = (Path(__file__).resolve().parents[1] / token_file).resolve()
            if token_file.is_file():
                token = token_file.read_text(encoding="utf-8", errors="replace").strip()
        if not token:
            token = "dev-token-change-me"
        notification_mode = os.getenv("OMI_NOTIFICATION_MODE", "auto").strip().lower()
        if notification_mode not in {"auto", "adb", "omi"}:
            notification_mode = "auto"
        chat_target = os.getenv("OMI_CHAT_MESSAGES_TARGET", "app").strip().lower()
        if chat_target not in {"app", "main"}:
            chat_target = "app"
        return cls(
            token=token,
            runtime_dir=runtime_dir,
            database_path=runtime_dir / "bridge.db",
            default_workspace=default_workspace,
            allowed_workspaces=allowed,
            autorun=os.getenv("OMI_CODEX_AUTORUN", "0").strip().lower() in {"1", "true", "yes", "on"},
            runner_mode=os.getenv("OMI_CODEX_RUNNER", "codex").strip().lower(),
            codex_timeout_seconds=int(os.getenv("OMI_CODEX_TIMEOUT_SECONDS", "1800")),
            obsidian_enabled=os.getenv("OMI_OBSIDIAN_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"},
            obsidian_vault_path=obsidian_vault,
            obsidian_root=os.getenv("OMI_OBSIDIAN_ROOT", "Codex/Omi Codex Bridge").strip() or "Codex/Omi Codex Bridge",
            omi_app_id=os.getenv("OMI_APP_ID", "").strip() or None,
            omi_app_secret=os.getenv("OMI_APP_SECRET", "").strip() or None,
            omi_api_base_url=os.getenv("OMI_API_BASE_URL", "https://api.omi.me").strip().rstrip("/") or "https://api.omi.me",
            omi_notification_mode=notification_mode,
            omi_chat_messages_enabled=os.getenv("OMI_CHAT_MESSAGES_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"},
            omi_chat_messages_target=chat_target,
            omi_chat_messages_notify=os.getenv("OMI_CHAT_MESSAGES_NOTIFY", "0").strip().lower() in {"1", "true", "yes", "on"},
            phone_status_updates=os.getenv("OMI_CODEX_PHONE_STATUS_UPDATES", "1").strip().lower() in {"1", "true", "yes", "on"},
            trusted_uids=_split_values(os.getenv("OMI_CODEX_TRUSTED_UIDS", "")),
            autorun_requires_trusted_uid=os.getenv("OMI_CODEX_AUTORUN_REQUIRE_TRUSTED_UID", "1").strip().lower()
            in {"1", "true", "yes", "on"},
            android_serial=os.getenv("OMI_ANDROID_SERIAL", "").strip() or None,
            android_expand_notifications=os.getenv("OMI_ANDROID_EXPAND_NOTIFICATIONS", "0").strip().lower() in {"1", "true", "yes", "on"},
            android_sleep_after_notify=os.getenv("OMI_ANDROID_SLEEP_AFTER_NOTIFY", "1").strip().lower() in {"1", "true", "yes", "on"},
        )

    @property
    def using_default_token(self) -> bool:
        return self.token == "dev-token-change-me"

    def can_autorun(self, uid: str | None) -> bool:
        if not self.autorun:
            return False
        if not self.autorun_requires_trusted_uid:
            return True
        return bool(uid and uid in self.trusted_uids)

    def normalize_workspace(self, workspace: str | None) -> Path:
        candidate = Path(workspace).expanduser().resolve() if workspace else self.default_workspace
        for allowed in self.allowed_workspaces:
            if candidate == allowed or allowed in candidate.parents:
                return candidate
        allowed_text = "; ".join(str(path) for path in self.allowed_workspaces)
        raise ValueError(f"Workspace {candidate} is outside allowed workspaces: {allowed_text}")
