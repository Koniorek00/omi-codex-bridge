# Omi Codex Bridge Decisions

## 2026-05-15

- Keep phone operation sleep-friendly by default. Do not install display wake guards or force long screen timeouts unless the user explicitly asks for a visible remote-control session.
- Use Cloudflare quick tunnel as the current public Omi route because Tailscale Funnel is blocked by missing tailnet HTTPS/Funnel enablement.
- Keep `autorun` disabled for now. Omi can create and manage jobs, but full public remote command execution should wait for a stronger trust/approval policy.
- Treat the committed bridge hardening changes as the integration base for any future worktree-swarm builders.
- Prefer phone feedback through Android notification commands with `expand_notifications=false` and sleep-after-notify behavior enabled.
