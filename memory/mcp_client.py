"""
MCP Client for Jarvis Assistant.

This module provides a client interface to communicate with the MCP server
and execute various tools like weather, crypto, news, search, etc.
"""

import aiohttp
import re
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

def _contains_any(text: str, keywords: List[str]) -> bool:
    """Whole-word/phrase match, so "ls" does not fire on "emails" or "eth" on "something"."""
    return any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in keywords)


@dataclass
class MCPTool:
    """Represents an available MCP tool."""
    name: str
    endpoint: str
    description: str
    parameters: List[str]
    requires_auth: bool = True

class MCPClient:
    """
    Client for communicating with Jarvis MCP server.
    
    This client provides a clean interface for Jarvis to access
    real-time data through various tools.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize MCP client."""
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.available_tools = {}
        self._initialize_tools()
        
    def _initialize_tools(self):
        """Initialize available MCP tools."""
        self.available_tools = {
            "crypto": MCPTool(
                name="crypto",
                endpoint="/crypto",
                description="Get cryptocurrency prices and market data",
                parameters=["symbol"],
                requires_auth=True
            ),
            "weather": MCPTool(
                name="weather", 
                endpoint="/weather",
                description="Get current weather and forecasts for locations",
                parameters=["location", "forecast"],
                requires_auth=True
            ),
            "news": MCPTool(
                name="news",
                endpoint="/news", 
                description="Get latest news articles and headlines",
                parameters=["query", "category"],
                requires_auth=True
            ),
            "search": MCPTool(
                name="search",
                endpoint="/search",
                description="Search the web for information",
                parameters=["query", "num_results"],
                requires_auth=True
            ),
            "filesystem": MCPTool(
                name="filesystem",
                endpoint="/filesystem",
                description="List and browse files and directories",
                parameters=["path", "operation"],
                requires_auth=False
            ),
            "system": MCPTool(
                name="system",
                endpoint="/system",
                description="Execute system commands safely",
                parameters=["command"],
                requires_auth=False
            ),
            "calendar": MCPTool(
                name="calendar",
                endpoint="/google_calendar",
                description="Access and manage Google Calendar events, schedule meetings, check availability",
                parameters=["action", "date", "event_details"],
                requires_auth=True
            ),
            "gmail": MCPTool(
                name="gmail", 
                endpoint="/gmail",
                description="Read, send, and manage Gmail emails with AI analysis",
                parameters=["action", "email_details"],
                requires_auth=True
            )
        }
        
        logger.info(f"MCP Client initialized with {len(self.available_tools)} tools")
    
    async def _get_session(self):
        """Get or create aiohttp session."""
        # Always create a fresh session to avoid event loop issues
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = aiohttp.ClientSession()
        return self.session
    
    async def test_connection(self) -> bool:
        """Test connection to MCP server."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"MCP server connection failed: {e}")
            return False
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call an MCP tool with parameters.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool parameters
            
        Returns:
            Dict containing tool response
        """
        if tool_name not in self.available_tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.available_tools[tool_name]
        session = await self._get_session()
        
        try:
            # Prepare request
            url = f"{self.base_url}{tool.endpoint}"
            headers = {}
            
            # Add API key for tools that require auth
            if tool.requires_auth:
                api_key = os.getenv("MCP_API_KEY")
                if not api_key:
                    raise ValueError("MCP_API_KEY environment variable not set")
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Make request - use POST for calendar and gmail, GET for others
            if tool_name in ["calendar", "gmail"]:
                # POST endpoints - action as query param, other params in JSON body
                headers["Content-Type"] = "application/json"
                action = kwargs.pop("action", "list_events")
                url_with_action = f"{url}?action={action}"
                json_data = kwargs.get("parameters", kwargs)
                async with session.post(url_with_action, json=json_data, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"MCP tool '{tool_name}' executed successfully")
                        return {"success": True, "data": data}
                    else:
                        error_text = await response.text()
                        logger.error(f"MCP tool '{tool_name}' failed: {response.status} - {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
            else:
                # GET endpoints with query params
                async with session.get(url, params=kwargs, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"MCP tool '{tool_name}' executed successfully")
                        return {"success": True, "data": data}
                    else:
                        error_text = await response.text()
                        logger.error(f"MCP tool '{tool_name}' failed: {response.status} - {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"Error calling MCP tool '{tool_name}': {e}")
            return {"success": False, "error": str(e)}
    
    async def get_crypto_price(self, symbol: str) -> Dict[str, Any]:
        """Get cryptocurrency price."""
        return await self.call_tool("crypto", symbol=symbol)
    
    async def get_weather(self, location: str, forecast: bool = False) -> Dict[str, Any]:
        """Get weather information."""
        return await self.call_tool("weather", location=location, forecast=str(forecast).lower())
    
    async def get_news(self, query: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        """Get news articles."""
        params = {}
        if query:
            params["query"] = query
        if category:
            params["category"] = category
        return await self.call_tool("news", **params)
    
    async def search_web(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Search the web."""
        return await self.call_tool("search", query=query, num_results=num_results)
    
    async def list_files(self, path: str = ".") -> Dict[str, Any]:
        """List files in directory."""
        return await self.call_tool("filesystem", path=path, operation="list")
    
    async def run_system_command(self, command: str) -> Dict[str, Any]:
        """Run system command safely."""
        return await self.call_tool("system", command=command)
    
    def get_available_tools(self) -> Dict[str, str]:
        """Get list of available tools with descriptions."""
        return {name: tool.description for name, tool in self.available_tools.items()}
    
    def can_handle_request(self, user_input: str) -> Optional[str]:
        """
        Analyze user input to determine if MCP tools should be used.
        
        Args:
            user_input: User's message
            
        Returns:
            Tool name if applicable, None otherwise
        """
        user_lower = user_input.lower()
        
        # Crypto keywords
        crypto_keywords = ["bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency", "price of", "dogecoin", "ada", "solana"]
        if _contains_any(user_lower, crypto_keywords):
            return "crypto"
        
        # Weather keywords  
        weather_keywords = ["weather", "temperature", "forecast", "rain", "sunny", "cloudy", "hot", "cold"]
        if _contains_any(user_lower, weather_keywords):
            return "weather"
        
        # News keywords
        news_keywords = ["news", "latest news", "headlines", "breaking news", "current events"]
        if _contains_any(user_lower, news_keywords):
            return "news"
        
        # Search keywords
        search_keywords = ["search for", "look up", "find information", "google", "web search"]
        if _contains_any(user_lower, search_keywords):
            return "search"
        
        # File system keywords
        fs_keywords = ["list files", "show files", "directory", "folder contents", "ls", "dir"]
        if _contains_any(user_lower, fs_keywords):
            return "filesystem"
        
        # Calendar keywords
        calendar_keywords = ["calendar", "schedule", "meeting", "appointment", "event", "what's on my calendar", "free time", "available", "busy", "august", "september", "today", "tomorrow", "next week", "next month", "add an event", "create event", "book appointment", "add appointment", "schedule meeting", "dentist"]
        if _contains_any(user_lower, calendar_keywords):
            return "calendar"
        
        # Gmail keywords
        gmail_keywords = ["email", "gmail", "inbox", "messages", "send email", "draft", "mail", "unread emails", "recent emails"]
        if _contains_any(user_lower, gmail_keywords):
            return "gmail"
        
        return None
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.session and not self.session.closed:
            try:
                import asyncio
                asyncio.create_task(self.session.close())
            except Exception:
                pass

# Global instance
mcp_client = MCPClient()