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
    
    # AI Agent Communication System
    def add_agent_message(self, from_agent: str, to_agent: str, message: str, message_type: str = "info"):
        """
        Add a message from one AI agent to another.
        
        Args:
            from_agent: The agent sending the message (claude, gemini, user)
            to_agent: The agent receiving the message (claude, gemini, user)
            message: The message content
            message_type: Type of message (info, request, response, handoff)
        """
        if "agent_messages" not in self.state:
            self.state["agent_messages"] = []
        
        message_entry = {
            "id": len(self.state["agent_messages"]) + 1,
            "timestamp": self._get_timestamp(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message,
            "type": message_type,
            "status": "unread"
        }
        
        self.state["agent_messages"].append(message_entry)
        self.log_action("agent_message", f"{from_agent} → {to_agent}: {message[:50]}...", "communication")
        self.save_state()
        return message_entry["id"]
    
    def get_messages_for_agent(self, agent: str, unread_only: bool = True) -> List[Dict]:
        """
        Get messages for a specific agent.
        
        Args:
            agent: The agent to get messages for
            unread_only: If True, only return unread messages
            
        Returns:
            List of message dictionaries
        """
        if "agent_messages" not in self.state:
            return []
        
        messages = [msg for msg in self.state["agent_messages"] if msg["to_agent"] == agent]
        
        if unread_only:
            messages = [msg for msg in messages if msg["status"] == "unread"]
        
        return messages
    
    def mark_message_read(self, message_id: int):
        """Mark a message as read."""
        if "agent_messages" not in self.state:
            return False
        
        for msg in self.state["agent_messages"]:
            if msg["id"] == message_id:
                msg["status"] = "read"
                msg["read_timestamp"] = self._get_timestamp()
                self.save_state()
                return True
        return False
    
    def create_handoff_session(self, from_agent: str, to_agent: str, context: str, task_description: str):
        """
        Create a handoff session when one AI agent passes work to another.
        
        Args:
            from_agent: Agent handing off the task
            to_agent: Agent receiving the task
            context: Current context and progress made
            task_description: What needs to be done
        """
        if "handoff_sessions" not in self.state:
            self.state["handoff_sessions"] = []
        
        session = {
            "id": len(self.state["handoff_sessions"]) + 1,
            "timestamp": self._get_timestamp(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "context": context,
            "task_description": task_description,
            "status": "pending",
            "completion_notes": None
        }
        
        self.state["handoff_sessions"].append(session)
        
        # Also create a message about the handoff
        self.add_agent_message(
            from_agent, 
            to_agent, 
            f"Task handoff: {task_description}. Context: {context}", 
            "handoff"
        )
        
        # Update current tasks
        self.set_current_task(from_agent, f"Handed off to {to_agent}: {task_description}")
        self.set_current_task(to_agent, f"Received from {from_agent}: {task_description}")
        
        self.log_action("handoff_created", f"{from_agent} → {to_agent}: {task_description}", "communication")
        return session["id"]
    
    def complete_handoff_session(self, session_id: int, completion_notes: str):
        """Complete a handoff session with notes."""
        if "handoff_sessions" not in self.state:
            return False
        
        for session in self.state["handoff_sessions"]:
            if session["id"] == session_id:
                session["status"] = "completed"
                session["completion_notes"] = completion_notes
                session["completed_timestamp"] = self._get_timestamp()
                self.log_action("handoff_completed", f"Session {session_id} completed", "communication")
                self.save_state()
                return True
        return False
    
    def get_active_handoffs_for_agent(self, agent: str) -> List[Dict]:
        """Get active handoff sessions for an agent."""
        if "handoff_sessions" not in self.state:
            return []
        
        return [
            session for session in self.state["handoff_sessions"] 
            if session["to_agent"] == agent and session["status"] == "pending"
        ]
    
    def save_session_summary(self, summary: str, next_session_goals: List[str] = None):
        """
        Save a summary of the current session for the next session.
        
        Args:
            summary: Summary of what was accomplished
            next_session_goals: Goals for the next session
        """
        if "session_summaries" not in self.state:
            self.state["session_summaries"] = []
        
        session_summary = {
            "timestamp": self._get_timestamp(),
            "summary": summary,
            "next_session_goals": next_session_goals or [],
            "current_state": {
                "pending_todos": len(self.get_todos("pending")),
                "in_progress_todos": len(self.get_todos("in_progress")),
                "completed_todos": len(self.get_todos("completed")),
                "goals_count": len(self.get_goals())
            }
        }
        
        self.state["session_summaries"].append(session_summary)
        
        # Keep only last 10 session summaries
        if len(self.state["session_summaries"]) > 10:
            self.state["session_summaries"] = self.state["session_summaries"][-10:]
        
        self.log_action("session_saved", f"Session summary saved: {summary[:50]}...", "session_management")
        self.save_state()
    
    def get_last_session_summary(self) -> Dict:
        """Get the most recent session summary."""
        if "session_summaries" not in self.state or not self.state["session_summaries"]:
            return None
        
        return self.state["session_summaries"][-1]

# Global state instance
jarvis_state = JarvisState()