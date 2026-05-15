from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import time
from typing import Any

import httpx

from .config import BridgeConfig


class PhoneNotificationError(RuntimeError):
    pass


def _run(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, timeout=timeout)


def _clean_text(value: str, fallback: str, limit: int) -> str:
    text = " ".join((value or fallback).split())
    return text[:limit] if text else fallback


def _adb_path() -> str | None:
    return shutil.which("adb")


def _parse_devices(stdout: str) -> list[dict[str, str]]:
    devices: list[dict[str, str]] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split(None, 2)
        if len(parts) >= 2:
            devices.append(
                {
                    "serial": parts[0],
                    "state": parts[1],
                    "detail": parts[2] if len(parts) > 2 else "",
                    "transport": "remote" if ":" in parts[0] else "usb",
                }
            )
    return devices


def select_adb_target(config: BridgeConfig) -> tuple[list[str], dict[str, Any]]:
    adb = _adb_path()
    if not adb:
        raise PhoneNotificationError("adb was not found on PATH.")
    devices_result = _run([adb, "devices", "-l"], timeout=10)
    devices = _parse_devices(devices_result.stdout)
    ready = [device for device in devices if device["state"] == "device"]
    if config.android_serial:
        match = next((device for device in ready if device["serial"] == config.android_serial), None)
        if not match:
            raise PhoneNotificationError(f"Configured Android serial is not ready: {config.android_serial}")
        target = match
    else:
        target = next((device for device in ready if device["transport"] == "usb"), None) or (ready[0] if ready else None)
    if not target:
        raise PhoneNotificationError("No authorized Android device found.")
    return [adb, "-s", target["serial"]], {"target": target, "devices": devices}


