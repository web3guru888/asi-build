# Phase 26.5 — KnowledgeOrchestrator: Unified Knowledge Management Pipeline

> **Issue**: [#582](https://github.com/web3guru888/asi-build/issues/582) | **S&T**: [#591](https://github.com/web3guru888/asi-build/discussions/591) | **Q&A**: [#592](https://github.com/web3guru888/asi-build/discussions/592) | **Planning**: [#577](https://github.com/web3guru888/asi-build/discussions/577)

## Overview

`KnowledgeOrchestrator` provides a unified knowledge management pipeline that composes ConceptGraph (26.1), OntologyManager (26.2), KnowledgeCompiler (26.3), and CommonSenseEngine (26.4) into a coherent knowledge lifecycle — acquisition, integration, retrieval, and maintenance.

## Architecture

### Four-Phase Knowledge Lifecycle

```
External Sources (Perception, Communication, Reasoning, Experience, Social)
    │
    ▼
┌─── ACQUIRE ───┐
│ Classify &     │
│ Normalize      │
└───────┬────────┘
        │
┌───────▼────────┐
│  INTEGRATE     │
│ Cross-ref &    │
│ Consistency    │
└───────┬────────┘
        │
┌───────▼────────┐
│  RETRIEVE      │
│ Query dispatch │
│ & caching      │
└───────┬────────┘
        │
┌───────▼────────┐
│  MAINTAIN      │
│ Prune, decay,  │
│ recompile      │
└────────────────┘
```

## Data Structures

### KnowledgeSource Enum

| Source | Origin | Target Subsystems |
|--------|--------|-------------------|
| `PERCEPTION` | EmbodiedOrchestrator (25.5) | ConceptGraph + CommonSense |
| `COMMUNICATION` | CommunicationOrchestrator (19.5) | OntologyManager + CommonSense |
| `REASONING` | ReasoningOrchestrator (20.5) | OntologyManager + Compiler |
| `EXPERIENCE` | MemoryConsolidator (18.2) | CommonSense + ConceptGraph |
| `SOCIAL` | SocialOrchestrator (24.5) | CommonSense |
| `BOOTSTRAP` | Initial load | All subsystems |

### KnowledgeContext Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `concept_graph` | `ConceptGraph` | 26.1 component |
| `ontology` | `OntologyManager` | 26.2 component |
| `compiled_rules` | `KnowledgeCompiler` | 26.3 component |
| `common_sense` | `CommonSenseEngine` | 26.4 component |
| `query_cache` | `Dict[str, Any]` | LRU cache |
| `active_concepts` | `FrozenSet[str]` | Currently activated |
| `last_maintenance` | `Optional[float]` | Last maintenance timestamp |

### KnowledgeQuery / KnowledgeResult

Query types: `"concept"`, `"ontology"`, `"rule"`, `"common_sense"`, `"unified"`.

Unified queries fan out to all four subsystems in parallel via `asyncio.gather`, with results merged by confidence-weighted ranking.

### MaintenanceReport Frozen Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `concepts_pruned` | `int` | Low-activation concepts removed |
| `axioms_validated` | `int` | Consistency-checked axioms |
| `rules_recompiled` | `int` | Rules optimized |
| `assertions_decayed` | `int` | Confidence-decayed assertions |
| `inconsistencies_found` | `int` | Detected inconsistencies |
| `duration_ms` | `float` | Cycle duration |

## Protocol

```python
@runtime_checkable
class KnowledgeOrchestrator(Protocol):
    async def acquire(self, source: KnowledgeSource, data: Dict[str, Any]) -> int: ...
    async def integrate(self) -> int: ...
    async def retrieve(self, query: KnowledgeQuery) -> KnowledgeResult: ...
    async def maintain(self) -> MaintenanceReport: ...
    async def explain_knowledge(self, concept_id: str) -> Dict[str, Any]: ...
    async def get_context(self) -> KnowledgeContext: ...
    async def activate_concepts(self, concept_ids: Set[str]) -> FrozenSet[str]: ...
    async def get_stats(self) -> Dict[str, int]: ...
```

## Implementation: AsyncKnowledgeOrchestrator

### Component Injection

```python
class AsyncKnowledgeOrchestrator:
    def __init__(self, concept_graph, ontology_manager,
                 knowledge_compiler, common_sense_engine, *,
                 cache_ttl=60.0, maintenance_interval=300.0,
                 max_cache_size=1000): ...
```

### Concurrency Model

Per-subsystem `asyncio.Lock` instances prevent deadlocks while allowing maximum concurrency. Integration uses a separate lock to serialize cross-subsystem operations.

### Retrieval Priority

When subsystems disagree, resolution follows the hierarchy:
1. DL proof (OntologyManager) — sound and complete
2. Compiled rule (KnowledgeCompiler) — verified against ontology
3. Concept graph (ConceptGraph) — structural but informal
4. Common sense (CommonSenseEngine) — plausible but uncertain

### Background Maintenance

5-minute cycle:
1. Prune low-activation concepts (ConceptGraph)
2. Validate consistency (OntologyManager)
3. Recompile + merge + decay (KnowledgeCompiler)
4. Decay assertion confidence (CommonSenseEngine)
5. Cross-subsystem reconciliation (every 3rd cycle)

### Cross-Orchestrator Integration

```
SocialOrchestrator (24.5) ──SOCIAL──►
EmbodiedOrchestrator (25.5) ──PERCEPTION──► KnowledgeOrchestrator
DecisionOrchestrator (23.5) ◄──RETRIEVE──     (26.5)
CommunicationOrchestrator (19.5) ──COMMUNICATION──►
MemoryConsolidator (18.2) ──EXPERIENCE──►
```

## Metrics (Prometheus)

| Metric | Type | Description |
|--------|------|-------------|
| `knowledge_acquisitions_total` | Counter | Items acquired by source |
| `knowledge_integrations_total` | Counter | Integration cycles |
| `knowledge_retrieval_seconds` | Histogram | Query latency |
| `knowledge_cache_hit_ratio` | Gauge | Cache hit rate |
| `knowledge_maintenance_seconds` | Histogram | Maintenance duration |

## Test Targets (12)

1–12: See issue #582 for full list.

## References

- Gruber, T.R. (1993). *A translation approach to portable ontology specifications*
- Davis, E. & Marcus, G. (2015). *Commonsense reasoning and commonsense knowledge in AI*
- Van Harmelen, F. et al. (2008). *Handbook of Knowledge Representation*
- Brachman, R.J. & Levesque, H.J. (2004). *Knowledge Representation and Reasoning*

---

## Phase 26 Sub-phase Tracker

| # | Component | Issue | Status |
|---|-----------|-------|--------|
| 26.1 | ConceptGraph | #578 | ✅ Spec'd |
| 26.2 | OntologyManager | #579 | ✅ Spec'd |
| 26.3 | KnowledgeCompiler | #580 | ✅ Spec'd |
| 26.4 | CommonSenseEngine | #581 | ✅ Spec'd |
| 26.5 | KnowledgeOrchestrator | #582 | ✅ Spec'd |
