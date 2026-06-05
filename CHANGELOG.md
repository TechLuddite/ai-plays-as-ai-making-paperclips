# Changelog

All notable changes to this project are documented here.

---

## [2.12.10] - 2026-06-05 — Fix AutoClipper/MegaClipper cost-crossover guard (regression of v2.4)

### Fixed
- **AutoClippers kept being bought even when MegaClippers were cheaper** (`bridge.user.js`) — live:
  AutoClipper $7,783 vs MegaClipper $5,072 (24 owned), yet the fast rule kept buying the pricier
  AutoClipper. The v2.4 cost-crossover guard was intact but *silently dead*: both it and
  `autoMegaClippers()` gated availability on `isVisible('megaClipperDiv')`, and that container-div id
  doesn't resolve in the live game, so `megaUnlocked` was always false → the "Mega is the better
  deal" guard never fired (and `autoMegaClippers()` never bought either — the 24 Megas were bought by
  the LLM/manually). Replaced both checks with a new `megaClipperUnlocked()` helper that gates off the
  **confirmed** `btnMakeMegaClipper` button id (checking both `display` via `offsetParent` and
  `visibility`), so it works regardless of the container id or how the game hides a locked upgrade.
  Now once MegaClippers are cheaper, the AutoClipper buy is skipped and `autoMegaClippers()` spends
  the cash on the cheaper, far-more-productive MegaClipper. **Tampermonkey REDEPLOY required.**
  Lesson (again, cf. v2.6): gate off confirmed button ids, not guessed container divs.

## [2.12.9] - 2026-06-05 — Fix fresh-game stage misdetection (compDiv ≠ Stage 2)

### Fixed
- **`getPhase()` flipped Stage 1 → Stage 2 the moment Quantum Computing was bought** (`bridge.user.js`)
  — on a freshly-restarted game the agent correctly read Stage 1, then jumped to Stage 2 (and started
  taking Stage-2/late-game actions) as soon as QC unlocked. Cause: `getPhase()` used
  `isVisible('compDiv')` as the Stage 2 marker, but `compDiv` is the **Quantum Computing panel,
  unlocked mid-Stage 1** — not a Stage 2 panel. Fixed to use the real Stage 2 panels
  (`powerDiv`/`factoryDiv`, matching `getStage2State()`); `spaceDiv` → Stage 3 is still checked first.
  Verified *not* the cause: the relay does a full state replace (no stale `colonized` leak) and the
  Python `get_stage()` fallback only triggers on keys the bridge sends per-stage. **Tampermonkey
  REDEPLOY required.** Confirmed resolved in live testing.

## [2.12.8] - 2026-06-05 — 🎉 Endgame reached (100% of the universe explored)

### Added
- **Endgame safety guard** (`agent.py`) — the colonization scaling (2.12.7) carried the run from
  68% → **100% of the universe explored**, and the "Message from the Emperor of Drift" endgame
  sequence appeared. The final Accept (New Game+ restart) / Reject (disassemble the empire →
  irreversible credits) choice is the player's alone, so the LLM `NEVER_BUY` guard now blocks every
  endgame project: the Emperor message + dialogue boxes, Accept, Reject, both Universe choices, the
  Disassemble chain, and the Driftwar Monument. Verified no false-match on legit Stage 3 buys.
  Python-only — **no redeploy**. This was the first complete run: Stage 1 → 2 → 3 → 100%.

## [2.12.7] - 2026-06-04 — Probe design scales past Max Trust 20 (colonization)

### Changed
- **Extra trust now drives colonization via Speed × Exploration** (`agent.py`, `config.json`) — the
  run survived (manual Haz 10 / Combat 13) but `colonized` was stuck near 0% because Speed 1 ×
  Exploration 3 ≈ no exploration rate. Per the wiki, once the swarm is big and combat is handled you
  raise Speed + Exploration to cover the universe (matter rate = the *product*; keep Speed ≥ Exp).
  `_probe_design_advice()` now runs a 3-phase budget that scales with Max Trust: pre-launch baseline
  (15) → combat reserve (held free until Drifters, then filled to `probe_combat_target` = 8) →
  colonize (all trust above survival pours into Speed/Exploration). Drove colonized 68% → 100%.
  Python-only — **no redeploy**.

