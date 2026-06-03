# Changelog

All notable changes to this project are documented here.

---

## [2.7.2] - 2026-06-03

### Fixed
- **Momentum (and other late-Stage-2 projects) never auto-purchased** (`bridge.user.js`) —
  `PROJECT_PRIORITY` was missing the Stage 2 production upgrades, so `autoSpendOnProjects()`
  couldn't see them. Most important: **Momentum** (20k creativity) lets Factory/Drone
  Performance exceed 100% (up to ~1000%) — a huge Stage 2 accelerator — and it sat affordable
  but unbought (676k creativity available). Added: Momentum, Theory of Mind, Swarm Computing,
  Upgraded Factories, Hyperspeed Factories, Drone flocking (collision avoidance / alignment /
  adversarial cohesion).
- **Yomi-cost projects couldn't be auto-bought** (`bridge.user.js`) — `getProjectCost()` only
  parsed ops/creativity/trust, so any yomi-priced project (Swarm Computing 36k yomi,
  Adversarial Cohesion 50k yomi) returned `null` and was skipped. Added yomi parsing + a yomi
  affordability check in `autoSpendOnProjects()`.
  **Requires Tampermonkey redeploy.**

### Known gaps surfaced (not yet fixed — see CLAUDE.md Known Issues)
- **Stage 2 memory growth / Swarm Gifts unhandled** (HIGH) — in Stage 2 memory/processors come
  from Swarm Gifts (drones "thinking"), not trust. The Work/Think slider sits at Work (0), so
  no gifts generate and memory is frozen at 77 — blocking the ops-heavy upgrades (need 80–100)
  and Space Exploration (needs 120). Next feature.
- **Clip-cost projects** (e.g. Self-correcting Supply Chain "1 sextillion clips") use word
  suffixes `getProjectCost()` can't parse — they won't auto-buy.
- **Space Exploration** is intentionally NOT auto-bought (it ends Stage 2; needs deliberate
  timing once memory ~120 and a battery bank are ready).

---

## [2.7.1] - 2026-06-03

### Fixed
- **Stage 2 builder cold-start deadlock** (`bridge.user.js`) — the v2.7 rule used
  `performance < 100` as its "build solar" trigger, but performance reads **0 when there are
  no consumers yet** (nothing to perform). So at cold start the condition was always true: it
  poured the spendable clip pool into Solar Farms (7 built, ~53B clips) until the next farm
  (~32B) was unaffordable, then did nothing every tick — the drone/factory builders were also
  gated behind `performance`, so production never started (clipRate stuck at 0). Rewrote the
  rule to drive off **power production vs consumption** instead of performance:
  - Build solar only on a real deficit (`production < consumption × margin`) or as a small
    cold-start baseline (`SOLAR_MIN` lowered 30 → 5; the cost curve is steep).
  - Build consumers into **spare power** (headroom = production − consumption), balancing
    factories vs drones by target progress so it can't build "all drones, no factory."
  - Baseline solar now **falls through** when unaffordable instead of returning, so the cheap
    first factory (100M clips) isn't blocked.
  - Batteries demoted to lowest priority (built only once consumers are at target) — they were
    about to eat the factory budget.
- **Bridge now sends `unusedClips`** (`unusedClipsDisplay`) — the actual Stage 2 spendable
  pool. The existing `clips` field is all-time total (never decreases), which hid that the 7
  farms had drained the spendable pool from ~59B to ~6.7B. `format_state()` shows it, and no
  longer falsely flags "UNDERPOWERED" at cold start (only when consumers exist).
  **Requires Tampermonkey redeploy.**

---

## [2.7] - 2026-06-03

