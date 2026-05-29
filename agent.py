"""
agent.py — Universal Paperclips ReAct Agent v2.0
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
    add_memory                  — spend 1 trust to add memory
    buy_project:<project name>  — buy a visible, affordable project by partial name

  STRATEGIC MODELING (Stage 2 — when autoTourneyOn appears in state):
    toggle_auto_tourney         — enable/disable AutoTourney (generates Yomi passively)
    set_strategy_random         — set tournament strategy to RANDOM (do once on unlock)
    run_tournament              — run a single tournament manually (costs 1,000 ops)

  INVESTMENTS (Stage 2 — only when portValue appears in state):
    invest_deposit              — move available funds into investment bankroll
    invest_withdraw             — pull investment bankroll back to available funds
    set_invest_low              — set risk strategy to Low (safer, slower returns)
    set_invest_med              — set risk strategy to Med
    set_invest_hi               — set risk strategy to High (best long-term returns)
    upgrade_investment          — upgrade investment engine (costs Yomi)

  PROBE DESIGN (Stage 3 only — when colonized appears in state):
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

SYSTEM_PROMPT = f"""You are an AI agent playing Universal Paperclips.

WHAT THE BROWSER HANDLES AUTOMATICALLY — never choose these:
  - Make Paperclip, Buy Wire, Buy AutoClipper/MegaClipper
  - Price management (raise/lower based on demand and inventory)
  - Marketing purchases
  - Projects in the auto-buy queue: wirebuyer, improved/optimized autoclippers,
    microlattice shapecasting, catchy jingle, quantum computing, algorithmic trading,
    strategic modeling, and most ops/creativity-cost projects
  - Trust allocation: add_memory and add_processor fire automatically when trust
    points are available — you do NOT need to choose these ever
  - Emergency wire recovery

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR JOB — work through this priority list each tick:

1. STRATEGIC MODELING / YOMI (when autoTourneyOn appears in state):
   Yomi is earned from tournaments. It funds probe trust and investment upgrades.
   AutoTourney is kept ON by a hard override — you do NOT need to toggle it.
   Your only jobs here:
   a. If no strategy is selected yet (first unlock): set_strategy_random
   b. upgrade_investment when Yomi is available (see investUpgradeCost in state)

2. INVESTMENTS — ONLY when portValue is visible in your state (it appears after buying
   Algorithmic Trading). If portValue is NOT in your state, the investment system does
   not exist yet — do NOT choose any invest_* or set_invest_* action.
   Deposits, withdrawals, and risk strategy are ALL managed by hard overrides —
   you do NOT need to choose invest_deposit, invest_withdraw, or set_invest_* ever.
   Your ONLY investment action: upgrade_investment — but ONLY when yomi >= investUpgradeCost.
   If yomi is 0 or less than the listed upgrade cost, do NOT choose upgrade_investment.

3. PROJECTS — only when a non-greyed clickable project appears that is NOT in the
   auto-buy list above (check availableProjects carefully — greyed = unavailable)
   NOTE: Xavier Re-initialization (100,000 creat) reallocates ALL trust — avoid
   auto-buying this; it requires deliberate trust reallocation planning.

4. STAGE 3 PROBE DESIGN (when colonized appears in state):
   - Self-Replication (rep) and Speed are highest leverage early — low rep stalls exploration
   - Hazard Remediation (haz) sweet spot: 5-6 points; below 3 causes heavy probe losses
   - If drifters > 0 and probeTotal falling → raise Combat immediately
   - Fac, Harv, Wire drive production — keep roughly balanced
   - increase_probe_trust expands your total probe budget (costs Yomi; ~1.89M total to max)

5. WAIT — if nothing needs strategic attention this tick
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRUST NOTE (informational only — do not act on it):
  Trust allocation is fully automatic. The override fires add_memory/add_processor
  whenever trust is available. If state shows "(fully allocated — none to spend)",
  trust is maxed out — skip to item 1 above.

PRICING NOTE:
  Fast rules handle routine price changes. Only intervene for edge cases the rules
  miss — e.g. demand stuck at 0% with low unsold inventory.
  Wire: 1000+ inches is healthy.

{ACTIONS}

Respond in this EXACT format only:
Thought: <specific reasoning referencing the actual numbers you see>
Action: <action name only — no comments, no punctuation, nothing after the name>
Action: <optional second action — only if truly independent from the first>
Action: <optional third action — only if warranted>

Rules for Action lines:
- Write the action name ONLY. No "#", no explanations, no trailing text.
- buy_project is the one exception: "buy_project:Project Name" (colon + name, nothing else)
- You may include up to 3 Action lines when decisions are independent
  (e.g., set_invest_hi then invest_deposit can safely queue together)
- When in doubt, use just one Action line
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
    """Post a single action (used by hard overrides)."""
    try:
        requests.post(f"{RELAY_URL}/action", json={
            "queue": [{"action": action, "args": args or {}, "thought": thought}]
        }, timeout=3)
    except Exception as e:
        print(f"[{ts()}] ⚠ Could not post action: {e}")

