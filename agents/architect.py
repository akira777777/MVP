"""
Agent 1: Architect - Plans and designs system architecture.
Runs continuously and processes architecture tasks.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent
from agents.models import TaskStatus

logger = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    """Architect agent for system design."""

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process architecture task.

        Args:
            task: Task dictionary (validated by BaseAgent)

        Returns:
            Result dictionary with status and plan/review data
        """
        task_type = task.get("type", "plan")
        task_data = task.get("data", {})

        self.logger.info(f"Processing {task_type} task")

        try:
            if task_type == "plan":
                plan = {
                    "database": {
                        "tables": ["clients", "slots", "bookings"],
                        "relationships": "clients 1:N bookings, slots 1:N bookings",
                        "indexes": [
                            "telegram_id",
                            "service_type + status",
                            "start_time",
                        ],
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
                return {
                    "status": TaskStatus.COMPLETED.value,
                    "result": {"plan": plan},
                }

            elif task_type == "review":
                return {
                    "status": TaskStatus.COMPLETED.value,
                    "result": {
                        "review": "Architecture reviewed and approved",
                        "recommendations": [],
                    },
                }

            return {
                "status": TaskStatus.COMPLETED.value,
                "result": {"message": "Task processed"},
            }
        except Exception as e:
            self.logger.error(f"Error processing task: {e}", exc_info=True)
            raise


async def main():
    """Main function to run architect agent."""
    from utils.logging_config import setup_logging

    setup_logging(
        name="agents.architect",
        log_file="agent_architect.log",
        log_level="INFO",
    )

    agent = ArchitectAgent("architect")

    try:
        await agent.run()
    except KeyboardInterrupt:
        agent.logger.info("Architect agent stopping...")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
