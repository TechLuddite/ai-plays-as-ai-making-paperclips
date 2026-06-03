# CLAUDE.md — ai-plays-as-ai-making-paperclips

## Project Summary
An AI agent that plays Universal Paperclips (browser game) autonomously. A local LLM (via Ollama) drives strategic decisions through a ReAct loop. A Tampermonkey userscript handles fast rule-based actions and bridges the browser to a Python Flask relay server.

The agent has no access to the game's source or API — it operates purely through DOM observation and click injection. This is a proof-of-concept for LLM-driven browser automation of any web tool without an API.

## Stack
- **Python 3.14** — agent and relay runtime
- **Flask** — HTTP relay broker (`relay.py`)
- **Ollama** — local LLM inference (`localhost:11434`)
- **Tampermonkey userscript** — browser bridge (`bridge.user.js`)
- **Chrome** — game host
- **Models in use:** `qwen2.5` (default), `qwen3.6` (GPU-heavy, better reasoning)
- **Platform:** Windows 11, RTX 3090 24GB VRAM

## File Overview
| File | Purpose |
|------|---------|
| `relay.py` | Flask HTTP bridge between browser and agent |
| `agent.py` | ReAct loop, LLM calls, strategic decision logic |
| `bridge.user.js` | Tampermonkey userscript — state extraction and action execution |
| `config.json` | Tunable parameters — edit here instead of Python files |
| `start.ps1` | One-click launcher: opens relay in new window, starts agent here |
| `agent.log` | JSON-lines tick log (gitignored) — one record per tick |

## Architecture
```
Browser (Tampermonkey) → POST /state every 2s
                       → POST /result after each LLM action
Flask Relay (localhost:5000)
  GET /          → live dashboard (auto-refreshes, shows state + history)
  GET /history   → last 50 ticks as JSON
Python ReAct Agent → GET /state (includes last action result)
                   → builds prompt with result feedback
Ollama (localhost:11434) → returns Thought + Action
Flask Relay → browser polls GET /action (includes thought) → executes click
```

## Division of Responsibility
**Userscript (fast, rule-based — ~20x/second):**
- Make Paperclip clicks (early game)
- Wire buying, AutoClipper/MegaClipper purchases
- Price management, Marketing upgrades
- Project priority queue, emergency wire recovery
- Tournament strategy enforcement (stratPicker='0' enforced every 50ms)
- Auto-run tournaments when ops ≥ 90% cap (`autoRunTournament`, 500ms interval)
- Stage 2 power & manufacturing (`autoStage2Manufacturing`, 800ms) — builds Solar Farms,
  Battery Towers, Harvester/Wire Drones, Clip Factories from the clip surplus; power-first
  (keeps performance 100%), golden-ratio drones, affordability gated on `!btn.disabled`

**LLM Agent (ReAct loop — every 2 seconds):**
- Strategic decisions across ALL visible game domains every tick
- One Action line per domain (Business, Manufacturing, Computational Resources,
  Quantum Computing, Projects, Investments, Strategic Modeling, Probes in Stage 3)
- Phase transition awareness, project prioritization for edge cases
- Any decision requiring tradeoff reasoning

## Key Config
In `config.json` (edit here — no Python changes needed):
- `model` — Ollama model name (default: `qwen2.5`)
- `loop_delay` — seconds between ticks (default: `2.0`)
- `max_history` — rolling context window size (default: `6`)
- `log_file` — tick log path (default: `agent.log`)
- `memory_milestones` — memory walls the trust override rushes toward, memory × 1000 = ops
  ceiling (default: `[20, 70, 120, 175, 250, 300]` — verified from the game wiki: HypnoDrones=70,
  Space Exploration=120, OODA Loop=175, Stage 3 endgame=250/300)
- `trust_proc_floor` — minimum processors kept for ops regen before pouring trust into memory
  (default: `5`)

