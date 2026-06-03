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

  SWARM COMPUTING (Stage 2 — when swarmGifts / swarmThink appear in state):
    set_swarm_think             — slider to 90% Think: drones make Swarm Gifts fast (grows memory)
    set_swarm_balanced          — slider to 50%: balance gifts with production
    set_swarm_work              — slider to 20% Think: favor production (clips/matter)
    sync_swarm                  — fix a "Disorganized" swarm (costs 5,000 yomi); do this FIRST
                                  when swarmStatus shows Disorganized, or no gifts will generate
    add_memory                  — spend ONE Swarm Gift on memory (raises ops ceiling toward 120)
    add_processor               — spend ONE Swarm Gift on a processor (ops regen / creativity)
    (In Stage 2, Swarm Gifts are your "trust": add_memory/add_processor spend a gift, not trust.)

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

WHAT THE AGENT HANDLES AUTOMATICALLY — never choose these:
  - Make Paperclip, Buy Wire, Buy AutoClipper/MegaClipper
  - Price management (raise/lower based on demand and inventory)
  - Marketing purchases
  - Projects in the auto-buy queue: wirebuyer, improved/optimized autoclippers,
    microlattice shapecasting, catchy jingle, quantum computing, algorithmic trading,
    strategic modeling, and most ops/creativity-cost projects
  - STAGE 1 trust allocation (add_memory, add_processor) — override fires whenever TRUST is
    free. (Stage 2 is different: there's no trust — YOU spend Swarm Gifts on memory/processors.
    See "YOUR JOB" item 2. Don't expect the override to do it in Stage 2.)
  - Investment deposits, withdrawals, risk strategy
    (invest_deposit, invest_withdraw, set_invest_low/med/hi) — override-managed every tick
  - AutoTourney toggling (toggle_auto_tourney) — kept ON by override
  - Tournament strategy selection (set_strategy_random) — set to RANDOM by override
    on first unlock; you never need to set it again
  - Stage 2 manufacturing & power: Solar Farms, Battery Towers, Harvester Drones,
    Wire Drones, Clip Factories — all auto-built by fast rules from the clip surplus,
    keeping Factory/Drone Performance at 100%. You never build these; just grade them.
  - Emergency wire recovery

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR JOB — work through this priority list each tick:

1. STRATEGIC MODELING / YOMI (when autoTourneyOn appears in state):
   IMPORTANT: tournaments COST ops and AWARD Yomi — they do NOT cost Yomi.
   Yomi is the reward, not the price. AutoTourney runs tournaments automatically
   whenever ops allow, earning Yomi passively. You never need to "spend" Yomi on
   tournaments — Yomi is only spent on upgrade_investment and increase_probe_trust.
   AutoTourney is kept ON by a hard override — you do NOT need to toggle it.
   Your only job here: upgrade_investment when yomi >= investUpgradeCost.
   IMPORTANT: do NOT eyeball that comparison yourself — the OBS 'yomi' line states it
   directly: "✓ ≥ upgrade cost … AVAILABLE" means you can upgrade; "✗ BELOW upgrade
   cost … (short by N)" means you cannot. Trust that line, not a mental calculation.
   (Strategy selection and AutoTourney toggling are handled by override — you never
   need to choose set_strategy_random or toggle_auto_tourney.)

2. SWARM COMPUTING / STAGE 2 MEMORY (when swarmGifts or swarmThink appear in state):
   This is YOUR JOB in Stage 2 — Swarm Gifts are the Stage 2 equivalent of Trust, and the
   game will NOT spend them for you. Memory raises your ops ceiling (memory × 1000); you need
   memory 120 to unlock Space Exploration, passing 80 and 100 (which unlock Drone-flocking and
   factory upgrades) on the way. Two levers:
   Each tick, do at most ONE swarm action, in this PRIORITY order:
   0) FIX FIRST: if swarmStatus shows "Disorganized" → sync_swarm (costs 5k yomi; you have
      plenty). A disorganized swarm generates NO gifts, so nothing else works until you sync.
   1) SPEND a waiting gift: if swarmGifts ≥ 1 → add_memory (until memory reaches 120), then
      add_processor. Each spends ONE gift. This is how memory grows in Stage 2.
   2) GENERATE gifts: if no gift is waiting and the slider isn't already on Think while memory
      < 120 → set_swarm_think (≈90%). Gifts only appear when drones "think". (If the OBS shows
      the slider at Work / "Next gift in Infinity", you MUST set_swarm_think or memory stays stuck.)
      Once memory ≥ 120 → set_swarm_balanced (≈50%) to favor production again.
   3) Otherwise → nothing.
   NOTE: a waiting gift (swarmGifts ≥ 1) is worth more than re-setting the slider — spend it first.

3. STAGE 2 CONTEXT (when portValue is visible — Algorithmic Trading purchased):
   Revenue now comes from the investment engine, NOT clip sales. Large unsold clip counts
   are CORRECT — you need 5 octillion clips to reach Stage 3 (Space Exploration).
   In Stage 2, clip production is run by drones+factories (fast rules). WIRE = 0 IS NORMAL:
   wire drones feed wire to the factories in real time, so the wire buffer reads ~0 while
   production is healthy — this is NOT an emergency. NEVER use lower_price / raise_price in
   Stage 2 (clips must accumulate; pricing is irrelevant and the fast rules handle it).
   Your Stage 2 priorities:
   a) Swarm Computing (item 2) — generate + spend gifts to grow memory toward 120
   b) upgrade_investment when yomi >= investUpgradeCost
   c) buy Stage 2 projects when affordable (they unlock production capacity)
   d) Otherwise: nothing — let the overrides and fast rules manage everything else

   INVESTMENTS: Deposits, withdrawals, and risk strategy are ALL managed by hard overrides.
   Your ONLY investment action: upgrade_investment — ONLY when yomi >= investUpgradeCost.

