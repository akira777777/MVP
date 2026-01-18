"""
Agent configuration using environment variables and Pydantic Settings.
Provides centralized configuration management for all agents.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Agent configuration from environment variables."""
    
    # Base agent settings
    agent_max_retries: int = 3
    agent_retry_delay: float = 5.0
    agent_health_check_interval: int = 60
    agent_enable_validation: bool = True
    agent_task_timeout: float = 300.0  # 5 minutes default
    
    # Task queue settings
    agent_tasks_dir: str = "tasks"
    agent_logs_dir: str = "logs"
    
    # Parallel agents settings
    parallel_task_timeout: float = 300.0
    parallel_max_concurrent: int = 10
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        case_sensitive=False,
        extra="ignore",
    )
    
    @classmethod
    def from_env(cls) -> "AgentSettings":
        """Create settings from environment variables."""
        return cls()


# Global settings instance
_settings: Optional[AgentSettings] = None


def get_settings() -> AgentSettings:
    """
    Get agent settings singleton.
    
    Returns:
        AgentSettings instance
    """
    global _settings
    if _settings is None:
        _settings = AgentSettings.from_env()
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (useful for testing)."""
    global _settings
    _settings = None
