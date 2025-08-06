"""
Weather tool for MCP server.

Provides current weather and forecast data using OpenWeatherMap API.
Supports location-based weather queries and forecast information.
"""

import os
import aiohttp
from typing import Dict, Any
from . import BaseTool

class WeatherTool(BaseTool):
    """Weather data tool using OpenWeatherMap API."""
    
    def __init__(self):
        super().__init__("weather")
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute weather action.
        
        Args:
            action: "current" or "forecast"
            parameters: {"location": str, "units": str}
            
        Returns:
            Weather data
        """
        if not self.api_key:
            return {"error": "OpenWeatherMap API key not configured"}
            
        location = parameters.get("location", "London")
        units = parameters.get("units", "metric")
        
        if action == "current":
            return await self._get_current_weather(location, units)
        elif action == "forecast":
            return await self._get_forecast(location, units)
        else:
            return {"error": f"Unknown weather action: {action}"}
    
    async def _get_current_weather(self, location: str, units: str) -> Dict[str, Any]:
        """Get current weather for location."""
        url = f"{self.base_url}/weather"
        params = {
            "q": location,
            "appid": self.api_key,
            "units": units
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "location": data["name"],
                            "country": data["sys"]["country"],
                            "temperature": data["main"]["temp"],
                            "description": data["weather"][0]["description"],
                            "humidity": data["main"]["humidity"],
                            "pressure": data["main"]["pressure"],
                            "wind_speed": data.get("wind", {}).get("speed"),
                            "units": units
                        }
                    else:
                        return {"error": f"Weather API error: {response.status}"}
        except Exception as e:
            return {"error": f"Weather request failed: {str(e)}"}
    
    async def _get_forecast(self, location: str, units: str) -> Dict[str, Any]:
        """Get weather forecast for location."""
        url = f"{self.base_url}/forecast"
        params = {
            "q": location,
            "appid": self.api_key,
            "units": units,
            "cnt": 16  # 5 days, 3-hour intervals
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        forecast_items = []
                        
                        for item in data["list"]:
                            forecast_items.append({
                                "datetime": item["dt_txt"],
                                "temperature": item["main"]["temp"],
                                "description": item["weather"][0]["description"],
                                "humidity": item["main"]["humidity"],
                                "wind_speed": item.get("wind", {}).get("speed")
                            })
                        
                        return {
                            "location": data["city"]["name"],
                            "country": data["city"]["country"],
                            "forecast": forecast_items,
                            "units": units
                        }
                    else:
                        return {"error": f"Forecast API error: {response.status}"}
        except Exception as e:
            return {"error": f"Forecast request failed: {str(e)}"}
    
    def health_check(self) -> bool:
        """Check if weather tool is healthy."""
        return bool(self.api_key)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get weather tool capabilities."""
        return {
            "name": self.name,
            "enabled": self.enabled and bool(self.api_key),
            "actions": [
                {
                    "name": "current",
                    "description": "Get current weather for location",
                    "parameters": ["location", "units"]
                },
                {
                    "name": "forecast", 
                    "description": "Get weather forecast for location",
                    "parameters": ["location", "units"]
                }
            ]
        }