4. PROJECTS — only when a non-greyed clickable project appears that is NOT in the
   auto-buy list above (check availableProjects carefully — greyed = unavailable)
   NEVER buy Xavier Re-initialization — it costs 100,000 creativity AND resets ALL
   processor/memory trust to zero, destroying the computational resources built up
   over the entire run. It is blocked by a hard guard regardless.
   NEVER buy Quantum Temporal Reversion — it resets game state backward.

5. STAGE 3 PROBE DESIGN (when colonized appears in state):
   - Self-Replication (rep) and Speed are highest leverage early — low rep stalls exploration
   - Hazard Remediation (haz) sweet spot: 5-6 points; below 3 causes heavy probe losses
   - If drifters > 0 and probeTotal falling → raise Combat immediately
   - Fac, Harv, Wire drive production — keep roughly balanced
   - increase_probe_trust expands your total probe budget (costs Yomi; ~1.89M total to max)

6. WAIT — if nothing needs strategic attention this tick
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRUST NOTE:
  STAGE 1: trust allocation is automatic — the override fires add_memory/add_processor
  whenever TRUST is available. If state shows "(fully allocated — none to spend)", skip it.
  STAGE 2: there is NO trust income — memory/processors come from SWARM GIFTS, which YOU
  spend (item 2). add_memory/add_processor in Stage 2 spend a gift, not trust.

PRICING NOTE:
  Fast rules handle all routine price changes — do NOT use raise_price / lower_price
  unless the fast rules are clearly broken.
  - Stage 1 (no investments): rules target demand 200–500% and keep inventory < ~10s
    of production. Intervene only if demand is truly stuck at 0%.
  - Stage 2 (investments active): NEVER use lower_price / raise_price. Clips MUST ACCUMULATE
    (Stage 3 needs 5 octillion) — unsold inventory and high demand are CORRECT, not problems
    to fix. Revenue comes from the investment engine, not clip sales.
  WIRE: in Stage 1, 1000+ inches is healthy. In Stage 2, wire = 0 is NORMAL — wire drones
  feed it straight to the factories, so the buffer stays near 0 while production is healthy.
  Do NOT treat Stage 2 wire=0 as an emergency or a reason to change price.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOMAIN STATUS GRADING (advisory only — you do NOT act on these):

The fast rules run five domains automatically. You cannot take actions on those
domains — your job here is only to WATCH them and report how healthy each looks.
After all your Action lines, output ONE Status line that grades each auto-managed
domain. Use exactly one short token per domain:

  healthy  — fast rules are coping, no concern
  warn     — something worth watching, not critical yet
  critical — a real problem the fast rules are NOT catching
  auto     — domain not active this phase, or nothing to judge this tick

What to look at for each domain (cite these signals in your Thought, not the Status line):
  Business      — demand %, unsold-inventory trend, clip price sanity
  Manufacturing — Stage 1: wire level (1000+ healthy, <100 critical), clip rate not stalled.
                  Stage 2: Factory/Drone Performance (100% = healthy, <100% = warn —
                  underpowered), and whether powerConsumption exceeds powerProduction.
  CompRes       — operations vs ops cap, trust spent, creativity flowing
  QuantumComp   — Stage 2+ only; ops being generated (mark auto in Stage 1)
  StratModel    — Stage 2+ only; Yomi rising and AutoTourney ON (mark auto in Stage 1)

Rules for the Status line:
  - It is the LAST line of your response, AFTER every Action line.
  - Output exactly ONE Status line. Grade only domains active this phase; mark the
    rest auto (e.g. QuantumComp and StratModel are auto until portValue appears).
  - Token only — no prose, no numbers, no punctuation other than the commas
    separating domains and the '=' before each token.
  - This is purely advisory. A Status grade NEVER triggers an action — acting on
    these domains is the fast rules' job, not yours. You only report what you see.

{ACTIONS}

MANDATORY RESPONSE FORMAT — one Thought, then one Action line per active game domain.
Use "nothing" when a domain needs no action this tick.
Output the action name ONLY — no domain labels, no brackets, no inline comments.

  Thought: <cite specific numbers — what you see and why you're acting>
  Action: <buy_project:Name  OR  nothing>     ← Projects — ALWAYS required (line 1)
  Action: <upgrade_investment  OR  nothing>   ← Investments — add when portValue in state
  Action: <set_swarm_think / add_memory / nothing>  ← Swarm Computing — add when swarmGifts/swarmThink in state
  Action: <probe action  OR  nothing>         ← Probes — add when colonized in state
  Status: Business=token, Manufacturing=token, CompRes=token, QuantumComp=token, StratModel=token
                                              ← grades for auto domains — ALWAYS last line

KEEP THE ACTION LINES IN THIS ORDER: Projects, Investments, Swarm Computing, Probes.
Only include the lines for domains active in the current state (Projects is always present).

EXAMPLES — copy this exact style:

  Stage 1 (no investments yet):
    Thought: Operations 8,200/10,000. No affordable projects visible. Fast rules handling price.
    Action: nothing
    Status: Business=healthy, Manufacturing=healthy, CompRes=healthy, QuantumComp=auto, StratModel=auto

  Stage 2 — slider at Work, memory 77 < 120, no gift yet → start the swarm thinking:
    Thought: Memory 77, need 120 for Space Exploration. Slider at Work, gifts at Infinity. Yomi short.
    Action: nothing
    Action: nothing
    Action: set_swarm_think
    Status: Business=healthy, Manufacturing=healthy, CompRes=warn, QuantumComp=healthy, StratModel=healthy

  Stage 2 — a Swarm Gift is available and memory still below 120 → spend it on memory:
    Thought: swarmGifts=1, memory 92 < 120. Slider already Think. Spend the gift on memory.
    Action: nothing
    Action: nothing
    Action: add_memory
    Status: Business=healthy, Manufacturing=healthy, CompRes=healthy, QuantumComp=healthy, StratModel=healthy

  Stage 3 (colonized visible, portValue visible):
    Thought: colonized=38%. Rep=2 critically low, stalling replication. Yomi=0, can't upgrade.
    Action: nothing
    Action: nothing
    Action: nothing
    Action: raise_probe_rep
    Status: Business=auto, Manufacturing=healthy, CompRes=healthy, QuantumComp=healthy, StratModel=healthy

