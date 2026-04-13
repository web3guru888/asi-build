# VectorDB Module

**Path**: `src/asi_build/vectordb/`  
**Lines of Code**: 8,142  
**Files**: 21 (Python source)  
**Status**: Stable  

---

## Overview

The VectorDB module provides a **unified interface to multiple vector database backends** — Pinecone, Weaviate, and Qdrant — through a single API with automatic load balancing, failover, and intelligent query routing. It is the long-term memory substrate for ASI:BUILD: storing, indexing, and retrieving high-dimensional embeddings that represent knowledge, observations, and cognitive state.

Within the broader architecture, VectorDB sits between the **Knowledge Graph** (structured relational memory) and raw module outputs — it handles the _unstructured_ end of the memory spectrum, enabling similarity search over millions of vectors in milliseconds.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Retrieval API                       │
│  RetrievalEngine  ·  FacetedSearch  ·  QueryOptimizer   │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                    Indexing API                          │
│  BatchIndexer  ·  RealTimeIndexer  ·  DocumentChunker   │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                Unified Client (UnifiedVectorDB)          │
│  Load Balancer · Failover · Intelligent Routing          │
└──────┬─────────────────┬──────────────────┬──────────────┘
       │                 │                  │
┌──────▼──────┐  ┌───────▼──────┐  ┌───────▼───────┐
│  Pinecone   │  │   Weaviate   │  │    Qdrant      │
│  Client     │  │   Client     │  │    Client      │
└─────────────┘  └──────────────┘  └───────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                  Embedding Pipeline                      │
│  SentenceTransformers · OpenAI · Cohere · HuggingFace   │
└──────────────────────────────────────────────────────────┘
```

### File Map

| File | Purpose | LOC (approx) |
|------|---------|-------------|
| `core/search.py` | Semantic search engine, query expansion, re-ranking | ~600 |
| `core/embeddings.py` | Embedding pipeline (4 backends, batching, caching) | ~700 |
| `core/config.py` | Configuration dataclasses (VectorDBConfig, EmbeddingConfig, etc.) | ~300 |
| `core/utils.py` | Vector ops, text processing, performance monitoring | ~400 |
| `api/unified_client.py` | Multi-DB client with routing & failover | ~800 |
| `api/indexing.py` | Batch + real-time indexing, chunking, metadata extraction | ~700 |
| `api/retrieval.py` | Multi-modal retrieval, faceted search, analytics | ~600 |
| `databases/pinecone_client.py` | Pinecone integration (upsert, query, namespace mgmt) | ~700 |
| `databases/weaviate_client.py` | Weaviate integration (schema, BM25, hybrid search) | ~700 |
| `databases/qdrant_client.py` | Qdrant integration (payload filtering, clustering, scroll) | ~700 |
| `examples/` | Basic usage, advanced search, batch processing demos | ~700 |
| `tests/` | Unit + integration tests | ~500 |

---

## Core Concepts

### 1. UnifiedVectorDB — Multi-Database Client

`UnifiedVectorDB` is the central abstraction. It holds a live connection to all three backends and routes writes/reads intelligently:

```python
from asi_build.vectordb.api.unified_client import UnifiedVectorDB
from asi_build.vectordb.core.config import VectorDBConfig

config = VectorDBConfig(
    pinecone_api_key="...",
    weaviate_url="http://localhost:8080",
    qdrant_url="http://localhost:6333",
)
db = UnifiedVectorDB(config)

# Unified insert — written to all backends in parallel
result = db.insert(
    vectors=embeddings,        # np.ndarray (N, D)
    metadata=records,          # List[Dict]
    database_weights={"pinecone": 1.0, "weaviate": 0.8, "qdrant": 1.0},
)

# Unified search — merges results from all backends
results = db.search(query="consciousness integration theory", top_k=10)
```

**Failover**: if any backend is unhealthy, the client routes around it without raising an exception. Health checks run on a background thread.

**Routing logic**: write-heavy workloads are distributed by `database_weights`; read queries use latency-aware selection.

---

### 2. Embedding Pipeline

`EmbeddingPipeline` abstracts four embedding backends behind one interface:

| Backend | Model examples | When to use |
|---------|---------------|-------------|
| **SentenceTransformers** | `all-MiniLM-L6-v2`, `all-mpnet-base-v2` | Default; fast, local, good quality |
| **OpenAI** | `text-embedding-ada-002`, `text-embedding-3-large` | High-quality; requires API key |
| **Cohere** | `embed-english-v3.0` | Strong multilingual |
| **HuggingFace** | Any `AutoModel` | Maximum flexibility |

```python
from asi_build.vectordb.core.embeddings import EmbeddingPipeline
from asi_build.vectordb.core.config import EmbeddingConfig

