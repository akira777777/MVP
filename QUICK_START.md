# Quick Start Guide - 30 Seconds Setup

## 1. Project Setup

```bash
# Clone/open project
cd telegram-beauty-salon-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

## 2. Database Setup

1. Create Supabase project (free tier)
2. Run SQL from README.md in Supabase SQL Editor
3. Update `.env` with Supabase credentials

## 3. Run Bot

```bash
python bot.py
```

## 4. Parallel Agents (Optional)

### Composer (Ctrl+K)
```
@agent1 Architect plan
@agent2 Code handlers
@tester Run Playwright
```

### TMUX Agents
```bash
python tmux_agents_parallel.py setup
tmux attach -t agents
```

### Auto-Deploy
```bash
python scripts/auto_test_deploy.py
```

## 5. MCP GitHub Setup

1. Install MCP GitHub server
2. Configure `.kilocode/mcp.json`
3. Use: `MCP GitHub: Create PR → Deploy`

## That's It! 🎉

Your bot is running and ready for parallel agent development.