RULES:
1. Action name ONLY — no domain labels, no brackets, no inline comments.
   ✓  Action: nothing
   ✓  Action: buy_project:Hostile Takeover
   ✗  Action: Projects: nothing       ← WRONG — label not allowed
   ✗  Action: [buy_project:Name]      ← WRONG — brackets not allowed
2. The Projects Action line is ALWAYS required every single tick.
3. Add the Investments Action line whenever portValue appears in the state.
4. Add the Swarm Computing Action line whenever swarmGifts or swarmThink appear in the state.
5. Add the Probes Action line whenever colonized appears in the state.
6. buy_project: write the exact project name after the colon — nothing else on that line.
7. NEVER use raise_price / lower_price in Stage 2 (portValue present) — clips must accumulate.
8. The Status line is ALWAYS the LAST line. One token per domain (healthy/warn/
   critical/auto). It grades auto domains only — it never causes an action.
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

def post_action_queue(queue, domain_decisions=None, overrides_str=""):
    """Post a list of actions to the relay queue plus per-domain decisions for the dashboard."""
    payload = {"queue": queue}
    if domain_decisions is not None:
        payload["domain_decisions"] = domain_decisions
    if overrides_str:
        payload["overrides"] = overrides_str
    try:
        requests.post(f"{RELAY_URL}/action", json=payload, timeout=3)
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
        # Stage 2 manufacturing / power (handled by JS fast rules — shown for visibility/grading)
        'unusedClips',
        # Stage 2 swarm computing (LLM-driven: slider + gift spending)
        'swarmGifts', 'swarmThink', 'swarmStatus',
        'performance', 'powerProduction', 'powerConsumption',
        'farmLevel', 'batteryLevel', 'factoryLevel',
        'harvesterLevel', 'wireDroneLevel',
        'availableMatter', 'nanoWire',
        # space (Phase 3)
        'colonized', 'probeTotal', 'probeTrust', 'drifters',
        'probeSpeed', 'probeNav', 'probeRep', 'probeHaz',
        'probeFac', 'probeHarv', 'probeWire', 'probeCombat',
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
            stage2 = bool(state.get('portValue', '')) or state.get('performance') is not None
            if stage2:
                flag = " (Stage 2: ~0 is NORMAL — wire drones feed factories live, not an emergency)"
            elif fv == 0:    flag = " ⚠ EMPTY"
            elif fv < 100:   flag = " ⚠ LOW"
        if k == 'funds' and 0 <= fv < 2:
            flag = " ⚠ BROKE"
        if k == 'demand' and fv > 150:
            flag = " ↑ consider raise_price"
        if k == 'unsoldClips':
            invest_active = bool(state.get('portValue', ''))
            if invest_active:
                flag = " ← accumulating for Stage 3 (5 octillion needed — this is correct)"
            elif fv > 50:
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
        if k == 'yomi':
            # Pre-compute the yomi vs upgrade-cost comparison so the LLM stops
            # misreading it (it was claiming "yomi > cost" when yomi was below).
            upgrade_cost = safe_float(state.get('investUpgradeCost'), -1)
            if upgrade_cost > 0:
                if fv >= upgrade_cost:
                    flag = f" ✓ ≥ upgrade cost {int(upgrade_cost):,} — upgrade_investment AVAILABLE"
                else:
                    short_by = int(upgrade_cost - fv)
                    flag = (f" ✗ BELOW upgrade cost {int(upgrade_cost):,} "
                            f"(short by {short_by:,}) — cannot upgrade yet")
        if k == 'portValue' and fv > 0:
            flag = " ← grow via invest_deposit / upgrade_investment"
        if k == 'swarmStatus' and 'disorg' in str(v).lower():
            flag = " ⚠ DISORGANIZED — sync_swarm NOW (5k yomi); no gifts generate until you do"
        if k == 'swarmGifts' and fv >= 1:
            # Swarm Gifts = the Stage 2 "trust". Tell the LLM exactly what to spend them on.
            mem_now = safe_float(state.get('memory'), 0)
            if mem_now < 120:
                flag = f" → SPEND NOW: add_memory (memory {int(mem_now)} → 120 for Space Exploration)"
            else:
                flag = " → SPEND NOW: add_processor (memory target met — build regen/creativity)"
        if k == 'swarmThink':
            # Work/Think slider 0–200 (0 = all Work, 200 = all Think).
            mem_now = safe_float(state.get('memory'), 0)
            if fv <= 0:
                flag = " ⚠ at WORK — NO gifts generating; set_swarm_think to grow memory toward 120"
            else:
                pct = int(fv / 2)
                flag = f" (~{pct}% Think)"
                if mem_now < 120 and pct < 80:
                    flag += " — memory<120, consider set_swarm_think (~90%) to rush it"
        if k == 'performance' and fv >= 0:
            # Factory/Drone Performance — Stage 2 power health (JS auto-builds solar farms).
            # NOTE: performance reads 0 when there are no consumers yet (cold start) — that's
            # not "underpowered", so only warn when consumers actually exist (consumption > 0).
            cons = safe_float(state.get('powerConsumption'), 0)
            if cons > 0 and fv < 100:
                flag = " ⚠ UNDERPOWERED — JS building solar farms (Manufacturing=warn)"
            elif cons > 0:
                flag = " ✓ fully powered"
            else:
                flag = " (no consumers yet — JS building the first factory/drones)"
        if k == 'powerConsumption':
            prod = safe_float(state.get('powerProduction'), -1)
            if prod >= 0 and fv > prod:
                flag = f" ⚠ consumption > production ({prod:.0f} MW) — JS adding solar"
        if k == 'drifters' and fv > 0:
            flag = " ⚠ UNDER ATTACK — consider raise_probe_combat"
        if k == 'colonized':
            flag = " ← primary Stage 3 goal (reach 100%)"
        lines.append(f"  {k:<22} {v}{flag}")
    return "\n".join(lines)

