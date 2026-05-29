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

    function isVisible(id) {
        const el = document.getElementById(id);
        return el && el.offsetParent !== null;
    }

    function clickBtn(id) {
        const el = document.getElementById(id);
        if (el && el.offsetParent !== null) { el.click(); return true; }
        return false;
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
            probeTrust:     getText('probeTrustUsedDisplay') + '/' + getText('probeTrustDisplay'),
            drifters:       getText('drifterCount'),
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

    // ── State extraction ──────────────────────────────────────────────────────

    function getState() {
        const wire   = getWire();
        const invest = getInvestmentState();
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
        }, invest, p3);
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
        if (opsM)  return { type: 'ops',        amount: parseInt(opsM[1].replace(/,/g,'')) };
        if (crtM)  return { type: 'creativity',  amount: parseInt(crtM[1].replace(/,/g,'')) };
        if (trstM) return { type: 'trust',       amount: parseInt(trstM[1]) };
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

        const opsText      = getText('operations') || '';
        const opsParts     = opsText.split('/').map(s => parseInt(s.replace(/,/g,'').trim()));
        const currentOps   = isNaN(opsParts[0]) ? 0 : opsParts[0];
        const currentCrt   = getNum('creativity');
        const currentTrust = parseInt(getText('trust') || '0');

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
                    (cost.type === 'trust'       && currentTrust >= cost.amount);
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
    // Fires btnRunTournament directly when ops hit 90%+ of max capacity.
    // Tournaments cost 1,000 ops and award Yomi.
    // This catches the case where AutoTourney is ON but strategy wasn't sticking.
    // Uses direct .click() (not clickBtn) to bypass the offsetParent visibility
    // check — btnRunTournament may report hidden inside strategyEngine.

    let lastTournamentRun = 0;

    function autoRunTournament() {
        if (!isVisible('strategyEngine')) return;
        if (Date.now() - lastTournamentRun < 2000) return;

        const opsText = getText('operations') || '';
        const parts   = opsText.split('/').map(s => parseInt(s.replace(/[^0-9]/g, '').trim()));
        const currOps = isNaN(parts[0]) ? 0 : parts[0];
        const maxOps  = isNaN(parts[1]) ? 1 : parts[1];

        if (maxOps > 100 && currOps >= maxOps * 0.9) {
            const btn = document.getElementById('btnRunTournament');
            if (btn && !btn.disabled) {
                btn.click();
                lastTournamentRun = Date.now();
                console.log(`[AGENT] Tournament run (ops ${currOps}/${maxOps})`);
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

        const spoolsAfter = Math.floor((funds - clipperCost) / wireCost);
        if (wire > 1000 && spoolsAfter >= 3) {
            if (clickBtn('btnMakeClipper')) {
                console.log(`[AGENT] AutoClipper bought (wire=${wire}, buffer=${spoolsAfter})`);
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
                // Use direct .click() — btnRunTournament may have offsetParent=null
                // inside strategyEngine even when clickable.
                const btn = document.getElementById('btnRunTournament');
                if (btn && !btn.disabled) { btn.click(); success = true; note = 'tournament run'; }
                else { note = 'run tournament button not found or disabled'; }
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
