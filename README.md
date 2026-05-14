# Omi Codex Bridge

Tailscale Funnel friendly bridge from Omi voice/chat commands to local Codex CLI jobs.

## Why this exists

Omi app webhooks are called by Omi's cloud/backend. A private Tailscale Serve URL is not reachable by Omi unless Omi is inside your tailnet. For this workflow, use Tailscale Funnel so Omi can call a public HTTPS URL while traffic still routes back to your local machine through Tailscale.

The bridge is intentionally not a raw "voice runs code immediately" endpoint. It queues jobs by default and lets you start them from a local dashboard.

## Run locally

```powershell
cd "F:\ag projects\apps\Omi\omi-codex-bridge"
$env:OMI_CODEX_BRIDGE_TOKEN="replace-with-long-random-token"
$env:OMI_CODEX_WORKSPACE="F:\ag projects\apps\Omi"
$env:OMI_CODEX_ALLOWED_WORKSPACES="F:\ag projects\apps\Omi"
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
- `run_codex_job`: start a queued or failed job by id.
- `run_next_codex_job`: start the oldest pending job without needing an id.
- `list_codex_jobs`: list recent jobs, optionally filtered by status.
- `get_codex_job`: inspect status, prompt, events, and a short output hint.
- `get_codex_job_output`: read final message or log output.
- `cancel_codex_job`: cancel a pending job.
- `retry_codex_job`: clone a failed, cancelled, or completed job into a fresh queued job.
- `check_bridge_status`: report bridge health, Codex CLI availability, autorun, and queue counts.

## Safety model

- All public Omi endpoints are under `/omi/{token}/...`.
- The token must be long and random before using Funnel.
- Workspaces are allowlisted by `OMI_CODEX_ALLOWED_WORKSPACES`.
- Jobs queue by default. They do not run until you press Run in the dashboard or call the run endpoint/tool.
- `OMI_CODEX_AUTORUN=1` exists, but should stay off unless you accept the risk.
- The Codex CLI runs with `--sandbox workspace-write` and `-c approval_policy="never"`, not with bypassed sandbox.

## Codex command used

When a queued job runs, the bridge uses:

```text
codex exec -c approval_policy="never" -C WORKSPACE --skip-git-repo-check --sandbox workspace-write --output-last-message runtime/jobs/job-N/codex-last-message.txt -
```

The prompt is sent through stdin.