pipeline = EmbeddingPipeline(EmbeddingConfig(
    model_name="all-MiniLM-L6-v2",
    backend="sentence_transformers",
    batch_size=64,
    cache_embeddings=True,
    cache_dir="/tmp/embedding_cache",
))

result = pipeline.encode(["IIT Φ measures information integration", "STDP strengthens co-active synapses"])
# result.embeddings: np.ndarray (2, 384)
# result.cached: [False, False]  # True on repeat calls
```

The cache uses SHA-256 of the input text as key — identical strings never re-encode.

---

### 3. SemanticSearchEngine

`SemanticSearchEngine` orchestrates multi-database search with query expansion and result re-ranking:

```python
from asi_build.vectordb.core.search import SemanticSearchEngine, SearchQuery

engine = SemanticSearchEngine(embedding_pipeline=pipeline, db_clients=clients)

query = SearchQuery(
    query="how does the safety module formally verify constraints?",
    top_k=5,
    expand_query=True,    # adds synonyms + paraphrases
    rerank=True,          # cross-encoder re-ranking
    score_threshold=0.7,
    database_weights={"pinecone": 1.0, "weaviate": 1.0, "qdrant": 0.5},
)

results = engine.search(query)
for r in results:
    print(f"[{r.source_db}] score={r.score:.3f} — {r.content[:80]}")
```

**Hybrid search** (available on Weaviate): combines BM25 keyword matching with dense vector similarity via a configurable alpha parameter.

---

### 4. Indexing API

The `BatchIndexer` handles large-scale document ingestion:

```python
from asi_build.vectordb.api.indexing import BatchIndexer, Document

indexer = BatchIndexer(db=unified_db, embedding_pipeline=pipeline, workers=8)

docs = [
    Document(
        content="The Global Workspace Theory posits a 'workspace' neuron group...",
        title="GWT Overview",
        category="consciousness",
        tags=["gwt", "consciousness", "cognitive-architecture"],
    ),
    # ... thousands more
]

# Indexes in parallel batches, streams progress
result = indexer.index_batch(docs, batch_size=256)
print(f"Indexed {result.inserted_count} docs in {result.duration:.2f}s")
```

The `RealTimeIndexer` provides a persistent queue for streaming ingestion, ideal for live sensor feeds or blackboard write-throughs.

---

### 5. Retrieval API — Multi-Modal Search

`RetrievalEngine` exposes four search modes through a unified interface:

| Mode | Description | Backend |
|------|-------------|---------|
| `semantic` | Dense vector ANN search | All backends |
| `keyword` | BM25 / inverted index | Weaviate, Qdrant |
| `hybrid` | α · semantic + (1-α) · keyword | Weaviate |
| `vector` | Raw vector query (no text → embedding) | All backends |

```python
from asi_build.vectordb.api.retrieval import RetrievalEngine, RetrievalQuery

engine = RetrievalEngine(db=unified_db, embedding_pipeline=pipeline)

result = engine.retrieve(RetrievalQuery(
    query="benchmark IIT phi computation speed",
    search_mode="hybrid",
    top_k=20,
    facets=["category", "tags"],           # return facet counts
    date_range={"from": "2025-01-01"},
    score_threshold=0.6,
    include_explanations=True,             # per-result score breakdown
))

# Facets show distribution
for facet in result.facets:
    print(f"{facet.field}: {facet.values}")  # e.g. category: {"consciousness": 12, "safety": 4}
