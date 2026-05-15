# Omi Codex Bridge Checklist

Mission: keep the Omi -> Codex -> PC/Android bridge usable, quiet on the phone, and restartable after PC boot.

- [x] Local bridge runs on `127.0.0.1:8766`.
- [x] Public Omi webhook route works through the current Cloudflare quick tunnel.
- [x] Android phone status/notification path works over ADB without expanding notifications.
- [x] Android quiet mode is enforced: no stay-awake guard, no volume wake guard, safe timeout profile.
- [x] Startup watchdog exists through the user Startup shortcut fallback.
- [x] Autorun is gated by trusted Omi uid settings before any automatic job start.
- [x] Watchdog uses a quick health endpoint so slow Android checks do not cause false restarts.
- [x] Bridge can recover its token from `runtime/current-token.txt` when launched without env wiring.
- [x] Test suite passes.
- [x] Current project state report exists in `PROJECT_STATUS.md`.
- [!] Tailscale Funnel blocked - tailnet HTTPS/Funnel certificates are not enabled in Tailscale admin settings.
- [x] Commit or otherwise seal the current dirty worktree before any worktree-swarm builder run.
- [x] Push local commits to GitHub so `origin/master` matches local `master`.
- [ ] After the user opens Omi on the phone, paste/update the current setup URL from `runtime/omi-setup.private.html` if the quick tunnel changes.
- [ ] Capture the real Omi phone uid and put it in `OMI_CODEX_TRUSTED_UIDS` before enabling trusted autorun.
- [ ] Decide whether Cloudflare quick tunnel stays primary or Tailscale Funnel should be fixed in Tailscale admin settings.
