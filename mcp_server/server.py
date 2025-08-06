"""
MCP (Model Context Protocol) Server for Jarvis Assistant.

This FastAPI server provides a centralized interface for all external tools and APIs.
It implements the MCP specification and serves as a bridge between Jarvis agents
and external services like weather, crypto, news, email, calendar, etc.

The server provides:
- RESTful API endpoints for each tool category
- Common JSON schema and authentication
- Rate limiting and error handling
- Health monitoring and diagnostics
"""

from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import tool modules
from .tools.weather import WeatherTool
from .tools.crypto import CryptoTool
from .tools.search import SearchTool
from .tools.news import NewsTool
from .tools.email import EmailTool
from .tools.calendar import CalendarTool
from .tools.filesystem import FilesystemTool
from .tools.system import SystemTool

logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="Jarvis MCP Server",
    description="Model Context Protocol server for Jarvis Assistant external tools",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models for API schemas
class MCPRequest(BaseModel):
    """Base MCP request model."""
    tool: str
    action: str
    parameters: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    """Base MCP response model."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: str

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    tools: Dict[str, bool]

# Tool instances
tools = {
    "weather": WeatherTool(),
    "crypto": CryptoTool(),
    "search": SearchTool(),
    "news": NewsTool(),
    "email": EmailTool(),
    "calendar": CalendarTool(),
    "filesystem": FilesystemTool(),
    "system": SystemTool()
}

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify API key authentication.
    
    Args:
        credentials: Bearer token credentials
        
    Returns:
        True if valid, raises HTTPException if invalid
    """
    expected_key = os.getenv("MCP_API_KEY", "jarvis-mcp-key-2025")
    
    if credentials.credentials != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return True

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring server status.
    
    Returns:
        Server health status and tool availability
    """
    tool_status = {}
    
    for name, tool in tools.items():
        try:
            tool_status[name] = tool.health_check()
        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            tool_status[name] = False
    
    return HealthResponse(
        status="healthy" if all(tool_status.values()) else "degraded",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        tools=tool_status
    )

@app.post("/mcp", response_model=MCPResponse)
async def mcp_endpoint(
    request: MCPRequest,
    authorized: bool = Depends(verify_api_key)
):
    """
    Main MCP endpoint for tool execution.
    
    Args:
        request: MCP request with tool, action, and parameters
        authorized: API key verification result
        
    Returns:
        MCP response with results or error information
    """
    try:
        # Validate tool exists
        if request.tool not in tools:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown tool: {request.tool}"
            )
        
        tool = tools[request.tool]
        
        # Execute tool action
        result = await tool.execute(request.action, request.parameters)
        
        return MCPResponse(
            success=True,
            data=result,
            metadata={
                "tool": request.tool,
                "action": request.action,
                "execution_time": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP execution error: {e}")
        return MCPResponse(
            success=False,
            error=str(e),
            metadata={
                "tool": request.tool,
                "action": request.action,
                "error_time": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )

# Individual tool endpoints for direct access
@app.get("/search")
async def search_endpoint(
    q: str,
    num_results: int = 5,
    authorized: bool = Depends(verify_api_key)
):
    """Web search endpoint."""
    return await tools["search"].execute("search", {"query": q, "num_results": num_results})

@app.get("/weather")
async def weather_endpoint(
    location: str,
    forecast: str = "false",
    authorized: bool = Depends(verify_api_key)
):
    """Weather information endpoint."""
    # Convert string to boolean
    forecast_bool = forecast.lower() in ("true", "1", "yes", "on")
    action = "forecast" if forecast_bool else "current"
    return await tools["weather"].execute(action, {"location": location})

@app.get("/crypto")
async def crypto_endpoint(
    symbol: str,
    vs_currency: str = "usd",
    authorized: bool = Depends(verify_api_key)
):
    """Cryptocurrency price endpoint."""
    return await tools["crypto"].execute("price", {"symbol": symbol, "vs_currency": vs_currency})

@app.get("/news")
async def news_endpoint(
    category: str = "general",
    country: str = "us",
    page_size: int = 10,
    authorized: bool = Depends(verify_api_key)
):
    """News headlines endpoint."""
    return await tools["news"].execute("headlines", {
        "category": category,
        "country": country,
        "page_size": page_size
    })

@app.post("/gmail")
async def gmail_endpoint(
    action: str,
    parameters: Dict[str, Any],
    authorized: bool = Depends(verify_api_key)
):
    """Gmail operations endpoint."""
    return await tools["email"].execute(action, parameters)

@app.post("/calendar")
async def calendar_endpoint(
    action: str,
    parameters: Dict[str, Any],
    authorized: bool = Depends(verify_api_key)
):
    """Google Calendar operations endpoint.""" 
    return await tools["calendar"].execute(action, parameters)

class FilesystemRequest(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}

@app.post("/fs/{path:path}")
async def filesystem_endpoint(
    path: str,
    request: FilesystemRequest,
    authorized: bool = Depends(verify_api_key)
):
    """Filesystem operations endpoint."""
    request.parameters["path"] = path
    return await tools["filesystem"].execute(request.action, request.parameters)

@app.post("/system/{command}")
async def system_endpoint(
    command: str,
    parameters: Dict[str, Any] = {},
    authorized: bool = Depends(verify_api_key)
):
    """System control endpoint."""
    parameters["command"] = command
    return await tools["system"].execute("run", parameters)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)