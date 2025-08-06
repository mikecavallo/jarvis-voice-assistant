"""
Modular LLM Interface for Jarvis Assistant.

This module provides a flexible interface for different LLM providers
(OpenAI, Ollama, etc.) with consistent API and easy switching between models.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """Represents a chat message with role and content."""
    role: str  # "system", "user", "assistant"
    content: str

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def chat(self, messages: List[ChatMessage], **kwargs) -> str:
        """Send chat messages and get response."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the current model name."""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            model: Model name (gpt-4o-mini, gpt-4o, gpt-3.5-turbo, etc.)
            api_key: OpenAI API key (defaults to env var)
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info(f"OpenAI provider initialized with model: {model}")
            except ImportError:
                logger.error("OpenAI package not installed")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
    
    async def chat(self, messages: List[ChatMessage], **kwargs) -> str:
        """Send chat to OpenAI and get response."""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        
        try:
            # Convert to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content} 
                for msg in messages
            ]
            
            # Set default parameters
            params = {
                "model": self.model,
                "messages": openai_messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 500),
            }
            
            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise RuntimeError(f"OpenAI request failed: {e}")
    
    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        return self.client is not None and bool(self.api_key)
    
    def get_model_name(self) -> str:
        """Get current model name."""
        return self.model

class OllamaProvider(LLMProvider):
    """Ollama local LLM provider implementation."""
    
    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.
        
        Args:
            model: Model name (llama2, mistral, etc.)
            base_url: Ollama server URL
        """
        self.model = model
        self.base_url = base_url
        logger.info(f"Ollama provider configured: {model} at {base_url}")
    
    async def chat(self, messages: List[ChatMessage], **kwargs) -> str:
        """Send chat to Ollama and get response."""
        try:
            import requests
            
            # Convert messages to Ollama format
            conversation = "\n".join([
                f"{msg.role}: {msg.content}" for msg in messages
            ])
            
            payload = {
                "model": self.model,
                "prompt": conversation + "\nassistant: ",
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 500)
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()["response"]
            
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise RuntimeError(f"Ollama request failed: {e}")
    
    def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_model_name(self) -> str:
        """Get current model name."""
        return f"ollama/{self.model}"

class LLMManager:
    """
    Manages multiple LLM providers and provides unified interface.
    
    Automatically selects the best available provider and allows
    easy switching between different models.
    """
    
    def __init__(self):
        """Initialize LLM manager with available providers."""
        self.providers: Dict[str, LLMProvider] = {}
        self.current_provider: Optional[str] = None
        
        # Initialize providers
        self._setup_providers()
        self._select_best_provider()
    
    def _setup_providers(self):
        """Set up all available LLM providers."""
        # OpenAI Provider
        openai_provider = OpenAIProvider()
        if openai_provider.is_available():
            self.providers["openai"] = openai_provider
            logger.info("OpenAI provider available")
        
        # Ollama Provider  
        ollama_provider = OllamaProvider()
        if ollama_provider.is_available():
            self.providers["ollama"] = ollama_provider
            logger.info("Ollama provider available")
        
        logger.info(f"Available LLM providers: {list(self.providers.keys())}")
    
    def _select_best_provider(self):
        """Select the best available provider."""
        # Priority order: OpenAI, Ollama
        priority = ["openai", "ollama"]
        
        for provider_name in priority:
            if provider_name in self.providers:
                self.current_provider = provider_name
                logger.info(f"Selected LLM provider: {provider_name}")
                return
        
        logger.warning("No LLM providers available")
    
    def set_provider(self, provider_name: str):
        """Manually set the LLM provider."""
        if provider_name in self.providers:
            self.current_provider = provider_name
            logger.info(f"Switched to LLM provider: {provider_name}")
        else:
            raise ValueError(f"Provider '{provider_name}' not available")
    
    def get_current_provider(self) -> Optional[LLMProvider]:
        """Get the current LLM provider."""
        if self.current_provider:
            return self.providers[self.current_provider]
        return None
    
    async def chat(self, messages: List[ChatMessage], **kwargs) -> str:
        """Send chat to current provider."""
        provider = self.get_current_provider()
        if not provider:
            raise RuntimeError("No LLM provider available")
        
        return await provider.chat(messages, **kwargs)
    
    def is_available(self) -> bool:
        """Check if any provider is available."""
        return len(self.providers) > 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        return {
            "available_providers": list(self.providers.keys()),
            "current_provider": self.current_provider,
            "current_model": self.providers[self.current_provider].get_model_name() if self.current_provider else None
        }

# Global instance
llm_manager = LLMManager()