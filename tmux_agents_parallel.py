"""
Enhanced TMUX agents manager for parallel agent execution.
Manages 20 terminals, each running a Cursor chat agent.
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path
import json

class ParallelAgentsManager:
    def __init__(self, config_path: str = "agents_config.json"):
        """Initialize parallel agents manager."""
        self.processes = {}
        self.session_name = "agents"
        self.config_path = config_path
        self.load_config()
    
    def load_config(self):
        """Load agent configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {
                "session_name": "agents",
                "windows": {},
                "global_settings": {
                    "log_file": "agents_session.log",
                    "pid_file": "agents_session.pid",
                    "auto_save_config": True
                }
            }
    
    def create_agent_window(self, name: str, task: str, cwd: str = None):
        """
        Create a tmux window for an agent.
        
        Args:
            name: Window name
            task: Task description for Cursor chat
            cwd: Working directory
        """
        print(f"Creating agent window '{name}' with task: {task}")
        
        # Command to run Cursor chat with task
        # Note: This assumes cursor CLI is available
        # Adjust based on your Cursor setup
        command = f'cursor --chat "{task}"'
        
        # Alternative: Run Python agent script
        agent_script = f"python agents/{name}.py" if Path(f"agents/{name}.py").exists() else None
        
        if agent_script:
            command = agent_script
        
        try:
            # Create tmux window
            tmux_cmd = [
                "tmux", "new-window",
                "-t", self.session_name,
                "-n", name,
                "-d",
                command
            ]
            
            if cwd:
                tmux_cmd.extend(["-c", cwd])
            
            result = subprocess.run(
                tmux_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✅ Agent window '{name}' created")
                return True
            else:
                print(f"❌ Failed to create window '{name}': {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating agent window '{name}': {e}")
            return False
    
    def setup_parallel_agents(self):
        """Setup 20 parallel agent terminals."""
        print(f"🚀 Setting up parallel agents session '{self.session_name}'...")
        
        # Create main session if it doesn't exist
        subprocess.run(["tmux", "new-session", "-d", "-s", self.session_name])
        
        # Define 20 agent tasks
        agents = [
            ("architect", "Architect: Design system architecture and database schema"),
            ("coder_bot_1", "Coder Bot 1: Implement booking handlers"),
            ("coder_bot_2", "Coder Bot 2: Implement payment handlers"),
            ("coder_db_1", "Coder DB 1: Implement Supabase client"),
            ("coder_db_2", "Coder DB 2: Implement CRUD operations"),
            ("tester_1", "Tester 1: Write Playwright E2E tests"),
            ("tester_2", "Tester 2: Test booking flow"),
            ("tester_3", "Tester 3: Test payment flow"),
            ("devops_1", "DevOps 1: Setup Docker configuration"),
            ("devops_2", "DevOps 2: Setup CI/CD pipelines"),
            ("reviewer_1", "Reviewer 1: Code quality review"),
            ("reviewer_2", "Reviewer 2: Security review"),
            ("fix_overbooking", "Fix bug: Prevent overbooking in slot selection"),
            ("fix_gdpr", "Fix GDPR: Research Telegram GDPR requirements"),
            ("optimize_db", "Optimize: Database query performance"),
            ("add_features", "Feature: Add recurring appointments"),
            ("monitoring", "Monitoring: Setup logging and metrics"),
            ("docs", "Documentation: Update README and API docs"),
            ("migration", "Migration: Database migration scripts"),
            ("deploy", "Deploy: Production deployment checklist"),
        ]
        
        # Create windows for each agent
        for name, task in agents:
            self.create_agent_window(name, task)
            time.sleep(0.5)  # Small delay between window creation
        
        print(f"\n✅ Created {len(agents)} agent windows")
        print(f"\nTo attach: tmux attach -t {self.session_name}")
        print(f"To list windows: tmux list-windows -t {self.session_name}")
    
    def list_windows(self):
        """List all agent windows."""
        result = subprocess.run(
            ["tmux", "list-windows", "-t", self.session_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"\nAgent windows in session '{self.session_name}':")
            print(result.stdout)
        else:
            print("No active session or tmux not available")
    
    def kill_window(self, name: str):
        """Kill a specific agent window."""
        subprocess.run(["tmux", "kill-window", "-t", f"{self.session_name}:{name}"])
        print(f"Killed window '{name}'")
    
    def run_interactive(self):
        """Run interactive management interface."""
        print(f"Parallel Agents Manager - Session: '{self.session_name}'")
        print("\nCommands:")
        print("  list - Show all agent windows")
        print("  kill <name> - Kill specific window")
        print("  attach - Attach to tmux session")
        print("  exit - Exit and cleanup")
        
        try:
            while True:
                cmd = input("\nagents> ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0] == "list":
                    self.list_windows()
                
                elif cmd[0] == "kill" and len(cmd) > 1:
                    self.kill_window(cmd[1])
                
                elif cmd[0] == "attach":
                    subprocess.run(["tmux", "attach", "-t", self.session_name])
                
                elif cmd[0] == "exit":
                    break
                
                else:
                    print("Unknown command. Use: list, kill <name>, attach, exit")
        
        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            print("Exiting...")


def main():
    """Main entry point."""
    manager = ParallelAgentsManager()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup":
            manager.setup_parallel_agents()
        elif sys.argv[1] == "list":
            manager.list_windows()
        else:
            print("Usage: python tmux_agents_parallel.py [setup|list]")
    else:
        manager.setup_parallel_agents()
        manager.run_interactive()


if __name__ == "__main__":
    main()
