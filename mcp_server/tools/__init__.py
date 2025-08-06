"""
MCP Tools package for Jarvis Assistant.

This package contains all external tool integrations that Jarvis can use
through the MCP (Model Context Protocol) server.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    """
    Base class for all MCP tools.
    
    All tool implementations should inherit from this class and implement
    the required methods for consistent behavior across the MCP server.
    """
    
    def __init__(self, name: str):
        """
        Initialize base tool.
        
        Args:
            name: Tool name identifier
        """
        self.name = name
        self.enabled = True
    
    @abstractmethod
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a tool action with given parameters.
        
        Args:
            action: Action to perform
            parameters: Action parameters
            
        Returns:
            Tool execution result
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the tool is healthy and available.
        
        Returns:
            True if tool is healthy, False otherwise
        """
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get tool capabilities and supported actions.
        
        Returns:
            Dictionary of supported actions and their parameters
        """
        return {
            "name": self.name,
            "enabled": self.enabled,
            "actions": []
        }