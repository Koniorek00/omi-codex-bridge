# Omi Codex Bridge

Tailscale Funnel friendly bridge from Omi voice/chat commands to local Codex CLI jobs.

## Why this exists

Omi app webhooks are called by Omi's cloud/backend. A private Tailscale Serve URL is not reachable by Omi unless Omi is inside your tailnet. For this workflow, use Tailscale Funnel so Omi can call a public HTTPS URL while traffic still routes back to your local machine through Tailscale.

The bridge is intentionally not a raw "voice runs code immediately" endpoint. It queues jobs by default and lets you start them from a local dashboard.

## Run locally

```powershell
cd "F:\ag projects\apps\Omi\omi-codex-bridge"
$env:OMI_CODEX_BRIDGE_TOKEN="replace-with-long-random-token"
# Optional when using scripts: $env:OMI_CODEX_TOKEN_FILE="runtime\current-token.txt"
$env:OMI_CODEX_WORKSPACE="F:\ag projects\apps\Omi"
$env:OMI_CODEX_ALLOWED_WORKSPACES="F:\ag projects\apps\Omi"
$env:OMI_OBSIDIAN_ENABLED="1"
$env:OMI_OBSIDIAN_VAULT_PATH="F:\programy\Obsidian\Codex Vault\Codex"
$env:OMI_OBSIDIAN_ROOT="Codex/Omi Codex Bridge"
$env:OMI_NOTIFICATION_MODE="auto" # auto, adb, or omi
$env:OMI_CODEX_PHONE_STATUS_UPDATES="1"
$env:OMI_ANDROID_EXPAND_NOTIFICATIONS="0" # keep status delivery sleep-friendly
$env:OMI_ANDROID_SLEEP_AFTER_NOTIFY="1"
# Optional official Omi push notifications:
# $env:OMI_APP_ID="your_omi_app_id"
# $env:OMI_APP_SECRET="your_omi_app_secret"
python -m uvicorn omi_codex_bridge.main:app --host 127.0.0.1 --port 8766
```

Or use the durable local setup script. It creates or reuses `runtime\current-token.txt`, sets the workspace allowlist, and can run the bridge in the background:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_local_bridge.ps1 -Background
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
```

Open:

```text
http://127.0.0.1:8766/omi/replace-with-long-random-token
```

## Test locally

```powershell
python -m pytest -q
python scripts\simulate_omi_codex.py --token replace-with-long-random-token
```

## Expose with Tailscale Funnel

Your local Tailscale status currently must be `Running`. If not:

```powershell
tailscale up
```

Then:

```powershell
tailscale funnel --bg --yes 8766
tailscale funnel status
```

Use the resulting `https://YOUR-MACHINE.YOUR-TAILNET.ts.net` URL with the tokenized paths below.

Funnel requires Tailscale HTTPS certificates for the tailnet. If `tailscale cert YOUR-MACHINE.YOUR-TAILNET.ts.net` fails, enable HTTPS/Funnel in the Tailscale admin console first.

If Funnel is blocked by tailnet HTTPS settings, use the Cloudflare quick-tunnel fallback:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_cloudflare_quick_tunnel.ps1
```

The fallback writes its public HTTPS base URL to `runtime\public-base-url.txt`. A private tokenized setup sheet is generated at `runtime\omi-setup-urls.private.txt`; do not paste that file into public notes.

To prepare everything in one pass:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare_all.ps1
```

To keep the local bridge and public tunnel alive after PC login, install the startup/watchdog helper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_startup_task.ps1
```

If Windows blocks Scheduled Tasks, the installer falls back to a Startup-folder shortcut that runs `watch_stack.ps1` every 15 minutes. The watcher keeps the phone in quiet mode and does not install display wake guards.

## Omi setup

Setup completed URL:

```text
https://YOUR-MACHINE.YOUR-TAILNET.ts.net/omi/YOUR_TOKEN/setup-completed
```

Memory creation webhook:

```text
https://YOUR-MACHINE.YOUR-TAILNET.ts.net/omi/YOUR_TOKEN/webhooks/memory
```

Realtime transcript webhook:

```text
https://YOUR-MACHINE.YOUR-TAILNET.ts.net/omi/YOUR_TOKEN/webhooks/realtime
```

Day summary webhook:

```text
https://YOUR-MACHINE.YOUR-TAILNET.ts.net/omi/YOUR_TOKEN/webhooks/day-summary
```

Chat Tools Manifest URL:

```text
https://YOUR-MACHINE.YOUR-TAILNET.ts.net/omi/YOUR_TOKEN/.well-known/omi-tools.json
```

App Home URL:

```text
https://YOUR-MACHINE.YOUR-TAILNET.ts.net/omi/YOUR_TOKEN
```

The local map for future agents is `OMI_AGENT_MAP.md`. The matching Obsidian memory index is:

```text
F:\programy\Obsidian\Codex Vault\Codex\Codex\Vibe Coding\omi-codex-bridge\index.md
```

## Obsidian export

The bridge writes Obsidian-readable Markdown notes directly into the configured vault. No Obsidian API key is stored in this project.

Default vault target:

```text
F:\programy\Obsidian\Codex Vault\Codex\Codex\Omi Codex Bridge
```

Saved items:

- `Memories/YYYY-MM-DD/` for Omi memory-created payloads.
- `Realtime/YYYY-MM-DD/` for realtime transcript captures that trigger Codex.
- `Events/day-summary/YYYY-MM-DD/` for Omi day summary payloads.
- `Jobs/job-N.md` for queued, cancelled, retried, running, and completed Codex jobs.

The `/health` response reports the Obsidian export status. To change the target, set:

```powershell
$env:OMI_OBSIDIAN_ENABLED="1"
$env:OMI_OBSIDIAN_VAULT_PATH="F:\programy\Obsidian\Codex Vault\Codex"
$env:OMI_OBSIDIAN_ROOT="Codex/Omi Codex Bridge"
```

## Phone and Omi notifications

`show_on_android` sends a short message to the phone without opening the notification shade by default. Delivery order:

- If `OMI_APP_ID` and `OMI_APP_SECRET` are set, the bridge uses Omi's official notification API.
- Otherwise it falls back to the connected Android phone over ADB.

The local startup script enables `OMI_CODEX_PHONE_STATUS_UPDATES=1`, so queued/running/completed Codex jobs can send short status updates back to the phone. It also keeps `OMI_ANDROID_EXPAND_NOTIFICATIONS=0` and `OMI_ANDROID_SLEEP_AFTER_NOTIFY=1`, so ADB fallback delivery does not intentionally keep the display awake.

Use this chat tool to verify the quiet path:

```text
Check phone status
```

To review Omi UIDs seen by tools and webhooks, open the protected local API:

```text
http://127.0.0.1:8766/omi/YOUR_TOKEN/api/known-uids
```

Use the real phone UID from this list only when intentionally adding `OMI_CODEX_TRUSTED_UIDS` for trusted autorun.

Trusted autorun can be prepared without editing env vars by hand:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\set_trusted_autorun.ps1 -Uid REAL_OMI_UID
powershell -ExecutionPolicy Bypass -File .\scripts\set_trusted_autorun.ps1 -Enable
powershell -ExecutionPolicy Bypass -File .\scripts\set_trusted_autorun.ps1 -List
```

