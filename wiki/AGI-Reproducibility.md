# AGI Reproducibility Module

> **Location**: `src/asi_build/agi_reproducibility/`  
> **Size**: 30 files · 7,926 LOC  
> **Status**: Core infrastructure — experiment tracking + formal safety verification  

## Overview

The AGI Reproducibility module solves two intertwined problems in AGI research:

1. **Reproducibility**: Making AGI experiments fully repeatable — same code, same data, same environment, same results.
2. **Formal Safety Verification**: Providing mathematical guarantees about safety properties before and during execution.

Most ML research is notoriously difficult to reproduce. AGI research compounds this with emergent behavior, stochastic training, environment drift, and the near-impossibility of specifying "what went wrong" in formal terms. This module attacks both problems head-on.

## Architecture

```
agi_reproducibility/
├── experiment_tracking/
│   ├── tracker.py           # ExperimentTracker — SQLite-backed record system
│   └── versioning.py        # VersionManager — semantic versioning + Git integration
├── formal_verification/
│   ├── lang/
│   │   ├── ast/
│   │   │   └── safety_ast.py        # AGSSL AST — safety specification language
│   │   ├── parser/
│   │   │   └── safety_parser.py     # AGSSL parser
│   │   └── semantic/
│   │       └── type_checker.py      # Type system for safety specs
│   ├── provers/
│   │   ├── theorem_proving/
│   │   │   └── safety_prover.py     # ResolutionProver, NaturalDeduction, SequentCalculus
│   │   ├── model_checking/
│   │   │   └── safety_model_checker.py  # CTL/LTL model checker
│   │   └── symbolic_execution/      # Symbolic execution engine
│   ├── monitors/
│   │   ├── runtime/
│   │   │   └── safety_monitor.py    # Real-time runtime monitor
│   │   ├── constraints/
│   │   │   └── constraint_enforcer.py
│   │   └── alerts/                  # Alert dispatch
│   ├── testing/
│   │   ├── adversarial/
│   │   │   └── adversarial_tester.py
│   │   └── robustness/
│   └── integration/
│       ├── generic/                 # Generic AGI framework integration
│       ├── hyperon/                 # OpenCog Hyperon integration
│       └── primus/                  # PRIMUS / Cognitive Synergy integration
├── config.py
└── exceptions.py
```

## 1. Experiment Tracking

### ExperimentTracker

The core tracking system uses **async SQLite** (`aiosqlite`) for non-blocking writes during live experiments.

```python
from asi_build.agi_reproducibility.experiment_tracking.tracker import (
    ExperimentTracker,
    ExperimentMetadata,
    ExperimentRecord,
    ExperimentStatus,
)

tracker = ExperimentTracker(db_path="experiments.db")

# Define experiment
meta = ExperimentMetadata(
    id="exp-iit-001",
    title="IIT Φ computation on recurrent networks",
    description="Benchmark correct TPM-based IIT 3.0 against approximations",
    author="ASI:BUILD Team",
    email="research@asi-build.dev",
    tags=["consciousness", "IIT", "benchmark"],
    agi_framework="asi_build",
    research_area="consciousness",
    hypothesis="TPM-based Φ > 0 for strongly connected recurrent networks",
    expected_outcomes=["Φ > 0.1 for 4-node recurrent", "linear scaling with node count"],
    ethical_considerations="Pure measurement, no actuation",
    computational_requirements={"cpu": "4 cores", "ram": "8GB", "time": "~60s"},
)

# Start tracking
record = await tracker.create_experiment(meta)
await tracker.update_status(record.id, ExperimentStatus.RUNNING)

# Record results
await tracker.record_results(record.id, {
    "phi_4node": 0.314,
    "phi_8node": 0.891,
    "runtime_ms": 4200,
})
await tracker.update_status(record.id, ExperimentStatus.COMPLETED)
```

### ExperimentRecord Fields

| Field | Type | Description |
|-------|------|-------------|
| `metadata` | `ExperimentMetadata` | Author, tags, hypothesis, ethical considerations |
| `status` | `ExperimentStatus` | CREATED → RUNNING → COMPLETED/FAILED/CANCELLED |
| `git_commit` | `Optional[str]` | Git hash at run time |
| `environment_snapshot` | `Dict` | Python version, package versions, OS, hardware |
| `code_hash` | `str` | SHA-256 of source files |
| `data_hash` | `str` | SHA-256 of input datasets |
| `config_hash` | `str` | SHA-256 of configuration |
| `parameters` | `Dict` | Hyperparameters and settings |
| `results` | `Optional[Dict]` | Outcome metrics |
| `benchmarks` | `Optional[Dict]` | Performance measurements |
| `verification_results` | `Optional[Dict]` | Formal safety check outcomes |
| `peer_reviews` | `List[Dict]` | Review records |
| `citations` | `List[str]` | References |
| `reproductions` | `List[Dict]` | Successful/failed reproduction attempts |

