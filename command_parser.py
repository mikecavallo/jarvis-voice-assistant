"""
Command Parser for Jarvis Assistant.

This module handles the interpretation and execution of voice commands.
It uses regex pattern matching to identify commands and maps them to
corresponding system functions.

The parser is designed to be easily extensible - new commands can be
added by extending the command dictionary or using the add_custom_command method.
"""

import re
import webbrowser
import asyncio
from datetime import datetime
from typing import Dict, Optional, Callable, List
from urllib.parse import quote_plus
from memory.state_manager import jarvis_state
from memory.conversation_manager import conversation_manager


class CommandParser:
    """
    Parses and executes voice commands for Jarvis Assistant.
    
    This class maintains a registry of available commands and their corresponding
    regex patterns. When a command is parsed, it matches the input against these
    patterns and executes the appropriate function.
    
    The parser supports:
    - Basic system commands (time, date, status)
    - Web browsing and search commands
    - Jarvis state management commands
    - Extensible custom commands
    
    Attributes:
        commands (Dict): Registry of available commands with patterns and functions
    """
    
    def __init__(self):
        """
        Initialize command parser with built-in commands.
        
        Sets up the command registry with all available built-in commands
        and logs the initialization to the system state.
        """
        self.commands = self._initialize_commands()
        jarvis_state.log_action("parser_initialized", "Command parser ready", "command_parser")
    
    def _initialize_commands(self) -> Dict[str, Dict]:
        """
        Initialize the built-in command registry.
        
        Each command entry contains:
        - patterns: List of regex patterns that match the command
        - function: Method to execute when command is matched
        - description: Human-readable description of the command
        
        Returns:
            Dict: Complete command registry with all built-in commands
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
                    r"go to (.+\.(?:com|org|net|edu|gov|io))",
                    r"open (.+\.(?:com|org|net|edu|gov|io))",
                    r"visit (.+\.(?:com|org|net|edu|gov|io))"
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
        Parse and execute a voice command.
        
        This is the main entry point for command processing. It:
        1. Normalizes the input text
        2. Attempts to match against all known command patterns
        3. Executes the first matching command
        4. Falls back to conversational AI if no command matches
        5. Returns the response text for voice synthesis
        
        Args:
            command_text: The recognized speech text from voice input
            
        Returns:
            str: Response text to be spoken back to the user, or None if error
        """
        if not command_text:
            return "I didn't catch that. Could you repeat?"
        
        # Normalize input for consistent matching
        command_text = command_text.lower().strip()
        jarvis_state.log_action("command_parsed", f"Processing: {command_text}", "command_parser")
        
        # Try to match command against all registered patterns
        for command_name, command_info in self.commands.items():
            for pattern in command_info["patterns"]:
                match = re.search(pattern, command_text, re.IGNORECASE)
                if match:
                    try:
                        # Execute the matched command
                        if match.groups():
                            # Command has parameters (e.g., search query)
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
        
        # No matching command found - try conversational AI
        try:
            jarvis_state.log_action("fallback_to_conversation", f"No command match, using AI: {command_text}", "command_parser")
            # Use asyncio to run the async conversation method
            response = asyncio.run(conversation_manager.get_response(command_text))
            jarvis_state.log_action("conversation_response", "Generated AI response", "command_parser")
            return response
        except Exception as e:
            jarvis_state.log_action("conversation_error", f"AI conversation failed: {e}", "command_parser")
            return f"I don't understand '{command_text}'. Say 'help' to see available commands."
    
    # Built-in Command Implementations
    
    def _get_time(self) -> str:
        """
        Get the current time in 12-hour format.
        
        Returns:
            str: Current time formatted as "HH:MM AM/PM"
        """
        current_time = datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}"
    
    def _get_date(self) -> str:
        """
        Get the current date in a human-readable format.
        
        Returns:
            str: Current date formatted as "Day, Month DD, YYYY"
        """
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {current_date}"
    
    def _open_browser(self) -> str:
        """
        Open the default web browser to Google's homepage.
        
        Returns:
            str: Confirmation message about browser opening
        """
        try:
            webbrowser.open('https://www.google.com')
            return "Opening your web browser"
        except Exception as e:
            return f"Sorry, I couldn't open the browser: {str(e)}"
    
    def _search_google(self, query: str) -> str:
        """
        Perform a Google search for the specified query.
        
        Args:
            query: Search terms extracted from the voice command
            
        Returns:
            str: Confirmation message about the search
        """
        try:
            # URL encode the search query for safe web usage
            encoded_query = quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            webbrowser.open(search_url)
            return f"Searching Google for {query}"
        except Exception as e:
            return f"Sorry, I couldn't search for that: {str(e)}"
    
    def _open_website(self, website: str) -> str:
        """
        Open a specific website in the default browser.
        
        Args:
            website: Website URL extracted from the voice command
            
        Returns:
            str: Confirmation message about opening the website
        """
        try:
            # Ensure the URL has a protocol
            if not website.startswith(('http://', 'https://')):
                website = 'https://' + website
            webbrowser.open(website)
            return f"Opening {website}"
        except Exception as e:
            return f"Sorry, I couldn't open that website: {str(e)}"
    
    def _show_help(self) -> str:
        """
        Generate a help message listing all available commands.
        
        Returns:
            str: Formatted list of available commands and their descriptions
        """
        help_text = "Here are the commands I understand: "
        commands = []
        for cmd_name, cmd_info in self.commands.items():
            commands.append(f"{cmd_name} - {cmd_info['description']}")
        
        return help_text + ". ".join(commands)
    
    def _get_status(self) -> str:
        """
        Get current Jarvis system status including task counts and active work.
        
        Returns:
            str: System status summary including task counts and current activities
        """
        pending_todos = len(jarvis_state.get_todos("pending"))
        in_progress_todos = len(jarvis_state.get_todos("in_progress"))
        
        status_parts = [
            "I'm running smoothly",
            f"{pending_todos} pending tasks",
            f"{in_progress_todos} tasks in progress"
        ]
        
        # Include current AI agent activities
        current_tasks = jarvis_state.get_all_current_tasks()
        if current_tasks.get("claude"):
            status_parts.append(f"Claude is working on: {current_tasks['claude']}")
        
        return ". ".join(status_parts)
    
    def _show_goals(self) -> str:
        """
        List the current system goals.
        
        Returns:
            str: Formatted list of current goals or message if none set
        """
        goals = jarvis_state.get_goals()
        if not goals:
            return "No goals are currently set"
        
        goal_text = "Current goals are: " + ". ".join(goals)
        return goal_text
    
    def _show_todos(self) -> str:
        """
        List pending todo items from the system state.
        
        Returns:
            str: Formatted list of pending tasks (limited to 5 for voice response)
        """
        todos = jarvis_state.get_todos("pending")
        if not todos:
            return "No pending tasks"
        
        todo_list = []
        # Limit to 5 tasks for manageable voice response
        for todo in todos[:5]:
            todo_list.append(f"{todo['task']} assigned to {todo['assigned_to']}")
        
        return "Pending tasks: " + ". ".join(todo_list)
    
    def _quit_jarvis(self) -> str:
        """
        Signal system shutdown request.
        
        Returns:
            str: Goodbye message indicating system shutdown
        """
        jarvis_state.log_action("shutdown_requested", "User requested shutdown", "command_parser")
        return "Goodbye! Shutting down Jarvis."
    
    # Extension Methods
    
    def add_custom_command(self, name: str, patterns: List[str], 
                          function: Callable, description: str):
        """
        Add a custom command to the parser registry.
        
        This allows dynamic extension of Jarvis capabilities by adding
        new commands at runtime without modifying the core parser.
        
        Args:
            name: Unique identifier for the command
            patterns: List of regex patterns that should trigger this command
            function: Callable that implements the command logic
            description: Human-readable description for help text
        """
        self.commands[name] = {
            "patterns": patterns,
            "function": function,
            "description": description
        }
        jarvis_state.log_action("command_added", f"Added custom command: {name}", "command_parser")
    
    def remove_command(self, name: str) -> bool:
        """
        Remove a command from the parser registry.
        
        Args:
            name: Name of the command to remove
            
        Returns:
            bool: True if command was removed, False if not found
        """
        if name in self.commands:
            del self.commands[name]
            jarvis_state.log_action("command_removed", f"Removed command: {name}", "command_parser")
            return True
        return False
    
    def list_commands(self) -> Dict[str, str]:
        """
        Get a dictionary of all available commands and their descriptions.
        
        Returns:
            Dict[str, str]: Mapping of command names to descriptions
        """
        return {name: info["description"] for name, info in self.commands.items()}
    
    def get_command_patterns(self, name: str) -> Optional[List[str]]:
        """
        Get the regex patterns for a specific command.
        
        Args:
            name: Name of the command
            
        Returns:
            List[str]: List of regex patterns, or None if command not found
        """
        command_info = self.commands.get(name)
        return command_info["patterns"] if command_info else None


# Module test function
if __name__ == "__main__":
    print("Testing CommandParser module...")
    parser = CommandParser()
    
    # Test various commands
    test_commands = [
        "what time is it",
        "search google for python tutorials",
        "help",
        "status",
        "unknown command"
    ]
    
    print("Running command tests:")
    for cmd in test_commands:
        print(f"\nCommand: '{cmd}'")
        response = parser.parse_command(cmd)
        print(f"Response: {response}")
    
    print(f"\nTotal commands available: {len(parser.list_commands())}")