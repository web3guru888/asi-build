# VectorDB

> **Maturity**: `alpha` · **Adapter**: `VectorDBBlackboardAdapter`

Vector database abstraction layer for semantic search across ASI:BUILD's knowledge stores. Provides a unified interface over multiple vector database backends (Pinecone, Weaviate, Qdrant), an embedding pipeline for converting text/data into vector representations, a semantic search engine with query optimization and result re-ranking, faceted search support, and indexing/retrieval APIs. Includes a `create_client()` factory function for backend-agnostic client instantiation.

## Key Classes

| Class | Description |
|-------|-------------|
| `VectorDBConfig` | Database configuration (backend, dimensions, metric) |
| `EmbeddingPipeline` | Text/data → vector embedding conversion pipeline |
| `SemanticSearchEngine` | Semantic similarity search with query optimization and re-ranking |
| `UnifiedVectorDB` | Backend-agnostic vector DB interface |
| `PineconeClient` | Pinecone backend client |
| `WeaviateClient` | Weaviate backend client |
| `QdrantClient` | Qdrant backend client |
| `IndexingAPI` | Document indexing API |
| `RetrievalAPI` | Document retrieval API |
| `create_client` | Factory function for backend-agnostic client instantiation |

## Example Usage

```python
from asi_build.vectordb import VectorDBConfig, EmbeddingPipeline, SemanticSearchEngine
config = VectorDBConfig(backend="qdrant", dimensions=768, metric="cosine")
pipeline = EmbeddingPipeline(model="all-MiniLM-L6-v2")
engine = SemanticSearchEngine(config=config, pipeline=pipeline)
engine.index("doc_1", text="Solar flares correlate with magnetic storms")
results = engine.search("space weather effects", top_k=5)
```

## Blackboard Integration

VectorDBBlackboardAdapter publishes indexing events, search results, and embedding metrics; consumes knowledge graph triples and discovery results for automatic semantic indexing.
