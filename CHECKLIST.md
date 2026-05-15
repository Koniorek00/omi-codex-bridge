# Omi Codex Bridge Checklist

Mission: keep the Omi -> Codex -> PC/Android bridge usable, quiet on the phone, and restartable after PC boot.

- [x] Local bridge runs on `127.0.0.1:8766`.
- [x] Public Omi webhook route works through the current Cloudflare quick tunnel.
- [x] Android phone status/notification path works over ADB without expanding notifications.
- [x] Android quiet mode is enforced: no stay-awake guard, no volume wake guard, safe timeout profile.
- [x] Startup watchdog exists through the user Startup shortcut fallback.
- [x] Autorun is gated by trusted Omi uid settings before any automatic job start.
- [x] Bridge records known Omi UIDs from tool and webhook requests.
- [x] Protected `/api/known-uids` endpoint lists captured UID sightings for setup/trust decisions.
- [x] Trusted UID and autorun settings can now persist through `runtime/trusted-uids.txt` and `runtime/autorun.enabled`.
- [x] Trusted autorun setup script validates UID edits, can remove UIDs, and refuses unsafe enable/disable conflicts.
- [x] Dashboard shows known Omi UIDs and marks trusted ones.
- [x] Polish Omi/Codex trigger parser handles normal diacritics like `żeby`, `połącz`, `sprawdź`, and `aplikację`.
- [x] Claude Opus API and local proxy are verified for test/review use.
- [x] Watchdog uses a quick health endpoint so slow Android checks do not cause false restarts.
- [x] Bridge can recover its token from `runtime/current-token.txt` when launched without env wiring.
- [x] Test suite passes.
- [x] Current project state report exists in `PROJECT_STATUS.md`.
- [x] Aria Companion phone path verified: Android UI message -> Claude/Aria response -> Codex task queued/completed -> phone notification ACKed.
- [x] Aria Companion APK updated so Codex routing persists and the foreground service switches to the current app device key after relaunch.
- [!] Tailscale Funnel blocked - tailnet HTTPS/Funnel certificates are not enabled in Tailscale admin settings.
- [x] Commit or otherwise seal the current dirty worktree before any worktree-swarm builder run.
- [x] Push local commits to GitHub so `origin/master` matches local `master`.
- [ ] After the user opens Omi on the phone, paste/update the current setup URL from `runtime/omi-setup.private.html` if the quick tunnel changes.
- [ ] Generate Omi MCP API key in the phone app and save it with `F:\ag projects\apps\tools\omi-v2-local\Set-OmiMcpApiKey.ps1`.
- [ ] Wait for the first real Omi phone request, then review `/api/known-uids` and put the real uid in `OMI_CODEX_TRUSTED_UIDS` only if trusted autorun is intentionally enabled.
- [!] `$PersonalBrowser` extension backend blocked in current Codex session - Chrome extension/native host now check out, but Codex needs reload before `agent.browsers.get("extension")` can be verified.
- [ ] Decide whether Cloudflare quick tunnel stays primary or Tailscale Funnel should be fixed in Tailscale admin settings.
