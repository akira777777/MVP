"""
Pydantic models for agent task validation and type safety.
Provides structured task definitions with validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskType(str, Enum):
    """Common task types across agents."""

    PLAN = "plan"
    IMPLEMENT = "implement"
    REVIEW = "review"
    TEST = "test"
    DEPLOY = "deploy"
    OPTIMIZE = "optimize"
    FIX = "fix"
    DOCUMENT = "document"
    MONITOR = "monitor"
    MIGRATE = "migrate"


class Task(BaseModel):
    """
    Validated task model for agent processing.

    Ensures all tasks have required fields and valid structure.
    """

    id: str = Field(..., description="Unique task identifier")
    type: str = Field(..., description="Task type (plan, implement, test, etc.)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Task-specific data")
    created_at: Optional[str] = Field(default=None, description="ISO datetime string")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    last_retry_at: Optional[str] = Field(
        default=None, description="Last retry timestamp"
    )
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1-10)")
    timeout: Optional[float] = Field(
        default=None, gt=0, description="Task timeout in seconds"
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def set_created_at(cls, v: Optional[str]) -> str:
        """Set created_at to current time if not provided."""
        if v is None:
            return datetime.utcnow().isoformat() + "Z"
        return v

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate task ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Task ID cannot be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate task type is not empty."""
        if not v or not v.strip():
            raise ValueError("Task type cannot be empty")
        return v.strip().lower()

    class Config:
        """Pydantic config."""

        use_enum_values = True
        extra = "forbid"  # Reject unknown fields


class TaskResult(BaseModel):
    """
    Standardized task result model.

    All agents should return results in this format.
    """

    status: TaskStatus = Field(..., description="Task status")
    agent: str = Field(..., description="Agent name that processed the task")
    task_id: str = Field(..., description="Original task ID")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Task result data"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    duration_seconds: Optional[float] = Field(
        default=None, ge=0, description="Processing duration"
    )
    completed_at: Optional[str] = Field(
        default=None, description="Completion timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("completed_at", mode="before")
    @classmethod
    def set_completed_at(cls, v: Optional[str], info) -> str:
        """Set completed_at to current time if not provided and status is completed."""
        if v is None and info.data.get("status") == TaskStatus.COMPLETED:
            return datetime.utcnow().isoformat() + "Z"
        return v

    class Config:
        """Pydantic config."""

        use_enum_values = True


class AgentStats(BaseModel):
    """Agent statistics model."""

    tasks_completed: int = Field(default=0, ge=0)
    tasks_failed: int = Field(default=0, ge=0)
    tasks_retried: int = Field(default=0, ge=0)
    health_checks: int = Field(default=0, ge=0)
    last_task_at: Optional[str] = Field(default=None)
    started_at: Optional[str] = Field(default=None)
    last_updated: Optional[str] = Field(default=None)
    current_task: Optional[str] = Field(default=None)
    running: bool = Field(default=True)
    uptime_seconds: float = Field(default=0.0, ge=0)

    class Config:
        """Pydantic config."""

        extra = "allow"  # Allow additional stats fields
