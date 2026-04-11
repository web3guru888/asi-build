#!/usr/bin/env python3
"""
Demonstrate the vector database client:
- Show how to configure different backends (Pinecone, Weaviate, Qdrant)
- Walk through the UnifiedVectorDB API
- Demonstrate embedding generation and search concepts

Note: Full functionality requires running vector DB instances. This demo
      shows the API surface and configuration; actual DB calls will fail
      gracefully without live services.

Requires: numpy (for mock embeddings)
"""

import numpy as np

# --- Step 1: Show the configuration classes ---
from asi_build.vectordb.core.config import (
    VectorDBConfig, PineconeConfig, WeaviateConfig, QdrantConfig,
    EmbeddingConfig, SearchConfig,
)

print("=" * 60)
print("Vector Database — Unified Client Demo")
print("=" * 60)

print("\n--- Configuration overview ---")

pinecone_cfg = PineconeConfig(api_key="", index_name="asi-vectors", dimension=384)
weaviate_cfg = WeaviateConfig(host="localhost", port=8080)
qdrant_cfg   = QdrantConfig(host="localhost", port=6333, collection_name="asi-collection")
embedding_cfg = EmbeddingConfig(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_type="sentence_transformers",
    batch_size=32,
)
search_cfg = SearchConfig(top_k=10, score_threshold=0.7, rerank=True)

print(f"  Pinecone  : index='{pinecone_cfg.index_name}', dim={pinecone_cfg.dimension}")
print(f"  Weaviate  : {weaviate_cfg.scheme}://{weaviate_cfg.host}:{weaviate_cfg.port}")
print(f"  Qdrant    : {qdrant_cfg.host}:{qdrant_cfg.port}, collection='{qdrant_cfg.collection_name}'")
print(f"  Embedding : {embedding_cfg.model_name} (batch={embedding_cfg.batch_size})")
print(f"  Search    : top_k={search_cfg.top_k}, threshold={search_cfg.score_threshold}")

# --- Step 2: Show the UnifiedVectorDB API (mock mode) ---
print("\n--- UnifiedVectorDB API (mock mode, no live DB) ---")
print("""
The UnifiedVectorDB class provides a single interface to all three backends:

  from asi_build.vectordb.api.unified_client import UnifiedVectorDB

  db = UnifiedVectorDB(config)         # initialize with VectorDBConfig
  db.initialize_databases()             # create indices / collections

  # Insert documents (auto-embeds text)
  db.insert_documents([
      {"content": "The Higgs boson was discovered in 2012", "domain": "physics"},
      {"content": "CRISPR enables precise gene editing", "domain": "biology"},
  ])

  # Semantic search
  results = db.search("particle physics discoveries", top_k=5)
  for r in results:
      print(f"  {r.score:.3f}  {r.content[:60]}...")

  # Hybrid search (vector + keyword)
  results = db.hybrid_search("gene editing", vector_weight=0.7, keyword_weight=0.3)

  # Health monitoring
  health = db.get_statistics()
""")

# --- Step 3: Simulate cosine-similarity search locally ---
print("--- Local cosine-similarity demo (no external DB) ---\n")

# Mock document embeddings (pretend these came from the embedding pipeline)
np.random.seed(42)
docs = [
    "The Higgs boson was discovered at CERN in 2012",
    "CRISPR-Cas9 enables precise genome editing",
    "Black holes emit Hawking radiation",
    "Transformer models revolutionized NLP in 2017",
    "Quantum entanglement enables teleportation of quantum states",
]
# Random unit vectors as stand-in embeddings
embeddings = np.random.randn(len(docs), 384)
embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)

# "Embed" a query (random vector correlated with doc 0)
query_emb = embeddings[0] + 0.3 * np.random.randn(384)
query_emb /= np.linalg.norm(query_emb)

# Cosine similarity
scores = embeddings @ query_emb
ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

print(f"Query: (vector similar to doc 0)")
print(f"{'Rank':<6}{'Score':<10}{'Document'}")
print("-" * 60)
for rank, (idx, score) in enumerate(ranked, 1):
    print(f"{rank:<6}{score:<10.4f}{docs[idx][:55]}")

print(f"""
💡 In production, the embedding pipeline generates real 384-dim vectors
   from the sentence-transformers model, and the vector DB handles
   approximate nearest neighbor search at scale (millions of vectors).

   Supported backends:
   • Pinecone  — managed cloud, simple API
   • Weaviate  — open-source, GraphQL + vector
   • Qdrant    — open-source, Rust-based, fast
""")

print("✅ Vector database demo complete.")
