"""
Integrations Bridge ↔ Blackboard Adapter
============================================

Bridges the integrations sub-modules (LangChain-Memgraph, SQL-to-Graph
migration agent, MCP-Memgraph server) with the Cognitive Blackboard.

This adapter acts as a bridge that connects external graph database tooling
and migration agents with the internal blackboard, enabling bidirectional
flow between graph modeling/query operations and the cognitive system.

Topics produced
~~~~~~~~~~~~~~~
- ``integrations.migration_status``  — SQL-to-graph migration progress and status
- ``integrations.query_result``      — Cypher query execution results
- ``integrations.graph_model``       — Graph model definitions from HyGM modeling

Topics consumed
~~~~~~~~~~~~~~~
- ``knowledge_graph``                — KG updates → trigger graph model sync
- ``graph_intelligence``             — Community detection → enrich graph models
- ``reasoning``                      — Reasoning inferences → generate Cypher queries

Events emitted
~~~~~~~~~~~~~~
- ``integrations.migration.completed``  — A migration task has finished
- ``integrations.query.executed``       — A Cypher query was executed

Events listened
~~~~~~~~~~~~~~~
- ``knowledge_graph.triple.added``      — Sync new triples to Memgraph
- ``graph_intelligence.community.detected`` — Update graph model with communities
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

_integrations_module = None


def _get_integrations():
    """Lazy import of integrations module to allow graceful degradation.

    The integrations module has heavy external dependencies (langchain,
    memgraph-toolbox, mysql-connector, langgraph) so graceful degradation
    is essential.
    """
    global _integrations_module
    if _integrations_module is None:
        try:
            from asi_build import integrations as _im

            _integrations_module = _im
        except (ImportError, ModuleNotFoundError):
            _integrations_module = False
    return _integrations_module if _integrations_module is not False else None


class IntegrationsBlackboardBridge:
    """Bridge adapter connecting integrations sub-modules to the Cognitive Blackboard.

    Wraps up to four components:

    - ``HyGM`` — Hybrid Graph Modeling engine (LLM-powered graph modeling)
    - ``MigrationAgent`` — SQL-to-graph migration orchestration
    - ``CypherGenerator`` — Cypher query generation from natural language
    - ``MemgraphToolkit`` — LangChain toolkit for Memgraph graph operations

    If a component is ``None`` (or its dependencies are unavailable), the
    bridge gracefully skips operations involving that component.

    Parameters
    ----------
    hygm : optional
        A ``HyGM`` graph modeling instance.
    migration_agent : optional
        A ``MigrationAgent`` instance (SQL-to-graph migration).
    cypher_generator : optional
        A ``CypherGenerator`` instance (Cypher query generation).
    toolkit : optional
        A ``MemgraphToolkit`` instance (LangChain graph tools).
    migration_status_ttl : float
        TTL in seconds for migration status entries (default 300).
    query_result_ttl : float
        TTL for query result entries (default 120).
    graph_model_ttl : float
        TTL for graph model entries (default 600).
    """

    MODULE_NAME = "integrations"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        hygm: Any = None,
        migration_agent: Any = None,
        cypher_generator: Any = None,
        toolkit: Any = None,
        *,
        migration_status_ttl: float = 300.0,
        query_result_ttl: float = 120.0,
        graph_model_ttl: float = 600.0,
    ) -> None:
        self._hygm = hygm
        self._migration_agent = migration_agent
        self._cypher_generator = cypher_generator
        self._toolkit = toolkit
        self._migration_status_ttl = migration_status_ttl
        self._query_result_ttl = query_result_ttl
        self._graph_model_ttl = graph_model_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change detection and state
        self._last_migration_status: Optional[str] = None
        self._last_model_hash: Optional[str] = None
        self._pending_query_results: List[Dict[str, Any]] = []
        self._total_queries_executed: int = 0
        self._total_migrations: int = 0

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
                "Integrations bridge: SQL-to-graph migration, Cypher query "
                "generation, HyGM graph modeling, and LangChain-Memgraph tools."
            ),
            topics_produced=frozenset(
                {
                    "integrations.migration_status",
                    "integrations.query_result",
                    "integrations.graph_model",
                }
            ),
            topics_consumed=frozenset(
                {
                    "knowledge_graph",
                    "graph_intelligence",
                    "reasoning",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "IntegrationsBlackboardBridge registered with blackboard "
            "(hygm=%s, migration_agent=%s, cypher_generator=%s, toolkit=%s)",
            self._hygm is not None,
            self._migration_agent is not None,
            self._cypher_generator is not None,
            self._toolkit is not None,
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
            elif event.event_type.startswith("graph_intelligence."):
                self._handle_graph_intelligence_event(event)
        except Exception:
            logger.debug(
                "IntegrationsBlackboardBridge: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── Public API: execute queries ───────────────────────────────────

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Execute a Cypher query and queue the result for the next production sweep.

        Parameters
        ----------
        query : str
            Cypher query string.
        params : optional
            Query parameters.

        Returns
        -------
        dict or None
            Query result, or None on failure.
        """
        if self._toolkit is None:
            return None

        try:
            # Try executing through toolkit
            run_fn = getattr(self._toolkit, "run_query", None)
            if run_fn is None:
                run_fn = getattr(self._toolkit, "execute", None)
            if run_fn is None:
                return None

            result = run_fn(query) if params is None else run_fn(query, params)

            result_data = {
                "query": query,
                "params": params,
                "result": result if isinstance(result, (dict, list, str)) else str(result),
                "timestamp": time.time(),
                "success": True,
            }

            with self._lock:
                self._pending_query_results.append(result_data)
                self._total_queries_executed += 1

            self._emit(
                "integrations.query.executed",
                {
                    "query": query[:100],
                    "success": True,
                },
            )

            return result_data

        except Exception as exc:
            logger.debug("Cypher query execution failed: %s", exc, exc_info=True)
            error_data = {
                "query": query,
                "params": params,
                "error": str(exc),
                "timestamp": time.time(),
                "success": False,
            }
            with self._lock:
                self._pending_query_results.append(error_data)
            return error_data

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current integrations state."""
        entries: List[BlackboardEntry] = []

        with self._lock:
            migration_entry = self._produce_migration_status()
            if migration_entry is not None:
                entries.append(migration_entry)

            query_entries = self._produce_query_results()
            entries.extend(query_entries)

            model_entry = self._produce_graph_model()
            if model_entry is not None:
                entries.append(model_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        KG updates → trigger graph model sync.
        Graph intelligence → enrich graph models.
        Reasoning inferences → generate Cypher queries.
        """
        for entry in entries:
            try:
                if entry.topic.startswith("knowledge_graph."):
                    self._consume_kg(entry)
                elif entry.topic.startswith("graph_intelligence."):
                    self._consume_graph_intelligence(entry)
                elif entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
            except Exception:
                logger.debug(
                    "IntegrationsBlackboardBridge: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_migration_status(self) -> Optional[BlackboardEntry]:
        """Check migration agent status and return entry if changed."""
        if self._migration_agent is None:
            return None

        try:
            status = getattr(self._migration_agent, "status",
                           getattr(self._migration_agent, "get_status", None))
            if callable(status):
                status = status()
        except Exception:
            return None

        if status is None:
            return None

        if isinstance(status, dict):
            status_data = status
        elif isinstance(status, str):
            status_data = {"status": status}
        else:
            status_data = {"raw": str(status)}

        status_name = str(status_data.get("status", status_data.get("state", "")))

        # Change detection
        if status_name == self._last_migration_status:
            return None
        self._last_migration_status = status_name

        is_completed = status_name.lower() in ("completed", "finished", "done", "success")
        priority = EntryPriority.HIGH if is_completed else EntryPriority.NORMAL

        # Enrich with progress info
        try:
            progress = getattr(self._migration_agent, "progress", None)
            if progress is not None:
                if isinstance(progress, dict):
                    status_data.update(progress)
                elif isinstance(progress, (int, float)):
                    status_data["progress_pct"] = progress
        except Exception:
            pass

        entry = BlackboardEntry(
            topic="integrations.migration_status",
            data=status_data,
            source_module=self.MODULE_NAME,
            confidence=0.9,
            priority=priority,
            ttl_seconds=self._migration_status_ttl,
            tags=frozenset({"integrations", "migration", "sql_to_graph", status_name.lower()}),
            metadata={"status": status_name},
        )

        if is_completed:
            with self._lock:
                self._total_migrations += 1
            self._emit(
                "integrations.migration.completed",
                {
                    "status": status_name,
                    "total_migrations": self._total_migrations,
                    "entry_id": entry.entry_id,
                },
            )

        return entry

    def _produce_query_results(self) -> List[BlackboardEntry]:
        """Flush pending query results as blackboard entries."""
        if not self._pending_query_results:
            return []

        entries: List[BlackboardEntry] = []
        results_to_post = list(self._pending_query_results)
        self._pending_query_results.clear()

        for result_data in results_to_post:
            success = result_data.get("success", False)
            entries.append(
                BlackboardEntry(
                    topic="integrations.query_result",
                    data=result_data,
                    source_module=self.MODULE_NAME,
                    confidence=0.9 if success else 0.3,
                    priority=EntryPriority.NORMAL if success else EntryPriority.HIGH,
                    ttl_seconds=self._query_result_ttl,
                    tags=frozenset({
                        "integrations", "cypher", "query",
                        "success" if success else "error",
                    }),
                    metadata={
                        "success": success,
                        "query_preview": result_data.get("query", "")[:50],
                    },
                )
            )

        return entries

    def _produce_graph_model(self) -> Optional[BlackboardEntry]:
        """Produce current graph model from HyGM."""
        if self._hygm is None:
            return None

        try:
            # Try to get current graph model
            model = getattr(self._hygm, "current_model",
                          getattr(self._hygm, "graph_model", None))
            if model is None:
                get_model_fn = getattr(self._hygm, "get_model", None)
                if get_model_fn is not None:
                    model = get_model_fn()
        except Exception:
            return None

        if model is None:
            return None

        # Normalize model to dict
        if hasattr(model, "dict"):
            model_data = model.dict()
        elif hasattr(model, "to_dict"):
            model_data = model.to_dict()
        elif hasattr(model, "__dict__"):
            try:
                from dataclasses import asdict
                model_data = asdict(model)
            except (TypeError, Exception):
                model_data = {
                    k: v for k, v in vars(model).items()
                    if not k.startswith("_")
                }
        elif isinstance(model, dict):
            model_data = model
        else:
            model_data = {"raw": str(model)}

        # Change detection: hash the model
        import hashlib
        model_hash = hashlib.md5(
            str(sorted(str(model_data).encode())).encode()
        ).hexdigest()[:16]

        if model_hash == self._last_model_hash:
            return None
        self._last_model_hash = model_hash

        # Enrich with node/relationship counts
        nodes = model_data.get("nodes", model_data.get("node_labels", []))
        rels = model_data.get("relationships", model_data.get("relationship_types", []))
        node_count = len(nodes) if isinstance(nodes, (list, dict)) else 0
        rel_count = len(rels) if isinstance(rels, (list, dict)) else 0

        return BlackboardEntry(
            topic="integrations.graph_model",
            data=model_data,
            source_module=self.MODULE_NAME,
            confidence=0.85,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._graph_model_ttl,
            tags=frozenset({"integrations", "graph_model", "hygm", "schema"}),
            metadata={
                "model_hash": model_hash,
                "node_count": node_count,
                "relationship_count": rel_count,
            },
        )

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_kg(self, entry: BlackboardEntry) -> None:
        """Sync KG updates to graph database via toolkit."""
        if self._toolkit is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}

        subject = data.get("subject", "")
        predicate = data.get("predicate", data.get("relation", ""))
        obj = data.get("object", data.get("target", ""))

        if not (subject and predicate and obj):
            return

        # Generate MERGE query for the triple
        cypher = (
            f"MERGE (s:Entity {{name: $subject}}) "
            f"MERGE (o:Entity {{name: $object}}) "
            f"MERGE (s)-[:`{predicate}`]->(o)"
        )
        self.execute_query(cypher, {
            "subject": str(subject),
            "object": str(obj),
        })

    def _consume_graph_intelligence(self, entry: BlackboardEntry) -> None:
        """Enrich graph model with community detection results."""
        if self._hygm is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        communities = data.get("communities", data.get("community_count", None))
        if communities is not None:
            # Store as metadata on the HyGM model for future modeling decisions
            try:
                if not hasattr(self._hygm, "_blackboard_metadata"):
                    self._hygm._blackboard_metadata = {}
                self._hygm._blackboard_metadata["community_info"] = {
                    "entry_id": entry.entry_id,
                    "communities": communities,
                    "timestamp": time.time(),
                }
            except (AttributeError, Exception):
                pass

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Use reasoning inferences to generate and execute Cypher queries."""
        if self._cypher_generator is None:
            return
        data = entry.data if isinstance(entry.data, dict) else {}
        conclusion = data.get("conclusion", data.get("result", data.get("inference", "")))

        if not conclusion or not isinstance(conclusion, str):
            return

        # Try to generate a Cypher query from the inference
        try:
            generate_fn = getattr(self._cypher_generator, "generate",
                                getattr(self._cypher_generator, "generate_cypher", None))
            if generate_fn is not None:
                cypher = generate_fn(conclusion)
                if cypher and isinstance(cypher, str):
                    self.execute_query(cypher)
        except Exception:
            logger.debug(
                "Failed to generate Cypher from reasoning inference",
                exc_info=True,
            )

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_kg_event(self, event: CognitiveEvent) -> None:
        """Sync new KG triples to Memgraph on event notification."""
        if self._toolkit is None:
            return
        payload = event.payload or {}
        subject = payload.get("subject", "")
        predicate = payload.get("predicate", "")
        obj = payload.get("object", "")

        if subject and predicate and obj:
            cypher = (
                f"MERGE (s:Entity {{name: $subject}}) "
                f"MERGE (o:Entity {{name: $object}}) "
                f"MERGE (s)-[:`{predicate}`]->(o)"
            )
            self.execute_query(cypher, {
                "subject": str(subject),
                "object": str(obj),
            })

    def _handle_graph_intelligence_event(self, event: CognitiveEvent) -> None:
        """Update graph model when community detection fires."""
        if self._hygm is None:
            return
        payload = event.payload or {}
        try:
            if not hasattr(self._hygm, "_blackboard_metadata"):
                self._hygm._blackboard_metadata = {}
            self._hygm._blackboard_metadata["latest_event"] = {
                "event_type": event.event_type,
                "payload": payload,
                "timestamp": time.time(),
            }
        except (AttributeError, Exception):
            pass

    # ── Convenience: pull snapshot on demand ──────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all integrations components."""
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_hygm": self._hygm is not None,
            "has_migration_agent": self._migration_agent is not None,
            "has_cypher_generator": self._cypher_generator is not None,
            "has_toolkit": self._toolkit is not None,
            "last_migration_status": self._last_migration_status,
            "last_model_hash": self._last_model_hash,
            "pending_query_results": len(self._pending_query_results),
            "total_queries_executed": self._total_queries_executed,
            "total_migrations": self._total_migrations,
            "registered": self._blackboard is not None,
        }

        if self._migration_agent is not None:
            try:
                status = getattr(self._migration_agent, "status", None)
                if callable(status):
                    status = status()
                snap["current_migration_status"] = status
            except Exception:
                snap["current_migration_status"] = None

        if self._hygm is not None:
            try:
                model = getattr(self._hygm, "current_model",
                              getattr(self._hygm, "graph_model", None))
                snap["has_graph_model"] = model is not None
            except Exception:
                snap["has_graph_model"] = None

        if self._toolkit is not None:
            try:
                tools = getattr(self._toolkit, "get_tools", None)
                if tools is not None and callable(tools):
                    snap["available_tools"] = len(tools())
            except Exception:
                pass

        return snap
