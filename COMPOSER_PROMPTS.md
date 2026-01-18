# Composer Prompts for Parallel Agents

## Quick Prompts (Vibe Mode)

### Single Agent Tasks
```
@agent1 Architect plan
@agent2 Code handlers
@tester Run Playwright
```

### Parallel Spawn
```
Spawn 5 agents: 2 coders (bot/db), 1 tester, 1 devops (docker), 1 reviewer.
```

## Detailed Prompts (Precise Mode)

### Architect Agent
```
@agent1 Architect: Design complete system architecture for Telegram beauty salon bot.
Include: Database schema (ERD), API structure, service boundaries, integration points.
Output: Architecture document with diagrams.
```

### Coder Agents
```
@agent2 Code handlers: Implement Telegram bot handlers for booking flow.
Include: FSM states, inline keyboards, error handling, edge cases.
Files: bot/handlers.py, bot/states.py, bot/keyboards.py

@agent3 Code DB: Implement Supabase database layer.
Include: CRUD operations, query optimization, transaction handling.
Files: db/supabase_client.py
```

### Tester Agent
```
@tester Run Playwright: Create E2E tests for complete booking flow.
Test: Book → Pay → Reminder → Cancel
Files: tests/test_e2e.py
```

### DevOps Agent
```
@devops Docker: Setup Docker configuration and CI/CD.
Include: Dockerfile, docker-compose.yml, GitHub Actions, Vercel deployment.
```

### Reviewer Agent
```
@reviewer Review: Check code quality, security, best practices.
Tools: ruff, mypy, security scanners.
```

## Iterative Fixes

### Fix Bug
```
Fix bug: overbooking → Apply → @web search GDPR Telegram
```

### Research & Fix
```
@web search GDPR Telegram bot requirements
Apply findings to GDPR consent handler
```

## Auto-Deploy Prompts

### Test & Deploy
```
Ctrl+Enter Apply changes
Terminal: playwright test / docker up
MCP GitHub: Create PR → Deploy to Vercel
```

### Full Pipeline
```
Run: python scripts/auto_test_deploy.py
On success: Create PR via MCP GitHub
Deploy: Vercel via MCP
```

## TMUX Integration

### Setup 20 Agents
```bash
python tmux_agents_parallel.py setup
```

### Individual Agent Tasks
Each tmux window runs:
```bash
cursor --chat "Task X"
```

## MCP GitHub Integration

### Create PR
```
MCP GitHub: Create pull request
Title: "Feature: Add recurring appointments"
Base: main
Head: feature/recurring-appointments
```

### Deploy to Vercel
```
MCP GitHub: Trigger deployment
Service: Vercel
Environment: production
```

## Tips

1. **Short prompts** = Vibe mode (freerun, creative)
2. **Long prompts** = Precise mode (detailed, specific)
3. **Parallel agents** = Faster development
4. **Auto-deploy** = CI/CD integration
5. **MCP GitHub** = Automated PR/deploy
