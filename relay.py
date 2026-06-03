"""
relay.py — Universal Paperclips local bridge v2.0
Sits between the Tampermonkey userscript (browser) and the ReAct agent.

Endpoints:
  POST /state     — browser posts current game state JSON
  GET  /state     — agent reads latest state (includes last action result)
  POST /action    — agent posts decided action (with optional 'thought' field)
  GET  /action    — browser polls for next action to execute
  POST /result    — browser reports whether the last action succeeded
  GET  /history   — last 50 tick records as JSON
  GET  /           — live HTML dashboard (auto-refreshes every 2s)
  GET  /dashboard — same as above
"""

from flask import Flask, request, jsonify, Response
from datetime import datetime
import threading

app = Flask(__name__)

# ── Shared state ──────────────────────────────────────────────────────────────

latest_state         = {}
action_queue         = []    # FIFO queue of action dicts; browser dequeues one per poll
last_result          = {}
tick_history         = []    # list of dicts, capped at HISTORY_MAX
last_decisions_history = []   # rolling list of last 3 tick entries, newest last

HISTORY_MAX = 50

state_lock     = threading.Lock()
action_lock    = threading.Lock()
result_lock    = threading.Lock()
history_lock   = threading.Lock()
decisions_lock = threading.Lock()

_tick_counter = 0

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[RELAY {ts}] {msg}")

def _push_history(entry):
    """Append a new tick record; trim to HISTORY_MAX."""
    global tick_history, _tick_counter
    _tick_counter += 1
    entry['tick'] = _tick_counter
    with history_lock:
        tick_history.append(entry)
        if len(tick_history) > HISTORY_MAX:
            tick_history.pop(0)

def _update_last_result(success, note):
    """Patch the most recent history entry with the action result."""
    with history_lock:
        if tick_history:
            tick_history[-1]['result_success'] = success
            tick_history[-1]['result_note']    = note

# ── Browser → Relay (state push) ─────────────────────────────────────────────

@app.route("/state", methods=["POST"])
def receive_state():
    global latest_state
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "no JSON"}), 400
    with state_lock:
        latest_state = data
    return jsonify({"ok": True})

# ── Agent → Relay (state read) ────────────────────────────────────────────────

@app.route("/state", methods=["GET"])
def get_state():
    with state_lock:
        data = dict(latest_state)
    with result_lock:
        data['_lastResult'] = dict(last_result)
    with decisions_lock:
        data['_decisions_history'] = list(last_decisions_history)
    return jsonify(data)

# ── Agent → Relay (action post) ───────────────────────────────────────────────

@app.route("/action", methods=["POST"])
def receive_action():
    global action_queue
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "no JSON"}), 400

    # Accept {"queue": [...]} for multi-action or the old single-action dict format.
    if 'queue' in data:
        items = data['queue']
    else:
        items = [data]

    with action_lock:
        action_queue.extend(items)

    # Extract per-domain decisions and overrides sent by agent.py for the dashboard
    domain_decisions = data.get('domain_decisions', [])
    overrides_str    = data.get('overrides', '')
    with decisions_lock:
        last_decisions_history.append({"domain_decisions": domain_decisions,
                                       "overrides": overrides_str})
        if len(last_decisions_history) > 3:
            last_decisions_history.pop(0)

    # Log and record the primary (first) action only
    primary = items[0] if items else {}
    action  = primary.get('action', '')
    args    = primary.get('args', {})
    thought = primary.get('thought', '') or data.get('thought', '')
    short   = (thought[:60] + '…') if len(thought) > 60 else thought
    extra   = f" +{len(items)-1} queued" if len(items) > 1 else ""
    log(f"Action: {action}{extra} | {short}")

    with state_lock:
        phase = latest_state.get('phase')
        clips = latest_state.get('clips')

    _push_history({
        'ts':              datetime.now().strftime("%H:%M:%S"),
        'phase':           phase,
        'clips':           clips,
        'thought':         thought,
        'action':          action + (f" (+{len(items)-1})" if len(items) > 1 else ""),
        'args':            args,
        'domain_decisions': domain_decisions,
        'overrides':       overrides_str,
        'result_success':  None,
        'result_note':     '',
    })
    return jsonify({"ok": True})

# ── Browser → Relay (action poll) ────────────────────────────────────────────

@app.route("/action", methods=["GET"])
def send_action():
    global action_queue
    with action_lock:
        if action_queue:
            return jsonify(action_queue.pop(0))   # dequeue oldest first
    return jsonify({"action": "wait"})

# ── Browser → Relay (result feedback) ────────────────────────────────────────

