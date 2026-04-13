# Phase 20.3 — KnowledgeFusion

> **Multi-source knowledge integration with conflict resolution, provenance tracking & ontology alignment.**

| Field | Value |
|---|---|
| **Package** | `asi.reasoning.fusion` |
| **Since** | Phase 20.3 |
| **Depends on** | WorldModel 13.1, LogicalInferenceEngine 20.1, DistributedTemporalSync 18.3 |
| **Integrates with** | CognitiveCycle, AnalogicalReasoner 20.2, AbductiveReasoner 20.4 |
| **Complexity** | High — multi-source conflict detection, trust-weighted resolution, provenance chains |

---

## Overview

**KnowledgeFusion** integrates knowledge from multiple heterogeneous sources — sensor data, inference results, analogical transfers, external APIs, agent communications — into a unified, consistent knowledge base. It detects conflicts between sources, resolves them via configurable policies (voting, trust-weighted, recency-based), tracks full provenance chains, and performs incremental ontology alignment.

### Design Principles

| Principle | Rationale |
|---|---|
| **Trust-weighted resolution** | Not all sources are equally reliable; resolution must account for source authority |
| **Provenance tracking** | Every fused atom must trace back to its origin through the full derivation chain |
| **Incremental ontology alignment** | Heterogeneous schemas must be unified without requiring a global ontology upfront |
| **Configurable conflict policy** | Different domains demand different resolution strategies (voting, recency, consensus) |
| **Frozen dataclasses** | Immutable atoms and records prevent accidental mutation across async boundaries |

---

## Data Flow

```
Sources (sensors, APIs, inference, agents)
        │
        ▼
┌─────────────────────────────────────────────┐
│           KnowledgeFusion                   │
│                                             │
│  ┌──────────┐  ┌──────────────┐  ┌───────┐ │
│  │ Validate  │→│ Deduplicate  │→│Detect  │ │
│  │ & Ingest  │  │ (subject,    │  │Conflict│ │
│  │           │  │  predicate)  │  │        │ │
│  └──────────┘  └──────────────┘  └───┬───┘ │
│                                      │      │
│  ┌──────────┐  ┌──────────────┐  ┌───▼───┐ │
│  │ Update    │←│ Merge &      │←│Resolve │ │
│  │Provenance │  │ Unify        │  │(Policy)│ │
│  └──────────┘  └──────────────┘  └───────┘ │
└─────────────────────┬───────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
    WorldModel   AnalogicalR.  AbductiveR.
      13.1          20.2          20.4
```

---

## Enums

### `ConflictPolicy`

```python
@enum.unique
class ConflictPolicy(enum.Enum):
    """Strategy for resolving conflicting knowledge atoms."""
    VOTING          = "voting"           # majority object_ wins
    TRUST_WEIGHTED  = "trust_weighted"   # sum(trust × confidence) per candidate
    RECENCY         = "recency"          # latest timestamp_ns wins
    CONSENSUS       = "consensus"        # require >2/3 agreement else PENDING_REVIEW
    MANUAL          = "manual"           # flag for human review
```

### `SourceTrust`

```python
@enum.unique
class SourceTrust(enum.Enum):
    """Trust level assigned to a knowledge source. Float mapping for scoring."""
    AUTHORITATIVE = "authoritative"  # 1.0
    HIGH          = "high"           # 0.8
    MEDIUM        = "medium"         # 0.5
    LOW           = "low"            # 0.3
    UNTRUSTED     = "untrusted"      # 0.1

    def weight(self) -> float:
        return {
            SourceTrust.AUTHORITATIVE: 1.0,
            SourceTrust.HIGH: 0.8,
            SourceTrust.MEDIUM: 0.5,
            SourceTrust.LOW: 0.3,
            SourceTrust.UNTRUSTED: 0.1,
        }[self]
```

### `FusionStatus`

```python
@enum.unique
class FusionStatus(enum.Enum):
    """Status of a knowledge atom after fusion."""
    CONSISTENT     = "consistent"      # no conflict detected
    CONFLICTED     = "conflicted"      # conflict detected, not yet resolved
    RESOLVED       = "resolved"        # conflict resolved by policy
    PENDING_REVIEW = "pending_review"  # requires manual review (CONSENSUS failed / MANUAL policy)
```

---

## Frozen Dataclasses

