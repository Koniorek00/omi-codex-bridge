# Plan: Omi Tony Stark Assistant Map
**Created:** 2026-05-15T15:04:50+02:00
**Status:** In Progress
**Risk Level:** High
**Reversal Cost:** Medium; most changes are scripts/config, but autorun touches remote command execution.
**Skills Orchestrated:** Claude+API, elite-planner, obsidian-vibe-coding, android-connection

---

## 1. Goal (Restated)
Make the user's Omi + Android phone + PC + Codex system behave like a persistent personal agent: voice/text from Omi can reach this PC, create Codex jobs, supervise project work, report back to the phone, use Obsidian memory, and eventually use Omi cloud memory plus Claude/local models as test/review backends.

## 2. Definition of Done
- [x] Claude/Bedrock API is verified directly and through the local proxy.
- [x] Android connection is verified without keeping the phone awake.
- [x] Omi Codex Bridge local and public endpoints are verified.
- [x] Omi v2 MCP/agent foundation is installed and tested on Windows-compatible parts.
- [ ] Autorun/trusted UID survives restarts and has an explicit setup script.
- [ ] Obsidian has a compact system map and runbook note.
- [ ] Phone-side Omi app setup gaps are clear and actionable.
- [ ] A real Omi MCP API key is stored and tested when available.
- [ ] End-to-end real Omi request from phone is verified, not only synthetic HTTP calls.
- [ ] `$PersonalBrowser` extension backend is connected with `openTabs()`.

## 3. Reconnaissance Notes
- Files read: bridge config/start scripts, watchdog/startup scripts, Omi v2 MCP/agent files, Android skill, Claude API skill, Obsidian skill.
- Current bridge: local `127.0.0.1:8766`, public Cloudflare tunnel, 14 Omi tools, Android ADB OK.
- Current phone: `RZCXB128SKH` over USB, remote profile also exists, screen is locked/AOD, no lock bypass.
- Current Claude: `us.anthropic.claude-opus-4-6-v1`, proxy on `127.0.0.1:8787`, verified.
- Current blockers: missing `OMI_API_KEY`; no confirmed real Omi UID for trusted autorun; phone app settings require unlock.
- Browser gap: Chrome extension and native host now verify, but current Codex session still exposes only the in-app browser backend; `$PersonalBrowser` needs Codex app reload before extension control can be proven.

## 3a. Capability Inventory
| Skill / Tool | Why selected | Used in stages | Fit |
|---|---|---:|---:|
| Claude+API | Local Claude Opus test/review backend | 1, 6 | 9/10 |
| elite-planner | Living plan and staged execution | all | 10/10 |
| obsidian-vibe-coding | Durable memory cockpit | 4 | 9/10 |
| android-connection | Owned phone ADB/scrcpy/headless control | 2, 5 | 10/10 |
| pytest / npm / uv | Regression gates | 1, 3, 6 | 9/10 |

## 4. Assumption Ledger
| # | Assumption | Confidence | If wrong impact | Validation |
|---|---|---:|---|---|
| 1 | `com.friend.ios` is the current Omi/Friend app package. | Medium | Wrong app opened | Package resolver and UI check |
| 2 | Real Omi UID is not yet captured. | High | Autorun cannot be safely enabled | `/api/known-uids` review |
| 3 | Omi MCP key must be generated inside Omi app. | High | MCP cloud memory blocked | Omi docs/repo and local MCP README |

## 5. Risks & Unknowns
| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Unsafe remote command execution | Medium | High | Trusted UID gate, explicit autorun file |
| Phone locked blocks Omi UI setup | High | Medium | Prepare all scripts, require one unlock only |
| Cloudflare quick tunnel URL changes | Medium | Medium | Watchdog refresh + setup URL file |
| Omi cloud API key missing | High | Medium | Setup script ready, blocked until key exists |
| PersonalBrowser extension backend missing in current session | Medium | Medium | Native host repaired; reload Codex then verify `openTabs()` |

## 6. Non-Goals
- Do not bypass the phone lock or extract app secrets.
- Do not expose ADB publicly.
- Do not disable the trusted UID gate for public autorun.
- Do not replace the full Omi app today; build reliable foundations first.

## 7. Rollback Plan
- Script/config changes can be reverted with git.
- Runtime autorun can be disabled by deleting `runtime/autorun.enabled`.
- Trusted UID list can be cleared by editing/deleting `runtime/trusted-uids.txt`.
- Android changes remain sleep-friendly; no persistent wake/display guard is installed.

## 8. Strategy
First make every existing working path restart-safe and measurable. Then add durable setup switches for autorun/trusted UID, persist the map in Obsidian, and only then attempt phone-side Omi UI setup. Anything requiring a secret or unlocking the phone is prepared but marked blocked until the required user-side action happens.

## 9. Stages

### Stage 1: Claude API Test Backend
- **Intent:** Claude can be used as a test/review backend.
- **Status:** Complete
- **Verification:** Direct test `HTTP 200 LOCAL CLAUDE API WORKS`; proxy test returned `CLAUDE_PROXY_OK`.

### Stage 2: Android Quiet Control
- **Intent:** Phone is reachable without wake loops.
- **Status:** Complete
- **Verification:** Android target `RZCXB128SKH`, `Dozing`, no stay-on, no display blocker.

