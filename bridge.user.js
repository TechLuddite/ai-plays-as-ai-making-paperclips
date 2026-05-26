// ==UserScript==
// @name         Universal Paperclips — ReAct Agent Bridge
// @namespace    http://localhost/
// @version      1.9
// @description  Reads game state and executes agent actions via local relay
// @author       paperclips-agent
// @match        https://www.decisionproblem.com/paperclips/*
// @match        http://www.decisionproblem.com/paperclips/*
// @match        https://browsercraft.com/play/universal-paperclips*
// @match        http://browsercraft.com/play/universal-paperclips*
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
    // transWire is used in space phase

    function getWire() {
        // prefer nanoWire in phase 3, fall back to phase 1 wire
        const nano = getNum('nanoWire', -1);
        if (nano >= 0 && isVisible('wireProductionDiv')) return nano;
        return getNum('wire', 0);
    }

    function wireBuyerActive() {
        // WireBuyer project toggles a button; if div is visible and status is ON, wire is auto-bought
        const status = getText('wireBuyerStatus');
        return isVisible('wireBuyerDiv') && status === 'ON';
    }

    // ── State extraction ──────────────────────────────────────────────────────

    function getState() {
        const wire = getWire();
        return {
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
            wireBuyerOn:       wireBuyerActive(),
            phase:             getPhase(),
            availableProjects: getProjects(),
        };
    }

    function getPhase() {
        // Phase 2: compDiv visible; Phase 3: spaceDiv visible
        if (isVisible('spaceDiv'))   return 3;
        if (isVisible('compDiv'))    return 2;
        return 1;
    }

    function getProjects() {
        const projects = [];
        document.querySelectorAll('#projectListTop button, #projectsDiv button').forEach(btn => {
            if (btn.offsetParent === null) return;     // hidden
            if (btn.disabled) return;                  // disabled
            // Greyed-out projects have reduced opacity or a 'greyed' class
            const style = window.getComputedStyle(btn);
            const opacity = parseFloat(style.opacity);
            if (opacity < 0.6) return;                 // visually greyed out
            projects.push(btn.innerText.trim().replace(/\n/g,' '));
        });
        return projects.join(' | ') || 'none';
    }

    // ── Parse project cost from button text ───────────────────────────────────

    function getProjectCost(btn) {
        const text = btn.innerText;
        const opsM   = text.match(/([\d,]+)\s*ops/i);
        const crtM   = text.match(/([\d,]+)\s*creat/i);
        const trstM  = text.match(/\(\s*(\d+)\s*Trust\s*\)/i);
        if (opsM)  return { type: 'ops',       amount: parseInt(opsM[1].replace(/,/g,'')) };
        if (crtM)  return { type: 'creativity', amount: parseInt(crtM[1].replace(/,/g,'')) };
        if (trstM) return { type: 'trust',      amount: parseInt(trstM[1]) };
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
        // ops-cost — production critical, in order of priority
        'improved autoclippers',     // 750 ops — buy immediately when available
        'wirebuyer',                 // 7,000 ops — eliminates wire crises
        'improved wire extrusion',   // 1,750 ops — 50% more wire per spool
        'optimized wire extrusion',  // 3,500 ops — 75% more wire per spool
        'even better autoclippers',  // 2,500 ops — 50% production boost
        'hadwiger clip diagrams',    // 6,000 ops — 500% autoclipper boost
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
        // trust-cost — buy freely, trust regenerates
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

        const opsText = getText('operations') || '';
        const opsParts = opsText.split('/').map(s => parseInt(s.replace(/,/g,'').trim()));
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
        const funds        = getNum('funds');
        const wire         = getWire();
        const wireCost     = getNum('wireCost', 9999);
        const megaCost     = getNum('megaClipperCost', 9999);
        const spoolsLeft   = Math.floor((funds - megaCost) / wireCost);
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

        // EMERGENCY: wire gone and broke
        if (wire <= 0 && funds < wireCost && !wireBuyerActive()) {
            handleEmergency();
            return;
        }

        // 1. Buy wire — skip if WireBuyer is handling it
        if (!wireBuyerActive() && wire < 1000 && funds >= wireCost) {
            if (clickBtn('btnBuyWire') && wire < 100) return; // critically low
        }

        // 2. Manual clicking in early game
        if (autoclippers < 5) {
            clickBtn('btnMakePaperclip');
        }

        // 3. Buy AutoClipper when safe
        const spoolsAfter = Math.floor((funds - clipperCost) / wireCost);
        if (wire > 1000 && spoolsAfter >= 3) {
            if (clickBtn('btnMakeClipper')) {
                console.log(`[AGENT] AutoClipper bought (wire=${wire}, buffer=${spoolsAfter})`);
            }
        }

        // 4. Price management
        if (unsold > 50) {
            clickBtn('btnLowerPrice');
        } else if (unsold < 10 && demand > 100) {
            clickBtn('btnRaisePrice');
        }
    }

    // ── LLM action execution ──────────────────────────────────────────────────

    function executeAction(action, args) {
        console.log(`[AGENT] LLM: ${action}`, args || '');
        switch (action) {
            case 'lower_price':        return clickBtn('btnLowerPrice');
            case 'raise_price':        return clickBtn('btnRaisePrice');
            case 'buy_wire':           return clickBtn('btnBuyWire');
            case 'buy_autoclipper':    return clickBtn('btnMakeClipper');
            case 'buy_megaclipper':    return clickBtn('btnMakeMegaClipper');
            case 'buy_marketing':      return clickBtn('btnExpandMarketing');
            case 'make_paperclip':     return clickBtn('btnMakePaperclip');
            case 'add_processor':      return clickBtn('btnAddProc');
            case 'add_memory':         return clickBtn('btnAddMem');
            case 'buy_project': {
                if (!args || !args.name) return false;
                const name = args.name.toLowerCase();
                const btns = document.querySelectorAll('#projectListTop button, #projectsDiv button');
                for (const btn of btns) {
                    if (btn.innerText.toLowerCase().includes(name) && btn.offsetParent !== null) {
                        btn.click();
                        return true;
                    }
                }
                console.warn(`[AGENT] Project not found: ${args.name}`);
                return false;
            }
            case 'wait':
            default:
                return true;
        }
    }

    // ── Relay communication ───────────────────────────────────────────────────

    function postState() {
        GM_xmlhttpRequest({
            method: 'POST',
            url: `${RELAY}/state`,
            headers: { 'Content-Type': 'application/json' },
            data: JSON.stringify(getState()),
            onerror: () => console.warn('[AGENT] relay state POST failed'),
        });
    }

    function pollAction() {
        GM_xmlhttpRequest({
            method: 'GET',
            url: `${RELAY}/action`,
            onload: (resp) => {
                try {
                    const data = JSON.parse(resp.responseText);
                    if (data && data.action && data.action !== 'wait') {
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
        setInterval(postState,           STATE_MS);
        setInterval(pollAction,          ACTION_MS);

        const badge = document.createElement('div');
        badge.innerText = '🤖 Agent Active';
        badge.style.cssText = `
            position: fixed; bottom: 10px; right: 10px;
            background: #1a1a2e; color: #00ff88;
            font-family: monospace; font-size: 12px;
            padding: 6px 12px; border-radius: 4px;
            border: 1px solid #00ff88; z-index: 9999;
            pointer-events: none;
        `;
        document.body.appendChild(badge);
    }

    window.addEventListener('load', () => setTimeout(init, 1000));

})();
