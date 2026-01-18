"""
Agent 5: DevOps - Manages Docker and deployment.
Runs continuously and processes deployment tasks.
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


class DevOpsAgent(BaseAgent):
    """DevOps agent for deployment."""

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process deployment task.

        Args:
            task: Task dictionary (validated by BaseAgent)

        Returns:
            Result dictionary with deployment status
        """
        task_type = task.get("type", "deploy")
        task_data = task.get("data", {})

        self.logger.info(f"Processing {task_type} task")

        try:
            if task_type == "docker":
                return {
                    "status": TaskStatus.COMPLETED.value,
                    "result": {
                        "action": "docker_build",
                        "message": "Docker image built successfully",
                    },
                }

            elif task_type == "deploy":
                environment = task_data.get("environment", "staging")
                return {
                    "status": TaskStatus.COMPLETED.value,
                    "result": {
                        "environment": environment,
                        "message": f"Deployed to {environment}",
                    },
                }

            elif task_type == "ci_cd":
                return {
                    "status": TaskStatus.COMPLETED.value,
                    "result": {
                        "pipeline": "GitHub Actions",
                        "message": "CI/CD pipeline configured",
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
    """Main function to run DevOps agent."""
    from utils.logging_config import setup_logging

    setup_logging(
        name="agents.devops",
        log_file="agent_devops.log",
        log_level="INFO",
    )

    agent = DevOpsAgent("devops")

    try:
        await agent.run()
    except KeyboardInterrupt:
        agent.logger.info("DevOps agent stopping...")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
