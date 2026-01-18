"""Parallel agents for development workflow."""

# Import agent classes for direct use
from agents.add import AddFeaturesAgent
from agents.architect import ArchitectAgent
from agents.base_agent import BaseAgent
from agents.coder_bot import CoderBotAgent
from agents.coder_db import CoderDBAgent
from agents.config import AgentSettings, get_settings
from agents.devops import DevOpsAgent
from agents.models import AgentStats, Task, TaskResult, TaskStatus, TaskType
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent

__all__ = [
    "ArchitectAgent",
    "CoderBotAgent",
    "CoderDBAgent",
    "TesterAgent",
    "DevOpsAgent",
    "ReviewerAgent",
    "AddFeaturesAgent",
    "BaseAgent",
    "Task",
    "TaskResult",
    "TaskStatus",
    "TaskType",
    "AgentStats",
    "AgentSettings",
    "get_settings",
]
