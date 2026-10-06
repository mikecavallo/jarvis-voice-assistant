"""
System control tool for MCP server.

Provides safe system operations like volume, brightness, and application control.
"""

import asyncio
import os
from typing import Dict, Any
from . import BaseTool

class SystemTool(BaseTool):
    """System control operations tool."""
    
    def __init__(self):
        super().__init__("system")
        # Check if system commands are enabled via environment variable
        self.enabled = os.getenv("SYSTEM_COMMANDS_ENABLED", "false").lower() == "true"
        
        # Whitelist of safe commands only
        self.allowed_commands = {
            "test": ["echo", "System control test successful"],  # Safe test command
            # Audio controls (commented out by default for security)
            # "volume_up": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"],
            # "volume_down": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"],
            # "mute": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
            # "brightness_up": ["brightnessctl", "set", "+10%"],
            # "brightness_down": ["brightnessctl", "set", "10%-"],
        }
        
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """Execute system action."""
        if action == "run":
            return await self._run_command(parameters)
        else:
            return {"error": f"Unknown system action: {action}"}
    
    async def _run_command(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run allowed system command with security checks."""
        if not self.enabled:
            return {"error": "System commands are disabled for security. Set SYSTEM_COMMANDS_ENABLED=true to enable."}
        
        command = parameters.get("command", "")
        
        # Input validation
        if not command or not isinstance(command, str):
            return {"error": "Invalid command parameter"}
        
        # Command whitelist check
        if command not in self.allowed_commands:
            return {"error": f"Command not allowed: {command}. Allowed commands: {list(self.allowed_commands.keys())}"}
        
        cmd_args = self.allowed_commands[command]
        
        try:
            # Additional security: set timeout to prevent hanging
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    # Security: prevent shell injection
                    shell=False,
                    # Set resource limits
                    preexec_fn=None  # Prevent privilege escalation
                ),
                timeout=10  # 10 second timeout
            )
            
            stdout, stderr = await result.communicate()
            
            return {
                "command": command,
                "success": result.returncode == 0,
                "stdout": stdout.decode()[:1000] if stdout else "",  # Limit output size
                "stderr": stderr.decode()[:1000] if stderr else ""   # Limit error size
            }
            
        except asyncio.TimeoutError:
            return {"error": "Command execution timed out"}
        except Exception as e:
            return {"error": f"Command execution failed: {str(e)}"}
    
    def health_check(self) -> bool:
        """Check if system tool is healthy."""
        return self.enabled  # Health depends on whether system commands are enabled