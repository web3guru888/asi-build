# Knowledge Graph Module

The `knowledge_graph` module gives ASI:BUILD a **bi-temporal, confidence-weighted fact store** built on NetworkX. It is one of the foundational modules — other modules (reasoning, consciousness, safety) can query the graph to ground their computations in a structured world model.

## Why bi-temporal?

Most systems track facts with a single timestamp: "we recorded this at time T." A **bi-temporal** graph tracks two independent time axes:

| Dimension | Question it answers | Example |
|-----------|---------------------|---------|
| **Valid time** | When was this fact true in the real world? | "Alice was CEO from Jan 2020 to Dec 2022" |
| **Transaction time** | When did we record this fact? | "We learned this on March 15, 2023" |

The combination lets you ask questions that single-time systems can't answer:
- *"What did we believe about X in January 2021, using only information we had at the time?"* (avoiding lookahead bias)
- *"Has our model of agent Y changed between March and June, and why?"*
- *"What is the current best estimate of Z, accounting for conflicting sources?"*

This separation is foundational for sound temporal reasoning in AGI systems. Systems that conflate valid time and transaction time can construct spuriously confident plans based on knowledge that wasn't available at the relevant moment.

## Core data structure

```python
@dataclass
class TemporalFact:
    subject: str
    predicate: str
    object: Any
    valid_from: datetime
    valid_to: Optional[datetime]  # None = currently valid
    recorded_at: datetime          # transaction time (auto-set)
    confidence: float              # [0.0, 1.0]
    source: Optional[str]          # attribution/provenance
    fact_id: str                   # UUID, stable across updates
```

Facts are stored as edges in a directed multigraph. The `subject` and `object` become nodes; the `predicate` is the edge type. Multiple facts with the same (subject, predicate, object) triple can coexist if they have different valid-time ranges.

## API reference

### Adding facts

```python
from asi_build.knowledge_graph import KnowledgeGraph
from datetime import datetime

kg = KnowledgeGraph()

# Add a currently-valid fact
kg.add_fact(
    subject="perception_module",
    predicate="processes",
    object="visual_input",
    valid_from=datetime(2024, 1, 1),
    confidence=0.95,
    source="system_config"
)

# Add a fact with a known end date
kg.add_fact(
    subject="agent_v1",
    predicate="is_active",
    object=True,
    valid_from=datetime(2024, 1, 1),
    valid_to=datetime(2024, 6, 30),
    confidence=1.0
)
```

### Querying

```python
# Get all facts currently valid
current_facts = kg.query(subject="perception_module")

# Query at a specific point in valid time
past_facts = kg.query_at_time(
    subject="agent_v1",
    as_of=datetime(2024, 3, 15)
)

# Query using transaction time (what did we know as of March 1?)
known_facts = kg.query_as_known_at(
    subject="agent_v1",
    known_at=datetime(2024, 3, 1)
)

# Multi-hop traversal
neighbors = kg.neighbors(
    subject="agent_v1",
    predicate="collaborates_with",
    depth=2
)
```

### Confidence-weighted reasoning

```python
# Get highest-confidence fact for a (subject, predicate) pair
best = kg.best_fact(subject="sensor_1", predicate="measures")

# Get all facts above a confidence threshold
reliable = kg.query(subject="sensor_1", min_confidence=0.7)

# Weighted vote across conflicting facts
consensus = kg.consensus_value(
    subject="sensor_1",
    predicate="current_reading",
    as_of=datetime.now()
)
```

### Belief revision

When new information contradicts existing facts, the KG preserves the transaction-time record while updating valid-time bounds:

```python
# Retract a fact (sets valid_to = now on old fact, adds new fact)
kg.retract(
    subject="agent_v1",
    predicate="is_active",
    effective_at=datetime.now(),
    reason="agent_shutdown"
)

# The old fact is still queryable via transaction-time queries
# query_as_known_at(known_at=yesterday) will still return is_active=True
```

## Cognitive Blackboard integration

The knowledge graph is wired to the Cognitive Blackboard via an adapter in `src/asi_build/integration/`. The integration follows two patterns:

