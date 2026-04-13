# Knowledge Management Module

> **Path**: `src/asi_build/knowledge_management/`  
> **Files**: 14 | **LOC**: ~5,816  
> **Status**: Stable ✅  
> **Tests**: Covered via integration test suite

---

## Overview

The Knowledge Management module implements an **omniscience network** — a multi-subsystem pipeline for ingesting, organizing, validating, synthesizing, and continuously learning from structured and unstructured knowledge. Its central orchestrator, `KnowledgeEngine`, coordinates six specialized subsystems to answer complex, contextual queries with high confidence.

Unlike the lower-level `knowledge_graph` module (which focuses on bi-temporal graph storage and pathfinding), the Knowledge Management module operates at a higher semantic layer: it aggregates from multiple sources, validates quality, synthesizes predictions, and adapts its behavior based on query history.

---

## Architecture

```
KnowledgeEngine (orchestrator)
├── InformationAggregator        — multi-source data ingestion
├── KnowledgeGraphManager        — relationship analysis (NetworkX)
├── IntelligentSearch            — 4-strategy retrieval system
├── PredictiveSynthesizer        — insight generation + forecasting
├── QualityController            — multi-dimensional validation
└── ContextualLearner            — adaptive pattern recognition
```

All subsystems are initialized from a single config dict and communicate through `KnowledgeQuery` / `KnowledgeResult` dataclasses. The engine tracks aggregate performance metrics: `query_count`, `total_processing_time`, `average_confidence`.

---

## Subsystems

### KnowledgeEngine (`core/knowledge_engine.py`)

Central orchestrator for the omniscience network. Accepts `KnowledgeQuery` objects and fans out to subsystems with configurable parallelism (`max_concurrent_queries: 10`).

**Key dataclasses:**

```python
@dataclass
class KnowledgeQuery:
    query: str
    context: Dict[str, Any]
    priority: int = 1
    timestamp: float = None   # auto-set
    session_id: str = None

@dataclass
class KnowledgeResult:
    query: KnowledgeQuery
    result: Dict[str, Any]
    confidence: float
    sources: List[str]
    processing_time: float
    metadata: Dict[str, Any]
```

**Default config:**

```python
{
    "max_concurrent_queries": 10,
    "default_timeout": 30.0,
    "quality_threshold": 0.7,
    "learning_enabled": True,
    "caching_enabled": True,
    "parallel_processing": True,
    "aggregator": {"max_sources": 50, "timeout_per_source": 5.0},
    "graph": {"max_depth": 5, "relationship_threshold": 0.6},
    "search": {"semantic_search": True, "fuzzy_matching": True, "context_expansion": True},
    "synthesis": {"prediction_horizon": "24h", "confidence_threshold": 0.8},
    "validation": {"fact_checking": True, "source_verification": True},
    "learning": {"adaptive_learning": True, "pattern_recognition": True},
}
```

---

### IntelligentSearch (`search/intelligent_search.py`)

Four-strategy retrieval engine with in-memory keyword indices, a semantic similarity cache, and full search history logging.

**Search types:**

| Type | Description |
|------|-------------|
| `keyword` | Inverted index over ingested documents, TF-IDF-style ranking |
| `semantic` | Embedding similarity via cached vectors |
| `fuzzy` | `difflib.SequenceMatcher` for approximate string matching |
| `comprehensive` | All three strategies combined, results merged by relevance |

**Key dataclasses:**

```python
@dataclass
class SearchQuery:
    query: str
    search_type: str = "comprehensive"
    filters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 50
    confidence_threshold: float = 0.3

@dataclass
class SearchResult:
    content: str
    source: str
    relevance_score: float
    confidence: float
    metadata: Dict[str, Any]
    highlighted_text: str = ""

@dataclass
class SearchResponse:
    query: SearchQuery
    results: List[SearchResult]
    total_results: int
    search_time: float
    search_strategies_used: List[str]
    metadata: Dict[str, Any]
```

Performance tracking: `total_searches`, `total_search_time`, automatic cache eviction.

