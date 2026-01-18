# Parallel Agents Workflow Guide

## 🎯 Overview

This project supports **parallel agent development** with:
- **Composer** integration (Ctrl+K)
- **TMUX** agents (20 terminals)
- **Auto-test & deploy** pipeline
- **MCP GitHub** integration

## 🚀 Quick Start (30 seconds)

### 1. Composer Prompts

**In Cursor Composer (Ctrl+K):**

```
@agent1 Architect plan
@agent2 Code handlers
@tester Run Playwright
```

**Parallel spawn:**
```
Spawn 5 agents: 2 coders (bot/db), 1 tester, 1 devops (docker), 1 reviewer.
```

### 2. TMUX Agents (20 Terminals)

```bash
# Setup 20 agent terminals
python tmux_agents_parallel.py setup

# Attach to session
tmux attach -t agents

# List windows
tmux list-windows -t agents
```

### 3. Auto-Deploy

```bash
# Full pipeline: test → build → deploy
python scripts/auto_test_deploy.py
```

## 📋 Agent Types

### 1. Architect (`agents/architect.py`)
- **Task**: System architecture design
- **Output**: Architecture plans, ERD, service boundaries
- **Usage**: `@agent1 Architect plan`

### 2. Coder Bot (`agents/coder_bot.py`)
- **Task**: Implement bot handlers
- **Files**: `bot/handlers.py`, `bot/keyboards.py`
- **Usage**: `@agent2 Code handlers`

### 3. Coder DB (`agents/coder_db.py`)
- **Task**: Database layer implementation
- **Files**: `db/supabase_client.py`
- **Usage**: `@agent3 Code DB`

### 4. Tester (`agents/tester.py`)
- **Task**: E2E testing with Playwright
- **Files**: `tests/test_e2e.py`
- **Usage**: `@tester Run Playwright`

### 5. DevOps (`agents/devops.py`)
- **Task**: Docker & deployment setup
- **Files**: `Dockerfile`, `docker-compose.yml`, `.github/workflows/`
- **Usage**: `@devops Docker setup`

### 6. Reviewer (`agents/reviewer.py`)
- **Task**: Code quality review
- **Tools**: ruff, security scanners
- **Usage**: `@reviewer Review code`

## 🔄 Workflow Examples

### Example 1: Fix Bug

```
Fix bug: overbooking → Apply → @web search GDPR Telegram
```

**Steps:**
1. Identify bug in code
2. Fix in Composer
3. Apply changes (Ctrl+Enter)
4. Research GDPR requirements
5. Update GDPR handler

### Example 2: Add Feature

```
@agent1 Architect: Design recurring appointments feature
@agent2 Code: Implement recurring booking logic
@tester Test: E2E test for recurring appointments
@reviewer Review: Code quality check
```

### Example 3: Full Pipeline

```
1. Code changes in Composer
2. Ctrl+Enter Apply changes
3. Terminal: playwright test
4. Terminal: docker-compose up
5. MCP GitHub: Create PR → Deploy to Vercel
```

## 🛠️ TMUX Agents Setup

### Configuration

Edit `agents_config.json` to customize agent windows:

```json
{
  "windows": {
    "agent_name": {
      "description": "Agent description",
      "command": "python agents/agent_name.py",
      "working_directory": ".",
      "auto_restart": true
    }
  }
}
```

### Available Commands

```bash
# Setup agents
python tmux_agents_parallel.py setup

# List windows
python tmux_agents_parallel.py list

# Interactive mode
python tmux_agents_parallel.py
```

### TMUX Shortcuts

- `Ctrl+B D` - Detach from session
- `Ctrl+B C` - Create new window
- `Ctrl+B N` - Next window
- `Ctrl+B P` - Previous window
- `Ctrl+B ,` - Rename window

## 🤖 MCP GitHub Integration

### Setup

1. Install MCP GitHub server:
```bash
npm install -g @modelcontextprotocol/server-github
```

2. Configure `.kilocode/mcp.json`:
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

### Usage

**Create PR:**
```
MCP GitHub: Create pull request
Title: "Feature: Add recurring appointments"
Base: main
Head: feature/recurring-appointments
```

**Deploy:**
```
MCP GitHub: Trigger Vercel deployment
Environment: production
```

## 🧪 Testing & Deployment

### Manual Testing

```bash
# Run tests
pytest tests/ -v

# Run Playwright
playwright test

# Run linter
ruff check .
```

### Auto-Deploy Pipeline

```bash
python scripts/auto_test_deploy.py
```

**Pipeline Steps:**
1. ✅ Linter (ruff)
2. ✅ Tests (pytest + Playwright)
3. ✅ Docker build
4. ✅ Deploy Docker
5. ✅ Create PR (MCP GitHub)
6. ✅ Deploy Vercel (MCP GitHub)

### GitHub Actions

Automatic on push to `main`:
- Run tests
- Build Docker
- Deploy to Vercel
- Create release

See `.github/workflows/auto_deploy.yml`

## 📝 Composer Prompts Reference

### Short Prompts (Vibe Mode)
- `@agent1 Architect plan`
- `@agent2 Code handlers`
- `@tester Run Playwright`

### Long Prompts (Precise Mode)
- `@agent1 Architect: Design complete system architecture...`
- `@agent2 Code handlers: Implement Telegram bot handlers...`
- `@tester Run Playwright: Create E2E tests...`

See [COMPOSER_PROMPTS.md](COMPOSER_PROMPTS.md) for full reference.

## 🎯 Best Practices

1. **Use parallel agents** for faster development
2. **Short prompts** = creative/vibe mode
3. **Long prompts** = precise/specific mode
4. **Auto-deploy** = CI/CD integration
5. **MCP GitHub** = Automated PR/deploy
6. **TMUX agents** = Persistent development sessions

## 🆘 Troubleshooting

### Agents not running?
- Check Python path: `which python`
- Check dependencies: `pip install -r requirements.txt`
- Check logs: `tail -f agents_session.log`

### TMUX not working?
- Install tmux: `brew install tmux` (macOS) or `apt install tmux` (Linux)
- Check session: `tmux list-sessions`

### MCP GitHub not connecting?
- Check token: `echo $GITHUB_TOKEN`
- Check config: `.kilocode/mcp.json`
- Restart Cursor

## 📚 Additional Resources

- [README.md](README.md) - Full project documentation
- [COMPOSER_PROMPTS.md](COMPOSER_PROMPTS.md) - Composer prompt examples
- [QUICK_START.md](QUICK_START.md) - 30-second setup guide
- [ERD.md](ERD.md) - Database schema documentation