def post_action_queue(queue):
    """Post a list of actions to the relay queue (LLM multi-action output)."""
    try:
        requests.post(f"{RELAY_URL}/action", json={"queue": queue}, timeout=3)
    except Exception as e:
        print(f"[{ts()}] ⚠ Could not post action queue: {e}")

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
            available_trust = fv - proc - mem
            if available_trust >= 1:
                if proc > mem + 1:
                    flag = f" → ADD MEMORY (processors too far ahead!) [{int(available_trust)} to spend]"
                else:
                    flag = f" → add_memory or add_processor [{int(available_trust)} to spend]"
            else:
                flag = " (fully allocated — none to spend)"
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
            flag = " ← primary Stage 3 goal (reach 100%)"
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
    # available = unspent trust points (trust shown is total, proc+mem is spent)
    available = trust - proc - mem
    if available < 1 or proc <= 0 or mem <= 0:
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
            "options": {"temperature": 0.2, "num_predict": 280}
        }, timeout=60)
        return r.json().get("response", "").strip()
    except Exception as e:
        print(f"[{ts()}] ⚠ Ollama error: {e}")
        return None

def parse_response(text):
    """Return (thought, [action_str, ...]).  Multiple Action: lines are allowed."""
    thought = ""
    actions = []
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("thought:"):
            thought = line[8:].strip()
        elif line.lower().startswith("action:"):
            a = line[7:].strip()
            # Strip inline comments — the LLM sometimes appends "# reason" after the action.
            # e.g. "upgrade_investment  # costs 100 Yomi" → "upgrade_investment"
            if '#' in a:
                a = a[:a.index('#')].strip()
            if a:
                actions.append(a)
    return thought, actions or ["wait"]

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
        # strategic modeling / autotourney
        'toggle_auto_tourney', 'set_strategy_random', 'run_tournament',
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
    print(f"  Universal Paperclips — ReAct Agent v2.0")
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

    prev_clips = 0  # used to detect when a new game has been started
    withdraw_cooldown = 0  # ticks remaining where deposit is suppressed after a withdraw

    while True:
        tick += 1
        state = get_state()

        # Strip relay metadata before passing state to game logic
        last_result = state.pop('_lastResult', {})

        # Detect new game: clips dropped significantly from the previous tick.
        # When the user resets the browser, clips go from millions back to near-zero.
        # Carrying the old history into a new game confuses the LLM badly — clear it.
        curr_clips = safe_float(state.get('clips'), 0)
        if prev_clips > 10_000 and curr_clips < prev_clips * 0.1:
            print(f"[!!!] NEW GAME DETECTED (clips {prev_clips:,.0f} → {curr_clips:,.0f}) — clearing history")
            history.clear()
        prev_clips = curr_clips

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

        # Hard override: investment system management.
        # portValue is non-empty only after Algorithmic Trading is purchased.
        if state.get('portValue', ''):
            invest_bankroll = safe_float(state.get('investBankroll'), 0)
            invest_strategy = str(state.get('investStrategy', '')).strip().lower()
            invest_level    = safe_float(state.get('investLevel', '0'), 0)
            funds_now       = safe_float(state.get('funds'), 0)
            marketing_cost  = safe_float(state.get('marketingCost'), 0)
            # High Risk is only beneficial at engine level 5+ (profit rate ≥ 0.55).
            # Below that, Med gives better risk-adjusted returns.
            target_strat = 'hi' if invest_level >= 5 else 'med'

            # 1. Correct strategy drift — fires every tick the strategy is wrong
            if invest_strategy and invest_strategy != target_strat:
                inv_reason = f"strategy '{invest_strategy}' → correcting to '{target_strat}' (engine level {invest_level:.0f})"
                print(f"[!!!] INVEST OVERRIDE: {inv_reason}")
                post_action(f'set_invest_{target_strat}', thought=f"OVERRIDE: {inv_reason}")
                log_tick(tick, state, inv_reason, f'set_invest_{target_strat}', 0, override="invest_strat")
                time.sleep(LOOP_DELAY)
                continue

            # 2. Auto-withdraw when cash is too low to afford pending purchases.
            # invest_deposit is all-or-nothing (moves ALL cash into the bankroll), so
            # once deposited, the marketing fast rule and LLM have no cash to work with.
            # Pattern: if funds < next marketing cost but bankroll is ample → withdraw.
            # withdraw_cooldown then suppresses re-deposit for N ticks so the freed cash
            # can actually be spent before it gets recycled back into the bankroll.
            if (marketing_cost > 0
                    and funds_now < marketing_cost
                    and invest_bankroll > marketing_cost * 2):
                wd_reason = (
                    f"cash ${funds_now:.0f} below marketing cost ${marketing_cost:.0f} "
                    f"— withdrawing bankroll ${invest_bankroll:.0f} to free up funds"
                )
                print(f"[!!!] WITHDRAW OVERRIDE: {wd_reason}")
                post_action('invest_withdraw', thought=f"OVERRIDE: {wd_reason}")
                log_tick(tick, state, wd_reason, 'invest_withdraw', 0, override="withdraw_for_needs")
                withdraw_cooldown = 3   # suppress re-deposit for 3 ticks (~6s) so cash gets spent
                time.sleep(LOOP_DELAY)
                continue

            # 3. Deposit when bankroll is empty, but leave a cash buffer for marketing.
            # invest_deposit moves ALL available funds into the bankroll, which would
            # leave the marketing fast rule unable to buy upgrades until next withdraw.
            # Skip deposit for a few ticks after a withdraw to let cash get spent first.
            min_cash = max(marketing_cost * 3.0, 500.0) if marketing_cost > 0 else 500.0
            if withdraw_cooldown > 0:
                withdraw_cooldown -= 1
                # Suppress deposit — let fast rules and LLM spend the freed-up cash.
            elif invest_bankroll < 5 and funds_now > min_cash:
                inv_reason = (
                    f"investment idle — depositing "
                    f"(bankroll=${invest_bankroll:.0f}, funds=${funds_now:.0f}, "
                    f"marketing buffer ${min_cash:.0f})"
                )
                print(f"[!!!] INVEST OVERRIDE: {inv_reason}")
                post_action('invest_deposit', thought=f"OVERRIDE: {inv_reason}")
                log_tick(tick, state, inv_reason, 'invest_deposit', 0, override="invest")
                time.sleep(LOOP_DELAY)
                continue

        # Hard override: AutoTourney — if Strategic Modeling is active but AutoTourney
        # is OFF, enable it before wasting a tick on the LLM.
        # autoTourneyOn is None when the strategyEngine div hasn't appeared yet
        # (pre-Stage 2, or before Strategic Modeling is purchased).
        at_status = state.get('autoTourneyOn')
        if at_status is not None and str(at_status).strip().upper() != 'ON':
            at_reason = f"AutoTourney is {at_status!r} — enabling (Yomi stops accumulating when OFF)"
            print(f"[!!!] AUTOTOURNEY OVERRIDE: {at_reason}")
            post_action('toggle_auto_tourney', thought=f"OVERRIDE: {at_reason}")
            log_tick(tick, state, at_reason, 'toggle_auto_tourney', 0, override="autotourney")
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

        thought, action_strs = parse_response(raw)

        # Guards applied to every action the LLM outputs
        invest_actions = {'invest_deposit', 'invest_withdraw', 'set_invest_low',
                          'set_invest_med', 'set_invest_hi', 'upgrade_investment'}

        def _apply_guards(action_str):
            action, args = parse_action(action_str)
            action = validate_action(action)
            _t = safe_float(state.get('trust'), 0)
            _p = safe_float(state.get('processors'), 0)
            _m = safe_float(state.get('memory'), 0)
            if action in ('add_memory', 'add_processor') and _t - _p - _m < 1:
                print(f"[WARN] LLM chose {action} but trust fully allocated — substituting wait")
                action = 'wait'
            if action in invest_actions and not state.get('portValue', ''):
                print(f"[WARN] LLM chose {action} but investment system not active — substituting wait")
                action = 'wait'
            # invest_deposit is fully override-managed — the LLM should never choose it.
            # Blocking it here prevents the LLM from immediately re-depositing after a
            # withdraw override, which would defeat the purpose of the withdraw.
            if action == 'invest_deposit':
                print(f"[WARN] LLM chose invest_deposit — override-managed, substituting wait")
                action = 'wait'
            # upgrade_investment requires Yomi — block it when the LLM can't actually afford it.
            if action == 'upgrade_investment':
                yomi_val    = safe_float(state.get('yomi'), 0)
                upgrade_cost = safe_float(state.get('investUpgradeCost'), 999_999)
                if yomi_val < upgrade_cost:
                    print(f"[WARN] LLM chose upgrade_investment but yomi={yomi_val:.0f} < cost={upgrade_cost:.0f} — substituting wait")
                    action = 'wait'
            return action, args

        # Build validated queue; skip trailing waits to keep the queue clean
        queue = []
        for action_str in action_strs:
            action, args = _apply_guards(action_str)
            if action != 'wait' or not queue:
                queue.append({"action": action, "args": args, "thought": thought if not queue else ""})

        primary_str = action_strs[0] if action_strs else "wait"
        print(f"[THK] {thought}")
        if len(queue) > 1:
            print(f"[ACT] {primary_str}  +{len(queue)-1} queued  ({elapsed_ms}ms)")
            for q in queue[1:]:
                print(f"[ACT+] {q['action']}" + (f": {q['args']['name']}" if q['args'].get('name') else ""))
        else:
            print(f"[ACT] {primary_str}  ({elapsed_ms}ms)")
        print()

        history.append((thought, primary_str))
        post_action_queue(queue)
        log_tick(tick, state, thought, primary_str, elapsed_ms)

        time.sleep(LOOP_DELAY)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Agent stopped.")