## [2.12.6] - 2026-06-04 — Owner's initial probe-design allocation + Combat reserve

### Changed
- **New opening 20-trust design** (`agent.py`, `config.json`) — 1 each in Speed/Exploration/Factory/
  Harvester/Wire, 5 each in Self-Replication and Hazard, and **5 in Combat held in reserve** until
  combat opens. By building only to 15 up front there's always cap headroom, so Combat deploys
  instantly without sacrificing Rep (the trap that nearly lost the run). Reordered the advisor:
  allocate → buy (deploy reserve) → rebalance (only when truly maxed) → launch. Python-only.

## [2.12.5] - 2026-06-04 — Stop the repeatable honor project draining yomi

### Fixed
- **"Threnody for the Heroes" is endlessly repeatable** (`bridge.user.js`) — added in 2.12.4, it was
  auto-bought every 1.5s (creat 50k +10k, yomi 20k +4k each, for 10k honor) and bled millions of
  yomi; the cost parser only saw the creativity cost, spending yomi invisibly. Removed it from
  `PROJECT_PRIORITY` (repeatable projects must never auto-buy) and added a `YOMI_RESERVE` (1M) guard
  that parses any yomi cost and skips a buy that would dip below the reserve. **Redeploy.**

## [2.12.4] - 2026-06-04 — Combat recovery: rebalance before launch, auto-buy honor projects

### Fixed
- **Advisor relaunched into death instead of fixing Combat** (`agent.py`) — after the swarm
  collapsed to 0 under 1.9B Drifters at Combat 0, the launch branch ran before the combat rebalance,
  so it relaunched (probes died instantly) forever. Reordered: combat emergency before launch;
  extended the launch guard to veto launching at Combat < 3 (not just Haz < 3).
### Added
- **Honor projects auto-buy** (`bridge.user.js`, **redeploy**) — Threnody + Glory to `PROJECT_PRIORITY`
  (Honor → Max Trust → Combat without sacrificing a stat). Aux stats (Fac/Harv/Wire) fill to 1 each
  only once Max Trust is raised; `memory release` added to the LLM never-buy guard.

## [2.12.3] - 2026-06-04 — Combat rebalance when Drifters attack and trust is maxed

### Fixed
- **Combat unallocated under attack** (`agent.py`) — Drifters attacking but Combat 0 with trust
  20/20 fully allocated and no Honor to raise the cap. Added a rebalance: lower an over-allocated
  stat (Self-Replication first, never Hazard) to free a point for Combat, walking Rep down and Combat
  up one click per tick. Python-only.

## [2.12.2] - 2026-06-04 — "Entertain the Swarm" (Bored-swarm recovery)

### Added
- **`entertain_swarm`** (`bridge.user.js`, **redeploy**; `agent.py`, `config.json`) — a Bored swarm
  (thinking with no matter left) stops generating Swarm Gifts; only the Disorganized→sync recovery
  had ever been wired. Added the sibling: a hard override that clicks "Entertain the Swarm" when
  `swarmStatus` is Bored and creativity ≥ `entertain_creativity_floor` (450k, kept above the Stage 3
  creativity projects). Works Stage 2 or 3.

## [2.12.1] - 2026-06-04 — Stage 3 live-test fixes

### Fixed
- **Allocate trust before buying more** — the advisor bought to the cap before allocating any, so it
  sat at "10/20, 0 allocated" while probes died. Reordered to allocate free points first.
- **Veto Haz-0 launches** — the `probeTotal=0` OBS flag said "launch now"; the LLM launched at Haz 0
  and all probes died to hazards. Fixed the flag + added a launch guard at Haz < 3.
