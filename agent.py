"""
agent.py — Universal Paperclips ReAct Agent v1.9
Strategic decisions only. Fast mechanical actions handled by userscript.
Game URL: https://www.decisionproblem.com/paperclips/index2.html
"""

import requests
import time
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

RELAY_URL   = "http://localhost:5000"
OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "qwen2.5"
LOOP_DELAY  = 2.0
MAX_HISTORY = 6

# ── Actions ───────────────────────────────────────────────────────────────────

ACTIONS = """
VALID ACTIONS — use exactly one, spelled exactly as shown:
  lower_price
  raise_price
  buy_marketing
  add_processor               — spend 1 trust to add a processor
  add_memory                  — spend 1 trust to add memory (PRIORITIZE THIS)
  buy_project:<project name>  — buy a visible, affordable project by partial name
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

PROJECTS — IMPORTANT:
  - availableProjects in your state lists ONLY the projects you can currently see
  - Greyed-out projects are NOT in that list and CANNOT be bought
  - Only use buy_project for projects explicitly named in availableProjects
  - Improved AutoClippers (750 ops) is high priority — buy it the moment it appears
  - New Slogan (25 creat, 2500 ops) boosts marketing 50% — buy when affordable
  - Catchy Jingle doubles marketing effectiveness — buy when affordable
  - Quantum Computing, Algorithmic Trading, Strategic Modeling unlock late-game power

PHASE 1 STRATEGY (no computational resources yet):
  - Price: keep unsold between 5-25; raise when demand high, lower when inventory piles up
  - Marketing: auto-handled; don't buy manually unless demand is critically stuck

PHASE 2 STRATEGY (processors/memory/ops visible):
  - MEMORY FIRST — always. Ops cap = memory × 1000.
  - Keep memory ahead of processors
  - Projects require ops to unlock; more memory = bigger ops cap = more projects available
  - Suggested milestones: memory 4 → Optimized Wire Extrusion; memory 5 → Catchy Jingle

PHASE 3 STRATEGY (space exploration):
  - Balance probe speed, replication, combat, and harvesting
  - Focus on colonization percentage

PRICING NOTES:
  - Wire is in inches. 1000+ is healthy. Don't worry unless wireBuyerOn=false AND wire=0.
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

def post_action(action, args=None):
    try:
        requests.post(f"{RELAY_URL}/action", json={"action": action, "args": args or {}}, timeout=3)
    except Exception as e:
        print(f"[{ts()}] ⚠ Could not post action: {e}")

def format_state(state):
    if not state:
        return "  (no state yet)"
    keys = [
        'clips', 'unsoldClips', 'clipRate', 'clipPrice', 'demand',
        'funds', 'wire', 'wireBuyerOn', 'wirePrice',
        'autoclippers', 'clipperCost', 'megaclippers', 'megaclipperCost',
        'marketing', 'marketingCost',
        'phase', 'trust', 'nextTrust', 'memory', 'processors',
        'operations', 'creativity',
        'availableProjects'
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
        lines.append(f"  {k:<22} {v}{flag}")
    return "\n".join(lines)

def check_trust_action(state):
    """
    Balance processors and memory.
    Memory controls ops cap (mem x 1000).
    Processors control ops regen speed.
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
    wire      = safe_float(state.get('wire'),  fallback=999.0)
    funds     = safe_float(state.get('funds'), fallback=999.0)
    wire_buyer = state.get('wireBuyerOn', False)
    return wire <= 0 and funds < 5 and not wire_buyer

def ask_ollama(prompt):
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 120}
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
        'lower_price', 'raise_price', 'buy_marketing',
        'add_processor', 'add_memory', 'buy_project', 'wait',
        'buy_wire', 'buy_autoclipper', 'buy_megaclipper', 'make_paperclip'
    }
    if action not in valid:
        print(f"[WARN] Invalid action '{action}' — substituting wait")
        return 'wait'
    return action

# ── Main loop ─────────────────────────────────────────────────────────────────

def run():
    history = []
    tick = 0

    print()
    divider("═")
    print(f"  Universal Paperclips — ReAct Agent v1.9")
    print(f"  Model  : {MODEL}")
    print(f"  Relay  : {RELAY_URL}")
    print(f"  Delay  : {LOOP_DELAY}s per tick")
    print(f"  Game   : https://www.decisionproblem.com/paperclips/index2.html")
    divider("═")
    print()
    print("Waiting for game state from browser...")
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

        divider()
        print(f"[{ts()}] TICK {tick}")
        divider()
        print(f"[OBS]\n{format_state(state)}\n")

        # Hard override: wire emergency
        if is_emergency(state):
            print(f"[!!!] EMERGENCY: wire=0, broke, no WireBuyer — forcing Beg for More Wire")
            post_action("buy_project", {"name": "Beg for More Wire"})
            time.sleep(LOOP_DELAY)
            continue

        # Hard override: trust spending balance
        trust_action, trust_reason = check_trust_action(state)
        if trust_action:
            print(f"[!!!] TRUST OVERRIDE: {trust_reason} — forcing {trust_action}")
            post_action(trust_action)
            time.sleep(LOOP_DELAY)
            continue

        history_text = ""
        if history:
            history_text = "\nRecent decisions:\n"
            for i, (t, a) in enumerate(history[-MAX_HISTORY:], 1):
                history_text += f"  {i}. Thought: {t}\n     Action: {a}\n"

        prompt = f"Current game state:\n{format_state(state)}\n{history_text}\nWhat is your next strategic decision?"

        print(f"[{ts()}] Querying {MODEL}...")
        raw = ask_ollama(prompt)

        if not raw:
            print(f"[ACT] wait (LLM unavailable)\n")
            post_action("wait")
            time.sleep(LOOP_DELAY)
            continue

        thought, action_str = parse_response(raw)
        action, args = parse_action(action_str)
        action = validate_action(action)

        print(f"[THK] {thought}")
        print(f"[ACT] {action_str}")
        if args:
            print(f"      args: {args}")
        print()

        history.append((thought, action_str))
        post_action(action, args)

        time.sleep(LOOP_DELAY)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Agent stopped.")
