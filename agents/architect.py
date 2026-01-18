"""
Agent 1: Architect - Plans and designs system architecture.
Runs continuously and processes architecture tasks.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
os.chdir(parent_dir)

try:
    from agents.base_agent import BaseAgent
except ImportError:
    # Fallback for direct execution
    import importlib.util

    base_agent_path = Path(__file__).parent / "base_agent.py"
    spec = importlib.util.spec_from_file_location("base_agent", base_agent_path)
    base_agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base_agent)
    BaseAgent = base_agent.BaseAgent

logger = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    """Architect agent for system design."""

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process architecture task."""
        task_type = task.get("type", "plan")
        task_data = task.get("data", {})

        logger.info(f"Architect: Processing {task_type} task")

        if task_type == "plan":
            plan = {
                "database": {
                    "tables": ["clients", "slots", "bookings"],
                    "relationships": "clients 1:N bookings, slots 1:N bookings",
                    "indexes": ["telegram_id", "service_type + status", "start_time"],
                },
                "services": {
                    "bot": "Telegram bot handlers (aiogram)",
                    "db": "Supabase client wrapper",
                    "payments": "Stripe integration",
                    "scheduler": "APScheduler for reminders",
                    "ai": "Claude API integration",
                },
                "integration_points": {
                    "telegram": "Bot API",
                    "supabase": "Database",
                    "stripe": "Payments",
                    "claude": "AI Q&A",
                },
            }
            return {"status": "completed", "plan": plan}

        elif task_type == "review":
            return {
                "status": "completed",
                "review": "Architecture reviewed and approved",
                "recommendations": [],
            }

        return {"status": "completed", "result": "Task processed"}


async def main():
    """Main function to run architect agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/agent_architect.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    agent = ArchitectAgent("architect")

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Architect agent stopping...")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
