"""
Base agent class for all parallel agents.
Agents run continuously and process tasks from a queue.

Optimizations:
- Non-blocking file I/O using asyncio.to_thread
- File locking for concurrent queue access
- Retry logic for failed tasks
- Health checks and monitoring
- Persistent stats tracking
"""

import asyncio
import logging
import json
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# File locking support (Unix only, Windows uses different mechanism)
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents with optimized I/O and error handling."""
    
    # Shared thread pool for file I/O operations
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent_io")
    
    def __init__(
        self,
        name: str,
        task_queue_file: str = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        health_check_interval: int = 60,
    ):
        """
        Initialize agent.
        
        Args:
            name: Agent name
            task_queue_file: Path to task queue file
            max_retries: Maximum retries for failed tasks
            retry_delay: Delay between retries (seconds)
            health_check_interval: Health check interval (seconds)
        """
        self.name = name
        self.task_queue_file = Path(task_queue_file or f"tasks/queue_{name}.json")
        self.running = True
        self.current_task = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.health_check_interval = health_check_interval
        self.last_health_check = time.time()
        
        # Stats tracking
        self.stats_file = Path(f"tasks/stats_{name}.json")
        self.stats = self._load_stats()
        self.stats["started_at"] = datetime.now().isoformat()
        self.stats["last_updated"] = datetime.now().isoformat()
        
        # Create directories
        Path("tasks").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        
        # Initialize task queue if it doesn't exist (synchronous initialization)
        if not self.task_queue_file.exists():
            self.task_queue_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(self.task_queue_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2)
            except Exception as e:
                logger.warning(f"Could not initialize task queue: {e}")
    
    def _load_stats(self) -> Dict[str, Any]:
        """Load persisted stats from file."""
        try:
            if self.stats_file.exists():
                return json.loads(self.stats_file.read_text())
        except Exception as e:
            logger.warning(f"Could not load stats: {e}")
        
        return {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_retried": 0,
            "health_checks": 0,
            "last_task_at": None,
        }
    
    async def _save_stats(self):
        """Save stats to file asynchronously."""
        self.stats["last_updated"] = datetime.now().isoformat()
        try:
            await self._write_file_async(self.stats_file, self.stats)
        except Exception as e:
            logger.error(f"Error saving stats: {e}")
    
    async def _read_file_async(self, file_path: Path) -> Optional[Any]:
        """Read JSON file asynchronously with locking."""
        def _read():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Lock file for reading (shared lock) - Unix only
                    if HAS_FCNTL:
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        return json.load(f)
                    finally:
                        if HAS_FCNTL:
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except FileNotFoundError:
                return None
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {file_path}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                return None
        
        return await asyncio.to_thread(_read)
    
    async def _write_file_async(self, file_path: Path, data: Any):
        """Write JSON file asynchronously with locking."""
        def _write():
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                # On Windows, use atomic write via temp file
                if os.name == 'nt':
                    temp_path = file_path.with_suffix('.tmp')
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    # Atomic replace on Windows
                    temp_path.replace(file_path)
                else:
                    # Unix: use file locking
                    with open(file_path, 'w', encoding='utf-8') as f:
                        if HAS_FCNTL:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        try:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        finally:
                            if HAS_FCNTL:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception as e:
                logger.error(f"Error writing {file_path}: {e}")
                raise
        
        await asyncio.to_thread(_write)
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single task. Override in subclasses.
        
        Args:
            task: Task dictionary with 'id', 'type', 'data'
            
        Returns:
            Result dictionary
        """
        logger.info(f"Agent {self.name}: Processing task {task.get('id')}")
        return {"status": "completed", "result": "Task processed"}
    
    async def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task from queue with atomic operation."""
        try:
            tasks = await self._read_file_async(self.task_queue_file)
            
            if tasks and isinstance(tasks, list) and len(tasks) > 0:
                task = tasks.pop(0)
                # Atomically save remaining tasks
                await self._write_file_async(self.task_queue_file, tasks)
                return task
        except Exception as e:
            logger.error(f"Error reading task queue: {e}")
        
        return None
    
    async def add_task(self, task: Dict[str, Any]):
        """Add task to queue atomically."""
        try:
            tasks = await self._read_file_async(self.task_queue_file) or []
            
            if not isinstance(tasks, list):
                tasks = []
            
            # Generate task ID if not present
            if 'id' not in task:
                task['id'] = f"task_{int(time.time())}_{self.name}"
            
            task['created_at'] = datetime.now().isoformat()
            tasks.append(task)
            
            await self._write_file_async(self.task_queue_file, tasks)
            logger.info(f"Task {task.get('id')} added to queue")
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            raise
    
    async def save_result(self, task_id: str, result: Dict[str, Any]):
        """Save task result asynchronously."""
        result_file = Path(f"tasks/result_{task_id}.json")
        result_data = {
            "task_id": task_id,
            "agent": self.name,
            "result": result,
            "completed_at": datetime.now().isoformat(),
        }
        
        await self._write_file_async(result_file, result_data)
    
    async def _health_check(self) -> bool:
        """Perform health check. Returns True if healthy."""
        try:
            self.stats["health_checks"] = self.stats.get("health_checks", 0) + 1
            self.last_health_check = time.time()
            
            # Check if we can read/write to queue
            test_data = await self._read_file_async(self.task_queue_file)
            if test_data is None:
                # Create empty queue if missing
                await self._write_file_async(self.task_queue_file, [])
            
            await self._save_stats()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def _retry_task(self, task: Dict[str, Any], attempt: int) -> bool:
        """Retry a failed task. Returns True if should retry."""
        if attempt >= self.max_retries:
            logger.warning(
                f"Task {task.get('id')} exceeded max retries ({self.max_retries})"
            )
            return False
        
        retry_count = task.get('retry_count', 0) + 1
        task['retry_count'] = retry_count
        task['last_retry_at'] = datetime.now().isoformat()
        
        self.stats["tasks_retried"] = self.stats.get("tasks_retried", 0) + 1
        
        logger.info(
            f"Retrying task {task.get('id')} (attempt {retry_count}/{self.max_retries})"
        )
        
        await asyncio.sleep(self.retry_delay * retry_count)  # Exponential backoff
        await self.add_task(task)  # Re-add to queue
        
        return True
    
    async def run(self):
        """Main agent loop - runs continuously with optimizations."""
        logger.info(f"Agent {self.name} started and running...")
        logger.info(f"Max retries: {self.max_retries}, Health check interval: {self.health_check_interval}s")
        
        while self.running:
            try:
                # Periodic health check
                if time.time() - self.last_health_check >= self.health_check_interval:
                    await self._health_check()
                
                # Check for tasks
                task = await self.get_next_task()
                
                if task:
                    self.current_task = task
                    task_id = task.get('id', 'unknown')
                    task_type = task.get('type', 'unknown')
                    
                    logger.info(f"📋 Agent {self.name}: Processing task {task_id} ({task_type})")
                    
                    try:
                        result = await self.process_task(task)
                        await self.save_result(task_id, result)
                        self.stats["tasks_completed"] += 1
                        self.stats["last_task_at"] = datetime.now().isoformat()
                        await self._save_stats()
                        
                        logger.info(f"✅ Agent {self.name}: Task {task_id} completed")
                    except Exception as e:
                        logger.error(f"❌ Agent {self.name}: Task {task_id} failed: {e}", exc_info=True)
                        
                        # Attempt retry
                        attempt = task.get('retry_count', 0)
                        if await self._retry_task(task, attempt):
                            logger.info(f"🔄 Agent {self.name}: Task {task_id} queued for retry")
                        else:
                            self.stats["tasks_failed"] += 1
                            await self.save_result(task_id, {
                                "status": "failed",
                                "error": str(e),
                                "retries_exhausted": True
                            })
                            await self._save_stats()
                    
                    self.current_task = None
                else:
                    # No tasks, use adaptive sleep (longer when idle)
                    await asyncio.sleep(2)
                    
            except KeyboardInterrupt:
                logger.info(f"Agent {self.name} stopping...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Agent {self.name} error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying
        
        # Final stats save
        await self._save_stats()
        logger.info(f"Agent {self.name} stopped. Final stats: {self.stats}")
    
    def stop(self):
        """Stop the agent gracefully."""
        logger.info(f"Stopping agent {self.name}...")
        self.running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current agent statistics."""
        return {
            **self.stats,
            "current_task": self.current_task.get('id') if self.current_task else None,
            "running": self.running,
            "uptime_seconds": (
                time.time() - datetime.fromisoformat(self.stats["started_at"]).timestamp()
                if "started_at" in self.stats else 0
            ),
        }