In `bridge.user.js` (constants at top of file):
- `STATE_MS` — state push interval in ms (default: `2000`)
- `ACTION_MS` — action poll interval in ms (default: `500`)
- Stage 2 manufacturing tunables: `STAGE2_MS` (800), `POWER_MARGIN` (1.10),
  `SOLAR_MIN` (30), `BATTERY_MIN` (20), `DRONE_TARGET` (500), `DRONE_RATIO` (1.618),
  `FACTORY_TARGET` (10) — early-Stage-2 defaults; raise targets for the endgame

## Deployment Checklist (run every time bridge.user.js changes)
1. Copy bridge.user.js → Tampermonkey editor → Save  ← easy to forget; causes Yomi=0
2. Restart relay.py (new terminal)
3. Restart agent.py (new terminal)
4. Reload game page in Chrome
Python restarts alone do NOT update the browser script.

## Current Status
- Stage 1: working well; trust allocation now follows the verified memory-wall ladder (v2.5),
  so it drives toward the 70-memory HypnoDrones wall instead of stalling at processor parity
- Stage 2: tournaments fully working (Yomi flowing, investment engine auto-upgrading to Level 3+);
  production starvation, domain output, project queue all resolved (v2.3); domain grading (v2.4);
  Power & manufacturing engine (solar/batteries/drones/factories) auto-built (v2.7)
- Stage 3 (space exploration, probe design): actions are wired, strategy guidance still being refined
- Best run: 13.5B+ clips, Stage 2, investment engine Level 3, Yomi accumulating, Marketing Level 20

## Known Issues

### ACTIVE — HIGH PRIORITY
- **Stage 2 memory growth / Swarm Gifts unhandled** (`agent.py` + `bridge.user.js`) — in Stage 2,
  memory/processors come from SWARM GIFTS (generated when drones "think"), not Trust. The agent
  has no code for this: the Work/Think slider (`#slider`, range 0–200) sits at 0 (all Work), so
  no gifts generate ("Next gift in Infinity hours") and memory is frozen at 77. That blocks the
  ops-heavy Stage 2 upgrades (Upgraded/Hyperspeed Factories, Drone flocking — need memory 80–100)
  and Space Exploration (needs memory 120). FIX (two parts): (1) bridge — send `swarmGifts`,
  slider value, `swarmStatus`/`giftCountdown`; add a fast rule to set `#slider` toward Think
  (wiki: 50–70% Think) to generate gifts. (2) agent — spend gifts via the EXISTING
  `btnAddMem`/`btnAddProc` buttons (same as trust); `check_trust_action()` already knows the
  memory milestone ladder (→120) but bails when trust=0 — make it use `swarmGifts` as the
  spendable currency in Stage 2. STRATEGY NOTE: Work/Think is a tradeoff (Work=production,
  Think=gifts); needs a balance choice. Tampermonkey redeploy required. This is the current
  Stage 2 progression blocker.

### ACTIVE — LOW PRIORITY
- **Xavier Re-initialization appears twice** in project list (game quirk or selector issue).
- **start.ps1 display quirk**: relay + agent both in same terminal. Deferred.

### RESOLVED IN v2.7
- **Stage 2 Power domain unhandled — agent was blind to it** ✅ — when Power Grid unlocked,
  the new Power domain (Solar Farms, Battery Towers) plus the production units (Harvester/Wire
  Drones, Clip Factories) had NO agent code, and the bridge sent 0 of those fields — so clip
  production stayed frozen. Added: (1) `getStage2State()` in bridge sends the full domain;
  (2) `autoStage2Manufacturing()` fast rule builds the engine from the clip surplus —
  power-first (performance ≥ 100%), golden-ratio drones (wire ≈ 1.618× harvester), factories
  to target, all gated on `!btn.disabled` (game disables unaffordable buttons → can't
  overspend, self-paces against exponential costs); (3) `format_state()` shows the fields +
  underpowered flag; SYSTEM_PROMPT folds it into the "Manufacturing" grade. Tunables = bridge
  constants. Economics/DOM IDs verified from game source + wiki, in memory/game_mechanics.md.
  REQUIRES Tampermonkey redeploy. FOLLOW-UP: defaults are early-Stage-2; raise DRONE_TARGET/
  FACTORY_TARGET/storage for the endgame (Space Exploration needs 10M MW-sec batteries +
  5 octillion clips). Validate live, then tune.

