"""
Parallel agents coordinator.
Spawns multiple agents to work in parallel on different tasks.
"""

import asyncio
import logging
from typing import Any, Dict, List

from agents import (
    ArchitectAgent,
    CoderBotAgent,
    CoderDBAgent,
    DevOpsAgent,
    ReviewerAgent,
    TesterAgent,
)

logger = logging.getLogger(__name__)


async def run_agent_task(
    agent_class: type, agent_name: str, task: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run a single task on an agent instance.

    Args:
        agent_class: Agent class to instantiate
        agent_name: Name for the agent
        task: Task dictionary

    Returns:
        Result dictionary with status and result/error
    """
    agent = None
    try:
        agent = agent_class(agent_name)
        result = await agent.process_task(task)
        return {"status": "completed", "agent": agent_name, "result": result}
    except asyncio.CancelledError:
        logger.warning(f"Agent {agent_name} task cancelled")
        return {"status": "cancelled", "agent": agent_name}
    except ValueError as e:
        logger.error(f"Invalid task data for agent {agent_name}: {e}", exc_info=True)
        return {"status": "error", "agent": agent_name, "error": f"Invalid data: {e}"}
    except Exception as e:
        logger.error(f"Error running agent {agent_name}: {e}", exc_info=True)
        return {"status": "error", "agent": agent_name, "error": str(e)}
    finally:
        # Cleanup agent resources if needed
        if agent and hasattr(agent, "cleanup"):
            try:
                await agent.cleanup()
            except Exception as cleanup_error:
                logger.warning(
                    f"Error cleaning up agent {agent_name}: {cleanup_error}"
                )


async def spawn_agents(agent_config: Dict[str, bool]) -> Dict[str, Any]:
    """
    Spawn multiple agents in parallel.

    Args:
        agent_config: Dict mapping agent names to enabled status

    Returns:
        Results from all agents
    """
    tasks: List[asyncio.Task] = []
    results: Dict[str, Any] = {}

    # Architect
    if agent_config.get("architect", False):
        task = {"id": "architect_task_1", "type": "plan", "data": {}}
        tasks.append(
            asyncio.create_task(run_agent_task(ArchitectAgent, "architect", task))
        )

    # Coders
    if agent_config.get("coder_bot", False):
        task = {
            "id": "coder_bot_task_1",
            "type": "implement",
            "data": {"handler": "booking"},
        }
        tasks.append(
            asyncio.create_task(run_agent_task(CoderBotAgent, "coder_bot", task))
        )

    if agent_config.get("coder_db", False):
        task = {
            "id": "coder_db_task_1",
            "type": "implement",
            "data": {"operation": "crud"},
        }
        tasks.append(
            asyncio.create_task(run_agent_task(CoderDBAgent, "coder_db", task))
        )

    # Tester
    if agent_config.get("tester", False):
        task = {"id": "tester_task_1", "type": "test", "data": {"file": "tests/"}}
        tasks.append(asyncio.create_task(run_agent_task(TesterAgent, "tester", task)))

    # DevOps
    if agent_config.get("devops", False):
        task = {"id": "devops_task_1", "type": "setup", "data": {"service": "docker"}}
        tasks.append(asyncio.create_task(run_agent_task(DevOpsAgent, "devops", task)))

    # Reviewer
    if agent_config.get("reviewer", False):
        task = {"id": "reviewer_task_1", "type": "review", "data": {"scope": "all"}}
        tasks.append(
            asyncio.create_task(run_agent_task(ReviewerAgent, "reviewer", task))
        )

    # Run all tasks in parallel
    logger.info(f"🚀 Spawning {len(tasks)} agents in parallel...")

    if tasks:
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        # Build agent names list in the same order as tasks were added
        agent_names = []
        if agent_config.get("architect", False):
            agent_names.append("architect")
        if agent_config.get("coder_bot", False):
            agent_names.append("coder_bot")
        if agent_config.get("coder_db", False):
            agent_names.append("coder_db")
        if agent_config.get("tester", False):
            agent_names.append("tester")
        if agent_config.get("devops", False):
            agent_names.append("devops")
        if agent_config.get("reviewer", False):
            agent_names.append("reviewer")

        for name, result in zip(agent_names, completed):
            if isinstance(result, Exception):
                logger.error(f"❌ {name}: Error - {result}", exc_info=True)
                results[name] = {"status": "error", "error": str(result)}
            elif isinstance(result, dict):
                results[name] = result
                status = result.get("status", "unknown")
                logger.info(f"✅ {name}: {status}")
            else:
                # Fallback for unexpected result types
                results[name] = {"status": "unknown", "result": str(result)}
                logger.warning(f"⚠️ {name}: Unexpected result type: {type(result)}")

    return results


async def main() -> None:
    """Main function to spawn all agents."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Spawn agents: 2 coders, 1 tester, 1 devops, 1 reviewer
    config: Dict[str, bool] = {
        "architect": False,  # Already done
        "coder_bot": True,
        "coder_db": True,
        "tester": True,
        "devops": True,
        "reviewer": True,
    }

    results = await spawn_agents(config)

    print("\n" + "=" * 50)
    print("AGENT RESULTS SUMMARY")
    print("=" * 50)
    for agent, result in results.items():
        print(f"\n{agent.upper()}:")
        if isinstance(result, dict):
            status = result.get("status", "completed")
            print(f"  Status: {status}")
            if "error" in result:
                print(f"  Error: {result['error']}")
            if "result" in result:
                print(f"  Result: {result['result']}")
        else:
            print(f"  Result: {result}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agents coordinator interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in agents coordinator: {e}", exc_info=True)
        raise
