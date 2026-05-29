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

**LLM Agent (ReAct loop — every 2 seconds):**
- Strategic pricing, trust allocation (processors vs memory)
- Project prioritization for edge cases
- Phase transition awareness
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

## Current Status
- Phase 1: working well
- Phase 2: functional but with known income/marketing issues (see Known Issues)
- Phase 3 (space exploration, probe design): actions are wired, strategy guidance is thin
- Best run: ~168M paperclips (Phase 2, overnight), $77M investments, zero bankruptcies

## Known Issues

### MAJOR — Active problems confirmed in live runs
- **Quantum Computing not automated**: `btnQcompute` is never clicked. The Compute button
  should be fired on every fast-rule tick when `compDiv` is visible — it's free, safe,
  and converts chip charge into ops. Add to `autoQuantumCompute()` in bridge.user.js.
- **AutoTourney never runs**: Yomi = 0 after an overnight run. Actions exist
  (toggle_auto_tourney, set_strategy_random) but the LLM never chooses them.
  Fix: add a hard override in agent.py — if autoTourneyOn is in state and not "ON",
  fire the setup actions before the LLM runs. Same pattern as trust/invest overrides.
- **Marketing severely underinvested**: Marketing stayed Level 3 despite $77M in investments.
  The auto-buy buffer only checks available cash. When cash is being deposited to investments,
  available funds stay low and marketing never fires. Fix: use total wealth
  (funds + investBankroll + investStocks) as the buffer signal, or auto-withdraw to fund marketing.
- **Price strategy needs rethinking**: Current rules target demand near 500% (ceiling).
  Better strategy may be to price for ~100% demand (higher price, fewer clips sold but
  more revenue per clip, inventory clears over time). Needs experimentation.
- **Investment risk drifts back to Low**: After being set to High Risk, overnight runs show
  Low Risk. The override only sets High Risk once (when bankroll is empty). Fix: periodic
  re-check that resets strategy if it drifts from 'hi'.
- **Duplicate numbering in SYSTEM_PROMPT**: Both "PROJECTS" and "PHASE 3" are labeled
  item 3. Fix by renumbering to 1-5.

### MINOR
- LLM occasionally produces invalid actions — caught and substituted with `wait`
- If Ollama is slow, agent falls back to `wait` for that tick
- Xavier Re-initialization appears twice in project list (game quirk or selector issue)
- start.ps1 display quirk (relay + agent both in same terminal) — deferred to v2

## Key DOM IDs (confirmed from game HTML source)
- Investments: `btnInvest` (Deposit), `btnWithdraw`, `#investStrat` (low/med/hi select),
  `investmentBankroll`, `secValue`, `portValue`, `btnImproveInvestments`
- Quantum Computing: `btnQcompute`, `compDiv`
- AutoTourney: `btnToggleAutoTourney`, `autoTourneyStatus`, `stratPicker`, `btnRunTournament`
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

## Next Steps (Roadmap)
1. AutoTourney hard override (Yomi = 0 overnight is a blocker)
2. Quantum Computing automation (btnQcompute fast rule — trivial, high impact)
3. Marketing buffer using total wealth instead of available cash
4. Price strategy: target ~100% demand vs demand-ceiling chasing
5. Investment risk drift fix (keep High Risk)
6. Phase 3 probe strategy refinement
7. Multi-action per tick (LLM outputs one decision per domain — discussed, scoped for v2)
8. Fix start.ps1 display quirk
9. Multi-model competition mode

## Notes for Claude Code
- Do not modify the ReAct output format — the parser depends on exact `Thought:`/`Action:` structure
- The userscript runs in a sandboxed browser context — keep it dependency-free
- When adding new actions, update: ACTIONS string, validate_action() set, bridge.user.js executeAction()
- Owner is non-coder — prefer clear, well-commented code over clever one-liners
- `agent.log` is gitignored; it's a JSON-lines file written by agent.py each tick
- The dashboard at `http://localhost:5000` is the preferred way to observe a run — no terminal needed
- Hard overrides pattern: check condition → post_action() → log_tick() → sleep → continue
- Safe float parsing: safe_float(state.get('key'), fallback) handles $, %, commas, empty strings