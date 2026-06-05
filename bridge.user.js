// ==UserScript==
// @name         Universal Paperclips — ReAct Agent Bridge
// @namespace    http://localhost/
// @version      2.0
// @description  Reads game state and executes agent actions via local relay
// @author       paperclips-agent
// @match        https://www.decisionproblem.com/paperclips/*
// @match        http://www.decisionproblem.com/paperclips/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// ==/UserScript==

(function () {
    'use strict';

    const RELAY     = 'http://localhost:5000';
    const STATE_MS  = 2000;
    const ACTION_MS = 500;

    // ── Stage 2 manufacturing / power tuning (edit to change build behavior) ─────
    // Stage 2 is a power-management game: drones (1 MW each) and factories (200 MW each)
    // CONSUME power; solar farms (+50 MW each) PRODUCE it. Everything is paid in CLIPS,
    // and the game disables each build button when you can't afford it — so the builder
    // just works toward these targets as clips allow, always keeping power ahead of
    // consumption (the wiki warns: stay at 100% power or production stalls).
    // Raise these later for the Stage 2 endgame (the wiki's "Quickening": ~200 factories,
    // hundreds of thousands of drones, 10M MW-seconds of storage for Space Exploration).
    const STAGE2_MS      = 800;    // how often the Stage 2 builder acts (ms)
    const POWER_MARGIN   = 1.10;   // keep power production >= consumption × this
    const SOLAR_MIN      = 5;      // cold-start baseline solar farms (cost grows STEEPLY —
                                   //   ~32B clips for the 8th — so keep the baseline small and
                                   //   let production-funded deficit-provisioning scale it up)
    const BATTERY_TARGET_MW = 10000000;  // build battery storage up to this many MW-seconds —
                                   //   Space Exploration's power requirement (the last Stage 2
                                   //   gate). Built last (after consumers), using +100/+10 buttons.
    const DRONE_TARGET   = 50000;  // total drones — ENDGAME scale (v2.10). The old 500 capped
                                   //   wire throughput and stalled clip production far below the
                                   //   5 octillion Space Exploration needs. Self-paced by clip
                                   //   affordability (!btn.disabled), so it only builds what it
                                   //   can afford; raise/lower to taste.
    const DRONE_RATIO    = 1.45;   // wire drones ÷ harvester drones. The wiki's "golden ratio"
                                   // 1.618 is the PRODUCTION ideal but it EXCEEDS the swarm's
                                   // 1.5× imbalance limit → "Disorganized" (halts gifts, costs
                                   // 5k yomi to Synchronize). Stay safely under 1.5 to avoid it.
    const FACTORY_TARGET = 200;    // clip factories — ENDGAME scale (v2.10; wiki: "you'll need a
                                   //   lot of factories (~200)"). 10 was an early-game cap that
                                   //   plateaued production. Self-paced by clip affordability.

    // ── Helpers ───────────────────────────────────────────────────────────────

    function getText(id) {
        const el = document.getElementById(id);
        return el ? el.innerText.trim() : null;
    }

    function getNum(id, fallback = 0) {
        const raw = getText(id);
        if (!raw) return fallback;
        const n = parseFloat(raw.replace(/[^0-9.]/g, ''));
        return isNaN(n) ? fallback : n;
    }

    // Parse a big number that may use a word suffix, e.g. "1 sextillion", "47.1 sextillion",
    // "100 million", "1,000". The game shows clip costs/totals this way (clips reach octillions).
    const NUM_SCALE = {
        thousand: 1e3, million: 1e6, billion: 1e9, trillion: 1e12, quadrillion: 1e15,
        quintillion: 1e18, sextillion: 1e21, septillion: 1e24, octillion: 1e27,
        nonillion: 1e30, decillion: 1e33,
    };
    function parseBigNum(text) {
        if (!text) return 0;
        const m = String(text).match(/([\d,.]+)\s*([a-zA-Z]+)?/);
        if (!m) return 0;
        const num = parseFloat(m[1].replace(/,/g, ''));
        if (isNaN(num)) return 0;
        const scale = m[2] ? (NUM_SCALE[m[2].toLowerCase()] || 1) : 1;
        return num * scale;
    }

    function isVisible(id) {
        const el = document.getElementById(id);
        return el && el.offsetParent !== null;
    }

    function clickBtn(id) {
        const el = document.getElementById(id);
        if (el && el.offsetParent !== null) { el.click(); return true; }
        return false;
    }

    // Set the Stage 2 Work/Think slider (#slider, range 0–200). Fires both 'input' and
    // 'change' so the game registers the programmatic move (same pattern as the selects).
    function setSwarmSlider(value) {
        const el = document.getElementById('slider');
        if (!el) return false;
        el.value = value;
        el.dispatchEvent(new Event('input',  { bubbles: true, cancelable: true }));
        el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
        return true;
    }

    // ── Wire detection ────────────────────────────────────────────────────────
    // Phase 1: wire is in span#wire (inside manufacturingDiv)
    // Phase 3: wire is in span#nanoWire (wire drone production)

    function getWire() {
        const nano = getNum('nanoWire', -1);
        if (nano >= 0 && isVisible('wireProductionDiv')) return nano;
        return getNum('wire', 0);
    }

    function wireBuyerActive() {
        const status = getText('wireBuyerStatus');
        return isVisible('wireBuyerDiv') && status === 'ON';
    }

    // ── Investment state ──────────────────────────────────────────────────────
    // Appears in Phase 2 after Algorithmic Trading is purchased.
    // The investmentEngine div contains:
    //   - #investStrat select (low/med/hi)
    //   - #btnInvest (Deposit), #btnWithdraw
    //   - #portValue (total = bankroll + stocks)
    //   - #investmentBankroll (cash in account)
    //   - #secValue (stocks value)
    //   - #investmentLevel, #investUpgradeCost (Yomi cost to upgrade)

    function getInvestmentState() {
        if (!isVisible('investmentEngine')) return {};
        const stratEl = document.getElementById('investStrat');
        return {
            portValue:         getText('portValue'),
            investBankroll:    getText('investmentBankroll'),
            investStocks:      getText('secValue'),
            investLevel:       getText('investmentLevel'),
            investStrategy:    stratEl ? stratEl.value : null,
            investUpgradeCost: getText('investUpgradeCost'),
        };
    }

    // ── Phase 3 state ─────────────────────────────────────────────────────────
    // Probe design and space exploration metrics.
    // Probe trust budget is split across 8 stats (Speed, Nav, Rep, Haz, Fac, Harv, Wire, Combat).

    function getPhase3State() {
        if (!isVisible('spaceDiv')) return {};
        return {
            colonized:      getText('colonizedDisplay'),
            probeTotal:     getText('probesTotalDisplay'),
            probesLaunched: getText('probesLaunchedDisplay'),   // probes launched manually
            probesBorn:     getText('probesBornDisplay'),       // self-replicated descendents
            probeCost:      getText('probeCostDisplay'),        // clips per launched probe
            // Probe Trust: allocate `available` (= total − used) points across the 8 stats.
            probeTrust:     getText('probeTrustUsedDisplay') + '/' + getText('probeTrustDisplay'),
            probeTrustUsed: getText('probeTrustUsedDisplay'),
            probeTrustTotal: getText('probeTrustDisplay'),
            maxTrust:       getText('maxTrustDisplay'),         // cap on total probe trust
            probeTrustCost: getText('probeTrustCostDisplay'),   // yomi for +1 probe trust
            maxTrustCost:   getText('maxTrustCostDisplay'),     // honor to raise the cap
            honor:          getText('honorDisplay'),
            drifters:       getText('drifterCount'),
            driftersKilled: getText('driftersKilled'),
            probeSpeed:     getText('probeSpeedDisplay'),
            probeNav:       getText('probeNavDisplay'),
            probeRep:       getText('probeRepDisplay'),
            probeHaz:       getText('probeHazDisplay'),
            probeFac:       getText('probeFacDisplay'),
            probeHarv:      getText('probeHarvDisplay'),
            probeWire:      getText('probeWireDisplay'),
            probeCombat:    getText('probeCombatDisplay'),
            performance:    getText('performance'),
        };
    }

    // ── Stage 2 state (Power + Manufacturing) ──────────────────────────────────
    // Appears once Power Grid / the manufacturing projects unlock (powerDiv / factoryDiv
    // visible). Drones harvest matter → wire → clips, all powered by Solar Farms.
    // Everything here is paid in clips. Returns {} until the domain unlocks.

    function getStage2State() {
        if (!isVisible('powerDiv') && !isVisible('factoryDiv')) return {};
        const sliderEl = document.getElementById('slider');
        return {
            unusedClips:      getText('unusedClipsDisplay'),    // spendable clip pool (Stage 2 currency)
            // Swarm Computing — Swarm Gifts are the Stage 2 "trust" (fund memory/processors).
            swarmGifts:       getText('swarmGifts'),            // unspent gifts available now
            swarmStatus:      getText('swarmStatus'),           // Active / Lonely / Bored ...
            giftCountdown:    getText('giftCountdown'),         // "Next gift in N seconds" / Infinity
            swarmThink:       sliderEl ? sliderEl.value : null, // Work/Think slider 0–200 (0=Work)
            performance:      getText('performance'),          // Factory/Drone Performance %
            powerProduction:  getText('powerProductionRate'),  // MW produced (solar)
            powerConsumption: getText('powerConsumptionRate'), // MW consumed (drones+factories)
            farmLevel:        getText('farmLevel'),
            farmCost:         getText('farmCost'),
            batteryLevel:     getText('batteryLevel'),
            batteryCost:      getText('batteryCost'),
            storedPower:      getText('storedPower'),
            maxStorage:       getText('maxStorage'),
            factoryLevel:     getText('factoryLevelDisplay'),
            factoryCost:      getText('factoryCostDisplay'),
            harvesterLevel:   getText('harvesterLevelDisplay'),
            harvesterCost:    getText('harvesterCostDisplay'),
            wireDroneLevel:   getText('wireDroneLevelDisplay'),
            wireDroneCost:    getText('wireDroneCostDisplay'),
            availableMatter:  getText('availableMatterDisplay'),
            acquiredMatter:   getText('acquiredMatterDisplay'),
            nanoWire:         getText('nanoWire'),
        };
    }

    // ── State extraction ──────────────────────────────────────────────────────

    function getState() {
        const wire   = getWire();
        const invest = getInvestmentState();
        const s2     = getStage2State();
        const p3     = getPhase3State();

        return Object.assign({
            clips:             getText('clips'),
            unsoldClips:       getText('unsoldClips'),
            funds:             getText('funds'),
            wire:              wire,
            wirePrice:         getText('wireCost'),
            clipPrice:         getText('margin'),
            demand:            getText('demand'),
            marketing:         getText('marketingLvl'),
            marketingCost:     getText('adCost'),
            autoclippers:      getText('clipmakerLevel2'),
            clipperCost:       getText('clipperCost'),
            megaclippers:      getText('megaClipperLevel'),
            megaclipperCost:   getText('megaClipperCost'),
            clipRate:          getText('clipmakerRate'),
            trust:             getText('trust'),
            nextTrust:         getText('nextTrust'),
            memory:            getText('memory'),
            processors:        getText('processors'),
            operations:        getText('operations') + ' / ' + getText('maxOps'),
            creativity:        getText('creativity'),
            yomi:              getText('yomiDisplay'),
            honor:             getText('honorDisplay'),
            wireBuyerOn:       wireBuyerActive(),
            phase:             getPhase(),
            availableProjects: getProjects(),
            // Strategic Modeling / AutoTourney state (null when not yet unlocked)
            autoTourneyOn:     isVisible('strategyEngine') ? getText('autoTourneyStatus') : null,
            stratPicker:       isVisible('strategyEngine') ? (document.getElementById('stratPicker')?.value || null) : null,
        }, invest, s2, p3);
    }

    function getPhase() {
        if (isVisible('spaceDiv'))  return 3;
        if (isVisible('compDiv'))   return 2;
        return 1;
    }

    function getProjects() {
        const projects = [];
        document.querySelectorAll('#projectListTop button, #projectsDiv button').forEach(btn => {
            if (btn.offsetParent === null) return;
            if (btn.disabled) return;
            const opacity = parseFloat(window.getComputedStyle(btn).opacity);
            if (opacity < 0.6) return;
            projects.push(btn.innerText.trim().replace(/\n/g, ' '));
        });
        return projects.join(' | ') || 'none';
    }

    // ── Parse project cost from button text ───────────────────────────────────

    function getProjectCost(btn) {
        const text = btn.innerText;
        const opsM  = text.match(/([\d,]+)\s*ops/i);
        const crtM  = text.match(/([\d,]+)\s*creat/i);
        const trstM = text.match(/\(\s*(\d+)\s*Trust\s*\)/i);
        const yomiM = text.match(/([\d,]+)\s*yomi/i);
        // Clip costs use word suffixes ("1 sextillion clips") — capture number + optional word.
        const clipM = text.match(/([\d,.]+)\s*([a-zA-Z]+)?\s*clips/i);
        if (opsM)  return { type: 'ops',        amount: parseInt(opsM[1].replace(/,/g,'')) };
        if (crtM)  return { type: 'creativity',  amount: parseInt(crtM[1].replace(/,/g,'')) };
        if (trstM) return { type: 'trust',       amount: parseInt(trstM[1]) };
        if (yomiM) return { type: 'yomi',        amount: parseInt(yomiM[1].replace(/,/g,'')) };
        if (clipM) return { type: 'clips',       amount: parseBigNum(clipM[2] ? `${clipM[1]} ${clipM[2]}` : clipM[1]) };
        return null;
    }

    // ── Emergency recovery ────────────────────────────────────────────────────

    function handleEmergency() {
        const btns = document.querySelectorAll('#projectListTop button, #projectsDiv button');
        for (const btn of btns) {
            if (btn.innerText.toLowerCase().includes('beg for more wire') && btn.offsetParent !== null) {
                btn.click();
                console.log('[AGENT] EMERGENCY: Beg for More Wire');
                return;
            }
        }
        clickBtn('btnLowerPrice');
    }

    // ── Auto-spend on projects ────────────────────────────────────────────────

    const PROJECT_PRIORITY = [
        // ops-cost — production critical
        'improved autoclippers',
        'wirebuyer',
        'improved wire extrusion',
        'optimized wire extrusion',
        'microlattice shapecasting',
        'even better autoclippers',
        'hadwiger clip diagrams',
        'hypno harmonics',
        'new slogan',
        'catchy jingle',
        'revtracker',
        'quantum computing',
        'algorithmic trading',
        'photonic chip',
        'strategic modeling',
        'megaclippers',               // project version (12,000 ops) — unlocks the mega button
        'spectral froth annealment',  // 200% more wire supply per spool
        'new strategy: a100',         // better tournament strategy for yomi
        'quantum foam annealment',    // 1000% more wire supply per spool
        'hypnodrones',
        // Stage 2 manufacturing (ops-cost, must be purchased in this order)
        'tóth tubule enfolding',     // 45k ops — unlocks manufacturing status indicators
                                     // (game's exact name is "Tóth Tubule Enfolding" — the
                                     //  earlier "tubulue" typo never matched, blocking Stage 2)
        'power grid',                // 40k ops — unlocks energy production
        'nanoscale wire production', // 35k ops — unlocks wire production indicators
        'harvester drones',          // 25k ops — converts Available Matter → Acquired Matter
        'wire drones',               // 25k ops — converts Acquired Matter → Wire
        'clip factories',            // 35k ops — industrial-scale clip production
        // Stage 2 production UPGRADES (huge multipliers — were missing, blocking progression)
        'momentum',                  // 20k creat — Performance can exceed 100% (→1000%+). Buy ASAP.
        'theory of mind',            // 25k creat — better tournament Yomi
        'swarm computing',           // 36k yomi — unlocks Swarm Gifts (memory/processors source)
        'self-correcting supply chain', // 1 sextillion CLIPS — each factory then boosts every
                                        //   factory's output 1,000× (massive; buy ASAP)
        'upgraded factories',        // 80k ops — needs memory ≥ 80
        'hyperspeed factories',      // 85k ops — needs memory ≥ 85
        'collision avoidance',       // 80k ops — "Drone flocking: collision avoidance" (memory ≥ 80)
        'flocking: alignment',       // 100k ops — "Drone flocking: alignment" (memory ≥ 100)
        'adversarial cohesion',      // 50k yomi — "Drone Flocking: Adversarial Cohesion"
        // (NOTE: Self-correcting Supply Chain costs CLIPS with a word suffix we can't parse —
        //  it won't auto-buy yet. Space Exploration is intentionally NOT auto-bought: it ENDS
        //  Stage 2 and should wait for memory ~120+ and a big battery bank — handle separately.)
        // Stage 3 probe-support projects (ops/creativity-cost — same auto-buy path as above;
        //  the LLM still owns the probe DESIGN/allocation, these are just the supporting tech).
        'elliptic hull polytopes',   // 125k ops — HALVES probe hazard losses. Buy ASAP: at low
                                     //   Hazard Remediation the swarm dies to hazards (top priority).
        'combat',                    // 150k ops — probe combat vs Drifters (unlocks when you start
                                     //   losing probes to Drifters ~1M); only matches the project btn
        'name the battles',          // 225k creat — unlocks Honor (raises Max Probe Trust)
        'the ooda loop',             // 175k ops — Speed aids combat survival
        'strategic attachment',      // 175k creat — Stage 3 honor/creativity project
        // creativity-cost
        'creativity',
        'neural net optimizer',
        'optimized autoclipper',
        // trust-cost
        'limerick',
        'lexical processing',
        'combinatory harmonics',
        'daisy, daisy',
        'the hadwiger problem',
        'the tóth sausage conjecture',
        'donkey space',
        'tubes within tubes',
        'coherent extrapolated volition',
        'cure for cancer',
        'world peace',
        'global warming',
    ];

    let lastProjectClick = 0;

    function autoSpendOnProjects() {
        if (Date.now() - lastProjectClick < 1500) return;

        const currentOps   = getNum('operations', 0);  // #operations is current ops only
        const currentCrt   = getNum('creativity');
        const currentTrust = parseInt(getText('trust') || '0');
        const currentYomi  = getNum('yomiDisplay', 0);
        const currentClips = parseBigNum(getText('unusedClipsDisplay'));  // Stage 2 spendable pool

        const btns = Array.from(
            document.querySelectorAll('#projectListTop button, #projectsDiv button')
        ).filter(btn => btn.offsetParent !== null && !btn.disabled);

        for (const keyword of PROJECT_PRIORITY) {
            for (const btn of btns) {
                if (!btn.innerText.toLowerCase().includes(keyword)) continue;
                const cost = getProjectCost(btn);
                if (!cost) continue;
                const canAfford =
                    (cost.type === 'ops'        && currentOps   >= cost.amount) ||
                    (cost.type === 'creativity'  && currentCrt   >= cost.amount) ||
                    (cost.type === 'trust'       && currentTrust >= cost.amount) ||
                    (cost.type === 'yomi'        && currentYomi  >= cost.amount) ||
                    (cost.type === 'clips'       && currentClips >= cost.amount);
                if (canAfford) {
                    btn.click();
                    lastProjectClick = Date.now();
                    console.log(`[AGENT] Project: ${btn.innerText.trim().split('\n')[0]} (${cost.type}: ${cost.amount})`);
                    return;
                }
            }
        }
    }

    // ── Auto-buy marketing ────────────────────────────────────────────────────

    let lastMarketingClick = 0;

    function autoMarketing() {
        if (Date.now() - lastMarketingClick < 5000) return;
        const funds   = getNum('funds');
        const wire    = getWire();
        const unsold  = getNum('unsoldClips');
        const demand  = getNum('demand');  // was missing from scope — marketing never fired at high demand!
        const cost    = parseFloat((getText('adCost') || '9999').replace(/[^0-9.]/g,''));
        // Use total wealth (available cash + investments) as the affordability signal.
        // When most funds are deposited into the investment bankroll, available cash
        // stays low and marketing would stall even during profitable overnight runs.
        const bankroll    = parseFloat((getText('investmentBankroll') || '0').replace(/[^0-9.]/g,'')) || 0;
        const stocks      = parseFloat((getText('secValue')           || '0').replace(/[^0-9.]/g,'')) || 0;
        const totalWealth = funds + bankroll + stocks;
        // Fire when:
        //   - total wealth is 1.5× the cost (we can genuinely afford it)
        //   - available funds cover the cost (game requires cash, not bankroll)
        //   - wire is healthy (don't buy marketing while about to run out of wire)
        //   - demand is at least minimal (> 50%) — skip only if nobody wants clips at all.
        //     The old condition (demand >= 400 || unsold < 40) was too restrictive:
        //     in Stage 2 with large unsold inventory and 200% demand it never fired,
        //     even though marketing is exactly what raises the demand ceiling to clear
        //     that inventory.
        if (totalWealth > cost * 1.5 && funds >= cost && wire > 200 && demand > 50) {
            if (clickBtn('btnExpandMarketing')) {
                lastMarketingClick = Date.now();
                console.log(`[AGENT] Marketing upgraded (cost=$${cost}, wealth=$${totalWealth.toFixed(0)})`);
            }
        }
    }

    // ── Auto-buy MegaClippers ─────────────────────────────────────────────────
    // Rate-limited to one per 5 s to prevent a large cash balance (e.g. after an
    // investment withdraw) from being spent entirely on clippers before marketing
    // or projects get a chance to fire.
    // Demand/inventory guard: don't add production capacity when we already have
    // a large unsold backlog and demand is well below ceiling — more clips would
    // just deepen the backlog with no revenue benefit.

    let lastMegaClipperClick = 0;

    function autoMegaClippers() {
        if (!isVisible('megaClipperDiv')) return;
        if (Date.now() - lastMegaClipperClick < 5000) return;

        const funds      = getNum('funds');
        const wire       = getWire();
        const wireCost   = getNum('wireCost', 9999);
        const megaCost   = getNum('megaClipperCost', 9999);
        const unsold     = getNum('unsoldClips');
        const demand     = getNum('demand');
        const spoolsLeft = Math.floor((funds - megaCost) / wireCost);

        // Skip if inventory is already large and demand isn't near the ceiling.
        // Production outpaces demand in this state — buying more capacity just
        // deepens the backlog without adding revenue.
        if (unsold > 100 && demand < 400) return;

        if (wire > 1000 && spoolsLeft >= 3) {
            if (clickBtn('btnMakeMegaClipper')) {
                lastMegaClipperClick = Date.now();
                console.log(`[AGENT] MegaClipper bought (funds=$${funds.toFixed(0)}, unsold=${unsold}, demand=${demand}%)`);
            }
        }
    }

    // ── Auto-build Stage 2 manufacturing (Power + Drones + Factories) ───────────
    // Stage 2 is a power-management game. Everything is paid in CLIPS (the spendable
    // "Unused Clips" pool), and the game DISABLES a build button when you can't afford it,
    // so gating on `!btn.disabled` makes overspending impossible and self-paces against the
    // exponentially rising costs.
    //
    // IMPORTANT: we drive off POWER PRODUCTION vs CONSUMPTION, never off "performance".
    // Performance reads 0 until consumers exist, so using it as the solar trigger
    // deadlocks the cold start (dump all clips into solar, never build the factories/drones
    // that actually start production). Instead we keep a power surplus (headroom) and build
    // consumers into it; factories convert wire→clips, drones make the wire — both needed.
    //
    // Priority each tick:
    //   1. real power DEFICIT (consumers outrunning production) → add solar
    //   2. cold-start baseline solar (falls through if unaffordable)
    //   3. CONSUMERS into spare power — factories + drones, balanced by target progress
    //   4. grow solar when we want consumers but lack headroom
    //   5. batteries — low-priority cheap hedge, only once consumers are at target
    let lastStage2Click = 0;

    // Click a build button only if it exists, is visible, and is affordable (!disabled).
    function buildClick(id) {
        const b = document.getElementById(id);
        if (b && b.offsetParent !== null && !b.disabled) {
            b.click();
            lastStage2Click = Date.now();
            return true;
        }
        return false;
    }

    // Build up to `n` drones of a type using the largest affordable batch button (+1k/+100/
    // +10/×1). Single builds can't reach the endgame's huge drone counts in reasonable time,
    // so we batch — but the caller caps `n` so a batch never breaks the ≤1.5 swarm ratio.
    function buildDroneBatch(type, n) {
        const ids = type === 'wire'
            ? ['btnWireDronex1000', 'btnWireDronex100', 'btnWireDronex10', 'btnMakeWireDrone']
            : ['btnHarvesterx1000', 'btnHarvesterx100', 'btnHarvesterx10', 'btnMakeHarvester'];
        const sizes = [1000, 100, 10, 1];
        for (let i = 0; i < ids.length; i++) {
            if (n >= sizes[i] && buildClick(ids[i])) return sizes[i];
        }
        return 0;
    }

    function autoStage2Manufacturing() {
        if (!isVisible('powerDiv')) return;                       // domain not unlocked yet
        if (Date.now() - lastStage2Click < STAGE2_MS) return;     // rate limit

        const prod      = getNum('powerProductionRate', 0);
        const cons      = getNum('powerConsumptionRate', 0);
        const farms     = getNum('farmLevel', 0);
        const batteries = getNum('batteryLevel', 0);
        const factories = getNum('factoryLevelDisplay', 0);
        const harv      = getNum('harvesterLevelDisplay', 0);
        const wireD     = getNum('wireDroneLevelDisplay', 0);
        const drones    = harv + wireD;
        const headroom  = prod - cons;                            // spare MW
        const maxStorage = getNum('maxStorage', 0);              // MW-seconds of battery storage

        // 1) REAL POWER DEFICIT: consumers exist and production has fallen behind → solar.
        if (cons > 0 && prod < cons * POWER_MARGIN) {
            if (buildClick('btnFarmx10') || buildClick('btnMakeFarm')) {
                console.log(`[AGENT] Solar Farm (deficit prod=${prod} cons=${cons})`);
            }
            return;   // never add load while underpowered
        }

        // 2) COLD-START baseline solar so the first consumers have headroom. Falls THROUGH
        //    to consumers if a farm isn't affordable (don't block the cheap factory on it).
        if (farms < SOLAR_MIN && buildClick('btnMakeFarm')) {
            console.log(`[AGENT] Solar Farm baseline (${farms + 1}/${SOLAR_MIN})`);
            return;
        }

        // 3) CONSUMERS — the clip-producing core, built into spare power.
        const wantFactory = factories < FACTORY_TARGET;
        const wantDrone   = drones    < DRONE_TARGET;
        const facProgress = FACTORY_TARGET ? factories / FACTORY_TARGET : 1;
        const droProgress = DRONE_TARGET  ? drones    / DRONE_TARGET    : 1;

        // Build a factory (200 MW) when it's proportionally behind drones and powered.
        if (wantFactory && headroom >= 200 && (facProgress <= droProgress || !wantDrone)) {
            if (buildClick('btnMakeFactory')) {
                console.log(`[AGENT] Clip Factory (${factories + 1}/${FACTORY_TARGET}, headroom=${headroom}MW)`);
                return;
            }
        }
        // Build drones (1 MW each) into spare power, targeting wire ≈ DRONE_RATIO × harvester.
        // Batch with the +10/+100/+1k buttons (single builds can't reach endgame counts), but
        // CAP each batch so neither type exceeds 1.5× the other — staying ≤1.5 keeps the swarm
        // Organized (and gradually fixes an already-disorganized ratio). The 1 MW/drone power
        // headroom also caps the batch, so drones and solar leapfrog as production scales.
        if (wantDrone && headroom >= 1) {
            let type, maxByRatio;
            if (wireD < harv * DRONE_RATIO) {            // need more wire drones
                type = 'wire';
                maxByRatio = Math.floor(harv * 1.5) - wireD;   // keep wire/harv ≤ 1.5
            } else {                                     // need more harvesters
                type = 'harvester';
                maxByRatio = Math.floor(wireD * 1.5) - harv;   // keep harv/wire ≤ 1.5
            }
            // How many we may add: limited by ratio, remaining-to-target, and power headroom.
            let n = Math.min(maxByRatio, DRONE_TARGET - drones, headroom);
            if (n < 1) n = 1;                            // always allowed to nudge toward balance
            const built = buildDroneBatch(type, n);
            if (built) {
                console.log(`[AGENT] ${type} drones +${built} (harv=${harv} wire=${wireD})`);
                return;
            }
        }

        // 4) Want more consumers but no power headroom → grow production (if affordable).
        if ((wantFactory || wantDrone) && headroom < 200) {
            if (buildClick('btnFarmx10') || buildClick('btnMakeFarm')) {
                console.log(`[AGENT] Solar Farm (grow headroom, headroom=${headroom}MW)`);
            }
            return;
        }

        // 5) BATTERIES — build storage up to BATTERY_TARGET_MW (Space Exploration's 10M MW-sec
        //    requirement). Use +100/+10 buttons so we don't crawl there one battery at a time.
        //    Lowest priority (after consumers); batteries cost clips, not power.
        if (maxStorage < BATTERY_TARGET_MW && !wantFactory && !wantDrone) {
            if (buildClick('btnBatteryx100') || buildClick('btnBatteryx10') || buildClick('btnMakeBattery')) {
                console.log(`[AGENT] Battery Tower (storage ${maxStorage}/${BATTERY_TARGET_MW} MW-sec)`);
                return;
            }
        }
    }

    // ── Quantum Computing ─────────────────────────────────────────────────────
    // The photonic chip's charge oscillates on a sine wave — clicking Compute adds the
    // CURRENT charge to ops. When the charge is negative, clicking DRAINS ops.
    // We read qCompDisplay (result of the last click) and pause after a negative result
    // to let the sine wave cycle back to positive before trying again.

    let qComputeCoolUntil = 0;

    function autoQuantumCompute() {
        if (!isVisible('compDiv')) return;
        if (Date.now() < qComputeCoolUntil) return;

        // qCompDisplay shows "qOps: NNN" after each click (NNN may be negative).
        //   is &nbsp; — the initial/empty state before any click.
        const raw   = (document.getElementById('qCompDisplay')?.innerText || '').replace(/ /g, '').trim();
        const match = raw.match(/-?\d+/);
        if (match && parseInt(match[0]) < 0) {
            // Last click was negative — pause 1.2s to let the chip cycle to positive phase
            qComputeCoolUntil = Date.now() + 1200;
            return;
        }

        clickBtn('btnQcompute');
    }

    // ── Auto-run tournament ───────────────────────────────────────────────────
    // Full two-step tournament cycle:
    //   Step 1 — btnNewTournament → newTourney(): spends ops, generates payoff matrix,
    //            tournament is now "in progress"
    //   Step 2 — btnRunTournament → runTourney(): applies the selected strategy and
    //            AWARDS YOMI — this step is also required, not optional
    // Both buttons are needed in sequence. The strategy must be set (RANDOM enforced
    // by the fast rule) before Step 2 is clicked.

    let lastTournamentRun  = 0;
    let pendingRunAt       = 0;   // timestamp after which we should click Run

    function autoRunTournament() {
        if (!isVisible('strategyEngine')) return;

        // Step 2: if we recently started a tournament, wait briefly then click Run
        if (pendingRunAt > 0 && Date.now() >= pendingRunAt) {
            const runBtn = document.getElementById('btnRunTournament');
            if (runBtn && !runBtn.disabled) {
                runBtn.click();
                console.log('[AGENT] Tournament Run clicked — Yomi awarded');
            }
            pendingRunAt = 0;  // clear regardless — don't retry if button wasn't ready
        }

        // Step 1: start a new tournament when ops are high enough
        if (Date.now() - lastTournamentRun < 5000) return;

        // #operations and #maxOps are separate DOM elements — read them independently.
        const currOps     = getNum('operations', 0);
        const maxOps      = getNum('maxOps', 0);
        const costText    = getText('newTourneyCost') || '1000';
        const tourneyCost = parseInt(costText.replace(/[^0-9]/g, '')) || 1000;

        if (maxOps > 100 && currOps >= maxOps * 0.9 && currOps >= tourneyCost) {
            const newBtn = document.getElementById('btnNewTournament');
            if (newBtn && !newBtn.disabled) {
                newBtn.click();
                lastTournamentRun = Date.now();
                pendingRunAt      = Date.now() + 1500;  // click Run 1.5s later
                console.log(`[AGENT] New tournament started (ops ${currOps}/${maxOps}, cost ${tourneyCost})`);
            }
        }
    }

    // ── Fast rules ────────────────────────────────────────────────────────────

    function runFastRules() {
        autoQuantumCompute();

        const funds        = getNum('funds');
        const wire         = getWire();
        const unsold       = getNum('unsoldClips');
        const demand       = getNum('demand');
        const clipperCost  = getNum('clipperCost', 9999);
        const wireCost     = getNum('wireCost',    9999);
        const autoclippers = getNum('clipmakerLevel2');

        if (wire <= 0 && funds < wireCost && !wireBuyerActive()) {
            handleEmergency();
            return;
        }

        if (!wireBuyerActive() && wire < 1000 && funds >= wireCost) {
            if (clickBtn('btnBuyWire') && wire < 100) return;
        }

        if (autoclippers < 5) {
            clickBtn('btnMakePaperclip');
        }

        // ── Auto-buy AutoClippers (with cost-crossover + inventory guards) ─────
        // Two guards mirror the MegaClipper rule so we never spend on the worse buy:
        //
        // 1. Cost crossover: once MegaClippers are unlocked, the AutoClipper price
        //    eventually grows past the MegaClipper price. At that point an AutoClipper
        //    costs MORE for FAR LESS production — a strictly worse deal. So if Megas
        //    are available and an AutoClipper is no longer cheaper than a MegaClipper,
        //    skip and let autoMegaClippers() spend the cash instead.
        // 2. Inventory/demand: if we already have a big unsold backlog and demand is
        //    well below the ceiling, more production capacity just deepens the backlog.
        const megaUnlocked = isVisible('megaClipperDiv');
        const megaCost     = getNum('megaClipperCost', Infinity);
        const spoolsAfter  = Math.floor((funds - clipperCost) / wireCost);

        const megaIsBetterDeal = megaUnlocked && clipperCost >= megaCost;  // guard 1
        const backlogTooDeep   = unsold > 100 && demand < 400;             // guard 2

        if (wire > 1000 && spoolsAfter >= 3 && !megaIsBetterDeal && !backlogTooDeep) {
            if (clickBtn('btnMakeClipper')) {
                console.log(`[AGENT] AutoClipper bought (wire=${wire}, buffer=${spoolsAfter}, cost=$${clipperCost.toFixed(0)} < mega=$${megaCost.toFixed(0)})`);
            }
        }

        // Tournament strategy — enforce RANDOM every fast-rules tick.
        // stratPicker may have offsetParent=null inside strategyEngine (reports hidden but
        // is functional). The agent override was silently bailing on the visibility check;
        // enforcing directly here at 50ms wins over the game's render resets.
        if (isVisible('strategyEngine')) {
            const sp = document.getElementById('stratPicker');
            if (sp && sp.value !== '0') {
                sp.value = '0';
                sp.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                sp.dispatchEvent(new Event('input',  { bubbles: true, cancelable: true }));
            }
        }

        // Price management — stage-aware.
        //
        // Stage 1 (portValue absent): revenue comes from selling clips.
        //   Target demand: 200–500%. If inventory outpaces the market, lower price.
        //   Cap: more than ~10 seconds of production sitting unsold = price too high.
        //
        // Stage 2+ (portValue present): primary income is the investment engine.
        //   Clips need to ACCUMULATE — Stage 3 (Space Exploration) requires 5 octillion clips.
        //   Do NOT lower price to clear inventory; let clips pile up for that goal.
        //   Only intervene if demand collapses near zero, or raise price at ceiling.
        //
        // Use portValue text rather than isVisible('investmentEngine') — the div may report
        // hidden in Stage 2 even though investments are active and portValue is readable.
        const investActive = !!getText('portValue');
        const clipRate     = getNum('clipmakerRate', 0);
        // ~10 seconds of production is a healthy Stage 1 buffer; above this, price is too high.
        const inventoryCap = Math.max(1000, clipRate * 10);

        if (demand >= 500) {
            // Demand ceiling — always raise price (more revenue per clip, both stages)
            clickBtn('btnRaisePrice');
        } else if (!investActive && (demand < 200 || unsold > inventoryCap)) {
            // Stage 1: demand below healthy floor OR inventory growing past buffer.
            // Clips must sell to fund wire/autoclippers — lower price.
            clickBtn('btnLowerPrice');
        } else if (investActive && demand < 50) {
            // Stage 2: investments handle revenue, but if demand nearly collapses
            // lower price so some clips still sell (keeps funds from hitting zero).
            clickBtn('btnLowerPrice');
        } else if (unsold < 10 && demand > 100) {
            // Inventory nearly empty and demand positive — raise price
            clickBtn('btnRaisePrice');
        }
    }

    // ── LLM action execution ──────────────────────────────────────────────────

    function executeAction(action, args) {
        console.log(`[AGENT] LLM: ${action}`, args || '');
        let success = false;
        let note    = '';

        switch (action) {

            // ── Basic actions ─────────────────────────────────────────────────
            case 'lower_price':      success = clickBtn('btnLowerPrice');       break;
            case 'raise_price':      success = clickBtn('btnRaisePrice');       break;
            case 'buy_wire':         success = clickBtn('btnBuyWire');          break;
            case 'buy_autoclipper':  success = clickBtn('btnMakeClipper');      break;
            case 'buy_megaclipper':  success = clickBtn('btnMakeMegaClipper');  break;
            case 'buy_marketing':    success = clickBtn('btnExpandMarketing');  break;
            case 'make_paperclip':   success = clickBtn('btnMakePaperclip');    break;
            case 'add_processor':    success = clickBtn('btnAddProc');          break;
            case 'add_memory':       success = clickBtn('btnAddMem');           break;

            // ── Swarm Computing: Work/Think slider (Stage 2) ──────────────────
            // #slider range 0–200: 0 = all Work (production), 200 = all Think (Swarm Gifts).
            // The LLM picks the balance; gifts fund memory/processors (the Stage 2 "trust").
            case 'set_swarm_think':     success = setSwarmSlider(180); note = '90% Think'; break;
            case 'set_swarm_balanced':  success = setSwarmSlider(100); note = '50% Think'; break;
            case 'set_swarm_work':      success = setSwarmSlider(40);  note = '20% Think'; break;
            // Recover a "Disorganized" swarm (drone imbalance tipped over) — costs 5k yomi.
            case 'sync_swarm':          success = clickBtn('btnSynchSwarm'); note = success ? 'synchronized swarm' : 'btnSynchSwarm not found'; break;

            // ── Project purchase ──────────────────────────────────────────────
            case 'buy_project': {
                if (!args || !args.name) { note = 'no project name given'; break; }
                const needle = args.name.toLowerCase();
                const btns   = document.querySelectorAll('#projectListTop button, #projectsDiv button');
                for (const btn of btns) {
                    if (btn.innerText.toLowerCase().includes(needle) && btn.offsetParent !== null) {
                        btn.click();
                        success = true;
                        note    = btn.innerText.trim().split('\n')[0];
                        break;
                    }
                }
                if (!success) {
                    note = `not found: ${args.name}`;
                    console.warn(`[AGENT] Project not found: ${args.name}`);
                }
                break;
            }

            // ── Investment actions ────────────────────────────────────────────
            // investmentEngine div contains:
            //   #investStrat select (low/med/hi)
            //   #btnInvest (Deposit), #btnWithdraw
            //   #btnImproveInvestments (upgrade, costs Yomi)

            case 'invest_deposit': {
                success = clickBtn('btnInvest');
                note    = success ? 'deposited funds into investment' : 'btnInvest not visible';
                break;
            }
            case 'invest_withdraw': {
                success = clickBtn('btnWithdraw');
                note    = success ? 'withdrew from investment' : 'btnWithdraw not visible';
                break;
            }
            case 'set_invest_low':
            case 'set_invest_med':
            case 'set_invest_hi': {
                const el = document.getElementById('investStrat');
                if (!el || el.offsetParent === null) { note = 'investStrat not visible'; break; }
                const valMap = { 'set_invest_low': 'low', 'set_invest_med': 'med', 'set_invest_hi': 'hi' };
                el.value = valMap[action];
                // Must dispatch 'change' with bubbles:true — the game likely uses document-level
                // event delegation. Non-bubbling events don't reach parent listeners, so the game
                // ignores them and resets the select back to its internal investMode on its next tick.
                el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                success  = true;
                note     = `risk strategy set to ${valMap[action]}`;
                break;
            }
            case 'upgrade_investment': {
                success = clickBtn('btnImproveInvestments');
                note    = success ? 'investment engine upgraded' : 'btnImproveInvestments not visible';
                break;
            }

            // ── Strategic Modeling / AutoTourney ──────────────────────────────
            case 'run_tournament': {
                // Full two-step: New Tournament (generates matrix) → Run (awards Yomi).
                // Both buttons are needed in sequence.
                const newBtn = document.getElementById('btnNewTournament');
                const runBtn = document.getElementById('btnRunTournament');
                if (newBtn && !newBtn.disabled) {
                    newBtn.click();
                    // Click Run after 1.5s — let the game process the new tournament first
                    setTimeout(() => { if (runBtn && !runBtn.disabled) runBtn.click(); }, 1500);
                    success = true;
                    note    = 'tournament started; Run scheduled in 1.5s';
                } else {
                    note = 'btnNewTournament not found or disabled';
                }
                break;
            }
            case 'toggle_auto_tourney': {
                success = clickBtn('btnToggleAutoTourney');
                note    = success ? 'AutoTourney toggled' : 'AutoTourney button not visible';
                break;
            }
            case 'set_strategy_random': {
                const el = document.getElementById('stratPicker');
                if (!el) { note = 'stratPicker not found'; break; }
                // Do NOT check el.offsetParent — the select is functional inside
                // strategyEngine even when the browser reports it as hidden.
                // Checking offsetParent is why this action silently did nothing before.
                el.value = '0'; // '0' = RANDOM strategy
                el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new Event('input',  { bubbles: true, cancelable: true }));
                success = true;
                note    = 'strategy set to RANDOM';
                break;
            }

            // ── Phase 3: Probe design ──────────────────────────────────────────
            // Each stat has a raise (>) and lower (<) button.
            // Total trust points across all 8 stats = probeTrustDisplay.
            // increase_probe_trust costs Yomi (probeTrustCostDisplay).

            case 'raise_probe_speed':   success = clickBtn('btnRaiseProbeSpeed');   break;
            case 'lower_probe_speed':   success = clickBtn('btnLowerProbeSpeed');   break;
            case 'raise_probe_nav':     success = clickBtn('btnRaiseProbeNav');     break;
            case 'lower_probe_nav':     success = clickBtn('btnLowerProbeNav');     break;
            case 'raise_probe_rep':     success = clickBtn('btnRaiseProbeRep');     break;
            case 'lower_probe_rep':     success = clickBtn('btnLowerProbeRep');     break;
            case 'raise_probe_haz':     success = clickBtn('btnRaiseProbeHaz');     break;
            case 'lower_probe_haz':     success = clickBtn('btnLowerProbeHaz');     break;
            case 'raise_probe_fac':     success = clickBtn('btnRaiseProbeFac');     break;
            case 'lower_probe_fac':     success = clickBtn('btnLowerProbeFac');     break;
            case 'raise_probe_harv':    success = clickBtn('btnRaiseProbeHarv');    break;
            case 'lower_probe_harv':    success = clickBtn('btnLowerProbeHarv');    break;
            case 'raise_probe_wire':    success = clickBtn('btnRaiseProbeWire');    break;
            case 'lower_probe_wire':    success = clickBtn('btnLowerProbeWire');    break;
            case 'raise_probe_combat':  success = clickBtn('btnRaiseProbeCombat');  break;
            case 'lower_probe_combat':  success = clickBtn('btnLowerProbeCombat');  break;
            case 'increase_probe_trust': success = clickBtn('btnIncreaseProbeTrust'); break;
            case 'increase_max_trust':   success = clickBtn('btnIncreaseMaxTrust');   break;
            case 'launch_probe':         success = clickBtn('btnMakeProbe');           break;

            case 'nothing':
            case 'wait':
            default:
                success = true;
                break;
        }

        if (action !== 'wait' && action !== 'nothing') {
            postResult(action, success, note);
        }
        return success;
    }

    // ── Relay communication ───────────────────────────────────────────────────

    function postState(stateData) {
        GM_xmlhttpRequest({
            method:  'POST',
            url:     `${RELAY}/state`,
            headers: { 'Content-Type': 'application/json' },
            data:    JSON.stringify(stateData),
            onerror: () => console.warn('[AGENT] relay state POST failed'),
        });
    }

    function postResult(action, success, note) {
        GM_xmlhttpRequest({
            method:  'POST',
            url:     `${RELAY}/result`,
            headers: { 'Content-Type': 'application/json' },
            data:    JSON.stringify({ action, success: !!success, note: note || '' }),
            onerror: () => console.warn('[AGENT] relay result POST failed'),
        });
    }

    // ── Badge ─────────────────────────────────────────────────────────────────
    // Adjust BADGE_OPACITY (0.0 = invisible, 1.0 = fully opaque) to taste.

    const BADGE_OPACITY = 0.93;

    let badgeEl       = null;
    let recentActions = [];   // last 3 LLM actions, [{label, tick}]
    let lastThought   = '';
    let tickCount     = 0;

    function createBadge() {
        badgeEl = document.createElement('div');
        badgeEl.id = 'agent-badge';
        badgeEl.style.cssText = `
            position: fixed; bottom: 12px; right: 12px;
            background: rgba(13,17,23,${BADGE_OPACITY}); color: #c9d1d9;
            font-family: monospace; font-size: 11px; line-height: 1.7;
            padding: 12px 16px; border-radius: 8px;
            border: 1px solid #30363d; z-index: 9999;
            pointer-events: none; width: 380px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        `;
        document.body.appendChild(badgeEl);
    }

    function updateBadge(state) {
        if (!badgeEl) return;

        const stage    = state ? state.phase          : '?';
        const clips    = state ? (state.clips   || '—') : '—';
        const funds    = state ? (state.funds   || '—') : '—';
        const wire     = state ? (state.wire    || '—') : '—';
        const demand   = state ? (state.demand  || null) : null;
        const yomi     = state ? (state.yomi    || null) : null;
        const unsold   = state ? (state.unsoldClips || null) : null;
        const ops      = state ? (state.operations  || null) : null;
        const autoTrny = state ? (state.autoTourneyOn || null) : null;

        const wireNum  = parseFloat(wire);
        const wireWarn = (!isNaN(wireNum) && wireNum < 100)
            ? ' <span style="color:#f85149">⚠ LOW</span>' : '';

        // Thought — longer display with word-break
        const thought = lastThought
            ? lastThought.substring(0, 200) + (lastThought.length > 200 ? '…' : '')
            : '(waiting for LLM…)';

        // Recent actions — newest first
        const actHtml = recentActions.length
            ? [...recentActions].reverse().map(a =>
                `<span style="color:#3fb950">▸</span> <span style="color:#e6edf3">#${a.tick}</span> ${a.label}`
              ).join('<br>')
            : '<span style="color:#484f58">—</span>';

        const hr = `<div style="border-top:1px solid #21262d;margin:7px 0 5px"></div>`;

        badgeEl.innerHTML =
            // Header
            `<div style="display:flex;justify-content:space-between;align-items:center;` +
            `border-bottom:1px solid #21262d;padding-bottom:5px;margin-bottom:7px">` +
            `<span style="color:#58a6ff;font-weight:bold;font-size:12px">🤖 AGENT v2.0</span>` +
            `<span style="color:#484f58">Stage ${stage} &nbsp;·&nbsp; tick #${tickCount}</span>` +
            `</div>` +
            // State grid
            `<span style="color:#8b949e">clips   </span>${clips}<br>` +
            `<span style="color:#8b949e">funds   </span>${funds}<br>` +
            `<span style="color:#8b949e">wire    </span>${wire}${wireWarn}<br>` +
            (demand  ? `<span style="color:#8b949e">demand  </span>${demand}<br>` : '') +
            (unsold  ? `<span style="color:#8b949e">unsold  </span>${unsold}<br>` : '') +
            (yomi    ? `<span style="color:#8b949e">yomi    </span>${yomi}<br>`   : '') +
            (ops     ? `<span style="color:#8b949e">ops     </span>${ops}<br>`    : '') +
            (autoTrny !== null
                ? `<span style="color:#8b949e">tourney </span>` +
                  `<span style="color:${autoTrny === 'ON' ? '#3fb950' : '#f85149'}">${autoTrny}</span><br>`
                : '') +
            // Thought
            hr +
            `<div style="color:#e3b341;font-size:10px;letter-spacing:.5px;margin-bottom:3px">THOUGHT</div>` +
            `<div style="color:#8b949e;font-size:10px;word-break:break-word;line-height:1.5">${thought}</div>` +
            // Recent actions
            hr +
            `<div style="color:#e3b341;font-size:10px;letter-spacing:.5px;margin-bottom:3px">RECENT ACTIONS</div>` +
            `<div style="font-size:10px;line-height:1.8">${actHtml}</div>`;
    }

    // ── Action polling ────────────────────────────────────────────────────────

    function pollAction() {
        GM_xmlhttpRequest({
            method: 'GET',
            url:    `${RELAY}/action`,
            onload: (resp) => {
                try {
                    const data = JSON.parse(resp.responseText);
                    if (data && data.action && data.action !== 'wait') {
                        tickCount++;
                        const label = data.action + (data.args && data.args.name ? ': ' + data.args.name : '');
                        lastThought = data.thought || lastThought;
                        recentActions.push({ label, tick: tickCount });
                        if (recentActions.length > 3) recentActions.shift();
                        executeAction(data.action, data.args);
                    }
                } catch (e) {
                    console.warn('[AGENT] Bad action JSON', e);
                }
            },
            onerror: () => console.warn('[AGENT] relay action GET failed'),
        });
    }

    // ── Startup ───────────────────────────────────────────────────────────────

    function init() {
        console.log('[AGENT] Universal Paperclips bridge v2.0 active');

        setInterval(runFastRules,        50);
        setInterval(autoSpendOnProjects, 500);
        setInterval(autoRunTournament,   500);
        setInterval(autoMarketing,       1000);
        setInterval(autoMegaClippers,    1000);
        setInterval(autoStage2Manufacturing, STAGE2_MS);   // Power + drones + factories
        setInterval(pollAction,          ACTION_MS);

        // Combined state push + badge update on the same interval
        setInterval(() => {
            const state = getState();
            postState(state);
            updateBadge(state);
        }, STATE_MS);

        createBadge();
    }

    window.addEventListener('load', () => setTimeout(init, 1000));

})();
