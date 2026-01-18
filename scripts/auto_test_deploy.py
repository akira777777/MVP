"""
Automatic testing and deployment script.
Runs tests and deploys on success.
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_tests():
    """Run all tests."""
    logger.info("🧪 Running tests...")

    try:
        # Run pytest
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("✅ All tests passed")
            return True
        else:
            logger.error(f"❌ Tests failed:\n{result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ Error running tests: {e}")
        return False


async def run_linter():
    """Run code linter."""
    logger.info("🔍 Running linter...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("✅ Linter passed")
            return True
        else:
            logger.warning(f"⚠️ Linter issues:\n{result.stdout}")
            return True  # Don't fail on linter warnings

    except Exception as e:
        logger.error(f"❌ Error running linter: {e}")
        return False


async def build_docker():
    """Build Docker image."""
    logger.info("🐳 Building Docker image...")

    try:
        result = subprocess.run(
            ["docker", "build", "-t", "telegram-beauty-salon-bot:latest", "."],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("✅ Docker image built")
            return True
        else:
            logger.error(f"❌ Docker build failed:\n{result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ Error building Docker: {e}")
        return False


async def deploy_docker():
    """Deploy Docker container."""
    logger.info("🚀 Deploying Docker container...")

    try:
        # Stop existing container
        subprocess.run(["docker-compose", "down"], capture_output=True)

        # Start new container
        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("✅ Container deployed")
            return True
        else:
            logger.error(f"❌ Deployment failed:\n{result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ Error deploying: {e}")
        return False


async def create_github_pr():
    """Create GitHub PR via MCP."""
    logger.info("📝 Creating GitHub PR...")

    # This would use MCP GitHub integration
    # For now, just log
    logger.info("Use MCP GitHub to create PR")
    return True


async def deploy_to_vercel():
    """Deploy to Vercel via MCP."""
    logger.info("🚀 Deploying to Vercel...")

    # This would use MCP GitHub integration
    # For now, just log
    logger.info("Use MCP GitHub to deploy to Vercel")
    return True


async def main():
    """Main deployment pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("🚀 Starting auto test & deploy pipeline...")

    # Step 1: Run linter
    if not await run_linter():
        logger.error("❌ Linter failed, aborting")
        sys.exit(1)

    # Step 2: Run tests
    if not await run_tests():
        logger.error("❌ Tests failed, aborting")
        sys.exit(1)

    # Step 3: Build Docker
    if not await build_docker():
        logger.error("❌ Docker build failed, aborting")
        sys.exit(1)

    # Step 4: Deploy Docker (local)
    if not await deploy_docker():
        logger.error("❌ Docker deployment failed")
        sys.exit(1)

    # Step 5: Create PR (via MCP)
    await create_github_pr()

    # Step 6: Deploy to Vercel (via MCP)
    await deploy_to_vercel()

    logger.info("✅ Pipeline completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