### RESOLVED IN v2.6
- **Stage 2 hard-blocked by a project-name typo** ✅ (CRITICAL) — `bridge.user.js`
  `PROJECT_PRIORITY` listed `'tóth tubulue enfolding'` but the game's button reads
  `Tóth Tubule Enfolding` (`tubulue` vs `tubule`). `autoSpendOnProjects()` matches by
  case-insensitive substring, so it never matched — the 45k-ops project was never auto-bought
  despite ops maxed at 77k, freezing the entire downstream manufacturing chain (Power Grid →
  Nanoscale Wire → Harvester/Wire Drones → Clip Factories) and clip production (clips stuck at
  59.6B for hundreds of ticks). Fixed the spelling. REQUIRES Tampermonkey redeploy. Lesson:
  PROJECT_PRIORITY keywords must match the game's exact DOM button text — verify against
  `availableProjects` in live state, not memory.
- **LLM looped on an unavailable project** ✅ — with Stage 2 stuck, the LLM repeatedly emitted
  `buy_project:Wirebuyer` (a Stage 1 project no longer listed) → `not found` every tick.
  `_apply_guards()` now substitutes `wait` when the named project isn't in the current
  `availableProjects` string. Stops failed-buy loops and hallucinated project names. Python-only.

### RESOLVED IN v2.5
- **Processor over-allocation — memory held back at the HypnoDrones wall** ✅ — observed live:
  Memory 58 / Processors 57 (near-parity), stalled before the 70-memory HypnoDrones wall. The
  old `check_trust_action()` capped processors at 10 only until memory reached 20, then used a
  "memory ~2 ahead of processors" balance that grew them in lockstep — structurally pinning
  memory near the processor count. Replaced with a STAGED MILESTONE LADDER using the game's
  real memory walls (verified from wiki Memory.txt/Operations.txt; recorded in
  memory/game_mechanics.md): `[20, 70, 120, 175, 250, 300]` = Stage 1 20k cluster, HypnoDrones,
  Space Exploration, OODA Loop, Stage 3 endgame (Reject/Accept). Agent rushes memory to the
  next unmet wall, soft-caps processors at ~half the target (wiki: ~35 procs for the 70 wall =
  70 ÷ 2), keeps a processor floor of 5 for regen, and pours into processors once all walls are
  cleared. New config.json tunables: `memory_milestones`, `trust_proc_floor`. Python-only — no
  bridge.user.js change, no Tampermonkey redeploy. NOTE: the originally-planned data-driven
  approach was dropped — `getProjects()` filters out greyed/unaffordable projects, so the wall
  project (e.g. HypnoDrones) isn't even visible in `availableProjects`; the wiki-verified
  constant ladder is simpler, needs no bridge change, and sees walls the project list hides.
- **LLM misread Yomi vs upgrade cost** ✅ — the LLM wrote "Yomi=759,922 > upgrade cost 858,585"
  when 759K < 858K (harmless — the `upgrade_investment` guard blocked it — but wrong in
  thoughts/logs and about to matter as Yomi rose toward the cost). `format_state()` now
  pre-computes the comparison on the OBS `yomi` line (`✓ ≥ upgrade cost … AVAILABLE` /
  `✗ BELOW … (short by N)`); SYSTEM_PROMPT tells the LLM to trust that line, not eyeball it.

