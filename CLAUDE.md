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

In `bridge.user.js` (constants at top of file):
- `STATE_MS` — state push interval in ms (default: `2000`)
- `ACTION_MS` — action poll interval in ms (default: `500`)

## Deployment Checklist (run every time bridge.user.js changes)
1. Copy bridge.user.js → Tampermonkey editor → Save  ← easy to forget; causes Yomi=0
2. Restart relay.py (new terminal)
3. Restart agent.py (new terminal)
4. Reload game page in Chrome
Python restarts alone do NOT update the browser script.

## Current Status
- Stage 1: working well
- Stage 2: tournaments fully working (Yomi flowing, investment engine auto-upgrading to Level 3+);
  all previously diagnosed bugs resolved in v2.3 (production starvation, domain output, project queue)
- Stage 3 (space exploration, probe design): actions are wired, strategy guidance still being refined
- Best run: 13.5B+ clips, Stage 2, investment engine Level 3, Yomi accumulating, Marketing Level 20

## Known Issues

### ACTIVE — HIGH PRIORITY
*(none — all high-priority issues resolved in v2.3)*

### ACTIVE — LOW PRIORITY
- **Xavier Re-initialization appears twice** in project list (game quirk or selector issue).
- **start.ps1 display quirk**: relay + agent both in same terminal. Deferred.

### RESOLVED IN v2.3
- Production starvation ✅ — Fix A: wire-starvation emergency withdraw when WireBuyer ON but
  can't afford wire; Fix B: replaced broken marketing-cost trigger with wire-price-based min_cash
  buffer (`wirePrice × 5`), which is always valid regardless of marketing level
- LLM domain output "LLM Failed" ✅ — Fix A: agent.py now appends "auto" entries for all
  JS-handled domains; relay.py dashboard renders "auto" as dim gray instead of red "LLM Failed"
- Stage 2 manufacturing project gap ✅ — Added Tóth Tubulue Enfolding, Power Grid, Nanoscale
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
11. **LLM domain grading** — LLM rates the health of JS-handled domains each tick
    (e.g., "Manufacturing: warn", "Business: healthy"). Intended design:
    - SYSTEM_PROMPT gains a "Domain Status" section; LLM outputs `Status: Domain=token` lines
    - `parse_response()` gains a `parse_status()` sibling to extract these
    - relay.py dashboard shows colored health badges alongside "auto" labels
    - Longer term: LLM can output parameter hints (e.g., `wire_threshold=200`) that
      agent.py reads and passes to the bridge as adjustments
12. **LLM domain output Fix B** — expand SYSTEM_PROMPT to all 7 domains with explicit Action
    lines (num_predict 400→700+); test qwen2.5 compliance before enabling
13. Multi-model competition mode

## Notes for Claude Code
- Do not modify the ReAct output format — the parser depends on exact `Thought:`/`Action:` structure
- The userscript runs in a sandboxed browser context — keep it dependency-free
- When adding new actions, update: ACTIONS string, validate_action() set, bridge.user.js executeAction()
- Owner is non-coder — prefer clear, well-commented code over clever one-liners
- `agent.log` is gitignored; it's a JSON-lines file written by agent.py each tick
- The dashboard at `http://localhost:5000` is the preferred way to observe a run — no terminal needed
- Hard overrides pattern (v2.0): collect into ov[] → LLM always runs → post_action_queue(ov + llm_q)
  Only wire emergency uses the old continue pattern (hard exit before LLM)
- Safe float parsing: safe_float(state.get('key'), fallback) handles $, %, commas, empty strings
- Game mechanics reference: see memory/game_mechanics.md — tournament buttons, investment PLR,
  stage progression, all DOM IDs. Use this as ground truth instead of assumptions.