---

### KnowledgeGraphManager (`core/knowledge_graph_manager.py`)

Relationship analysis layer backed by **NetworkX** for in-process graph queries. Integrates with the external bi-temporal graph via the `knowledge_graph` module.

**Key dataclasses:**

```python
@dataclass
class KnowledgeNode:
    id: str
    label: str
    node_type: str
    properties: Dict[str, Any]
    confidence: float = 1.0
    timestamp: float = None

@dataclass
class KnowledgeRelationship:
    source_id: str
    target_id: str
    relationship_type: str
    properties: Dict[str, Any]
    strength: float = 1.0
    confidence: float = 1.0

@dataclass
class GraphAnalysisResult:
    query: str
    nodes_analyzed: int
    relationships_found: int
    key_concepts: List[str]
    relationship_patterns: Dict[str, int]
    confidence_distribution: Dict[str, float]
    insights: List[str]
    metadata: Dict[str, Any]
```

Config: `max_depth: 5`, `relationship_threshold: 0.6`. Supports BFS/DFS traversal, key-concept extraction, and insight generation.

---

### PredictiveSynthesizer (`synthesis/predictive_synthesizer.py`)

Synthesizes information from multiple subsystems and generates forward-looking predictions.

**Synthesis types:**

| Mode | Output |
|------|--------|
| `predictive` | Probability-weighted future scenarios |
| `analytical` | Trend and pattern breakdowns |
| `comparative` | Source-vs-source contrast analysis |
| `comprehensive` | All of the above |

**Prediction dataclass:**

```python
@dataclass
class Prediction:
    description: str
    probability: float
    confidence: float
    time_frame: str           # '1h', '24h', '7d', '30d'
    supporting_evidence: List[str]
    risk_factors: List[str]
    metadata: Dict[str, Any]
```

**KnowledgeSynthesis output:**

```python
@dataclass
class KnowledgeSynthesis:
    query: str
    summary: str
    key_findings: List[str]
    predictions: List[Dict[str, Any]]
    insights: List[str]
    confidence_score: float
    sources_analyzed: List[str]
    synthesis_metadata: Dict[str, Any]
    recommendations: List[str]
```

---

### QualityController (`validation/quality_controller.py`)

Multi-dimensional validation layer. Every piece of ingested knowledge passes through configurable `ValidationRule` checks before it enters the system.

**Validation dimensions:**

| Dimension | Description |
|-----------|-------------|
| `consistency` | Cross-source agreement checking |
| `accuracy` | Fact verification against known anchors |
| `completeness` | Required field and coverage checks |
| `reliability` | Source reputation scoring |

**ValidationResult:**

```python
@dataclass
class ValidationResult:
    overall_score: float
    passed_checks: int
    total_checks: int
    validation_issues: List[str]
    quality_metrics: Dict[str, float]
    recommendations: List[str]
    confidence_adjustments: Dict[str, float]
    metadata: Dict[str, Any]
```

Config: `quality_threshold: 0.7`, `fact_checking: True`, `source_verification: True`.

---

### ContextualLearner (`learning/contextual_learner.py`)

Adaptive learning system that improves retrieval and synthesis over time by observing query patterns, result quality, and user feedback.

**Learning data structures:**

```python
@dataclass
class LearningPattern:
    pattern_id: str
    pattern_type: str     # 'query', 'result', 'performance', 'error'
    pattern_data: Dict[str, Any]
    frequency: int = 1
    confidence: float = 0.5
    last_seen: float = None
    created_at: float = None

@dataclass
class LearningEvent:
    event_id: str
    event_type: str
    query: str
    result_quality: float
    processing_time: float
    user_feedback: Optional[Dict[str, Any]]
    system_metrics: Dict[str, Any]

@dataclass
class AdaptationRule:
    rule_id: str
    rule_type: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    effectiveness: float = 0.5
    usage_count: int = 0
    enabled: bool = True
```