def _send_omi_notification(config: BridgeConfig, uid: str, message: str) -> dict[str, str]:
    if not config.omi_app_id or not config.omi_app_secret:
        raise PhoneNotificationError("Omi app notification credentials are not configured.")
    url = f"{config.omi_api_base_url}/v2/integrations/{config.omi_app_id}/notification"
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                url,
                params={"uid": uid, "message": message},
                headers={"Authorization": f"Bearer {config.omi_app_secret}", "Content-Type": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise PhoneNotificationError("Omi notification API is temporarily unreachable.") from exc
    if response.status_code >= 400:
        raise PhoneNotificationError(f"Omi notification API rejected the request with HTTP {response.status_code}.")
    return {"result": "Sent through Omi notification API.", "delivery": "omi_api"}


def post_phone_notification(
    config: BridgeConfig,
    uid: str,
    title: str,
    message: str,
    *,
    expand_notifications: bool | None = None,
) -> dict[str, str]:
    clean_title = _clean_text(title, "Codex", 80)
    clean_message = _clean_text(message, "", 2000)
    if not clean_message:
        raise PhoneNotificationError("Message is empty.")
    if os.getenv("OMI_ANDROID_DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"}:
        return {"result": f"Shown on Android: {clean_title}", "message": clean_message, "delivery": "dry_run"}

    omi_message = f"{clean_title}: {clean_message}" if clean_title else clean_message
    omi_warning = ""
    if config.omi_notification_mode in {"auto", "omi"} and config.omi_app_id and config.omi_app_secret:
        try:
            sent = _send_omi_notification(config, uid, omi_message)
            return {"result": f"Shown through Omi: {clean_title}", "message": clean_message, **sent}
        except PhoneNotificationError as exc:
            if config.omi_notification_mode == "omi":
                raise
            omi_warning = str(exc)
    elif config.omi_notification_mode == "omi":
        raise PhoneNotificationError("Omi notification mode is enabled, but OMI_APP_ID/OMI_APP_SECRET are missing.")

    adb_prefix, _ = select_adb_target(config)
    pre_power = _device_power(adb_prefix)
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
    result = _run(
        [
            *adb_prefix,
            "shell",
            notification_command,
        ],
        timeout=15,
    )
    if result.returncode != 0:
        raise PhoneNotificationError((result.stderr or result.stdout or "Android notification post failed.").strip())

    should_expand = config.android_expand_notifications if expand_notifications is None else expand_notifications
    if should_expand:
        _run([*adb_prefix, "shell", "cmd", "statusbar", "expand-notifications"], timeout=10)
    elif config.android_sleep_after_notify and pre_power.get("wakefulness") in {"Dozing", "Asleep"}:
        time.sleep(0.4)
        _run([*adb_prefix, "shell", "input", "keyevent", "SLEEP"], timeout=5)

    response = {"result": f"Shown on Android: {clean_title}", "message": clean_message, "delivery": "adb"}
    if omi_warning:
        response["omi_warning"] = omi_warning
    return response


def _parse_power(stdout: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    patterns = {
        "wakefulness": r"mWakefulness=([A-Za-z]+)",
        "stay_on": r"mStayOn=(true|false)",
        "holding_display_suspend_blocker": r"mHoldingDisplaySuspendBlocker=(true|false)",
        "screen_off_timeout_ms": r"mScreenOffTimeoutSetting=(\d+)",
        "stay_on_while_plugged_in": r"mStayOnWhilePluggedInSetting=(\d+)",
        "wake_lock_summary": r"mWakeLockSummary=(0x[0-9a-fA-F]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, stdout)
        if not match:
            continue
        value = match.group(1)
        if value in {"true", "false"}:
            fields[key] = value == "true"
        elif value.isdigit():
            fields[key] = int(value)
        else:
            fields[key] = value
    return fields


def _device_power(adb_prefix: list[str]) -> dict[str, Any]:
    try:
        result = _run([*adb_prefix, "shell", "dumpsys", "power"], timeout=10)
    except Exception:
        return {}
    if result.returncode != 0:
        return {}
    return _parse_power(result.stdout)


def _wake_guard_tasks() -> dict[str, Any]:
    names = ["AndroidConnection BackgroundGuard", "AndroidConnection VolumeWake", "AndroidConnection KeepAlive"]
    schtasks = shutil.which("schtasks")
    if schtasks:
        rows: list[dict[str, str]] = []
        for name in names:
            try:
                result = _run([schtasks, "/Query", "/TN", name, "/FO", "LIST", "/V"], timeout=3)
            except Exception:
                rows.append({"name": name, "state": "unknown", "actions": ""})
                continue
            if result.returncode != 0:
                rows.append({"name": name, "state": "not_installed", "actions": ""})
                continue
            fields: dict[str, str] = {}
            for line in result.stdout.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
            rows.append(
                {
                    "name": name,
                    "state": fields.get("Status") or fields.get("Scheduled Task State") or "unknown",
                    "actions": fields.get("Task To Run", ""),
                }
            )
        return {
            "available": True,
            "tasks": rows,
            "wake_guards_disabled": all(
                row.get("state") == "not_installed"
                for row in rows
                if row.get("name") in {"AndroidConnection BackgroundGuard", "AndroidConnection VolumeWake"}
            ),
        }

    powershell = shutil.which("powershell")
    if not powershell:
        return {"available": False, "reason": "powershell not found"}
    script = (
        "$names=@('AndroidConnection BackgroundGuard','AndroidConnection VolumeWake','AndroidConnection KeepAlive');"
        "$rows=foreach($name in $names){"
        "$t=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue;"
        "$state=if($t){[string]$t.State}else{'not_installed'};"
        "$actions=if($t){(($t.Actions|ForEach-Object{($_.Execute+' '+$_.Arguments).Trim()}) -join ' || ')}else{''};"
        "[pscustomobject]@{name=$name;state=$state;actions=$actions}"
        "};"
        "$rows|ConvertTo-Json -Compress"
    )
    try:
        result = _run([powershell, "-NoProfile", "-Command", script], timeout=8)
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
    if result.returncode != 0 or not result.stdout.strip():
        return {"available": False, "reason": (result.stderr or result.stdout).strip()}
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"available": False, "reason": "unreadable scheduled task output"}
    if isinstance(rows, dict):
        rows = [rows]
    return {
        "available": True,
        "tasks": rows,
        "wake_guards_disabled": all(
            row.get("state") == "not_installed"
            for row in rows
            if row.get("name") in {"AndroidConnection BackgroundGuard", "AndroidConnection VolumeWake"}
        ),
    }


def android_status(config: BridgeConfig, *, include_power: bool = True, include_guards: bool = True) -> dict[str, Any]:
    adb = _adb_path()
    status: dict[str, Any] = {
        "adb_found": bool(adb),
        "available": False,
        "target": None,
        "transport": None,
        "devices": [],
        "unauthorized": [],
        "quiet_ready": False,
    }
    if not adb:
        status["reason"] = "adb not found"
        return status
    try:
        devices_result = _run([adb, "devices", "-l"], timeout=10)
        devices = _parse_devices(devices_result.stdout)
    except Exception as exc:
        status["reason"] = str(exc)
        return status

    ready = [device for device in devices if device["state"] == "device"]
    unauthorized = [device for device in devices if device["state"] == "unauthorized"]
    target = None
    if config.android_serial:
        target = next((device for device in ready if device["serial"] == config.android_serial), None)
    if target is None:
        target = next((device for device in ready if device["transport"] == "usb"), None) or (ready[0] if ready else None)

    status.update(
        {
            "available": target is not None,
            "target": target["serial"] if target else None,
            "transport": target["transport"] if target else None,
            "devices": devices,
            "unauthorized": unauthorized,
        }
    )
    if target and include_power:
        power = _device_power([adb, "-s", target["serial"]])
        status["power"] = power
        status["quiet_ready"] = (
            power.get("stay_on") is False
            and power.get("stay_on_while_plugged_in") == 0
        )
    elif target:
        status["quiet_ready"] = True
    if include_guards:
        guards = _wake_guard_tasks()
        status["wake_guards"] = guards
        if guards.get("available") and not guards.get("wake_guards_disabled", True):
            status["quiet_ready"] = False
    return status
