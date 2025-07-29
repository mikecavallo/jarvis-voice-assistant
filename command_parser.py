"""
Command Parser for Jarvis Assistant.
Interprets voice commands and maps them to system functions.
"""

import re
import webbrowser
import subprocess
import os
from datetime import datetime
from typing import Dict, Optional, Callable, List
from jarvis_state import jarvis_state

class CommandParser:
    """Parses and executes voice commands for Jarvis."""
    
    def __init__(self):
        """Initialize command parser with available commands."""
        self.commands = self._initialize_commands()
        jarvis_state.log_action("parser_initialized", "Command parser ready", "command_parser")
    
    def _initialize_commands(self) -> Dict[str, Dict]:
        """
        Initialize the command mapping dictionary.
        Each command has patterns (regex), function, and description.
        """
        return {
            "time": {
                "patterns": [
                    r"what time is it",
                    r"tell me the time",
                    r"current time",
                    r"what's the time"
                ],
                "function": self._get_time,
                "description": "Get current time"
            },
            "date": {
                "patterns": [
                    r"what date is it",
                    r"tell me the date",
                    r"what's today's date",
                    r"current date"
                ],
                "function": self._get_date,
                "description": "Get current date"
            },
            "open_browser": {
                "patterns": [
                    r"open browser",
                    r"launch browser",
                    r"start browser",
                    r"open web browser"
                ],
                "function": self._open_browser,
                "description": "Open default web browser"
            },
            "search_google": {
                "patterns": [
                    r"search (?:google )?for (.+)",
                    r"google (.+)",
                    r"look up (.+)",
                    r"find (.+) on the internet"
                ],
                "function": self._search_google,
                "description": "Search Google for a query"
            },
            "open_website": {
                "patterns": [
                    r"go to (.+\.(?:com|org|net|edu|gov))",
                    r"open (.+\.(?:com|org|net|edu|gov))",
                    r"visit (.+\.(?:com|org|net|edu|gov))"
                ],
                "function": self._open_website,
                "description": "Open a specific website"
            },
            "help": {
                "patterns": [
                    r"help",
                    r"what can you do",
                    r"list commands",
                    r"available commands"
                ],
                "function": self._show_help,
                "description": "Show available commands"
            },
            "status": {
                "patterns": [
                    r"status",
                    r"how are you",
                    r"system status",
                    r"jarvis status"
                ],
                "function": self._get_status,
                "description": "Get Jarvis system status"
            },
            "goals": {
                "patterns": [
                    r"what are (?:your|our|my) goals",
                    r"list goals",
                    r"show goals",
                    r"current goals"
                ],
                "function": self._show_goals,
                "description": "Show current goals"
            },
            "todos": {
                "patterns": [
                    r"what(?:'s| is) on (?:the )?(?:todo|to-do) list",
                    r"list (?:todos|tasks)",
                    r"show (?:todos|tasks)",
                    r"pending tasks"
                ],
                "function": self._show_todos,
                "description": "Show pending tasks"
            },
            "quit": {
                "patterns": [
                    r"quit",
                    r"exit",
                    r"goodbye",
                    r"stop listening",
                    r"shut down"
                ],
                "function": self._quit_jarvis,
                "description": "Stop Jarvis"
            }
        }
    
    def parse_command(self, command_text: str) -> Optional[str]:
        """
        Parse voice command and execute corresponding function.
        
        Args:
            command_text: The recognized speech text
            
        Returns:
            Response text to be spoken back to user
        """
        if not command_text:
            return "I didn't catch that. Could you repeat?"
        
        command_text = command_text.lower().strip()
        jarvis_state.log_action("command_parsed", f"Processing: {command_text}", "command_parser")
        
        # Try to match command against patterns
        for command_name, command_info in self.commands.items():
            for pattern in command_info["patterns"]:
                match = re.search(pattern, command_text, re.IGNORECASE)
                if match:
                    try:
                        # Execute the command function
                        if match.groups():
                            # Command has parameters (like search query)
                            response = command_info["function"](match.group(1))
                        else:
                            # Command has no parameters
                            response = command_info["function"]()
                        
                        jarvis_state.log_action("command_executed", f"Executed {command_name}", "command_parser")
                        return response
                        
                    except Exception as e:
                        error_msg = f"Error executing {command_name}: {str(e)}"
                        jarvis_state.log_action("command_error", error_msg, "command_parser")
                        return f"Sorry, I encountered an error: {str(e)}"
        
        # No matching command found
        jarvis_state.log_action("command_unknown", f"Unknown command: {command_text}", "command_parser")
        return f"I don't understand '{command_text}'. Say 'help' to see available commands."
    
    # Command implementation methods
    def _get_time(self) -> str:
        """Get current time."""
        current_time = datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}"
    
    def _get_date(self) -> str:
        """Get current date."""
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {current_date}"
    
    def _open_browser(self) -> str:
        """Open default web browser."""
        try:
            webbrowser.open('https://www.google.com')
            return "Opening your web browser"
        except Exception as e:
            return f"Sorry, I couldn't open the browser: {str(e)}"
    
    def _search_google(self, query: str) -> str:
        """Search Google for the given query."""
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            return f"Searching Google for {query}"
        except Exception as e:
            return f"Sorry, I couldn't search for that: {str(e)}"
    
    def _open_website(self, website: str) -> str:
        """Open a specific website."""
        try:
            if not website.startswith(('http://', 'https://')):
                website = 'https://' + website
            webbrowser.open(website)
            return f"Opening {website}"
        except Exception as e:
            return f"Sorry, I couldn't open that website: {str(e)}"
    
    def _show_help(self) -> str:
        """Show available commands."""
        help_text = "Here are the commands I understand: "
        commands = []
        for cmd_name, cmd_info in self.commands.items():
            commands.append(f"{cmd_name} - {cmd_info['description']}")
        
        return help_text + ". ".join(commands)
    
    def _get_status(self) -> str:
        """Get Jarvis system status."""
        pending_todos = len(jarvis_state.get_todos("pending"))
        in_progress_todos = len(jarvis_state.get_todos("in_progress"))
        
        status_parts = [
            "I'm running smoothly",
            f"{pending_todos} pending tasks",
            f"{in_progress_todos} tasks in progress"
        ]
        
        current_tasks = jarvis_state.get_all_current_tasks()
        if current_tasks.get("claude"):
            status_parts.append(f"Claude is working on: {current_tasks['claude']}")
        
        return ". ".join(status_parts)
    
    def _show_goals(self) -> str:
        """Show current goals."""
        goals = jarvis_state.get_goals()
        if not goals:
            return "No goals are currently set"
        
        goal_text = "Current goals are: " + ". ".join(goals)
        return goal_text
    
    def _show_todos(self) -> str:
        """Show pending todos."""
        todos = jarvis_state.get_todos("pending")
        if not todos:
            return "No pending tasks"
        
        todo_list = []
        for todo in todos[:5]:  # Limit to 5 for voice response
            todo_list.append(f"{todo['task']} assigned to {todo['assigned_to']}")
        
        return "Pending tasks: " + ". ".join(todo_list)
    
    def _quit_jarvis(self) -> str:
        """Signal to quit Jarvis."""
        jarvis_state.log_action("shutdown_requested", "User requested shutdown", "command_parser")
        return "Goodbye! Shutting down Jarvis."
    
    def add_custom_command(self, name: str, patterns: List[str], 
                          function: Callable, description: str):
        """
        Add a custom command to the parser.
        
        Args:
            name: Command name
            patterns: List of regex patterns to match
            function: Function to execute
            description: Command description
        """
        self.commands[name] = {
            "patterns": patterns,
            "function": function,
            "description": description
        }
        jarvis_state.log_action("command_added", f"Added custom command: {name}", "command_parser")
    
    def list_commands(self) -> Dict[str, str]:
        """Get a dictionary of all available commands and their descriptions."""
        return {name: info["description"] for name, info in self.commands.items()}

# Test function for standalone usage
if __name__ == "__main__":
    parser = CommandParser()
    
    # Test some commands
    test_commands = [
        "what time is it",
        "search google for python tutorials",
        "help",
        "unknown command"
    ]
    
    for cmd in test_commands:
        print(f"Command: {cmd}")
        response = parser.parse_command(cmd)
        print(f"Response: {response}\n")