Learns from: query patterns, result quality scores, system performance metrics, user feedback, and error recovery strategies. Adaptation rules are evaluated per-query and updated based on effectiveness.

---

### InformationAggregator (`core/information_aggregator.py`)

Pulls from up to 50 sources in parallel (configurable timeout per source: 5s). Normalizes heterogeneous inputs into a unified representation before passing to the graph manager and search engine.

---

## Data Flow

```
External query
      │
      ▼
KnowledgeQuery (with context, priority, session_id)
      │
      ▼
KnowledgeEngine.process()
      ├─→ InformationAggregator  (fetch from sources)
      ├─→ KnowledgeGraphManager  (relationship analysis)
      ├─→ IntelligentSearch      (retrieve relevant chunks)
      ├─→ PredictiveSynthesizer  (generate synthesis + predictions)
      ├─→ QualityController      (validate output quality)
      └─→ ContextualLearner      (update patterns, fire adaptation rules)
            │
            ▼
      KnowledgeResult (confidence, sources, metadata)
```

---

## API

### REST API (`api/knowledge_api.py`)

```python
# Query the omniscience network
POST /api/knowledge/query
{
    "query": "What are the implications of IIT Φ for consciousness theories?",
    "context": {"domain": "consciousness", "session_id": "abc123"},
    "priority": 1
}

# Direct search
POST /api/knowledge/search
{
    "query": "IIT phi computation",
    "search_type": "comprehensive",
    "max_results": 20
}

# Synthesize knowledge on a topic
POST /api/knowledge/synthesize
{
    "query": "Homomorphic encryption trends",
    "synthesis_type": "predictive",
    "time_horizon": "7d"
}
```

---

## Integration with Other Modules

| Module | Integration |
|--------|-------------|
| `knowledge_graph` | `KnowledgeGraphManager` wraps the bi-temporal KG for graph queries |
| `reasoning` | `KnowledgeEngine` results feed the `HybridReasoningEngine` context window |
| `consciousness` | GWT workspace broadcasts surface via `IntelligentSearch` as a knowledge source |
| `safety` | `QualityController` rules can include safety-relevant consistency checks |
| `cognitive_blackboard` | Not yet wired — see Issue #82 |

### Blackboard Integration (Planned — Issue #82)

The `KnowledgeEngine` is a natural Blackboard writer: every `KnowledgeResult` is a structured artifact with confidence scores and source provenance. A `KnowledgeBlackboardAdapter` would:

1. Subscribe to `QUERY_REQUESTED` events from the Blackboard
2. Fan out to `KnowledgeEngine.process()`
3. Write `KnowledgeResult` back as a `BlackboardEntry` with appropriate TTL and confidence

---

## Open Questions

1. **Source discovery**: How should `InformationAggregator` discover new sources dynamically? Should it use the `rings_network` for P2P knowledge federation?
2. **Cache invalidation**: The `IntelligentSearch` semantic cache has no explicit eviction policy — what TTL strategy fits best for long-running deployments?
3. **Learning feedback loop**: `ContextualLearner` adaptation rules currently update in-memory only — should they persist to SQLite (like `agi_reproducibility`'s `ExperimentTracker`)?
4. **Quality threshold calibration**: Is 0.7 the right default `quality_threshold`? Should it vary by domain (e.g., lower for exploratory synthesis, higher for safety-critical facts)?
5. **Prediction evaluation**: `PredictiveSynthesizer` generates forecasts with probability and confidence scores — how do we evaluate prediction accuracy over time?

---

## Related Issues & Discussions

- **Issue #82**: Wire KnowledgeEngine to Cognitive Blackboard (KnowledgeBlackboardAdapter) *(planned)*
- **Issue #15**: Update docs/modules/ for all 29 modules *(includes this module)*
- **Discussion #33**: Q&A on bi-temporal knowledge graph — closely related architecture
- **Discussion #35**: Full-system orchestration — KnowledgeEngine plays a key role

---

*Last updated: 2026-04-12 — ASI:BUILD v0.1.0-alpha*
