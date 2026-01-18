"""
Agent 4: Tester - Runs Playwright E2E tests.
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_playwright_tests():
    """
    Tester agent: Runs Playwright E2E tests.

    Tests:
    - Booking flow
    - Payment flow
    - Reminder system
    - GDPR consent
    - AI Q&A
    - Edge cases
    """
    logger.info("🧪 Tester: Running Playwright E2E tests...")

    try:
        # Run pytest with Playwright
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("✅ Tester: All tests passed")
            return {"status": "passed", "output": result.stdout}
        else:
            logger.error(f"❌ Tester: Tests failed\n{result.stderr}")
            return {"status": "failed", "output": result.stderr}

    except Exception as e:
        logger.error(f"❌ Tester: Error running tests: {e}")
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_playwright_tests())
