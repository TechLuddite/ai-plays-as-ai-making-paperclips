# Quick Setup Reference

## First Time

```
# 1. Install Python dependencies
py -m pip install flask requests

# 2. Pull the LLM model
ollama pull qwen2.5

# 3. Install Tampermonkey in Chrome
# https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo

# 4. Install the userscript
# Tampermonkey → Dashboard → + → paste paperclips_bridge.user.js → Ctrl+S
```

## Every Session

```
# Terminal 1
py relay.py

# Terminal 2  
py agent.py

# Then open:
# https://www.decisionproblem.com/paperclips/index2.html
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ollama` not found in cmd | Add `%LOCALAPPDATA%\Programs\Ollama` to PATH |
| Agent says "Relay unreachable" | Make sure `relay.py` is running first |
| No 🤖 badge in game | Check Tampermonkey is enabled for the site |
| LLM keeps returning `wait` | Ollama may be timing out — try `ollama run qwen2.5 "hello"` to verify |
| Wire keeps running out | Prioritize the WireBuyer project (7,000 ops) |
