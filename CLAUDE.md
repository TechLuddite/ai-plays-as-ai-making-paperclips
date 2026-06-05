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
- Auto-run tournaments when ops ≥ 90% cap (`autoRunTournament`, 500ms interval) — but HELD while a
  claimable `PROJECT_PRIORITY` ops-project is affordable-at-cap (`opsProjectWaiting()`, v2.12.11), so
  ops fill to buy the project instead of draining on tournaments. (The agent.py override likewise
  pauses the game's built-in AutoTourney via the `opsProjectWaiting` state flag.)
- Stage 2 power & manufacturing (`autoStage2Manufacturing`, 800ms) — builds Solar Farms,
  Battery Towers, Harvester/Wire Drones, Clip Factories from the clip surplus; power-first
  (keeps performance 100%), golden-ratio drones, affordability gated on `!btn.disabled`

**LLM Agent (ReAct loop — every 2 seconds):**
- Strategic decisions across ALL visible game domains every tick
- One Action line per active LLM-owned domain, in order: Projects, Investments (Stage 2),
  Swarm Computing (Stage 2), Probes (Stage 3); plus a Status grade line for the auto domains
- **Swarm Computing (Stage 2)** — the LLM owns it (v2.9): sets the Work/Think slider
  (set_swarm_think/balanced/work) and spends Swarm Gifts on memory/processors (add_memory/
  add_processor). Swarm Gifts are the Stage 2 "trust". This is deliberately LLM-driven, not a
  JS override — keeping the model central to gameplay.
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
- 🎉 **FIRST COMPLETE RUN (v2.12.8):** the agent played autonomously Stage 1 → 2 → 3 → **100% of the
  universe explored**, reaching the endgame ("Message from the Emperor of Drift" → the player's
  Accept/Reject choice). The agent is blocked from triggering that irreversible finale (NEVER_BUY).
- Stage 1: solid — trust follows the verified memory-wall ladder (v2.5).
- Stage 2: solid — tournaments/Yomi, investment engine, power+manufacturing+swarm all auto (v2.3–2.9).
- Stage 3 (probe design / colonization): bootstrap stall fixed in v2.12 (stage-aware OBS/prompt +
  history reset + deterministic probe-design advisor); v2.12.1–.8 iterated live to survival + full
  colonization — allocate-before-buy, launch vetoes at Haz/Combat < 3, a Combat **reserve** that
  deploys when Drifters attack without gutting Rep, auto-buy of Stage 3 support + Honor projects
  (the repeatable Threnody is NOT auto-bought — it drains yomi), Bored-swarm "Entertain" recovery,
  and the colonization fix (spare trust → Speed × Exploration). See "RESOLVED/CHANGED IN v2.12.x".
- Best run: the first full game (Stage 1 → 100% explored). Earlier peak: 13.5B+ clips in Stage 2.

## Known Issues

### ACTIVE — HIGH PRIORITY
- *(none — the Stage 3 bootstrap stall is addressed in v2.12; see "RESOLVED IN v2.12". Reopen if
  live testing shows the LLM still won't launch probes.)*

### ACTIVE — LOW PRIORITY
- **Dashboard needs further refinement** — the v2.8 stage-grouped layout is a first pass; owner
  will scope specific dashboard changes in a later request. Placeholder until then.
- **Xavier Re-initialization appears twice** in project list (game quirk or selector issue).
- **start.ps1 display quirk**: relay + agent both in same terminal. Deferred.

### RESOLVED IN v2.12.11 (tournaments drained ops that should have gone to claimable projects)
- **Tournaments ran non-stop, starving projects that were claimable once ops filled to the cap** ✅
  (bridge.user.js + agent.py → REDEPLOY + restart agent) — live: ops 17,545/21,000, AutoTourney ON. A
  project costing 90–100% of the ops cap can NEVER be afforded because tournaments fire at 90% of cap
  and drain ops first. TWO ops-drainers ignored waiting projects: the bridge `autoRunTournament()`
  fast-rule AND the `agent.py` override that kept the game's built-in AutoTourney unconditionally ON.
  Fix: new bridge helper `opsProjectWaiting()` (true when a `PROJECT_PRIORITY` ops-project is
  affordable once ops fill to the cap — `cost <= maxOps` — but not bought yet; scans the DOM directly
  incl. disabled/greyed buttons so it sees unaffordable-but-revealed projects, which getProjects()
  filters out). While it holds: `autoRunTournament()` skips, and the bridge sends an `opsProjectWaiting`
  state flag so the agent.py AutoTourney override PAUSES AutoTourney (toggle OFF) instead of forcing it
  ON — re-enabling only when no claimable ops-project remains. Projects costing MORE than maxOps need
  more memory first, so they don't block tournaments (ops sit at the cap, AutoTourney mints Yomi until
  memory grows). Matches the wiki ("switch AutoTourney OFF to save ops for projects"). NOTE: only
  PROJECT_PRIORITY projects are protected — a revealed ops-project NOT in that list (e.g. "New
  Strategy: B100") is neither auto-bought nor blocks tournaments; add it to PROJECT_PRIORITY if it
  should be claimed.

### RESOLVED IN v2.12.10 (AutoClipper/MegaClipper cost-crossover guard was silently dead)
- **AutoClippers kept being bought even when MegaClippers were cheaper** ✅ (bridge.user.js → REDEPLOY)
  — live: AutoClipper $7,783 vs MegaClipper $5,072 (24 Megas owned), yet the fast rule kept buying the
  pricier AutoClipper. The v2.4 cost-crossover guard logic was correct, but its availability check —
  shared with `autoMegaClippers()` — was `isVisible('megaClipperDiv')`, and that container-div id
  doesn't resolve in the live game, so `megaUnlocked` was ALWAYS false → the guard never fired (and
  `autoMegaClippers()` never auto-bought a Mega either; the 24 came from LLM/manual buys). Fix: new
  `megaClipperUnlocked()` helper gates off the CONFIRMED `btnMakeMegaClipper` button id (checks
  `offsetParent` for display AND computed `visibility`), used by both the AutoClipper guard and
  `autoMegaClippers()`. Now once Megas are cheaper, AutoClipper buys are skipped and the cash goes to
  the cheaper/more-productive MegaClipper. Lesson (again, cf. the v2.6 typo): gate off confirmed
  button ids verified against live state, NOT guessed container-div ids.

### RESOLVED IN v2.12.9 (fresh-game stage misdetection — flipped to Stage 2/3 during Stage 1)
- **`getPhase()` used `compDiv` as the Stage 2 marker, but `compDiv` = "Quantum Computing unlocked"
  (mid-STAGE 1)** ✅ (bridge.user.js → REDEPLOY) — live on a freshly-restarted game the agent first
  correctly read Stage 1, then flipped to Stage 2 the instant Quantum Computing was bought, and began
  emitting Stage-2/late-game actions while still in Stage 1. Root cause: `getPhase()` returned 2 on
  `isVisible('compDiv')`, but per game_mechanics.md `compDiv` is the QC panel (unlocked in Stage 1),
  NOT a Stage 2 panel. Meanwhile `getStage2State()` was already gating correctly on
  `powerDiv`/`factoryDiv`. Fix: `getPhase()` now matches — `spaceDiv`→3, `powerDiv`||`factoryDiv`→2,
  else 1 (spaceDiv checked first so it still resolves to 3 even if powerDiv persists into Stage 3).
  Verified NOT the cause: relay does a full state REPLACE (`latest_state = data`, no merge, so no
  stale `colonized` leak), and the Python `get_stage()` fallback only triggers on keys the bridge
  sends per-stage. bridge.user.js only — Python untouched, but restart relay+agent after redeploy.

### CHANGED IN v2.12.8 (ENDGAME reached — protect the final choice)
- **100% of the universe explored** 🎉 (v2.12.7 colonization worked — owner drove colonized 68%→100%).
  The "Message from the Emperor of Drift" endgame sequence appeared. Added a SAFETY: the agent must
  never trigger the irreversible finale, so the LLM `NEVER_BUY` guard now blocks the endgame projects
  — the Emperor message + dialogue boxes, **Accept** (New Game+ restart) / **Reject** (disassemble
  the empire → credits, irreversible without cheats), both Universe choices, the Disassemble chain,
  and the Driftwar Monument. Only the player makes the final Accept/Reject choice. Verified the
  substrings don't false-match any legit Stage 3 buy (Elliptic Hull, Combat, Name the Battles, OODA,
  Strategic Attachment, Glory, Threnody). agent.py only — restart agent, NO redeploy.

