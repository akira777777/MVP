"""
Windows-compatible parallel agents manager.
Uses subprocess instead of tmux for Windows compatibility.
Agents run continuously and process tasks from queues.

Optimizations:
- Config-driven agent definitions
- Health monitoring and auto-restart
- Better error handling and logging
- Process lifecycle management
"""

import subprocess
import sys
import time
import signal
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/agents_manager.log", encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class ParallelAgentsManager:
    """Manages parallel agent processes with health monitoring."""
    
    def __init__(self, config_path: str = "agents_config.json"):
        """Initialize parallel agents manager."""
        self.processes: Dict[str, Dict] = {}
        self.session_name = "agents"
        self.config_path = Path(config_path)
        self.pid_file = Path("agents_session.pid")
        self.health_check_interval = 30  # seconds
        self.auto_restart = True
        self.max_restart_attempts = 3
        
        self.load_config()
        self.load_processes()
    
    def load_config(self):
        """Load agent configuration from file or create default."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"Loaded config from {self.config_path}")
            else:
                self.config = self._get_default_config()
                self.save_config()
                logger.info(f"Created default config at {self.config_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default agent configuration."""
        return {
            "session_name": "agents",
            "agents": [
                {
                    "name": "architect",
                    "script": "agents/architect.py",
                    "description": "Architect: Design system architecture and database schema",
                    "auto_restart": True,
                    "max_restarts": 3
                },
                {
                    "name": "coder_bot_1",
                    "script": "agents/coder_bot.py",
                    "description": "Coder Bot 1: Implement booking handlers",
                    "auto_restart": True
                },
                {
                    "name": "coder_bot_2",
                    "script": "agents/coder_bot.py",
                    "description": "Coder Bot 2: Implement payment handlers",
                    "auto_restart": True
                },
                {
                    "name": "coder_db_1",
                    "script": "agents/coder_db.py",
                    "description": "Coder DB 1: Implement Supabase client",
                    "auto_restart": True
                },
                {
                    "name": "coder_db_2",
                    "script": "agents/coder_db.py",
                    "description": "Coder DB 2: Implement CRUD operations",
                    "auto_restart": True
                },
                {
                    "name": "tester_1",
                    "script": "agents/tester.py",
                    "description": "Tester 1: Write Playwright E2E tests",
                    "auto_restart": True
                },
                {
                    "name": "tester_2",
                    "script": "agents/tester.py",
                    "description": "Tester 2: Test booking flow",
                    "auto_restart": True
                },
                {
                    "name": "tester_3",
                    "script": "agents/tester.py",
                    "description": "Tester 3: Test payment flow",
                    "auto_restart": True
                },
                {
                    "name": "devops_1",
                    "script": "agents/devops.py",
                    "description": "DevOps 1: Setup Docker configuration",
                    "auto_restart": True
                },
                {
                    "name": "devops_2",
                    "script": "agents/devops.py",
                    "description": "DevOps 2: Setup CI/CD pipelines",
                    "auto_restart": True
                },
                {
                    "name": "reviewer_1",
                    "script": "agents/reviewer.py",
                    "description": "Reviewer 1: Code quality review",
                    "auto_restart": True
                },
                {
                    "name": "reviewer_2",
                    "script": "agents/reviewer.py",
                    "description": "Reviewer 2: Security review",
                    "auto_restart": True
                },
                {
                    "name": "fix_overbooking",
                    "script": "agents/fix.py",
                    "description": "Fix bug: Prevent overbooking in slot selection",
                    "auto_restart": True
                },
                {
                    "name": "fix_gdpr",
                    "script": "agents/fix.py",
                    "description": "Fix GDPR: Research Telegram GDPR requirements",
                    "auto_restart": True
                },
                {
                    "name": "optimize_db",
                    "script": "agents/optimize.py",
                    "description": "Optimize: Database query performance",
                    "auto_restart": True
                },
                {
                    "name": "add_features",
                    "script": "agents/add.py",
                    "description": "Feature: Add recurring appointments",
                    "auto_restart": True
                },
                {
                    "name": "monitoring",
                    "script": "agents/monitoring.py",
                    "description": "Monitoring: Setup logging and metrics",
                    "auto_restart": True
                },
                {
                    "name": "docs",
                    "script": "agents/docs.py",
                    "description": "Documentation: Update README and API docs",
                    "auto_restart": True
                },
                {
                    "name": "migration",
                    "script": "agents/migration.py",
                    "description": "Migration: Database migration scripts",
                    "auto_restart": True
                },
                {
                    "name": "deploy",
                    "script": "agents/deploy.py",
                    "description": "Deploy: Production deployment checklist",
                    "auto_restart": True
                },
            ],
            "global_settings": {
                "log_file": "agents_session.log",
                "pid_file": "agents_session.pid",
                "auto_save_config": True,
                "health_check_interval": 30,
                "auto_restart": True,
                "max_restart_attempts": 3
            }
        }
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def _get_agent_config(self, name: str) -> Optional[Dict]:
        """Get agent configuration by name."""
        agents = self.config.get("agents", [])
        for agent in agents:
            if agent.get("name") == name:
                return agent
        return None
    
    def _resolve_script_path(self, name: str, script_path: str) -> Path:
        """Resolve script path, creating placeholder if needed."""
        script_path = Path(script_path)
        
        if not script_path.exists():
            # Try alternative locations
            alternatives = [
                Path(f"agents/{name}.py"),
                Path(f"agents/{name.split('_')[0]}.py"),
            ]
            
            for alt_path in alternatives:
                if alt_path.exists():
                    logger.info(f"Using alternative script path: {alt_path}")
                    return alt_path
            
            # Create placeholder if script doesn't exist
            logger.warning(f"Script not found: {script_path}, creating placeholder")
            script_path.parent.mkdir(parents=True, exist_ok=True)
            self._create_placeholder_script(script_path, name)
        
        return script_path
    
    def _create_placeholder_script(self, script_path: Path, name: str):
        """Create a placeholder agent script."""
        class_name = ''.join(word.capitalize() for word in name.split('_')) + 'Agent'
        script_content = f'''"""
Placeholder agent script for {name}.
Replace this with actual implementation.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/agent_{name}.log", encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class {class_name}(BaseAgent):
    """Placeholder agent for {name}."""
    
    async def process_task(self, task):
        """Process task - implement in subclass."""
        logger.info(f"Processing task: {{task.get('id')}} - {{task.get('type')}}")
        return {{"status": "completed", "result": "Placeholder implementation"}}


async def main():
    """Main function to run agent."""
    agent = {class_name}("{name}")
    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Agent stopping...")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
'''
        script_path.write_text(script_content, encoding='utf-8')
    
    def create_agent_process(self, name: str, description: str = None, cwd: str = None) -> bool:
        """
        Create a process for an agent (Windows-compatible).
        
        Args:
            name: Agent name
            description: Task description (optional, from config if not provided)
            cwd: Working directory
            
        Returns:
            True if successful, False otherwise
        """
        # Get agent config
        agent_config = self._get_agent_config(name)
        if agent_config:
            script_path = agent_config.get("script", f"agents/{name}.py")
            description = description or agent_config.get("description", f"Agent: {name}")
            auto_restart = agent_config.get("auto_restart", True)
            max_restarts = agent_config.get("max_restarts", self.max_restart_attempts)
        else:
            # Fallback: infer from name
            base_name = name.split("_")[0]
            script_path = f"agents/{base_name}.py"
            description = description or f"Agent: {name}"
            auto_restart = True
            max_restarts = self.max_restart_attempts
        
        logger.info(f"Creating agent process '{name}' - {description}")
        
        script_path = self._resolve_script_path(name, script_path)
        
        try:
            # Create directories
            log_file = Path(f"logs/agent_{name}.log")
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            task_queue = Path(f"tasks/queue_{name}.json")
            task_queue.parent.mkdir(parents=True, exist_ok=True)
            if not task_queue.exists():
                task_queue.write_text("[]", encoding='utf-8')
            
            # Start agent process
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=cwd or os.getcwd(),
                stdout=open(log_file, 'w', encoding='utf-8'),
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                start_new_session=True
            )
            
            self.processes[name] = {
                "process": process,
                "pid": process.pid,
                "log_file": log_file,
                "task_queue": task_queue,
                "description": description,
                "script_path": script_path,
                "auto_restart": auto_restart,
                "max_restarts": max_restarts,
                "restart_count": 0,
                "started_at": time.time(),
                "last_health_check": time.time(),
            }
            
            self.save_processes()
            
            logger.info(f"✅ Agent '{name}' started (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating agent '{name}': {e}", exc_info=True)
            return False
    
    def setup_parallel_agents(self):
        """Setup parallel agent processes from configuration."""
        session_name = self.config.get("session_name", self.session_name)
        logger.info(f"🚀 Setting up parallel agents session '{session_name}'...")
        print(f"🚀 Setting up parallel agents session '{session_name}'...")
        print("Agents will run continuously and process tasks from queues.\n")
        
        # Create directories
        Path("logs").mkdir(exist_ok=True)
        Path("tasks").mkdir(exist_ok=True)
        
        # Load global settings
        global_settings = self.config.get("global_settings", {})
        self.health_check_interval = global_settings.get("health_check_interval", 30)
        self.auto_restart = global_settings.get("auto_restart", True)
        self.max_restart_attempts = global_settings.get("max_restart_attempts", 3)
        
        # Get agents from config
        agents = self.config.get("agents", [])
        
        if not agents:
            logger.warning("No agents defined in config, using default set")
            # Fallback to hardcoded list if config is empty
            agents = [
                {"name": "architect", "description": "Architect: Design system architecture"},
                {"name": "coder_bot_1", "description": "Coder Bot 1: Implement booking handlers"},
                {"name": "coder_bot_2", "description": "Coder Bot 2: Implement payment handlers"},
                {"name": "coder_db_1", "description": "Coder DB 1: Implement Supabase client"},
                {"name": "coder_db_2", "description": "Coder DB 2: Implement CRUD operations"},
                {"name": "tester_1", "description": "Tester 1: Write Playwright E2E tests"},
                {"name": "tester_2", "description": "Tester 2: Test booking flow"},
                {"name": "tester_3", "description": "Tester 3: Test payment flow"},
                {"name": "devops_1", "description": "DevOps 1: Setup Docker configuration"},
                {"name": "devops_2", "description": "DevOps 2: Setup CI/CD pipelines"},
                {"name": "reviewer_1", "description": "Reviewer 1: Code quality review"},
                {"name": "reviewer_2", "description": "Reviewer 2: Security review"},
            ]
        
        # Create processes for each agent
        created = 0
        failed = 0
        
        for agent_config in agents:
            name = agent_config.get("name")
            description = agent_config.get("description", f"Agent: {name}")
            
            if self.create_agent_process(name, description):
                created += 1
                time.sleep(0.2)  # Small delay between process creation
            else:
                failed += 1
        
        print(f"\n✅ Created {created} agent processes")
        if failed > 0:
            print(f"⚠️  Failed to create {failed} agent processes")
        
        print(f"\n📁 Directories:")
        print(f"   Logs: logs/")
        print(f"   Tasks: tasks/")
        print(f"\n📋 Commands:")
        print(f"   List agents: py tmux_agents_parallel_windows.py list")
        print(f"   Stop all: py tmux_agents_parallel_windows.py stop")
        print(f"   Health check: py tmux_agents_parallel_windows.py health")
        print(f"   View log: type logs\\agent_<name>.log")
        print(f"\n💡 Agents are running continuously and waiting for tasks!")
        print(f"   Add tasks to: tasks/queue_<agent_name>.json")
    
    def save_processes(self):
        """Save process PIDs to file."""
        try:
            pids = {name: info.get("pid") for name, info in self.processes.items() if info.get("pid")}
            with open(self.pid_file, 'w') as f:
                json.dump(pids, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save process PIDs: {e}")
    
    def load_processes(self):
        """Load process PIDs from file and check if they're still running."""
        if not self.pid_file.exists():
            return
        
        try:
            with open(self.pid_file, 'r', encoding='utf-8') as f:
                pids = json.load(f)
            
            for name, pid in pids.items():
                try:
                    # Check if process is still running
                    if self._is_process_running(pid):
                        # Reconstruct process info
                        self.processes[name] = {
                            "pid": pid,
                            "log_file": Path(f"logs/agent_{name}.log"),
                            "task_queue": Path(f"tasks/queue_{name}.json"),
                            "description": "Restored from PID file",
                            "restart_count": 0,
                            "started_at": time.time(),
                            "last_health_check": time.time(),
                        }
                        logger.info(f"Restored process info for {name} (PID: {pid})")
                except Exception as e:
                    logger.debug(f"Process {pid} ({name}) not running: {e}")
        except Exception as e:
            logger.debug(f"Could not load processes: {e}")
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running."""
        try:
            import psutil
            return psutil.pid_exists(pid)
        except ImportError:
            # Fallback: try to send signal 0 (doesn't kill, just checks)
            try:
                if os.name == 'nt':
                    # Windows: use OpenProcess
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.OpenProcess(1, 0, pid)  # PROCESS_QUERY_INFORMATION
                    if handle:
                        kernel32.CloseHandle(handle)
                        return True
                    return False
                else:
                    os.kill(pid, 0)
                    return True
            except (OSError, ProcessLookupError):
                return False
        except Exception:
            return False
    
    def check_agent_health(self, name: str) -> Tuple[bool, str]:
        """
        Check health of a specific agent.
        
        Returns:
            Tuple of (is_healthy, status_message)
        """
        if name not in self.processes:
            return False, "Agent not found"
        
        info = self.processes[name]
        pid = info.get("pid")
        
        if not pid:
            return False, "No PID"
        
        if not self._is_process_running(pid):
            return False, "Process not running"
        
        # Check if log file is being updated (indicates activity)
        log_file = info.get("log_file")
        if log_file and log_file.exists():
            try:
                mtime = log_file.stat().st_mtime
                age = time.time() - mtime
                if age > 300:  # 5 minutes without log updates
                    return False, f"Log stale (last update {age:.0f}s ago)"
            except Exception:
                pass
        
        info["last_health_check"] = time.time()
        return True, "Healthy"
    
    def health_check_all(self) -> Dict[str, Dict]:
        """Check health of all agents and optionally restart failed ones."""
        results = {}
        restarted = []
        
        for name in list(self.processes.keys()):
            is_healthy, status = self.check_agent_health(name)
            results[name] = {
                "healthy": is_healthy,
                "status": status,
                "pid": self.processes[name].get("pid"),
            }
            
            # Auto-restart if unhealthy and enabled
            if not is_healthy and self.auto_restart:
                info = self.processes[name]
                restart_count = info.get("restart_count", 0)
                max_restarts = info.get("max_restarts", self.max_restart_attempts)
                
                if restart_count < max_restarts:
                    logger.warning(f"Agent {name} unhealthy ({status}), attempting restart...")
                    if self._restart_agent(name):
                        restarted.append(name)
                        results[name]["restarted"] = True
                else:
                    logger.error(
                        f"Agent {name} exceeded max restart attempts ({max_restarts})"
                    )
                    results[name]["max_restarts_exceeded"] = True
        
        return results
    
    def _restart_agent(self, name: str) -> bool:
        """Restart a failed agent."""
        if name not in self.processes:
            return False
        
        info = self.processes[name]
        description = info.get("description", f"Agent: {name}")
        restart_count = info.get("restart_count", 0) + 1
        
        # Kill old process if still running
        self.kill_process(name)
        
        # Create new process
        if self.create_agent_process(name, description):
            self.processes[name]["restart_count"] = restart_count
            logger.info(f"Successfully restarted agent {name} (attempt {restart_count})")
            return True
        else:
            logger.error(f"Failed to restart agent {name}")
            return False
    
    def list_processes(self):
        """List all agent processes with health status."""
        print(f"\nAgent processes in session '{self.session_name}':")
        
        # Reload processes from PIDs
        self.load_processes()
        
        if not self.processes:
            print("  No active processes")
            return
        
        running_count = 0
        healthy_count = 0
        
        for name, info in self.processes.items():
            pid = info.get("pid")
            is_healthy, status = self.check_agent_health(name)
            
            if is_healthy:
                status_display = "✅ running"
                running_count += 1
                healthy_count += 1
            elif pid and self._is_process_running(pid):
                status_display = "⚠️  running (unhealthy)"
                running_count += 1
            else:
                status_display = "❌ stopped"
            
            print(f"  {name:25} {status_display:20} PID: {pid}")
            if "description" in info:
                print(f"    Description: {info['description']}")
            print(f"    Status: {status}")
            print(f"    Log: {info.get('log_file', 'N/A')}")
            print(f"    Queue: {info.get('task_queue', 'N/A')}")
            restart_count = info.get("restart_count", 0)
            if restart_count > 0:
                print(f"    Restarts: {restart_count}")
            print()
        
        print(f"Total: {running_count}/{len(self.processes)} agents running")
        print(f"Healthy: {healthy_count}/{len(self.processes)} agents healthy")
    
    def kill_process(self, name: str):
        """Kill a specific agent process."""
        if name not in self.processes:
            logger.warning(f"Process '{name}' not found")
            return
        
        info = self.processes[name]
        pid = info.get("pid")
        
        if pid and self._is_process_running(pid):
            try:
                if os.name == 'nt':
                    # Windows: use taskkill
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        timeout=5
                    )
                else:
                    # Unix: send SIGTERM, then SIGKILL
                    try:
                        os.kill(pid, signal.SIGTERM)
                        time.sleep(2)
                        if self._is_process_running(pid):
                            os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Already dead
                
                logger.info(f"Killed process '{name}' (PID: {pid})")
            except Exception as e:
                logger.error(f"Error killing process '{name}': {e}")
        
        # Remove from processes dict
        del self.processes[name]
        self.save_processes()
    
    def stop_all(self):
        """Stop all agent processes."""
        print("\n🛑 Stopping all agent processes...")
        for name in list(self.processes.keys()):
            self.kill_process(name)
        print("✅ All processes stopped")
    
    def add_task_to_agent(self, agent_name: str, task: dict):
        """Add a task to an agent's queue."""
        if agent_name not in self.processes:
            print(f"❌ Agent '{agent_name}' not found")
            return
        
        queue_file = self.processes[agent_name]["task_queue"]
        
        try:
            tasks = []
            if queue_file.exists():
                with open(queue_file, 'r') as f:
                    tasks = json.load(f)
            
            task_id = f"task_{int(time.time())}"
            task["id"] = task_id
            tasks.append(task)
            
            with open(queue_file, 'w') as f:
                json.dump(tasks, f, indent=2)
            
            print(f"✅ Task {task_id} added to {agent_name} queue")
        except Exception as e:
            print(f"❌ Error adding task: {e}")
    
    def run_interactive(self):
        """Run interactive management interface."""
        print(f"🤖 Parallel Agents Manager (Windows) - Session: '{self.session_name}'")
        print("\nCommands:")
        print("  list - Show all agent processes")
        print("  kill <name> - Kill specific process")
        print("  stop - Stop all processes")
        print("  logs <name> - Show log for agent")
        print("  task <agent> <type> <data> - Add task to agent")
        print("  exit - Exit")
        
        try:
            while True:
                cmd = input("\nagents> ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0] == "list":
                    self.list_processes()
                
                elif cmd[0] == "kill" and len(cmd) > 1:
                    self.kill_process(cmd[1])
                
                elif cmd[0] == "stop":
                    self.stop_all()
                
                elif cmd[0] == "logs" and len(cmd) > 1:
                    name = cmd[1]
                    if name in self.processes:
                        log_file = self.processes[name]["log_file"]
                        if log_file.exists():
                            print(f"\n📄 Log for {name} (last 50 lines):")
                            try:
                                lines = log_file.read_text(encoding='utf-8').split('\n')
                                print('\n'.join(lines[-50:]))
                            except Exception as e:
                                print(f"Error reading log: {e}")
                        else:
                            print(f"❌ Log file not found: {log_file}")
                    else:
                        print(f"❌ Agent '{name}' not found")
                
                elif cmd[0] == "health":
                    print("\n🏥 Health check for all agents:")
                    results = self.health_check_all()
                    for name, result in results.items():
                        status_icon = "✅" if result["healthy"] else "❌"
                        print(f"  {status_icon} {name:25} {result['status']}")
                    if any(r.get("restarted") for r in results.values()):
                        print("\n⚠️  Some agents were restarted")
                
                elif cmd[0] == "task" and len(cmd) >= 3:
                    agent_name = cmd[1]
                    task_type = cmd[2]
                    task_data = " ".join(cmd[3:]) if len(cmd) > 3 else {}
                    self.add_task_to_agent(agent_name, {
                        "type": task_type,
                        "data": {"description": task_data}
                    })
                
                elif cmd[0] == "exit":
                    break
                
                else:
                    print("❓ Unknown command. Use: list, kill <name>, stop, logs <name>, task <agent> <type>, exit")
        
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted")
        finally:
            self.stop_all()


def main():
    """Main entry point."""
    manager = ParallelAgentsManager()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup":
            manager.setup_parallel_agents()
            print("\n✅ Agents are running in background!")
            print("Use 'py tmux_agents_parallel_windows.py list' to see status")
            print("Use 'py tmux_agents_parallel_windows.py stop' to stop all")
        elif sys.argv[1] == "list":
            manager.list_processes()
        elif sys.argv[1] == "stop":
            manager.stop_all()
        elif sys.argv[1] == "health":
            print("🏥 Running health check...")
            results = manager.health_check_all()
            for name, result in results.items():
                status_icon = "✅" if result["healthy"] else "❌"
                print(f"  {status_icon} {name:25} {result['status']}")
            restarted = [name for name, r in results.items() if r.get("restarted")]
            if restarted:
                print(f"\n⚠️  Restarted {len(restarted)} agents: {', '.join(restarted)}")
        else:
            print("Usage: py tmux_agents_parallel_windows.py [setup|list|stop|health]")
    else:
        manager.setup_parallel_agents()
        manager.run_interactive()


if __name__ == "__main__":
    main()
