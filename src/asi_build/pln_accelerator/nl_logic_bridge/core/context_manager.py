"""
Context Manager for NL-Logic Bridge.

This module manages conversational context, session state, and contextual information
to enable coherent multi-turn interactions and context-aware translations.
"""

import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ContextType(Enum):
    """Types of context information."""

    CONVERSATIONAL = "conversational"
    DOMAIN = "domain"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    USER_PROFILE = "user_profile"
    SESSION = "session"
    DISCOURSE = "discourse"


@dataclass
class ContextItem:
    """Individual piece of context information."""

    key: str
    value: Any
    context_type: ContextType
    timestamp: float
    confidence: float
    source: str
    decay_rate: float = 0.1
    importance: float = 0.5

    def is_expired(self, max_age: float = 3600) -> bool:
        """Check if context item has expired."""
        age = time.time() - self.timestamp
        return age > max_age

    def get_current_confidence(self) -> float:
        """Get confidence adjusted for time decay."""
        age = time.time() - self.timestamp
        decayed_confidence = self.confidence * (1.0 - self.decay_rate * age / 3600)
        return max(0.0, decayed_confidence)


@dataclass
class SessionContext:
    """Context for a specific session."""

    session_id: str
    start_time: float
    last_activity: float
    context_items: Dict[str, ContextItem] = field(default_factory=dict)
    conversation_history: deque = field(default_factory=lambda: deque(maxlen=100))
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    domain_context: Dict[str, Any] = field(default_factory=dict)
    active_topics: Set[str] = field(default_factory=set)

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def is_active(self, timeout: float = 1800) -> bool:
        """Check if session is still active."""
        return (time.time() - self.last_activity) < timeout


