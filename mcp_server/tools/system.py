"""
System control tool for MCP server.

Provides safe system operations like volume, brightness, and application control.
"""

import asyncio
import subprocess
from typing import Dict, Any
from . import BaseTool

class SystemTool(BaseTool):
    """System control operations tool."""
    
    def __init__(self):
        super().__init__("system")
        self.allowed_commands = {
            "volume_up": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"],
            "volume_down": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"],
            "mute": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
            "brightness_up": ["brightnessctl", "set", "+10%"],
            "brightness_down": ["brightnessctl", "set", "10%-"],
            "test": ["echo", "System control test successful"]  # Safe test command
        }
        
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """Execute system action."""
        if action == "run":
            return await self._run_command(parameters)
        else:
            return {"error": f"Unknown system action: {action}"}
    
    async def _run_command(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run allowed system command."""
        command = parameters.get("command", "")
        
        if command not in self.allowed_commands:
            return {"error": f"Command not allowed: {command}"}
        
        cmd_args = self.allowed_commands[command]
        
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            return {
                "command": command,
                "success": result.returncode == 0,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else ""
            }
            
        except Exception as e:
            return {"error": f"Command execution failed: {str(e)}"}
    
    def health_check(self) -> bool:
        """Check if system tool is healthy."""
        return True  # Basic system commands should always be available