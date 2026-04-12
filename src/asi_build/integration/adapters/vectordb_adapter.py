"""
VectorDB ↔ Blackboard Adapter
=================================

Bridges the vectordb module (``EmbeddingPipeline``, ``SemanticSearchEngine``,
``VectorDBConfig``) with the Cognitive Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``vectordb.search_results``   — Semantic search results from queries
- ``vectordb.index_stats``      — Index statistics and health
- ``vectordb.embeddings``       — Embedding generation metrics

Topics consumed
~~~~~~~~~~~~~~~
- ``knowledge_graph``           — KG triples → index as searchable vectors
- ``reasoning``                 — Reasoning inferences → semantic search for related work

Events emitted
~~~~~~~~~~~~~~
- ``vectordb.search.completed`` — A semantic search query completed
- ``vectordb.index.updated``    — Index was updated with new documents

Events listened
~~~~~~~~~~~~~~~
- ``knowledge_graph.triple.added``     — Auto-index new triples
- ``reasoning.inference.completed``    — Trigger similarity search for related inferences
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Sequence

from ..protocols import (
    BlackboardEntry,
    BlackboardQuery,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    EventHandler,
    ModuleCapability,
    ModuleInfo,
)

logger = logging.getLogger(__name__)

_vectordb_module = None


def _get_vectordb():
    """Lazy import of vectordb module to allow graceful degradation."""
    global _vectordb_module
    if _vectordb_module is None:
        try:
            from asi_build import vectordb as _vm

            _vectordb_module = _vm
        except (ImportError, ModuleNotFoundError):
            _vectordb_module = False
    return _vectordb_module if _vectordb_module is not False else None


class VectorDBBlackboardAdapter:
    """Adapter connecting the vectordb module to the Cognitive Blackboard.

    Wraps up to three components:

    - ``EmbeddingPipeline`` — embedding generation for text/documents
    - ``SemanticSearchEngine`` — multi-backend semantic search
    - ``VectorDBConfig`` — database configuration and connection state

    If a component is ``None``, the adapter gracefully skips operations
    involving that component.

    Parameters
    ----------
    embedding_pipeline : optional
        An ``EmbeddingPipeline`` instance.
    search_engine : optional
        A ``SemanticSearchEngine`` instance.
    config : optional
        A ``VectorDBConfig`` instance.
    search_results_ttl : float
        TTL in seconds for search result entries (default 120).
    index_stats_ttl : float
        TTL for index statistics entries (default 300).
    embeddings_ttl : float
        TTL for embedding metrics entries (default 180).
    """

    MODULE_NAME = "vectordb"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        embedding_pipeline: Any = None,
        search_engine: Any = None,
        config: Any = None,
        *,
        search_results_ttl: float = 120.0,
        index_stats_ttl: float = 300.0,
        embeddings_ttl: float = 180.0,
    ) -> None:
        self._embedding_pipeline = embedding_pipeline
        self._search_engine = search_engine
        self._config = config
        self._search_results_ttl = search_results_ttl
        self._index_stats_ttl = index_stats_ttl
        self._embeddings_ttl = embeddings_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # State tracking
        self._pending_search_results: List[Dict[str, Any]] = []
        self._last_index_doc_count: Optional[int] = None
        self._total_searches: int = 0
        self._total_embeddings_generated: int = 0
        self._last_embedding_stats: Optional[Dict[str, Any]] = None

    # ── BlackboardParticipant protocol ────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER
                | ModuleCapability.CONSUMER
                | ModuleCapability.TRANSFORMER
            ),
            description=(
                "Vector database: embedding generation, semantic search, "
                "and multi-backend vector indexing."
            ),
            topics_produced=frozenset(
                {
                    "vectordb.search_results",
                    "vectordb.index_stats",
                    "vectordb.embeddings",
                }
            ),
            topics_consumed=frozenset(
                {
                    "knowledge_graph",
                    "reasoning",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "VectorDBBlackboardAdapter registered with blackboard "
            "(pipeline=%s, search=%s, config=%s)",
            self._embedding_pipeline is not None,
            self._search_engine is not None,
            self._config is not None,
        )

    # ── EventEmitter protocol ─────────────────────────────────────────

    def set_event_handler(self, handler: EventHandler) -> None:
        self._event_handler = handler

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit an event via the injected handler."""
        if self._event_handler is not None:
            self._event_handler(
                CognitiveEvent(
                    event_type=event_type,
                    payload=payload,
                    source=self.MODULE_NAME,
                )
            )

    # ── EventListener protocol ────────────────────────────────────────

    def handle_event(self, event: CognitiveEvent) -> None:
        """Handle incoming events from other modules."""
        try:
            if event.event_type.startswith("knowledge_graph."):
                self._handle_kg_event(event)
            elif event.event_type.startswith("reasoning."):
                self._handle_reasoning_event(event)
        except Exception:
            logger.debug(
                "VectorDBBlackboardAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current vectordb state."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            # Flush any pending search results
            search_entries = self._produce_search_results()
            entries.extend(search_entries)

            index_entry = self._produce_index_stats()
            if index_entry is not None:
                entries.append(index_entry)

            embed_entry = self._produce_embeddings()
            if embed_entry is not None:
                entries.append(embed_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        KG triples → index as searchable vectors.
        Reasoning inferences → trigger semantic search for related work.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("knowledge_graph."):
                    self._consume_kg(entry)
                elif entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
            except Exception:
                logger.debug(
                    "VectorDBBlackboardAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Public API for external search requests ───────────────────────

    def search(self, query_text: str, top_k: int = 10) -> Optional[Dict[str, Any]]:
        """Execute a semantic search and queue results for next production sweep.

        Returns the search results dict immediately (or None on failure).
        Results are also buffered for the next ``produce()`` call.
        """
        if self._search_engine is None:
            return None

        try:
            # Build a SearchQuery if the class is available
            vdb = _get_vectordb()
            SearchQuery = None
            if vdb is not None:
                SearchQuery = getattr(vdb, "SearchQuery", None)
                if SearchQuery is None:
                    try:
                        from asi_build.vectordb.core.search import SearchQuery as _SQ
                        SearchQuery = _SQ
                    except (ImportError, AttributeError):
                        pass

            if SearchQuery is not None:
                query = SearchQuery(
                    query_text=query_text,
                    top_k=top_k,
                )
                results = self._search_engine.search(query)
            else:
                # Fallback: call search with kwargs
                search_fn = getattr(self._search_engine, "search", None)
                if search_fn is None:
                    return None
                results = search_fn(query_text=query_text, top_k=top_k)

            # Normalize results
            if isinstance(results, list):
                result_data = {
                    "query": query_text,
                    "top_k": top_k,
                    "results": [
                        {
                            "id": getattr(r, "id", getattr(r, "document_id", i)),
                            "score": getattr(r, "score", getattr(r, "similarity", 0.0)),
                            "content": getattr(r, "content", getattr(r, "text", "")),
                            "metadata": getattr(r, "metadata", {}),
                        }
                        for i, r in enumerate(results)
                    ],
                    "result_count": len(results),
                    "timestamp": time.time(),
                }
            elif isinstance(results, dict):
                result_data = {"query": query_text, "top_k": top_k, **results}
            else:
                result_data = {"query": query_text, "raw": str(results)}

            with self._lock:
                self._pending_search_results.append(result_data)
                self._total_searches += 1

            self._emit(
                "vectordb.search.completed",
                {
                    "query": query_text,
                    "result_count": result_data.get("result_count", 0),
                },
            )

            return result_data
        except Exception:
            logger.debug("Semantic search failed", exc_info=True)
            return None

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_search_results(self) -> List[BlackboardEntry]:
        """Flush pending search results as blackboard entries."""
        if not self._pending_search_results:
            return []

        entries: List[BlackboardEntry] = []
        results_to_post = list(self._pending_search_results)
        self._pending_search_results.clear()

        for result_data in results_to_post:
            result_count = result_data.get("result_count", 0)
            top_score = 0.0
            results_list = result_data.get("results", [])
            if results_list and isinstance(results_list, list):
                scores = [r.get("score", 0.0) for r in results_list if isinstance(r, dict)]
                if scores:
                    top_score = max(scores)

            entries.append(
                BlackboardEntry(
                    topic="vectordb.search_results",
                    data=result_data,
                    source_module=self.MODULE_NAME,
                    confidence=min(1.0, top_score),
                    priority=EntryPriority.HIGH if result_count > 0 else EntryPriority.LOW,
                    ttl_seconds=self._search_results_ttl,
                    tags=frozenset({"vectordb", "search", "semantic", "results"}),
                    metadata={
                        "query": result_data.get("query", ""),
                        "result_count": result_count,
                        "top_score": top_score,
                    },
                )
            )

        return entries

    def _produce_index_stats(self) -> Optional[BlackboardEntry]:
        """Gather index statistics from the search engine / config."""
        stats: Dict[str, Any] = {}

        # Try getting stats from search engine
        if self._search_engine is not None:
            try:
                stats_fn = getattr(self._search_engine, "get_stats", None)
                if stats_fn is not None:
                    result = stats_fn()
                    if isinstance(result, dict):
                        stats.update(result)
            except Exception:
                pass

            # Try getting document count
            try:
                doc_count = getattr(self._search_engine, "document_count", None)
                if doc_count is not None:
                    stats["document_count"] = doc_count
            except Exception:
                pass

        # Try config for connection info
        if self._config is not None:
            try:
                valid_fn = getattr(self._config, "validate_config", None)
                if valid_fn is not None:
                    stats["config_valid"] = valid_fn()
            except Exception:
                pass

            # Enumerate active databases
            for db_name in ("pinecone", "weaviate", "qdrant"):
                try:
                    db_config = getattr(self._config, f"{db_name}_config", None)
                    if db_config is not None:
                        enabled = getattr(db_config, "enabled", True)
                        stats[f"{db_name}_enabled"] = enabled
                except Exception:
                    pass

        if not stats:
            return None

        # Change detection: only post if document count changed
        doc_count = stats.get("document_count")
        if doc_count is not None and doc_count == self._last_index_doc_count:
            return None
        if doc_count is not None:
            self._last_index_doc_count = doc_count

        stats["total_searches"] = self._total_searches
        stats["total_embeddings"] = self._total_embeddings_generated

        entry = BlackboardEntry(
            topic="vectordb.index_stats",
            data=stats,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._index_stats_ttl,
            tags=frozenset({"vectordb", "index", "statistics"}),
            metadata={"document_count": doc_count},
        )

        if doc_count is not None and self._last_index_doc_count is not None:
            self._emit(
                "vectordb.index.updated",
                {"document_count": doc_count, "entry_id": entry.entry_id},
            )

        return entry

    def _produce_embeddings(self) -> Optional[BlackboardEntry]:
        """Report embedding pipeline stats."""
        if self._embedding_pipeline is None:
            return None

        stats: Dict[str, Any] = {}
        try:
            stats["model_name"] = getattr(
                self._embedding_pipeline, "model_name",
                getattr(self._embedding_pipeline, "config", {})
            )
            if isinstance(stats["model_name"], dict):
                stats["model_name"] = stats["model_name"].get("model_name", "unknown")
        except Exception:
            stats["model_name"] = "unknown"

        try:
            dim = getattr(self._embedding_pipeline, "dimension", None)
            if dim is None:
                get_dim_fn = getattr(self._embedding_pipeline, "get_dimension", None)
                if get_dim_fn is not None:
                    dim = get_dim_fn()
            stats["dimension"] = dim
        except Exception:
            pass

        try:
            stats["is_available"] = getattr(self._embedding_pipeline, "is_available", lambda: True)()
        except Exception:
            stats["is_available"] = None

        stats["total_embeddings_generated"] = self._total_embeddings_generated

        # Change detection
        if stats == self._last_embedding_stats:
            return None
        self._last_embedding_stats = dict(stats)

        return BlackboardEntry(
            topic="vectordb.embeddings",
            data=stats,
            source_module=self.MODULE_NAME,
            confidence=0.8,
            priority=EntryPriority.LOW,
            ttl_seconds=self._embeddings_ttl,
            tags=frozenset({"vectordb", "embeddings", "pipeline"}),
        )

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_kg(self, entry: BlackboardEntry) -> None:
        """Index knowledge graph triples as searchable vectors."""
        if self._embedding_pipeline is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}

        # Build text from triple
        subject = data.get("subject", "")
        predicate = data.get("predicate", data.get("relation", ""))
        obj = data.get("object", data.get("target", ""))
        text = f"{subject} {predicate} {obj}".strip()

        if not text:
            return

        try:
            encode_fn = getattr(self._embedding_pipeline, "encode", None)
            if encode_fn is not None:
                encode_fn([text])
                with self._lock:
                    self._total_embeddings_generated += 1
        except Exception:
            logger.debug("Failed to embed KG triple", exc_info=True)

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Trigger semantic search for reasoning inferences."""
        data = entry.data if isinstance(entry.data, dict) else {}
        conclusion = data.get("conclusion", data.get("result", data.get("inference", "")))
        if conclusion and isinstance(conclusion, str) and len(conclusion) > 10:
            self.search(conclusion, top_k=5)

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_kg_event(self, event: CognitiveEvent) -> None:
        """Auto-index new KG triples on event notification."""
        if self._embedding_pipeline is None:
            return
        payload = event.payload or {}
        subject = payload.get("subject", "")
        predicate = payload.get("predicate", "")
        obj = payload.get("object", "")
        text = f"{subject} {predicate} {obj}".strip()
        if text:
            try:
                encode_fn = getattr(self._embedding_pipeline, "encode", None)
                if encode_fn is not None:
                    encode_fn([text])
                    with self._lock:
                        self._total_embeddings_generated += 1
            except Exception:
                pass

    def _handle_reasoning_event(self, event: CognitiveEvent) -> None:
        """Trigger similarity search for completed inferences."""
        payload = event.payload or {}
        conclusion = payload.get("conclusion", payload.get("result", ""))
        if conclusion and isinstance(conclusion, str) and len(conclusion) > 10:
            self.search(conclusion, top_k=5)

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all vectordb components."""
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_embedding_pipeline": self._embedding_pipeline is not None,
            "has_search_engine": self._search_engine is not None,
            "has_config": self._config is not None,
            "total_searches": self._total_searches,
            "total_embeddings_generated": self._total_embeddings_generated,
            "pending_search_results": len(self._pending_search_results),
            "last_index_doc_count": self._last_index_doc_count,
            "registered": self._blackboard is not None,
        }

        if self._embedding_pipeline is not None:
            try:
                snap["embedding_dimension"] = getattr(
                    self._embedding_pipeline, "dimension", None
                )
            except Exception:
                pass

        if self._config is not None:
            try:
                valid_fn = getattr(self._config, "validate_config", None)
                if valid_fn is not None:
                    snap["config_valid"] = valid_fn()
            except Exception:
                pass

        return snap
