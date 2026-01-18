"""
Agent 6: Code Reviewer - Reviews code quality and best practices.
"""

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def review_code():
    """
    Reviewer agent: Reviews code quality.

    Checks:
    - Code style (ruff/flake8)
    - Type hints
    - Error handling
    - Security issues
    - Best practices
    """
    logger.info("👀 Reviewer: Reviewing code quality...")

    try:
        # Run ruff linter
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", ".", "--output-format=github"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )

        issues = []
        if result.stdout:
            issues = result.stdout.strip().split("\n")

        if result.returncode == 0:
            logger.info("✅ Reviewer: No linting issues found")
            return {"status": "passed", "issues": []}
        else:
            logger.warning(f"⚠️ Reviewer: Found {len(issues)} issues")
            return {"status": "issues", "issues": issues}

    except Exception as e:
        logger.error(f"❌ Reviewer: Error reviewing code: {e}")
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    review_code()
