"""
Parallel agents coordinator.
Spawns multiple agents to work in parallel on different tasks.
"""

import asyncio
import logging
from typing import Dict, List

from agents import (
    architect_plan,
    code_bot_handlers,
    code_db_layer,
    run_playwright_tests,
    setup_docker,
    review_code,
)

logger = logging.getLogger(__name__)


async def spawn_agents(agent_config: Dict[str, bool]) -> Dict[str, any]:
    """
    Spawn multiple agents in parallel.
    
    Args:
        agent_config: Dict mapping agent names to enabled status
        
    Returns:
        Results from all agents
    """
    tasks = []
    results = {}
    
    # Architect
    if agent_config.get("architect", False):
        tasks.append(("architect", architect_plan()))
    
    # Coders
    if agent_config.get("coder_bot", False):
        tasks.append(("coder_bot", asyncio.to_thread(code_bot_handlers)))
    
    if agent_config.get("coder_db", False):
        tasks.append(("coder_db", asyncio.to_thread(code_db_layer)))
    
    # Tester
    if agent_config.get("tester", False):
        tasks.append(("tester", run_playwright_tests()))
    
    # DevOps
    if agent_config.get("devops", False):
        tasks.append(("devops", asyncio.to_thread(setup_docker)))
    
    # Reviewer
    if agent_config.get("reviewer", False):
        tasks.append(("reviewer", asyncio.to_thread(review_code)))
    
    # Run all tasks in parallel
    logger.info(f"🚀 Spawning {len(tasks)} agents in parallel...")
    
    if tasks:
        task_names, coros = zip(*tasks)
        completed = await asyncio.gather(*coros, return_exceptions=True)
        
        for name, result in zip(task_names, completed):
            if isinstance(result, Exception):
                logger.error(f"❌ {name}: Error - {result}")
                results[name] = {"status": "error", "error": str(result)}
            else:
                results[name] = result
                logger.info(f"✅ {name}: Completed")
    
    return results


async def main():
    """Main function to spawn all agents."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Spawn 5 agents: 2 coders, 1 tester, 1 devops, 1 reviewer
    config = {
        "architect": False,  # Already done
        "coder_bot": True,
        "coder_db": True,
        "tester": True,
        "devops": True,
        "reviewer": True,
    }
    
    results = await spawn_agents(config)
    
    print("\n" + "="*50)
    print("AGENT RESULTS SUMMARY")
    print("="*50)
    for agent, result in results.items():
        print(f"\n{agent.upper()}:")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status', 'completed')}")
        else:
            print(f"  Result: {result}")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