@app.route("/result", methods=["POST"])
def receive_result():
    global last_result
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "no JSON"}), 400
    with result_lock:
        last_result = data

    success = data.get('success')
    note    = data.get('note', '')
    icon    = '✓' if success else '✗'
    log(f"Result: {data.get('action', '?')} {icon}" + (f" — {note}" if note else ""))

    _update_last_result(success, note)
    return jsonify({"ok": True})

# ── Agent / Observer (history) ────────────────────────────────────────────────

@app.route("/history", methods=["GET"])
def get_history():
    with history_lock:
        return jsonify(list(tick_history))

# ── Dashboard HTML ────────────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Paperclips Agent</title>
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#0d1117; color:#c9d1d9; font-family:monospace; padding:20px; }
  h1   { color:#58a6ff; font-size:20px; margin-bottom:3px; }
  .sub { color:#8b949e; font-size:12px; margin-bottom:20px; }
  a    { color:#58a6ff; }
  .card { background:#161b22; border:1px solid #30363d; border-radius:6px;
          padding:16px; margin-bottom:16px; }
  .card h2 { color:#58a6ff; font-size:12px; letter-spacing:1px;
             text-transform:uppercase; margin-bottom:12px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:8px; }
  .kv   { background:#0d1117; border-radius:4px; padding:8px 10px; }
  .kv .k { color:#8b949e; font-size:10px; text-transform:uppercase; letter-spacing:.5px; }
  .kv .v { color:#e6edf3; font-size:14px; font-weight:bold; margin-top:2px; }
  .warn { color:#f85149 !important; }
  .ok   { color:#3fb950 !important; }
  .dim  { color:#8b949e !important; }
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th { color:#8b949e; text-align:left; padding:4px 8px; border-bottom:1px solid #30363d;
       font-size:10px; text-transform:uppercase; letter-spacing:.5px; }
  td { padding:5px 8px; border-bottom:1px solid #21262d; vertical-align:top; }
  .thought { color:#8b949e; font-size:11px; }
  #dot { display:inline-block; width:8px; height:8px; border-radius:50%;
         background:#3fb950; margin-right:6px; vertical-align:middle; }
</style>
</head>
<body>
<h1><span id="dot"></span>Paperclips Agent</h1>
<p class="sub">Live — updates every 2s &nbsp;|&nbsp; <a href="/history">raw JSON</a></p>

<div class="card">
  <h2>Live State</h2>
  <div class="grid" id="metrics">Connecting…</div>
</div>

<div class="card">
  <h2>LLM Decisions</h2>
  <div id="decisions-wrap"><span class="dim">No decisions yet</span></div>
</div>

<div class="card">
  <h2>Tick History</h2>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Time</th><th>Ph</th><th>Clips</th>
        <th>Action</th><th>Result</th><th>Thought</th>
      </tr>
    </thead>
    <tbody id="hist"></tbody>
  </table>
</div>

<script>
const KEYS = [
  'phase','clips','unsoldClips','clipRate','clipPrice','demand',
  'funds','wire','wireBuyerOn',
  'autoclippers','megaclippers','marketing',
  'trust','memory','processors','operations','creativity',
  'portValue','investMode'
];

function warnClass(k, v) {
  const n = parseFloat(v);
  if (k === 'wire'  && !isNaN(n) && n < 100)  return 'warn';
  if (k === 'funds' && !isNaN(n) && n < 2)    return 'warn';
  if (k === 'wireBuyerOn' && v === false)       return 'warn';
  return '';
}

async function refresh() {
  try {
    const [state, hist] = await Promise.all([
      fetch('/state').then(r => r.json()),
      fetch('/history').then(r => r.json())
    ]);

    // Metrics grid
    const lr    = state._lastResult || {};
    const cards = KEYS.filter(k => state[k] != null).map(k =>
      `<div class="kv">
         <div class="k">${k}</div>
         <div class="v ${warnClass(k, state[k])}">${state[k]}</div>
       </div>`
    ).join('');
    const resultCard = lr.action
      ? `<div class="kv">
           <div class="k">last result</div>
           <div class="v ${lr.success ? 'ok' : 'warn'}">
             ${lr.action} ${lr.success ? '✓' : '✗'}${lr.note ? ' — ' + lr.note : ''}
           </div>
         </div>`
      : '';
    document.getElementById('metrics').innerHTML = cards + resultCard;

    // LLM Decisions — static 8-domain table, last 3 ticks
    const DEC_LABELS = ['Business','Manufacturing','Comp Resources','Quantum Computing',
                        'Projects','Investments','Strat Modeling','Probes'];
    const DEC_KEYS   = ['Business','Manufacturing','Computational Resources','Quantum Computing',
                        'Projects','Investments','Strategic Modeling','Probes'];
    const decHist = (state._decisions_history || []).slice().reverse(); // newest first
    const AGE_LBL = ['latest', '−1', '−2'];
    if (decHist.length) {
      let hdr = '<tr><th style="text-align:left;min-width:54px"></th>';
      DEC_LABELS.forEach(n => {
        hdr += `<th style="text-align:center;padding:4px 6px">${n}</th>`;
      });
      hdr += '</tr>';
      let rows = '';
      for (let i = 0; i < 3; i++) {
        const entry   = decHist[i];
        const opacity = i === 0 ? '1' : i === 1 ? '0.6' : '0.35';
        rows += `<tr style="opacity:${opacity}">`;
        rows += `<td style="color:#8b949e;font-size:10px;padding:4px 6px;white-space:nowrap">${AGE_LBL[i]}</td>`;
        DEC_KEYS.forEach(key => {
          if (!entry) {
            rows += `<td style="text-align:center;color:#30363d;padding:3px 5px">—</td>`;
          } else {
            const dec = (entry.domain_decisions || []).find(d => d.domain === key);
            if (!dec) {
              rows += `<td style="text-align:center;color:#f85149;font-size:11px;padding:3px 5px">LLM Failed</td>`;
            } else if (dec.action === 'n/a') {
              rows += `<td style="text-align:center;color:#30363d;font-size:11px;padding:3px 5px">n/a</td>`;
            } else if (dec.action === 'auto') {
              // "auto" = fast rules own this domain. The LLM's advisory health grade
              // (dec.status) shows as a small colored dot: dim green=healthy,
              // amber=warn, red=critical. A red dot differs from "LLM Failed" red
              // text — the dot means the JS is running but the LLM flags a concern.
              // No status → no dot, just the dim gray "auto" as before.
              const DOT = {healthy:'#2ea043', warn:'#d29922', critical:'#f85149'};
              const dc  = DOT[dec.status];
              const dot = dc
                ? `<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${dc};margin-right:5px;vertical-align:middle"></span>`
                : '';
              rows += `<td style="text-align:center;color:#484f58;font-size:11px;padding:3px 5px">${dot}auto</td>`;
            } else {
              const isAct = dec.action !== 'nothing' && dec.action !== 'wait';
              const col   = isAct ? '#3fb950' : '#8b949e';
              const wt    = isAct ? 'bold' : 'normal';
              rows += `<td style="text-align:center;color:${col};font-weight:${wt};padding:3px 5px">${dec.action}</td>`;
            }
          }
        });
        rows += '</tr>';
      }
      const latestOvr = (decHist[0] && decHist[0].overrides || '').trim();
      if (latestOvr) {
        rows += `<tr><td style="color:#8b949e;font-size:10px;padding:4px 6px;white-space:nowrap">overrides</td>`;
        rows += `<td colspan="${DEC_KEYS.length}" style="color:#f85149;padding:4px 6px">${latestOvr}</td></tr>`;
      }
      document.getElementById('decisions-wrap').innerHTML =
        `<table style="width:100%;border-collapse:collapse;font-size:12px">${hdr}${rows}</table>`;
    } else {
      document.getElementById('decisions-wrap').innerHTML = '<span class="dim">No decisions yet</span>';
    }

    // History table (newest first)
    document.getElementById('hist').innerHTML = [...hist].reverse().map(h =>
      `<tr>
         <td class="dim">${h.tick}</td>
         <td class="dim">${h.ts || ''}</td>
         <td>${h.phase || '?'}</td>
         <td>${h.clips || ''}</td>
         <td style="color:${h.result_success === true ? '#3fb950' : h.result_success === false ? '#f85149' : '#c9d1d9'}">
           ${h.action || 'wait'}${h.args && h.args.name ? ': ' + h.args.name : ''}
         </td>
         <td>${h.result_success === true ? '✓' : h.result_success === false ? '✗' : '—'}
             ${h.result_note ? ' ' + h.result_note : ''}</td>
         <td class="thought">${(h.thought || '').substring(0, 90)}</td>
       </tr>`
    ).join('');

    document.getElementById('dot').style.background = '#3fb950';
  } catch (e) {
    document.getElementById('dot').style.background = '#f85149';
  }
}

refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>"""

@app.route("/")
@app.route("/dashboard")
def dashboard():
    return Response(DASHBOARD_HTML, mimetype="text/html")

# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log("Relay starting on http://localhost:5000")
    log("Dashboard  → http://localhost:5000")
    log("History    → http://localhost:5000/history")
    log("Waiting for browser and agent to connect…")
    app.run(host="localhost", port=5000, debug=False)
