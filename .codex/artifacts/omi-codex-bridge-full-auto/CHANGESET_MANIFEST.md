# Changeset Manifest

Mission: Omi/Codex bridge full-auto hardening.

Status: bridge hardening is sealed as the integration base after tests and doctor checks.

Owned areas:

- `omi_codex_bridge/*` - bridge API, Android status/notification, runner status notifications.
- `scripts/*` - doctor, stack startup, watchdog, setup helpers.
- `tests/*` - bridge and Android quiet-channel coverage.
- `README.md`, `OMI_AGENT_MAP.md`, `PHONE_READY_NEXT.md`, `.env.example` - setup and operating notes.
- `CHECKLIST.md`, `WORKLOG.md`, `DECISIONS.md` - full-auto execution trail.

Verification evidence:

- `python -m pytest -q` -> 29 passed.
- `scripts/start_stack.ps1 -Port 8766` -> local bridge healthy, Android quiet profile applied, Cloudflare quick tunnel healthy.
- `scripts/doctor.ps1` -> core bridge, Android quiet channel, Omi manifest, setup endpoint OK; Tailscale Funnel blocked.
- Live `show_on_android` tool call -> delivered through ADB.
- Live realtime webhook "pokaz na telefonie" -> delivered through ADB and phone remained `Dozing`.

Swarm eligibility:

- Future worktree-swarm builder branches may start from this clean integration base.
