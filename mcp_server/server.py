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

from fastapi import FastAPI, Depends, HTTPException, Security, Request, Response
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
from .tools.google_calendar import GoogleCalendarTool
from .tools.gmail import GmailTool

# Import security utilities
from .security import RateLimiter, InputValidator, SecurityHeaders, hash_api_key, PARAMETER_SCHEMAS

logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="Jarvis MCP Server",
    description="Model Context Protocol server for Jarvis Assistant external tools",
    version="1.0.0"
)

# CORS middleware - restrict to specific origins in production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Security
security = HTTPBearer()
rate_limiter = RateLimiter(max_requests=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")), window_minutes=1)

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
    "system": SystemTool(),
    "google_calendar": GoogleCalendarTool(),
    "gmail": GmailTool()
}

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def verify_api_key_and_rate_limit(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Verify API key authentication and check rate limits.
    
    Args:
        request: FastAPI request object
        credentials: Bearer token credentials
        
    Returns:
        True if valid, raises HTTPException if invalid
    """
    # Check rate limiting first
    client_ip = get_client_ip(request)
    if not rate_limiter.is_allowed(client_ip):
        reset_time = rate_limiter.get_reset_time(client_ip)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int((reset_time - datetime.now()).total_seconds()))} if reset_time else {}
        )
    
    # Verify API key
    expected_key = os.getenv("MCP_API_KEY")
    if not expected_key:
        logger.error("MCP_API_KEY environment variable not configured")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error"
        )
    
    if credentials.credentials != expected_key:
        logger.warning(f"Invalid API key attempt from IP: {client_ip}, key hash: {hash_api_key(credentials.credentials)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    logger.info(f"Authenticated request from IP: {client_ip}")
    return True

@app.get("/health", response_model=HealthResponse)
async def health_check(response: Response):
    """Health check endpoint with security headers."""
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
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
    mcp_request: MCPRequest,
    request: Request,
    response: Response,
    authorized: bool = Depends(verify_api_key_and_rate_limit)
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
        # Add security headers
        for header, value in SecurityHeaders.get_headers().items():
            response.headers[header] = value
        
        # Validate tool exists
        if mcp_request.tool not in tools:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown tool: {mcp_request.tool}"
            )
        
        tool = tools[mcp_request.tool]
        
        # Validate parameters if schema exists
        if mcp_request.tool in PARAMETER_SCHEMAS:
            try:
                validated_params = InputValidator.validate_parameters(
                    mcp_request.parameters, 
                    PARAMETER_SCHEMAS[mcp_request.tool]
                )
                mcp_request.parameters = validated_params
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Parameter validation failed: {str(e)}")
        
        # Execute tool action
        result = await tool.execute(mcp_request.action, mcp_request.parameters)
        
        return MCPResponse(
            success=True,
            data=result,
            metadata={
                "tool": mcp_request.tool,
                "action": mcp_request.action,
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
                "tool": mcp_request.tool,
                "action": mcp_request.action,
                "error_time": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )

# Individual tool endpoints for direct access
@app.get("/search")
async def search_endpoint(
    q: str,
    request: Request,
    response: Response,
    num_results: int = 5,
    authorized: bool = Depends(verify_api_key_and_rate_limit)
):
    """Web search endpoint with input validation."""
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    # Validate parameters
    try:
        params = InputValidator.validate_parameters(
            {"query": q, "num_results": num_results},
            PARAMETER_SCHEMAS["search"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Parameter validation failed: {str(e)}")
    
    return await tools["search"].execute("search", params)

@app.get("/weather")
async def weather_endpoint(
    location: str,
    request: Request,
    response: Response,
    forecast: str = "false",
    authorized: bool = Depends(verify_api_key_and_rate_limit)
):
    """Weather information endpoint with input validation."""
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    # Validate parameters
    try:
        params = InputValidator.validate_parameters(
            {"location": location, "forecast": forecast},
            PARAMETER_SCHEMAS["weather"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Parameter validation failed: {str(e)}")
    
    # Convert string to boolean
    forecast_bool = params["forecast"].lower() in ("true", "1", "yes", "on")
    action = "forecast" if forecast_bool else "current"
    return await tools["weather"].execute(action, {"location": params["location"]})

@app.get("/crypto")
async def crypto_endpoint(
    symbol: str,
    request: Request,
    response: Response,
    vs_currency: str = "usd",
    authorized: bool = Depends(verify_api_key_and_rate_limit)
):
    """Cryptocurrency price endpoint with input validation."""
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    # Validate parameters
    try:
        params = InputValidator.validate_parameters(
            {"symbol": symbol, "vs_currency": vs_currency},
            PARAMETER_SCHEMAS["crypto"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Parameter validation failed: {str(e)}")
    
    return await tools["crypto"].execute("price", params)

@app.get("/news")
async def news_endpoint(
    request: Request,
    response: Response,
    category: str = "general",
    country: str = "us",
    page_size: int = 10,
    authorized: bool = Depends(verify_api_key_and_rate_limit)
):
    """News headlines endpoint with input validation."""
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    # Validate parameters
    try:
        params = InputValidator.validate_parameters(
            {"category": category, "country": country, "page_size": page_size},
            PARAMETER_SCHEMAS["news"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Parameter validation failed: {str(e)}")
    
    return await tools["news"].execute("headlines", params)

@app.post("/gmail")
async def gmail_endpoint(
    action: str,
    parameters: Dict[str, Any],
    request: Request,
    response: Response,
    authorized: bool = Depends(verify_api_key_and_rate_limit)
):
    """Gmail integration endpoint with OAuth2 authentication and AI features."""
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    # Input validation
    action = InputValidator.sanitize_string(action, 50)
    
    # Rate limiting for Google APIs (more restrictive)
    client_ip = get_client_ip(request)
    if not rate_limiter.is_allowed(client_ip, max_requests=30):  # 30 requests per minute for Google APIs
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for Gmail API"
        )
    
    return await tools["gmail"].execute(action, parameters)

@app.post("/calendar")
async def calendar_endpoint(
    action: str,
    parameters: Dict[str, Any],
    request: Request,
    response: Response,
    authorized: bool = Depends(verify_api_key_and_rate_limit)
):
    """Google Calendar operations endpoint with security.""" 
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    # Basic input validation
    action = InputValidator.sanitize_string(action, 50)
    return await tools["calendar"].execute(action, parameters)

@app.post("/google_calendar")
async def google_calendar_endpoint(
    action: str,
    parameters: Dict[str, Any],
    request: Request,
    response: Response,
    authorized: bool = Depends(verify_api_key_and_rate_limit)
):
    """Google Calendar integration endpoint with OAuth2 authentication."""
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    # Input validation
    action = InputValidator.sanitize_string(action, 50)
    
    # Rate limiting for Google APIs (more restrictive)
    client_ip = get_client_ip(request)
    if not rate_limiter.is_allowed(client_ip, max_requests=30):  # 30 requests per minute for Google APIs
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for Google Calendar API"
        )
    
    return await tools["google_calendar"].execute(action, parameters)

class FilesystemRequest(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}

@app.post("/fs/{path:path}")
async def filesystem_endpoint(
    path: str,
    fs_request: FilesystemRequest,
    request: Request,
    response: Response,
    authorized: bool = Depends(verify_api_key_and_rate_limit)
):
    """Filesystem operations endpoint with security."""
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    # Input validation
    path = InputValidator.sanitize_string(path, 500)
    action = InputValidator.sanitize_string(fs_request.action, 50)
    
    fs_request.parameters["path"] = path
    return await tools["filesystem"].execute(action, fs_request.parameters)

@app.post("/system/{command}")
async def system_endpoint(
    command: str,
    request: Request,
    response: Response,
    authorized: bool = Depends(verify_api_key_and_rate_limit),
    parameters: Dict[str, Any] = {}
):
    """System control endpoint with security."""
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    # Input validation
    command = InputValidator.sanitize_string(command, 50)
    parameters["command"] = command
    
    logger.warning(f"System command requested: {command} from IP: {get_client_ip(request)}")
    return await tools["system"].execute("run", parameters)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)