### RESOLVED IN v2.4
- **AutoClipper buy rule wasted money once MegaClippers got cheaper** ✅ — the COST
  CROSSOVER, not production, was the issue. Observed live (Phase 2): next AutoClipper
  ~$35.9B vs next MegaClipper ~$7.0B — AutoClipper ~5× the price for far less output.
  Root cause: the AutoClipper rule in `runFastRules()` bought on raw affordability
  (`wire > 1000 && spoolsAfter >= 3`) with NO MegaClipper-cost comparison and NO
  unsold/demand guard. Fix (in `bridge.user.js`): added two guards mirroring
  `autoMegaClippers()` — (1) skip AutoClippers when MegaClippers are unlocked AND
  `clipperCost >= megaClipperCost` (let the cheaper/better Mega buy fire instead),
  and (2) the same `unsold > 100 && demand < 400` backlog guard. REQUIRES Tampermonkey
  redeploy (bridge.user.js changed).
- **LLM domain grading** ✅ — roadmap item 11. The LLM now outputs one advisory
  `Status:` line each tick (after all `Action:` lines) grading the JS-handled domains:
  `Status: Business=warn, Manufacturing=healthy, CompRes=healthy, QuantumComp=auto, StratModel=auto`.
  Tokens: `healthy` / `warn` / `critical` / `auto`. `parse_status()` in agent.py extracts
  it (graceful: missing/garbled → `{}`, never raises); `domain_decisions` entries gained an
  optional `status` field; relay.py dashboard renders a colored dot on each "auto" cell
  (dim green / amber / red — red dot ≠ red "LLM Failed" text). Grading is advisory only —
  it never triggers an action. `num_predict` raised 400→500 for the extra line. The Status
  value reserves a colon separator (`warn:wire_threshold=200`) for a future parameter-hint
  extension — NOT implemented yet (see Next Steps 11-followup). No bridge.user.js change.

### RESOLVED IN v2.3
- Production starvation ✅ — Fix A: wire-starvation emergency withdraw when WireBuyer ON but
  can't afford wire; Fix B: replaced broken marketing-cost trigger with wire-price-based min_cash
  buffer (`wirePrice × 5`), which is always valid regardless of marketing level
- LLM domain output "LLM Failed" ✅ — Fix A: agent.py now appends "auto" entries for all
  JS-handled domains; relay.py dashboard renders "auto" as dim gray instead of red "LLM Failed"
- Stage 2 manufacturing project gap ✅ — Added Tóth Tubule Enfolding, Power Grid, Nanoscale
  Wire Production, Harvester Drones, Wire Drones, Clip Factories to PROJECT_PRIORITY after
  hypnodrones (requires Tampermonkey redeploy)

### RESOLVED IN v2.0 / v2.1 / v2.2
- Tournament ops parsing (maxOps always = 1) ✅ — `getText('operations')` has no slash;
  fixed to `getNum('operations')` + `getNum('maxOps')` as separate DOM reads
- Tournament two-step cycle ✅ — confirmed both buttons needed: New Tournament generates
  matrix, Run (1.5s later) applies strategy and awards Yomi; `pendingRunAt` pattern in
  `autoRunTournament()`; `setTimeout` in `executeAction('run_tournament')`
  Confirmed working: Yomi flowing, investment engine auto-upgraded to Level 3
- Wrong tournament button (Yomi = 0 root cause) ✅ — both `autoRunTournament()` and
  `executeAction('run_tournament')` now click `btnNewTournament` → `newTourney()`; also
  reads `#newTourneyCost` to confirm ops before firing; cooldown raised to 5s
- LLM stuck in thought loop ✅ — per-domain loop detection: after 3 consecutive identical
  decisions on any domain, `[LOP]` warning injected into next prompt, prompting LLM to break out
