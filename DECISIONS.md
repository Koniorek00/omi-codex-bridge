# Omi Codex Bridge Decisions

## 2026-05-15

- Keep phone operation sleep-friendly by default. Do not install display wake guards or force long screen timeouts unless the user explicitly asks for a visible remote-control session.
- Use Cloudflare quick tunnel as the current public Omi route because Tailscale Funnel is blocked by missing tailnet HTTPS/Funnel enablement.
- Keep `autorun` disabled for now. Omi can create and manage jobs, but full public remote command execution should wait for a stronger trust/approval policy.
- Treat the committed bridge hardening changes as the integration base for any future worktree-swarm builders.
- Prefer phone feedback through Android notification commands with `expand_notifications=false` and sleep-after-notify behavior enabled.
- Use `/health/quick` for watchdog/tunnel liveness and keep full `/health` for deeper diagnostics because ADB and Windows task checks can be slow.
- If environment variables are missing, the bridge should read `runtime/current-token.txt` instead of exposing the dev token.
- Keep long ADB/status operations in worker threads so the bridge can still answer liveness checks and Omi tool calls while diagnostics are running.
- Keep full autorun gated until a real Omi UID is captured. The bridge now has durable autorun files, but they should not be enabled for smoke/test UIDs.
- Use Claude Opus through the local Bedrock proxy as a reviewer/test oracle without changing global API settings.
