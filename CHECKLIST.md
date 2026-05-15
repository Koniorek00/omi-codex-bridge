# Omi Codex Bridge Checklist

Mission: keep the Omi -> Codex -> PC/Android bridge usable, quiet on the phone, and restartable after PC boot.

- [x] Local bridge runs on `127.0.0.1:8766`.
- [x] Public Omi webhook route works through the current Cloudflare quick tunnel.
- [x] Android phone status/notification path works over ADB without expanding notifications.
- [x] Android quiet mode is enforced: no stay-awake guard, no volume wake guard, safe timeout profile.
- [x] Startup watchdog exists through the user Startup shortcut fallback.
- [x] Test suite passes.
- [!] Tailscale Funnel blocked - tailnet HTTPS/Funnel certificates are not enabled in Tailscale admin settings.
- [x] Commit or otherwise seal the current dirty worktree before any worktree-swarm builder run.
- [ ] After the user opens Omi on the phone, paste/update the current setup URL from `runtime/omi-setup.private.html` if the quick tunnel changes.
- [ ] Add a stronger authenticated queue/run policy before enabling full remote autorun from public Omi traffic.