class ContextManager:
    """
    Context Manager for maintaining conversational and session context.

    This class manages different types of context information to enable
    coherent multi-turn conversations and context-aware processing.
    """

    def __init__(self, max_sessions: int = 1000):
        """Initialize the context manager."""
        self.logger = logging.getLogger(__name__)
        self.max_sessions = max_sessions

        # Session storage
        self.sessions: Dict[str, SessionContext] = {}
        self.global_context: Dict[str, ContextItem] = {}

        # Thread safety
        self.lock = threading.RLock()

        # Statistics
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "context_items_stored": 0,
            "context_retrievals": 0,
        }

        # Context patterns and rules
        self._init_context_patterns()

    def _init_context_patterns(self):
        """Initialize context extraction patterns and rules."""
        self.context_extractors = {
            ContextType.TEMPORAL: {
                "patterns": [
                    r"(yesterday|today|tomorrow|now|then|recently|soon)",
                    r"(\d{1,2}:\d{2}|\d{1,2}\s*(am|pm))",
                    r"(morning|afternoon|evening|night)",
                    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                    r"(january|february|march|april|may|june|july|august|september|october|november|december)",
                ],
                "decay_rate": 0.2,
            },
            ContextType.SPATIAL: {
                "patterns": [
                    r"(here|there|nearby|far|close|distant)",
                    r"(north|south|east|west|left|right|up|down)",
                    r"(inside|outside|above|below|behind|in front of)",
                ],
                "decay_rate": 0.1,
            },
            ContextType.DOMAIN: {
                "patterns": [
                    r"(medical|health|doctor|patient|symptoms)",
                    r"(legal|law|court|attorney|contract)",
                    r"(technical|software|computer|programming|code)",
                    r"(business|finance|money|profit|investment)",
                ],
                "decay_rate": 0.05,
            },
        }

        # Coreference patterns
        self.coreference_patterns = {
            "pronouns": ["it", "he", "she", "they", "this", "that", "these", "those"],
            "definite_references": ["the above", "the following", "such", "said"],
        }

    def create_session(self, session_id: str, user_id: Optional[str] = None) -> SessionContext:
        """Create a new session context."""
        with self.lock:
            if session_id in self.sessions:
                # Update existing session
                self.sessions[session_id].update_activity()
                return self.sessions[session_id]

            # Clean up old sessions if at limit
            if len(self.sessions) >= self.max_sessions:
                self._cleanup_old_sessions()

            # Create new session
            session = SessionContext(
                session_id=session_id, start_time=time.time(), last_activity=time.time()
            )

            if user_id:
                session.context_items["user_id"] = ContextItem(
                    key="user_id",
                    value=user_id,
                    context_type=ContextType.USER_PROFILE,
                    timestamp=time.time(),
                    confidence=1.0,
                    source="system",
                    decay_rate=0.0,  # User ID doesn't decay
                    importance=1.0,
                )

            self.sessions[session_id] = session
            self.stats["total_sessions"] += 1
            self.stats["active_sessions"] += 1

            self.logger.info(f"Created new session: {session_id}")
            return session

    def update_session_context(
        self, session_id: str, text: str, additional_context: Optional[Dict[str, Any]] = None
    ):
        """Update session context with new information."""
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                session = self.create_session(session_id)

            session.update_activity()

            # Add to conversation history
            session.conversation_history.append(
                {"timestamp": time.time(), "text": text, "context": additional_context or {}}
            )

            # Extract context from text
            extracted_context = self._extract_context_from_text(text)

            # Add extracted context to session
            for item in extracted_context:
                session.context_items[item.key] = item

            # Add additional context if provided
            if additional_context:
                for key, value in additional_context.items():
                    context_item = ContextItem(
                        key=key,
                        value=value,
                        context_type=ContextType.SESSION,
                        timestamp=time.time(),
                        confidence=0.8,
                        source="user_provided",
                        importance=0.7,
                    )
                    session.context_items[key] = context_item

            # Update active topics
            self._update_active_topics(session, text)

            self.stats["context_items_stored"] += len(extracted_context)

    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get context for a specific session."""
        with self.lock:
            self.stats["context_retrievals"] += 1

            session = self.sessions.get(session_id)
            if not session:
                return {}

            session.update_activity()

            # Build context dictionary
            context = {
                "session_id": session_id,
                "session_start": session.start_time,
                "last_activity": session.last_activity,
                "conversation_length": len(session.conversation_history),
                "active_topics": list(session.active_topics),
                "user_preferences": session.user_preferences.copy(),
                "domain_context": session.domain_context.copy(),
            }

            # Add current context items (non-expired)
            current_context = {}
            for key, item in session.context_items.items():
                if not item.is_expired() and item.get_current_confidence() > 0.1:
                    current_context[key] = {
                        "value": item.value,
                        "type": item.context_type.value,
                        "confidence": item.get_current_confidence(),
                        "age": time.time() - item.timestamp,
                        "importance": item.importance,
                    }

            context["current_context"] = current_context

            # Add recent conversation context
            recent_history = list(session.conversation_history)[-10:]  # Last 10 exchanges
            context["recent_conversation"] = recent_history

            # Add global context that might be relevant
            relevant_global = self._get_relevant_global_context(session)
            context["global_context"] = relevant_global

            return context

    def _extract_context_from_text(self, text: str) -> List[ContextItem]:
        """Extract context information from text."""
        extracted_items = []
        text_lower = text.lower()

        # Extract temporal context
        temporal_items = self._extract_temporal_context(text, text_lower)
        extracted_items.extend(temporal_items)

        # Extract spatial context
        spatial_items = self._extract_spatial_context(text, text_lower)
        extracted_items.extend(spatial_items)

        # Extract domain context
        domain_items = self._extract_domain_context(text, text_lower)
        extracted_items.extend(domain_items)

        # Extract entities as context
        entity_items = self._extract_entity_context(text)
        extracted_items.extend(entity_items)

        return extracted_items

    def _extract_temporal_context(self, text: str, text_lower: str) -> List[ContextItem]:
        """Extract temporal context from text."""
        items = []

        import re

        for pattern in self.context_extractors[ContextType.TEMPORAL]["patterns"]:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]  # Take first group from regex

                item = ContextItem(
                    key=f"temporal_{match}",
                    value=match,
                    context_type=ContextType.TEMPORAL,
                    timestamp=time.time(),
                    confidence=0.7,
                    source="text_extraction",
                    decay_rate=self.context_extractors[ContextType.TEMPORAL]["decay_rate"],
                    importance=0.6,
                )
                items.append(item)

        return items

    def _extract_spatial_context(self, text: str, text_lower: str) -> List[ContextItem]:
        """Extract spatial context from text."""
        items = []

        import re

        for pattern in self.context_extractors[ContextType.SPATIAL]["patterns"]:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]

                item = ContextItem(
                    key=f"spatial_{match}",
                    value=match,
                    context_type=ContextType.SPATIAL,
                    timestamp=time.time(),
                    confidence=0.6,
                    source="text_extraction",
                    decay_rate=self.context_extractors[ContextType.SPATIAL]["decay_rate"],
                    importance=0.5,
                )
                items.append(item)

        return items

    def _extract_domain_context(self, text: str, text_lower: str) -> List[ContextItem]:
        """Extract domain-specific context from text."""
        items = []

        import re

        for pattern in self.context_extractors[ContextType.DOMAIN]["patterns"]:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]

                # Determine domain based on match
                domain = self._classify_domain(match)

                item = ContextItem(
                    key=f"domain_{domain}",
                    value=domain,
                    context_type=ContextType.DOMAIN,
                    timestamp=time.time(),
                    confidence=0.8,
                    source="text_extraction",
                    decay_rate=self.context_extractors[ContextType.DOMAIN]["decay_rate"],
                    importance=0.8,
                )
                items.append(item)

        return items

    def _extract_entity_context(self, text: str) -> List[ContextItem]:
        """Extract named entities as context."""
        items = []

        # Simple entity extraction (in full implementation, would use NER)
        import re

        # Extract potential proper nouns (capitalized words)
        proper_nouns = re.findall(r"\b[A-Z][a-z]+\b", text)

        for noun in proper_nouns[:5]:  # Limit to 5 entities
            item = ContextItem(
                key=f"entity_{noun.lower()}",
                value=noun,
                context_type=ContextType.DISCOURSE,
                timestamp=time.time(),
                confidence=0.5,
                source="entity_extraction",
                decay_rate=0.1,
                importance=0.6,
            )
            items.append(item)

        return items

    def _classify_domain(self, keyword: str) -> str:
        """Classify domain based on keyword."""
        domain_keywords = {
            "medical": ["medical", "health", "doctor", "patient", "symptoms", "diagnosis"],
            "legal": ["legal", "law", "court", "attorney", "contract", "lawsuit"],
            "technical": ["technical", "software", "computer", "programming", "code", "system"],
            "business": ["business", "finance", "money", "profit", "investment", "market"],
        }

        for domain, keywords in domain_keywords.items():
            if keyword.lower() in keywords:
                return domain

        return "general"

    def _update_active_topics(self, session: SessionContext, text: str):
        """Update active topics based on text content."""
        # Simple topic extraction based on keywords
        # In full implementation, would use topic modeling

        keywords = text.lower().split()

        # Filter out common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        meaningful_words = [word for word in keywords if word not in stop_words and len(word) > 3]

        # Add to active topics (keep top 10)
        for word in meaningful_words[:5]:
            session.active_topics.add(word)

        # Keep only most recent topics
        if len(session.active_topics) > 10:
            # Convert to list, keep last 10, convert back to set
            topic_list = list(session.active_topics)
            session.active_topics = set(topic_list[-10:])

    def _get_relevant_global_context(self, session: SessionContext) -> Dict[str, Any]:
        """Get globally relevant context for the session."""
        relevant_context = {}

        # Get global context items that match session topics
        for key, item in self.global_context.items():
            if not item.is_expired() and item.get_current_confidence() > 0.3:
                # Check if item is relevant to current session
                if any(topic in key.lower() for topic in session.active_topics):
                    relevant_context[key] = {
                        "value": item.value,
                        "confidence": item.get_current_confidence(),
                        "type": item.context_type.value,
                    }

        return relevant_context

    def add_global_context(
        self,
        key: str,
        value: Any,
        context_type: ContextType,
        confidence: float = 0.8,
        source: str = "system",
    ):
        """Add global context that applies across sessions."""
        with self.lock:
            item = ContextItem(
                key=key,
                value=value,
                context_type=context_type,
                timestamp=time.time(),
                confidence=confidence,
                source=source,
                importance=0.7,
            )

            self.global_context[key] = item

    def resolve_coreference(self, session_id: str, text: str) -> str:
        """Resolve coreferences in text using session context."""
        session = self.sessions.get(session_id)
        if not session:
            return text

        resolved_text = text

        # Simple coreference resolution
        for pronoun in self.coreference_patterns["pronouns"]:
            if pronoun in text.lower():
                # Find most recent relevant entity
                recent_entity = self._find_recent_entity(session, pronoun)
                if recent_entity:
                    resolved_text = resolved_text.replace(pronoun, recent_entity)

        return resolved_text

    def _find_recent_entity(self, session: SessionContext, pronoun: str) -> Optional[str]:
        """Find the most recent entity that could be referenced by pronoun."""
        # Look through recent conversation history for entities
        for entry in reversed(list(session.conversation_history)[-5:]):  # Last 5 entries
            text = entry["text"]

            # Extract entities from text (simplified)
            import re

            entities = re.findall(r"\b[A-Z][a-z]+\b", text)

            if entities:
                return entities[0]  # Return first entity found

        return None

    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of current context state."""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        # Count context items by type
        type_counts = defaultdict(int)
        confidence_scores = []

        for item in session.context_items.values():
            if not item.is_expired():
                type_counts[item.context_type.value] += 1
                confidence_scores.append(item.get_current_confidence())

        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        )

        return {
            "session_id": session_id,
            "active_context_items": len(
                [item for item in session.context_items.values() if not item.is_expired()]
            ),
            "context_by_type": dict(type_counts),
            "average_confidence": avg_confidence,
            "active_topics": list(session.active_topics),
            "conversation_length": len(session.conversation_history),
            "session_age_minutes": (time.time() - session.start_time) / 60,
        }

    def _cleanup_old_sessions(self):
        """Clean up old inactive sessions."""
        current_time = time.time()
        sessions_to_remove = []

        for session_id, session in self.sessions.items():
            if not session.is_active():
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            self.stats["active_sessions"] -= 1

        if sessions_to_remove:
            self.logger.info(f"Cleaned up {len(sessions_to_remove)} inactive sessions")

    def cleanup_expired_context(self):
        """Clean up expired context items from all sessions."""
        cleaned_items = 0

        with self.lock:
            # Clean session contexts
            for session in self.sessions.values():
                expired_keys = [
                    key for key, item in session.context_items.items() if item.is_expired()
                ]
                for key in expired_keys:
                    del session.context_items[key]
                    cleaned_items += 1

            # Clean global context
            expired_global_keys = [
                key for key, item in self.global_context.items() if item.is_expired()
            ]
            for key in expired_global_keys:
                del self.global_context[key]
                cleaned_items += 1

        if cleaned_items > 0:
            self.logger.info(f"Cleaned up {cleaned_items} expired context items")

    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        with self.lock:
            return {
                **self.stats,
                "active_sessions": len([s for s in self.sessions.values() if s.is_active()]),
                "total_context_items": sum(len(s.context_items) for s in self.sessions.values())
                + len(self.global_context),
            }
