# Quick Start Guide - Optimized Setup

## 1. Project Setup

### Windows (Command Prompt / PowerShell)

```cmd
# Clone/open project
cd telegram-beauty-salon-bot

# Option 1: Use setup script (recommended)
setup_env.bat

# Option 2: Manual setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Windows (Git Bash)

```bash
# Clone/open project
cd telegram-beauty-salon-bot

# Option 1: Use setup script (recommended)
bash setup_env.sh

# Option 2: Manual setup
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

### Linux/macOS

```bash
# Clone/open project
cd telegram-beauty-salon-bot

# Option 1: Use setup script (recommended)
bash setup_env.sh

# Option 2: Manual setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Note:**

- If `python` command doesn't work, try `py` (Windows Python Launcher) or `python3`
- **Python 3.14 users:**
  - Ensure pip is up-to-date: `python -m pip install --upgrade pip setuptools wheel`
  - Project uses `aiogram>=3.16.0` and `pydantic>=2.10.0` for Python 3.14 compatibility
- **Recommended:** Use Python 3.11 or 3.12 for best compatibility (as specified in Dockerfile)

## 2. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
# Required variables:
# - BOT_TOKEN (from @BotFather)
# - SUPABASE_URL and SUPABASE_KEY
# - STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY
# - CLAUDE_API_KEY
```

## 3. Database Setup

1. Create Supabase project (free tier at supabase.com)
2. Run SQL from README.md in Supabase SQL Editor
3. Update `.env` with your Supabase credentials

## 4. Run Bot

```bash
# Start the bot
python bot.py

# Or with Docker
docker-compose up -d
```

## 5. Parallel Agents (Optional)

### Windows Agents Manager (Recommended)

```bash
# Setup 20 parallel agent processes
py tmux_agents_parallel_windows.py setup

# List all agents and their status
py tmux_agents_parallel_windows.py list

# Health check (auto-restarts failed agents)
py tmux_agents_parallel_windows.py health

# Stop all agents
py tmux_agents_parallel_windows.py stop
```

**Features:**

- ✅ Config-driven agent definitions (`agents_config.json`)
- ✅ Health monitoring and auto-restart
- ✅ Process lifecycle management
- ✅ Structured logging

### Composer Integration (Ctrl+K)

```
@agent1 Architect plan
@agent2 Code handlers
@tester Run Playwright
```

### Linux/macOS TMUX Agents

```bash
python tmux_agents_parallel.py setup
tmux attach -t agents
```

## 6. Agent Configuration

Edit `agents_config.json` to customize:

- Agent scripts and descriptions
- Auto-restart settings
- Health check intervals
- Max restart attempts

## 7. Task Management

Agents process tasks from JSON queues:

```bash
# Add task to agent queue
# Edit: tasks/queue_<agent_name>.json
[
  {
    "id": "task_1234567890",
    "type": "plan",
    "data": {"description": "Design booking system"}
  }
]

# View results
cat tasks/result_task_1234567890.json
```

## 8. Monitoring & Logs

```bash
# View agent logs
type logs\agent_<name>.log  # Windows
cat logs/agent_<name>.log    # Linux/macOS

# View manager log
type logs\agents_manager.log
```

## 9. Auto-Deploy

```bash
# Run full pipeline: test → build → deploy
python scripts/auto_test_deploy.py
```

## 10. MCP GitHub Setup

1. Install MCP GitHub server
2. Configure `.kilocode/mcp.json`
3. Use: `MCP GitHub: Create PR → Deploy`

## Troubleshooting

### Agents not starting?

- Check Python path: `python --version` (requires 3.11+)
- Verify script exists: `ls agents/<name>.py`
- Check logs: `logs/agents_manager.log`

### Health check fails?

- Run: `py tmux_agents_parallel_windows.py health`
- Check process status: `py tmux_agents_parallel_windows.py list`
- Review agent logs for errors

### Tasks not processing?

- Verify queue file exists: `tasks/queue_<agent_name>.json`
- Check JSON format is valid
- Ensure agent process is running

## That's It! 🎉

Your bot is running with optimized parallel agent development support.

**Key Improvements:**

- ✅ Non-blocking async I/O for better performance
- ✅ File locking for concurrent queue access
- ✅ Automatic retry logic for failed tasks
- ✅ Health monitoring and auto-restart
- ✅ Config-driven agent management
- ✅ Structured logging with rotation
