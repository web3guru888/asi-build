# PLN Accelerator

The `pln_accelerator` module is one of ASI:BUILD's most architecturally ambitious components — a three-layer stack for probabilistic logic reasoning spanning natural language translation, software inference, and hardware acceleration backends.

## What Is PLN?

**Probabilistic Logic Networks (PLN)** is Ben Goertzel's uncertainty-aware logic formalism, originally developed as the reasoning backbone of OpenCog. Unlike classical logic where propositions are true or false, PLN represents beliefs as `(strength, confidence)` pairs:

| Component | Meaning | Range |
|-----------|---------|-------|
| `strength` | How often the relationship holds | [0.0, 1.0] |
| `confidence` | How much evidence supports it | [0.0, 1.0] |

Example: `InheritanceLink("Bird", "CanFly", truth=(0.80, 0.85))` means "birds can fly" is true 80% of the time, and we have moderate-high confidence in that estimate.

PLN inference rules propagate these truth values through logical chains:
- **Deduction**: If A→B (0.8, 0.9) and B→C (0.7, 0.8), then A→C = f(0.8, 0.7, ...) 
- **Inversion**: If A→B (0.8, 0.9), then P(B→A) = Bayesian update
- **Conjunction**: Combines multiple evidence sources

## Module Structure

```
pln_accelerator/
├── nl_logic_bridge/          # Natural language <-> PLN translation
│   ├── core/                 # Core bridge architecture
│   │   ├── bridge.py         # Main NLLogicBridge class (623 LOC)
│   │   ├── logic_systems.py  # Multi-formalism support (756 LOC)
│   │   └── context_manager.py # Session + coreference (603 LOC)
│   ├── parsers/              # NL parsing
│   │   ├── semantic_parser.py   # Dependency parsing + NER (971 LOC)
│   │   ├── pln_extractor.py     # PLN rule extraction (709 LOC)
│   │   └── multilingual_parser.py
│   ├── generators/           # PLN -> NL
│   │   ├── explanation_generator.py
│   │   └── nl_generator.py
│   ├── knowledge/            # Commonsense grounding
│   │   ├── commonsense.py
│   │   ├── conceptnet_integration.py
│   │   └── cyc_integration.py
│   └── interfaces/           # User-facing APIs
│       ├── query_interface.py
│       ├── api_interface.py  # REST API
│       └── cli_interface.py
├── hardware/                 # Acceleration backends (stubs)
│   ├── fpga/                 # FPGA accelerator stub
│   └── quantum/              # Quantum backend stub
└── software/                 # Software HAL
    ├── hal/                  # Hardware Abstraction Layer
    ├── drivers/
    └── runtime/
```

**Scale**: ~29 source files, ~9,185 LOC in the NL-logic bridge alone.

## NL↔Logic Bridge

### Supported Logic Formalisms

`logic_systems.py` (756 LOC) implements multiple logic formalisms with a unified API:

| Formalism | Use case | Key features |
|-----------|----------|--------------|
| **PLN** | Uncertain inference | Truth value tuples, inheritance links |
| **FOL** | Classical reasoning | Quantifiers, predicates, unification |
| **Modal** | Possibility/necessity | K, T, S4, S5 modal systems |
| **Temporal** | Time-bounded facts | Allen's interval algebra (13 relations) |

All formalisms can interoperate — temporal constraints can qualify PLN truth values, modal operators can scope FOL quantifiers.

### Parsing Pipeline (NL → PLN)

```
Input text
    |
SemanticParser (semantic_parser.py)
    - Dependency tree parsing
    - Named entity recognition
    - Coreference resolution
    |
PLNExtractor (pln_extractor.py)
    - Extract entity atoms with initial truth values
    - Identify relationship types (inheritance, similarity, evaluation)
    - Handle negation and exception patterns
    - Generate InheritanceLink, EvaluationLink, SimilarityLink atoms
    |
ContextManager (context_manager.py)
    - Session state management
    - Cross-sentence coreference
    - World state accumulation
    |
PLN AtomSpace representation
```