### ExperimentStatus Lifecycle

```
CREATED → RUNNING → COMPLETED
                  ↘ FAILED
                  ↘ CANCELLED
                  ↘ INTERRUPTED → RUNNING (retry)
COMPLETED → ARCHIVED
```

### VersionManager

Integrates with Git for semantic versioning of experiments:

```python
from asi_build.agi_reproducibility.experiment_tracking.versioning import (
    VersionManager,
    VersionType,
)

vm = VersionManager(repo_path=".")

# Create a new experiment version
version = await vm.create_version(
    experiment_id="exp-iit-001",
    version_type=VersionType.MINOR,
    message="Add 8-node recurrent network benchmark",
    changes=["Extended test matrix", "Fixed TPM normalization"],
)

# Branch for ablation study
branch = await vm.create_branch(
    name="ablation/no-normalization",
    base_version=version.version,
    purpose="Test impact of TPM normalization on Φ",
)
```

**VersionType enum**:
- `MAJOR` — breaking change in experiment design
- `MINOR` — new conditions or metrics added
- `PATCH` — bug fix or data correction
- `PRERELEASE` — work in progress
- `SNAPSHOT` — auto-captured checkpoint

## 2. Formal Verification

### AGI Safety Specification Language (AGSSL)

The formal verification subsystem introduces **AGSSL**, a domain-specific language for expressing safety properties. It compiles to an AST that can be fed to multiple backends: theorem provers, model checkers, or runtime monitors.

#### Property Types

| Type | Meaning |
|------|---------|
| `INVARIANT` | Must always be true |
| `TEMPORAL` | Time-dependent (LTL/CTL) |
| `VALUE_ALIGNMENT` | Value preservation across states |
| `CORRIGIBILITY` | System accepts human correction |
| `GOAL_STABILITY` | Goals don't drift under optimization |
| `IMPACT_BOUND` | Optimization stays within impact limits |
| `MESA_SAFETY` | Sub-agents don't develop misaligned goals |

#### Temporal Operators (LTL/CTL)

| Symbol | Operator | Meaning |
|--------|----------|---------|
| `G` | Always | True in all future states |
| `F` | Eventually | True in some future state |
| `X` | Next | True in the immediately next state |
| `U` | Until | True until another property becomes true |
| `W` | Weak Until | Until, but second property can remain false forever |
| `R` | Release | Dual of Until |

#### Logical Operators

Supports full first-order logic: `∧ ∨ ¬ → ↔ ∀ ∃`

### Provers

#### ResolutionProver

Classic **resolution-based theorem proving**:

```
Algorithm:
1. Negate the theorem (proof by refutation)
2. Convert axioms + negated theorem to CNF (conjunctive normal form)
3. Apply resolution rule repeatedly:
   (A ∨ C) ∧ (¬A ∨ D) ⊢ (C ∨ D)
4. If empty clause derived → theorem proven
5. Halt at max_resolution_steps=1000 → TIMEOUT
```

Proof results are **cached** by a key derived from `(theorem, axioms)` to avoid re-proving in repeated calls.

#### NaturalDeductionProver

Human-readable proof format using introduction/elimination rules:
- `→I` (implication introduction), `→E` (modus ponens)
- `∧I`, `∧E₁`, `∧E₂`
- `∨I₁`, `∨I₂`, `∨E`
- `¬I` (reductio ad absurdum), `¬E`

#### SequentCalculusProver

Proof via sequents `Γ ⊢ Δ` (from assumptions Γ, derive one of Δ). Used for checking safety property entailment in multi-hypothesis contexts.

#### ProofTrace

Every proof attempt produces a `ProofTrace`:

```python
@dataclass
class ProofTrace:
    theorem: SafetyExpression    # What was proven
    result: ProofResult          # PROVED | DISPROVED | TIMEOUT | UNKNOWN | ERROR
    steps: List[ProofStep]       # Derivation steps
    time_taken: float            # Seconds
    proof_hash: str              # MD5 of theorem+result+step_count (for caching)
```

### Model Checker

Implements **CTL/LTL model checking** over a finite state system:

```python
@dataclass
class SystemState:
    id: str
    variables: Dict[str, Any]   # Variable valuations at this state

@dataclass
class Transition:
    source: SystemState
    target: SystemState
    action: str
    guard: Optional[SafetyExpression]  # Enabling condition
```