### CHANGED IN v2.12.7 (probe design scales past Max Trust 20 — COLONIZATION)
- **Extra trust past 20 now drives colonization (Speed × Exploration)** ✅ (agent.py + config.json —
  restart agent, NO redeploy) — live: the run was saved on survival (owner's manual Haz 10 / Combat
  13) but `colonized` was stuck near 0% because Speed 1 × Exploration 3 ≈ 0 exploration rate. Per
  the wiki (Stages "Stage 3 Strategy"): once the swarm is big and combat is handled, *"increase
  Exploration and Speed to cover the universe"* — matter/exploration rate = **Speed × Exploration**,
  keep **Speed ≥ Exploration**. Implemented a 3-phase budget in `_probe_design_advice()` that scales
  with Max Trust: PHASE 1 pre-launch baseline (15: haz5 rep5 + 1 each in speed/exp/fac/harv/wire);
  PHASE 2 combat reserve (held free until Drifters open combat, then filled to `probe_combat_target`,
  now **8** per wiki — a swarm that outnumbers the drifters needs no more); PHASE 3 colonize — ALL
  trust beyond baseline+combat pours into Speed+Exploration (Speed≥Exp). `buy_to` is the survival
  design before the first launch (quick, low value-drift) and the FULL Max Trust cap after launch
  (to fund colonization). The combat reserve is held free (colonization won't eat it) until Drifters
  appear. NOTE: colonization is now yomi-gated — buying trust to allocate Speed/Exp needs Yomi
  (AutoTourney supplies it). Combat 6-8 is the wiki ceiling; the owner's manual Combat 13 was
  over-invested vs exploring. All targets are config.json tunables.

### CHANGED IN v2.12.6 (owner-specified initial probe design)
- **New initial 20-trust probe allocation** ✅ (agent.py + config.json — restart agent, NO redeploy)
  — owner's spec for the opening design: **1 each** in Speed, Exploration(nav), Factory, Harvester,
  Wire; **5 each** in Self-Replication(rep) and Hazard(haz); **5 in Combat HELD IN RESERVE** until
  combat opens (Drifters appear). That's 15 allocated up front + 5 reserved = 20. Config targets
  changed: haz 6→5, rep 6→5, speed 4→1, nav 4→1, combat 8→5 (aux unchanged at 1). The advisor now
  builds only to 15 (`buy_to` excludes Combat until Drifters), so there is ALWAYS 5 points of cap
  headroom: when combat opens it BUYS the reserved 5 and allocates Combat — **no Rep sacrifice**
  (the rebalance that nearly lost the last run is now just a maxed-out safety net). Reordered
  `_probe_design_advice()`: allocate-first → buy (deploy reserve) → combat-rebalance (only when
  truly maxed) → launch. Aux (Fac/Harv/Wire) are now part of the initial design, not deferred.

### RESOLVED IN v2.12.5
- **Endlessly-repeatable honor project drained millions of yomi** ✅ (bridge.user.js → REDEPLOY) —
  v2.12.4 added `Threnody for the Heroes` to `PROJECT_PRIORITY`, but the wiki confirms it is
  **endlessly repeatable** (creat 50k +10k each buy, **yomi 20k +4k each buy**, for a fixed 10k
  honor), so `autoSpendOnProjects()` bought it every 1.5s and bled millions of yomi. Worse, the
  cost parser returns only the FIRST cost (creativity), so it never even saw the yomi half — it
  spent yomi invisibly. Fix: (1) REMOVED `threnody for the heroes` from `PROJECT_PRIORITY` — an
  endlessly-repeatable project must never be on a 1.5s auto-loop; buy it deliberately (LLM/manual)
  for honor. (2) Added a **YOMI_RESERVE** (1M) guard to `autoSpendOnProjects()`: it now parses any
  yomi cost straight from the button text (catching the second cost the parser misses) and skips a
  project if buying it would drop yomi below the reserve — general protection for the yomi that
  funds `increase_probe_trust`. `Glory` (one-time, 10k yomi) stays in auto-buy.

### RESOLVED IN v2.12.4 (live-test follow-up to v2.12.3)
Live: the swarm COLLAPSED to probeTotal 0 (9.9B born, all dead) under 1.9B Drifters with Combat
still 0, Honor −227. Three issues:
- **Advisor relaunched into death every tick instead of fixing Combat** ✅ (agent.py — restart) —
  the LAUNCH branch ran BEFORE the combat-rebalance branch, so with probeTotal 0 + Drifters present
  it kept emitting `launch_probe` (fresh probes slaughtered at Combat 0) and never rebalanced.
  REORDERED `_probe_design_advice()`: the combat emergency (lower Rep → raise Combat when trust is
  maxed) now runs BEFORE launch, so Combat reaches target FIRST, then it launches into a defended
  position. Also extended the `launch_probe` guard: veto launches when Drifters present AND Combat
  < 3 (not just Haz < 3) — fresh probes are slaughtered (combat table: Combat 0-2 ≈ 0 kills). OBS
  probeTotal=0 flag updated to say "raise Combat first" under attack.
- **Two must-buy HONOR projects ignored** ✅ (bridge.user.js → REDEPLOY) — `Threnody for the Heroes
  of Durenstein` (50k creat +20k yomi → +10,000 honor) and `Glory` (200k ops +30k yomi → honor per
  victory) were not in `PROJECT_PRIORITY`. Honor buys Max Trust (`increase_max_trust`), the only way
  to add Combat without sacrificing another stat — so these are the strategic unlock. Added both
  (the cost parser reads the first/non-yomi cost; the yomi half is tiny and always affordable).
- **"0 in 4 probe areas" + Memory release** ✅ — Fac/Harv/Wire at 0 is wiki-CORRECT under 20 trust
  (a big swarm self-provides; every point is needed for Haz/Combat/Rep/Speed/Nav). The advisor now
  fills Fac/Harv/Wire to 1 each (probe_aux_max) but ONLY once Max Trust is raised past the core
  budget (via the honor projects) — so they stay 0 at 20 trust (correct) and fill in later. Added
  `memory release` to the LLM NEVER_BUY guard (it dismantles memory for clips — pointless/harmful;
  it also has no parseable cost so the bridge never auto-bought it).

### RESOLVED IN v2.12.3
- **Combat unallocated when Drifters attack & trust is maxed** ✅ (Python-only — restart agent, NO
  redeploy) — live: Drifters 3.7M attacking, losing probes, but **Combat 0** with Trust 20/20 fully
  allocated (Rep 12, Haz 6, Speed 1, Exp 1). The advisor had no free points, couldn't raise Max
  Trust (Honor 0 — Honor only comes from killing Drifters), and so returned None — nothing happened.
  Added a **REBALANCE** branch to `_probe_design_advice()`: when Drifters present and Combat <
  target and trust is maxed, free a point by lowering an OVER-allocated stat (Self-Replication
  first — the swarm is already huge; never Hazard), which the allocate-first block then spends on
  Combat next tick. Net: it walks Rep down and Combat up (e.g. Rep 12→4, Combat 0→8) one click per
  tick until Combat hits target, then holds. Still prefers `increase_max_trust` (Honor) when
  affordable (doesn't sacrifice another stat). Drifters OBS flag updated to explain the rebalance.

### RESOLVED IN v2.12.2
- **"Entertain the Swarm" was never wired** ✅ — when the swarm "thinks" with no Available Matter
  left it goes **Bored** and stops generating Swarm Gifts; the cure is the "Entertain the Swarm"
  button (`btnEntertainSwarm`, costs creativity: 10k first time, +10k each subsequent). Only
  `sync_swarm` (Disorganized) had ever been handled — Bored had no action at all (so the agent sat
  on a Bored swarm, as observed live). Added the sibling mechanical recovery, mirroring sync_swarm:
  bridge `entertain_swarm` action (clicks `btnEntertainSwarm`); agent OBS flag ("⚠ BORED —
  entertain_swarm"); a hard override that fires when `swarmStatus` contains "bored" AND creativity
  ≥ `entertain_creativity_floor` (config, default 450k — kept above the Stage 3 creativity projects
  Name the Battles 225k + Strategic Attachment 175k so entertaining never starves them), with a
  5-tick cooldown. Works in Stage 2 OR 3. `entertain_swarm` added to ACTIONS + validate_action.
  **bridge.user.js change → TAMPERMONKEY REDEPLOY required** (+ restart agent for the override).

### RESOLVED IN v2.12.1 (live-test follow-up to v2.12)
First live test of v2.12 surfaced three issues, now fixed:
- **Advisor bought trust to 20 BEFORE allocating any** ✅ — the LLM sat at "Trust 10/20, 0
  allocated" while the swarm died, because `_probe_design_advice()` recommended
  `increase_probe_trust` until total hit the cap, then allocated. REORDERED: ALLOCATE free points
  first (combat-if-drifters → haz → rep → speed/nav), and BUY only when `avail == 0` and total is
  below the allocation budget (`desired = sum of stat targets`, capped at Max Trust — buying beyond
  what you allocate just raises value drift). Now at 4 free points it raises Hazard immediately.
  agent.py only — restart agent.
- **LLM freelance-launched probes into certain death** ✅ — the `probeTotal=0` OBS flag said
  "launch_probe now", so the LLM launched every other tick at Haz 0 → all 154 lost to hazards.
  Fixed the flag (Haz<3 → "DON'T launch yet, allocate Hazard first") AND added a guard in
  `_apply_guards()` vetoing `launch_probe` when Haz<3 (substitutes wait — a futile-action veto like
  the unaffordable-project guard, NOT a probe auto-player; the LLM launches freely once Haz is set).
  agent.py only — restart agent.
- **Ignored Stage 3 project (Elliptic Hull Polytopes, 125k ops — HALVES probe hazard losses)** ✅ —
  the LLM, hyper-focused on probes, left it unbought though it directly fixes the dying swarm. Added
  the Stage 3 ops/creativity projects to the bridge `PROJECT_PRIORITY` (elliptic hull polytopes,
  combat, name the battles, the ooda loop, strategic attachment) so `autoSpendOnProjects()` buys
  them when affordable — the SAME cross-stage auto-buy used for Stage 1/2 projects (the LLM still
  owns probe DESIGN; these are just supporting tech). **bridge.user.js change → TAMPERMONKEY
  REDEPLOY required.**

### RESOLVED IN v2.12
- **Stage 3 LLM bootstrap stall — FIXED via stage-aware inputs** ✅ (PENDING LIVE TEST) — the LLM
  was frozen at colonized 0% / 0 probes, emitting `wait` every tick while quoting a stale Stage-2
  thought ("Memory 382, processors 1294 >> memory, add_memory urgently"). Root cause (confirmed from
  agent.log): `format_state()` kept showing Stage-2 memory/processor fields in Stage 3 AND fired two
  NAIVE flags — `processors` "⚠ WAY AHEAD OF MEMORY — add_memory urgently" and the `trust`
  "ADD MEMORY" hint — that bypass `_mem_proc_ladder` and are simply WRONG once memory passes its
  250-300 cap (in Stage 3, processors > memory is CORRECT). Those loud wrong flags drowned out the
  already-correct swarmGifts "add_processor" advice, so the model defaulted to `wait`; stale thoughts
  also re-anchored via `history`. Fix is LLM-side ONLY (owner constraint: no JS auto-player, no
  hard-override backstop — these are richer INPUTS; the LLM still emits every action). Six parts, all
  `agent.py` + `config.json` (NO bridge change → NO Tampermonkey redeploy; restart relay+agent):
  1. `get_stage(state)` — 1/2/3 from the bridge `phase` field (+ colonized/portValue fallback).
  2. **Stage-aware OBS** — Stage 3 uses a PROBE-FIRST whitelist (`STAGE3_KEYS`): drops Stage-1
     business + Stage-2 power/manufacturing clutter, but deliberately KEEPS memory/processors/
     creativity/swarmGifts as clearly SECONDARY (wiki-backed, owner's call: memory tops out at
     250-300, then processors farm the 400k creativity for Name the Battles 225k + Strategic
     Attachment 175k). The wrong proc/trust "add_memory urgently" flags are gated OFF in Stage 3 and
     replaced with correct guidance; added Stage-3 creativity-target + yomi-funds-probe-trust hints.
  3. **Loud Stage-3 SYSTEM_PROMPT header** (`STAGE_HEADERS` / `build_system_prompt`) prepended each
     tick: "YOU ARE IN STAGE 3 … ignore memory/processors/clips/swarm … follow the PROBE PLAN …
     don't wait while probeTotal is 0." `ask_ollama()` now takes a `system=` arg.
  4. **History + loop-tracker reset on STAGE TRANSITION** (reuses the new-game pattern; `prev_phase`)
     so prior-stage reasoning stops re-anchoring the model.
  5. **Stage-3 loop-breaker tip** points at increase_probe_trust → haz/rep → launch_probe (not the
     generic "is there a project?" nudge).
  6. **NEW deterministic probe-design advisor** `_probe_design_advice()` (mirrors `_mem_proc_ladder`)
     — emits one `►► PROBE PLAN → <action>` OBS line/tick driving the wiki opening: buy trust→20 →
     Haz 6 → Rep 6 → launch_probe → Speed/Nav (keep Speed≥Nav) → Combat 6-8 when Drifters appear
     (increase_max_trust w/ Honor if maxed). Targets are config.json tunables: `probe_trust_target`,
     `probe_haz_target`, `probe_rep_target`, `probe_speed_target`, `probe_nav_target`,
     `probe_combat_target`, `probe_aux_max`. Probe-design is "particular" (an 8-stat budget problem
     under value-drift cost) — too hard for a small model from prose alone, hence the advisor.
  Unit-tested: full opening sequence advances correctly; Stage-1/2 OBS unchanged (no regression).
  FOLLOW-UP after live test: optional late-game rebalance (lower Rep, raise Speed/Nav once
  colonization is stable); try qwen3.6 if qwen2.5 still wobbles. See memory game_mechanics.md
  (Stage 3 probe strategy) + stage3_llm_stall_deepdive.md.

### RESOLVED IN v2.9
- **Stage 2 Swarm Gifts now LLM-driven** ✅ — Swarm Gifts are the Stage 2 "trust" (fund
  memory/processors); memory was frozen at 77 because nothing generated or spent them. Made it
  LLM-OWNED (not a JS override, per the project vision): 3 new slider actions
  (set_swarm_think/balanced/work) + gift-spending via add_memory/add_processor (Stage 2 guard now
  allows them when a gift is available). Bridge sends swarmGifts/swarmThink/swarmStatus/giftCountdown
  + setSwarmSlider(); OBS nudges + SYSTEM_PROMPT Swarm job section (wiki strategy: Think ~90% until
  memory 120, then balance; spend gifts on memory→120 then processors). "Swarm Computing" is now an
  LLM-owned dashboard domain. Requires Tampermonkey redeploy.
- **LLM lower_price loop in Stage 2** ✅ — taught the LLM (OBS: wire=0 is normal in Stage 2;
  SYSTEM_PROMPT: never price in Stage 2) + guard substitutes wait for lower_price/raise_price once
  portValue present. (Fixed by teaching the LLM, not removing its agency.)

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