### Added
- **Stage 3 support projects auto-buy** (`bridge.user.js`, **redeploy**) — Elliptic Hull Polytopes
  (halves probe hazard losses), Combat, Name the Battles, The OODA Loop, Strategic Attachment.

## [2.12] - 2026-06-04 — Stage 3 LLM bootstrap stall fixed (stage-aware inputs)

### Fixed
- **The agent reached Stage 3 but froze** at colonized 0% / 0 probes, emitting `wait` every tick while
  re-quoting a stale Stage-2 "add_memory urgently" thought. Root cause: `format_state()` still showed
  Stage-2 memory/processor fields in Stage 3 and fired two naive flags that are *wrong* once memory
  passes its 250–300 cap, drowning out the correct advice. Fixed entirely LLM-side (owner constraint:
  keep Stage 3 LLM-driven — no JS auto-player), all `agent.py` + `config.json`, **no redeploy**:
  1. `get_stage(state)` from the bridge `phase` field.
  2. Stage-aware OBS (`STAGE3_KEYS`, probe-first) with the misleading flags gated off in Stage 3.
  3. A loud Stage-3 SYSTEM_PROMPT header (`STAGE_HEADERS` / `build_system_prompt`).
  4. History + loop-tracker reset on stage transition.
  5. A Stage-3 loop-breaker tip pointing at the probe actions.
  6. A deterministic probe-design advisor `_probe_design_advice()` emitting one `►► PROBE PLAN →
     <action>` OBS line per tick (config-tunable targets) — the key technique for a weak local model.

---

## [2.11] - 2026-06-04 — Stage 3 (Space Exploration + Von Neumann Probes)

### Added
- **Stage 3 launch + probe-trust actions** (`bridge.user.js`, `agent.py`) — Space Exploration was
  bought and Stage 3 began, but the actions that actually *start and drive* it were missing (only
  the probe-stat raise/lower allocation was wired). Added:
  - `launch_probe` (btnMakeProbe) — launch the initial Von Neumann probe swarm (costs clips);
    without probes, nothing explores. `increase_max_trust` (btnIncreaseMaxTrust) — raise the
    probe-trust cap with Honor. (`increase_probe_trust` was already wired.)
  - `getPhase3State()` now sends the fields the LLM needs: `probesLaunched`, `probesBorn`,
    `probeCost`, `probeTrustUsed`/`probeTrustTotal`/`maxTrust`, `probeTrustCost`/`maxTrustCost`,
    `honor`, `driftersKilled`.
  - `format_state()` flags the Stage 3 opening: "NO PROBES — launch_probe now" when probeTotal=0,
    and "N trust to ALLOCATE …" / "increase_probe_trust for more" from the used/total/max.
  - SYSTEM_PROMPT rewrote the Stage 3 section into the wiki opening sequence: get trust → allocate
    (haz 5–6, rep ≥4, some speed/nav) → launch the swarm → maintain (combat 6–8 vs drifters,
    raise the cap with honor, keep colonized climbing toward 100%).
  Stage 3 is LLM-driven (the model owns probe strategy — the most "game-playing" stage).
  **Requires Tampermonkey redeploy.**

---

## [2.10.4] - 2026-06-04

### Added
- **Space Exploration launch (Stage 2 → Stage 3 trigger)** (`agent.py`) — the goal of the whole
  Stage 2 buildup. The game lists "Space Exploration" in availableProjects only once every
  requirement is met (120k ops + 5 octillion clips + 10M MW-sec storage), so its presence = ready.
  - OBS: `maxStorage` now shows progress toward the 10M MW-sec gate; when Space Exploration is
    listed, the availableProjects line is flagged "🚀 LAUNCH NOW".
  - SYSTEM_PROMPT: Space Exploration is the explicit #1 priority — buy it the moment it appears.
  - LLM-first with a backstop: the LLM gets first crack at `buy_project:Space Exploration`; if it
    stays available for 3 ticks unbought, a hard-override launches it (so the run can't idle past
    this one-time transition — the failure mode seen with the swarm sync).
  Python-only — **no Tampermonkey redeploy** (restart agent).

---

