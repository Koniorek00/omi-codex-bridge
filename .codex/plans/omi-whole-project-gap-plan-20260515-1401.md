# Plan: Omi Whole Project Gap Plan
**Created:** 2026-05-15T14:01:30+02:00
**Status:** Complete
**Risk Level:** Medium
**Reversal Cost:** Low to medium. Most work is docs, checks, git sync, and additive hardening; remote push is reversible by later commits.
**Skills Orchestrated:** elite-planner

---

## 1. Goal (Restated)
Create a clear, normal project report for the whole Omi/Codex bridge state: what works, what is missing, what is blocked, what is next, and what still needs execution. Then start closing the highest-value gaps without creating chaos.

## 2. Definition of Done
- [x] A living plan exists in `.codex/plans/` and lists current state, gaps, and next tasks.
- [x] A simple user-facing status report exists in the repo.
- [x] Project checklist shows done, pending, and blocked items.
- [x] Current code remains verified with `python -m pytest -q`.
- [x] Local connections are checked and the result is recorded.
- [x] Git state is clean or every dirty file is explained.
- [x] GitHub/remote sync is either completed or marked blocked with a concrete reason.
- [x] Existing behavior remains intact: Omi bridge, phone notifications, Obsidian REST, Codex queue, trusted autorun gate, quick health.

## 3. Reconnaissance Notes
- Files read:
  - `CHECKLIST.md`
  - `DECISIONS.md`
  - `WORKLOG.md`
  - `README.md`
  - repo root file listing
  - git status/log/remote
- Current source state:
  - `omi-codex-bridge` is on `master`.
  - Local branch is ahead of `origin/master` by 6 commits.
  - Tests pass: `33 passed`.
  - Local connections pass: core skills, workflow boundary, Codex Cockpit, Omi Bridge, Obsidian REST, Claude direct/proxy.
- Key dependencies / call sites:
  - `omi_codex_bridge/main.py` FastAPI app.
  - `omi_codex_bridge/config.py` env/token/workspace config.
  - `omi_codex_bridge/phone.py` Android/Omi notification path.
  - `scripts/start_stack.ps1`, `scripts/doctor.ps1`, `scripts/start_local_bridge.ps1`.
- Existing conventions to match:
  - Keep `CHECKLIST.md`, `DECISIONS.md`, `WORKLOG.md` as project tracking artifacts.
  - Keep autorun disabled unless explicitly trusted.
  - Prefer quiet Android operation.
  - Use `/health/quick` for liveness and full `/health` for diagnostics.
- Blast radius:
  - Public Omi webhook behavior.
  - Local bridge startup/watchdog.
  - Obsidian memory path.
  - Android phone notification behavior.
  - GitHub/remote deployment state.

## 3a. Capability Inventory
**Skills discovered from `.agents/skills`:** 11

**Skills selected for this task:**
| Skill / Tool | Why selected | Used in stage(s) | Fit score |
|---|---|---:|---:|
| elite-planner | User explicitly requested it; owns plan, gap map, checklist, gated execution | 1-5 | 10/10 |
| Git CLI | Current gap is local commits not on remote; git status/log/push are exact tools | 2, 5 | 9/10 |
| Pytest | Existing verification suite for bridge behavior | 1, 5 | 9/10 |
| Omi local doctor scripts | Verifies bridge, tunnel, phone, Obsidian, manifest | 1, 5 | 9/10 |

**Skills considered but not used right now:**
| Skill | Why not selected now |
|---|---|
| codex-process-hygiene | No current runaway process symptom during this stage |
| obsidian-vibe-coding | Obsidian REST is already checked; no note-writing task is required yet |
| worktree-swarm | Now unblocked, but user did not ask to spawn agents; future optional stage |
| github skill/plugin | Git CLI is enough for status/push unless push or PR fails |

**Tools / plugins available or relevant:**
- `git`
- `python -m pytest`
- PowerShell project scripts
- `check-local-connections.ps1`
- `run-daily-doctor.ps1`
- Obsidian Local REST API
- Cloudflare quick tunnel fallback

**Gaps in capability:**
- Tailscale admin setting cannot be fixed locally unless the user has admin access and wants that path.
- Real Omi phone uid cannot be guessed; it must come from an actual Omi request/log.
- Full public autorun security needs product decisions, not just code.

