# ai-plays-as-ai-making-paperclips

> *An AI agent, driven by a local LLM, playing a game about an AI that makes paperclips.*

**Version 2.12.13 — last updated 6 June 2026.**

---

## 1. Summary

This is a local LLM playing [Universal Paperclips](https://www.decisionproblem.com/paperclips/index2.html) start to finish with no human touching the game UI. It has completed a full run: Stage 1 through Stage 3, 100% of the universe explored, stopping short of the endgame choice because that one belongs to the player.

The practical point is the architecture, not the game. The agent has no API, no game hooks, and no access to the source. It reads the DOM, injects clicks through a Tampermonkey userscript, and makes decisions in a ReAct loop against a model running on my own hardware. The same approach applies to any web tool that doesn't expose an interface, which is most of the ones I deal with day to day.

The absurdity is intentional. Universal Paperclips is a game about an AI that becomes so single-minded about manufacturing paperclips that it...

<details>

<summary>⚠️ Spoiler — the end goal</summary>

...converts all matter in the universe to serve that goal. It's a playable version of Nick Bostrom's paperclip maximizer, and a meditation on misaligned objectives. Every decision the LLM makes here is ultimately in service of that.

</details>

So this is an AI playing an AI making paperclips. Its entire existence is optimizing the conversion of matter into paperclips. I appreciate the joke more than I probably should.

---

## 2. Background

I'm a technical services director at an MSP with nearly three decades of building computers, then deploying and managing networks and servers, and eventually owning security decisions. Programming is the one thing I deliberately left alone — scripting and editing code when the job required it, nothing more.

That position stopped being sensible. Understanding use cases, terminology, risk vectors, supply chains, information disclosure surfaces, and data flows isn't optional for someone in this role anymore, and it can't be done from a distance. This project is one step in that direction: a hands-on, public experiment in what's actually achievable when IT experience is paired with an LLM coding assistant.

To be clear about what this is not: **it is not an endorsement of AI as a whole**, or of how governments and large corporations are deploying it, or of the environmental and social cost of the current build-out. It's an honest attempt to understand the technology, because understanding it is the only responsible position available to me.

The development was streamed live on Twitch, and all ad revenue from those streams goes to charity (section 15).

**Stream recordings:**
- [AFK Test Stream — Session 1](https://www.twitch.tv/videos/2779567062)
- [AFK Test Stream — Session 2](https://www.twitch.tv/videos/2779602441)
- [AFK Test Stream — Session 3](https://www.twitch.tv/videos/2780344614)

---

## 3. Current status

Honest position first: **the agent has completed a full game, and the current build has a known bug that stalls Stage 1.**

**What works.** As of v2.12.8 the agent played autonomously from Stage 1 through Stage 3 and colonized 100% of the universe, reaching the "Message from the Emperor of Drift" endgame. It is deliberately blocked from making the final Accept/Reject choice — that's irreversible and it's the player's call.

**What's broken.** The most recent long Stage-1 run (v2.12.13, ~3,815 ticks, stopped by me) ended with the agent toggling AutoTourney on and off on 1,171 consecutive ticks — roughly 39 minutes producing no Yomi and doing nothing else. Clip production and trust allocation kept working through it because those are rule-driven, but Yomi stalled. This is the first thing to fix next session; details and root-cause leads are in section 12 and in `CLAUDE.md`.

**Where the run stood when I stopped it:** clips 8.24B, memory 47 (climbing toward the 70-memory HypnoDrones wall), trust 71 fully allocated, portfolio value $112.9B, creativity 434k, Yomi stuck around 11.6k.

My assumption is that the AutoTourney flap is an edge-trigger problem rather than a design problem, but I haven't proven that yet.

---

## 4. How it works

```
Browser (Tampermonkey userscript)
  │  POST /state every 2s — pushes game state as JSON
  │  POST /result — reports whether each action succeeded or failed
  ▼
Flask Relay  (localhost:5000)
  │  GET / — live dashboard (auto-refreshes, no terminal needed)
  │  agent reads state via GET /state (includes last action result)
  ▼
Python ReAct Agent
  │  builds prompt with state + result feedback, queries local LLM
  │  writes one JSON record per tick to agent.log
  ▼
Ollama  (localhost:11434)
  │  returns Thought + Action
  ▼
Flask Relay
  │  browser polls GET /action (response includes thought for badge)
  ▼
Browser (userscript executes click, reports success/failure back)
```

The relay sits in the middle as a broker so the browser and the agent don't have to agree on timing. The browser pushes state on its own interval; the agent reads and writes independently. That decoupling has saved a lot of debugging.

### 4.1 Division of responsibility

Work is split between two layers so LLM inference time isn't spent on decisions that don't need judgment. Anything mechanical and repetitive belongs in the userscript. Anything involving a tradeoff belongs to the model.

**Userscript — fast, rule-based, roughly 20x per second:**
- Clicking Make Paperclip in the early game
- Buying wire, AutoClippers, and MegaClippers, preferring whichever is genuinely the better deal
- Price management and Marketing upgrades
- Spending ops, creativity, cash, and trust on projects via a priority queue
- Tournament strategy enforcement, and running tournaments when ops are near cap
- Stage 2 power and manufacturing — Solar Farms, Battery Towers, Harvester and Wire Drones, Clip Factories, built from the clip surplus with power kept at 100%
- Emergency wire recovery

**LLM agent — ReAct loop, every 2 seconds:**
- One decision per active game domain per tick: Projects, Investments (Stage 2), Swarm Computing (Stage 2), Probes (Stage 3)
- **Swarm Computing** is deliberately LLM-owned rather than automated in JavaScript. Swarm Gifts are the Stage 2 equivalent of Trust, and handing that to a rule would have taken the model out of the part of the game that matters most in that stage
- Phase transition awareness and project prioritization for edge cases
- An advisory `Status:` grade each tick on the domains the rules own, so there's visibility into the parts the model doesn't control
- Anything requiring a tradeoff

A handful of hard overrides fire before the model runs each tick — wire emergency, trust allocation, investments, AutoTourney. These exist because the failure modes they cover are unambiguous and expensive, not because I wanted to take decisions away from the model.

### 4.2 What you see while it runs

Terminal output is deliberately readable:

```
────────────────────────────────────────────────────────────
[14:22:01] TICK 47
────────────────────────────────────────────────────────────
[OBS]
  clips                  717,469,831
  unsoldClips            693,640,114  ↓ consider lower_price
  demand                 428%  ↑ consider raise_price
  funds                  $2,412,111.07
  wire                   137,419
  trust                  34  (fully allocated — none to spend)
  memory                 21  (ops cap: 21,000)
  processors             13
  operations             16,016 / 21,000
  yomi                   0
  portValue              $13,514,506
  investUpgradeCost      100
  autoTourneyOn          ON
  availableProjects      Full Monopoly (3,000 yomi, $10,000,000)

[FB ] Last: add_processor ✓


[14:22:01] Querying qwen2.5...
[THK] Monopoly needs 3,000 yomi — we have 0. Yomi is 0 so can't upgrade investment either. Need AutoTourney running to build yomi.
[OVR] add_memory
[ACT] nothing | nothing  (203ms)
```

`[ACT]` shows one entry per active domain — Projects first, then Investments, then Probes. `nothing` means the model considered that domain and had no action this tick, which is different from a failure. `[OVR]` is a hard override, and those always fire ahead of LLM actions.

Two other views, both easier than watching a terminal:
- **Live dashboard** at http://localhost:5000 while the relay is running — state, tick history, thoughts, action results, and per-domain health.
- **In-game badge**, bottom-right of the game page — phase, clip count, last action, and the model's current reasoning.

---

## 5. Requirements

| Tool | Purpose |
|------|---------|
| [Chrome](https://www.google.com/chrome/) | Run the game visibly |
| [Tampermonkey](https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo) | Inject the userscript into the game page |
| [Ollama](https://ollama.com/download/windows) | Run a local LLM |
| Python 3.10+ | Run the relay and agent |

`qwen2.5` is the recommended model — reasonable judgment, fast inference, and it fits comfortably in VRAM. On a capable GPU, `qwen3.6` reasons noticeably better at the cost of speed. Everything else in this repo is model-agnostic.

---

## 6. Setup

First-time setup, one action per step. Steps 1 to 4 are only needed once.

**1. Install the Tampermonkey extension.**
[Install from the Chrome Web Store](https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo).

**2. Install Ollama and pull the model.**
Run the [Ollama installer](https://ollama.com/download/windows), then:
```
ollama pull qwen2.5
```
Verify: `ollama run qwen2.5 "hello"` should return a response. If it doesn't, nothing downstream will work.

**3. Install the Python dependencies.**
```
py -m pip install flask requests
```

**4. Install the userscript.**
1. Tampermonkey → Dashboard → **+** tab
2. Delete the placeholder content
3. Paste the full contents of `bridge.user.js`
4. **Ctrl+S** to save

**5. Start the relay and agent.**

Option A — launcher (Windows):
```
.\start.ps1
```
Opens the relay in a new window, waits for it, then runs the agent in the current one. Note the display quirk in section 12.

Option B — manual, two terminals:
```
py relay.py      # terminal 1
py agent.py      # terminal 2
```

**6. Open the game.**
https://www.decisionproblem.com/paperclips/index2.html

Verify: a **🤖 Agent Active** badge appears bottom-right, and the agent terminal starts printing observations within a few seconds. No badge generally means Tampermonkey isn't enabled for the site.

### 6.1 Redeploy checklist — read this before changing `bridge.user.js`

This is the single most common way to lose an evening. **Restarting Python does not update the browser script.** Any change to `bridge.user.js` requires all four steps, in order:

1. Copy `bridge.user.js` into the Tampermonkey editor and save
2. Restart `relay.py`
3. Restart `agent.py`
4. Reload the game page in Chrome

Skipping step 1 produces symptoms that look like agent bugs — the classic one being Yomi stuck at 0 while everything else appears healthy.

---

## 7. Configuration

Common settings live in `config.json`. Edit and restart the agent — no Python changes needed.

| Setting | Default | Description |
|---------|---------|-------------|
| `model` | `qwen2.5` | Ollama model name |
| `loop_delay` | `2.0` | Seconds between agent ticks |
| `max_history` | `6` | Past decisions included in each prompt |
| `log_file` | `agent.log` | JSON-lines tick log path (gitignored) |
| `memory_milestones` | `[20, 70, 120, 175, 250, 300]` | Memory walls the agent rushes toward (memory × 1000 = ops ceiling); taken from the game wiki |
| `trust_proc_floor` | `5` | Minimum processors kept for ops regen before pouring trust into memory |
| `probe_*_target` | see file | Stage 3 probe-design allocation targets (hazard, replication, speed, exploration, combat) |
| `entertain_creativity_floor` | `450000` | Creativity kept in reserve before spending on "Entertain the Swarm" |

Browser-side constants sit at the top of `bridge.user.js`. These are early-Stage-2 defaults; the build targets need raising for the Stage 2 endgame.

| Setting | Default | Description |
|---------|---------|-------------|
| `STATE_MS` | `2000` | How often state is pushed to the relay (ms) |
| `ACTION_MS` | `500` | How often the browser polls for actions (ms) |
| `STAGE2_MS` | `800` | How often the Stage 2 power/manufacturing builder acts (ms) |
| `POWER_MARGIN` | `1.10` | Keep power production ≥ consumption × this |
| `SOLAR_MIN` / `BATTERY_MIN` | `30` / `20` | Baseline solar farms / battery towers built early |
| `DRONE_TARGET` / `DRONE_RATIO` | `500` / `1.618` | Total drones, and the wire ÷ harvester golden ratio |
| `FACTORY_TARGET` | `10` | Clip factories to build |

---

## 8. Design decisions

A few choices that are worth understanding before changing anything:

1. **No persistent memory.** The agent uses a rolling window of recent decisions as context. Every tick is a fresh LLM call with current state plus history. This is stateless by design and I'd like to keep it that way — it makes behaviour reproducible and keeps the prompt honest.
2. **ReAct pattern.** Every response is `Thought:` followed by `Action:`. The parser depends on that exact structure, so it shouldn't be changed casually. It also means the reasoning is visible and loggable, which is most of the value.
3. **Rules where rules belong.** If a decision has one correct answer, it goes in the userscript. Sending it to the model costs two seconds and adds a chance of being wrong.
4. **Everything the model emits is validated.** Hallucinated or unaffordable actions are substituted with `wait` rather than sent to the browser. Early versions taught me why.
5. **The game's own affordability gates do the accounting.** Build buttons are disabled when unaffordable, so the fast rules are gated on button state rather than trying to track costs independently. This self-paces against exponential pricing.

---

## 9. File overview

| File | Purpose |
|------|---------|
| `relay.py` | Flask HTTP bridge — state, action, and result endpoints, plus the live dashboard |
| `agent.py` | ReAct loop, LLM calls, hard overrides, strategic decision logic |
| `bridge.user.js` | Tampermonkey userscript — state extraction, action execution, result reporting |
| `config.json` | Tunable settings — edit here instead of the Python files |
| `start.ps1` | One-click launcher for Windows |
| `agent.log` | JSON-lines tick log written by the agent (gitignored) |
| `CHANGELOG.md` | Per-version detail |
| `CLAUDE.md` | Working notes, DOM reference, and known-issue detail |

---

## 10. Tested on

- Windows 11, Chrome, Tampermonkey
- Python 3.14
- Ollama with `qwen2.5` (4.7GB) and `qwen3.6` (23GB)
- RTX 3090, 24GB VRAM

Nothing here should be Windows-specific apart from `start.ps1`, but I haven't tested elsewhere and wouldn't claim it works until someone has.

---

## 11. Assumptions and out of scope

Stated plainly so nobody has to infer them:

**Assumptions**
- The game is played at the official URL in a visible Chrome window. Headless operation hasn't been tested.
- The game's DOM element IDs are stable. They are the entire interface, so a change on the game's side would break the bridge.
- Ollama is reachable on `localhost:11434` and the relay on `localhost:5000`.
- One agent, one browser tab, one game at a time.

**Out of scope**
- Modifying, patching, or reverse-engineering the game. DOM observation and click injection only.
- Save-file manipulation or anything that would amount to cheating.
- Triggering the endgame Accept/Reject choice. That's blocked deliberately and I intend to keep it that way.
- Hosted or multi-user operation. This runs on one machine, locally.
- Any claim that this is a general-purpose game-playing agent. It isn't — it's one game, played through a documented DOM.

---

## 12. Known issues and limitations

**Active — high priority**

- **AutoTourney override flaps every tick.** In the last long Stage-1 run the agent issued the `toggle_auto_tourney` override on 1,171 consecutive ticks (about 39 minutes) and did nothing else, so no Yomi accumulated. The logic that pauses AutoTourney while a claimable project is waiting for ops gets stuck: live state reports AutoTourney `ON` and "ops project waiting" `True` on the same tick, so the override re-issues the toggle indefinitely. My current assumption is that either the toggle isn't sticking or the waiting-project check is permanently true because of a revealed-but-unbuyable project, but I haven't confirmed which. This is the next fix. See `CLAUDE.md` for the full root-cause notes.

**Active — low priority**

- **The model can sit in a `wait` loop quoting a stale, wrong-stage thought.** In Stage 1, qwen2.5 sometimes re-anchors on a Stage-2 thought from its rolling history and emits `wait` for many ticks. It isn't harmful — Stage 1 is rule-driven, so clippers, projects, and trust allocation keep progressing regardless — but it's untidy. Likely fixes are a tighter Stage-1 prompt, clearing history sooner, or moving to a larger model. Documented rather than fixed, for now.
- **Xavier Re-initialization appears twice** in the project list. Game quirk or selector issue, no impact.
- **`start.ps1` display quirk** — relay and agent can end up sharing a terminal window. The manual two-terminal start is the reliable alternative.

**General limitations**

- Stage 3 probe design is driven by a deterministic advisor reading wiki-verified targets. The model still emits every action, but the strategic guidance is prescriptive rather than discovered. That was a practical concession to running a small local model, not a preference.
- Invalid actions from the model are caught and substituted with `wait`, so they cost a tick.
- If Ollama is slow to respond, the agent falls back to `wait` for that tick.

Per-version fix history — and there's a lot of it — is in `CHANGELOG.md`.

---

## 13. Version history

Full detail for every version is in `CHANGELOG.md`. The milestones worth knowing about:

| Version | What changed |
|---------|--------------|
| **v2.12.13** *(current)* | Auto-buy cash-cost and philanthropy +Trust projects. Trust is the Stage-1 bottleneck and the cost parser didn't understand `$` costs, so millions in cash sat idle while +Trust projects went unclaimed. |
| **v2.12.9 – .12** | Fresh-game stage misdetection, AutoClipper/MegaClipper cost-crossover guard, tournament hold while a project is claimable, and a Stage-1 yomi-reserve deadlock. |
| **v2.12.8** | 🎉 **First complete run — 100% of the universe explored.** Stage 1 → 2 → 3 → endgame. The agent is now blocked from triggering the irreversible finale. |
| **v2.12 – .7** | The Stage 3 arc. Unstuck the bootstrap stall with stage-aware inputs and a deterministic probe-design advisor, then worked through survival (hazard, combat reserve, honor projects, bored-swarm recovery) to colonization via Speed × Exploration. |
| **v2.11** | Reached Stage 3. Space Exploration launched and the Von Neumann probe actions wired up. |
| **v2.10.x** | Stage 2 endgame scaling — factories to 200, drones to 50k, batched battery storage toward the 10M MW-sec gate. |
| **v2.9** | Swarm Computing handed to the LLM rather than a JS override, in line with keeping the model central to the game. |
| **v2.8** | Dashboard overhaul — decisions grouped into three stage sections with per-domain health badges. |
| **v2.7** | Built the Stage 2 power and manufacturing engine, a whole domain the agent had been blind to. |
| **v2.6** | Unblocked Stage 2. A single misspelled project name (`Tubulue` for `Tubule`) had frozen the entire manufacturing chain. |
| **v2.5** | Trust allocation rebuilt around the game's real memory walls, clearing the processor over-allocation that stalled progress at HypnoDrones. |
| **v2.4** | LLM domain grading via an advisory `Status:` line, plus the AutoClipper cost-crossover fix. |
| **v2.3** | Production starvation fixed, honest dashboard coverage for all 8 domains, Stage 2 project queue. |
| **v2.2** | Tournament system fully working after a three-part bug hunt. Yomi flowing, investment engine self-upgrading. |
| **v2.0** | Parallel override architecture, per-domain LLM output, multi-action queue, marketing fixed. |
| **v1.9** | Action feedback loop, live dashboard, Stage 2/3 wiring, `config.json`, `start.ps1`. |
| **v1.0 – v1.8** | v1.0 produced zero paperclips — the model hallucinated every action. Progressive fixes from there: wire bankruptcy recovery, trust allocation, project priority queue, MegaClipper automation. |

---

## 14. Where this goes next

The immediate priority is the AutoTourney flap in section 12. Nothing else should start until Stage 1 runs clean again.

After that, in the order I'd tackle them:

1. **LLM parameter hints.** The `Status:` line already reserves a colon separator (`Manufacturing=warn:wire_threshold=200`) for the model to suggest a parameter change alongside a grade. Parsing that hint and passing it to the userscript as a tunable turns grading from observation into gentle control. Requires a `bridge.user.js` change and a redeploy.
2. **Expand the LLM to all seven domains.** Grow the system prompt so the model emits an `Action:` line for every Stage 2 domain, not just Projects, Investments, Swarm, and Probes. Needs `num_predict` raised from 500 to 700+, and qwen2.5 compliance tested before it's enabled.
3. **A generic +Trust auto-buy rule.** Right now new +Trust projects have to be added to the priority list by name. That's been whack-a-mole three times, which is two times more than it should have been.
4. **Multi-model competition.** Run two local models against the same game and compare. Mostly curiosity, but it's the cleanest way to find out how much of the current behaviour is the architecture and how much is qwen2.5.
5. **`start.ps1` display fix.** Minor, and it has been minor for a while.

---

## 15. Credits and acknowledgements

### Universal Paperclips

This project exists because of a genuinely great game. **Universal Paperclips** was designed by [Frank Lantz](http://www.franklantz.net/) and programmed by Frank Lantz and [Bennett Foddy](https://en.wikipedia.org/wiki/Bennett_Foddy), released in 2017 by [Everybody House Games](http://www.franklantz.net/universal-paperclips/). It's a playable version of Nick Bostrom's paperclip maximizer thought experiment and an all-time classic of the incremental genre.

Play it here: **https://www.decisionproblem.com/paperclips/index2.html**

### Open source stack

| Project | Role | License |
|---------|------|---------|
| [Ollama](https://github.com/ollama/ollama) | Local LLM inference server | MIT |
| [Qwen 2.5](https://github.com/QwenLM/Qwen2.5) (Alibaba / Qwen Team) | Language model used for agent reasoning | Apache 2.0 |
| [Flask](https://github.com/pallets/flask) | Python HTTP relay server | BSD-3-Clause |
| [Tampermonkey](https://www.tampermonkey.net/) | Browser userscript manager | Proprietary (free) |
| [Python](https://www.python.org/) | Agent runtime | PSF License |
| [Requests](https://github.com/psf/requests) | HTTP client library | Apache 2.0 |
| [Anthropic Claude](https://claude.ai) | AI coding assistant used to build this project | — |

### Concept lineage

The paperclip maximizer was first described by **Nick Bostrom** in 2003 and expanded in *Superintelligence* (2014).

The **ReAct** pattern (Reason + Act) used by the agent comes from:
> Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models*, ICLR 2023.
> https://arxiv.org/abs/2210.03629

---

## 16. Attribution

I built this through iterative prompting and feedback using [Claude](https://claude.ai) as the coding assistant. I directed the vision, found the bugs, tested every version live, and made every decision about what the agent should do. Claude wrote the code.

That distinction matters, and I'd rather state it plainly than let anyone assume otherwise. If you're wondering whether a non-coder can build something like this through LLM collaboration alone — yes, and the bug list in section 12 is a fair picture of what that actually looks like.

---

## 17. Charity

The Twitch streams associated with this project donate 100% of ad revenue to charity. The current round benefits **[Breakthrough T1D](https://www.breakthrought1d.org/)**, a global organization funding type 1 diabetes research and advocacy.

Current round: **$1,730 raised of a $2,000 goal.**

If you'd like to contribute, you can do so via the [TechLuddite Twitch page](https://www.twitch.tv/techluddite).

---

## 18. Why?

Because someone had to find out whether a local LLM could play a game about a misaligned AI making paperclips, with no API and no coding background on my side.

It can. Not elegantly at first — v1.0 produced zero paperclips, early versions bankrupted themselves repeatedly, and at one point the agent accumulated negative trust in ways I didn't know were possible in this game. The current build has run the whole game start to finish without a human touching the UI, and it still has a bug that makes it toggle a button at itself for 39 minutes.

Both of those are true at once. That's roughly where the technology is.

---

## License

MIT — see [LICENSE](LICENSE).