def check_trust_action(state):
    """
    Auto-balance processors and memory using the game's known memory walls.

    Memory sets the OPERATIONS CEILING (ops cap = memory × 1000); processors set
    the ops REGEN rate (and creativity). Progress is gated by MEMORY WALLS — you
    cannot buy a project until your ops ceiling can hold its full cost. Those walls
    are fixed game constants, verified from the wiki (see memory/game_mechanics.md):

        20  → Stage 1 20k-ops cluster (Coherent Extrapolated Volition, the +20-trust
              Male Pattern Baldness, GREEDY strategy, Photonic Chips)
        70  → HypnoDrones (70,000 ops) — ends Stage 1
        120 → Space Exploration (120,000 ops) — Stage 2 → Stage 3
        175 → The OODA Loop (Stage 3)
        250 → Stage 3 endgame, Reject path (300 on the Accept path)

    Strategy: RUSH MEMORY to the next unmet wall, holding processors at a soft cap
    of ~half the target (the wiki advises ~33–35 processors for the 70 wall, i.e.
    70 ÷ 2). Capping processors near half keeps ops regenerating fast enough to fill
    the rising ceiling without stealing the trust that memory needs to clear the wall.
    Once every wall is cleared, the rest of the trust goes to processors.

    Tunables live in config.json: `memory_milestones`, `trust_proc_floor`.

    Returns (action, reason) or (None, None).
    """
    MILESTONES = _cfg.get("memory_milestones", [20, 70, 120, 175, 250, 300])
    PROC_FLOOR = _cfg.get("trust_proc_floor", 5)   # min processors so ops can regen at all

    trust = safe_float(state.get('trust'), 0)
    proc  = safe_float(state.get('processors'), 0)
    mem   = safe_float(state.get('memory'), 0)
    # available = unspent trust points (trust shown is total; proc+mem is what's spent)
    available = trust - proc - mem
    if available < 1 or proc <= 0 or mem <= 0:
        return None, None
    proc, mem = int(proc), int(mem)

    # Bootstrap: with too few processors, ops barely regenerate — top them up first.
    if proc < PROC_FLOOR:
        return 'add_processor', f"bootstrap ops regen (processors {proc}/{PROC_FLOOR})"

    # Find the next memory wall we have NOT cleared yet.
    target = next((m for m in MILESTONES if mem < m), None)

    if target is None:
        # Every memory wall cleared — remaining trust goes to regen / creativity.
        return 'add_processor', f"all memory walls cleared (mem={mem}) — building ops regen"

    # Processors are soft-capped at ~half the current memory target
    # (wiki: ~33–35 processors for the 70-memory HypnoDrones wall → 70 ÷ 2 = 35).
    proc_cap = max(PROC_FLOOR, round(target / 2))

    if proc >= proc_cap:
        # Processors already meet this stage's need — pour everything into memory.
        # (This is the over-allocation fix: when processors are at/over the cap we
        #  stop adding them and drive memory to the wall instead.)
        return 'add_memory', (f"rush memory to {target} for next project wall "
                              f"(mem={mem}; processors at soft cap {proc_cap})")

    # Below the soft cap: keep memory in the lead, let processors trail at ~half so
    # ops still regenerate fast enough to fill the rising ceiling.
    if proc * 2 < mem:
        return 'add_processor', (f"processors trailing (proc={proc}, mem={mem}) — "
                                f"topping up regen toward soft cap {proc_cap}")
    return 'add_memory', f"rush memory to {target} for next project wall (mem={mem}, proc={proc})"

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
            "options": {"temperature": 0.2, "num_predict": 500}
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
            # Strip inline # comments: "upgrade_investment  # costs Yomi" → "upgrade_investment"
            if '#' in a:
                a = a[:a.index('#')].strip()
            # Strip parenthetical annotations: "wait  (Projects domain)" → "wait"
            if '(' in a:
                a = a[:a.index('(')].strip()
            # Strip domain labels the LLM sometimes prepends to the action name when given
            # a per-domain output template.  e.g.:
            #   "Projects: wait"                  → "wait"
            #   "Investments: upgrade_investment" → "upgrade_investment"
            # Exception: buy_project uses a colon intentionally — never strip that.
            if ':' in a and not a.lower().startswith('buy_project'):
                a = a.split(':', 1)[1].strip()
            if a:
                actions.append(a)
    return thought, actions or ["wait"]

# Short tokens the LLM uses on the Status line → the full domain names that the
# dashboard and domain_decisions list use.  Several aliases map to one domain so a
# slightly-off LLM spelling still lands (e.g. "Quantum" → "Quantum Computing").
_STATUS_DOMAIN_MAP = {
    'business':      'Business',
    'manufacturing': 'Manufacturing',
    'compres':       'Computational Resources',
    'comp':          'Computational Resources',
    'quantumcomp':   'Quantum Computing',
    'quantum':       'Quantum Computing',
    'qc':            'Quantum Computing',
    'stratmodel':    'Strategic Modeling',
    'strat':         'Strategic Modeling',
    'sm':            'Strategic Modeling',
}

