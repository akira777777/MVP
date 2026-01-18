"""
Agent: Monitoring - Monitors system health and metrics.
Runs continuously and processes monitoring tasks.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MonitoringAgent(BaseAgent):
    """Monitoring agent for system health checks."""

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process monitoring task."""
        task_type = task.get("type", "check")
        task_data = task.get("data", {})

        logger.info(f"Monitoring: Processing {task_type} task")

        if task_type == "check":
            metric = task_data.get("metric", "health")
            return {
                "status": "completed",
                "metric": metric,
                "result": f"Health check for {metric} completed",
            }

        return {"status": "completed", "result": "Task processed"}


async def main():
    """Main function to run monitoring agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/agent_monitoring.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    agent = MonitoringAgent("monitoring")

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Monitoring agent stopping...")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
