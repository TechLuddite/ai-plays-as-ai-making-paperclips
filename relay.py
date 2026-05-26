"""
relay.py — Universal Paperclips local bridge
Sits between the Tampermonkey userscript (browser) and the ReAct agent.

Endpoints:
  POST /state   — browser posts current game state JSON
  GET  /action  — agent reads latest state, returns next action
  POST /action  — agent posts the decided action for the browser to execute
"""

from flask import Flask, request, jsonify
from datetime import datetime
import threading

app = Flask(__name__)

# Shared state between browser and agent
latest_state = {}
pending_action = None
state_lock = threading.Lock()
action_lock = threading.Lock()

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[RELAY {ts}] {msg}")

# ── Browser → Relay ──────────────────────────────────────────────────────────

@app.route("/state", methods=["POST"])
def receive_state():
    global latest_state
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "no JSON"}), 400
    with state_lock:
        latest_state = data
    return jsonify({"ok": True})

# ── Agent → Relay (read state) ───────────────────────────────────────────────

@app.route("/state", methods=["GET"])
def get_state():
    with state_lock:
        return jsonify(latest_state)

# ── Agent → Relay (post action) ──────────────────────────────────────────────

@app.route("/action", methods=["POST"])
def receive_action():
    global pending_action
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "no JSON"}), 400
    with action_lock:
        pending_action = data
    log(f"Action queued: {data.get('action')} | args: {data.get('args', {})}")
    return jsonify({"ok": True})

# ── Browser → Relay (poll for action) ────────────────────────────────────────

@app.route("/action", methods=["GET"])
def send_action():
    global pending_action
    with action_lock:
        action = pending_action
        pending_action = None  # consume it
    if action:
        return jsonify(action)
    return jsonify({"action": "wait"})

if __name__ == "__main__":
    log("Relay starting on http://localhost:5000")
    log("Waiting for browser and agent to connect...")
    app.run(host="localhost", port=5000, debug=False)