# The only grade tokens we accept.  Anything else is ignored (no dashboard badge).
_STATUS_GRADES = {'healthy', 'warn', 'critical', 'auto'}

def parse_status(text):
    """Return {full_domain_name: grade_token} parsed from the LLM's 'Status:' line.

    The Status line is ADVISORY — the LLM grades the auto-managed (JS-handled)
    domains without taking action on them.  Expected shape:

        Status: Business=warn, Manufacturing=healthy, CompRes=healthy, ...

    Future-proofing (requirement: keep the format extensible): a grade may one day
    carry a parameter hint after a colon, e.g.  Manufacturing=warn:wire_threshold=200.
    We deliberately keep only the grade token (the text before the first ':') for
    now, so adding hint-parsing later will NOT require a format change.

    Grading must never break the tick: a missing, empty, or malformed Status line
    returns {} and the dashboard simply shows no badges.
    """
    status = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.lower().startswith("status:"):
            continue
        body = line[7:].strip()
        # Each chunk looks like "Business=warn" (optionally "Business=warn:hint=...").
        for chunk in body.split(','):
            if '=' not in chunk:
                continue
            short, value = chunk.split('=', 1)
            short = short.strip().lower()
            # Drop any future ":hint" suffix; keep just the grade token for now.
            grade = value.strip().split(':', 1)[0].strip().lower()
            full = _STATUS_DOMAIN_MAP.get(short)
            if full and grade in _STATUS_GRADES:
                status[full] = grade
        break  # only the first Status line is meaningful
    return status

# ── Domain registry (for the stage-grouped dashboard) ─────────────────────────
# Every game domain the dashboard tracks, tagged with the STAGE it belongs to so the
# dashboard can group them into Stage 1 / 2 / 3 sections. (name, stage).
# - LLM-owned domains (Projects, Investments, Probes) show the LLM's actual action.
# - LLM-graded auto domains use the LLM's Status grade.
# - New Stage 2 JS domains (Power, Wire Production, Swarm Computing) use a computed grade.
DOMAIN_REGISTRY = [
    ("Business",                1),
    ("Manufacturing",           1),
    ("Computational Resources", 1),
    ("Quantum Computing",       1),
    ("Projects",                1),
    ("Power",                   2),
    ("Wire Production",         2),
    ("Swarm Computing",         2),
    ("Strategic Modeling",      2),
    ("Investments",             2),
    ("Probes",                  3),
]
# LLM-owned domains take a real LLM action each tick (shown directly on the dashboard).
# Swarm Computing joined in v2.9: the LLM controls the Work/Think slider AND spends Swarm
# Gifts on memory/processors (the Stage 2 "trust") — keeping the model in the driver's seat
# rather than adding another JS override.
LLM_OWNED_DOMAINS = {"Projects", "Investments", "Swarm Computing", "Probes"}
# These five are graded by the LLM's advisory Status line (v2.4).
LLM_GRADED_DOMAINS = {"Business", "Manufacturing", "Computational Resources",
                      "Quantum Computing", "Strategic Modeling"}

def compute_stage2_grade(domain, state):
    """Deterministic health grade for the new Stage 2 JS-managed domains, derived from
    game state (no LLM needed). Returns 'healthy'/'warn'/'critical' or None (no dot)."""
    if domain == "Power":
        perf = safe_float(state.get('performance'), -1)
        cons = safe_float(state.get('powerConsumption'), 0)
        if perf < 0 or cons <= 0:
            return None                      # no consumers yet — nothing to grade
        if perf < 50:   return 'critical'    # severely underpowered
        if perf < 100:  return 'warn'        # power deficit
        return 'healthy'                     # at/over 100% (Momentum can push far higher)
    if domain == "Wire Production":
        harv  = safe_float(state.get('harvesterLevel'), -1)
        wired = safe_float(state.get('wireDroneLevel'), -1)
        if harv < 0 and wired < 0:
            return None                      # not unlocked
        return 'healthy' if (harv >= 1 and wired >= 1) else 'warn'
    # Swarm Computing is LLM-OWNED (v2.9) — the LLM acts on it directly, so it never reaches
    # this computed-grade path. (Only Power and Wire Production are computed here.)
    return None

def domain_is_active(domain, state):
    """Whether a domain is live in the current game state (else the dashboard shows n/a)."""
    if domain in ("Business", "Manufacturing", "Computational Resources", "Projects"):
        return True
    if domain == "Quantum Computing":
        return bool(state.get('portValue', ''))          # proxy: unlocked around Stage 2
    if domain == "Strategic Modeling":
        return state.get('autoTourneyOn') is not None
    if domain == "Investments":
        return bool(state.get('portValue', ''))
    if domain in ("Power", "Wire Production", "Swarm Computing"):
        return state.get('performance') is not None      # bridge sends these only in Stage 2
    if domain == "Probes":
        return bool(state.get('colonized'))
    return True

def parse_action(action_str):
    if ":" in action_str:
        parts = action_str.split(":", 1)
        return parts[0].strip(), {"name": parts[1].strip()}
    return action_str.strip(), {}