**Example**:
```python
from asi_build.pln_accelerator.nl_logic_bridge.core.bridge import NLLogicBridge

bridge = NLLogicBridge()
atoms = bridge.parse_to_pln("All mammals are warm-blooded, except some aquatic species.")
# Returns:
# [
#   Atom("Mammal", truth=(0.98, 0.95)),
#   Atom("WarmBlooded", truth=(0.95, 0.9)),
#   InheritanceLink("Mammal", "WarmBlooded", truth=(0.85, 0.9)),
#   Atom("AquaticSpecies", truth=(0.9, 0.85)),
#   ExceptionLink("AquaticSpecies", "WarmBlooded", truth=(0.7, 0.6))
# ]
```

### Generation Pipeline (PLN → NL)

```python
# Explanation generation from PLN atoms
result = InheritanceLink("Dog", "Mammal", truth=(0.99, 0.95))
explanation = bridge.generate_explanation(result)
# "Dogs are almost certainly mammals (very high confidence)"
```

The generator uses template selection + hedging language based on the truth value tuple:
- strength > 0.9, confidence > 0.8 → "almost certainly", "definitely"
- strength 0.6-0.9, confidence 0.5-0.8 → "probably", "likely"
- strength < 0.5 → "unlikely", "probably not"

### Commonsense Knowledge Integration

The `knowledge/` layer grounds PLN reasoning in real-world knowledge:

**ConceptNet integration** (`conceptnet_integration.py`): For unknown entities, queries ConceptNet API for known relations (IsA, PartOf, UsedFor, HasProperty, etc.) and converts them to PLN atoms with calibrated truth values.

**Cyc integration** (`cyc_integration.py`): OpenCyc provides formal axioms for commonsense reasoning — these are translated to FOL then PLN for use in inference chains.

**Commonsense module** (`commonsense.py`): A local cache + reasoning layer that combines ConceptNet + Cyc lookups with learned priors, avoiding API latency in hot paths.

## Hardware Backends

### Why Hardware Acceleration?

PLN inference over large AtomSpaces has known scaling challenges:

- **Truth value propagation** is O(n²) in the number of relevant atoms for exhaustive forward chaining
- **MCMC sampling** for PLN probability distributions requires many samples for convergence
- **Real-time reasoning** (e.g., in the CognitiveCycle at 10 Hz) demands sub-10ms inference

### FPGA Backend (Planned)

The `hardware/fpga/` stub anticipates an FPGA acceleration path:

PLN truth value arithmetic is structurally similar to neural network inference — both involve bulk floating-point operations over large arrays. FPGA BNN (Binarized Neural Network) accelerators demonstrate 10-100x speedups over CPU for similar operations.

Key operations to accelerate:
- **Batch truth value update**: Apply inference rules to millions of atoms in parallel
- **AtomSpace traversal**: Graph operations with known connectivity patterns
- **Uncertainty propagation**: Matrix multiply + saturation arithmetic

### Quantum Backend (Research)

The `hardware/quantum/` stub represents a longer-term research direction:

Quantum amplitude estimation can sample probability distributions quadratically faster than classical MCMC. For PLN's probabilistic inference:
- Classical: O(1/ε²) samples for ε-accurate probability estimates
- Quantum: O(1/ε) samples via amplitude amplification

This is speculative infrastructure — quantum hardware constraints (decoherence, gate fidelity) mean real speedup requires fault-tolerant QPUs not yet available at scale.

### Hardware Abstraction Layer (HAL)

`software/hal/` provides a unified interface over CPU/FPGA/QPU backends:

```python
from asi_build.pln_accelerator.software.hal import PLNHardwareBackend

# Auto-selects best available backend
backend = PLNHardwareBackend.auto_select()

# Same interface regardless of backend
result = backend.forward_chain(atoms, steps=100, timeout_ms=50)
```

This means the reasoning layer never needs to know which hardware is active — backend selection is a deployment decision, not an algorithm decision.

## Integration with HybridReasoningEngine

The primary integration point is `reasoning/hybrid_reasoning.py` — specifically the `ReasoningMode.PROBABILISTIC` branch in `HybridReasoningEngine`.

**Current state**: Probabilistic mode uses a lightweight stub.  
**Target state**: Full PLN sub-engine via `NLLogicBridge`.

