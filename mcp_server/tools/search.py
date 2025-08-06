"""
Web search tool for MCP server.

Provides web search capabilities using SerpAPI for Google search results.
"""

import os
import aiohttp
from typing import Dict, Any
from . import BaseTool

class SearchTool(BaseTool):
    """Web search tool using SerpAPI."""
    
    def __init__(self):
        super().__init__("search")
        self.api_key = os.getenv("SERPAPI_KEY")
        self.base_url = "https://serpapi.com/search"
        
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """Execute search action."""
        if not self.api_key:
            return {"error": "SerpAPI key not configured"}
            
        if action == "search":
            return await self._search(parameters)
        else:
            return {"error": f"Unknown search action: {action}"}
    
    async def _search(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search."""
        query = parameters.get("query", "")
        num_results = parameters.get("num_results", 5)
        
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": num_results
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        for result in data.get("organic_results", []):
                            results.append({
                                "title": result.get("title"),
                                "link": result.get("link"),
                                "snippet": result.get("snippet")
                            })
                        
                        return {"results": results, "query": query}
                    else:
                        return {"error": f"Search API error: {response.status}"}
        except Exception as e:
            return {"error": f"Search request failed: {str(e)}"}
    
    def health_check(self) -> bool:
        """Check if search tool is healthy."""
        return bool(self.api_key)