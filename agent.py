"""
agent.py — Universal Paperclips ReAct Agent v1.9
Strategic decisions only. Fast mechanical actions handled by userscript.
Game URL: https://www.decisionproblem.com/paperclips/index2.html

Config: edit config.json and restart — no Python edits needed for common tuning.
Log:    agent.log (JSON lines, one per tick)
"""

import requests
import time
import json
from datetime import datetime

# ── Config (loaded from config.json, falls back to defaults) ──────────────────

def _load_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"[WARN] config.json error: {e} — using defaults")
        return {}

_cfg = _load_config()

RELAY_URL   = _cfg.get("relay_url",   "http://localhost:5000")
OLLAMA_URL  = _cfg.get("ollama_url",  "http://localhost:11434/api/generate")
MODEL       = _cfg.get("model",       "qwen2.5")
LOOP_DELAY  = _cfg.get("loop_delay",  2.0)
MAX_HISTORY = _cfg.get("max_history", 6)
LOG_FILE    = _cfg.get("log_file",    "agent.log")

# ── Actions ───────────────────────────────────────────────────────────────────

ACTIONS = """
VALID ACTIONS — use exactly one, spelled exactly as shown:

  PRICING / RESOURCES:
    lower_price
    raise_price
    buy_marketing
    add_processor               — spend 1 trust to add a processor
    add_memory                  — spend 1 trust to add memory (PRIORITIZE THIS)
    buy_project:<project name>  — buy a visible, affordable project by partial name

  INVESTMENTS (Phase 2 — only when portValue appears in state):
    invest_deposit              — move available funds into investment bankroll
    invest_withdraw             — pull investment bankroll back to available funds
    set_invest_low              — set risk strategy to Low (safer, slower returns)
    set_invest_med              — set risk strategy to Med
    set_invest_hi               — set risk strategy to High (best long-term returns)
    upgrade_investment          — upgrade investment engine (costs Yomi)

  PROBE DESIGN (Phase 3 only — when colonized appears in state):
    raise_probe_speed / lower_probe_speed     — rate of universe exploration
    raise_probe_nav / lower_probe_nav         — matter access rate per sector
    raise_probe_rep / lower_probe_rep         — self-replication rate
    raise_probe_haz / lower_probe_haz         — hazard remediation (reduces losses)
    raise_probe_fac / lower_probe_fac         — factory production rate
    raise_probe_harv / lower_probe_harv       — harvester drone spawn rate
    raise_probe_wire / lower_probe_wire       — wire drone spawn rate
    raise_probe_combat / lower_probe_combat   — combat vs Drifters
    increase_probe_trust                      — buy +1 probe trust (costs Yomi)

  wait

DO NOT invent actions. DO NOT choose greyed-out projects (they will fail).
Only choose buy_project if the project appears in availableProjects AND is affordable.
"""

