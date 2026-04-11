# ASI:BUILD Examples

Runnable demonstrations of each major ASI:BUILD module. Each example is self-contained and designed to run without external services (database instances, APIs) unless noted.

## Quick Start

```bash
# From the ASI:BUILD repo root:
pip install -e ".[all]"

# Run any example:
python examples/consciousness_demo.py
```

## Examples

| Example | Module | Description | External Deps |
|---------|--------|-------------|---------------|
| [`consciousness_demo.py`](consciousness_demo.py) | `consciousness/` | Global Workspace Theory competition & broadcast; IIT Φ computation | None (numpy, scipy, networkx) |
| [`synergy_metrics_demo.py`](synergy_metrics_demo.py) | `cognitive_synergy/` | All 7 information-theoretic synergy metrics on correlated vs random signals | None (numpy, scipy, scikit-learn) |
| [`homomorphic_encryption_demo.py`](homomorphic_encryption_demo.py) | `homomorphic/` | BGV scheme: keygen → encrypt → homomorphic add/multiply → decrypt | None (numpy) |
| [`knowledge_graph_demo.py`](knowledge_graph_demo.py) | Knowledge graph | Bi-temporal triples, contradiction detection, path finding (SQLite in-process) | None (sqlite3 stdlib) |
| [`vectordb_demo.py`](vectordb_demo.py) | `vectordb/` | Configuration walkthrough, API reference, local cosine-similarity mock | ⚠️ Full use needs Pinecone/Weaviate/Qdrant |
| [`graph_reasoning_demo.py`](graph_reasoning_demo.py) | `graph_intelligence/` | Community detection (Louvain), FastToG reasoning concept | ⚠️ Full FastToG needs Memgraph |
| [`bio_inspired_demo.py`](bio_inspired_demo.py) | `bio_inspired/` | Evolutionary optimization of 10-D Rastrigin function with adaptive GA | None (numpy) |

## Dependencies per example

All examples need the base ASI:BUILD install. Additional requirements:

- **consciousness_demo.py**: `numpy`, `scipy`, `networkx`
- **synergy_metrics_demo.py**: `numpy`, `scipy`, `scikit-learn`
- **homomorphic_encryption_demo.py**: `numpy`
- **knowledge_graph_demo.py**: None (uses stdlib `sqlite3`)
- **vectordb_demo.py**: `numpy` (mock mode); full mode needs vector DB client libraries
- **graph_reasoning_demo.py**: `numpy`, `networkx`
- **bio_inspired_demo.py**: `numpy`

## Notes

- The homomorphic encryption implementation is **pedagogical** — for production FHE, use [Microsoft SEAL](https://github.com/microsoft/SEAL), [OpenFHE](https://github.com/openfheorg/openfhe-development), or [TenSEAL](https://github.com/OpenMined/TenSEAL).
- The knowledge graph demo uses a standalone SQLite database to avoid requiring Memgraph. The full `graph_intelligence/` module uses Memgraph via the Bolt protocol.
- Vector DB examples show the API surface in mock mode. To run with live databases, set connection parameters in `VectorDBConfig`.
