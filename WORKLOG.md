# Omi Codex Bridge Worklog

## 2026-05-15

- Confirmed `python -m pytest -q` passes: 33 tests.
- Confirmed stack start/repair script reports local bridge healthy, Android quiet power profile applied, and Cloudflare quick tunnel healthy.
- Confirmed doctor reports bridge health, Obsidian export, Android quiet channel, Omi tool manifest, setup endpoint, and private setup sheet OK.
- Confirmed real `show_on_android` tool call delivered through ADB.
- Confirmed real realtime webhook phrase for "pokaz na telefonie" routes directly to Android notification and does not queue a Codex job.
- Confirmed phone remains in `Dozing` with quiet mode enabled after notification delivery.
- Refreshed `runtime/logs/stack-watchdog-last-run.log` with a clean successful stack check.
- Sealed the bridge hardening code in commit `15fd035` and kept this execution trail as the project-level handoff.
- Added runtime token-file recovery so a direct or watcher launch does not fall back to the dev token.
- Added `/health/quick` and switched stack/public tunnel probes to it, avoiding false restarts when full Android health is slow.
- Confirmed live bridge after restart is using the real token, phone status updates are on, Android remains quiet, and Cloudflare quick tunnel is reachable.
- Moved full health, phone status, and Android notification calls off the FastAPI event loop; concurrent full-health plus quick-health smoke test returned quick health in under 1 second.