## [2.10.3] - 2026-06-04

### Changed
- **Batteries now build in +100/+10 batches toward the 10M MW-sec Space Exploration gate**
  (`bridge.user.js`) — with clips (6 octillion) and ops already past Space Exploration's
  thresholds, battery storage is the last requirement (10,000,000 MW-seconds). The builder was
  adding batteries one at a time, and the old `BATTERY_MIN=200` would have capped storage at
  ~2M MW-sec anyway. Replaced with `BATTERY_TARGET_MW = 10,000,000`: the builder now reads
  `maxStorage` and builds batteries with the +100/+10 buttons until storage reaches the target.
  **Requires Tampermonkey redeploy.**

---

## [2.10.2] - 2026-06-04

### Fixed
- **Clip-cost projects never auto-bought (e.g. Self-correcting Supply Chain)** (`bridge.user.js`)
  — projects priced in CLIPS use word suffixes ("1 sextillion clips"), which `getProjectCost()`
  couldn't parse, so it returned `null` and the auto-buyer skipped them. Self-correcting Supply
  Chain (1 sextillion clips — "each factory then boosts every factory's output 1,000×", a massive
  production multiplier toward the 5-octillion Space Exploration goal) was sitting available and
  affordable (47 sextillion unused clips) but unbought. Fixes:
  - Added `parseBigNum()` (handles thousand…decillion word suffixes) and a `clips` cost type in
    `getProjectCost()`; `autoSpendOnProjects()` now checks clip cost against the unused-clip pool.
  - Added `self-correcting supply chain` to `PROJECT_PRIORITY` (high — buy ASAP).
  **Requires Tampermonkey redeploy.**

---

## [2.10.1] - 2026-06-04

