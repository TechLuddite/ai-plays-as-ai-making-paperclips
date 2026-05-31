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
- Stage 2: tournament button fixed in code; per-domain loop detection active; two diagnosed
  bugs pending fix (LLM domain output, production starvation — see Known Issues)
- Stage 3 (space exploration, probe design): actions are wired, strategy guidance still being refined
- Best run: 13.5B clips, Stage 2, ~$27M investments, Marketing Level 20, 102+ ticks

## Known Issues

### ACTIVE — HIGH PRIORITY

#### 1. LLM Domain Output — "LLM Failed" for 6/8 domains
Root cause: SYSTEM_PROMPT only asks for 3 Action lines (Projects, Investments, Probes).
The other 5 domains are listed as "automatically handled." The LLM is correct — it was
never told to output those domains. relay.py dashboard has 8 static columns; any domain
missing from domain_decisions shows "LLM Failed" in red.

**Fix A (recommended first)**: Populate missing domains in agent.py with label "auto"
(dim on dashboard) instead of leaving them absent (which causes "LLM Failed"):
  - Build domain_decisions for ALL_STAGE2_DOMAINS = ["Business", "Manufacturing",
    "Computational Resources", "Quantum Computing", "Projects", "Investments",
    "Strategic Modeling"] and ALL_STAGE3_DOMAINS (adds "Probes")
  - LLM-covered domains get their actual label; others get "auto"
  - Also update relay.py dashboard: "auto" label should be dim/gray, not red
  - Fast, zero risk — honest representation of fast-rule-managed domains

**Fix B (future)**: Expand SYSTEM_PROMPT to 7 domain Action lines
  - Remove the 5 domains from "handled automatically" section
  - Add explicit Action lines for all 7 Stage 2 domains in format examples
  - LLM outputs "nothing" for fast-rule domains unless it sees an edge case
  - Requires: new examples, num_predict 400→700+; test qwen2.5 compliance first

#### 2. Production Starvation — Wire=0, $26M locked in investments
Wire hits 0 every 2-4 ticks while $26M sits in investments. Three interlocking failures:

**Failure A — Withdraw trigger breaks at high marketing levels:**
  Condition: `funds < marketing_cost AND bankroll > marketing_cost × 2`
  Marketing Level 20 cost = $52.4M → requires bankroll > $104.8M to trigger.
  Bankroll is $26.9M → withdraw NEVER fires. The condition is permanently broken
  at high marketing levels because marketing cost grows faster than the bankroll.

**Failure B — Emergency check skips when WireBuyer is on:**
  `is_emergency()` returns False when wireBuyerOn=True, even if WireBuyer can't
  afford a spool. Being "on" ≠ being able to buy. The check is logically wrong.

**Failure C — LLM defers to the broken override:**
  SYSTEM_PROMPT says invest_withdraw is "override-managed." LLM correctly outputs
  "wait" every tick, trusting the override that never actually fires.

**Fix A (add before marketing-cost withdraw check in agent.py):**
  ```python
  wire_val   = safe_float(state.get('wire'), 999)
  wire_price = safe_float(state.get('wirePrice'), 9999)
  wire_buyer = state.get('wireBuyerOn', False)
  if wire_buyer and wire_val < 100 and funds_now < wire_price * 2 and invest_bankroll > wire_price * 5:
      ov.append({"action": "invest_withdraw", "thought": "OVERRIDE: wire starvation"})
      withdraw_cooldown = 3
  ```

**Fix B (replace the broken marketing-cost trigger entirely):**
  Keep at least 5 wire spools worth of cash available at all times:
  ```python
  min_cash = max(safe_float(state.get('wirePrice'), 1000) * 5, 500.0)
  if invest_bankroll > min_cash and funds_now < min_cash:
      ov.append({"action": "invest_withdraw", ...})
  ```
  More general — fixes both wire starvation AND the marketing-level explosion issue.
  Implement both: Fix A catches the critical case immediately, Fix B permanently
  replaces the broken marketing-cost logic.

#### 3. Stage 2 project priority gap
bridge.user.js `PROJECT_PRIORITY` missing all Stage 2 manufacturing projects.
See game_mechanics.md for the correct ordered list.

### ACTIVE — LOW PRIORITY
- **Xavier Re-initialization appears twice** in project list (game quirk or selector issue).
- **start.ps1 display quirk**: relay + agent both in same terminal. Deferred.

### RESOLVED IN v2.0 / v2.1
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

### CRITICAL — Tournament buttons (commonly confused):
- `btnNewTournament` → `newTourney()` — **"New Tournament"** — STARTS tournament, costs ops,
  generates payoff matrix, awards Yomi. This is what you click to RUN a tournament.
- `btnRunTournament` → `runTourney()` — **"Run"** — display/result selection only.
  Does NOT cost ops. Does NOT earn Yomi on its own.
- `#newTourneyCost` — ops cost per tournament (= 1,000 × number of strategies available)
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
4. **Fix wrong tournament button** — change `btnRunTournament` → `btnNewTournament` everywhere
5. ~~Investment risk drift fix~~ ✅ done in v2.0
6. **Full per-domain LLM output** — expand SYSTEM_PROMPT to cover all 7 Stage 2 domains
7. ~~Multi-action per tick~~ ✅ done in v2.0
8. **Stage 2 manufacturing project queue** — add Stage 2 projects to PROJECT_PRIORITY
9. Fix start.ps1 display quirk
10. Multi-model competition mode

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
