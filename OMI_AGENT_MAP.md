---
type: omi-codex-bridge-map
project: omi-codex-bridge
status: active
created: 2026-05-14
tags:
  - omi
  - codex
  - agents
---

# Omi Codex Bridge Map

## Goal
Voice or chat requests from Omi should become queued Codex jobs on this PC. Jobs are reviewed and run from the local dashboard or through Omi chat tools.

## Active Bridge
- Project: `F:\ag projects\apps\Omi\omi-codex-bridge`
- Local dashboard: `http://127.0.0.1:8766/omi/<token>`
- Token file: `F:\ag projects\apps\Omi\omi-codex-bridge\runtime\current-token.txt`
- Health check: `http://127.0.0.1:8766/health`
- Current quick-tunnel base URL file: `F:\ag projects\apps\Omi\omi-codex-bridge\runtime\public-base-url.txt`
- Private tokenized Omi setup URLs: `F:\ag projects\apps\Omi\omi-codex-bridge\runtime\omi-setup-urls.private.txt`
- Private setup HTML page: `F:\ag projects\apps\Omi\omi-codex-bridge\runtime\omi-setup.private.html`
- Startup watchdog shortcut: `C:\Users\wikto\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Omi Codex Bridge Watchdog.lnk`
- Startup/watchdog scripts: `scripts\install_startup_task.ps1`, `scripts\watch_stack.ps1`, `scripts\start_stack.ps1`
- Research notes: `F:\ag projects\apps\Omi\omi-codex-bridge\OMI_RESEARCH_NOTES.md`
- Default workspace: `F:\ag projects\apps\Omi`
- Allowed workspace roots: `F:\ag projects`, `C:\Users\wikto\.codex\skills`, `C:\Users\wikto\.agents\skills`, `F:\programy\Obsidian\Codex Vault\Codex`
- Obsidian export root: `F:\programy\Obsidian\Codex Vault\Codex\Codex\Omi Codex Bridge`

## Omi URLs
Use the Tailscale Funnel HTTPS base URL plus the tokenized paths below.

- App Home URL: `/omi/<token>`
- Setup completed URL: `/omi/<token>/setup-completed`
- Memory creation webhook: `/omi/<token>/webhooks/memory`
- Realtime transcript webhook: `/omi/<token>/webhooks/realtime`
- Day summary webhook: `/omi/<token>/webhooks/day-summary`
- Chat Tools Manifest URL: `/omi/<token>/.well-known/omi-tools.json`

## Voice Triggers
- English: `Hey Omi Codex ...`, `Ask Codex to ...`, `Tell Codex to ...`, `Codex run/fix/build ...`
- Polish: `Hej Omi kodeks ...`, `Powiedz Codexowi żeby ...`, `Omi to jest do ciebie ...`
- Exact tested open phrase: `Hej Omi powiedz Codex zeby otworzyl na moim komputerze teraz jakis plik z pulpitu obojetne`
- Speech-recognition aliases: `Codex`, `Kodex`, and `Kodeks` all target this local Codex bridge.
- Omi chat tools expose `ask_codex` as the primary natural-language route to this PC.
- `open_desktop_file` opens a Windows Desktop/Pulpit file immediately; vague requests use/create `omi-codex-open-test.txt`.
- `show_on_android` pushes a short notification to the connected Android phone.
- `show_on_android` uses Omi official push notifications when `OMI_APP_ID` and `OMI_APP_SECRET` exist; otherwise it uses ADB fallback.
- `show_on_android` is sleep-friendly by default: it does not expand the notification shade and `OMI_ANDROID_SLEEP_AFTER_NOTIFY=1` puts the display back to sleep if it was already dozing.
- `check_phone_status` reports ADB reachability, current screen state, and whether wake guards are disabled.
- Realtime commands like `Powiedz Codexowi zeby pokazal na telefonie: test` now send the phone status directly instead of queuing a Codex job.
- `quick_codex_task` routes common work as presets: `build`, `create`, `fix`, `test`, `review`, `setup`, `android`, `obsidian`, `research`.

## Job Flow
1. Omi sends transcript or memory data to the bridge.
2. The bridge extracts Codex-specific instructions and deduplicates repeated transcript segments.
3. A job is queued in SQLite under `runtime\bridge.db`.
4. Matching Omi memory, realtime trigger, day-summary, and job notes are written to Obsidian under the export root.
5. The user or Omi chat tool runs a queued job.
6. The bridge starts `codex exec` in the requested allowlisted workspace.
7. Output is stored under `runtime\jobs\<job-id>` and the job note is updated when the job finishes.

## Phone State
ADB sees authorized phone serial `RZCXB128SKH`. BackgroundGuard and VolumeWake are intentionally not installed. KeepAlive remains active and uses `Ensure-AndroidConnection.ps1 -Prefer any -Control none`, so it reconnects without opening scrcpy or waking the display.

## Startup And Watchdog
- Windows Task Scheduler registration is blocked by user-level access on this machine, so startup uses a Startup-folder shortcut fallback.
- `watch_stack.ps1` runs hidden after login and checks every 15 minutes.
- `start_stack.ps1` is idempotent: it starts local bridge if needed, reapplies Android quiet power profile, verifies/refreshes the public tunnel, and rewrites private setup URLs.
- Cloudflare quick tunnel DNS can fail through the local Windows resolver while public DNS works. `doctor.ps1` and `start_stack.ps1` use a `curl --resolve` fallback via public DNS so they do not rotate a valid tunnel unnecessarily.

## Verification
- `python -m pytest -q` passes in `omi-codex-bridge`.
- `python -m pytest -q` passes in `omi-hermes-bridge`.
- `codex --version` reports Codex CLI installed.
- `tailscale status` reports this Windows machine online.
- Cloudflare quick tunnel is running for port `8766` because Tailscale Funnel is blocked by missing tailnet HTTPS certificate support.
- Public manifest exposes `open_desktop_file`, `show_on_android`, and `quick_codex_task`.
- Public manifest exposes `check_phone_status`.
- Public manifest exposes Omi `chat_messages` with target `app`.
- Public `show_on_android` and realtime phone-message smoke tests delivered through ADB while the phone returned to `Dozing` with `stay_on=false`, `mHoldingDisplaySuspendBlocker=false`, and 30s screen timeout.
- Public `quick_codex_task` smoke test queued `job-19` and saved its Obsidian job note.
- Public realtime smoke test with the exact Polish desktop phrase opened `C:\Users\wikto\Desktop\omi-codex-open-test.txt`.
- Public webhook smoke tests queued and cancelled `job-15`, `job-16`, and `job-17`.
- `scripts\prepare_all.ps1` prepares bridge, tunnel, setup files, and doctor pass.
- Startup fallback installed and active: hidden `watch_stack.ps1` process plus Startup shortcut.
- `scripts\start_stack.ps1 -Port 8766` completes cleanly with bridge healthy, Android quiet profile applied, and Cloudflare quick tunnel healthy.
- Obsidian export writes Markdown notes directly to `Codex\Omi Codex Bridge`; `/health` reports the active vault path and root.
- `scripts\wait_for_android.ps1 -OpenOmi -StartScrcpy` is opt-in only for visible setup; do not use it as a background keepalive.
- `PHONE_READY_NEXT.md` is the short runbook for finishing phone-side setup after USB debugging authorization.

## Notes
Do not store bridge tokens, Omi API keys, OAuth links, or app API keys in notes. The token file path may be documented; the token value should stay out of reports.