### `KnowledgeSource`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class KnowledgeSource:
    """A registered knowledge source."""
    source_id: str
    name: str
    trust: SourceTrust
    domain: str                  # e.g. "sensor", "inference", "external_api"
    last_updated_ns: int         # monotonic nanoseconds
```

### `ProvenanceRecord`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    """Single link in a provenance chain."""
    record_id: str
    source: KnowledgeSource
    timestamp_ns: int
    derivation_chain: tuple[str, ...]   # ordered record_ids of ancestors
    confidence: float                   # [0.0, 1.0]
```

### `KnowledgeAtom`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class KnowledgeAtom:
    """Atomic unit of knowledge — an (S, P, O) triple with provenance."""
    atom_id: str
    subject: str
    predicate: str
    object_: str                        # trailing underscore avoids builtin clash
    provenance: tuple[ProvenanceRecord, ...]
    status: FusionStatus
    confidence: float                   # aggregated confidence [0.0, 1.0]
```

### `ConflictReport`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class ConflictReport:
    """Report describing a detected conflict between two atoms."""
    atom_a: KnowledgeAtom
    atom_b: KnowledgeAtom
    conflict_type: str              # e.g. "value_mismatch", "temporal_inconsistency"
    resolution: KnowledgeAtom | None        # populated after resolve
    policy_used: ConflictPolicy | None      # populated after resolve
```

### `FusionConfig`

```python
@dataclasses.dataclass(frozen=True, slots=True)
class FusionConfig:
    """Configuration for the fusion pipeline."""
    conflict_policy: ConflictPolicy = ConflictPolicy.TRUST_WEIGHTED
    min_confidence: float = 0.3
    enable_provenance: bool = True
    max_atoms: int = 100_000
    alignment_threshold: float = 0.7    # Jaccard similarity threshold for ontology alignment
    auto_resolve: bool = True           # auto-resolve conflicts; False → PENDING_REVIEW
```

---

## Protocol

```python
@typing.runtime_checkable
class KnowledgeFusion(typing.Protocol):
    """Multi-source knowledge integration with conflict resolution & provenance."""

    async def fuse(
        self, atoms: tuple[KnowledgeAtom, ...],
    ) -> tuple[KnowledgeAtom, ...]:
        """Run the full fusion pipeline: validate → deduplicate → detect → resolve → merge → provenance."""
        ...

    async def add_source(self, source: KnowledgeSource) -> None:
        """Register a new knowledge source."""
        ...

    async def detect_conflicts(self) -> tuple[ConflictReport, ...]:
        """Scan the atom store for conflicting atoms (same subject+predicate, different object_)."""
        ...

    async def resolve_conflict(
        self,
        report: ConflictReport,
        policy: ConflictPolicy | None = None,
    ) -> KnowledgeAtom:
        """Resolve a conflict using the given policy (or config default)."""
        ...

    async def get_provenance(self, atom_id: str) -> tuple[ProvenanceRecord, ...]:
        """Return the full provenance chain for an atom."""
        ...

    async def align_ontology(
        self,
        source_schema: dict[str, str],
        target_schema: dict[str, str],
    ) -> dict[str, str]:
        """Align source schema keys to target schema keys via similarity + structural isomorphism."""
        ...
```

---

## Implementation — `AsyncKnowledgeFusion`

### Construction

```python
class AsyncKnowledgeFusion:
    """Production implementation of KnowledgeFusion.

    Internals
    ---------
    _sources : dict[str, KnowledgeSource]  — registered sources keyed by source_id
    _atoms   : dict[str, KnowledgeAtom]    — atom store keyed by atom_id
    _index   : dict[tuple[str,str], list[str]]  — (subject, predicate) → [atom_id, ...]
    _lock    : asyncio.Lock                — guards _atoms / _index mutations
    _config  : FusionConfig
    """

    def __init__(self, config: FusionConfig | None = None) -> None: ...
```

### Fusion Pipeline

The `fuse()` method executes a 6-step pipeline:

```
1. Validate: drop atoms below min_confidence, cap at max_atoms.
2. Deduplicate: group by (subject, predicate, object_) — merge provenance.
3. Detect conflicts: same (subject, predicate) with different object_.
4. Resolve: apply conflict_policy (or flag PENDING_REVIEW).
5. Merge: upsert into _atoms + update _index.
6. Update provenance: append fusion record to each surviving atom.
```

Returns the fused atoms that were accepted.

### Conflict Detection

