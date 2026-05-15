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
- Verified Claude Opus direct API and local OpenAI-compatible proxy on `127.0.0.1:8787`.
- Added durable trusted UID and autorun runtime files plus `scripts/set_trusted_autorun.ps1`.
- Added config regression coverage; bridge tests now pass 37 tests after the known-UID trusted flag coverage.
- Created living plan `.codex/plans/omi-tony-stark-assistant-map-20260515-1504.md`.
- Created Obsidian project memory note and session note for the Omi Tony Stark assistant setup.
- Opened Omi/Friend Android app package `com.friend.ios/.MainActivity` and added `open-omi` macro.
- Repaired Chrome native host manifest/registry for the Codex browser extension; extension is installed/enabled, but this Codex session still needs reload before `$PersonalBrowser` can expose `openTabs()`.
- Verified the Aria Companion phone-agent path: Android app message created an Aria conversation, queued an approved Codex task, the Codex worker completed it, and the phone command was ACKed as an Android notification.
- Updated and reinstalled the Aria Companion APK so Codex routing persists and the foreground service restarts its polling loop when the active companion device key changes.
- Updated the Aria companion doctor script so it no longer guesses app-scoped Android IDs from ADB; the app now keeps its own stable device key by default.
- Confirmed the phone returned to quiet mode after setup: `Dozing`, no stay-on, no display suspend blocker.
- Hardened trusted autorun setup: UID add/remove validation, conflict guard, durable file docs, dashboard known-UID panel, and trusted UID flags in `/api/known-uids`.
- Repaired Polish trigger parsing so real Omi phrases with normal diacritics work, while keeping compatibility with older mojibake examples.