Disable it again with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\set_trusted_autorun.ps1 -Disable
```

The manifest also exposes Omi `chat_messages` so Omi knows the app can send app-chat messages.

The Android helper can open the Omi app after ADB is authorized:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\wait_for_android.ps1 -OpenOmi -StartScrcpy
powershell -ExecutionPolicy Bypass -File .\scripts\copy_setup_url.ps1 -Name realtime
```

## Voice phrases

These create queued jobs:

```text
Hey Omi Codex build a landing page for this app
Omi Codex fix the failing tests
Ask Codex to add a SQLite settings table
Tell Codex to refactor the dashboard
Codex start writing the Notion sync integration
Hej Omi kodeks napraw aplikację
Powiedz Codexowi żeby uruchomił testy
Omi to jest do ciebie popraw bridge
Hej Omi powiedz Codex zeby otworzyl na moim komputerze teraz jakis plik z pulpitu obojetne
Powiedz Codexowi zeby pokazal na telefonie: test z komputera
Powiedz Codexowi quick fix: sprawdz czemu nie dziala bridge
```

These control existing jobs through Omi chat tools:

```text
What Codex jobs are queued?
Run Codex job job-12
Run the next Codex job
What happened with job-12?
Show the Codex output for job-12
Cancel Codex job job-13
Retry Codex job job-13
Check the Codex bridge status
```

## Tool functions

The manifest exposes these Omi chat tools:

- `start_codex_task`: queue a task with an optional allowlisted workspace.
- `open_desktop_file`: open a Desktop/Pulpit file on this Windows PC immediately. Vague requests open/create `omi-codex-open-test.txt`.
- `show_on_android`: show a short title/message on the connected Android phone as a notification; notification shade expansion is opt-in.
- `check_phone_status`: check ADB reachability, screen quiet mode, and wake-guard tasks without waking the phone.
- `quick_codex_task`: queue common Codex work using presets: `build`, `create`, `fix`, `test`, `review`, `setup`, `android`, `obsidian`, `research`.
- `run_codex_job`: start a queued or failed job by id.
- `run_next_codex_job`: start the oldest pending job without needing an id.
- `list_codex_jobs`: list recent jobs, optionally filtered by status.
- `get_codex_job`: inspect status, prompt, events, and a short output hint.
- `get_codex_job_output`: read final message or log output.
- `cancel_codex_job`: cancel a pending job.
- `retry_codex_job`: clone a failed, cancelled, or completed job into a fresh queued job.
- `check_bridge_status`: report bridge health, Codex CLI availability, autorun, and queue counts.

## Research loop

Use this to refresh the local Omi/GitHub watchlist:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\research_omi_sources.ps1
```

Notes are kept in `OMI_RESEARCH_NOTES.md`.

## Safety model

- All public Omi endpoints are under `/omi/{token}/...`.
- The token must be long and random before using Funnel.
- Workspaces are allowlisted by `OMI_CODEX_ALLOWED_WORKSPACES`.
- Jobs queue by default. They do not run until you press Run in the dashboard or call the run endpoint/tool.
- `OMI_CODEX_AUTORUN=1` exists, but should stay off unless you accept the risk.
- If autorun is enabled, `OMI_CODEX_AUTORUN_REQUIRE_TRUSTED_UID=1` keeps automatic starts limited to `OMI_CODEX_TRUSTED_UIDS`.
- `runtime\trusted-uids.txt` and `runtime\autorun.enabled` are local runtime files. They are not committed.
- The Codex CLI runs with `--sandbox workspace-write` and `-c approval_policy="never"`, not with bypassed sandbox.

## Codex command used

When a queued job runs, the bridge uses:

```text
codex exec -c approval_policy="never" -C WORKSPACE --skip-git-repo-check --sandbox workspace-write --output-last-message runtime/jobs/job-N/codex-last-message.txt -
```

The prompt is sent through stdin.
