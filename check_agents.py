"""
Quick script to check if agents are running by checking their logs.
"""

from pathlib import Path

def check_agents():
    """Check which agents are running based on log activity."""
    logs_dir = Path("logs")

    if not logs_dir.exists():
        print("No logs directory found. Run 'py tmux_agents_parallel_windows.py setup' first.")
        return

    print("Checking agent status from logs...\n")

    agents = [
        "architect", "coder_bot_1", "coder_bot_2", "coder_db_1", "coder_db_2",
        "tester_1", "tester_2", "tester_3", "devops_1", "devops_2",
        "reviewer_1", "reviewer_2", "fix_overbooking", "fix_gdpr", "optimize_db",
        "add_features", "monitoring", "docs", "migration", "deploy"
    ]

    running = []
    stopped = []

    for agent in agents:
        log_file = logs_dir / f"agent_{agent}.log"

        if log_file.exists():
            try:
                # Read last few lines
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        # Check if it contains "started and running"
                        if "started and running" in last_line.lower():
                            running.append(agent)
                        else:
                            stopped.append(agent)
                    else:
                        stopped.append(agent)
            except Exception:
                stopped.append(agent)
        else:
            stopped.append(agent)

    print(f"✅ Running agents ({len(running)}/20):")
    for agent in running:
        print(f"   • {agent}")

    if stopped:
        print(f"\n⚠️ Stopped agents ({len(stopped)}):")
        for agent in stopped[:5]:  # Show first 5
            print(f"   • {agent}")
        if len(stopped) > 5:
            print(f"   ... and {len(stopped) - 5} more")

    print(f"\n📊 Summary: {len(running)}/20 agents running")
    print("\n💡 To add tasks, edit files in tasks/queue_<agent_name>.json")
    print("💡 To view logs: type logs\\agent_<name>.log")

if __name__ == "__main__":
    check_agents()