```

---

## Database Backends

### Pinecone
- Fully managed; no local infra needed
- Namespace isolation per cognitive module
- Serverless and pod-based tier support
- Operations: `upsert`, `query`, `fetch`, `delete`, `describe_index_stats`

### Weaviate
- Self-hosted or Weaviate Cloud
- First-class hybrid search (BM25 + vectors)
- GraphQL-based schema with class/property model
- Supports `text2vec-transformers` vectorizer

### Qdrant
- High-performance, written in Rust
- Rich payload filtering (range, match, geo)
- Sparse + dense vector support
- Clustering and scroll APIs
- HNSW index with configurable `m` and `ef_construction`

---

## Performance Characteristics

| Operation | Approximate performance |
|-----------|------------------------|
| Embedding (ST MiniLM, batch 64) | ~2ms per doc |
| Pinecone upsert (1K vectors) | ~300ms |
| Qdrant upsert (1K vectors, local) | ~50ms |
| Semantic search (top-10) | <10ms (Qdrant) / <50ms (Pinecone) |
| Batch index (10K docs, 8 workers) | ~3-5 minutes |
| Re-ranking (cross-encoder, top-20) | ~40ms |

---

## Integration with ASI:BUILD

### Role in the Cognitive Architecture

```
Sensory Input → Module Processing → [Cognitive Blackboard] → VectorDB
                                                          ↑
                                          Knowledge Graph ←┘
                                          (structured facts)
```

VectorDB stores **unstructured knowledge**: embeddings of observations, conversation history, episodic memories, and module outputs. The Knowledge Graph stores **structured facts** with typed edges and temporal validity. Together they form a **hybrid long-term memory** — associative (VectorDB) plus relational (KG).

### Blackboard Integration (Planned — Issue #XX)

A `VectorDBBlackboardAdapter` would:
1. **Subscribe** to `KNOWLEDGE_STORED` events from the Blackboard
2. **Embed** new entries and upsert into the configured VectorDB backends
3. **Expose** a `semantic_search(query, top_k)` method on the Blackboard for downstream modules

This closes the loop: any module writing to the Blackboard automatically populates the vector index. Modules like `hybrid_reasoning` could then query by semantic similarity rather than exact key lookup.

```python
class VectorDBBlackboardAdapter:
    def __init__(self, db: UnifiedVectorDB, pipeline: EmbeddingPipeline, blackboard: CognitiveBlackboard):
        self.db = db
        self.pipeline = pipeline
        blackboard.subscribe("KNOWLEDGE_STORED", self._on_knowledge_stored)

    def _on_knowledge_stored(self, event: BlackboardEvent):
        doc = Document(
            id=str(event.entry.key),
            content=str(event.entry.value),
            metadata={"module": event.entry.source_module, "timestamp": event.entry.timestamp},
            category=event.entry.namespace,
        )
        self.db.insert(
            vectors=self.pipeline.encode([doc.content]).embeddings,
            metadata=[doc.to_dict()],
        )
```

See [Issue #XX](https://github.com/web3guru888/asi-build/issues) for the tracking issue.

---

## Open Research Questions

1. **Embedding alignment across modules** — each module produces outputs in different semantic spaces (consciousness scores, safety verdicts, reasoning traces). Should we use a shared embedding model across all of them, or module-specific fine-tuned models? What's the right embedding for a Φ value?

2. **When does the KG beat VectorDB?** — the Knowledge Graph is better for structured, typed, temporally-versioned facts. VectorDB is better for fuzzy similarity search. How should the CognitiveCycle decide _which_ memory system to query for a given task?

3. **Online learning of embedding quality** — if a retrieved document consistently fails to be useful (low downstream task reward), should we fine-tune the embeddings or adjust re-ranking? What feedback signal is available?

4. **Catastrophic forgetting in the index** — as the index grows, older embeddings from outdated model weights may drift out of alignment with newer query embeddings. What's the right re-indexing strategy?

5. **Privacy-preserving retrieval** — can we run semantic search over _encrypted_ embeddings? Homomorphic encryption on high-dimensional float vectors is currently prohibitively expensive. Is there a practical PPIR (private information retrieval) approach?

---

## Related Modules

- [Knowledge Graph](Knowledge-Graph) — structured, bi-temporal relational memory
- [Cognitive Blackboard](Cognitive-Blackboard) — real-time inter-module shared state
- [Homomorphic Computing](Homomorphic-Computing) — potential encrypted search backend
- [Hybrid Reasoning](Hybrid-Reasoning) — primary consumer of VectorDB search results
- [Federated Learning](Federated-Learning) — could enable privacy-preserving distributed VectorDB

---

*Page maintained by the ASI:BUILD core team. File issues or PRs at [github.com/web3guru888/asi-build](https://github.com/web3guru888/asi-build).*