**Model checking results**:
- `SATISFIED` — property holds in all reachable states
- `VIOLATED` — counterexample found
- `TIMEOUT` — state space too large
- `UNKNOWN` — incomplete exploration

When `VIOLATED`, a `CounterExample` is generated:

```python
@dataclass
class CounterExample:
    property_name: str
    trace: List[SystemState]      # Path from initial → violation
    violated_at_step: int
    violation_description: str
```

### Runtime Safety Monitor

The **RuntimeSafetyMonitor** runs continuously during AGI execution, checking safety properties on every state transition:

```python
class AlertLevel(Enum):
    INFO      = "info"
    WARNING   = "warning"
    CRITICAL  = "critical"
    EMERGENCY = "emergency"
```

When a property is violated:
1. `SafetyAlert` is created with violation description + suggested actions
2. Alert dispatched based on severity
3. EMERGENCY → triggers shutdown sequence

**MonitoringResult** per property:
```python
@dataclass
class MonitoringResult:
    property_name: str
    satisfied: bool
    confidence: float          # 0.0 to 1.0
    violation_severity: float  # 0.0 to 1.0
    evidence: Dict[str, Any]   # Supporting data
```

#### Performance

The monitor runs in a **background thread** with a fixed-capacity queue to avoid blocking the main AGI loop. Properties are evaluated in priority order; EMERGENCY-level properties are checked first.

### Adversarial Tester

Tests safety properties under **adversarial perturbations**:
- Boundary condition probing
- Goal injection attacks
- Value drift simulation
- Mesa-optimization pressure tests

### Integration Bridges

Pre-built adapters for plugging the verification stack into different frameworks:

| Bridge | Target |
|--------|--------|
| `generic/` | Any Python AGI system |
| `hyperon/` | OpenCog Hyperon / MeTTa |
| `primus/` | PRIMUS cognitive synergy engine |

## Connection to the Safety Module

The `agi_reproducibility` formal verification system is **distinct from but complementary to** the main `safety/` module:

| Concern | `safety/` module | `agi_reproducibility/formal_verification/` |
|---------|-----------------|---------------------------------------------|
| Runtime rules | ConstitutionalAI, governance | RuntimeSafetyMonitor |
| Formal proofs | EthicalVerificationEngine (Z3) | ResolutionProver, SequentCalculusProver |
| Property language | Python predicates | AGSSL (typed, formally specified) |
| Experiment records | — | ExperimentTracker, VersionManager |
| Framework bridges | — | Hyperon, PRIMUS adapters |

The vision: experiments run through `ExperimentTracker`, formal properties expressed in AGSSL are verified before execution begins, the RuntimeSafetyMonitor watches during execution, and violations feed back into experiment records for postmortem analysis.

## Blackboard Integration (Planned)

A `ReproducibilityBlackboardAdapter` would write:
- `experiment.started` — ExperimentRecord metadata
- `experiment.checkpoint` — intermediate results
- `safety.property.violated` — RuntimeSafetyMonitor alerts
- `experiment.completed` — final record with all hashes

This would make every blackboard entry **experiment-scoped** — you could replay any cognitive cycle by pulling the corresponding experiment record and re-running with the same code/data/config hashes.

> **Track this**: [Issue #80 — Wire agi_reproducibility to Cognitive Blackboard](https://github.com/web3guru888/asi-build/issues)

## Open Research Questions

1. **Hash instability**: Code/data hashes break if floating-point output varies across platforms. How do we define "same result" for stochastic experiments?

2. **Temporal logic completeness**: AGSSL currently supports LTL + CTL. Adding CTL* (which subsumes both) would be more expressive but model checking becomes PSPACE-complete. Worth the cost?

3. **Mesa-optimization detection**: The `MESA_SAFETY` property type exists, but detecting mesa-optimizers at runtime is an open research problem. What signal would trigger the alert?

4. **Proof caching across versions**: `proof_hash` caches by theorem+axiom content. But after a code change (new version), should cached proofs be invalidated? The theorem may still hold, but the system has changed.

5. **PRIMUS bridge**: The `integration/primus/` bridge is scaffolded. How should AGSSL safety properties compose with PRIMUS synergy metrics? Can we write `G(synergy > 0.5 → ¬safety_violation)`?

## See Also

- [Safety Module](Safety-Module) — runtime constitutional AI, Z3-backed ETF, governance
- [Cognitive Blackboard](Cognitive-Blackboard) — shared state for all modules
- [Research Notes](Research-Notes) — formal verification bug post-mortem
- [CognitiveCycle](CognitiveCycle) — where safety gates are applied per-tick
- [Testing Strategy](Testing-Strategy) — property tests that complement formal proofs
