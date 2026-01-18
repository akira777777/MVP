"""
Base agent class for all parallel agents.
Agents run continuously and process tasks from a queue.

Optimizations:
- Non-blocking file I/O using asyncio.to_thread
- File locking for concurrent queue access
- Retry logic for failed tasks
- Health checks and monitoring
- Persistent stats tracking
- Task validation with Pydantic
- Structured error handling
"""

import asyncio
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# File locking support (Unix only, Windows uses different mechanism)
try:
    import fcntl

    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

from agents.models import Task, TaskResult, TaskStatus
from utils.exceptions import TaskTimeoutError, TaskValidationError
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents with optimized I/O and error handling."""

    # Shared thread pool for file I/O operations
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent_io")

    def __init__(
        self,
        name: str,
        task_queue_file: Optional[str] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        health_check_interval: Optional[int] = None,
        enable_validation: Optional[bool] = None,
    ):
        """
        Initialize agent.

        Args:
            name: Agent name (must be non-empty)
            task_queue_file: Path to task queue file (optional, uses config default)
            max_retries: Maximum retries for failed tasks (optional, uses config)
            retry_delay: Delay between retries in seconds (optional, uses config)
            health_check_interval: Health check interval in seconds (optional, uses config)
            enable_validation: Enable Pydantic task validation (optional, uses config)

        Raises:
            ValueError: If validation parameters are invalid
        """
        if not name or not name.strip():
            raise ValueError("Agent name cannot be empty")

        # Use settings defaults if not provided
        cfg = get_settings()
        self.max_retries = (
            max_retries if max_retries is not None else cfg.agent_max_retries
        )
        self.retry_delay = (
            retry_delay if retry_delay is not None else cfg.agent_retry_delay
        )
        self.health_check_interval = (
            health_check_interval
            if health_check_interval is not None
            else cfg.agent_health_check_interval
        )
        self.enable_validation = (
            enable_validation
            if enable_validation is not None
            else cfg.agent_enable_validation
        )

        # Validate parameters
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.retry_delay <= 0:
            raise ValueError("retry_delay must be > 0")
        if self.health_check_interval <= 0:
            raise ValueError("health_check_interval must be > 0")

        self.name = name.strip()
        tasks_dir = cfg.agent_tasks_dir
        self.task_queue_file = Path(
            task_queue_file or f"{tasks_dir}/queue_{self.name}.json"
        )
        self.running = True
        self.current_task: Optional[Task] = None
        self.last_health_check = time.time()

        # Setup logging
        cfg = get_settings()
        setup_logging(
            name=f"agents.{self.name}",
            log_file=f"agent_{self.name}.log",
            log_dir=cfg.agent_logs_dir,
            log_level=cfg.log_level,
        )
        self.logger = logging.getLogger(f"agents.{self.name}")

        # Stats tracking
        self.stats_file = Path(f"{tasks_dir}/stats_{self.name}.json")
        self.stats = self._load_stats()
        self.stats["started_at"] = datetime.utcnow().isoformat() + "Z"
        self.stats["last_updated"] = datetime.utcnow().isoformat() + "Z"

        # Create directories
        Path(tasks_dir).mkdir(exist_ok=True)
        Path(cfg.agent_logs_dir).mkdir(exist_ok=True)

        # Initialize task queue if it doesn't exist (synchronous initialization)
        if not self.task_queue_file.exists():
            self.task_queue_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(self.task_queue_file, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)
            except Exception as e:
                self.logger.warning(f"Could not initialize task queue: {e}")

    def _load_stats(self) -> Dict[str, Any]:
        """Load persisted stats from file."""
        try:
            if self.stats_file.exists():
                return json.loads(self.stats_file.read_text())
        except Exception as e:
            # Use module logger since self.logger may not be initialized yet
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
        self.stats["last_updated"] = datetime.utcnow().isoformat() + "Z"
        try:
            await self._write_file_async(self.stats_file, self.stats)
        except Exception as e:
            self.logger.error(f"Error saving stats: {e}")

    async def _read_file_async(self, file_path: Path) -> Optional[Any]:
        """Read JSON file asynchronously with locking."""

        def _read():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
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
                if os.name == "nt":
                    temp_path = file_path.with_suffix(".tmp")
                    with open(temp_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    # Atomic replace on Windows
                    temp_path.replace(file_path)
                else:
                    # Unix: use file locking
                    with open(file_path, "w", encoding="utf-8") as f:
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

    def _validate_task(self, task_data: Dict[str, Any]) -> Task:
        """
        Validate task data using Pydantic model.

        Args:
            task_data: Raw task dictionary

        Returns:
            Validated Task model

        Raises:
            TaskValidationError: If task validation fails
        """
        if not self.enable_validation:
            # Return a minimal Task if validation is disabled
            return Task(
                id=task_data.get("id", f"task_{int(time.time())}_{self.name}"),
                type=task_data.get("type", "unknown"),
                data=task_data.get("data", {}),
            )

        try:
            return Task(**task_data)
        except Exception as e:
            raise TaskValidationError(f"Task validation failed: {e}") from e

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single task. Override in subclasses.

        Args:
            task: Task dictionary with 'id', 'type', 'data'

        Returns:
            Result dictionary with 'status' and optional 'result'/'error'

        Raises:
            TaskValidationError: If task validation fails
            TaskTimeoutError: If task exceeds timeout
        """
        validated_task = self._validate_task(task)
        self.logger.info(
            f"Processing task {validated_task.id} (type: {validated_task.type})"
        )

        # Default implementation - subclasses should override
        return {
            "status": TaskStatus.COMPLETED.value,
            "result": {"message": "Task processed"},
        }

    async def get_next_task(self) -> Optional[Task]:
        """
        Get next task from queue with atomic operation.

        Returns:
            Validated Task model or None if queue is empty

        Raises:
            TaskValidationError: If task in queue is invalid
        """
        try:
            tasks_data = await self._read_file_async(self.task_queue_file)

            if tasks_data and isinstance(tasks_data, list) and len(tasks_data) > 0:
                task_data = tasks_data.pop(0)

                # Validate task
                try:
                    task = self._validate_task(task_data)
                except TaskValidationError as e:
                    self.logger.error(f"Invalid task in queue: {e}")
                    # Remove invalid task and continue
                    await self._write_file_async(self.task_queue_file, tasks_data)
                    return None

                # Atomically save remaining tasks
                await self._write_file_async(self.task_queue_file, tasks_data)
                return task
        except Exception as e:
            self.logger.error(f"Error reading task queue: {e}", exc_info=True)

        return None

    async def add_task(self, task: Dict[str, Any]) -> Task:
        """
        Add task to queue atomically with validation.

        Args:
            task: Task dictionary (will be validated)

        Returns:
            Validated Task model

        Raises:
            TaskValidationError: If task validation fails
        """
        try:
            # Validate task before adding
            validated_task = self._validate_task(task)

            tasks_data = await self._read_file_async(self.task_queue_file) or []

            if not isinstance(tasks_data, list):
                tasks_data = []

            # Convert Task model to dict for JSON serialization
            task_dict = validated_task.model_dump()
            tasks_data.append(task_dict)

            await self._write_file_async(self.task_queue_file, tasks_data)
            self.logger.info(f"Task {validated_task.id} added to queue")

            return validated_task
        except TaskValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error adding task: {e}", exc_info=True)
            raise

    async def save_result(self, task_id: str, result: Dict[str, Any]):
        """
        Save task result asynchronously with validation.

        Args:
            task_id: Task identifier
            result: Result dictionary (should contain 'status' and optional 'result'/'error')
        """
        result_file = Path(f"tasks/result_{task_id}.json")

        # Create validated result
        try:
            task_result = TaskResult(
                status=result.get("status", TaskStatus.COMPLETED.value),
                agent=self.name,
                task_id=task_id,
                result=result.get("result"),
                error=result.get("error"),
                duration_seconds=result.get("duration_seconds"),
                metadata=result.get("metadata", {}),
            )
            result_data = task_result.model_dump()
        except Exception as e:
            self.logger.warning(f"Could not validate result, saving raw: {e}")
            result_data = {
                "task_id": task_id,
                "agent": self.name,
                "result": result,
                "completed_at": datetime.utcnow().isoformat() + "Z",
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

    async def _handle_task_error(
        self, task: Task, error: Exception, duration: float
    ) -> None:
        """
        Handle task error with retry logic.

        Args:
            task: Failed task
            error: Exception that occurred
            duration: Task processing duration
        """
        attempt = task.retry_count

        if await self._retry_task(task, attempt):
            self.logger.info(f"🔄 Task {task.id} queued for retry")
        else:
            self.stats["tasks_failed"] += 1
            await self.save_result(
                task.id,
                {
                    "status": TaskStatus.FAILED.value,
                    "error": str(error),
                    "duration_seconds": duration,
                    "retries_exhausted": True,
                },
            )
            await self._save_stats()

    async def _retry_task(self, task: Task, attempt: int) -> bool:
        """
        Retry a failed task. Returns True if should retry.

        Args:
            task: Task to retry
            attempt: Current attempt number

        Returns:
            True if task was queued for retry, False if max retries exceeded
        """
        if attempt >= self.max_retries:
            self.logger.warning(
                f"Task {task.id} exceeded max retries ({self.max_retries})"
            )
            return False

        # Update task retry count
        task.retry_count += 1
        task.last_retry_at = datetime.utcnow().isoformat() + "Z"

        self.stats["tasks_retried"] = self.stats.get("tasks_retried", 0) + 1

        self.logger.info(
            f"Retrying task {task.id} (attempt {task.retry_count}/{self.max_retries})"
        )

        # Exponential backoff
        await asyncio.sleep(self.retry_delay * task.retry_count)

        # Re-add to queue
        await self.add_task(task.model_dump())

        return True

    async def run(self):
        """Main agent loop - runs continuously with optimizations."""
        logger.info(f"Agent {self.name} started and running...")
        logger.info(
            f"Max retries: {self.max_retries}, Health check interval: {self.health_check_interval}s"
        )

        while self.running:
            try:
                # Periodic health check
                if time.time() - self.last_health_check >= self.health_check_interval:
                    await self._health_check()

                # Check for tasks
                task = await self.get_next_task()

                if task:
                    self.current_task = task
                    task_id = task.id
                    task_type = task.type
                    start_time = time.time()

                    self.logger.info(
                        f"📋 Processing task {task_id} (type: {task_type}, priority: {task.priority})"
                    )

                    try:
                        # Process with timeout if specified
                        if task.timeout:
                            result = await asyncio.wait_for(
                                self.process_task(task.model_dump()),
                                timeout=task.timeout,
                            )
                        else:
                            result = await self.process_task(task.model_dump())

                        # Calculate duration
                        duration = time.time() - start_time
                        result["duration_seconds"] = duration

                        await self.save_result(task_id, result)
                        self.stats["tasks_completed"] += 1
                        self.stats["last_task_at"] = datetime.utcnow().isoformat() + "Z"
                        await self._save_stats()

                        self.logger.info(
                            f"✅ Task {task_id} completed in {duration:.2f}s"
                        )
                    except asyncio.TimeoutError:
                        duration = time.time() - start_time
                        error_msg = f"Task {task_id} exceeded timeout ({task.timeout}s)"
                        self.logger.error(error_msg)

                        timeout_error = TaskTimeoutError(error_msg)
                        await self._handle_task_error(task, timeout_error, duration)
                    except TaskValidationError as e:
                        duration = time.time() - start_time
                        self.logger.error(f"❌ Task {task_id} validation failed: {e}")
                        await self._handle_task_error(task, e, duration)
                    except Exception as e:
                        duration = time.time() - start_time
                        self.logger.error(
                            f"❌ Task {task_id} failed: {e}", exc_info=True
                        )
                        await self._handle_task_error(task, e, duration)

                    self.current_task = None
                else:
                    # No tasks, use adaptive sleep (longer when idle)
                    await asyncio.sleep(2)

            except KeyboardInterrupt:
                self.logger.info("Stopping agent...")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

        # Final stats save
        await self._save_stats()
        self.logger.info(f"Agent stopped. Final stats: {self.stats}")

    def stop(self) -> None:
        """Stop the agent gracefully."""
        self.logger.info("Stopping agent...")
        self.running = False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current agent statistics.

        Returns:
            Dictionary with agent statistics
        """
        uptime = 0.0
        if "started_at" in self.stats and self.stats["started_at"]:
            try:
                started = datetime.fromisoformat(
                    self.stats["started_at"].replace("Z", "+00:00")
                )
                uptime = (
                    datetime.utcnow() - started.replace(tzinfo=None)
                ).total_seconds()
            except Exception:
                pass

        return {
            **self.stats,
            "current_task": self.current_task.id if self.current_task else None,
            "running": self.running,
            "uptime_seconds": max(0.0, uptime),
        }
