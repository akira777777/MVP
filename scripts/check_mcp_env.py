#!/usr/bin/env python3
"""
Check MCP server environment variables and provide setup guidance.
"""

import os
import sys
from pathlib import Path


def check_env_var(var_name: str, required: bool = True) -> tuple[bool, str]:
    """Check if environment variable is set."""
    value = os.getenv(var_name)
    if value:
        # Mask sensitive values
        masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
        return True, masked
    return False, ""


def main():
    """Check MCP server environment variables."""
    print("=" * 70)
    print("MCP Server Environment Variables Check")
    print("=" * 70)
    print()

    # Define required environment variables for each server
    servers_config = {
        "github": {
            "var": "GITHUB_TOKEN",
            "required": True,
            "description": "GitHub Personal Access Token",
            "help_url": "https://github.com/settings/tokens",
        },
        "brave-search": {
            "var": "BRAVE_API_KEY",
            "required": False,
            "description": "Brave Search API Key",
            "help_url": "https://brave.com/search/api/",
        },
        "tavily": {
            "var": "TAVILY_API_KEY",
            "required": False,
            "description": "Tavily Search API Key",
            "help_url": "https://tavily.com/",
        },
        "context7": {
            "var": "CONTEXT7_API_KEY",
            "required": False,
            "description": "Context7 API Key",
            "help_url": "https://context7.com/",
        },
        "google-maps-platform-code-assist": {
            "var": "GOOGLE_MAPS_API_KEY",
            "required": False,
            "description": "Google Maps Platform API Key",
            "help_url": "https://console.cloud.google.com/apis/credentials",
        },
    }

    results = {}
    missing_required = []
    missing_optional = []

    for server_name, config in servers_config.items():
        var_name = config["var"]
        is_set, value = check_env_var(var_name, config["required"])

        results[server_name] = {
            "set": is_set,
            "value": value,
            "required": config["required"],
        }

        status = (
            "✅ SET"
            if is_set
            else (
                "❌ MISSING (REQUIRED)"
                if config["required"]
                else "⚠️  MISSING (OPTIONAL)"
            )
        )
        print(f"{server_name:35} {status}")
        if is_set:
            print(f"  Value: {value}")
        else:
            print(f"  Description: {config['description']}")
            print(f"  Get key: {config['help_url']}")
            if config["required"]:
                missing_required.append((server_name, var_name, config))
            else:
                missing_optional.append((server_name, var_name, config))
        print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()

    if missing_required:
        print("🔴 REQUIRED environment variables missing:")
        for server_name, var_name, config in missing_required:
            print(f"  - {var_name} (for {server_name})")
            print(f"    Get it at: {config['help_url']}")
        print()

    if missing_optional:
        print("⚠️  OPTIONAL environment variables missing (servers will be disabled):")
        for server_name, var_name, config in missing_optional:
            print(f"  - {var_name} (for {server_name})")
        print()

    if not missing_required and not missing_optional:
        print("✅ All environment variables are set!")
        print()

    # Instructions
    print("=" * 70)
    print("Setup Instructions")
    print("=" * 70)
    print()

    if missing_required or missing_optional:
        print("To set environment variables on Windows:")
        print()
        print("1. Temporary (current session):")
        print("   set GITHUB_TOKEN=your_token_here")
        print()
        print("2. Permanent (User-level):")
        print("   - Open System Properties > Environment Variables")
        print("   - Add variables to User variables")
        print("   - Restart Cursor after setting")
        print()
        print("3. Or create a .env file in the project root:")
        print("   GITHUB_TOKEN=your_token_here")
        print("   BRAVE_API_KEY=your_key_here")
        print("   # ... etc")
        print()

    print("After setting environment variables:")
    print("1. Restart Cursor completely")
    print("2. Open MCP Servers settings")
    print("3. Click 'Refresh' or 'Reconnect' for each server")
    print("4. Check server status indicators")
    print()

    # Check if .env file exists
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"✅ Found .env file at: {env_file}")
        print("   Note: MCP servers may need environment variables set at system level")
        print("   or in Cursor's environment, not just in .env file")
    else:
        print(f"ℹ️  No .env file found at: {env_file}")
        print("   You can create one for project-level configuration")
    print()

    return 0 if not missing_required else 1


if __name__ == "__main__":
    sys.exit(main())