### Stage 3: Durable Autorun/Trusted UID
- **Intent:** Full-auto can survive PC restart while staying gated to trusted Omi UID.
- **Status:** Complete for infrastructure; blocked for real autorun until real Omi UID is captured.
- **Steps:**
  - [x] Add runtime files `trusted-uids.txt` and `autorun.enabled` support.
  - [x] Add and harden a setup script for trusted UID and autorun toggle.
  - [x] Add tests.
  - [x] Verify config state: autorun false, trusted UID count 0.
  - [x] Verify PC startup entries for Aria, bridge watchdog, and Android keepalive.
  - [ ] Verify live bridge after restart with a real trusted UID.
 - **Evidence:** `pytest -q` passes 37 tests. `scripts/set_trusted_autorun.ps1 -List` reports autorun false and trusted UID count 0.

### Stage 4: Obsidian System Map
- **Intent:** Agents have one memory/runbook entry for the whole system.
- **Status:** Complete
- **Steps:**
  - [x] Create/update Obsidian index note.
  - [x] Create/update current session note.
  - [x] Read back notes.
 - **Evidence:** Obsidian note `Codex/Vibe Coding/omi-tony-stark-assistant/index.md` exists and REST list returns `index.md`; session note created under `Sessions/`.

### Stage 5: Phone Omi App Setup
- **Intent:** Open Omi app and finish settings where possible.
- **Status:** Blocked by lockscreen for UI-only settings
- **Steps:**
  - [x] Identify likely Omi app package: `com.friend.ios`.
  - [x] Open Omi app activity with ADB.
  - [x] Create `open-omi` Android macro.
  - [ ] Open Omi app after unlock or visible control.
  - [ ] Generate/copy MCP key in Omi app.
  - [ ] Save key with `Set-OmiMcpApiKey.ps1`.

### Stage 6: End-to-End Omi Command
- **Intent:** Real voice/text from Omi starts Codex and reports back.
- **Status:** Pending
- **Steps:**
  - [ ] Capture real Omi UID via webhook/tool call.
  - [ ] Trust real UID if user wants full auto.
  - [ ] Test `start_codex_task`.
  - [ ] Test `show_on_android`.
  - [ ] Test job status/output retrieval.

### Stage 6A: Aria Companion Phone Agent Path
- **Intent:** Use the custom Android companion as the working phone surface while Omi MCP/real UID setup remains blocked.
- **Status:** Complete
- **Steps:**
  - [x] Register current native Android companion key.
  - [x] Enable `Route to Codex queue` and phone reply delivery.
  - [x] Send a real message from the Android UI.
  - [x] Confirm Aria/Claude response, Codex task creation, Codex worker completion, and phone notification ACK.
  - [x] Patch companion app so routing persists and the foreground service switches to the current app device key after relaunch.
  - [x] Patch companion doctor so it no longer guesses app-scoped Android IDs from ADB.
  - [x] Build, reinstall, relaunch, and smoke PC -> phone notification delivery.
- **Evidence:** Latest phone command ACKed with `delivery=notification`; latest phone-created Codex task succeeded; phone returned to `Dozing` with no stay-on/display blocker.

### Stage 7: PersonalBrowser Extension
- **Intent:** Agent can use the user's real logged-in Chrome profile through the official extension backend.
- **Status:** Blocked by current Codex session backend list.
- **Steps:**
  - [x] Verify Chrome installed/running.
  - [x] Verify Chrome Codex extension installed/enabled.
  - [x] Repair native host manifest and registry.
  - [x] Re-run native host diagnostic: correct.
  - [ ] After Codex app reload, run `browser.user.openTabs()` through extension backend.
- **Evidence:** Native host diagnostic `correct: true`; extension diagnostic `installed: true`, `enabled: true`; Node REPL backend attempt returns `Browser is not available: extension`.

## 10. Final Whole-Task Verification
- [x] Re-read user request stack.
- [ ] Confirm no non-deferred checklist item remains.
- [x] Run bridge tests, Omi v2 tests, Claude proxy test, Android status, public manifest.
- [x] Confirm Obsidian notes read back.

Latest evidence:
- Bridge tests: 37 passing.
- Omi v2 MCP tests: 14 passing.
- Omi v2 desktop agent tests: 74 passing; build passes.
- Claude proxy: returns `OK`.
- Public manifest: 14 tools, includes `start_codex_task` and `show_on_android`.
- Android: `Dozing`, `mStayOn=false`, `mHoldingDisplaySuspendBlocker=false`.
- Obsidian: `index.md` and `Sessions/` listed.

## 11. Delivery Report
Not complete: blocked by missing Omi MCP API key, phone lock for Omi app settings, no real Omi UID captured, and current Codex session not exposing the repaired Chrome extension backend until reload.

## 12. Change Log
- 2026-05-15T15:04:50+02:00 - Created map from current verified state and earlier unresolved asks.
- 2026-05-15T15:12:00+02:00 - Added durable autorun/trusted UID runtime support and Claude-reviewed remaining blockers.
- 2026-05-15T15:18:00+02:00 - Added Obsidian map/session notes and Android `open-omi` macro.
- 2026-05-15T15:23:00+02:00 - Repaired Chrome native host manifest; marked `$PersonalBrowser` blocked until Codex exposes extension backend after reload.
- 2026-05-15T15:28:00+02:00 - Ran whole-stack verification and recorded remaining blockers.
- 2026-05-15T15:47:00+02:00 - Verified Aria Companion phone-agent path, patched Android service/device-key persistence issue, reinstalled APK, and confirmed quiet phone state.
- 2026-05-15T16:05:00+02:00 - Hardened trusted autorun setup script, added trusted flags to known UID API, and added known UID dashboard panel.
- 2026-05-15T16:15:00+02:00 - Repaired Polish trigger parsing for real diacritics and added regression assertions.
- 2026-05-15T16:00:00+02:00 - Verified Windows startup entries for Aria, Omi bridge watchdog, and Android keepalive; process-hygiene audit found no safe close candidates.