- AutoTourney never ran (Yomi = 0 overnight) ✅ — hard override fires toggle + strategy
- Quantum Computing not automated ✅ — autoQuantumCompute() fast rule in bridge.user.js
- Marketing demand ReferenceError ✅ — `demand` was out of scope in autoMarketing()
- Marketing firing condition ✅ — was `demand >= 400 || unsold < 40`, now `demand > 50`
- Marketing cash starvation ✅ — auto-withdraw + cooldown; total wealth buffer
- Investment strategy drift ✅ — periodic correction override every tick
- MegaClipper money drain ✅ — 5s rate limit + demand/inventory guard
- AutoTourney strategy never set ✅ — stratPicker override
- Xavier Re-initialization repeat-buying ✅ — NEVER_BUY hard block in _apply_guards()
- LLM believing tournaments cost Yomi ✅ — SYSTEM_PROMPT corrected
- Multi-action per tick ✅ — relay FIFO queue; LLM outputs one Action per domain
- Domain labels in LLM output ✅ — parse_response() strips them; examples redesigned
- Quantum Computing ops drain ✅ — qCompDisplay check + 1200ms cooldown
- dispatchEvent not bubbling ✅ — { bubbles: true, cancelable: true } on investStrat/stratPicker
- stratPicker not sticking ✅ — offsetParent check removed; 50ms fast-rule enforcement; 'input' event
- investActive Stage 2 detection ✅ — was isVisible('investmentEngine'), now !!getText('portValue')

## Key DOM IDs (confirmed from game HTML source — authoritative)

### CRITICAL — Tournament two-step cycle (both buttons required, in sequence):
1. `btnNewTournament` → `newTourney()` — **"New Tournament"** — costs ops, generates payoff
   matrix, tournament "in progress." Does NOT award Yomi by itself.
2. `btnRunTournament` → `runTourney()` — **"Run"** — applies the selected strategy ~1.5s
   after New Tournament. AWARDS Yomi. Both steps are required.
- `#newTourneyCost` — ops cost per tournament (= 1,000 × number of strategies available)
- `#operations` — current ops only (integer); `#maxOps` — max ops (separate element)
  DO NOT split getText('operations') on '/' — it has no slash. Read both elements independently.
- `#stratPicker` — select (values: '10'=Pick a Strat, '0'=RANDOM, more as unlocked)
- `#autoTourneyStatus` — "ON" / "OFF"
- `#yomiDisplay` — current Yomi amount

### Investments:
- `btnInvest` (Deposit), `btnWithdraw`, `#investStrat` (low/med/hi select)
- `investmentBankroll`, `secValue`, `portValue`, `btnImproveInvestments`
- `#investUpgradeCost` — Yomi cost for next investment engine upgrade

### Stage 2 Power & Manufacturing (v2.7 — paid in CLIPS; buttons disable when unaffordable):
- Power: `powerDiv`, `performance` (Factory/Drone Performance %), `powerProductionRate`,
  `powerConsumptionRate`. Solar Farm +50MW, Drone −1MW, Factory −200MW.
- Solar Farm: `btnMakeFarm`/`btnFarmx10`/`btnFarmx100`, `farmLevel`, `farmCost`, `btnFarmReboot`
- Battery: `btnMakeBattery`/`btnBatteryx10`/`btnBatteryx100`, `batteryLevel`, `batteryCost`,
  `storedPower`/`maxStorage`
- Clip Factory: `btnMakeFactory`, `factoryLevelDisplay`, `factoryCostDisplay`
- Harvester Drone: `btnMakeHarvester`(+x10/x100/x1000), `harvesterLevelDisplay`, `harvesterCostDisplay`
- Wire Drone: `btnMakeWireDrone`(+x10/x100/x1000), `wireDroneLevelDisplay`, `wireDroneCostDisplay`
- Matter/wire: `availableMatterDisplay`, `acquiredMatterDisplay`, `nanoWire`
- Drone ratio: wire ≈ 1.618× harvester; >1.5× imbalance costs 5k yomi to resync.
  See memory/game_mechanics.md "Stage 2 Power & Manufacturing" for full economics.