### Added
- **Stage 2 Power & Manufacturing engine** (`bridge.user.js`, `agent.py`) — the agent had
  no code for the Power domain (Solar Farms, Battery Towers) or the Stage 2 production units
  (Harvester Drones, Wire Drones, Clip Factories). The bridge sent 0 of these fields, so the
  agent was blind to the whole domain and clip production was frozen.
  - **Bridge state extraction** — new `getStage2State()` sends `performance`,
    `powerProduction`, `powerConsumption`, `farmLevel`/`farmCost`, `batteryLevel`/`batteryCost`,
    `storedPower`/`maxStorage`, `factoryLevel`/`factoryCost`, `harvesterLevel`/`harvesterCost`,
    `wireDroneLevel`/`wireDroneCost`, `availableMatter`, `acquiredMatter`, `nanoWire`.
  - **Bridge fast rule** `autoStage2Manufacturing()` — builds the whole engine from the clip
    surplus, in priority order: (1) power first — add Solar Farms whenever Factory/Drone
    Performance < 100% or production < consumption × margin; (2) baseline solar + cheap
    battery storage; (3) Harvester/Wire Drones toward a target, kept at the golden-ratio mix
    (wire ≈ 1.618 × harvester, since >1.5× imbalance disorganizes the swarm); (4) Clip
    Factories toward a target, only while fully powered. Affordability is gated on
    `!btn.disabled` (the game disables unaffordable build buttons), which makes overspending
    impossible and self-paces against the exponentially rising costs.
  - **Tunables** — constants at the top of `bridge.user.js`: `STAGE2_MS`, `POWER_MARGIN`,
    `SOLAR_MIN`, `BATTERY_MIN`, `DRONE_TARGET`, `DRONE_RATIO`, `FACTORY_TARGET`. Defaults are
    conservative early-Stage-2 values (wiki-based); raise them for the endgame.
  - **Agent visibility** — `format_state()` shows the power/manufacturing fields with an
    "UNDERPOWERED" flag when performance < 100%; SYSTEM_PROMPT lists the engine as
    JS-handled and folds it into the LLM's "Manufacturing" Status grade.
  All facts (DOM IDs, power economics, costs, drone ratio) verified from the game HTML source
  and the wiki Stages strategy doc; recorded in `memory/game_mechanics.md`.
  **Requires Tampermonkey redeploy.**

### Still active
- **Xavier Re-initialization appears twice** in the project list (game quirk).
- **start.ps1 display quirk** — relay and agent share a terminal window.

---

## [2.6] - 2026-06-03

### Fixed
- **Stage 2 hard-blocked by a project-name typo** (`bridge.user.js` — CRITICAL) — the entire
  Stage 2 manufacturing chain stalled because `PROJECT_PRIORITY` listed the project as
  `'tóth tubulue enfolding'` but the game's actual button text is **`Tóth Tubule Enfolding`**
  (`tubulue` vs `tubule`). `autoSpendOnProjects()` matches by case-insensitive substring, so the
  keyword never matched and the 45k-ops project was never auto-bought — even with ops maxed at
  77,000. Because every later manufacturing project (Power Grid, Nanoscale Wire Production,
  Harvester Drones, Wire Drones, Clip Factories) sits behind it, the whole chain was frozen
  (clips stuck at 59.6B for hundreds of ticks). Fixed the spelling. **Requires Tampermonkey
  redeploy.**
- **LLM looped on an unavailable project** (`agent.py`, `_apply_guards()`) — with Stage 2
  stuck, the LLM repeatedly emitted `buy_project: Wirebuyer` (a Stage 1 project no longer in
  the list) → `not found` every tick. Added a guard: `buy_project` is substituted with `wait`
  when the named project isn't present in the current `availableProjects` string. Stops the
  failed-buy loop and any future hallucinated project name. Python-only — no redeploy.

### Note
- v2.5's staged memory ladder was confirmed working in the same logs: memory climbed past the
  70-memory HypnoDrones wall to 77, and the Yomi-vs-cost OBS hint read correctly ("short by N").

---

## [2.5] - 2026-06-03