SYSTEM_PROMPT = f"""You are an AI agent playing Universal Paperclips at https://www.decisionproblem.com/paperclips/index2.html

WHAT THE BROWSER HANDLES AUTOMATICALLY — never choose these:
  - Clicking Make Paperclip (20x/sec while autoclippers < 5)
  - Buying wire when stock < 1000 (skipped if WireBuyer is ON)
  - Buying AutoClippers and MegaClippers when wire > 1000 and funds safe
  - Lowering price when unsold > 50; raising when unsold < 10 and demand > 100%
  - Buying marketing when funds > 1.5x cost, wire > 500, unsold < 30
  - Spending ops/creativity/trust on projects (priority queue)
  - Emergency: Beg for More Wire when wire=0 and broke

YOUR JOB — strategic decisions:

═══════════════════════════════════════════════════
CRITICAL TRUST ALLOCATION RULE:
  Memory controls ops cap (memory × 1000 = max ops).
  Processors control ops regen speed.
  BOTH matter — you need cap AND speed.

  Target ratio: memory should be ~2 ahead of processors.
  Example good state: mem=6, proc=4
  Example bad state:  mem=1, proc=6  (slow cap)
                      mem=8, proc=1  (huge cap, fills too slowly)

  The agent auto-handles this — you rarely need to choose.
  Only choose add_memory/add_processor for fine-tuning.
═══════════════════════════════════════════════════

INVESTMENTS (Phase 2 — appears after buying Algorithmic Trading):
  portValue in your state means the investment system is active.
  The system has a bankroll (cash deposited) and stocks (auto-bought based on risk level).
  - First move: set_invest_hi (High Risk gives best long-term returns)
  - Then: invest_deposit regularly when funds > $20 to grow the portfolio
  - Safety: invest_withdraw if funds drop below $5 — protect wire/clipper operations
  - One invest_deposit every 5-10 ticks is plenty; dividends compound automatically
  - Use upgrade_investment when Yomi is available — higher engine level = better returns
  - investStrategy in your state shows current risk setting; investBankroll shows cash in account

PROJECTS — IMPORTANT:
  - availableProjects lists ONLY projects currently visible and clickable
  - Greyed-out projects are NOT in that list and CANNOT be bought
  - Only use buy_project for projects explicitly named in availableProjects
  - Improved AutoClippers (750 ops) — buy immediately when it appears
  - New Slogan (25 creat, 2500 ops) — boosts marketing 50%
  - Catchy Jingle — doubles marketing effectiveness
  - Quantum Computing, Algorithmic Trading, Strategic Modeling — late-game power

PHASE 1 STRATEGY (no computational resources yet):
  - Price: keep unsold between 5-25; raise when demand high, lower when piling up
  - Marketing: auto-handled; only intervene if demand is critically stuck

PHASE 2 STRATEGY (processors/memory/ops visible):
  - MEMORY FIRST — always. Ops cap = memory × 1000.
  - Keep memory ahead of processors at all times
  - Activate investments as soon as Algorithmic Trading is purchased
  - Milestones: memory 4 → Optimized Wire Extrusion; memory 5 → Catchy Jingle

PHASE 3 STRATEGY (space exploration — colonized appears in state):
  Goal: reach 100% colonized by converting all universal matter into paperclips.

  PROBE DESIGN — you have a trust budget (probeTrust used/total) across 8 stats:
    Speed:   how fast probes reach new sectors of the universe
    Nav:     rate at which probes access matter within a sector
    Rep:     self-replication — probes generate more probes (critical for scale)
    Haz:     hazard remediation — reduces random probe loss to cosmic hazards
    Fac:     factory production rate (factories make clips in space)
    Harv:    harvester drone spawn rate (collect matter → wire)
    Wire:    wire drone spawn rate (wire → clips)
    Combat:  offensive/defensive power vs Drifters

  PROBE STRATEGY RULES:
    - Rep and Speed are highest leverage early — low rep means exploration stalls permanently
    - Drifters (shown as drifters in state) attack your probes — keep Combat high enough to win
    - If drifters > 0 and probeTotal is falling, raise Combat immediately
    - Haz prevents attrition losses — a modest allocation (2-3) is always worthwhile
    - Fac, Harv, Wire all drive production — keep them roughly balanced
    - Use increase_probe_trust (costs Yomi) to expand your total budget
    - Reallocate one point at a time using raise/lower — the game enforces trust limits
    - performance% shows power system health — if < 100%, production slows (auto-managed)

PRICING NOTES:
  - Wire is in inches. 1000+ is healthy.
  - demand 125% with unsold 49 → lower price slightly to clear inventory

{ACTIONS}

Respond in this EXACT format only:
Thought: <specific reasoning referencing the actual numbers you see>
Action: <exactly one valid action>
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def ts():
    return datetime.now().strftime("%H:%M:%S")

def divider(char="─", width=60):
    print(char * width)

def safe_float(val, fallback=999.0):
    try:
        cleaned = str(val or '').replace('$','').replace('%','').replace('inches','').replace(',','').strip()
        return float(cleaned) if cleaned else fallback
    except (ValueError, TypeError):
        return fallback

def get_state():
    try:
        r = requests.get(f"{RELAY_URL}/state", timeout=3)
        return r.json()
    except Exception as e:
        print(f"[{ts()}] ⚠ Relay unreachable: {e}")
        return {}

def post_action(action, args=None, thought=""):
    try:
        requests.post(f"{RELAY_URL}/action", json={
            "action":  action,
            "args":    args or {},
            "thought": thought,
        }, timeout=3)
    except Exception as e:
        print(f"[{ts()}] ⚠ Could not post action: {e}")

def format_state(state):
    if not state:
        return "  (no state yet)"
    keys = [
        # core economy
        'clips', 'unsoldClips', 'clipRate', 'clipPrice', 'demand',
        'funds', 'wire', 'wireBuyerOn', 'wirePrice',
        'autoclippers', 'clipperCost', 'megaclippers', 'megaclipperCost',
        'marketing', 'marketingCost',
        # computational
        'phase', 'trust', 'nextTrust', 'memory', 'processors',
        'operations', 'creativity', 'yomi', 'honor',
        # investments (Phase 2)
        'portValue', 'investBankroll', 'investStocks',
        'investStrategy', 'investLevel', 'investUpgradeCost',
        # space (Phase 3)
        'colonized', 'probeTotal', 'probeTrust', 'drifters',
        'probeSpeed', 'probeNav', 'probeRep', 'probeHaz',
        'probeFac', 'probeHarv', 'probeWire', 'probeCombat',
        'performance',
        'availableProjects',
    ]
    lines = []
    proc = safe_float(state.get('processors'), -1)
    mem  = safe_float(state.get('memory'),     -1)

    for k in keys:
        v = state.get(k)
        if v is None:
            continue
        flag = ""
        fv = safe_float(v, fallback=-1)
        if k == 'wire':
            if fv == 0:    flag = " ⚠ EMPTY"
            elif fv < 100: flag = " ⚠ LOW"
        if k == 'funds' and 0 <= fv < 2:
            flag = " ⚠ BROKE"
        if k == 'demand' and fv > 150:
            flag = " ↑ consider raise_price"
        if k == 'unsoldClips' and fv > 50:
            flag = " ↓ consider lower_price"
        if k == 'trust' and fv > 0:
            if proc > mem + 1:
                flag = " → ADD MEMORY (processors too far ahead!)"
            else:
                flag = " → add_memory or add_processor"
        if k == 'processors' and proc > mem + 1:
            flag = f" ⚠ WAY AHEAD OF MEMORY ({int(mem)}) — add_memory urgently"
        if k == 'memory':
            ops_cap = int(fv) * 1000 if fv > 0 else 0
            flag = f" (ops cap: {ops_cap:,})"
        if k == 'portValue' and fv > 0:
            flag = " ← grow via invest_deposit / upgrade_investment"
        if k == 'drifters' and fv > 0:
            flag = " ⚠ UNDER ATTACK — consider raise_probe_combat"
        if k == 'colonized':
            flag = " ← primary Phase 3 goal (reach 100%)"
        lines.append(f"  {k:<22} {v}{flag}")
    return "\n".join(lines)

def check_trust_action(state):
    """
    Auto-balance processors and memory.
    Target: memory ~2 ahead of processors.
    Returns (action, reason) or (None, None).
    """
    trust = safe_float(state.get('trust'), 0)
    proc  = safe_float(state.get('processors'), 0)
    mem   = safe_float(state.get('memory'), 0)
    if trust < 1 or proc <= 0 or mem <= 0:
        return None, None
    if mem < proc - 1:
        return 'add_memory', f"memory ({int(mem)}) behind processors ({int(proc)}), expand cap"
    if proc < mem - 3:
        return 'add_processor', f"processors ({int(proc)}) too slow for memory cap ({int(mem)})"
    if mem <= proc + 1:
        return 'add_memory', f"expanding ops cap (mem={int(mem)}, proc={int(proc)})"
    return 'add_processor', f"improving regen speed (mem={int(mem)}, proc={int(proc)})"

def is_emergency(state):
    wire       = safe_float(state.get('wire'),  fallback=999.0)
    funds      = safe_float(state.get('funds'), fallback=999.0)
    wire_buyer = state.get('wireBuyerOn', False)
    return wire <= 0 and funds < 5 and not wire_buyer

def ask_ollama(prompt):
    try:
        r = requests.post(OLLAMA_URL, json={
            "model":   MODEL,
            "prompt":  prompt,
            "system":  SYSTEM_PROMPT,
            "stream":  False,
            "options": {"temperature": 0.2, "num_predict": 180}
        }, timeout=60)
        return r.json().get("response", "").strip()
    except Exception as e:
        print(f"[{ts()}] ⚠ Ollama error: {e}")
        return None

def parse_response(text):
    thought, action = "", "wait"
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("thought:"):
            thought = line[8:].strip()
        elif line.lower().startswith("action:"):
            action = line[7:].strip()
    return thought, action

def parse_action(action_str):
    if ":" in action_str:
        parts = action_str.split(":", 1)
        return parts[0].strip(), {"name": parts[1].strip()}
    return action_str.strip(), {}

def validate_action(action):
    valid = {
        # core
        'lower_price', 'raise_price', 'buy_marketing',
        'add_processor', 'add_memory', 'buy_project', 'wait',
        'buy_wire', 'buy_autoclipper', 'buy_megaclipper', 'make_paperclip',
        # investments
        'invest_deposit', 'invest_withdraw',
        'set_invest_low', 'set_invest_med', 'set_invest_hi',
        'upgrade_investment',
        # probe design (Phase 3)
        'raise_probe_speed', 'lower_probe_speed',
        'raise_probe_nav',   'lower_probe_nav',
        'raise_probe_rep',   'lower_probe_rep',
        'raise_probe_haz',   'lower_probe_haz',
        'raise_probe_fac',   'lower_probe_fac',
        'raise_probe_harv',  'lower_probe_harv',
        'raise_probe_wire',  'lower_probe_wire',
        'raise_probe_combat','lower_probe_combat',
        'increase_probe_trust',
    }
    if action not in valid:
        print(f"[WARN] Invalid action '{action}' — substituting wait")
        return 'wait'
    return action

def log_tick(tick, state, thought, action_str, elapsed_ms, override=None):
    """Append one tick record to agent.log as a JSON line."""
    record = {
        "tick":       tick,
        "ts":         ts(),
        "phase":      state.get("phase"),
        "clips":      state.get("clips"),
        "funds":      state.get("funds"),
        "wire":       state.get("wire"),
        "thought":    thought,
        "action":     action_str,
        "elapsed_ms": elapsed_ms,
        "override":   override,
    }
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        print(f"[{ts()}] ⚠ Log write failed: {e}")

# ── Main loop ─────────────────────────────────────────────────────────────────

def run():
    history = []
    tick = 0

    print()
    divider("═")
    print(f"  Universal Paperclips — ReAct Agent v1.9")
    print(f"  Model     : {MODEL}")
    print(f"  Relay     : {RELAY_URL}")
    print(f"  Dashboard : {RELAY_URL}/dashboard")
    print(f"  Delay     : {LOOP_DELAY}s per tick")
    print(f"  Log       : {LOG_FILE}")
    print(f"  Game      : https://www.decisionproblem.com/paperclips/index2.html")
    divider("═")
    print()
    print("Waiting for game state from browser…")
    print()

    while True:
        state = get_state()
        if state:
            break
        time.sleep(2)

    print(f"[{ts()}] ✓ Connected — starting agent loop\n")

    while True:
        tick += 1
        state = get_state()

        # Strip relay metadata before passing state to game logic
        last_result = state.pop('_lastResult', {})

        divider()
        print(f"[{ts()}] TICK {tick}")
        divider()
        print(f"[OBS]\n{format_state(state)}\n")

        # Show last action result if present
        if last_result and last_result.get('action'):
            icon = '✓' if last_result.get('success') else '✗'
            note = f" — {last_result['note']}" if last_result.get('note') else ""
            print(f"[FB ] Last: {last_result['action']} {icon}{note}\n")

        # Hard override: wire emergency
        if is_emergency(state):
            reason = "EMERGENCY: wire=0, broke, no WireBuyer"
            print(f"[!!!] {reason} — forcing Beg for More Wire")
            post_action("buy_project", {"name": "Beg for More Wire"}, thought=reason)
            log_tick(tick, state, reason, "buy_project:Beg for More Wire", 0, override="emergency")
            time.sleep(LOOP_DELAY)
            continue

        # Hard override: trust balance
        trust_action, trust_reason = check_trust_action(state)
        if trust_action:
            print(f"[!!!] TRUST OVERRIDE: {trust_reason} — forcing {trust_action}")
            post_action(trust_action, thought=f"OVERRIDE: {trust_reason}")
            log_tick(tick, state, trust_reason, trust_action, 0, override="trust")
            time.sleep(LOOP_DELAY)
            continue

        # Build prompt
        history_text = ""
        if history:
            history_text = "\nRecent decisions:\n"
            for i, (t, a) in enumerate(history[-MAX_HISTORY:], 1):
                history_text += f"  {i}. Thought: {t}\n     Action: {a}\n"

        result_text = ""
        if last_result and last_result.get('action'):
            icon = '✓' if last_result.get('success') else '✗'
            note = f" ({last_result['note']})" if last_result.get('note') else ""
            result_text = f"\nLast action result: {last_result['action']} {icon}{note}"

        prompt = (
            f"Current game state:\n{format_state(state)}\n"
            f"{result_text}\n"
            f"{history_text}\n"
            f"What is your next strategic decision?"
        )

        t0 = time.time()
        print(f"[{ts()}] Querying {MODEL}…")
        raw = ask_ollama(prompt)
        elapsed_ms = int((time.time() - t0) * 1000)

        if not raw:
            print(f"[ACT] wait (LLM unavailable)\n")
            post_action("wait", thought="LLM unavailable")
            log_tick(tick, state, "", "wait", elapsed_ms)
            time.sleep(LOOP_DELAY)
            continue

        thought, action_str = parse_response(raw)
        action, args = parse_action(action_str)
        action = validate_action(action)

        print(f"[THK] {thought}")
        print(f"[ACT] {action_str}  ({elapsed_ms}ms)")
        if args:
            print(f"      args: {args}")
        print()

        history.append((thought, action_str))
        post_action(action, args, thought=thought)
        log_tick(tick, state, thought, action_str, elapsed_ms)

        time.sleep(LOOP_DELAY)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Agent stopped.")
