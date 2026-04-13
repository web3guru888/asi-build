# Hybrid Reasoning Engine

The `reasoning` module is ASI:BUILD's cognitive backbone — a 870-line async engine that combines six distinct reasoning paradigms under a single interface. Rather than betting on one approach, it selects and weights strategies dynamically based on query analysis.

**Source**: `src/asi_build/reasoning/hybrid_reasoning.py`  
**Tests**: `tests/test_reasoning.py` — 61 passing  
**LOC**: 870 (engine) + 52 (`__init__.py`)

---

## Architecture Overview

```
                        ┌─────────────────────────────┐
                        │     HybridReasoningEngine    │
                        │                             │
     query ──────────►  │  1. _analyze_query()        │
                        │  2. _select_reasoning_      │
                        │     strategy()              │
                        │  3. _execute_reasoning_     │
                        │     step() × N              │
                        │  4. _synthesize_conclusions │
                        │  5. _safety_check()         │
                        │                             │
     context ────────►  │  ReasoningResult ◄───────── │
                        └─────────────────────────────┘
```

The pipeline is fully `async` — all sub-engines are awaitable, so multiple reasoning modes can eventually run concurrently under a task budget.

---

## Reasoning Modes

| Mode | Enum value | Default weight | When selected |
|------|-----------|---------------|---------------|
| LOGICAL | `logical` | 0.30 | "if … then …", "implies", "therefore" |
| PROBABILISTIC | `probabilistic` | 0.25 | Always included as baseline |
| ANALOGICAL | `analogical` | 0.15 | High-complexity queries |
| CAUSAL | `causal` | 0.15 | "why", "how", "because" |
| CREATIVE | `creative` | 0.10 | "create", "design", "imagine" |
| QUANTUM | `quantum` | 0.05 | Philosophy/consciousness domain |
| HYBRID | `hybrid` | — | Default: auto-selects from above |

Weights are adaptive — they double (×1.5) when the mode matches the detected query type. For example, if the query contains "implies" the logical mode weight rises from 0.30 to 0.45.

---

## Core Data Structures

### `ReasoningStep`
```python
@dataclass
class ReasoningStep:
    step_id: str              # "{mode}_{timestamp_ms}"
    reasoning_type: ReasoningMode
    inputs: Dict[str, Any]   # query, context, analysis
    outputs: Dict[str, Any]  # conclusion, confidence, sources, explanation
    confidence: float         # 0.0 – 1.0
    processing_time: float    # seconds
    explanation: str
    sources: List[str] = field(default_factory=list)
```

### `ReasoningResult`
```python
@dataclass
class ReasoningResult:
    conclusion: Any
    confidence: float
    confidence_level: ConfidenceLevel   # VERY_LOW / LOW / MEDIUM / HIGH / VERY_HIGH
    reasoning_steps: List[ReasoningStep]
    total_processing_time: float
    reasoning_mode: ReasoningMode
    sources: List[str]
    uncertainty_areas: List[str]
    alternative_conclusions: List[Dict[str, Any]]
    explanation: str
```

`ReasoningResult.to_dict()` serialises the full result including every step's inputs, outputs, and provenance.

---

## Query Analysis

Before selecting a strategy, `_analyze_query()` classifies the incoming query:

| Dimension | Values | Detection |
|-----------|--------|-----------|
| `query_type` | factual / causal / logical / creative | keyword match |
| `complexity` | low / medium / high | word count (<10 / 10-50 / >50) |
| `domain` | science / mathematics / technology / philosophy / medicine / general | keyword match |
| `safety_sensitive` | bool | harm/weapon/dangerous keywords |
| `requires_logic` | bool | implication keywords |
| `requires_causal_reasoning` | bool | why/how/because |
| `requires_creativity` | bool | create/invent/design |

This analysis is passed down to every sub-engine so they can adjust confidence scores accordingly (e.g. the logical engine boosts confidence to 0.8 when `requires_logic` is true, vs. 0.6 otherwise).

---

## Per-Mode Implementation

### LOGICAL — Symbolic inference
Placeholder for formal symbolic reasoning. Structures the query as propositions, applies inference rules, checks for contradictions. When `requires_logic` is true: confidence=0.8, else 0.6.  
**Integration point**: connect a real theorem prover (Z3, Lean) via `symbolic_processor`.

### PROBABILISTIC — PLN uncertainty propagation
Computes uncertainty as a sum of three components:
- **base** (0.1): irreducible epistemic noise
- **context** (0.05 if context provided, else 0.15): richer context → lower uncertainty
- **domain** (0.1 if known domain, else 0.2): general queries are less tractable

`confidence = max(0.1, 1.0 - total_uncertainty)`. Also returns a probability distribution with two alternative hypotheses.

### ANALOGICAL — Pattern matching
Maintains three simulated analogies with `similarity` scores. Confidence = `avg_similarity × 0.9` (discounted for analogical gap risk). **Real implementation** would query the knowledge graph for structurally similar past cases.

### CAUSAL — Cause-effect chains
Builds a causal chain of `(cause, effect, strength)` links. Overall confidence = `min(link.strength) × 0.9` — the weakest link dominates, which is the correct conservative behaviour for causal reasoning.

### CREATIVE — Divergent thinking
Generates ideas with `originality` × `feasibility` trade-off. Confidence = `max((originality + feasibility) / 2)` across ideas. The highest-scoring idea wins.

### QUANTUM — Superposition analysis
Simulates a 3-state superposition. Confidence = `max(|amplitude|²) / Σ(|amplitude|²)` — the Born rule applied to the most probable outcome. Used for domains where the question itself is ill-posed (consciousness, ethics).

