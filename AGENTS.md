# Omi Codex Bridge Agent Notes

Before editing this project, read `OMI_AGENT_MAP.md` and then verify the specific files from source.

This bridge turns Omi transcript, memory, and chat-tool requests into queued local Codex jobs. Keep `OMI_CODEX_AUTORUN=0` unless the user explicitly accepts voice-triggered execution risk.

Do not commit or print the bridge token from `runtime\current-token.txt`, Omi API keys, OAuth URLs, or app API keys. It is okay to document tokenized URL shapes with `<token>`.

Use these checks after changes:

```powershell
python -m pytest -q
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
```

The Obsidian project memory index is:

```text
F:\programy\Obsidian\Codex Vault\Codex\Codex\Vibe Coding\omi-codex-bridge\index.md
```
