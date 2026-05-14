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
ADB sees authorized phone serial `RZCXB128SKH`. Public Omi endpoint smoke test successfully posted an Android notification through `show_on_android`.

## Verification
- `python -m pytest -q` passes in `omi-codex-bridge`.
- `python -m pytest -q` passes in `omi-hermes-bridge`.
- `codex --version` reports Codex CLI installed.
- `tailscale status` reports this Windows machine online.
- Cloudflare quick tunnel is running for port `8766` because Tailscale Funnel is blocked by missing tailnet HTTPS certificate support.
- Public manifest exposes `open_desktop_file`, `show_on_android`, and `quick_codex_task`.
- Public manifest exposes Omi `chat_messages` with target `app`.
- Public `show_on_android` smoke test displayed `Codex test dwa` with full message text on the Android phone.
- Public `quick_codex_task` smoke test queued `job-19` and saved its Obsidian job note.
- Public realtime smoke test with the exact Polish desktop phrase opened `C:\Users\wikto\Desktop\omi-codex-open-test.txt`.
- Public webhook smoke tests queued and cancelled `job-15`, `job-16`, and `job-17`.
- `scripts\prepare_all.ps1` prepares bridge, tunnel, setup files, and doctor pass.
- Obsidian export writes Markdown notes directly to `Codex\Omi Codex Bridge`; `/health` reports the active vault path and root.
- `scripts\wait_for_android.ps1 -OpenOmi -StartScrcpy` is ready for the moment ADB is authorized.
- `PHONE_READY_NEXT.md` is the short runbook for finishing phone-side setup after USB debugging authorization.

## Notes
Do not store bridge tokens, Omi API keys, OAuth links, or app API keys in notes. The token file path may be documented; the token value should stay out of reports.
