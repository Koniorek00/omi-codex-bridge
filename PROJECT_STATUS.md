# Omi Codex Bridge - Current State

Last updated: 2026-05-15

## Short Version

The project works locally. Omi can reach the bridge, the bridge can queue Codex jobs, phone notifications work quietly, Obsidian REST works, and tests pass.

The main unfinished items are not core code bugs. They are setup/product gaps: GitHub sync, final Omi phone-side URL update, real trusted Omi UID capture, and Tailscale Funnel admin settings.

## What We Have

- Working local bridge on `127.0.0.1:8766`.
- Public Cloudflare quick tunnel fallback.
- Omi tool manifest with job control tools.
- Codex job queue with manual run controls.
- Autorun disabled by default.
- Trusted UID gate for future autorun.
- Android phone notifications through ADB.
- Quiet phone behavior by default.
- `check_phone_status` tool.
- Obsidian export and Obsidian Local REST connection.
- `/health/quick` for fast liveness checks.
- Full `/health` for deeper diagnostics.
- Startup/watchdog scripts.
- Project docs: `README.md`, `CHECKLIST.md`, `DECISIONS.md`, `WORKLOG.md`, `OMI_AGENT_MAP.md`.
- Passing tests: `python -m pytest -q`.
- Worktree-swarm preflight is clean/ready locally.

## What We Do Not Have Yet

- Tailscale Funnel is not fully working because HTTPS/Funnel cert support is blocked in Tailscale admin settings.
- Full public autorun is not enabled.
- Real Omi phone `uid` is not captured into `OMI_CODEX_TRUSTED_UIDS`.
- Omi phone-side setup may need a URL refresh if the Cloudflare quick tunnel changes.
- Local commits still need to be pushed to GitHub if remote sharing is required.
- Stronger public remote-control policy is still a future security/product decision.

## Current Verification

- `python -m pytest -q` passes.
- Local connection check passes:
  - core skills OK
  - workflow boundary OK
  - Codex Cockpit OK
  - Omi Codex Bridge OK
  - Obsidian REST OK
  - Claude direct/proxy OK

## Next Checklist

- [ ] Push local commits to GitHub.
- [ ] Confirm GitHub branch is no longer behind local work.
- [ ] If Cloudflare URL changed, update the Omi app setup URL on the phone.
- [ ] Capture real Omi `uid` from an incoming request.
- [ ] Add trusted UID only if autorun is intentionally enabled later.
- [ ] Decide whether to keep Cloudflare as primary or fix Tailscale Funnel.
- [ ] Add stronger public remote-control policy before broader remote control.

## Blocked

- [!] Tailscale Funnel - blocked by Tailscale HTTPS/Funnel admin/certificate settings.
- [!] Trusted autorun - waiting for real Omi `uid` and explicit decision to enable autorun.

## Important Rule

Keep autorun off unless the user explicitly decides otherwise. The safe normal mode is: Omi queues work, then the user or dashboard runs it.