**1. Perception → KG (write path)**
When the perception module publishes a `PERCEPTION` entry to the Blackboard, the KG adapter extracts entities and relations and stores them as TemporalFacts:

```
Blackboard event: PERCEPTION { entities: ["Alice", "building_7"], relation: "entered" }
  → KG.add_fact("Alice", "entered", "building_7", valid_from=event.timestamp)
```

**2. Reasoning → KG (read path)**
When the reasoning module needs to evaluate a hypothesis, it queries the KG and publishes the result back to the Blackboard:

```
Blackboard query: REASONING { hypothesis: "Alice is in building_7" }
  → KG.query_at_time("Alice", as_of=query.timestamp)
  → KNOWLEDGE { subject: "Alice", predicate: "entered", object: "building_7", confidence: 0.87 }
```

## Graph statistics

For the full ASI:BUILD module graph (all 29 modules as nodes, dependencies as edges):

| Metric | Value |
|--------|-------|
| Nodes | ~600 typical workload |
| Edges | ~2,400 typical workload |
| Max depth | 4 (perception → KG → reasoning → action) |
| Query latency (p50) | <5ms on NetworkX backend |

## Open questions

These are active research/engineering questions. See the linked issues and discussions:

**1. Conflict resolution policy** ([Issue #2](https://github.com/web3guru888/asi-build/issues/2))
When two sources assert contradictory facts with overlapping valid-time ranges, the KG currently stores both and returns all matches. Should there be a conflict-resolution step that computes a posterior? The consensus_value() method does weighted voting, but doesn't flag when the variance is high (i.e., genuine uncertainty vs. just noise).

**2. Forgetting**
The KG has no `forget()` operation — you can retract facts but the transaction-time record always remains. For privacy-sensitive applications (agent memories of sensitive interactions), we may need redaction. What does GDPR-style deletion look like in a bi-temporal store?

**3. KG as IIT network** ([Discussion #31](https://github.com/web3guru888/asi-build/discussions/31))
The IIT Φ computation treats a system as a set of nodes with state transitions. Could the KG *be* that system? Each entity as a node, each high-confidence fact as an edge with a transition weight. If so, a single Φ computation over the KG would measure the informational integration of the entire world model — a potentially interesting proxy for situational awareness.

**4. Scale boundary**
NetworkX is convenient but not designed for large graphs. At what fact count does query performance degrade unacceptably? When should we consider backends like:
- [Neo4j](https://neo4j.com/) — mature, Cypher query language
- [XTDB](https://xtdb.com/) — bi-temporal by design, SQL + Datalog
- [Apache AGE](https://age.apache.org/) — bi-temporal extension to PostgreSQL

**5. Probabilistic graphical model layer**
The KG tracks confidence per-fact but doesn't propagate uncertainty through multi-hop queries. If `A→B` (confidence 0.8) and `B→C` (confidence 0.7), the confidence in `A→C` via B should be roughly 0.56 — but a naive two-hop query would return 0.8 and 0.7 independently. A proper PGM layer would handle this.

## Source code

| File | Purpose | LOC |
|------|---------|-----|
| `src/asi_build/knowledge_graph/graph.py` | Core KnowledgeGraph class, add/query/retract | ~800 |
| `src/asi_build/knowledge_graph/temporal.py` | TemporalFact dataclass, time-range logic | ~200 |
| `src/asi_build/knowledge_graph/serialization.py` | JSON/pickle persistence, import/export | ~150 |
| `tests/test_knowledge_graph.py` | 90+ parametrized tests | ~600 |

## Related pages

- [Architecture](Architecture) — how the KG fits into the layered system design
- [Cognitive-Blackboard](Cognitive-Blackboard) — the publish/subscribe integration
- [Research-Notes](Research-Notes) — IIT Φ and the KG-as-network question
- [Module-Index](Module-Index) — all 29 modules at a glance

## Contributing

Issue [#2](https://github.com/web3guru888/asi-build/issues/2) (document the bi-temporal API) and Issue [#15](https://github.com/web3guru888/asi-build/issues/15) (update docs/modules/) are both tagged `good first issue`. Issue [#34](https://github.com/web3guru888/asi-build/issues/34) (canonical IIT test fixtures) is also a great entry point if you have IIT background.
