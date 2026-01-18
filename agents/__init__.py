"""Parallel agents for development workflow."""

from .architect import architect_plan
from .coder_bot import code_bot_handlers
from .coder_db import code_db_layer
from .tester import run_playwright_tests
from .devops import setup_docker, deploy_to_vercel
from .reviewer import review_code

__all__ = [
    "architect_plan",
    "code_bot_handlers",
    "code_db_layer",
    "run_playwright_tests",
    "setup_docker",
    "deploy_to_vercel",
    "review_code",
]