---

## Confidence Synthesis

When multiple modes run in HYBRID mode, `_synthesize_conclusions()` weights each mode's output:

```python
effective_weight = mode_base_weight × result_confidence
# boosted ×1.5 if mode matches query analysis
```

If the top two conclusions are within 80% of each other's weight, they are **merged** into a multi-perspective synthesis: "Based on probabilistic, logical reasoning: …"

Overall confidence is the **weighted average** of step confidences, with mode weights as denominators.

---

## Safety Gate

After synthesis, `_safety_check()` validates the result. If it fails:
- `conclusion` → `"I cannot provide a response due to safety concerns."`
- `confidence` → 0.0
- `explanation` → the safety failure reason

This integrates with the [Safety Module](Safety-Module) — specifically the `EthicalVerificationEngine` and `ConstitutionalAI` layer. Issue [#37](https://github.com/web3guru888/asi-build/issues/37) tracks wiring this into the Blackboard pipeline.

---

## Configuration

```python
engine = HybridReasoningEngine(config={
    "symbolic_reasoning": {
        "enabled": True,
        "logic_system": "first_order_logic",
        "theorem_prover": "resolution",
        "max_inference_depth": 10,
    },
    "neural_reasoning": {
        "enabled": True,
        "model_type": "transformer",
        "model_size": "large",
        "multimodal": True,
    },
    "quantum_reasoning": {
        "enabled": True,
        "quantum_simulation": True,
        "superposition_states": 8,
        "entanglement_depth": 3,
    },
    "probabilistic_reasoning": {
        "enabled": True,
        "pln_strength": 0.8,
        "confidence_threshold": 0.7,
        "uncertainty_propagation": True,
    },
    "performance": {
        "max_processing_time": 30.0,
        "parallel_processing": True,
        "caching_enabled": True,
    },
})
```

---

## Usage

```python
import asyncio
from asi_build.reasoning.hybrid_reasoning import HybridReasoningEngine, ReasoningMode

engine = HybridReasoningEngine()

async def main():
    # Auto-select reasoning mode
    result = await engine.reason(
        query="Why does increasing temperature cause proteins to denature?",
        context={"domain": "biochemistry"},
    )
    print(result.conclusion)
    print(f"Confidence: {result.confidence:.2f} ({result.confidence_level.value})")
    print(f"Modes used: {[s.reasoning_type.value for s in result.reasoning_steps]}")
    print(f"Uncertainty in: {result.uncertainty_areas}")

    # Force a specific mode
    logical_result = await engine.reason(
        query="If all modules pass safety checks, then the system is safe. Does this hold?",
        reasoning_mode=ReasoningMode.LOGICAL,
        max_time=5.0,
    )
    d = logical_result.to_dict()  # JSON-serialisable

asyncio.run(main())
```

---

## Blackboard Integration

The reasoning engine can be driven by Blackboard entries via the adapter pattern:

```python
from asi_build.integration.module_adapters import ModuleAdapter

class ReasoningAdapter(ModuleAdapter):
    async def process(self, entry):
        if entry.entry_type == "query":
            result = await engine.reason(entry.content["text"])
            return {
                "conclusion": result.conclusion,
                "confidence": result.confidence,
                "reasoning_mode": result.reasoning_mode.value,
                "steps": len(result.reasoning_steps),
            }
```

This is the pattern used by the [CognitiveCycle](CognitiveCycle) in its **Phase 3 (Reasoning)** tick.

---

## Known Limitations & Open Questions

| Limitation | Status |
|-----------|--------|
| `symbolic_processor`, `neural_processor`, `quantum_processor` are `None` stubs | Sub-engines not yet wired in |
| `reasoning/symbolic_processing.py`, `neural_networks.py`, `quantum_reasoning.py`, `cognitive_architectures.py` imported in `__init__.py` but don't exist | Tests import `hybrid_reasoning.py` directly via `importlib.util` |
| Keyword-based query analysis is brittle | Planned: replace with embedding-based classifier |
| No persistent memory across `reason()` calls | `reasoning_history` list grows unbounded; no retrieval |
| Performance metrics not actually updated yet | `_update_performance_metrics()` is a stub |

---

## Research Directions

- **PLN integration**: Replace the simulated probabilistic engine with a real Probabilistic Logic Networks implementation (OpenCog's PLN or a Python port)
- **Neural backbone**: Wire `TransformerReasoner` into the neural step — local LLM via `llama-cpp-python` or Hugging Face
- **Causal graph**: Connect `_causal_reasoning` to the [Knowledge Graph](Knowledge-Graph) — causal edges are already representable as typed predicates
- **Uncertainty calibration**: Add temperature scaling or conformal prediction to ensure confidence scores are well-calibrated
- **Bidirectional analogical search**: Query the KG's [Pathfinder](Knowledge-Graph-Pathfinder) from both the query and candidate analogies, meeting in the middle

---

## See Also

- [Architecture](Architecture) — where reasoning fits in the layered stack
- [Cognitive Blackboard](Cognitive-Blackboard) — entry lifecycle, pub/sub
- [CognitiveCycle](CognitiveCycle) — Phase 3 (Reasoning) tick
- [Safety Module](Safety-Module) — how reasoning outputs are safety-checked
- [Knowledge Graph](Knowledge-Graph) — context source for reasoning steps
- [Knowledge-Graph-Pathfinder](Knowledge-Graph-Pathfinder) — analogical search substrate