For each `(subject, predicate)` key in `_index` with more than one `atom_id`:
- Compare `object_` values pairwise → `ConflictReport(conflict_type="value_mismatch")`
- Check temporal inconsistency if provenance timestamps diverge by more than a configurable window

### Conflict Resolution

Dispatch to `_resolve_*` methods based on the `ConflictPolicy`:

| Policy | Algorithm |
|---|---|
| **VOTING** | Count occurrences across sources; majority `object_` wins |
| **TRUST_WEIGHTED** | `sum(source.trust.weight() × atom.confidence)` per distinct `object_`; highest score wins |
| **RECENCY** | Latest provenance `timestamp_ns` wins |
| **CONSENSUS** | >2/3 sources agree → accept; else → `PENDING_REVIEW` |
| **MANUAL** | Mark `PENDING_REVIEW` immediately |

```python
async def _resolve_voting(self, a: KnowledgeAtom, b: KnowledgeAtom) -> KnowledgeAtom: ...
async def _resolve_trust_weighted(self, a: KnowledgeAtom, b: KnowledgeAtom) -> KnowledgeAtom: ...
async def _resolve_recency(self, a: KnowledgeAtom, b: KnowledgeAtom) -> KnowledgeAtom: ...
async def _resolve_consensus(self, a: KnowledgeAtom, b: KnowledgeAtom) -> KnowledgeAtom: ...
```

### Provenance Tracking

```python
async def get_provenance(self, atom_id: str) -> tuple[ProvenanceRecord, ...]:
    """Return provenance chain ordered by timestamp_ns ascending."""

def _append_provenance(self, atom: KnowledgeAtom, record: ProvenanceRecord) -> KnowledgeAtom:
    """Return new KnowledgeAtom with record appended to provenance tuple (frozen)."""
```

### Ontology Alignment

```python
async def align_ontology(
    self,
    source_schema: dict[str, str],
    target_schema: dict[str, str],
) -> dict[str, str]:
    """
    1. Compute Jaccard similarity on character 3-grams for every (source_key, target_key) pair.
    2. Filter pairs below alignment_threshold.
    3. Greedy bipartite matching (highest similarity first, 1:1 mapping).
    4. Structural isomorphism check: verify mapped keys share comparable value types.
    Returns dict mapping source_key → target_key.
    """

@staticmethod
def _jaccard_ngrams(a: str, b: str, n: int = 3) -> float:
    """Character n-gram Jaccard similarity ∈ [0.0, 1.0]."""
```

---

## Null Implementation

```python
class NullKnowledgeFusion:
    """No-op implementation for DI / testing."""
    async def fuse(self, atoms): return atoms
    async def add_source(self, source): pass
    async def detect_conflicts(self): return ()
    async def resolve_conflict(self, report, policy=None):
        return report.atom_a
    async def get_provenance(self, atom_id): return ()
    async def align_ontology(self, source_schema, target_schema): return {}
```

---

## Factory

```python
def make_knowledge_fusion(
    *,
    config: FusionConfig | None = None,
    null: bool = False,
) -> KnowledgeFusion:
    if null:
        return NullKnowledgeFusion()
    return AsyncKnowledgeFusion(config=config or FusionConfig())
```

---

## Integration Map

```
┌─────────────────────────────────────────────────────────────┐
│                     CognitiveCycle                           │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐│
│  │LogicalInf. │  │ Knowledge    │  │ AnalogicalReasoner   ││
│  │Engine 20.1 │─▶│ Fusion 20.3  │◀─│ 20.2                 ││
│  │(inferences)│  │              │  │(analogical transfers)││
│  └────────────┘  │  ┌────────┐  │  └──────────────────────┘│
│                  │  │Conflict│  │                           │
│  ┌────────────┐  │  │Resolver│  │  ┌──────────────────────┐│
│  │WorldModel  │◀─│  └────────┘  │─▶│ AbductiveReasoner    ││
│  │13.1        │  │  ┌────────┐  │  │ 20.4                 ││
│  │(grounded)  │  │  │Prove-  │  │  │(hypothesis atoms)   ││
│  └────────────┘  │  │nance   │  │  └──────────────────────┘│
│                  │  └────────┘  │                           │
│  ┌────────────┐  │              │                           │
│  │Distributed │─▶│  ┌────────┐  │                           │
│  │TemporalSync│  │  │Ontology│  │                           │
│  │18.3        │  │  │Aligner │  │                           │
│  └────────────┘  └──┴────────┴──┘                           │
└─────────────────────────────────────────────────────────────┘
```