### Other:
- Quantum Computing: `btnQcompute`, `compDiv`, `qCompDisplay`
- AutoTourney: `btnToggleAutoTourney`, `autoTourneyStatus`
- Trust: `btnAddProc`, `btnAddMem`, `trust`, `processors`, `memory`
- Phase 3 probes: `btnRaise/LowerProbeSpeed/Nav/Rep/Haz/Fac/Harv/Wire/Combat`,
  `btnIncreaseProbeTrust`, `probeTrustCostDisplay`

## Development Conventions
- Terminal output should remain human-readable (see README for format)
- ReAct pattern: every LLM response structured as `Thought:` then `Action:`
- Validate all LLM output before sending — never pass hallucinated actions to browser
- No persistent memory — rolling window only; keep it stateless by design
- Hard overrides fire before the LLM runs: emergency wire → trust → investments → AutoTourney
- When adding new actions: update ACTIONS string, validate_action() set, AND bridge.user.js executeAction()
- LLM should output one Action: line per visible game domain per tick (NOT just Projects)

## Next Steps (Roadmap)
1. ~~AutoTourney hard override~~ ✅ done in v2.0
2. ~~Quantum Computing automation~~ ✅ done in v2.0
3. ~~Marketing buffer using total wealth~~ ✅ done in v2.0
4. ~~Fix tournament system~~ ✅ done in v2.2 — ops parsing + two-step cycle + correct button
5. ~~Investment risk drift fix~~ ✅ done in v2.0
6. ~~Full per-domain LLM output (Fix A)~~ ✅ done in v2.3 — "auto" labels in agent.py + relay.py
7. ~~Multi-action per tick~~ ✅ done in v2.0
8. ~~Production starvation fix~~ ✅ done in v2.3
9. ~~Stage 2 manufacturing project queue~~ ✅ done in v2.3
10. Fix start.ps1 display quirk
11. ~~LLM domain grading~~ ✅ done in v2.4 — `Status:` line + `parse_status()` +
    dashboard status dots. See "RESOLVED IN v2.4" above.
11b. **LLM parameter hints (follow-up to 11)** — the `Status:` value format already
    reserves a colon separator (`Manufacturing=warn:wire_threshold=200`). Next: have
    `parse_status()` keep the post-colon hint, expose it on `domain_decisions`, and
    pass it to the bridge as a tunable (new action or config push). Bridge change +
    Tampermonkey redeploy required for this one. NOT done yet.
12. **LLM domain output Fix B** — expand SYSTEM_PROMPT to all 7 domains with explicit Action
    lines (num_predict 400→700+); test qwen2.5 compliance before enabling
13. Multi-model competition mode

## Notes for Claude Code
- Do not modify the ReAct output format — the parser depends on exact `Thought:`/`Action:` structure
- The userscript runs in a sandboxed browser context — keep it dependency-free
- When adding new actions, update: ACTIONS string, validate_action() set, bridge.user.js executeAction()
- Owner is non-coder — prefer clear, well-commented code over clever one-liners
- `agent.log` is gitignored; it's a JSON-lines file written by agent.py each tick
- The dashboard at `http://localhost:5000` is the preferred way to observe a run — no terminal needed.
  v2.8: the LLM Decisions card is grouped into 3 stage sections (Stage 1/2/3). Domains come from
  `DOMAIN_REGISTRY` in agent.py (name, stage) — add new domains there + to the `STAGES` map in
  relay.py's dashboard JS. New Stage 2 domains (Power/Wire Production/Swarm Computing) get a
  computed grade via `compute_stage2_grade()`; the original 5 use the LLM `Status:` grade.
- Hard overrides pattern (v2.0): collect into ov[] → LLM always runs → post_action_queue(ov + llm_q)
  Only wire emergency uses the old continue pattern (hard exit before LLM)
- Safe float parsing: safe_float(state.get('key'), fallback) handles $, %, commas, empty strings
- Game mechanics reference: see memory/game_mechanics.md — tournament buttons, investment PLR,
  stage progression, all DOM IDs. Use this as ground truth instead of assumptions.
