"""
Security utilities for MCP server.

Provides input validation, sanitization, rate limiting, and other security functions.
"""

import re
import time
import hashlib
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Token bucket rate limiter for API endpoints."""
    
    def __init__(self, max_requests: int = 60, window_minutes: int = 1):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the time window
            window_minutes: Time window in minutes
        """
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.requests = defaultdict(deque)
    
    def is_allowed(self, client_ip: str) -> bool:
        """
        Check if request is allowed for client IP.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        client_requests = self.requests[client_ip]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] < now - self.window_seconds:
            client_requests.popleft()
        
        # Check if under rate limit
        if len(client_requests) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return False
        
        # Add current request
        client_requests.append(now)
        return True
    
    def get_reset_time(self, client_ip: str) -> Optional[datetime]:
        """Get when the rate limit resets for a client."""
        client_requests = self.requests[client_ip]
        if not client_requests:
            return None
        
        oldest_request = client_requests[0]
        return datetime.fromtimestamp(oldest_request + self.window_seconds)

class InputValidator:
    """Input validation and sanitization utilities."""
    
    # Regex patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    CRYPTO_SYMBOL_PATTERN = re.compile(r'^[A-Z]{2,10}$')
    LOCATION_PATTERN = re.compile(r'^[a-zA-Z0-9\s,.-]{1,100}$')
    SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s._-]{1,255}$')
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        re.compile(r'[;&|`$(){}[\]\\]'),  # Shell injection characters
        re.compile(r'<script', re.IGNORECASE),  # XSS attempts
        re.compile(r'javascript:', re.IGNORECASE),  # JavaScript URLs
        re.compile(r'data:', re.IGNORECASE),  # Data URLs
        re.compile(r'vbscript:', re.IGNORECASE),  # VBScript URLs
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 255) -> str:
        """
        Sanitize string input by removing dangerous characters.
        
        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Trim and limit length
        value = value.strip()[:max_length]
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(value):
                raise ValueError(f"Input contains dangerous characters: {value}")
        
        return value
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email address format."""
        if not isinstance(email, str) or len(email) > 254:
            return False
        return bool(cls.EMAIL_PATTERN.match(email))
    
    @classmethod
    def validate_crypto_symbol(cls, symbol: str) -> bool:
        """Validate cryptocurrency symbol."""
        if not isinstance(symbol, str):
            return False
        return bool(cls.CRYPTO_SYMBOL_PATTERN.match(symbol.upper()))
    
    @classmethod
    def validate_location(cls, location: str) -> bool:
        """Validate location string."""
        if not isinstance(location, str):
            return False
        return bool(cls.LOCATION_PATTERN.match(location))
    
    @classmethod
    def validate_safe_string(cls, value: str) -> bool:
        """Validate that string contains only safe characters."""
        if not isinstance(value, str):
            return False
        return bool(cls.SAFE_STRING_PATTERN.match(value))
    
    @classmethod
    def validate_parameters(cls, params: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters against a schema.
        
        Args:
            params: Parameters to validate
            schema: Schema defining expected parameters and types
            
        Returns:
            Validated and sanitized parameters
            
        Raises:
            ValueError: If validation fails
        """
        validated = {}
        
        for key, config in schema.items():
            param_type = config.get('type')
            required = config.get('required', False)
            default = config.get('default')
            validator = config.get('validator')
            
            if key not in params:
                if required:
                    raise ValueError(f"Required parameter missing: {key}")
                if default is not None:
                    validated[key] = default
                continue
            
            value = params[key]
            
            # Type validation
            if param_type and not isinstance(value, param_type):
                if param_type == str and isinstance(value, (int, float)):
                    value = str(value)  # Allow string conversion for numbers
                else:
                    raise ValueError(f"Parameter {key} must be of type {param_type.__name__}")
            
            # String sanitization
            if isinstance(value, str):
                value = cls.sanitize_string(value, config.get('max_length', 255))
            
            # Custom validation
            if validator and not validator(value):
                raise ValueError(f"Parameter {key} failed validation")
            
            validated[key] = value
        
        return validated

class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }
    
    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """Get security headers dictionary."""
        return cls.SECURITY_HEADERS.copy()

def hash_api_key(api_key: str) -> str:
    """
    Hash API key for secure logging.
    
    Args:
        api_key: API key to hash
        
    Returns:
        SHA256 hash of the API key (first 8 characters)
    """
    if not api_key:
        return "empty"
    
    hash_obj = hashlib.sha256(api_key.encode())
    return hash_obj.hexdigest()[:8]

# Parameter schemas for different endpoints
PARAMETER_SCHEMAS = {
    "search": {
        "query": {"type": str, "required": True, "max_length": 500, "validator": InputValidator.validate_safe_string},
        "num_results": {"type": int, "default": 5, "validator": lambda x: 1 <= x <= 20}
    },
    "weather": {
        "location": {"type": str, "required": True, "max_length": 100, "validator": InputValidator.validate_location},
        "forecast": {"type": str, "default": "false"}
    },
    "crypto": {
        "symbol": {"type": str, "required": True, "validator": InputValidator.validate_crypto_symbol},
        "vs_currency": {"type": str, "default": "usd", "validator": InputValidator.validate_crypto_symbol}
    },
    "news": {
        "category": {"type": str, "default": "general", "validator": InputValidator.validate_safe_string},
        "country": {"type": str, "default": "us", "validator": lambda x: len(x) == 2 and x.isalpha()},
        "page_size": {"type": int, "default": 10, "validator": lambda x: 1 <= x <= 100}
    }
}