### Fixed
- **Processor over-allocation — memory was being held back** (`agent.py`,
  `check_trust_action()`) — observed live: Memory 58 / Processors 57 (near-parity), with
  progression stalled at the 70-memory HypnoDrones wall. The old logic capped processors at
  10 only until memory reached 20, then switched to a "memory ~2 ahead of processors" balance
  that let processors climb in lockstep with memory — structurally pinning memory near the
  processor count. But the game needs memory FAR ahead. Replaced with a STAGED MILESTONE
  LADDER driven by the game's actual memory walls (verified from the wiki):
  - `MEMORY_MILESTONES = [20, 70, 120, 175, 250, 300]` — 20 (Stage 1 20k-ops cluster),
    70 (HypnoDrones, ends Stage 1), 120 (Space Exploration → Stage 3), 175 (OODA Loop),
    250/300 (Stage 3 endgame, Reject/Accept paths).
  - The agent rushes memory to the next unmet wall, soft-capping processors at ~half the
    target (wiki: ~33–35 processors for the 70 wall → 70 ÷ 2 = 35). When processors are at/
    over that cap, every trust point goes to memory. A small processor floor (5) is kept so
    ops can still regenerate. Once all walls are cleared, remaining trust goes to processors.
  - New `config.json` tunables: `memory_milestones`, `trust_proc_floor`.
  - Python-only change — no `bridge.user.js` change, no Tampermonkey redeploy.
- **LLM misread of Yomi vs upgrade cost** (`agent.py`) — the LLM repeatedly wrote
  "Yomi=759,922 > upgrade cost 858,585" when 759K is BELOW 858K (harmless because the
  `upgrade_investment` guard blocks it, but inaccurate in thoughts/logs and about to matter
  as Yomi climbed toward the cost). `format_state()` now pre-computes the comparison on the
  OBS `yomi` line: "✓ ≥ upgrade cost … AVAILABLE" or "✗ BELOW upgrade cost … (short by N)".
  SYSTEM_PROMPT now tells the LLM to trust that line instead of eyeballing the math.

### Reference
- Recorded the authoritative memory-wall ladder (wiki Memory.txt / Operations.txt) into
  `memory/game_mechanics.md` as ground truth for trust allocation.

### Still active
- **Xavier Re-initialization appears twice** in the project list (game quirk).
- **start.ps1 display quirk** — relay and agent share a terminal window.

---

## [2.4] - 2026-06-02

