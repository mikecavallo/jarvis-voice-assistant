"""
Personal Memory Manager for Jarvis Assistant.

This module handles personal information and short-term memory about the user,
including name, preferences, and recent conversation context. It provides
key-value storage for personal details that Jarvis learns during conversations.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PersonalMemory:
    """
    Manages personal information and preferences about the user.
    
    This class provides persistent storage for:
    - User's name and personal details
    - Learned preferences and interests
    - Recent conversation context
    - Important dates and reminders
    """
    
    def __init__(self, memory_file: str = "memory/personal_memory.json"):
        """
        Initialize personal memory system.
        
        Args:
            memory_file: Path to JSON file for storing personal data
        """
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize with empty memory structure
        self.data = {
            "user_profile": {
                "name": None,
                "preferred_name": None,
                "location": None,
                "timezone": None
            },
            "preferences": {},
            "interests": [],
            "important_dates": {},
            "conversation_context": {
                "last_topics": [],
                "mood_indicators": [],
                "recent_requests": []
            },
            "learned_facts": {},
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": None,
                "version": "1.0"
            }
        }
        
        self.load_memory()
        logger.info(f"Personal memory initialized: {self.memory_file}")
    
    def load_memory(self):
        """Load personal memory from JSON file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    stored_data = json.load(f)
                    # Merge with default structure to handle new fields
                    self._merge_data(self.data, stored_data)
                logger.debug("Personal memory loaded from file")
            except Exception as e:
                logger.error(f"Failed to load personal memory: {e}")
                logger.info("Using default memory structure")
        else:
            self.save_memory()
    
    def save_memory(self):
        """Save personal memory to JSON file."""
        try:
            self.data["metadata"]["last_updated"] = datetime.now().isoformat()
            with open(self.memory_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            logger.debug("Personal memory saved to file")
        except Exception as e:
            logger.error(f"Failed to save personal memory: {e}")
    
    def _merge_data(self, default: Dict, stored: Dict):
        """Merge stored data with default structure."""
        for key, value in stored.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_data(default[key], value)
                else:
                    default[key] = value
            else:
                default[key] = value
    
    # User Profile Methods
    
    def get_user_name(self) -> Optional[str]:
        """Get user's name (preferred name or full name)."""
        preferred = self.data["user_profile"].get("preferred_name")
        full_name = self.data["user_profile"].get("name")
        return preferred or full_name
    
    def set_user_name(self, name: str, preferred_name: Optional[str] = None):
        """Set user's name and preferred name."""
        self.data["user_profile"]["name"] = name
        if preferred_name:
            self.data["user_profile"]["preferred_name"] = preferred_name
        else:
            # If no preferred name given, use first name
            self.data["user_profile"]["preferred_name"] = name.split()[0]
        self.save_memory()
        logger.info(f"User name set: {name} (preferred: {self.get_user_name()})")
    
    def get_location(self) -> Optional[str]:
        """Get user's location."""
        return self.data["user_profile"].get("location")
    
    def set_location(self, location: str):
        """Set user's location."""
        self.data["user_profile"]["location"] = location
        self.save_memory()
        logger.info(f"User location set: {location}")
    
    # Preferences and Interests
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        self.data["preferences"][key] = {
            "value": value,
            "learned_date": datetime.now().isoformat()
        }
        self.save_memory()
        logger.info(f"Preference set: {key} = {value}")
    
    def get_preference(self, key: str) -> Optional[Any]:
        """Get a user preference."""
        pref = self.data["preferences"].get(key)
        return pref["value"] if pref else None
    
    def add_interest(self, interest: str):
        """Add user interest."""
        if interest not in self.data["interests"]:
            self.data["interests"].append(interest)
            self.save_memory()
            logger.info(f"Interest added: {interest}")
    
    def get_interests(self) -> List[str]:
        """Get user's interests."""
        return self.data["interests"].copy()
    
    # Learned Facts
    
    def learn_fact(self, key: str, value: str, context: Optional[str] = None):
        """Learn and store a fact about the user."""
        self.data["learned_facts"][key] = {
            "value": value,
            "context": context,
            "learned_date": datetime.now().isoformat()
        }
        self.save_memory()
        logger.info(f"Fact learned: {key} = {value}")
    
    def get_fact(self, key: str) -> Optional[str]:
        """Get a learned fact."""
        fact = self.data["learned_facts"].get(key)
        return fact["value"] if fact else None
    
    def get_all_facts(self) -> Dict[str, str]:
        """Get all learned facts as key-value pairs."""
        return {k: v["value"] for k, v in self.data["learned_facts"].items()}
    
    # Conversation Context
    
    def add_conversation_topic(self, topic: str):
        """Add recent conversation topic."""
        topics = self.data["conversation_context"]["last_topics"]
        if topic not in topics:
            topics.insert(0, topic)  # Add to beginning
            # Keep only last 10 topics
            self.data["conversation_context"]["last_topics"] = topics[:10]
            self.save_memory()
    
    def get_recent_topics(self, limit: int = 5) -> List[str]:
        """Get recent conversation topics."""
        return self.data["conversation_context"]["last_topics"][:limit]
    
    def add_recent_request(self, request: str):
        """Add recent user request."""
        requests = self.data["conversation_context"]["recent_requests"]
        request_entry = {
            "request": request,
            "timestamp": datetime.now().isoformat()
        }
        requests.insert(0, request_entry)
        # Keep only last 5 requests
        self.data["conversation_context"]["recent_requests"] = requests[:5]
        self.save_memory()
    
    # Initialization Checks
    
    def needs_introduction(self) -> bool:
        """Check if user needs to be introduced (no name set)."""
        return not self.get_user_name()
    
    def get_missing_info(self) -> List[str]:
        """Get list of missing basic information."""
        missing = []
        
        if not self.get_user_name():
            missing.append("name")
        if not self.get_location():
            missing.append("location")
        
        return missing
    
    def get_greeting_context(self) -> Dict[str, Any]:
        """Get context for personalized greeting."""
        return {
            "name": self.get_user_name(),
            "recent_topics": self.get_recent_topics(3),
            "interests": self.get_interests()[:3],
            "preferences": dict(list(self.data["preferences"].items())[:3])
        }
    
    # Summary Methods
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all personal information."""
        return {
            "profile": self.data["user_profile"],
            "preferences_count": len(self.data["preferences"]),
            "interests_count": len(self.data["interests"]),
            "facts_count": len(self.data["learned_facts"]),
            "recent_topics": self.get_recent_topics(3)
        }

# Global instance
personal_memory = PersonalMemory()