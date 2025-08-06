"""
News tool for MCP server.

Provides news headlines and articles using NewsAPI.
"""

import os
import aiohttp
from typing import Dict, Any
from . import BaseTool

class NewsTool(BaseTool):
    """News tool using NewsAPI."""
    
    def __init__(self):
        super().__init__("news")
        self.api_key = os.getenv("NEWS_API_KEY")
        self.base_url = "https://newsapi.org/v2"
        
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """Execute news action."""
        if not self.api_key:
            return {"error": "NewsAPI key not configured"}
            
        if action == "headlines":
            return await self._get_headlines(parameters)
        elif action == "search":
            return await self._search_articles(parameters)
        else:
            return {"error": f"Unknown news action: {action}"}
    
    async def _get_headlines(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get top headlines."""
        category = parameters.get("category", "general")
        country = parameters.get("country", "us")
        page_size = parameters.get("page_size", 10)
        
        url = f"{self.base_url}/top-headlines"
        params = {
            "apiKey": self.api_key,
            "category": category,
            "country": country,
            "pageSize": page_size
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = []
                        
                        for article in data.get("articles", []):
                            articles.append({
                                "title": article.get("title"),
                                "description": article.get("description"),
                                "url": article.get("url"),
                                "source": article.get("source", {}).get("name"),
                                "published_at": article.get("publishedAt")
                            })
                        
                        return {"articles": articles, "total_results": data.get("totalResults")}
                    else:
                        return {"error": f"News API error: {response.status}"}
        except Exception as e:
            return {"error": f"News request failed: {str(e)}"}
    
    async def _search_articles(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Search for articles."""
        query = parameters.get("query", "")
        page_size = parameters.get("page_size", 10)
        
        url = f"{self.base_url}/everything"
        params = {
            "apiKey": self.api_key,
            "q": query,
            "pageSize": page_size,
            "sortBy": "relevancy"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = []
                        
                        for article in data.get("articles", []):
                            articles.append({
                                "title": article.get("title"),
                                "description": article.get("description"),
                                "url": article.get("url"),
                                "source": article.get("source", {}).get("name"),
                                "published_at": article.get("publishedAt")
                            })
                        
                        return {"articles": articles, "query": query}
                    else:
                        return {"error": f"Search API error: {response.status}"}
        except Exception as e:
            return {"error": f"Search request failed: {str(e)}"}
    
    def health_check(self) -> bool:
        """Check if news tool is healthy."""
        return bool(self.api_key)