### Added
- **LLM domain grading** (`agent.py`, `relay.py`) — the LLM now outputs one advisory
  `Status:` line each tick, after all `Action:` lines, grading the health of the five
  JS-handled (auto) domains it doesn't directly control:
  `Status: Business=warn, Manufacturing=healthy, CompRes=healthy, QuantumComp=auto, StratModel=auto`
  - Tokens: `healthy` (rules coping) / `warn` (worth watching) / `critical` (a problem
    the rules aren't catching) / `auto` (domain not active this phase, or nothing to judge).
  - New `parse_status()` in `agent.py` extracts the line into `{domain: grade}`. It is
    graceful by design — a missing or malformed `Status:` line returns `{}` and never
    raises, so grading can never break a tick. Short-name aliases (e.g. `Quantum` →
    `Quantum Computing`) and unknown tokens are handled safely.
  - `domain_decisions` entries gained an optional `status` field (the grade for auto
    domains; `None` for LLM-owned domains, which are judged by their action instead).
  - `relay.py` dashboard renders a small colored dot on each "auto" cell: dim green =
    healthy, amber = warn, red = critical. The red dot is distinct from the red
    "LLM Failed" *text* — the dot means the JS is running but the LLM flags a concern.
    No status → no dot, just the dim gray "auto" as before.
  - The `Status:` value format reserves a colon separator (`warn:wire_threshold=200`) for
    a future parameter-hint extension — not implemented yet (see roadmap), but the format
    won't have to change to add it.
  - `num_predict` raised 400 → 500 to leave room for the extra line.
  - **No `bridge.user.js` change** — grading is purely a Python/dashboard concern; no
    Tampermonkey redeploy was required for this part.

### Fixed
- **AutoClipper buy rule wasted money once MegaClippers got cheaper** (`bridge.user.js`) —
  the real issue was the COST CROSSOVER, not production volume. Observed live (Phase 2):
  the next AutoClipper cost ~$35.9B while the next MegaClipper cost ~$7.0B — i.e. an
  AutoClipper had become ~5× the price of a MegaClipper while producing far less. Root
  cause: the AutoClipper rule in `runFastRules()` bought on raw affordability
  (`wire > 1000 && spoolsAfter >= 3`) with NO comparison to `megaClipperCost` and NO
  unsold/demand guard, so it would spend funds on the strictly-worse unit the moment cash
  recovered (e.g. after an investment withdraw). Fix: added two guards mirroring
  `autoMegaClippers()` — (1) skip AutoClippers when MegaClippers are unlocked AND
  `clipperCost >= megaClipperCost` (let the cheaper/better Mega buy fire instead), and
  (2) the same `unsold > 100 && demand < 400` backlog guard.
  **Requires Tampermonkey redeploy** (copy bridge.user.js → editor → save → reload page).

### Still active
- **Xavier Re-initialization appears twice** in the project list (game quirk).
- **start.ps1 display quirk** — relay and agent share a terminal window.

---

## [2.3] - 2026-06-01

### Fixed
- **Production starvation — wire-starvation emergency** (`agent.py`) — added a bare `if`
  block (not `elif`) that fires when WireBuyer is ON but wire < 100 and funds can't cover
  two spools while investments hold > 5× the spool price. Previous logic checked
  `is_emergency()` which returned False when WireBuyer was ON, even if it couldn't afford
  wire. "On" ≠ able to buy.
- **Production starvation — marketing-cost trigger** (`agent.py`) — the old withdraw
  condition (`funds < marketing_cost AND bankroll > 2× marketing_cost`) permanently failed
  at Marketing Level 20 because the cost (~$52M) required $104M in the bankroll to trigger.
  Replaced with a general wire-price-based cash buffer: `min_cash = wirePrice × 5`. Keeps
  at least 5 spool-equivalents of cash available at all times; withdraws from investments
  when cash falls below that threshold. Scales naturally as wire prices change and is
  independent of marketing level.
- **Dashboard "LLM Failed" for JS-handled domains** (`agent.py`, `relay.py`) — dashboard
  showed "LLM Failed" in red for all 5 JS-handled domains (Business, Manufacturing, Comp
  Resources, Quantum Computing, Strategic Modeling) because `domain_decisions` only included
  LLM-owned domains. `agent.py` now appends every domain to `domain_decisions` every tick:
  - LLM-owned domains get their actual action label
  - Active JS-handled domains get `"auto"` (dim gray on dashboard)
  - Domains not yet unlocked for the current game phase get `"n/a"` (near-invisible dark gray)
  `relay.py` dashboard updated with matching color tiers: red "LLM Failed" is now reserved
  for genuine LLM failures on domains it owns.
- **Stage 2 manufacturing project priority gap** (`bridge.user.js`) — `PROJECT_PRIORITY`
  was missing all six Stage 2 manufacturing projects. Added in correct ops-cost order after
  `hypnodrones`: Tóth Tubule Enfolding (45k) → Power Grid (40k) → Nanoscale Wire
  Production (35k) → Harvester Drones (25k) → Wire Drones (25k) → Clip Factories (35k).
  **Requires Tampermonkey redeploy** (copy bridge.user.js → editor → save → reload page).

### Still active
- **Xavier Re-initialization appears twice** in the project list (game quirk).
- **start.ps1 display quirk** — relay and agent share a terminal window.

---

## [2.2] - 2026-05-30

### Fixed
- **Tournament ops parsing** (`bridge.user.js` — CRITICAL) — `autoRunTournament()` split
  `getText('operations')` on `'/'` expecting `"21,000 / 21,000"`. But `#operations` is only
  the current ops (`"21,000"`); `#maxOps` is a separate DOM element. `parts[1]` was always
  `undefined`, so `maxOps` fell back to `1`, making `maxOps > 100` permanently false.
  `newTourney()` was never called in any run. Fixed by reading `getNum('operations')` and
  `getNum('maxOps')` as independent element reads.
- **Tournament two-step cycle** (`bridge.user.js` — CRITICAL) — confirmed from live gameplay:
  both buttons are required in sequence to earn Yomi.
  1. `btnNewTournament` → `newTourney()`: spends ops, generates payoff matrix ("in progress")
  2. `btnRunTournament` → `runTourney()`: applies selected strategy ~1.5s later, awards Yomi
  `autoRunTournament()` now sets `pendingRunAt` after clicking New Tournament; fires Run on
  the next 500ms interval once the delay expires. `executeAction('run_tournament')` uses
  `setTimeout(1500)` for the same sequence.
  Confirmed working: Yomi flowing, investment engine auto-upgraded to Level 3.

### Changed
- `autoSpendOnProjects()` ops read simplified — was splitting a string that never had a slash;
  now uses `getNum('operations', 0)` directly, matching the rest of the codebase.

---

## [2.1] - 2026-05-30

### Added
- **Dashboard LLM Decisions card** (`relay.py`) — new card between Live State and Tick History
  showing a static 8-column table (Business, Manufacturing, Computational Resources, Quantum
  Computing, Projects, Investments, Strategic Modeling, Probes) with the last 3 ticks of LLM
  decisions per domain. Opacity fades by age (latest full, older dimmed). Domain missing from
  `domain_decisions` shows "LLM Failed" in red; real actions green; nothing/wait dim gray.
- **Per-domain loop detection** (`agent.py`) — `domain_loop_tracker` dict tracks the last 5
  actions per domain. After 3 consecutive identical decisions on any domain, `[LOP]` prints in
  terminal and a `⚠ LOOP ALERT` block injects into the next tick's prompt with targeted
  break-out guidance. Resets cleanly on new-game detection.
- **Deployment checklist** (`CLAUDE.md`) — documents that Tampermonkey must be manually
  updated (copy-paste entire file) after every `bridge.user.js` change. Python restarts alone
  do not affect the browser script.

### Fixed
- **Tournament button** (`bridge.user.js`) — `autoRunTournament()` and
  `executeAction('run_tournament')` were clicking `btnRunTournament` ("Run"), which only
  displays strategy results and does not start a tournament. Changed to `btnNewTournament`.
  Also reads `#newTourneyCost` to confirm ops are sufficient; cooldown raised 2s → 5s.
- **stratPicker not sticking** (`bridge.user.js`) — `set_strategy_random` action was checking
  `el.offsetParent === null` and bailing silently; removed check. Added both `'change'` and
  `'input'` events. 50ms fast-rule enforcement in `runFastRules()` wins over game render resets.
- **`investActive` Stage 2 detection** (`bridge.user.js`) — was `isVisible('investmentEngine')`
  (unreliable; div reports hidden). Changed to `!!getText('portValue')` which is reliably
  present when investments are active.

### Changed
- `post_action_queue()` (`agent.py`) — accepts `domain_decisions` list and `overrides_str`
  kwargs; posts them in the action payload for the relay dashboard to consume.
- Relay `receive_action()` — extracts and stores `domain_decisions` + `overrides` in a rolling
  3-entry `last_decisions_history`; attached as `_decisions_history` on `GET /state`.
- `active_domains` logic in main loop — builds ["Projects", "Investments", "Probes"] per stage
  and zips with `llm_display` to populate `domain_decisions` for the dashboard.

---

## [2.0] - 2026-05-29

### Added
- **Multi-action queue** — relay now holds a FIFO queue instead of a single pending action.
  Agent can post multiple actions per tick; browser dequeues one per poll.
- **Parallel override architecture** — all domain overrides (trust, investment, AutoTourney,
  tournament strategy) collect into `ov[]` without blocking the LLM. Every tick: overrides
  fire *and* the LLM runs; the final queue is `ov + llm_q` posted together.
- **Per-domain LLM output** — agent prompts for one `Action:` line per active game domain
  (Projects, Investments, Probes) every tick so no domain is ever skipped.
- **`nothing` action** — per-domain display-only no-op. Shows in `[ACT]` terminal output
  and rolling history; never posted to relay. LLM uses this instead of `wait` when a
  domain needs no action this tick.
- **AutoTourney hard override** — if `autoTourneyOn` is in state and not "ON", fires
  `toggle_auto_tourney` automatically before the LLM runs.
- **Tournament strategy override** — if `stratPicker != '0'` (RANDOM not selected yet),
  fires `set_strategy_random` automatically so Yomi accumulates from day one of Stage 2.
- **Auto-withdraw override** — if cash < marketing cost but investment bankroll >
  2× marketing cost, fires `invest_withdraw` and sets a 3-tick deposit cooldown to prevent
  immediate re-deposit before fast rules can spend the freed cash.
- **Investment strategy drift correction** — checks every tick; if current strategy ≠
  target, corrects immediately (`med` until engine level 5, then `hi`).
- **Quantum Computing automation** (`bridge.user.js`) — `autoQuantumCompute()` fires
  `btnQcompute` on every 50ms fast-rule tick when `compDiv` is visible. Converts chip charge
  to ops continuously; free and safe to spam.
- **MegaClipper rate limit and demand guard** (`bridge.user.js`) — 5-second cooldown between
  purchases; skips when unsold > 100 and demand < 400 to prevent cash drain after withdrawals.
- **Processor cap** — processors hard-capped at 10 until memory ≥ 20, ensuring the ops
  ceiling is large enough for core Stage 2 projects before regen speed is prioritised.
- **Hard block: Xavier Re-initialization and Quantum Temporal Reversion** — added to
  `NEVER_BUY` list in `_apply_guards()`. Xavier costs 100k creativity and resets all
  processor/memory trust to zero; QTR resets game state backward. Both are catastrophic.
- **`invest_deposit` and `invest_withdraw` both blocked from LLM** — fully override-managed;
  LLM output choosing either is silently replaced with `wait`.
- **Badge redesign** (`bridge.user.js`) — expanded from a minimal 220px label to a 380px
  panel with rgba background, full state readout (stage, clips, funds, wire + LOW warning,
  demand, unsold, yomi, ops, AutoTourney status), LLM thought (200 chars, word-wrapped),
  and last 3 actions with tick numbers.

### Fixed
- **Marketing ReferenceError** (`bridge.user.js` — CRITICAL) — `demand` variable was not
  in scope inside `autoMarketing()`. Marketing never fired in strict mode. Fixed by declaring
  `const demand = getNum('demand')` inside the function.
- **Marketing firing condition** — condition was `demand >= 400 || unsold < 40`, which was
  always false in Stage 2 with hundreds of millions of unsold clips. Changed to `demand > 50`
  (marketing raises the demand ceiling — gating it on high demand was backwards).
- **Marketing total wealth buffer** — affordability now checks `funds + bankroll + stocks`
  instead of cash only. Actual click still requires `funds >= cost` since the game needs cash.
- **Quantum Computing ops drain** — reads `qCompDisplay` for negative ops; 1200ms cooldown
  prevents runaway compute cycles that deplete the ops pool.
- **`dispatchEvent` bubbling** — `{ bubbles: true, cancelable: true }` added for `investStrat`
  and `stratPicker` selects so the game registers programmatic changes.
- **LLM inline `#` comments in action names** — stripped in `parse_response()` before
  validation (e.g. `upgrade_investment  # costs Yomi` → `upgrade_investment`).
- **Domain labels in LLM action output** — `parse_response()` strips `"Projects: wait"` →
  `"wait"` as a safety net; SYSTEM_PROMPT redesigned with concrete examples to prevent
  domain labels appearing at source.
- **Duplicate "3." numbering** in SYSTEM_PROMPT — renumbered priorities 1–5.
- **Stage vs Phase terminology** — corrected throughout SYSTEM_PROMPT and ACTIONS string
  (the game uses "Stage", not "Phase").

### Changed
- **SYSTEM_PROMPT intel overhaul** based on wiki-accurate game mechanics:
  - Tournament mechanics corrected: tournaments *cost* ops and *award* Yomi. The LLM
    previously believed tournaments cost Yomi, causing it to avoid them entirely (Yomi = 0
    overnight despite AutoTourney being nominally active).
  - Probe guidance improved: hazard remediation sweet spot 5–6 points, self-replication
    priority for early Stage 3, when to raise combat vs drifters.
  - Investment lifecycle clarified: `invest_deposit` moves all cash (all-or-nothing);
    only bankroll (not stocks) can be withdrawn.
  - Clear separation of what the agent handles automatically vs what the LLM decides.
- **Response format redesign** — concrete stage-by-stage examples replace the
  `<Domain: action OR wait>` template style that caused domain labels to appear in output.
- **`num_predict`** increased 180 → 400 to give the LLM room for multi-line domain output.
- **relay.py action queue** — replaced single `pending_action` string with FIFO
  `action_queue = []`; accepts `{"queue": [...]}` (multi) and legacy single-action format.

### Resolved from v1.9 known issues
- AutoTourney never ran (Yomi = 0 overnight) ✅
- Marketing severely underinvested despite large portfolio ✅
- Investment risk drifting back to Low Risk ✅
- Quantum Computing not automated ✅
- Multi-action per tick ✅
- Duplicate "3." in SYSTEM_PROMPT ✅

### Still active
- **Price strategy** — current rules push demand toward 500% (ceiling). Targeting ~100%
  demand at a higher unit price may generate better revenue. Under investigation.
- **Xavier Re-initialization appears twice** in the project list (game quirk).
- **start.ps1 display quirk** — relay and agent share a terminal window. Use the manual
  two-terminal start as the reliable alternative.

---

## [1.9] - 2026-05-25

### Changed
- Renamed `paperclips_bridge.user.js` to `bridge.user.js` for naming consistency with `relay.py` and `agent.py`
- Version bumped to 1.9 across all files

---

## [1.8] - 2026-05-25

### Fixed
- Trust allocation now uses a balanced processor/memory ratio (target: memory ~2 ahead of processors)
- Previously the agent stacked memory or processors one-sidedly, causing either slow ops regen or a tiny ops cap
- Hard Python-level override forces correct trust spending regardless of LLM output
- `getProjects()` now filters greyed-out (unaffordable) projects using opacity detection — LLM no longer sees or attempts locked projects
- `Improved AutoClippers` added as #1 priority in the auto-spend queue

### Changed
- Marketing threshold lowered to 1.2x cost (was 1.5x) — fires more readily in early game
- Wire requirement for marketing dropped to 200 (was 500)
- System prompt trust section rewritten to explain balanced ratio rather than memory-only priority

---

## [1.7] - 2026-05-25

### Added
- Full audit against actual game HTML source (`index2.html`) — corrected all element IDs
- `#projectListTop` added as project container (projects render here, not just `#projectsDiv`)
- `adCost` span correctly read for marketing cost
- `wireBuyerStatus` detection — wire buying and emergency logic skip when WireBuyer project is ON
- MegaClippers auto-purchased with same wire/fund safety rules as AutoClippers
- Phase detection: `spaceDiv` visible = phase 3; `compDiv` visible = phase 2
- Wire detection: reads `nanoWire` in phase 3, falls back to `wire` in phase 1
- `add_processor` and `add_memory` added as valid LLM actions
- `wireBuyerOn` included in state so LLM understands wire is managed
- `browsercraft.com` match rules added to userscript (alternative host)
- Game URL documented in agent header and prompt

### Changed
- Agent prompt updated: LLM told not to worry about wire when WireBuyer is active
- `trust > 0` now shows contextual hint in OBS output

---

## [1.6] - 2026-05-25

### Added
- `autoMarketing()` — buys marketing upgrades automatically when funds/wire/inventory conditions are safe
- Trust-cost and creativity-cost projects now handled in `autoSpendOnProjects()` alongside ops-cost projects
- `getProjectCost()` parses ops, creativity, and trust costs from button text
- Rate limiting on project auto-spend (one purchase per 1.5 seconds)
- Expanded project priority list with trust-cost projects (Limerick, Lexical Processing, etc.)
- LLM action polling rate increased to every 500ms (was 1500ms)

---

## [1.5] - 2026-05-25

### Added
- `autoSpendOps()` — automatically spends operations on projects when ops are at 80%+ capacity
- Priority queue for ops spending: WireBuyer → Wire Extrusion → Even Better AutoClippers → Creativity → etc.
- Ops cost parsed directly from button text to determine affordability

### Fixed
- Operations no longer sit at cap, wasting regen cycles

---

## [1.4] — Userscript / 2026-05-25

### Fixed
- Wire threshold raised to 1000 inches (was 500)
- Autoclipper purchase now requires wire > 1000 AND 3-spool funds buffer (was wire > 300, 10$ buffer)
- `wireSpoolsAffordable` calculation prevents buying autoclippers that would leave you unable to restock wire
- Wire buying now correctly skips when wire > 1000 to preserve funds

---

## [1.4] — Agent / 2026-05-25

### Fixed
- `safe_float()` helper replaces all fragile float parsing — handles `$`, `%`, `inches`, `None`, commas
- Wire flag now only shows `⚠ EMPTY` at 0 and `⚠ LOW` under 50 — no longer false-alarming on healthy wire
- LLM no longer told wire is empty when it has 700+ inches
- `validate_action()` catches hallucinated actions (e.g. `use_operations`) and substitutes `wait`
- WireBuyer added as #1 priority project in prompt
- OBS output shows `↑ raise price` and `↓ lower price` contextual hints

---

## [1.3] - 2026-05-24

### Added
- `getNum()` helper in userscript — clean numeric extraction, no NaN surprises
- Price raising: if unsold < 10 and demand > 100%, raise price automatically (was lower-only)
- Emergency wire handler looks for Beg for More Wire project button and clicks it directly

### Fixed
- Autoclipper purchase requires $10 buffer — no longer drains funds needed for wire
- Wire buying maintains $5 buffer

---

## [1.2] - 2026-05-24

### Added
- Emergency detection in Python: wire=0 and funds<$5 skips LLM and forces `buy_project:Beg for More Wire`
- `⚠ EMPTY` and `⚠ BROKE` flags in OBS terminal output
- Trust-cost project awareness in LLM prompt (Beg for More Wire costs Trust, not money)
- `browsercraft.com` added to userscript `@match` rules

### Fixed
- `is_emergency()` now uses safe parsing — no longer crashes on `None` wire values
- Wire buffer logic prevents simultaneous wire and autoclipper purchases leaving funds at zero

---

## [1.1] - 2026-05-24

### Added
- `runFastRules()` fires at 20x/second for mechanical actions
- Auto-click Make Paperclip (while autoclippers < 5)
- Auto-buy wire when stock < 100, with $5 buffer
- Auto-buy AutoClipper when affordable, with $10 buffer
- Auto-lower price when unsold > 50

### Changed
- LLM prompt updated: make_paperclip, buy_wire, buy_autoclipper removed from LLM action list
- LLM now focused on strategy only: pricing, marketing, projects
- `LOOP_DELAY` reduced to improve responsiveness

---

## [1.0] - 2026-05-24

### Initial release

- Flask relay (`relay.py`) bridging browser and agent
- Tampermonkey userscript reading game DOM state and executing actions
- Python ReAct agent querying local Ollama model
- ReAct loop: Observation → Thought → Action printed to terminal
- Supports: make_paperclip, lower_price, raise_price, buy_wire, buy_autoclipper, buy_marketing, buy_project, wait
- State includes: clips, unsoldClips, funds, wire, clipPrice, demand, marketing, autoclippers, trust, memory, processors, operations, creativity, availableProjects