## 4. Assumption Ledger
| # | Assumption | Confidence | If wrong -> impact | Validation |
|---|---|---:|---|---|
| 1 | `omi-codex-bridge` is the main code repo for this project | High | Plan misses side apps | Current workspace has one child git repo and daily doctor targets it |
| 2 | Cloudflare quick tunnel is acceptable fallback while Tailscale Funnel is blocked | High | Public Omi route may be considered incomplete | Doctor reports Cloudflare OK; checklist marks Tailscale blocked |
| 3 | Autorun should stay off until trusted UID and stronger security are decided | High | Remote code execution risk | Current config and decisions keep autorun disabled |
| 4 | Branch should be synced to GitHub when local work is stable | Medium | Remote remains stale if not pushed | Git status shows ahead 6 |

## 5. Risks & Unknowns
| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---:|---:|---|---|
| Remote push fails due credentials/network | Medium | GitHub stays stale | Try `git push`; if blocked, record exact error | Planner/Git CLI |
| Tailscale Funnel remains blocked | High | Public route depends on Cloudflare | Keep Cloudflare fallback documented | Planner |
| Omi tunnel URL changes | Medium | Phone-side Omi app points to old URL | Update setup URL after user opens Omi | User + planner |
| Enabling autorun too early | Medium | Security risk | Keep autorun off, trusted UID gate, manual run flow | Planner |
| Background Omi jobs mutate repo | Low | Dirty worktree confusion | Check job queue and git status before/after work | Planner |

## 6. Non-Goals (Explicit)
- Do not enable full public autorun now.
- Do not force Tailscale admin changes from local scripts.
- Do not install or change phone wake guards unless user requests visible phone control.
- Do not spawn worktree-swarm agents unless user explicitly asks for agents/swarm work.
- Do not store secrets or tokens in markdown.

## 7. Rollback Plan
- **Per-stage revert:** use normal git revert for committed repo changes.
- **Data safety:** no runtime token files committed; `runtime/` remains ignored.
- **Remote push:** if pushed and bad, revert with a new commit rather than rewriting remote history.
- **Point of no return:** none in current planned stages.

## 8. Strategy
First make the state readable: plan, status report, checklist. Then close the practical gap that blocks sharing: remote sync. Keep verification simple and repeatable: pytest, local connection check, git status. Defer product/security choices that require the user's real phone UID or Tailscale admin access.

## 9. Stages

### Stage 1: Write State Report And Checklist
- **Intent:** Make current state and gaps clear in markdown.
- **Delegated to:** elite-planner
- **Inputs to skill:** current git status, existing `CHECKLIST.md`, `DECISIONS.md`, `WORKLOG.md`, test/local connection evidence.
- **Expected output:** `PROJECT_STATUS.md`, updated checklist, this plan.
- **Changes:** docs only.
- **Must not break:** no source code changes.
- **Implementation steps:**
  - [x] Create `PROJECT_STATUS.md`.
  - [x] Update `CHECKLIST.md` with remaining gaps.
  - [x] Run tests and local connection check.
- **Verification gate:**
  - [x] `python -m pytest -q`
  - [x] `check-local-connections.ps1`
  - [x] `git diff --check`
- **Status:** Complete
- **Verified:** Yes
- **Evidence:** `python -m pytest -q` -> 33 passed. `check-local-connections.ps1` -> core skills OK, workflow boundary OK, Codex Cockpit OK, Omi Codex Bridge OK, Obsidian REST OK, Claude direct/proxy OK. `git diff --check` -> exit 0.
- **Notes / deviations:** None.

### Stage 2: Sync Stable Work To GitHub
- **Intent:** Remove the "local only / ahead 6" gap.
- **Delegated to:** planner direct with Git CLI.
- **Inputs:** clean git status, passing tests, remote `origin`.
- **Expected output:** branch pushed or blocked reason recorded.
- **Changes:** remote git state only.
- **Must not break:** local clean state.
- **Implementation steps:**
  - [x] Confirm clean status.
  - [x] Run `git push origin master`.
  - [x] Verify branch no longer ahead, or record blocker.
- **Verification gate:**
  - [x] `git status -sb`
  - [x] `git log --oneline --decorate -3`
