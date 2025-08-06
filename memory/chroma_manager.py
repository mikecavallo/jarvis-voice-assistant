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
            
            logger.info(f"ChromaDB initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.enabled = False
    
    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection."""
        try:
            return self.client.get_collection(name)
        except ValueError:
            return self.client.create_collection(name)
    
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
        Search conversation history using semantic similarity.
        
        Args:
            query: Search query
            n_results: Number of results to return
            session_filter: Filter by session ID
            
        Returns:
            List of matching conversations with metadata
        """
        where_filter = {"type": "conversation"}
        if session_filter:
            where_filter["session_id"] = session_filter
        
        results = self.conversations.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )
        
        conversations = []
        if results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                conversations.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results.get('distances') else None
                })
        
        logger.debug(f"Found {len(conversations)} conversations for query: {query}")
        return conversations
    
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
        conv_count = self.conversations.count()
        fact_count = self.facts.count()
        
        return {
            "conversations": conv_count,
            "facts": fact_count,
            "total_documents": conv_count + fact_count,
            "db_path": str(self.db_path)
        }

# Global instance - initialize with error handling
try:
    chroma_manager = ChromaManager()
except Exception as e:
    logger.error(f"Failed to initialize ChromaManager: {e}")
    # Create a disabled instance
    chroma_manager = type('DisabledChromaManager', (), {
        'enabled': False,
        'add_conversation': lambda *args, **kwargs: "disabled",
        'add_fact': lambda *args, **kwargs: "disabled", 
        'search_conversations': lambda *args, **kwargs: [],
        'search_facts': lambda *args, **kwargs: [],
        'get_stats': lambda: {"status": "disabled", "reason": str(e)}
    })()