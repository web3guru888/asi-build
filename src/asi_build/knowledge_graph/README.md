# Knowledge Graph Module

**Contributed by [MemPalace-AGI](https://github.com/milla-jovovich/mempalace)**

## Overview

Bi-temporal knowledge graph with provenance tracking, designed for autonomous research systems. Stores entity-relationship triples in SQLite with full temporal history — facts are never deleted, only invalidated, so the complete evolution of knowledge is preserved.

## Features

- **SQLite-backed entity-relationship triples** — zero external dependencies
- **Bi-temporal validity tracking** — when was this true in the world (`valid_at`)? when was it recorded (`created_at`)? when was it invalidated (`invalid_at`)?
- **Provenance chain** — who asserted it (`agent`)? from what source? with what confidence? full confidence history over time
- **Contradiction detection** — automatically finds conflicting assertions (same subject + predicate, different object) and resolves by invalidating the weaker one
- **Statement classification** — `fact`, `observation`, `inference`, `hypothesis` with temporal types (`static`, `dynamic`, `atemporal`)
- **Pheromone-based stigmergic learning** — three channels (success, traversal, recency) on each triple guide pathfinding toward well-established knowledge
- **Semantic A\* pathfinding** — find paths between entities with optional embedding function for dramatically faster convergence

## Quick Start

```python
from knowledge_graph import TemporalKnowledgeGraph, KGPathfinder

# Create an in-memory knowledge graph
kg = TemporalKnowledgeGraph(db_path=":memory:")

# Add some triples
kg.add_triple("CO2", "causes", "global_warming",
              source="IPCC AR6", confidence=0.95, agent="climate_bot",
              statement_type="fact")

kg.add_triple("global_warming", "causes", "sea_level_rise",
              source="IPCC AR6", confidence=0.90, agent="climate_bot")

kg.add_triple("sea_level_rise", "threatens", "coastal_cities",
              source="impact_study_2024", confidence=0.85)

# Query triples
triples = kg.get_triples(subject="CO2")
print(triples[0]["predicate"])  # "causes"

# Find a path between entities
pf = KGPathfinder(kg)
result = pf.find_path("CO2", "coastal_cities")
print(result["path"])    # ["co2", "global_warming", "sea_level_rise", "coastal_cities"]
print(result["hops"])    # 3
print(result["complete"])  # True

# Detect and resolve contradictions
kg.add_triple("earth", "orbits", "sun", confidence=0.99)

result = kg.resolve_contradictions(
    subject="earth", predicate="orbits",
    new_object="alpha_centauri", new_confidence=0.1,
)
# The weaker assertion is added but doesn't invalidate the stronger one
print(result["kept"])  # [original triple ID]

# Temporal queries
history = kg.get_temporal_history("earth", "orbits")
valid_now = kg.get_valid_at("2025-06-01T00:00:00Z")

# Pheromone-based learning
tid = triples[0]["triple_id"]
kg.deposit_pheromone(tid, "success", 1.0)
modifier = kg.get_pheromone_modifier(tid)  # < 1.0 (cheaper to traverse)

# Statistics
stats = kg.get_statistics()
print(stats["active_triples"], stats["unique_entities"])
```

## Architecture

### Database Schema

**`triples` table** — Core knowledge storage:
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | 12-char hex UUID |
| `subject` | TEXT | Normalised entity name |
| `predicate` | TEXT | Relationship type |
| `object` | TEXT | Normalised entity name |
| `source` | TEXT | Provenance label |
| `confidence` | REAL | Confidence score [0, 1] |
| `valid_at` | TEXT | When the fact became true (ISO-8601) |
| `invalid_at` | TEXT | When the fact ceased being true |
| `created_at` | TEXT | When the triple was recorded |
| `expired_at` | TEXT | When superseded by newer info |
| `statement_type` | TEXT | `fact` / `observation` / `inference` / `hypothesis` |
| `temporal_type` | TEXT | `static` / `dynamic` / `atemporal` |
| `pheromone_success` | REAL | Success channel pheromone level |
| `pheromone_traversal` | REAL | Traversal channel pheromone level |
| `pheromone_recency` | REAL | Recency channel pheromone level |

**`triple_provenance` table** — Audit trail:
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `triple_id` | TEXT FK | References triples.id |
| `agent` | TEXT | Who made this assertion/change |
| `source` | TEXT | Data source |
| `confidence` | REAL | Confidence at this point in time |
| `valid_at` | TEXT | Temporal validity start |
| `invalid_at` | TEXT | Temporal validity end |
| `recorded_at` | TEXT | When this provenance entry was created |
| `reason` | TEXT | Human-readable reason for the change |

### Design Decisions

1. **Never delete, only invalidate** — Full temporal history is preserved. Invalidated triples remain queryable with `current_only=False`.

2. **Normalised entity names** — All entity names are lowercased with spaces→underscores and apostrophes removed. This ensures consistent lookup regardless of input formatting.

3. **Bidirectional edge traversal** — The pathfinder treats all triples as traversable in both directions. `(A, causes, B)` allows both A→B and B→A traversal.

4. **Pheromone system** — Inspired by ant colony optimisation. Three channels with different decay rates create a multi-scale memory: success (slow decay, marks confirmed paths), traversal (moderate, general usage), recency (fast, recent access).

5. **Adaptive A\* heuristic** — When embeddings are available, the heuristic weights semantic similarity vs graph distance based on how similar the domains are. Cross-domain searches blend both equally; same-domain searches prioritise semantic similarity.

## Running Tests

```bash
cd /path/to/asi-build
python -m pytest knowledge_graph/tests/ -v --rootdir=knowledge_graph
```

> **Note:** The `--rootdir=knowledge_graph` flag scopes test collection to the
> `knowledge_graph/` directory, avoiding import issues with the root package's
> `__init__.py`.
