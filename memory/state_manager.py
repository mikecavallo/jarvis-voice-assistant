"""
Jarvis State Management Module.

This module provides persistent state management for the Jarvis Assistant using
JSON file storage. It handles:
- Goal tracking and management
- Todo list with priority and assignment
- Action logging with component tracking
- Current task management for AI agents
- Inter-agent communication system
- Session handoff coordination
- Session summary storage

The state is automatically saved to disk after each modification to ensure
data persistence across system restarts.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class JarvisState:
    """
    Manages persistent state for Jarvis Assistant using JSON file storage.
    
    This class provides a centralized state management system that tracks:
    - System goals and objectives
    - Todo items with status, priority, and assignment
    - Action logs for debugging and monitoring
    - Current tasks for AI agents (Claude, Gemini, User)
    - Inter-agent messaging and task handoff
    - Session summaries for continuity
    
    The state is automatically persisted to disk after each modification
    to ensure data survives system restarts and crashes.
    
    Attributes:
        state_file (Path): Path to the JSON state file
        state (dict): In-memory state dictionary
    """
    
    def __init__(self, state_file: str = "jarvis_state.json"):
        """
        Initialize the state manager with persistent JSON storage.
        
        Args:
            state_file: Path to JSON file for state persistence (defaults to jarvis_state.json)
        """
        self.state_file = Path(state_file)
        self.load_state()
    
    def load_state(self):
        """
        Load state from JSON file or initialize with default structure.
        
        If the state file exists, loads the existing state. Otherwise,
        creates a new state with default goals, initial todos, and
        system metadata.
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load state file: {e}")
                print("Creating new state file...")
                self._create_default_state()
        else:
            self._create_default_state()
    
    def _create_default_state(self):
        """
        Create the default state structure for a new Jarvis installation.
        
        Sets up initial goals, sample todo, logging system, and metadata.
        """
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
        """
        Save current state to JSON file with updated timestamp.
        
        Updates the last_updated metadata and writes the entire state
        to disk with proper formatting.
        """
        try:
            self.state["metadata"]["last_updated"] = self._get_timestamp()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving state file: {e}")
    
    def _get_timestamp(self) -> str:
        """
        Get current timestamp in ISO 8601 format.
        
        Returns:
            str: Current timestamp as ISO formatted string
        """
        return datetime.now().isoformat()
    
    # Goals Management Methods
    
    def add_goal(self, goal: str):
        """
        Add a new goal to the system goal list.
        
        Args:
            goal: Description of the new goal to track
        """
        if goal and goal.strip():
            self.state["goals"].append(goal.strip())
            self.log_action("goal_added", f"Added goal: {goal}")
            self.save_state()
    
    def remove_goal(self, goal: str) -> bool:
        """
        Remove a goal from the system goal list.
        
        Args:
            goal: Goal description to remove
            
        Returns:
            bool: True if goal was found and removed, False otherwise
        """
        if goal in self.state["goals"]:
            self.state["goals"].remove(goal)
            self.log_action("goal_removed", f"Removed goal: {goal}")
            self.save_state()
            return True
        return False
    
    def get_goals(self) -> List[str]:
        """
        Get all current system goals.
        
        Returns:
            List[str]: List of current goal descriptions
        """
        return self.state["goals"].copy()
    
    # Todo Management Methods
    
    def add_todo(self, task: str, assigned_to: str = "unassigned", priority: str = "medium") -> int:
        """
        Add a new todo item to the task list.
        
        Args:
            task: Description of the task to be completed
            assigned_to: Agent or person responsible (claude, gemini, user, system)
            priority: Task priority level (high, medium, low)
            
        Returns:
            int: Unique ID assigned to the new todo item
        """
        if not task or not task.strip():
            return None
            
        # Generate unique ID
        todo_id = max([t["id"] for t in self.state["todo"]], default=0) + 1
        
        todo_item = {
            "id": todo_id,
            "task": task.strip(),
            "assigned_to": assigned_to,
            "status": "pending",
            "created": self._get_timestamp(),
            "priority": priority
        }
        
        self.state["todo"].append(todo_item)
        self.log_action("todo_added", f"Added todo: {task} (assigned to {assigned_to})")
        self.save_state()
        return todo_id
    
    def update_todo_status(self, todo_id: int, status: str) -> bool:
        """
        Update the status of a specific todo item.
        
        Args:
            todo_id: Unique identifier of the todo item
            status: New status (pending, in_progress, completed, cancelled)
            
        Returns:
            bool: True if todo was found and updated, False otherwise
        """
        valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
        if status not in valid_statuses:
            print(f"Invalid status: {status}. Valid options: {valid_statuses}")
            return False
            
        for todo in self.state["todo"]:
            if todo["id"] == todo_id:
                old_status = todo["status"]
                todo["status"] = status
                todo["updated"] = self._get_timestamp()
                self.log_action("todo_updated", f"Todo {todo_id} status: {old_status} → {status}")
                self.save_state()
                return True
        return False
    
    def get_todos(self, status: str = None, assigned_to: str = None) -> List[Dict]:
        """
        Get todo items with optional filtering.
        
        Args:
            status: Filter by status (pending, in_progress, completed, cancelled)
            assigned_to: Filter by assignee (claude, gemini, user, system)
            
        Returns:
            List[Dict]: List of todo items matching the filter criteria
        """
        todos = self.state["todo"].copy()
        
        if status:
            todos = [t for t in todos if t["status"] == status]
        
        if assigned_to:
            todos = [t for t in todos if t["assigned_to"] == assigned_to]
            
        return todos
    
    def remove_todo(self, todo_id: int) -> bool:
        """
        Remove a todo item from the list.
        
        Args:
            todo_id: Unique identifier of the todo to remove
            
        Returns:
            bool: True if todo was found and removed, False otherwise
        """
        for i, todo in enumerate(self.state["todo"]):
            if todo["id"] == todo_id:
                removed_todo = self.state["todo"].pop(i)
                self.log_action("todo_removed", f"Removed todo {todo_id}: {removed_todo['task']}")
                self.save_state()
                return True
        return False
    
    # Logging Methods
    
    def log_action(self, action: str, details: str, component: str = "system"):
        """
        Add an entry to the system action log.
        
        Automatically manages log size to prevent excessive file growth
        by keeping only the most recent 100 entries.
        
        Args:
            action: Type of action performed (descriptive identifier)
            details: Detailed description of what happened
            component: System component that performed the action
        """
        log_entry = {
            "timestamp": self._get_timestamp(),
            "action": action,
            "details": details,
            "component": component
        }
        
        self.state["log"].append(log_entry)
        
        # Maintain log size limit to prevent file bloat
        if len(self.state["log"]) > 100:
            self.state["log"] = self.state["log"][-100:]
    
    def get_recent_logs(self, count: int = 10, component: str = None) -> List[Dict]:
        """
        Get the most recent log entries with optional component filtering.
        
        Args:
            count: Maximum number of log entries to return
            component: Filter logs by specific component (optional)
            
        Returns:
            List[Dict]: List of recent log entries, newest first
        """
        logs = self.state["log"]
        
        if component:
            logs = [log for log in logs if log["component"] == component]
        
        return logs[-count:] if logs else []
    
    # Current Task Management Methods
    
    def set_current_task(self, agent: str, task: str):
        """
        Set the current task for a specific agent.
        
        Tracks what each agent (claude, gemini, user) is actively working on
        for coordination and status reporting.
        
        Args:
            agent: The agent name (claude, gemini, user, system)
            task: Description of the current task, or None to clear
        """
        valid_agents = ["claude", "gemini", "user", "system"]
        if agent not in valid_agents:
            print(f"Warning: Unknown agent '{agent}'. Valid agents: {valid_agents}")
        
        self.state["current_task"][agent] = task
        self.log_action("task_assigned", f"{agent} is now working on: {task}")
        self.save_state()
    
    def get_current_task(self, agent: str) -> str:
        """
        Get the current task for a specific agent.
        
        Args:
            agent: The agent name to query
            
        Returns:
            str: Current task description, or None if no task assigned
        """
        return self.state["current_task"].get(agent)
    
    def get_all_current_tasks(self) -> Dict[str, str]:
        """
        Get current tasks for all agents.
        
        Returns:
            Dict[str, str]: Mapping of agent names to their current tasks
        """
        return self.state["current_task"].copy()
    
    def clear_current_task(self, agent: str):
        """
        Clear the current task for a specific agent.
        
        Args:
            agent: The agent name to clear the task for
        """
        self.set_current_task(agent, None)
    
    # AI Agent Communication System Methods
    def add_agent_message(self, from_agent: str, to_agent: str, message: str, message_type: str = "info") -> int:
        """
        Add a message from one AI agent to another for inter-agent communication.
        
        Enables AI agents to communicate with each other for task coordination,
        handoffs, and information sharing.
        
        Args:
            from_agent: The agent sending the message (claude, gemini, user, system)
            to_agent: The agent receiving the message (claude, gemini, user, system)
            message: The message content
            message_type: Type of message (info, request, response, handoff, error)
            
        Returns:
            int: Unique message ID for tracking
        """
        if "agent_messages" not in self.state:
            self.state["agent_messages"] = []
        
        valid_types = ["info", "request", "response", "handoff", "error"]
        if message_type not in valid_types:
            message_type = "info"
        
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
        
        # Keep only last 50 messages to prevent bloat
        if len(self.state["agent_messages"]) > 50:
            self.state["agent_messages"] = self.state["agent_messages"][-50:]
        
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

# Global state instance - shared across all Jarvis components
jarvis_state = JarvisState()