### Integration Contracts

- **WorldModel 13.1**: After fusion, resolved atoms are pushed via `world_model.upsert_entity()` to ground the unified knowledge.
- **LogicalInferenceEngine 20.1**: Inference conclusions arrive as `KnowledgeAtom` tuples with `source.domain="inference"`. The engine calls `fuse()` after each reasoning cycle.
- **DistributedTemporalSync 18.3**: Remote peers push atoms via `receive_push()` → `fuse()`. Provenance records carry the originating peer's clock vector.
- **AnalogicalReasoner 20.2**: Analogical transfers produce candidate atoms with `source.domain="analogy"` and typically `SourceTrust.MEDIUM`. Fusion validates and resolves conflicts with existing knowledge.
- **AbductiveReasoner 20.4**: Hypotheses are submitted as atoms with `source.domain="abduction"` and `SourceTrust.LOW`. If they survive conflict resolution, they are promoted to the knowledge base.
- **CognitiveCycle**: Calls `fuse()` once per tick after collecting atoms from all reasoning sub-systems. Monitors `detect_conflicts()` output for self-improvement triggers.

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `asi_fusion_atoms_total` | Gauge | — | Active knowledge atoms in the store |
| `asi_fusion_conflicts_detected` | Counter | — | Total conflicts detected |
| `asi_fusion_conflicts_resolved` | Counter | `policy` | Conflicts resolved, labeled by policy |
| `asi_fusion_fuse_seconds` | Histogram | — | Fusion pipeline end-to-end latency |
| `asi_fusion_sources_active` | Gauge | — | Registered knowledge sources |

### PromQL Examples

```promql
# Conflict resolution rate over 5m
rate(asi_fusion_conflicts_resolved_total[5m])

# Unresolved conflict ratio
asi_fusion_conflicts_detected_total - ignoring(policy) sum(asi_fusion_conflicts_resolved_total)

# Fusion throughput (atoms/sec)
rate(asi_fusion_atoms_total[1m])

# P99 fusion latency
histogram_quantile(0.99, rate(asi_fusion_fuse_seconds_bucket[5m]))
```

### Grafana Alerts

```yaml
- alert: HighConflictRate
  expr: rate(asi_fusion_conflicts_detected_total[5m]) > 10
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "KnowledgeFusion detecting >10 conflicts/sec for 3m"

- alert: FusionLatencyHigh
  expr: histogram_quantile(0.99, rate(asi_fusion_fuse_seconds_bucket[5m])) > 2.0
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "KnowledgeFusion P99 latency exceeds 2s"

- alert: PendingReviewBacklog
  expr: count(asi_fusion_atoms_total{status="pending_review"}) > 50
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Over 50 knowledge atoms awaiting manual review"
```

---

## mypy Strict Compliance

| Pattern | Technique |
|---|---|
| `ConflictPolicy \| None` parameter | `if policy is None: policy = self._config.conflict_policy` narrows type |
| `KnowledgeAtom \| None` resolution | `assert resolution is not None` after policy dispatch |
| `dict[str, str]` schema | Explicit `dict[str, str]` avoids `Any` inference |
| `tuple[ProvenanceRecord, ...]` immutable | Concatenation via `(*existing, new_record)` preserves tuple type |
| Frozen dataclass mutation | `dataclasses.replace(atom, status=FusionStatus.RESOLVED)` returns new instance |
| `_resolve_*` dispatch | `match/case` on `ConflictPolicy` enum exhaustiveness check |

---

## Test Targets (12)

| # | Test | Assertion |
|---|---|---|
| 1 | `test_fuse_deduplicates_identical_atoms` | Identical (S,P,O) triples → single atom with merged provenance |
| 2 | `test_fuse_detects_value_mismatch` | Same (S,P), different O → conflict detected |
| 3 | `test_resolve_voting_majority_wins` | 3 sources: 2 agree → majority object_ chosen |
| 4 | `test_resolve_trust_weighted_highest_score` | AUTHORITATIVE source beats two MEDIUM sources |
| 5 | `test_resolve_recency_latest_wins` | Most recent timestamp_ns atom is picked |
| 6 | `test_resolve_consensus_below_threshold` | <2/3 agreement → PENDING_REVIEW status |
| 7 | `test_provenance_chain_append_only` | After N fusions, provenance length = N+1 |
| 8 | `test_align_ontology_above_threshold` | Similar keys aligned; dissimilar keys excluded |
| 9 | `test_align_ontology_structural_check` | Type-mismatch keys rejected even if names similar |
| 10 | `test_null_implementation_protocol` | `isinstance(NullKnowledgeFusion(), KnowledgeFusion)` is True |
| 11 | `test_factory_null_flag` | `make_knowledge_fusion(null=True)` returns NullKnowledgeFusion |
| 12 | `test_max_atoms_cap_enforced` | Exceeding `max_atoms` triggers eviction of lowest-confidence atoms |

