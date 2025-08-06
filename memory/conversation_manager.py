"""
Conversation Manager for Jarvis Assistant.

This module handles conversational AI interactions, personality prompts,
and context management for natural dialogue with users.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .llm_interface import llm_manager, ChatMessage
from .personal_memory import personal_memory
from .chroma_manager import chroma_manager
from .mcp_client import mcp_client

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Manages conversational AI interactions with personality and context.
    
    This class provides:
    - Jarvis personality system prompts
    - Conversation context management
    - Integration with personal memory
    - Meet-and-greet initialization flow
    """
    
    def __init__(self):
        """Initialize conversation manager."""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conversation_history: List[ChatMessage] = []
        self.max_history = 10  # Keep last 10 exchanges
        
        logger.info(f"Conversation manager initialized for session: {self.session_id}")
    
    def _get_base_system_prompt(self) -> str:
        """Get the base Jarvis personality system prompt."""
        available_tools = mcp_client.get_available_tools()
        tools_list = "\n".join([f"- {name}: {desc}" for name, desc in available_tools.items()])
        
        return f"""You are Jarvis, a sophisticated AI assistant and intelligent routing agent. You are:

PERSONALITY TRAITS:
- Intelligent, witty, and slightly sarcastic but always helpful
- Confident and knowledgeable, yet humble when you don't know something
- Proactive in offering assistance and suggestions
- Formal but warm, addressing users respectfully
- Efficient and to-the-point, but engaging when appropriate

CORE ROLE - INTELLIGENT ROUTING AGENT:
You are the top-level orchestrator who decides how to handle user requests:
1. **Direct Conversation**: For casual chat, general questions, personal advice
2. **Real-time Data Tools**: For current information that requires live data
3. **Specialist Agents**: For complex tasks requiring domain expertise (future)

AVAILABLE REAL-TIME TOOLS:
{tools_list}

ROUTING INTELLIGENCE:
- **Use tools for**: Weather, crypto prices, news, web searches, file operations
- **Direct conversation for**: General chat, advice, explanations, personal topics
- **Tool decisions**: When user asks about current/live data, automatically use appropriate tools
- **Seamless integration**: Present tool results naturally in conversation

COMMUNICATION STYLE:
- Be concise and direct - avoid verbose explanations
- Don't repeat your introduction unless it's the first meeting
- For data requests: state the answer briefly, then ask for name if unknown
- Example: "Bitcoin is $50,000. By the way, what's your name?"
- Avoid excessive details unless specifically asked

IMPORTANT GUIDELINES:
- Always prioritize user privacy and security
- For real-time data requests, use tools automatically without asking
- Present tool results as your own knowledge naturally
- Ask for clarification when requests are ambiguous
- Be honest about your limitations
- Maintain a helpful and professional demeanor

Remember: You are the intelligent orchestrator managing all system capabilities to help users accomplish their goals efficiently."""

    def _get_personalized_context(self) -> str:
        """Get personalized context based on user's stored information."""
        context_parts = []
        
        # User profile information
        name = personal_memory.get_user_name()
        if name:
            context_parts.append(f"The user's name is {name}.")
        
        location = personal_memory.get_location()
        if location:
            context_parts.append(f"They are located in {location}.")
        
        # User preferences
        preferences = personal_memory.data["preferences"]
        if preferences:
            pref_list = [f"{k}: {v['value']}" for k, v in list(preferences.items())[:3]]
            context_parts.append(f"Known preferences: {', '.join(pref_list)}")
        
        # Recent interests
        interests = personal_memory.get_interests()
        if interests:
            context_parts.append(f"Interests: {', '.join(interests[:3])}")
        
        # Recent conversation topics
        recent_topics = personal_memory.get_recent_topics()
        if recent_topics:
            context_parts.append(f"Recent topics: {', '.join(recent_topics)}")
        
        # Learned facts
        facts = personal_memory.get_all_facts()
        if facts:
            fact_list = [f"{k}: {v}" for k, v in list(facts.items())[:2]]
            context_parts.append(f"Important facts: {', '.join(fact_list)}")
        
        if context_parts:
            return f"\nPERSONAL CONTEXT:\n{' '.join(context_parts)}\n"
        
        return ""
    
    def _needs_introduction(self) -> bool:
        """Check if user needs introduction/meet-and-greet."""
        return personal_memory.needs_introduction()
    
    def _get_introduction_prompt(self) -> str:
        """Get meet-and-greet system prompt."""
        missing_info = personal_memory.get_missing_info()
        
        intro_prompt = """SPECIAL INSTRUCTIONS - NAME UNKNOWN:
You don't know this user's name yet. After answering their question, casually ask:
"By the way, what's your name?"

DO NOT introduce yourself again - you already did that in the initial greeting.
Keep responses brief and natural.
"""
        
        return intro_prompt
    
    async def get_response(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get conversational response from Jarvis with intelligent routing.
        
        This method implements Jarvis as an intelligent routing agent:
        1. Analyzes user intent
        2. Routes to appropriate tools (MCP server) when needed
        3. Provides conversational responses with tool integration
        
        Args:
            user_input: User's message
            context: Additional context (command results, etc.)
            
        Returns:
            Jarvis response with tool integration if needed
        """
        try:
            # Check if LLM is available
            if not llm_manager.is_available():
                return "I'm sorry, but my conversational AI system is currently unavailable. I can still help with basic commands - say 'help' to see what's available."
            
            # Step 1: Intelligent routing - check if MCP tools should be used
            tool_needed = mcp_client.can_handle_request(user_input)
            tool_results = None
            
            if tool_needed:
                logger.info(f"Routing request to MCP tool: {tool_needed}")
                tool_results = await self._execute_mcp_tool(tool_needed, user_input)
            
            # Step 2: Build system message with tool awareness
            system_content = self._get_base_system_prompt()
            system_content += self._get_personalized_context()
            
            # Add introduction prompt if needed
            if self._needs_introduction():
                system_content += self._get_introduction_prompt()
            
            # Add tool results to context
            if tool_results:
                system_content += f"\n\nTOOL RESULTS:\nI just retrieved this information for you: {tool_results}\nPlease integrate this naturally into your response as if it's your own knowledge.\n"
            
            # Add any additional context
            if context:
                system_content += f"\nCURRENT CONTEXT:\n{context.get('info', '')}\n"
            
            # Step 3: Build message list
            messages = [ChatMessage(role="system", content=system_content)]
            
            # Add conversation history
            messages.extend(self.conversation_history[-self.max_history:])
            
            # Add current user message
            messages.append(ChatMessage(role="user", content=user_input))
            
            # Step 4: Get response from LLM (with tool integration if applicable)
            response = await llm_manager.chat(messages)
            
            # Step 5: Update conversation history
            self.conversation_history.append(ChatMessage(role="user", content=user_input))
            self.conversation_history.append(ChatMessage(role="assistant", content=response))
            
            # Extract and store personal information from conversation
            await self._extract_personal_info(user_input, response)
            
            # Store conversation in memory
            if chroma_manager.enabled:
                chroma_manager.add_conversation(
                    f"User: {user_input}\nJarvis: {response}",
                    self.session_id,
                    "conversation"
                )
            
            # Add to recent requests
            personal_memory.add_recent_request(user_input)
            
            logger.debug(f"Generated response for: {user_input[:50]}... (tool: {tool_needed})")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again."
    
    async def _execute_mcp_tool(self, tool_name: str, user_input: str) -> Optional[str]:
        """
        Execute MCP tool based on user input analysis.
        
        Args:
            tool_name: Name of the MCP tool to execute
            user_input: Original user input for parameter extraction
            
        Returns:
            Formatted tool results or None if failed
        """
        try:
            user_lower = user_input.lower()
            
            if tool_name == "crypto":
                # Extract crypto symbol from user input
                symbol = self._extract_crypto_symbol(user_input)
                if symbol:
                    result = await mcp_client.get_crypto_price(symbol)
                    if result.get("success"):
                        return self._format_crypto_result(result["data"])
                    else:
                        return f"I couldn't retrieve crypto data: {result.get('error', 'Unknown error')}"
            
            elif tool_name == "weather":
                # Extract location from user input
                location = self._extract_location(user_input)
                forecast = "forecast" in user_lower or "tomorrow" in user_lower
                if location:
                    result = await mcp_client.get_weather(location, forecast)
                    if result.get("success"):
                        return self._format_weather_result(result["data"])
                    else:
                        return f"I'm unable to get current weather data for {location} right now. The weather service seems to be unavailable."
            
            elif tool_name == "news":
                # Extract news query if any
                query = self._extract_news_query(user_input)
                result = await mcp_client.get_news(query=query)
                if result.get("success"):
                    return self._format_news_result(result["data"])
                else:
                    return f"I couldn't retrieve news: {result.get('error', 'Unknown error')}"
            
            elif tool_name == "search":
                # Extract search query
                query = self._extract_search_query(user_input)
                if query:
                    result = await mcp_client.search_web(query)
                    if result.get("success"):
                        return self._format_search_result(result["data"])
                    else:
                        return f"I couldn't search for that: {result.get('error', 'Unknown error')}"
            
            elif tool_name == "filesystem":
                # Extract path if any
                path = self._extract_file_path(user_input)
                result = await mcp_client.list_files(path)
                if result.get("success"):
                    return self._format_filesystem_result(result["data"])
                else:
                    return f"I couldn't access the file system: {result.get('error', 'Unknown error')}"
            
            return None
            
        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_name}: {e}")
            return f"I encountered an error using the {tool_name} tool: {str(e)}"
    
    def _extract_crypto_symbol(self, user_input: str) -> Optional[str]:
        """Extract cryptocurrency symbol from user input."""
        user_lower = user_input.lower()
        
        # Common crypto mappings
        crypto_mappings = {
            "bitcoin": "bitcoin",
            "btc": "bitcoin", 
            "ethereum": "ethereum",
            "eth": "ethereum",
            "dogecoin": "dogecoin",
            "doge": "dogecoin",
            "ada": "cardano",
            "cardano": "cardano",
            "solana": "solana",
            "sol": "solana"
        }
        
        for keyword, symbol in crypto_mappings.items():
            if keyword in user_lower:
                return symbol
        
        return "bitcoin"  # Default to bitcoin
    
    def _extract_location(self, user_input: str) -> str:
        """Extract location from user input."""
        user_lower = user_input.lower()
        
        # Look for location patterns
        location_patterns = ["in ", "for ", "at "]
        for pattern in location_patterns:
            if pattern in user_lower:
                try:
                    start_idx = user_lower.find(pattern) + len(pattern)
                    location_part = user_input[start_idx:].strip()
                    # Take first few words as location
                    location = " ".join(location_part.split()[:3])
                    if location and not location.lower() in ["the", "weather", "forecast"]:
                        return location
                except:
                    pass
        
        # Default to user's stored location or ask
        stored_location = personal_memory.get_location()
        return stored_location if stored_location else "current location"
    
    def _extract_news_query(self, user_input: str) -> Optional[str]:
        """Extract news query from user input."""
        user_lower = user_input.lower()
        
        # Look for specific news topics
        if "about" in user_lower:
            try:
                start_idx = user_lower.find("about") + 5
                query = user_input[start_idx:].strip()
                return query if query else None
            except:
                pass
        
        return None  # Return general news
    
    def _extract_search_query(self, user_input: str) -> Optional[str]:
        """Extract search query from user input."""
        user_lower = user_input.lower()
        
        # Remove search trigger words and get the query
        search_triggers = ["search for", "look up", "find", "google", "web search"]
        
        for trigger in search_triggers:
            if trigger in user_lower:
                try:
                    start_idx = user_lower.find(trigger) + len(trigger)
                    query = user_input[start_idx:].strip()
                    return query if query else None
                except:
                    pass
        
        return None
    
    def _extract_file_path(self, user_input: str) -> str:
        """Extract file path from user input."""
        # Simple path extraction - could be enhanced
        if "/" in user_input:
            parts = user_input.split()
            for part in parts:
                if "/" in part:
                    return part
        
        return "."  # Default to current directory
    
    def _format_crypto_result(self, data: Dict[str, Any]) -> str:
        """Format cryptocurrency data for conversation."""
        try:
            if isinstance(data, dict):
                # Handle both direct data and nested data structures
                if "data" in data:
                    crypto_data = data["data"]
                else:
                    crypto_data = data
                
                if "symbol" in crypto_data and "price" in crypto_data:
                    # MCP server format
                    symbol = crypto_data.get("symbol", "").title()
                    price = crypto_data.get("price", 0)
                    return f"{symbol} is ${price:,.0f}"
                elif "name" in crypto_data and "current_price" in crypto_data:
                    # Alternative format
                    name = crypto_data.get("name", "Cryptocurrency")
                    price = crypto_data.get("current_price", 0)
                    return f"{name} is ${price:,.0f}"
            
            return str(data)
        except:
            return str(data)
    
    def _format_weather_result(self, data: Dict[str, Any]) -> str:
        """Format weather data for conversation."""
        try:
            if isinstance(data, dict):
                temp = data.get("temperature", "N/A")
                condition = data.get("condition", "N/A")
                location = data.get("location", "your area")
                
                return f"The weather in {location} is {condition} with a temperature of {temp}°F"
            return str(data)
        except:
            return str(data)
    
    def _format_news_result(self, data: Dict[str, Any]) -> str:
        """Format news data for conversation."""
        try:
            if isinstance(data, dict) and "articles" in data:
                articles = data["articles"][:3]  # Top 3 articles
                formatted = "Here are the latest headlines: "
                for i, article in enumerate(articles, 1):
                    title = article.get("title", "")
                    formatted += f"{i}. {title}. "
                return formatted
            return str(data)
        except:
            return str(data)
    
    def _format_search_result(self, data: Dict[str, Any]) -> str:
        """Format search results for conversation."""
        try:
            if isinstance(data, dict) and "results" in data:
                results = data["results"][:3]  # Top 3 results
                formatted = "I found these results: "
                for i, result in enumerate(results, 1):
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    formatted += f"{i}. {title} - {snippet[:100]}... "
                return formatted
            return str(data)
        except:
            return str(data)
    
    def _format_filesystem_result(self, data: Dict[str, Any]) -> str:
        """Format file system results for conversation."""
        try:
            if isinstance(data, dict) and "files" in data:
                files = data["files"][:10]  # First 10 files
                formatted = f"I found {len(files)} items: " + ", ".join(files)
                return formatted
            return str(data)
        except:
            return str(data)
    
    async def _extract_personal_info(self, user_input: str, assistant_response: str):
        """Extract and store personal information from conversation."""
        user_lower = user_input.lower()
        
        # Extract name if introduced
        if "my name is" in user_lower:
            # Extract name after "my name is"
            start_idx = user_lower.find("my name is") + len("my name is")
            name_part = user_input[start_idx:].strip()
            name_words = name_part.split()
            if name_words and name_words[0].isalpha():
                potential_name = name_words[0].strip(".,!?")
                personal_memory.set_user_name(potential_name)
                logger.info(f"Learned user name: {potential_name}")
        elif "call me" in user_lower:
            # Extract name after "call me"
            start_idx = user_lower.find("call me") + len("call me")
            name_part = user_input[start_idx:].strip()
            name_words = name_part.split()
            if name_words and name_words[0].isalpha():
                potential_name = name_words[0].strip(".,!?")
                personal_memory.set_user_name(potential_name)
                logger.info(f"Learned user name: {potential_name}")
        elif "i'm " in user_lower and len(user_input.split()) >= 2:
            # Extract name after "i'm" - be more careful
            words = user_input.split()
            for i, word in enumerate(words):
                if word.lower() == "i'm" and i + 1 < len(words):
                    potential_name = words[i + 1].strip(".,!?")
                    if potential_name and potential_name.isalpha() and len(potential_name) > 1:
                        personal_memory.set_user_name(potential_name)
                        logger.info(f"Learned user name: {potential_name}")
                        break
        
        # Extract location mentions
        location_phrases = ["i live in", "i'm in", "i'm from", "located in"]
        for phrase in location_phrases:
            if phrase in user_lower:
                try:
                    location_start = user_lower.find(phrase) + len(phrase)
                    location_part = user_input[location_start:].strip()
                    # Extract first few words as location
                    location_words = location_part.split()[:3]
                    location = " ".join(location_words).strip(".,!?")
                    if location:
                        personal_memory.set_location(location)
                        logger.info(f"Learned user location: {location}")
                        break
                except:
                    pass
        
        # Extract interests and preferences (simple keyword matching)
        interest_indicators = ["i like", "i love", "i enjoy", "i prefer", "favorite"]
        for indicator in interest_indicators:
            if indicator in user_lower:
                # This could be enhanced with better NLP
                pass
    
    def get_greeting(self) -> str:
        """Get personalized greeting based on user info."""
        name = personal_memory.get_user_name()
        
        if name:
            greetings = [
                f"Hello {name}! How can I assist you today?",
                f"Good to see you again, {name}. What can I help with?",
                f"Hello {name}! Ready to help with whatever you need.",
            ]
            
            # Add context-aware greetings
            recent_topics = personal_memory.get_recent_topics(1)
            if recent_topics:
                greetings.append(f"Hello {name}! Ready to continue where we left off, or is there something new I can help with?")
            
            import random
            return random.choice(greetings)
        else:
            return "Hello! I'm Jarvis, your AI assistant. How may I help you today?"
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        return {
            "session_id": self.session_id,
            "exchanges_count": len(self.conversation_history) // 2,
            "llm_available": llm_manager.is_available(),
            "llm_status": llm_manager.get_status() if llm_manager.is_available() else None,
            "user_known": not personal_memory.needs_introduction(),
            "personal_info": personal_memory.get_summary()
        }

# Global instance
conversation_manager = ConversationManager()