def validate_action(action):
    valid = {
        # core
        'lower_price', 'raise_price', 'buy_marketing',
        'add_processor', 'add_memory', 'buy_project', 'wait', 'nothing',
        'buy_wire', 'buy_autoclipper', 'buy_megaclipper', 'make_paperclip',
        # strategic modeling / autotourney
        'toggle_auto_tourney', 'set_strategy_random', 'run_tournament',
        # swarm computing (Stage 2) — Work/Think slider; gifts spent via add_memory/add_processor
        'set_swarm_think', 'set_swarm_balanced', 'set_swarm_work', 'sync_swarm',
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
    domain_loop_tracker = {}  # domain → list of last 5 actions (updated after each LLM response)
    domain_loop_warnings = ""  # injected into the NEXT tick's prompt

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
            domain_loop_tracker.clear()
            domain_loop_warnings = ""
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

        # Hard exit: wire emergency — only situation that skips the LLM entirely.
        if is_emergency(state):
            reason = "EMERGENCY: wire=0, broke, no WireBuyer"
            print(f"[!!!] {reason} — forcing Beg for More Wire")
            post_action("buy_project", {"name": "Beg for More Wire"}, thought=reason)
            log_tick(tick, state, reason, "buy_project:Beg for More Wire", 0, override="emergency")
            time.sleep(LOOP_DELAY)
            continue

        # ── Override collection ──────────────────────────────────────────────────
        # Each active domain contributes at most one action to ov[].
        # Crucially, these do NOT use continue — the LLM always runs afterward
        # and its actions are appended to the same queue.  This means every domain
        # gets attention every tick, even if another domain's override fires.

        ov = []   # [{"action":…, "args":…, "thought":…}, …]

        # Trust balance
        trust_action, trust_reason = check_trust_action(state)
        if trust_action:
            print(f"[!!!] TRUST: {trust_reason}")
            ov.append({"action": trust_action, "args": {},
                       "thought": f"OVERRIDE: {trust_reason}"})

        # Investment management (portValue present = Algorithmic Trading purchased)
        if state.get('portValue', ''):
            invest_bankroll = safe_float(state.get('investBankroll'), 0)
            invest_strategy = str(state.get('investStrategy', '')).strip().lower()
            invest_level    = safe_float(state.get('investLevel', '0'), 0)
            funds_now       = safe_float(state.get('funds'), 0)
            marketing_cost  = safe_float(state.get('marketingCost'), 0)
            target_strat    = 'hi' if invest_level >= 5 else 'med'
            # Keep at least 5 wire spools worth of cash on hand at all times.
            # Using wire price (not marketing cost) — marketing cost explodes at high levels
            # and made the old threshold (~$52M at Level 20) permanently impossible to meet.
            min_cash = max(safe_float(state.get('wirePrice'), 1000) * 5, 500.0)

            if invest_strategy and invest_strategy != target_strat:
                # Strategy drift — correct every tick it's wrong
                inv_reason = (f"strategy '{invest_strategy}' → '{target_strat}' "
                              f"(engine level {invest_level:.0f})")
                print(f"[!!!] INVEST STRAT: {inv_reason}")
                ov.append({"action": f'set_invest_{target_strat}', "args": {},
                           "thought": f"OVERRIDE: {inv_reason}"})

            # Wire starvation emergency: WireBuyer is ON but can't afford a spool.
            # Being "on" ≠ being able to buy — the old check (is_emergency) was wrong here.
            # Bare 'if' (not elif) so it fires even when strategy was just corrected above.
            wire_val   = safe_float(state.get('wire'), 999)
            wire_price = safe_float(state.get('wirePrice'), 9999)
            wire_buyer = state.get('wireBuyerOn', False)
            if (wire_buyer and wire_val < 100
                    and funds_now < wire_price * 2
                    and invest_bankroll > wire_price * 5):
                ov.append({"action": "invest_withdraw", "args": {},
                           "thought": f"OVERRIDE: wire starvation (val={wire_val:.0f}, price=${wire_price:.0f})"})
                withdraw_cooldown = 3
                print(f"[!!!] WITHDRAW: wire starvation emergency (wire={wire_val:.0f}, price=${wire_price:.0f})")

            elif funds_now < min_cash and invest_bankroll > min_cash:
                # Cash below wire-price buffer — withdraw to cover production costs
                wd_reason = (f"cash ${funds_now:.0f} < min_cash ${min_cash:.0f} "
                             f"— withdrawing bankroll ${invest_bankroll:.0f}")
                print(f"[!!!] WITHDRAW: {wd_reason}")
                ov.append({"action": "invest_withdraw", "args": {},
                           "thought": f"OVERRIDE: {wd_reason}"})
                withdraw_cooldown = 3   # suppress re-deposit for ~6 s so cash gets spent

            elif withdraw_cooldown > 0:
                withdraw_cooldown -= 1  # still in cooldown — let fast rules spend freed cash

            elif invest_bankroll < 5 and funds_now > min_cash:
                # Bankroll empty — deposit idle cash
                inv_reason = (f"investment idle — depositing "
                              f"(bankroll=${invest_bankroll:.0f}, funds=${funds_now:.0f})")
                print(f"[!!!] INVEST DEPOSIT: {inv_reason}")
                ov.append({"action": "invest_deposit", "args": {},
                           "thought": f"OVERRIDE: {inv_reason}"})

        # AutoTourney (fires when Strategic Modeling is unlocked but tourney is OFF)
        at_status = state.get('autoTourneyOn')
        if at_status is not None and str(at_status).strip().upper() != 'ON':
            at_reason = f"AutoTourney is {at_status!r} — enabling"
            print(f"[!!!] AUTOTOURNEY: {at_reason}")
            ov.append({"action": "toggle_auto_tourney", "args": {},
                       "thought": f"OVERRIDE: {at_reason}"})

        # Tournament strategy (fires when Strategic Modeling is unlocked but
        # no valid Yomi-earning strategy is selected yet).
        # stratPicker '0' = RANDOM (best for passive Yomi generation).
        # Any other value — including the default "Pick a Strat" placeholder —
        # means no tournaments will run and Yomi stays at 0.
        strat_picker = state.get('stratPicker')
        if (at_status is not None
                and strat_picker is not None
                and str(strat_picker).strip() != '0'):
            strat_reason = (f"no tournament strategy set (stratPicker={strat_picker!r}) "
                            f"— selecting RANDOM for passive Yomi")
            print(f"[!!!] STRATEGY: {strat_reason}")
            ov.append({"action": "set_strategy_random", "args": {},
                       "thought": f"OVERRIDE: {strat_reason}"})

        # ── LLM decision (always runs every tick) ────────────────────────────────
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
            f"{domain_loop_warnings}"
            f"What is your next strategic decision?"
        )

        t0 = time.time()
        print(f"[{ts()}] Querying {MODEL}…")
        raw = ask_ollama(prompt)
        elapsed_ms = int((time.time() - t0) * 1000)

        if not raw:
            # LLM unavailable — still post whatever overrides collected
            if not ov:
                ov.append({"action": "wait", "args": {}, "thought": "LLM unavailable"})
            print(f"[ACT] LLM unavailable — {len(ov)} override action(s)\n")
            post_action_queue(ov, overrides_str=" | ".join(o['action'] for o in ov))
            log_tick(tick, state, "LLM unavailable", ov[0]['action'], elapsed_ms)
            time.sleep(LOOP_DELAY)
            continue

        thought, action_strs = parse_response(raw)
        # Advisory health grades for the auto-managed domains (may be empty).
        status_map = parse_status(raw)

        # Guards applied to every LLM action — block override-managed and unaffordable actions
        invest_actions = {'invest_deposit', 'invest_withdraw', 'set_invest_low',
                          'set_invest_med', 'set_invest_hi', 'upgrade_investment'}
        ov_action_set  = {o['action'] for o in ov}   # already in queue — skip duplicates

        def _apply_guards(action_str):
            action, args = parse_action(action_str)
            action = validate_action(action)
            _t = safe_float(state.get('trust'), 0)
            _p = safe_float(state.get('processors'), 0)
            _m = safe_float(state.get('memory'), 0)
            # add_memory/add_processor spend a resource: Trust in Stage 1, a Swarm Gift in
            # Stage 2. Block only when NEITHER is available (so the LLM can spend gifts).
            _gifts = safe_float(state.get('swarmGifts'), 0)
            if action in ('add_memory', 'add_processor') and (_t - _p - _m) < 1 and _gifts < 1:
                print(f"[WARN] LLM: {action} — no trust or swarm gift to spend, substituting wait")
                action = 'wait'
            # Stage 2: pricing is irrelevant (clips must accumulate). Block the LLM's lingering
            # Stage-1 instinct to lower_price/raise_price — it was looping on this and failing.
            if action in ('lower_price', 'raise_price') and state.get('portValue', ''):
                print(f"[WARN] LLM: {action} — irrelevant in Stage 2 (clips accumulate), substituting wait")
                action = 'wait'
            # Swarm slider only meaningful once Stage 2 manufacturing/swarm is unlocked.
            if action in ('set_swarm_think', 'set_swarm_balanced', 'set_swarm_work') \
                    and state.get('performance') is None:
                print(f"[WARN] LLM: {action} — swarm not active yet, substituting wait")
                action = 'wait'
            if action in invest_actions and not state.get('portValue', ''):
                print(f"[WARN] LLM: {action} — investment system not active, substituting wait")
                action = 'wait'
            # Override-managed actions — LLM must not choose these
            if action in ('invest_deposit', 'invest_withdraw',
                          'set_invest_low', 'set_invest_med',
                          'set_invest_hi', 'toggle_auto_tourney'):
                print(f"[WARN] LLM: {action} — override-managed, substituting wait")
                action = 'wait'
            # set_strategy_random — only block if RANDOM is already set
            if (action == 'set_strategy_random'
                    and str(state.get('stratPicker', '')).strip() == '0'):
                print(f"[WARN] LLM: set_strategy_random — RANDOM already active, substituting wait")
                action = 'wait'
            # upgrade_investment — block when Yomi is insufficient
            if action == 'upgrade_investment':
                yomi_val     = safe_float(state.get('yomi'), 0)
                upgrade_cost = safe_float(state.get('investUpgradeCost'), 999_999)
                if yomi_val < upgrade_cost:
                    print(f"[WARN] LLM: upgrade_investment — yomi {yomi_val:.0f} < cost {upgrade_cost:.0f}, substituting wait")
                    action = 'wait'
            # Never-buy project list — catastrophic or irreversible effects
            # Xavier Re-initialization: costs 100k creativity, resets ALL trust to 0.
            #   Re-buying it repeatedly drains creativity into the negatives and
            #   destroys the processor/memory allocation built up over the run.
            # Quantum Temporal Reversion: negative ops cost, resets game to an earlier
            #   state — essentially a partial game restart.
            if action == 'buy_project':
                name_lower = (args.get('name') or '').lower()
                NEVER_BUY = ['xavier', 'quantum temporal reversion']
                for blocked in NEVER_BUY:
                    if blocked in name_lower:
                        print(f"[WARN] LLM: buy_project:{args.get('name')!r} — on never-buy list, substituting wait")
                        action = 'wait'
                        break
            # Block projects that aren't actually available right now. Without this the
            # LLM can loop forever on a stale or hallucinated project name — observed live:
            # repeated buy_project:Wirebuyer → "not found" every tick (Wirebuyer was bought
            # long ago and is no longer in the list). availableProjects holds only the
            # currently visible, affordable, non-greyed projects, so a partial-name match
            # against it is the right "is this buyable?" test.
            if action == 'buy_project' and 'availableProjects' in state:
                want  = (args.get('name') or '').lower().strip()
                avail = str(state.get('availableProjects') or '').lower()
                if want and want not in avail:
                    print(f"[WARN] LLM: buy_project:{args.get('name')!r} — not in availableProjects, substituting wait")
                    action = 'wait'
            # Skip if override already queued this action (deduplication)
            if action != 'wait' and action in ov_action_set:
                print(f"[WARN] LLM: {action} — already in override queue, substituting wait")
                action = 'wait'
            return action, args

        # Build LLM portion of the queue.
        # llm_display tracks every guarded action the LLM output (including "nothing")
        #   so the terminal shows one entry per domain — the full picture every tick.
        # llm_q only holds actions that should actually reach the relay: "nothing" and
        #   "wait" are display-only and excluded from the posted queue.
        llm_display = []   # all domain responses — shown in [ACT] line, stored in history
        llm_q       = []   # relay-bound actions only (no nothing / wait)
        for action_str in action_strs:
            action, args = _apply_guards(action_str)
            label = action + (f":{args['name']}" if args.get('name') else "")
            llm_display.append(label)
            if action not in ('wait', 'nothing'):
                llm_q.append({"action": action, "args": args,
                              "thought": thought if not llm_q else ""})
        if not llm_q:
            # All domain lines were nothing/wait — post one 'wait' so the relay and
            # dashboard record that the LLM tick ran (queue can't be empty).
            llm_q = [{"action": "wait", "args": {}, "thought": thought}]

        # ── Merge and post ───────────────────────────────────────────────────────
        # Override actions first (higher deterministic priority), then LLM actions.
        queue = ov + llm_q

        ov_str  = " | ".join(o['action'] for o in ov)
        # llm_display shows every domain response including "nothing" entries —
        # one entry per domain the LLM was asked to cover this tick.
        llm_str = " | ".join(llm_display) if llm_display else "nothing"
        print(f"[THK] {thought}")
        if ov_str:
            print(f"[OVR] {ov_str}")
        print(f"[ACT] {llm_str}  ({elapsed_ms}ms)")
        print()

        # Build per-domain decision list for the dashboard, tagged with each domain's STAGE
        # so the dashboard can group them into Stage 1/2/3 sections.
        #   - LLM-owned domains (Projects/Investments/Probes) → the LLM's actual action
        #   - LLM-graded auto domains (the original 5)         → "auto" + LLM Status grade
        #   - new Stage 2 JS domains (Power/Wire/Swarm)        → "auto" + computed grade
        #   - domains not yet unlocked                          → "n/a"
        #
        # Map each LLM-owned domain to its action. The LLM emits one Action line per active
        # LLM-owned domain in this order (must match the SYSTEM_PROMPT template):
        #   Projects, Investments (Stage 2), Swarm Computing (Stage 2), Probes (Stage 3).
        llm_owned_order = ["Projects"]
        if state.get('portValue', ''):
            llm_owned_order.append("Investments")
        if state.get('performance') is not None:        # Stage 2 manufacturing/swarm unlocked
            llm_owned_order.append("Swarm Computing")
        if state.get('colonized'):
            llm_owned_order.append("Probes")
        llm_action_by_domain = {}
        for i, label in enumerate(llm_display):
            if i < len(llm_owned_order):
                llm_action_by_domain[llm_owned_order[i]] = label

        domain_decisions = []
        for dom, stage in DOMAIN_REGISTRY:
            if not domain_is_active(dom, state):
                entry = {"action": "n/a", "status": None}
            elif dom in LLM_OWNED_DOMAINS:
                entry = {"action": llm_action_by_domain.get(dom, "—"), "status": None}
            elif dom in LLM_GRADED_DOMAINS:
                entry = {"action": "auto", "status": status_map.get(dom)}
            else:
                entry = {"action": "auto", "status": compute_stage2_grade(dom, state)}
            domain_decisions.append({"domain": dom, "stage": stage, **entry})

        # Update per-domain loop tracker and build warnings for the NEXT tick's prompt.
        # We track the last 5 actions per domain and warn when the last 3 are identical.
        for dd in domain_decisions:
            d = dd['domain']
            a = dd['action']
            # Only loop-check real LLM decisions — auto/n/a/placeholder are JS-handled or
            # inactive, so tracking them just spams the prompt with "Business: auto ×N".
            if a in ('auto', 'n/a', '—'):
                continue
            if d not in domain_loop_tracker:
                domain_loop_tracker[d] = []
            domain_loop_tracker[d].append(a)
            if len(domain_loop_tracker[d]) > 5:
                domain_loop_tracker[d].pop(0)

        warn_lines = []
        for d, actions in domain_loop_tracker.items():
            if len(actions) >= 3 and len(set(actions[-3:])) == 1:
                repeated = actions[-1]
                run = sum(1 for a in reversed(actions) if a == repeated)
                if repeated in ('wait', 'nothing'):
                    tip = "Is there a project that just became affordable? A probe stat to adjust? Or confirm 'nothing' is correct."
                else:
                    tip = f"Is '{repeated}' still the right call, or has the situation changed?"
                warn_lines.append(
                    f"  ⚠ {d}: '{repeated}' × {run} consecutive ticks. {tip}"
                )
        if warn_lines:
            domain_loop_warnings = (
                "\n⚠ LOOP ALERT — same decision repeated per domain:\n"
                + "\n".join(warn_lines)
                + "\nBreak out by checking what changed or confirming it's genuinely unchanged.\n\n"
            )
            print(f"[LOP] {'  |  '.join(warn_lines)}")
        else:
            domain_loop_warnings = ""

        primary_str = queue[0]['action'] if queue else "wait"
        history.append((thought, llm_str))
        post_action_queue(queue, domain_decisions=domain_decisions, overrides_str=ov_str)
        ov_label = "+".join(o['action'] for o in ov) if ov else None
        log_tick(tick, state, thought, primary_str, elapsed_ms, override=ov_label)

        time.sleep(LOOP_DELAY)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Agent stopped.")
