# Omi Research Notes

Last checked: 2026-05-14

## Sources Checked

- Official Omi Chat Tools docs: https://docs.omi.me/doc/developer/apps/ChatTools
- Official Omi Integration Apps docs: https://docs.omi.me/doc/developer/apps/Integrations
- Official Omi Notifications docs: https://docs.omi.me/doc/developer/apps/Notifications
- Official Omi Developer API docs: https://docs.omi.me/doc/developer/api/overview
- Official Omi MCP docs: https://docs.omi.me/doc/developer/mcp/introduction
- Official Omi CLI docs: https://docs.omi.me/doc/developer/cli/introduction
- Omi docs index: https://docs.omi.me/llms.txt
- Omi GitHub repo/issues/releases: https://github.com/BasedHardware/omi
- Omi feedback board and Reddit community search.

## Findings That Matter For This Bridge

- Chat tools are the right Omi-native route for conversational commands. Manifest tool names should stay action-oriented and descriptions must explicitly say when to use each tool.
- Omi supports a top-level `chat_messages` manifest section. The bridge now exposes it so Omi can treat this app as capable of app chat messages.
- Omi has an official direct notification API: `POST https://api.omi.me/v2/integrations/{app_id}/notification?uid=...&message=...` with `Authorization: Bearer <app secret>`. The bridge now supports this when `OMI_APP_ID` and `OMI_APP_SECRET` are configured.
- ADB notifications remain useful as a local fallback because they work without Omi app secrets and were verified on Android serial `RZCXB128SKH`.
- Real-time transcript processors must return quickly, dedupe repeated segments, and track `session_id`; the bridge already does this.
- GitHub issues around Omi webhook reliability mention auto-disable after sustained failures and retry/backoff. This bridge should keep endpoints fast, return concise JSON, and monitor public manifest/setup health.
- Community feedback points toward advanced workflows built from webhook triggers into Notion/Obsidian/agent systems. The bridge should keep Obsidian export and quick Codex presets as first-class paths.
- MCP and `omi-cli` are now official surfaces for Omi data access. Future bridge work should add optional local checks for `omi-cli` and an Omi MCP setup note, but without storing API keys.

## Current Implemented Actions

- Added `chat_messages` to the Omi tool manifest.
- Added optional official Omi notification delivery with ADB fallback.
- Added manifest/phone notification state to `/health` and `check_bridge_status`.
- Made `scripts/doctor.ps1` verify required Omi tools and `chat_messages`, not just the existence of one tool.

## Next Useful Improvements

- Add optional `omi-cli` detection to doctor after the user installs/authenticates it.
- Add an optional Omi MCP setup checker that verifies only presence/config shape, never prints keys.
- Add webhook latency logging and a simple failure counter so we can catch reliability issues before Omi auto-disables the app.
- Add a GitHub issue/PR voice preset later: collect 3-5 segments, then create a local queued Codex job or GitHub issue.
