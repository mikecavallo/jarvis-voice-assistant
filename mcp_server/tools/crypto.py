"""
Cryptocurrency tool for MCP server.

Provides crypto price data and market information using CoinGecko API.
Supports real-time pricing, market data, and trending information.
"""

import aiohttp
from typing import Dict, Any, List
from . import BaseTool

class CryptoTool(BaseTool):
    """Cryptocurrency data tool using CoinGecko API."""
    
    def __init__(self):
        super().__init__("crypto")
        self.base_url = "https://api.coingecko.com/api/v3"
        
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute crypto action.
        
        Args:
            action: "price", "market", or "trending"
            parameters: Action-specific parameters
            
        Returns:
            Crypto data
        """
        if action == "price":
            return await self._get_price(parameters)
        elif action == "market":
            return await self._get_market_data(parameters)
        elif action == "trending":
            return await self._get_trending()
        else:
            return {"error": f"Unknown crypto action: {action}"}
    
    async def _get_price(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get cryptocurrency price."""
        symbol = parameters.get("symbol", "bitcoin").lower()
        vs_currency = parameters.get("vs_currency", "usd").lower()
        
        url = f"{self.base_url}/simple/price"
        params = {
            "ids": symbol,
            "vs_currencies": vs_currency,
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if symbol in data:
                            coin_data = data[symbol]
                            return {
                                "symbol": symbol,
                                "price": coin_data.get(vs_currency),
                                "currency": vs_currency,
                                "market_cap": coin_data.get(f"{vs_currency}_market_cap"),
                                "volume_24h": coin_data.get(f"{vs_currency}_24h_vol"),
                                "change_24h": coin_data.get(f"{vs_currency}_24h_change")
                            }
                        else:
                            return {"error": f"Cryptocurrency '{symbol}' not found"}
                    else:
                        return {"error": f"CoinGecko API error: {response.status}"}
        except Exception as e:
            return {"error": f"Crypto price request failed: {str(e)}"}
    
    async def _get_market_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get cryptocurrency market data."""
        symbol = parameters.get("symbol", "bitcoin").lower()
        
        url = f"{self.base_url}/coins/{symbol}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        market_data = data.get("market_data", {})
                        
                        return {
                            "symbol": data.get("symbol", "").upper(),
                            "name": data.get("name"),
                            "current_price": market_data.get("current_price", {}).get("usd"),
                            "market_cap": market_data.get("market_cap", {}).get("usd"),
                            "total_volume": market_data.get("total_volume", {}).get("usd"),
                            "price_change_24h": market_data.get("price_change_24h"),
                            "price_change_percentage_24h": market_data.get("price_change_percentage_24h"),
                            "market_cap_rank": market_data.get("market_cap_rank"),
                            "ath": market_data.get("ath", {}).get("usd"),
                            "atl": market_data.get("atl", {}).get("usd")
                        }
                    else:
                        return {"error": f"Market data API error: {response.status}"}
        except Exception as e:
            return {"error": f"Market data request failed: {str(e)}"}
    
    async def _get_trending(self) -> Dict[str, Any]:
        """Get trending cryptocurrencies."""
        url = f"{self.base_url}/search/trending"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        coins = data.get("coins", [])
                        
                        trending_coins = []
                        for coin_info in coins[:10]:  # Top 10
                            coin = coin_info.get("item", {})
                            trending_coins.append({
                                "name": coin.get("name"),
                                "symbol": coin.get("symbol"),
                                "market_cap_rank": coin.get("market_cap_rank"),
                                "thumb": coin.get("thumb")
                            })
                        
                        return {"trending_coins": trending_coins}
                    else:
                        return {"error": f"Trending API error: {response.status}"}
        except Exception as e:
            return {"error": f"Trending request failed: {str(e)}"}
    
    def health_check(self) -> bool:
        """Check if crypto tool is healthy."""
        return True  # CoinGecko doesn't require API key for basic endpoints
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get crypto tool capabilities."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "actions": [
                {
                    "name": "price",
                    "description": "Get cryptocurrency price",
                    "parameters": ["symbol", "vs_currency"]
                },
                {
                    "name": "market",
                    "description": "Get detailed market data for cryptocurrency",
                    "parameters": ["symbol"]
                },
                {
                    "name": "trending",
                    "description": "Get trending cryptocurrencies",
                    "parameters": []
                }
            ]
        }