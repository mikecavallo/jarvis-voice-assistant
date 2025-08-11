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
    
    def _search_conversation_history(self, query: str, limit: int = 5) -> str:
        """
        Search past conversations for relevant context.
        
        Args:
            query: User's question or search terms
            limit: Maximum number of results to return
            
        Returns:
            Formatted conversation history or empty string
        """
        if not chroma_manager.enabled:
            return ""
        
        try:
            # Search for relevant past conversations
            results = chroma_manager.search_conversations(query, n_results=limit)
            
            if not results:
                return ""
            
            # Format results as context with priority information
            context_parts = []
            for i, result in enumerate(results):
                # Extract conversation content
                content = result.get('document', result.get('text', ''))
                distance = result.get('distance', 0)
                priority = result.get('priority', 0)
                
                # Skip if too distant (not relevant enough)
                if distance and distance > 0.8:
                    continue
                
                # Debug: show priority scores
                print(f"🔍 DEBUG: Memory {i+1} - Priority: {priority:.3f}, Distance: {distance:.3f if distance else 'N/A'}")
                
                context_parts.append(f"Past conversation {i+1}: {content}")
            
            if context_parts:
                return f"RELEVANT PAST CONVERSATIONS:\n" + "\n".join(context_parts[:3])  # Limit to 3 most relevant
            
            return ""
            
        except Exception as e:
            logger.error(f"Error searching conversation history: {e}")
            return ""
    
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
            
            # Check if user is asking about past conversations/memory
            memory_keywords = ["yesterday", "before", "previous", "earlier", "last time", "remember", "talked about", "discussed", "conversation", "what did we", "what have we"]
            is_memory_query = any(keyword in user_input.lower() for keyword in memory_keywords)
            
            conversation_context = ""
            if is_memory_query:
                print(f"🔍 DEBUG: Memory query detected: {user_input}")
                conversation_context = self._search_conversation_history(user_input)
                if conversation_context:
                    print(f"🔍 DEBUG: Found relevant conversations: {len(conversation_context)} chars")
                else:
                    print("🔍 DEBUG: No relevant conversations found")
            
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
            
            # Add conversation history context if this is a memory query
            if conversation_context:
                system_content += f"\n{conversation_context}\n"
                system_content += "\nUSE THIS INFORMATION: The user is asking about past conversations. Use the relevant past conversations above to answer their question accurately.\n"
            
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
            
            elif tool_name == "calendar":
                # Extract calendar action and parameters
                action, params = self._extract_calendar_request(user_input)
                print(f"🔍 DEBUG: Calendar action: {action}")
                print(f"🔍 DEBUG: Calendar params: {params}")
                
                # Validate required information for create_event
                if action == "create_event":
                    missing_info = []
                    
                    # Check for event title/summary
                    if not params.get("summary") or params.get("summary") == "New Event":
                        missing_info.append("what the appointment is for")
                    
                    # Check for specific time (if still using defaults)
                    if "10:00" in params.get("start_time", "") and "10:00" not in user_input.lower():
                        missing_info.append("what time")
                    
                    # Check for specific date (if still using today as default and no date mentioned)
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    if today_str in params.get("start_time", "") and not any(word in user_input.lower() for word in ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                        missing_info.append("what day")
                    
                    if missing_info:
                        missing_str = ", ".join(missing_info[:-1])
                        if len(missing_info) > 1:
                            missing_str += f" and {missing_info[-1]}"
                        else:
                            missing_str = missing_info[0]
                        
                        return f"I'd be happy to add that appointment! Could you please tell me {missing_str}?"
                
                result = await mcp_client.call_tool("calendar", action=action, parameters=params)
                print(f"🔍 DEBUG: Calendar result: {result}")
                if result.get("success"):
                    return self._format_calendar_result(result["data"])
                else:
                    return f"I couldn't access your calendar right now: {result.get('error', 'Calendar integration needs setup')}"
            
            elif tool_name == "gmail":
                # Extract email action
                action, details = self._extract_gmail_request(user_input)
                result = await mcp_client.call_tool("gmail", action=action, details=details)
                if result.get("success"):
                    return self._format_gmail_result(result["data"])
                else:
                    return f"I couldn't access your Gmail right now: {result.get('error', 'Gmail integration needs setup')}"
            
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
    
    def _extract_calendar_request(self, user_input: str) -> tuple[str, Dict[str, str]]:
        """Extract calendar action and parameters from user input."""
        user_lower = user_input.lower()
        
        # Extract action with more specific detection
        print(f"🔍 DEBUG: Determining action for: '{user_lower}'")
        
        if any(word in user_lower for word in ["add", "create", "schedule", "book", "make an appointment", "appointment"]):
            action = "create_event"
        elif any(word in user_lower for word in ["update", "change", "modify", "move", "reschedule", "fix"]):
            action = "update_event"
        elif any(word in user_lower for word in ["delete", "remove", "cancel"]):
            action = "delete_event"
        elif any(phrase in user_lower for phrase in ["what's on", "what's in", "check calendar", "show me"]) and not any(word in user_lower for word in ["add", "create", "schedule", "book"]):
            action = "list_events"
        elif "free time" in user_lower or "available" in user_lower:
            action = "find_free_time"
        else:
            # Default to create_event if it mentions appointment/meeting/event
            if any(word in user_lower for word in ["appointment", "meeting", "event"]):
                action = "create_event"
            else:
                action = "list_events"
        
        print(f"🔍 DEBUG: Action determined: {action}")
        
        # Extract date info with proper datetime conversion
        import re
        from datetime import datetime, timedelta
        import pytz
        
        date_patterns = [
            r"august (\d+)",
            r"september (\d+)", 
            r"today",
            r"tomorrow",
            r"next week",
            r"this week",
            r"monday",
            r"tuesday", 
            r"wednesday",
            r"thursday",
            r"friday",
            r"saturday",
            r"sunday"
        ]
        
        date_info = None  # Will be set to actual date
        now = datetime.now()
        
        for pattern in date_patterns:
            match = re.search(pattern, user_lower)
            if match:
                if "august" in pattern:
                    date_info = f"2025-08-{match.group(1).zfill(2)}"
                elif "september" in pattern:
                    date_info = f"2025-09-{match.group(1).zfill(2)}"
                elif "today" in pattern:
                    date_info = now.strftime("%Y-%m-%d")
                elif "tomorrow" in pattern:
                    tomorrow = now + timedelta(days=1)
                    date_info = tomorrow.strftime("%Y-%m-%d")
                elif "next week" in pattern:
                    next_week = now + timedelta(days=7)
                    date_info = next_week.strftime("%Y-%m-%d")
                elif "this week" in pattern:
                    # Default to next business day this week
                    days_ahead = 1 if now.weekday() < 4 else (7 - now.weekday())
                    next_day = now + timedelta(days=days_ahead)
                    date_info = next_day.strftime("%Y-%m-%d")
                elif pattern in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                    # Find the next occurrence of this weekday
                    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                    target_weekday = weekdays.index(pattern)
                    current_weekday = now.weekday()
                    
                    # Calculate days until target weekday
                    days_ahead = (target_weekday - current_weekday) % 7
                    if days_ahead == 0:  # If it's today, assume next week
                        days_ahead = 7
                    
                    target_date = now + timedelta(days=days_ahead)
                    date_info = target_date.strftime("%Y-%m-%d")
                    print(f"🔍 DEBUG: Found {pattern} -> {date_info}")
                break
        
        # Default to today if no date found
        if not date_info:
            date_info = now.strftime("%Y-%m-%d")
        
        # Extract time info for create_event
        time_info = "10:00"  # Default
        
        # DEBUG: Print what we're parsing
        print(f"🔍 DEBUG: Parsing time from: '{user_lower}'")
        
        # Check for special time words first
        if "noon" in user_lower or "12 pm" in user_lower or "12pm" in user_lower:
            time_info = "12:00"
            print(f"🔍 DEBUG: Found noon -> {time_info}")
        elif "midnight" in user_lower or "12 am" in user_lower or "12am" in user_lower:
            time_info = "00:00"
            print(f"🔍 DEBUG: Found midnight -> {time_info}")
        else:
            # Try different time patterns (improved for your use case)
            time_patterns = [
                r"(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)",  # "2:30pm", "10:15am"
                r"(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)",          # "2pm", "10am"
                r"(\d{1,2})-(\d{1,2})",                      # "2-5" (2pm to 5pm)
                r"(\d{1,2})\s*to\s*(\d{1,2})",              # "2 to 5"
                r"from\s*(\d{1,2})\s*to\s*(\d{1,2})",       # "from 2 to 5"
            ]
            
            for i, pattern in enumerate(time_patterns):
                time_match = re.search(pattern, user_lower)
                if time_match:
                    print(f"🔍 DEBUG: Found time match with pattern {i}: {time_match.groups()}")
                    
                    if i <= 1:  # Standard time patterns
                        if len(time_match.groups()) == 3:  # HH:MM format
                            hour = int(time_match.group(1))
                            minute = time_match.group(2)
                            ampm = time_match.group(3).lower().replace(".", "")
                        else:  # H format
                            hour = int(time_match.group(1))
                            minute = "00"
                            ampm = time_match.group(2).lower().replace(".", "")
                        
                        print(f"🔍 DEBUG: Parsed - hour:{hour}, minute:{minute}, ampm:{ampm}")
                        
                        # Convert to 24-hour format
                        if "pm" in ampm and hour != 12:
                            hour += 12
                        elif "am" in ampm and hour == 12:
                            hour = 0
                        
                        time_info = f"{hour:02d}:{minute}"
                    
                    elif i >= 2:  # Range patterns like "2-5" or "2 to 5"
                        start_hour = int(time_match.group(1))
                        end_hour = int(time_match.group(2))
                        
                        # Assume afternoon if reasonable hours
                        if start_hour <= 12 and end_hour <= 12:
                            if start_hour < 8:  # Likely PM if before 8
                                start_hour += 12
                            if end_hour < 8:  # Likely PM if before 8
                                end_hour += 12
                        
                        time_info = f"{start_hour:02d}:00"
                        print(f"🔍 DEBUG: Range detected - start:{start_hour:02d}:00, end:{end_hour:02d}:00")
                    
                    print(f"🔍 DEBUG: Final time: {time_info}")
                    break
        
        if time_info == "10:00":
            print(f"🔍 DEBUG: No time found, using default: {time_info}")
        
        # Extract event title for create_event
        event_title = None  # Will be None if not found
        if action == "create_event":
            # Try to extract event details with improved patterns
            patterns = [
                r"for (.+?)(?:\s+at\s+\d+|\s+on\s+\w+|\s+tomorrow|\s+today|$)",  # "for the dentist at 2pm" or "for the dentist tomorrow"
                r"add (.+?)(?:\s+at\s+\d+|\s+on\s+\w+|\s+tomorrow|\s+today|$)",  # "add dentist appointment at 2pm"
                r"schedule (.+?)(?:\s+at\s+\d+|\s+on\s+\w+|\s+tomorrow|\s+today|$)",  # "schedule meeting at 3pm"
                r"appointment.+?for (.+?)(?:\s+at\s+\d+|\s+on\s+\w+|\s+tomorrow|\s+today|$)",  # "appointment for dentist at 2pm"
                r"book (.+?)(?:\s+at\s+\d+|\s+on\s+\w+|\s+tomorrow|\s+today|$)"  # "book dinner at 7pm"
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    event_title = match.group(1).strip()
                    # Clean up common words
                    event_title = re.sub(r'^(an?\s+)', '', event_title, flags=re.IGNORECASE)
                    # Don't use generic words as titles
                    if event_title.lower() in ["appointment", "meeting", "event", "it", "this", "that"]:
                        event_title = None
                    break
        
        # Build parameters dict
        if action == "create_event":
            # Get user's timezone (assuming Eastern Time, but this should be configurable)
            user_tz = pytz.timezone('America/New_York')  # Eastern Time
            
            # Parse the date and time in user's timezone
            start_dt = datetime.strptime(f"{date_info} {time_info}", "%Y-%m-%d %H:%M")
            start_dt = user_tz.localize(start_dt)
            
            # Convert to UTC for Google Calendar API
            start_dt_utc = start_dt.astimezone(pytz.UTC)
            end_dt_utc = start_dt_utc + timedelta(hours=1)  # Default 1-hour duration
            
            # Format as ISO strings
            start_datetime = start_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            end_datetime = end_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            print(f"🔍 DEBUG: User time: {start_dt} -> UTC time: {start_dt_utc}")
            
            params = {
                "summary": event_title,
                "start_time": start_datetime,
                "end_time": end_datetime,
                "description": f"Event created via Jarvis voice command: {user_input}"
            }
        elif action == "update_event":
            # For update, we need to find the event first
            # We'll use the event title to search for existing events
            params = {
                "summary": event_title,
                "date": date_info,
                "new_start_time": f"{date_info}T{time_info}:00",
                "search_query": user_input  # Pass full query for intelligent matching
            }
            # Add end time if we have new timing
            if time_info != "10:00":  # If we detected a new time
                start_hour = int(time_info.split(":")[0])
                end_hour = (start_hour + 1) % 24
                end_datetime = f"{date_info}T{end_hour:02d}:00:00"
                if end_hour < start_hour:
                    end_date = datetime.strptime(date_info, "%Y-%m-%d") + timedelta(days=1)
                    end_datetime = f"{end_date.strftime('%Y-%m-%d')}T{end_hour:02d}:00:00"
                params["new_end_time"] = end_datetime
        elif action == "delete_event":
            params = {
                "summary": event_title,
                "date": date_info,
                "search_query": user_input
            }
        else:
            # For list_events and other actions
            params = {
                "date": date_info
            }
                
        return action, params
    
    def _extract_gmail_request(self, user_input: str) -> tuple[str, str]:
        """Extract Gmail action and details from user input."""
        user_lower = user_input.lower()
        
        # Extract action
        if "send" in user_lower:
            action = "send_email"
        elif "draft" in user_lower:
            action = "draft_email"
        elif "unread" in user_lower:
            action = "list_unread"
        elif "recent" in user_lower:
            action = "list_recent"
        else:
            action = "list_recent"
        
        # Extract details - for now just pass the full input
        return action, user_input
    
    def _format_calendar_result(self, data: Dict[str, Any]) -> str:
        """Format calendar results for conversation."""
        try:
            if isinstance(data, dict):
                if "events" in data:
                    events = data["events"][:5]  # First 5 events
                    if not events:
                        return "You have no events scheduled."
                    
                    formatted = "Here are your upcoming events: "
                    for event in events:
                        title = event.get("summary", "Untitled")
                        time = event.get("start", {}).get("dateTime", "No time")
                        formatted += f"{title} at {time}. "
                    return formatted
                elif "event" in data and data.get("success"):
                    # Handle create_event success
                    event = data.get("event", {})
                    title = event.get("summary", "Event")
                    start_time = event.get("start_time", "")
                    # Extract date and time from ISO format
                    if "T" in start_time:
                        date_part = start_time.split("T")[0]
                        time_part = start_time.split("T")[1].split(":")[0]
                        formatted_time = f"{int(time_part) % 12 or 12}{'AM' if int(time_part) < 12 else 'PM'}"
                        return f"Perfect! I've added '{title}' to your calendar for {date_part} at {formatted_time}."
                    return f"I've successfully added '{title}' to your calendar."
                elif "message" in data:
                    return data["message"]
                elif "success" in data and data["success"]:
                    return "Calendar operation completed successfully."
            return str(data)
        except:
            return "I couldn't parse the calendar information."
    
    def _format_gmail_result(self, data: Dict[str, Any]) -> str:
        """Format Gmail results for conversation."""
        try:
            if isinstance(data, dict):
                if "emails" in data:
                    emails = data["emails"][:3]  # First 3 emails
                    if not emails:
                        return "You have no new emails."
                    
                    formatted = "Here are your recent emails: "
                    for email in emails:
                        subject = email.get("subject", "No subject")
                        sender = email.get("from", "Unknown sender")
                        formatted += f"'{subject}' from {sender}. "
                    return formatted
                elif "message" in data:
                    return data["message"]
            return str(data)
        except:
            return "I couldn't parse the email information."
    
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
            # Extract name after "i'm" - only if it looks like name introduction
            # Avoid common words that aren't names
            avoid_words = {"looking", "going", "trying", "working", "thinking", "feeling", "getting", "doing", "coming", "having", "making", "taking", "good", "bad", "fine", "okay", "here", "there", "ready", "done", "back", "up", "down"}
            
            words = user_input.split()
            for i, word in enumerate(words):
                if word.lower() == "i'm" and i + 1 < len(words):
                    potential_name = words[i + 1].strip(".,!?")
                    if (potential_name and potential_name.isalpha() and 
                        len(potential_name) > 1 and potential_name.lower() not in avoid_words and
                        potential_name[0].isupper()):  # Names usually start with capital
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