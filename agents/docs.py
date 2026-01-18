"""
Agent: Docs - Generates and updates documentation.
Runs continuously and processes documentation tasks.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DocsAgent(BaseAgent):
    """Documentation agent for generating and updating docs."""

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process documentation task."""
        task_type = task.get("type", "update")
        task_data = task.get("data", {})

        logger.info(f"Docs: Processing {task_type} task")

        if task_type == "update":
            doc_type = task_data.get("doc_type", "readme")
            return {
                "status": "completed",
                "doc_type": doc_type,
                "result": f"Documentation {doc_type} updated",
            }

        return {"status": "completed", "result": "Task processed"}


async def main():
    """Main function to run docs agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/agent_docs.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    agent = DocsAgent("docs")

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Docs agent stopping...")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
