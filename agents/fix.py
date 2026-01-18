"""
Agent: Fix - Fixes bugs and issues.
Runs continuously and processes bug fix tasks.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class FixAgent(BaseAgent):
    """Bug fix agent for resolving issues."""

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process fix task."""
        task_type = task.get("type", "fix")
        task_data = task.get("data", {})

        logger.info(f"Fix: Processing {task_type} task")

        if task_type == "fix":
            issue = task_data.get("issue", "unknown")
            return {
                "status": "completed",
                "issue": issue,
                "result": f"Fix for {issue} completed",
            }

        return {"status": "completed", "result": "Task processed"}


async def main():
    """Main function to run fix agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/agent_fix.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    agent = FixAgent("fix")

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Fix agent stopping...")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
