"""
Parallel agents coordinator.
Spawns multiple agents to work in parallel on different tasks.

Improvements:
- Task validation with Pydantic
- Timeout handling for agent tasks
- Better error handling and reporting
- Structured logging
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from agents import (
    ArchitectAgent,
    CoderBotAgent,
    CoderDBAgent,
    DevOpsAgent,
    ReviewerAgent,
    TesterAgent,
)
from agents.models import Task, TaskStatus
from utils.exceptions import AgentError, TaskValidationError
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


async def run_agent_task(
    agent_class: type,
    agent_name: str,
    task: Dict[str, Any],
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Run a single task on an agent instance with validation and timeout.

    Args:
        agent_class: Agent class to instantiate
        agent_name: Name for the agent
        task: Task dictionary (will be validated)
        timeout: Optional timeout in seconds

    Returns:
        Result dictionary with status and result/error
    """
    agent = None
    start_time = time.time()

    try:
        # Validate task before processing
        try:
            validated_task = Task(**task)
        except Exception as e:
            logger.error(f"Invalid task data for agent {agent_name}: {e}")
            return {
                "status": TaskStatus.FAILED.value,
                "agent": agent_name,
                "error": f"Task validation failed: {e}",
            }

        agent = agent_class(agent_name)

        # Process with timeout if specified
        if timeout:
            result = await asyncio.wait_for(
                agent.process_task(validated_task.model_dump()), timeout=timeout
            )
        else:
            result = await agent.process_task(validated_task.model_dump())

        duration = time.time() - start_time
        result["duration_seconds"] = duration

        return {
            "status": result.get("status", TaskStatus.COMPLETED.value),
            "agent": agent_name,
            "result": result.get("result"),
            "duration_seconds": duration,
        }
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        logger.error(f"Agent {agent_name} task timeout after {timeout}s")
        return {
            "status": TaskStatus.FAILED.value,
            "agent": agent_name,
            "error": f"Task timeout after {timeout}s",
            "duration_seconds": duration,
        }
    except asyncio.CancelledError:
        duration = time.time() - start_time
        logger.warning(f"Agent {agent_name} task cancelled")
        return {
            "status": TaskStatus.CANCELLED.value,
            "agent": agent_name,
            "duration_seconds": duration,
        }
    except TaskValidationError as e:
        duration = time.time() - start_time
        logger.error(f"Task validation error for agent {agent_name}: {e}")
        return {
            "status": TaskStatus.FAILED.value,
            "agent": agent_name,
            "error": f"Task validation failed: {e}",
            "duration_seconds": duration,
        }
    except AgentError as e:
        duration = time.time() - start_time
        logger.error(f"Agent error for {agent_name}: {e}", exc_info=True)
        return {
            "status": TaskStatus.FAILED.value,
            "agent": agent_name,
            "error": str(e),
            "duration_seconds": duration,
        }
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error running agent {agent_name}: {e}", exc_info=True)
        return {
            "status": TaskStatus.FAILED.value,
            "agent": agent_name,
            "error": str(e),
            "duration_seconds": duration,
        }
    finally:
        # Cleanup agent resources if needed
        if agent and hasattr(agent, "cleanup"):
            try:
                await agent.cleanup()
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up agent {agent_name}: {cleanup_error}")


async def spawn_agents(
    agent_config: Dict[str, bool],
    task_timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Spawn multiple agents in parallel with validation and timeout.

    Args:
        agent_config: Dict mapping agent names to enabled status
        task_timeout: Timeout in seconds for each agent task (default: 300s)

    Returns:
        Results from all agents with status and duration
    """
    tasks: List[asyncio.Task] = []
    results: Dict[str, Any] = {}
    agent_names: List[str] = []

    # Architect
    if agent_config.get("architect", False):
        task = {
            "id": f"architect_task_{int(time.time())}",
            "type": "plan",
            "data": {},
        }
        agent_names.append("architect")
        tasks.append(
            asyncio.create_task(
                run_agent_task(ArchitectAgent, "architect", task, timeout=timeout)
            )
        )

    # Coders
    if agent_config.get("coder_bot", False):
        task = {
            "id": f"coder_bot_task_{int(time.time())}",
            "type": "implement",
            "data": {"handler": "booking"},
        }
        agent_names.append("coder_bot")
        tasks.append(
            asyncio.create_task(
                run_agent_task(CoderBotAgent, "coder_bot", task, timeout=timeout)
            )
        )

    if agent_config.get("coder_db", False):
        task = {
            "id": f"coder_db_task_{int(time.time())}",
            "type": "implement",
            "data": {"operation": "crud"},
        }
        agent_names.append("coder_db")
        tasks.append(
            asyncio.create_task(
                run_agent_task(CoderDBAgent, "coder_db", task, timeout=timeout)
            )
        )

    # Tester
    if agent_config.get("tester", False):
        task = {
            "id": f"tester_task_{int(time.time())}",
            "type": "test",
            "data": {"file": "tests/"},
        }
        agent_names.append("tester")
        tasks.append(
            asyncio.create_task(
                run_agent_task(TesterAgent, "tester", task, timeout=timeout)
            )
        )

    # DevOps
    if agent_config.get("devops", False):
        task = {
            "id": f"devops_task_{int(time.time())}",
            "type": "deploy",
            "data": {"service": "docker"},
        }
        agent_names.append("devops")
        tasks.append(
            asyncio.create_task(
                run_agent_task(DevOpsAgent, "devops", task, timeout=timeout)
            )
        )

    # Reviewer
    if agent_config.get("reviewer", False):
        task = {
            "id": f"reviewer_task_{int(time.time())}",
            "type": "review",
            "data": {"scope": "all"},
        }
        agent_names.append("reviewer")
        tasks.append(
            asyncio.create_task(
                run_agent_task(ReviewerAgent, "reviewer", task, timeout=timeout)
            )
        )

    # Run all tasks in parallel
    logger.info(f"🚀 Spawning {len(tasks)} agents in parallel (timeout: {timeout}s)...")

    if tasks:
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for name, result in zip(agent_names, completed):
            if isinstance(result, Exception):
                logger.error(f"❌ {name}: Error - {result}", exc_info=True)
                results[name] = {
                    "status": TaskStatus.FAILED.value,
                    "agent": name,
                    "error": str(result),
                }
            elif isinstance(result, dict):
                results[name] = result
                status = result.get("status", "unknown")
                duration = result.get("duration_seconds", 0)
                logger.info(f"✅ {name}: {status} (duration: {duration:.2f}s)")
            else:
                # Fallback for unexpected result types
                results[name] = {
                    "status": TaskStatus.FAILED.value,
                    "agent": name,
                    "error": f"Unexpected result type: {type(result)}",
                }
                logger.warning(f"⚠️ {name}: Unexpected result type: {type(result)}")

    return results


async def main() -> None:
    """Main function to spawn all agents."""
    setup_logging(
        name="agents_parallel",
        log_file="agents_parallel.log",
        log_level="INFO",
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

    # Use config defaults for timeout
    results = await spawn_agents(config)

    print("\n" + "=" * 50)
    print("AGENT RESULTS SUMMARY")
    print("=" * 50)
    for agent, result in results.items():
        print(f"\n{agent.upper()}:")
        if isinstance(result, dict):
            status = result.get("status", TaskStatus.COMPLETED.value)
            print(f"  Status: {status}")
            if "error" in result:
                print(f"  Error: {result['error']}")
            if "result" in result:
                print(f"  Result: {result['result']}")
            if "duration_seconds" in result:
                print(f"  Duration: {result['duration_seconds']:.2f}s")
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