- **Status:** Complete
- **Verified:** Yes
- **Evidence:** `git push origin master` -> `a14bb42..62540da master -> master`. Pre-push status was `ahead 7`.

### Stage 3: Phone/Omi Final Setup
- **Intent:** Close remaining setup tasks that need live phone/Omi context.
- **Delegated to:** future planner/user assisted.
- **Changes:** likely runtime/Omi app config, not code.
- **Implementation steps:**
  - [ ] Open/update Omi app with current setup URL if Cloudflare URL changed.
  - [ ] Capture real Omi `uid` from a request/log.
  - [ ] Add trusted UID only if autorun is intentionally enabled later.
- **Verification gate:**
  - [ ] `scripts/doctor.ps1`
  - [ ] real Omi phrase smoke test
- **Status:** Deferred
- **Verified:** No
- **Evidence:** Needs user phone/Omi interaction.

### Stage 4: Tailscale Funnel Decision
- **Intent:** Decide whether to keep Cloudflare fallback or fix Tailscale Funnel in admin settings.
- **Delegated to:** user/admin + planner.
- **Implementation steps:**
  - [ ] If desired, enable HTTPS/Funnel cert support in Tailscale admin.
  - [ ] Run `scripts/start_tailscale_funnel.ps1`.
  - [ ] Update docs/checklist if Tailscale becomes primary.
- **Verification gate:**
  - [ ] `tailscale funnel status`
  - [ ] public `/health/quick` check
- **Status:** Blocked
- **Verified:** No
- **Evidence:** Current doctor says Tailscale Funnel blocked by tailnet HTTPS/cert settings.

### Stage 5: Final Whole-State Verification
- **Intent:** Confirm no chaos after changes.
- **Delegated to:** planner direct.
- **Implementation steps:**
  - [x] Run pytest.
  - [x] Run local connection check.
  - [x] Check git clean.
  - [x] Update plan delivery report.
- **Verification gate:**
  - [x] All prior gates green or explicitly blocked/deferred.
- **Status:** Complete
- **Verified:** Yes
- **Evidence:** `python -m pytest -q` -> 33 passed. `check-local-connections.ps1` -> all listed checks OK. `check-worktree-candidate.ps1` -> READY, dirtyCount 0. `git status -sb` -> `## master...origin/master`.

## 10. Final Whole-Task Verification
- [x] Re-read original request top to bottom; every ask addressed.
- [x] All Definition of Done items checked with evidence.
- [x] `WORKLOG.md`, `CHECKLIST.md`, and `DECISIONS.md` updated.
- [x] No unchecked non-deferred checklist item remains.
- [x] Regression criteria re-verified end-to-end.
- [x] Assumption Ledger reviewed.
- [x] No debug code, scratch files, commented experiments, unused assets.
- [x] "If this shipped now, what would embarrass us?" answered and fixed or recorded.

## 11. Delivery Report
- What was done: Created an elite-planner living plan, created `PROJECT_STATUS.md`, updated `CHECKLIST.md`, pushed local work to GitHub, and verified the whole current state.
- Skills/tools used and what each contributed: `elite-planner` structured the plan/gaps; Git CLI committed and pushed; Pytest verified app behavior; local connection scripts verified bridge/Obsidian/Cockpit/Claude.
- How verified: `python -m pytest -q` -> 33 passed; local connection check -> all OK; worktree candidate -> READY dirtyCount 0; git status -> synced with `origin/master`.
- Known limitations / deferred items: Tailscale Funnel is blocked by admin/cert settings; real Omi UID still needs capture before trusted autorun; Omi phone setup URL may need refresh if Cloudflare URL changes.
- Decisions the user should know about: Autorun remains off by default; Cloudflare quick tunnel is current public fallback; worktree-swarm is ready but should only be used when explicitly requested.

## 12. Change Log
- 2026-05-15T14:01:30+02:00 - Created initial living plan from current project state.
- 2026-05-15T14:06:00+02:00 - Completed Stage 1: created `PROJECT_STATUS.md`, updated `CHECKLIST.md`, and verified tests/local connections/diff check.
- 2026-05-15T14:08:00+02:00 - Completed Stage 2: pushed local `master` to GitHub.
- 2026-05-15T14:11:00+02:00 - Completed final whole-state verification and delivery report.