### Test Skeletons

```python
@pytest.mark.asyncio
async def test_fuse_deduplicates_identical_atoms():
    fusion = make_knowledge_fusion(config=FusionConfig())
    source = KnowledgeSource("s1", "sensor", SourceTrust.HIGH, "sensor", 0)
    prov = ProvenanceRecord("r1", source, 1000, (), 0.9)
    atom_a = KnowledgeAtom("a1", "temp", "reading", "25C", (prov,), FusionStatus.CONSISTENT, 0.9)
    atom_b = KnowledgeAtom("a2", "temp", "reading", "25C", (prov,), FusionStatus.CONSISTENT, 0.85)
    result = await fusion.fuse((atom_a, atom_b))
    assert len(result) == 1
    assert len(result[0].provenance) >= 2  # merged provenance

@pytest.mark.asyncio
async def test_resolve_trust_weighted_highest_score():
    fusion = make_knowledge_fusion(config=FusionConfig(conflict_policy=ConflictPolicy.TRUST_WEIGHTED))
    auth_source = KnowledgeSource("s1", "authority", SourceTrust.AUTHORITATIVE, "sensor", 0)
    med_source = KnowledgeSource("s2", "medium", SourceTrust.MEDIUM, "api", 0)
    prov_a = ProvenanceRecord("r1", auth_source, 1000, (), 0.9)
    prov_b = ProvenanceRecord("r2", med_source, 2000, (), 0.8)
    atom_a = KnowledgeAtom("a1", "temp", "reading", "25C", (prov_a,), FusionStatus.CONFLICTED, 0.9)
    atom_b = KnowledgeAtom("a2", "temp", "reading", "30C", (prov_b,), FusionStatus.CONFLICTED, 0.8)
    report = ConflictReport(atom_a, atom_b, "value_mismatch", None, None)
    winner = await fusion.resolve_conflict(report)
    assert winner.object_ == "25C"  # AUTHORITATIVE×0.9 > MEDIUM×0.8
```

---

## Implementation Order

1. Define `ConflictPolicy`, `SourceTrust`, `FusionStatus` enums with `weight()` method
2. Define `KnowledgeSource`, `ProvenanceRecord`, `KnowledgeAtom`, `ConflictReport`, `FusionConfig` frozen dataclasses
3. Define `KnowledgeFusion` Protocol with `@runtime_checkable`
4. Implement `NullKnowledgeFusion` + `make_knowledge_fusion()` factory
5. Implement `AsyncKnowledgeFusion.__init__` with `_sources`, `_atoms`, `_index`, `_lock`, metrics
6. Implement `add_source()` with Gauge metric
7. Implement `_jaccard_ngrams()` static method + unit tests
8. Implement `align_ontology()` with greedy bipartite matching
9. Implement deduplication logic (group by S,P,O → merge provenance)
10. Implement `detect_conflicts()` via `_index` scan
11. Implement `_resolve_voting`, `_resolve_trust_weighted`, `_resolve_recency`, `_resolve_consensus`
12. Implement `resolve_conflict()` dispatcher with `match/case`
13. Implement `fuse()` full pipeline orchestrating steps 9–12 + provenance append
14. Integration test: end-to-end `fuse()` with mixed sources, verify WorldModel + AnalogicalReasoner handoff

---

## Phase 20 — Knowledge Synthesis & Reasoning — Sub-phase Tracker

| Sub-phase | Component | Issue | Status |
|---|---|---|---|
| 20.1 | LogicalInferenceEngine | #484 | 🟡 Spec'd |
| 20.2 | AnalogicalReasoner | #485 | 🟡 Spec'd |
| **20.3** | **KnowledgeFusion** | **#482** | **🟡 Spec'd** |
| 20.4 | AbductiveReasoner | #483 | 🟡 Spec'd |
| 20.5 | ReasoningOrchestrator | #486 | 🟡 Spec'd |

---

*Tracking: #109 · Discussion: #481*