### Fixed
- **Swarm never got synced — LLM stuck ignoring the disorganization** (`agent.py`) — with
  production scaling fine, the swarm sat "Disorganized" and the LLM looped on `wait` (identical
  thought 10+ ticks), never issuing `sync_swarm`. The per-domain loop-breaker fired its alert but
  qwen2.5 ignored it: the LLM was idle (memory maxed, gifts useless) and kept missing the one real
  pending action. Disorganization recovery is deterministic and mechanical — so, like the wire/
  trust/AutoTourney/investment recoveries, it's now a HARD OVERRIDE: if `swarmStatus` is
  Disorganized and yomi ≥ 5,000, the agent fires `sync_swarm` before the LLM runs (with a short
  cooldown so it doesn't double-spend 5k yomi while the status updates). The LLM still owns the
  strategic swarm decisions (slider, gift allocation) — only the binary "it's broken → fix it"
  recovery is overridden. `sync_swarm` already shipped in the bridge (v2.9.1), so this is
  Python-only — **no Tampermonkey redeploy** (restart agent).
- Confirmed live: v2.10 endgame scaling working — clip rate ~16.8 quadrillion → ~742 sextillion/
  sec, factories 10 → 43→200, drones batching at a healthy ~1.44 ratio.

---

## [2.10] - 2026-06-04 — Stage 2 endgame scaling

### Changed
- **Raised the Stage 2 build targets so production can reach Space Exploration** (`bridge.user.js`)
  — diagnosed live: the agent had maxed its conservative early-Stage-2 caps (10 factories,
  500 drones) and plateaued. Clip production sat at ~16.8 quadrillion/sec — about 6 million×
  short of the 5 octillion clips Space Exploration needs — so the agent was idling (memory/
  processors overshot, gifts dumped into useless processors, lots of `wait`). New targets
  (wiki "Quickening" endgame, all self-paced by clip affordability via `!btn.disabled`):
  - `FACTORY_TARGET` 10 → 200, `DRONE_TARGET` 500 → 50000, `BATTERY_MIN` 20 → 200.
- **Batch drone building** (`bridge.user.js`) — single drone builds (1 per 800 ms) can't reach
  tens of thousands in any reasonable time. Added `buildDroneBatch()` using the +10/+100/+1k
  buttons, with each batch CAPPED so neither drone type exceeds 1.5× the other. This keeps the
  swarm Organized AND gradually corrects an already-disorganized ratio (simulated: 191/309 =
  1.618 → converges to ~1.42, never exceeding 1.5). Power headroom (1 MW/drone) also caps the
  batch, so drones and solar farms leapfrog as production scales.
  **Requires Tampermonkey redeploy.**

### Note
- Targets are tunable constants at the top of `bridge.user.js` — start here and raise/lower
  after watching a run. The drone ratio fix (≤1.5) means the recurring "Disorganized" syncs
  should stop once the swarm rebuilds at the new ratio.

---

## [2.9.3] - 2026-06-04

### Fixed
- **Processors over-ran memory in Stage 2 (162 vs 120)** (`agent.py`) — the v2.5 milestone
  ladder soft-caps processors at ~half the memory target, but that logic lived only in
  `check_trust_action()` (Stage 1 trust). Stage 2 gift-spending is LLM-driven, and the prompt/OBS
  told it "add_memory until 120, then add_processor" — no cap, and a hard stop at 120 — so once
  memory hit 120 the LLM poured every surplus gift into processors (reached 162, while ops were
  already pinned at 120,000 and creativity was 858k). Fixes:
  - Extracted the ladder into a shared `_mem_proc_ladder(mem, proc)` used by BOTH Stage 1 trust
    and the Stage 2 OBS recommendation (memory leads to the next milestone — 120 → 175 → 250 —
    processors trail at ~half).
  - The OBS `swarmGifts` line now shows the ladder's exact recommendation ("SPEND NOW: add_memory
    (rush memory to 175 …)" / "add_processor …"); SYSTEM_PROMPT tells the LLM to follow it and to
    keep memory ahead of processors (don't stop at 120 — push to 175 for Stage 3).
  Net effect: memory now keeps climbing past 120 toward 175/250 and processors hold until memory
  catches up. Python-only — **no Tampermonkey redeploy** (restart agent).

---

## [2.9.2] - 2026-06-04

### Changed
- **Faster memory climb — stop the LLM wasting ticks re-setting the slider** (`agent.py`) — with
  the swarm working, the LLM alternated `set_swarm_think` / `add_memory`, roughly halving the
  memory growth rate while gifts piled up unspent (950+ banked). Root cause was a misconception
  in its thoughts ("set_swarm_think to grow memory") — but set_swarm_think only GENERATES gifts;
  only `add_memory` grows memory. Fixed by teaching, not overriding:
  - SYSTEM_PROMPT Swarm section now states it plainly and says: if a gift is waiting and memory
    < 120, the answer is `add_memory` EVERY tick — set the slider only once (when at Work).
  - `format_state()` swarmThink line now reads "✓ already on Think — do NOT re-set; SPEND gifts
    (add_memory)" once the slider is on Think, instead of nudging set_swarm_think again.
  Python-only — **no Tampermonkey redeploy** (restart agent).

---

## [2.9.1] - 2026-06-04

### Fixed
- **Drone ratio caused a "Disorganized" swarm** (`bridge.user.js`) — `DRONE_RATIO` was 1.618
  (the wiki's PRODUCTION-optimal golden ratio), but that EXCEEDS the swarm's 1.5× imbalance
  limit, so the builder drove the drones to 191/309 = 1.618 and the swarm tipped to
  "Disorganized" — which halts Swarm Gift generation (a hidden reason memory was stuck).
  Lowered `DRONE_RATIO` to 1.45 (safely under 1.5).
- **No recovery from a Disorganized swarm** (`bridge.user.js`, `agent.py`) — added a
  `sync_swarm` LLM action (clicks "Synchronize the Swarm", `btnSynchSwarm`, costs 5k yomi).
  The Swarm Computing prompt now does sync FIRST (a disorganized swarm generates no gifts),
  then spends a waiting gift, then sets the slider. `format_state()` flags the Disorganized
  status loudly.

### Note
- Root cause of "nothing happened" after v2.9: the **bridge wasn't redeployed** — the live
  state showed `swarmGifts`/`swarmThink`/`swarmStatus` absent and `set_swarm_think` returning
  an empty note (v2.9 sets "90% Think"), confirming the browser still ran the old bridge.
  v2.9's LLM features only work once `bridge.user.js` is copied into Tampermonkey.
  **Requires Tampermonkey redeploy** (v2.9 + v2.9.1 together).

---

## [2.9] - 2026-06-04

LLM-first Stage 2: the model now drives Swarm Computing (the Stage 2 progression engine)
instead of a JS override — keeping the local LLM central to gameplay.

### Added
- **LLM-controlled Swarm Computing** (`bridge.user.js`, `agent.py`) — Swarm Gifts are the
  Stage 2 equivalent of Trust (they fund memory/processors), and memory was frozen at 77 because
  nothing generated or spent them. Now the **LLM** runs both halves:
  - **Generate** — three new LLM actions set the Work/Think slider: `set_swarm_think` (90% Think),
    `set_swarm_balanced` (50%), `set_swarm_work` (20%). Bridge adds `setSwarmSlider()` +
    `executeAction` cases (sets `#slider`, fires input/change).
  - **Spend** — `add_memory`/`add_processor` already map to the same buttons; the Stage 2 guard
    now allows them when a Swarm Gift is available (previously blocked because trust = 0 in Stage 2).
  - Bridge sends `swarmGifts`, `swarmThink` (slider), `swarmStatus`, `giftCountdown`.
  - `format_state()` surfaces it with explicit nudges ("SPEND NOW: add_memory → 120",
    "slider at WORK — set_swarm_think"). SYSTEM_PROMPT gains a Swarm Computing job section with
    the wiki strategy (Think ~90% until memory 120, then balance; spend gifts on memory→120 then
    processors). "Swarm Computing" is now an LLM-owned domain (its own Action line + dashboard cell).
  **Requires Tampermonkey redeploy.**

### Fixed
- **LLM `lower_price` loop in Stage 2** (`agent.py`) — the LLM spammed `lower_price` (failing)
  on a Stage-1 wire/demand misread. Taught it the Stage 2 reality instead of hard-coding around it:
  the OBS now says wire = 0 is NORMAL in Stage 2 (drones feed factories live), the SYSTEM_PROMPT
  says never price in Stage 2, and a guard substitutes `wait` for `lower_price`/`raise_price` once
  `portValue` is present (backstop).

---

## [2.8] - 2026-06-03

### Changed
- **Dashboard overhaul — stage-grouped domains** (`agent.py`, `relay.py`) — the LLM Decisions
  card showed a static 8-column table that omitted the new Stage 2 domains entirely (Power,
  Wire Production, Swarm Computing weren't represented). Rebuilt it into **three stage sections**
  (Stage 1 — Core / Stage 2 — Industry / Stage 3 — Space), each a mini-table of its domains with
  the last 3 ticks and a health badge.
  - `agent.py` now builds `domain_decisions` from a stage-tagged `DOMAIN_REGISTRY` (11 domains)
    instead of a flat list of 8. Each entry carries a `stage` (1/2/3).
  - New Stage 2 domains get a **computed health grade** from game state (no LLM needed):
    Power (from Factory/Drone Performance — healthy ≥100% / warn / critical <50%), Wire
    Production (from harvester+wire drone presence). Swarm Computing shows plain "auto" until
    the Swarm Gifts feature lands. The original 5 auto domains keep their LLM Status grade.
  - `relay.py` dashboard renders the three sections via a stage map + a shared cell renderer
    (action / auto+dot / n/a / LLM Failed).
- **Loop-tracker noise reduced** (`agent.py`) — the per-domain repeat detector now skips
  `auto`/`n/a` entries, so it no longer spams the prompt with "Business: auto ×N" warnings for
  JS-handled domains (only real LLM decisions are loop-checked).
  Agent + relay change only — **no Tampermonkey redeploy** (restart relay + agent).

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
