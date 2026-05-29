# Changelog

All notable changes to this project are documented here.

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
