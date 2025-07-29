"""
Jarvis State Management.
Handles the shared state file for goals, todos, logs, and current tasks.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

class JarvisState:
    """Manages Jarvis's persistent state using JSON storage."""
    
    def __init__(self, state_file: str = "jarvis_state.json"):
        """Initialize state manager with specified file."""
        self.state_file = Path(state_file)
        self.load_state()
    
    def load_state(self):
        """Load state from JSON file or create default structure."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            # Create default state structure
            self.state = {
                "goals": [
                    "Build a modular voice-controlled AI assistant",
                    "Learn Python architecture and Git workflows",
                    "Add daily features to expand capabilities"
                ],
                "todo": [
                    {
                        "id": 1,
                        "task": "Implement basic voice recognition",
                        "assigned_to": "claude",
                        "status": "in_progress",
                        "created": self._get_timestamp(),
                        "priority": "high"
                    }
                ],
                "log": [
                    {
                        "timestamp": self._get_timestamp(),
                        "action": "jarvis_state_initialized",
                        "details": "Created initial state structure",
                        "component": "state_manager"
                    }
                ],
                "current_task": {
                    "claude": "Setting up project backbone",
                    "gemini": None,
                    "user": "Reviewing architecture and learning"
                },
                "metadata": {
                    "created": self._get_timestamp(),
                    "last_updated": self._get_timestamp(),
                    "version": "1.0.0"
                }
            }
            self.save_state()
    
    def save_state(self):
        """Save current state to JSON file."""
        self.state["metadata"]["last_updated"] = self._get_timestamp()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=4)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    # Goals management
    def add_goal(self, goal: str):
        """Add a new goal to the list."""
        self.state["goals"].append(goal)
        self.log_action("goal_added", f"Added goal: {goal}")
        self.save_state()
    
    def get_goals(self) -> List[str]:
        """Get all current goals."""
        return self.state["goals"]
    
    # Todo management
    def add_todo(self, task: str, assigned_to: str = "unassigned", priority: str = "medium"):
        """Add a new todo item."""
        todo_id = max([t["id"] for t in self.state["todo"]], default=0) + 1
        todo_item = {
            "id": todo_id,
            "task": task,
            "assigned_to": assigned_to,
            "status": "pending",
            "created": self._get_timestamp(),
            "priority": priority
        }
        self.state["todo"].append(todo_item)
        self.log_action("todo_added", f"Added todo: {task} (assigned to {assigned_to})")
        self.save_state()
        return todo_id
    
    def update_todo_status(self, todo_id: int, status: str):
        """Update the status of a todo item."""
        for todo in self.state["todo"]:
            if todo["id"] == todo_id:
                todo["status"] = status
                todo["updated"] = self._get_timestamp()
                self.log_action("todo_updated", f"Todo {todo_id} status changed to {status}")
                self.save_state()
                return True
        return False
    
    def get_todos(self, status: str = None) -> List[Dict]:
        """Get todos, optionally filtered by status."""
        if status:
            return [t for t in self.state["todo"] if t["status"] == status]
        return self.state["todo"]
    
    # Logging
    def log_action(self, action: str, details: str, component: str = "system"):
        """Add an entry to the action log."""
        log_entry = {
            "timestamp": self._get_timestamp(),
            "action": action,
            "details": details,
            "component": component
        }
        self.state["log"].append(log_entry)
        # Keep only last 100 log entries to prevent file from growing too large
        if len(self.state["log"]) > 100:
            self.state["log"] = self.state["log"][-100:]
    
    def get_recent_logs(self, count: int = 10) -> List[Dict]:
        """Get the most recent log entries."""
        return self.state["log"][-count:]
    
    # Current task management
    def set_current_task(self, agent: str, task: str):
        """Set what an agent (claude/gemini/user) is currently working on."""
        self.state["current_task"][agent] = task
        self.log_action("task_assigned", f"{agent} is now working on: {task}")
        self.save_state()
    
    def get_current_task(self, agent: str) -> str:
        """Get current task for specified agent."""
        return self.state["current_task"].get(agent)
    
    def get_all_current_tasks(self) -> Dict[str, str]:
        """Get all current tasks."""
        return self.state["current_task"]

# Global state instance
jarvis_state = JarvisState()