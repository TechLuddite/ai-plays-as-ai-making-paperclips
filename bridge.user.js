// ==UserScript==
// @name         Universal Paperclips — ReAct Agent Bridge
// @namespace    http://localhost/
// @version      1.9
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
        'even better autoclippers',
        'hadwiger clip diagrams',
        'hypno harmonics',
        'new slogan',
        'catchy jingle',
        'revtracker',
        'quantum computing',
        'algorithmic trading',
        'strategic modeling',
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
        const funds  = getNum('funds');
        const wire   = getWire();
        const unsold = getNum('unsoldClips');
        const cost   = parseFloat((getText('adCost') || '9999').replace(/[^0-9.]/g,''));
        if (funds > cost * 1.2 && wire > 200 && unsold < 40) {
            if (clickBtn('btnExpandMarketing')) {
                lastMarketingClick = Date.now();
                console.log(`[AGENT] Marketing upgraded (cost was $${cost})`);
            }
        }
    }

    // ── Auto-buy MegaClippers ─────────────────────────────────────────────────

    function autoMegaClippers() {
        if (!isVisible('megaClipperDiv')) return;
        const funds      = getNum('funds');
        const wire       = getWire();
        const wireCost   = getNum('wireCost', 9999);
        const megaCost   = getNum('megaClipperCost', 9999);
        const spoolsLeft = Math.floor((funds - megaCost) / wireCost);
        if (wire > 1000 && spoolsLeft >= 3) {
            clickBtn('btnMakeMegaClipper');
        }
    }

    // ── Fast rules ────────────────────────────────────────────────────────────

    function runFastRules() {
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

        if (unsold > 50) {
            clickBtn('btnLowerPrice');
        } else if (demand > 500) {
            // demand extremely high — raise price regardless of inventory level
            clickBtn('btnRaisePrice');
        } else if (unsold < 10 && demand > 100) {
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
                success  = true;
                note     = `risk strategy set to ${valMap[action]}`;
                break;
            }
            case 'upgrade_investment': {
                success = clickBtn('btnImproveInvestments');
                note    = success ? 'investment engine upgraded' : 'btnImproveInvestments not visible';
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

            case 'wait':
            default:
                success = true;
                break;
        }

        if (action !== 'wait') {
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

    let badgeEl     = null;
    let lastAction  = '—';
    let lastThought = '';
    let tickCount   = 0;

    function createBadge() {
        badgeEl = document.createElement('div');
        badgeEl.id = 'agent-badge';
        badgeEl.style.cssText = `
            position: fixed; bottom: 10px; right: 10px;
            background: #0d1117; color: #c9d1d9;
            font-family: monospace; font-size: 11px; line-height: 1.6;
            padding: 10px 14px; border-radius: 6px;
            border: 1px solid #30363d; z-index: 9999;
            pointer-events: none; min-width: 220px; max-width: 300px;
        `;
        document.body.appendChild(badgeEl);
    }

    function updateBadge(state) {
        if (!badgeEl) return;
        const phase    = state ? state.phase    : '?';
        const clips    = state ? state.clips    : '—';
        const funds    = state ? state.funds    : '—';
        const wire     = state ? state.wire     : '—';
        const wireWarn = (wire !== '—' && parseFloat(wire) < 100) ? ' ⚠' : '';
        const thought  = lastThought
            ? lastThought.substring(0, 55) + (lastThought.length > 55 ? '…' : '')
            : '—';
        badgeEl.innerHTML =
            `<span style="color:#58a6ff;font-weight:bold">🤖 Agent</span>` +
            `<span style="color:#8b949e;float:right">Ph ${phase} · #${tickCount}</span><br>` +
            `<span style="color:#8b949e">clips </span> ${clips}<br>` +
            `<span style="color:#8b949e">funds </span> ${funds}<br>` +
            `<span style="color:#8b949e">wire  </span> ${wire}${wireWarn}<br>` +
            `<span style="color:#8b949e">act   </span> <span style="color:#3fb950">${lastAction}</span><br>` +
            `<span style="color:#8b949e">why   </span> <span style="color:#8b949e;font-size:10px">${thought}</span>`;
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
                        lastAction  = data.action + (data.args && data.args.name ? ': ' + data.args.name : '');
                        lastThought = data.thought || '';
                        tickCount++;
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
        console.log('[AGENT] Universal Paperclips bridge v1.9 active');

        setInterval(runFastRules,        50);
        setInterval(autoSpendOnProjects, 500);
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
