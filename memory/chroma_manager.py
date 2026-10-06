"""
ChromaDB Memory Manager for Jarvis Assistant.

This module handles persistent vector memory storage using ChromaDB for:
- Conversation embeddings for long-term context retrieval
- Structured facts (key-value pairs) with metadata
- Semantic search across conversation history

Part of the Jarvis Assistant memory management system.
"""

import os
import warnings

# Suppress ChromaDB telemetry warnings
os.environ["ANONYMIZED_TELEMETRY"] = "False"
warnings.filterwarnings('ignore', message='.*telemetry.*')

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import uuid
import logging
import json
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

class ChromaManager:
    """
    Manages persistent vector memory storage using ChromaDB.
    
    This class provides interfaces for storing and retrieving:
    - Conversation embeddings with full context
    - Structured facts with metadata
    - Semantic search capabilities
    """
    
    def __init__(self, db_path: str = "memory/chroma_db"):
        """
        Initialize ChromaDB manager.
        
        Args:
            db_path: Path to ChromaDB storage directory
        """
        self.db_path = Path(db_path)
        self.enabled = CHROMADB_AVAILABLE
        
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available. Memory features disabled.")
            return
            
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize collections
            self.conversations = self._get_or_create_collection("conversations")
            self.facts = self._get_or_create_collection("facts")
            
            # Initialize Gmail and Calendar intelligence collections
            self.gmail_intelligence = self._get_or_create_collection("gmail_intelligence")
            self.calendar_events = self._get_or_create_collection("calendar_events")
            self.calendar_intelligence = self._get_or_create_collection("calendar_intelligence")
            
            # Memory prioritization system (memU-inspired)
            self.memory_stats_file = self.db_path / "memory_stats.json"
            self.memory_stats = self._load_memory_stats()
            self.access_counts = defaultdict(int)
            self.last_access_times = defaultdict(float)
            self.email_threads = self._get_or_create_collection("email_threads")
            
            # Adaptive forgetting system (memU-inspired)
            self.archived_conversations = self._get_or_create_collection("archived_conversations")
            self.memory_insights = self._get_or_create_collection("memory_insights")
            
            logger.info(f"ChromaDB initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.enabled = False
    
    def _load_memory_stats(self) -> Dict[str, Any]:
        """Load memory access statistics (memU-inspired prioritization)."""
        if self.memory_stats_file.exists():
            try:
                with open(self.memory_stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load memory stats: {e}")
        
        return {
            "access_counts": {},
            "last_access_times": {},
            "memory_importance": {},
            "created_at": time.time()
        }
    
    def _save_memory_stats(self):
        """Save memory access statistics."""
        try:
            self.memory_stats.update({
                "access_counts": dict(self.access_counts),
                "last_access_times": dict(self.last_access_times),
                "last_updated": time.time()
            })
            
            with open(self.memory_stats_file, 'w') as f:
                json.dump(self.memory_stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory stats: {e}")
    
    def _calculate_memory_priority(self, memory_id: str, content: str, created_at: float = None) -> float:
        """
        Calculate memory priority score using memU-inspired algorithm.
        
        Args:
            memory_id: Unique identifier for the memory
            content: Memory content for analysis
            created_at: Timestamp when memory was created
            
        Returns:
            Priority score (higher = more important)
        """
        current_time = time.time()
        created_at = created_at or current_time
        
        # Factor 1: Recency (newer memories score higher)
        age_hours = (current_time - created_at) / 3600
        recency_score = max(0, 1.0 - (age_hours / (24 * 7)))  # Decay over 1 week
        
        # Factor 2: Access frequency 
        access_count = self.access_counts.get(memory_id, 0)
        frequency_score = min(1.0, access_count / 10)  # Cap at 10 accesses
        
        # Factor 3: Recent access (adaptive forgetting)
        last_access = self.last_access_times.get(memory_id, created_at)
        last_access_hours = (current_time - last_access) / 3600
        recent_access_score = max(0, 1.0 - (last_access_hours / (24 * 3)))  # Decay over 3 days
        
        # Factor 4: Information density (personal info, names, important events)
        content_lower = content.lower()
        importance_keywords = [
            "my name", "call me", "i'm", "i am", "i live", "birthday", "anniversary",
            "important", "remember", "don't forget", "password", "phone", "address",
            "family", "work", "job", "doctor", "appointment", "meeting"
        ]
        
        importance_score = sum(0.1 for keyword in importance_keywords if keyword in content_lower)
        importance_score = min(1.0, importance_score)  # Cap at 1.0
        
        # Combined weighted score (memU adaptive approach)
        priority = (
            recency_score * 0.3 +      # 30% recency
            frequency_score * 0.2 +    # 20% frequency  
            recent_access_score * 0.3 + # 30% recent access
            importance_score * 0.2      # 20% content importance
        )
        
        return priority
    
    def adaptive_memory_maintenance(self, max_conversations: int = 100):
        """
        Perform adaptive forgetting by archiving low-priority memories (memU-inspired).
        
        This method implements memU's approach where "less relevant content is 
        deprioritized or forgotten" while keeping important memories accessible.
        
        Args:
            max_conversations: Maximum number of conversations to keep active
        """
        try:
            # Get all conversations with their metadata
            all_conversations = self.conversations.get()
            
            if not all_conversations['documents'] or len(all_conversations['documents']) <= max_conversations:
                logger.debug("Memory maintenance not needed - within limits")
                return
            
            logger.info(f"Starting adaptive memory maintenance - {len(all_conversations['documents'])} conversations")
            
            # Calculate priority for each conversation
            conversations_with_priority = []
            
            for i, doc in enumerate(all_conversations['documents']):
                doc_id = all_conversations['ids'][i]
                metadata = all_conversations['metadatas'][i] if all_conversations['metadatas'] else {}
                
                # Get creation timestamp
                created_at = metadata.get('timestamp')
                if created_at:
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                    except Exception:
                        created_at = time.time()
                else:
                    created_at = time.time()
                
                priority = self._calculate_memory_priority(doc_id, doc, created_at)
                
                conversations_with_priority.append({
                    'id': doc_id,
                    'document': doc,
                    'metadata': metadata,
                    'priority': priority
                })
            
            # Sort by priority (lowest first for archiving)
            conversations_with_priority.sort(key=lambda x: x['priority'])
            
            # Archive low-priority conversations (bottom 30% or excess beyond max_conversations)
            archive_count = max(
                len(conversations_with_priority) - max_conversations,  # Excess beyond limit
                int(len(conversations_with_priority) * 0.1)  # At least 10% if over limit
            )
            
            if archive_count > 0:
                conversations_to_archive = conversations_with_priority[:archive_count]
                
                logger.info(f"Archiving {len(conversations_to_archive)} low-priority conversations")
                
                # Move conversations to archive
                archive_docs = []
                archive_metadatas = []
                archive_ids = []
                remove_ids = []
                
                for conv in conversations_to_archive:
                    # Prepare for archive
                    archive_metadata = conv['metadata'].copy()
                    archive_metadata['archived_at'] = datetime.now().isoformat()
                    archive_metadata['original_priority'] = conv['priority']
                    archive_metadata['type'] = 'archived_conversation'
                    
                    archive_docs.append(conv['document'])
                    archive_metadatas.append(archive_metadata)
                    archive_ids.append(conv['id'])
                    remove_ids.append(conv['id'])
                
                # Add to archive collection
                if archive_docs:
                    self.archived_conversations.add(
                        documents=archive_docs,
                        metadatas=archive_metadatas,
                        ids=archive_ids
                    )
                    
                    # Remove from active conversations
                    self.conversations.delete(ids=remove_ids)
                    
                    logger.info(f"Successfully archived {len(archive_docs)} conversations")
                    
                    # Clean up access stats for archived conversations
                    for conv_id in remove_ids:
                        if conv_id in self.access_counts:
                            del self.access_counts[conv_id]
                        if conv_id in self.last_access_times:
                            del self.last_access_times[conv_id]
                    
                    self._save_memory_stats()
                    
        except Exception as e:
            logger.error(f"Error during adaptive memory maintenance: {e}")
    
    def search_archived_conversations(self, query: str, n_results: int = 3) -> List[Dict]:
        """Search archived conversations if needed (for very old memories)."""
        try:
            results = self.archived_conversations.query(
                query_texts=[query],
                n_results=n_results,
                where={"type": "archived_conversation"}
            )
            
            conversations = []
            if results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    conversations.append({
                        'document': doc,
                        'content': doc,
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if results.get('distances') else None,
                        'archived': True
                    })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error searching archived conversations: {e}")
            return []
    
    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection."""
        # get_or_create_collection works across chromadb 0.4.x and 1.x
        # (1.x raises NotFoundError instead of ValueError from get_collection).
        return self.client.get_or_create_collection(name)
    
    def add_conversation(self, 
                        conversation_text: str, 
                        session_id: str,
                        speaker: str = "user",
                        metadata: Optional[Dict] = None) -> str:
        """
        Add a conversation to memory with embeddings.
        
        Args:
            conversation_text: The conversation content
            session_id: Unique session identifier
            speaker: Who spoke ("user" or "jarvis")
            metadata: Additional metadata
            
        Returns:
            Document ID for the stored conversation
        """
        if not self.enabled:
            logger.warning("ChromaDB not available - conversation not stored")
            return "disabled"
            
        if not hasattr(self, 'conversations'):
            logger.error("ChromaDB collections not initialized")
            return "error"
        doc_id = str(uuid.uuid4())
        
        conversation_metadata = {
            "session_id": session_id,
            "speaker": speaker,
            "timestamp": datetime.now().isoformat(),
            "type": "conversation"
        }
        
        if metadata:
            conversation_metadata.update(metadata)
        
        self.conversations.add(
            documents=[conversation_text],
            metadatas=[conversation_metadata],
            ids=[doc_id]
        )
        
        logger.debug(f"Added conversation: {doc_id[:8]}...")
        return doc_id
    
    def add_fact(self, 
                 key: str, 
                 value: str, 
                 session_id: str,
                 summary: Optional[str] = None) -> str:
        """
        Add a structured fact to memory.
        
        Args:
            key: Fact key/category
            value: Fact value/content
            session_id: Session where fact was learned
            summary: Brief summary of the fact
            
        Returns:
            Document ID for the stored fact
        """
        doc_id = str(uuid.uuid4())
        
        fact_text = f"{key}: {value}"
        if summary:
            fact_text += f" ({summary})"
        
        fact_metadata = {
            "key": key,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "type": "fact",
            "summary": summary or f"Fact about {key}"
        }
        
        self.facts.add(
            documents=[fact_text],
            metadatas=[fact_metadata],
            ids=[doc_id]
        )
        
        logger.debug(f"Added fact: {key} = {value}")
        return doc_id
    
    def search_conversations(self, 
                           query: str, 
                           n_results: int = 5,
                           session_filter: Optional[str] = None) -> List[Dict]:
        """
        Search conversation history using memU-inspired prioritization and semantic similarity.
        
        Args:
            query: Search query
            n_results: Number of results to return
            session_filter: Filter by session ID
            
        Returns:
            List of matching conversations with metadata, sorted by priority
        """
        where_filter = {"type": "conversation"}
        if session_filter:
            where_filter["session_id"] = session_filter
        
        # Get more results initially for priority filtering
        search_results = min(n_results * 3, 50)  # Search 3x more, capped at 50
        
        results = self.conversations.query(
            query_texts=[query],
            n_results=search_results,
            where=where_filter
        )
        
        conversations = []
        if results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                doc_id = metadata.get('id', f"conv_{i}")
                
                # Calculate priority using memU algorithm
                created_at = metadata.get('timestamp')
                if created_at:
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                    except Exception:
                        created_at = time.time()
                else:
                    created_at = time.time()
                
                priority = self._calculate_memory_priority(doc_id, doc, created_at)
                
                # Track access for adaptive learning
                self.access_counts[doc_id] += 1
                self.last_access_times[doc_id] = time.time()
                
                conversations.append({
                    'document': doc,  # Use 'document' key for compatibility
                    'content': doc,   # Also keep 'content' for backward compatibility  
                    'metadata': metadata,
                    'distance': results['distances'][0][i] if results.get('distances') else None,
                    'priority': priority,
                    'id': doc_id
                })
        
        # Sort by combined score: priority + semantic similarity
        def combined_score(conv):
            # Lower distance = higher similarity, so invert it
            similarity_score = 1.0 - (conv.get('distance', 1.0) if conv.get('distance') is not None else 1.0)
            priority_score = conv.get('priority', 0.0)
            
            # Weight: 60% priority, 40% similarity (memU approach)
            return priority_score * 0.6 + similarity_score * 0.4
        
        conversations.sort(key=combined_score, reverse=True)
        
        # Save updated access stats
        self._save_memory_stats()
        
        # Return top N results
        final_results = conversations[:n_results]
        
        logger.debug(f"Found {len(conversations)} conversations, returning top {len(final_results)} by priority")
        return final_results
    
    def search_facts(self, 
                    query: str, 
                    n_results: int = 10) -> List[Dict]:
        """
        Search stored facts using semantic similarity.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of matching facts with metadata
        """
        results = self.facts.query(
            query_texts=[query],
            n_results=n_results,
            where={"type": "fact"}
        )
        
        facts = []
        if results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                facts.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results.get('distances') else None
                })
        
        logger.debug(f"Found {len(facts)} facts for query: {query}")
        return facts
    
    def get_fact_by_key(self, key: str) -> Optional[Dict]:
        """
        Get the most recent fact by key.
        
        Args:
            key: Fact key to search for
            
        Returns:
            Most recent fact with that key, or None
        """
        results = self.facts.query(
            query_texts=[key],
            n_results=1,
            where={"type": "fact", "key": key}
        )
        
        if results['documents'][0]:
            return {
                'content': results['documents'][0][0],
                'metadata': results['metadatas'][0][0]
            }
        
        return None
    
    def get_conversation_context(self, 
                               session_id: str, 
                               limit: int = 10) -> List[Dict]:
        """
        Get recent conversation context for a session.
        
        Args:
            session_id: Session to get context for
            limit: Maximum number of conversations to return
            
        Returns:
            List of recent conversations in chronological order
        """
        # Get all conversations for session
        results = self.conversations.get(
            where={"session_id": session_id, "type": "conversation"},
            limit=limit
        )
        
        conversations = []
        if results['documents']:
            for i, doc in enumerate(results['documents']):
                conversations.append({
                    'content': doc,
                    'metadata': results['metadatas'][i],
                    'id': results['ids'][i]
                })
        
        # Sort by timestamp
        conversations.sort(key=lambda x: x['metadata']['timestamp'])
        
        logger.debug(f"Retrieved {len(conversations)} conversations for session {session_id}")
        return conversations
    
    def add_email_intelligence(self, 
                             email_data: Dict[str, Any],
                             analysis: Optional[Dict] = None) -> str:
        """
        Add email data to intelligence collection.
        
        Args:
            email_data: Email data dictionary
            analysis: Optional analysis data
            
        Returns:
            Document ID for stored email intelligence
        """
        if not self.enabled or not hasattr(self, 'gmail_intelligence'):
            return "disabled"
        
        doc_id = str(uuid.uuid4())
        email_text = f"{email_data.get('subject', '')} {email_data.get('body', '')}"
        
        intelligence_metadata = {
            "email_id": email_data.get('id'),
            "type": "email_intelligence",
            "from": email_data.get('from', ''),
            "subject": email_data.get('subject', ''),
            "category": analysis.get('category') if analysis else 'unknown',
            "urgency": analysis.get('urgency') if analysis else 'normal',
            "has_action_items": bool(analysis.get('action_items')) if analysis else False,
            "timestamp": email_data.get('timestamp', datetime.now().isoformat()),
            "processed_at": datetime.now().isoformat()
        }
        
        self.gmail_intelligence.add(
            documents=[email_text],
            metadatas=[intelligence_metadata],
            ids=[doc_id]
        )
        
        logger.debug(f"Added email intelligence: {doc_id[:8]}...")
        return doc_id
    
    def add_calendar_event(self, 
                          event_data: Dict[str, Any]) -> str:
        """
        Add calendar event to intelligence collection.
        
        Args:
            event_data: Calendar event data
            
        Returns:
            Document ID for stored calendar event
        """
        if not self.enabled or not hasattr(self, 'calendar_events'):
            return "disabled"
        
        doc_id = str(uuid.uuid4())
        event_text = f"{event_data.get('summary', '')} {event_data.get('description', '')} at {event_data.get('location', '')}"
        
        event_metadata = {
            "event_id": event_data.get('id'),
            "type": "calendar_event",
            "summary": event_data.get('summary', ''),
            "start_time": event_data.get('start_time'),
            "end_time": event_data.get('end_time'),
            "location": event_data.get('location', ''),
            "attendee_count": len(event_data.get('attendees', [])),
            "has_location": bool(event_data.get('location')),
            "timestamp": datetime.now().isoformat()
        }
        
        self.calendar_events.add(
            documents=[event_text],
            metadatas=[event_metadata],
            ids=[doc_id]
        )
        
        logger.debug(f"Added calendar event: {event_data.get('summary', 'Unknown')}")
        return doc_id
    
    def search_email_intelligence(self, 
                                query: str, 
                                n_results: int = 10,
                                category_filter: Optional[str] = None) -> List[Dict]:
        """
        Search email intelligence using semantic similarity.
        
        Args:
            query: Search query
            n_results: Number of results to return
            category_filter: Filter by email category
            
        Returns:
            List of matching email intelligence with metadata
        """
        if not self.enabled or not hasattr(self, 'gmail_intelligence'):
            return []
        
        where_filter = {"type": "email_intelligence"}
        if category_filter:
            where_filter["category"] = category_filter
        
        results = self.gmail_intelligence.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )
        
        intelligence = []
        if results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                intelligence.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results.get('distances') else None
                })
        
        logger.debug(f"Found {len(intelligence)} email intelligence results for query: {query}")
        return intelligence
    
    def search_calendar_events(self, 
                             query: str, 
                             n_results: int = 10,
                             time_filter: Optional[str] = None) -> List[Dict]:
        """
        Search calendar events using semantic similarity.
        
        Args:
            query: Search query
            n_results: Number of results to return
            time_filter: Optional time-based filter
            
        Returns:
            List of matching calendar events with metadata
        """
        if not self.enabled or not hasattr(self, 'calendar_events'):
            return []
        
        where_filter = {"type": "calendar_event"}
        
        results = self.calendar_events.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )
        
        events = []
        if results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                events.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results.get('distances') else None
                })
        
        logger.debug(f"Found {len(events)} calendar events for query: {query}")
        return events
    
    def cleanup_old_data(self, days_old: int = 30):
        """
        Clean up conversations older than specified days.
        
        Args:
            days_old: Number of days to keep data
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cutoff_iso = cutoff_date.isoformat()
        
        # Note: ChromaDB doesn't support date range queries directly
        # This is a placeholder for future implementation
        logger.info(f"Cleanup would remove data older than {cutoff_iso}")
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.
        
        Returns:
            Dictionary with collection counts and stats
        """
        if not self.enabled:
            return {"status": "disabled"}
        
        conv_count = self.conversations.count()
        fact_count = self.facts.count()
        
        # Get counts for Gmail and Calendar collections
        gmail_count = 0
        calendar_count = 0
        calendar_intel_count = 0
        email_threads_count = 0
        
        try:
            if hasattr(self, 'gmail_intelligence'):
                gmail_count = self.gmail_intelligence.count()
            if hasattr(self, 'calendar_events'):
                calendar_count = self.calendar_events.count()
            if hasattr(self, 'calendar_intelligence'):
                calendar_intel_count = self.calendar_intelligence.count()
            if hasattr(self, 'email_threads'):
                email_threads_count = self.email_threads.count()
        except Exception as e:
            logger.warning(f"Failed to get collection counts: {e}")
        
        total_docs = conv_count + fact_count + gmail_count + calendar_count + calendar_intel_count + email_threads_count
        
        return {
            "conversations": conv_count,
            "facts": fact_count,
            "gmail_intelligence": gmail_count,
            "calendar_events": calendar_count,
            "calendar_intelligence": calendar_intel_count,
            "email_threads": email_threads_count,
            "total_documents": total_docs,
            "db_path": str(self.db_path),
            "enabled": self.enabled
        }

# Global instance - initialize with error handling
try:
    chroma_manager = ChromaManager()
except Exception as e:
    logger.error(f"Failed to initialize ChromaManager: {e}")
    _disabled_reason = str(e)  # `e` is unbound after the except block ends
    # Create a disabled instance
    chroma_manager = type('DisabledChromaManager', (), {
        'enabled': False,
        'add_conversation': lambda *args, **kwargs: "disabled",
        'add_fact': lambda *args, **kwargs: "disabled", 
        'search_conversations': lambda *args, **kwargs: [],
        'search_facts': lambda *args, **kwargs: [],
        'get_stats': lambda *args, **kwargs: {"status": "disabled", "reason": _disabled_reason}
    })()