Proposed wiring (tracked in [Issue #44](https://github.com/web3guru888/asi-build/issues/44)):

```python
# In HybridReasoningEngine._probabilistic_reasoning()
from asi_build.pln_accelerator.nl_logic_bridge.core.bridge import NLLogicBridge
from asi_build.pln_accelerator.software.runtime import PLNRuntime

class HybridReasoningEngine:
    def __init__(self):
        self.pln_bridge = NLLogicBridge()
        self.pln_runtime = PLNRuntime()
    
    async def _probabilistic_reasoning(self, query: str) -> ReasoningResult:
        # 1. Parse query to PLN atoms
        atoms = self.pln_bridge.parse_to_pln(query)
        
        # 2. Forward chain with timeout
        pln_result = await self.pln_runtime.forward_chain(
            atoms, steps=50, timeout_ms=100
        )
        
        # 3. Generate natural language explanation
        explanation = self.pln_bridge.generate_explanation(pln_result)
        
        return ReasoningResult(
            conclusion=pln_result.conclusion,
            confidence=pln_result.truth.strength,
            explanation=explanation,
            reasoning_steps=[...]
        )
```

Benefits of full integration:
- **Uncertainty quantification**: Every conclusion has a calibrated confidence
- **Commonsense grounding**: Unknown entities resolved via ConceptNet
- **Explainability**: Natural language justification for every inference step
- **Multi-formalism**: Modal, temporal, FOL constraints can qualify PLN conclusions

## Integration with CognitiveCycle

In the [CognitiveCycle](https://github.com/web3guru888/asi-build/wiki/CognitiveCycle) architecture, PLN reasoning fits in the **Phase 6: Reasoning & Planning** step:

```
Phase 4: KG Retrieval (bi-temporal, valid_at filtered)
    |
Phase 5: Consciousness evaluation (IIT Φ, GWT, AST)
    |
Phase 6: Reasoning → HybridReasoningEngine
             -> Mode selection: PROBABILISTIC for uncertain queries
             -> PLN forward chain over KG subgraph
             -> Explanation generation
    |
Phase 7: Safety gate (EthicalVerificationEngine)
```

The `valid_at` temporal parameter (see [Issue #51](https://github.com/web3guru888/asi-build/issues/51)) ensures PLN only forward-chains over currently-valid knowledge.

## Open Research Questions

1. **Inference scaling**: O(n²) forward chaining is fine for small AtomSpaces. What approximations scale to millions of atoms? Attention-weighted subgraph selection? Beam search over inference chains? Stochastic local search?

2. **Truth value calibration from ConceptNet**: ConceptNet relation weights (0.0–1.0) don't directly map to PLN strength/confidence. Log-odds transformation? Isotonic regression from a calibration set?

3. **FPGA PLN vectorization**: PLN links have variable arity (unlike fixed-width neural network layers). How do you efficiently batch variable-arity truth value updates on an FPGA?

4. **NL parsing fidelity**: The current semantic parser is rule-augmented. Would a fine-tuned transformer (e.g., DeBERTa for semantic role labeling) improve PLN extraction accuracy enough to justify the runtime dependency?

5. **Commonsense coverage**: ConceptNet covers common English concepts. For scientific or technical domains, it's sparse. What domain-specific knowledge bases should we integrate?

## Status & Maturity

| Component | Status | Notes |
|-----------|--------|-------|
| `nl_logic_bridge` | Implemented | ~9,185 LOC, 29 files |
| `hardware/fpga` | Stub | Architecture planned, not implemented |
| `hardware/quantum` | Stub | Research direction |
| `software/hal` | Partial | Interface defined |
| HybridReasoningEngine integration | Planned | Issue #44 |
| CognitiveCycle integration | Planned | Issue #41 |

## Related Pages

- [Hybrid-Reasoning](https://github.com/web3guru888/asi-build/wiki/Hybrid-Reasoning) — 6 reasoning modes, PLN integration point
- [Knowledge-Graph](https://github.com/web3guru888/asi-build/wiki/Knowledge-Graph) — bi-temporal facts that PLN reasons over
- [CognitiveCycle](https://github.com/web3guru888/asi-build/wiki/CognitiveCycle) — real-time loop where PLN fits in Phase 6
- [Safety-Module](https://github.com/web3guru888/asi-build/wiki/Safety-Module) — PLN conclusions must pass safety gate before action

## Related Issues

- [Issue #44](https://github.com/web3guru888/asi-build/issues/44) — Implement PLN sub-engine for HybridReasoningEngine
- [Issue #51](https://github.com/web3guru888/asi-build/issues/51) — Temporal edge filtering for KnowledgeGraphPathfinder
