# Getting Started

This guide walks you from zero to running your first ASI:BUILD experiment.

---

## Prerequisites

- **Python 3.10, 3.11, or 3.12** (3.11 recommended)
- **pip** or a virtual environment manager (`venv`, `conda`, `uv`)
- **Git**

Optional but useful:
- [Memgraph](https://memgraph.com/) — for `graph_intelligence` and `memgraph_toolbox` modules
- [Qiskit](https://qiskit.org/) — for `quantum` module circuits

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/web3guru888/asi-build.git
cd asi-build
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows
```

### 3. Install the package

```bash
# Minimal install (core modules only)
pip install -e .

# With development tools (recommended)
pip install -e ".[dev]"

# With all optional extras
pip install -e ".[dev,quantum,homomorphic]"
```

The `[dev]` extras install: `pytest`, `black`, `mypy`, `ruff`, and all test dependencies.

---

## Verify the Install

```bash
# Run the full test suite
pytest tests/ -q

# Expected output:
# 2581 passed, 42 skipped in ~45s
```

If you see import errors, check that you're in your virtual environment and that `pip install -e .` completed without errors.

---

## Your First Experiment

### Example 1: Knowledge Graph

```python
from asi_build.knowledge_graph import TemporalKnowledgeGraph

kg = TemporalKnowledgeGraph()

# Add entities and relationships
kg.add_entity("AlphaGo", {"type": "AI system", "domain": "games"})
kg.add_entity("Reinforcement Learning", {"type": "technique"})
kg.add_relationship("AlphaGo", "Reinforcement Learning", "uses")

# Query
results = kg.query_entities({"type": "AI system"})
print(results)

# Find path between nodes (A* pathfinding)
path = kg.find_path("AlphaGo", "Reinforcement Learning")
print(f"Path: {path}")
```

### Example 2: Consciousness Measurement

```python
from asi_build.consciousness import GlobalWorkspaceTheory, IntegratedInformation

# Global Workspace Theory — broadcast competition
gwt = GlobalWorkspaceTheory()
result = gwt.broadcast({
    "modality": "visual",
    "content": "red square",
    "salience": 0.9,
})
print(f"Won broadcast: {result['winner']}")
print(f"Coalition size: {result['coalition_size']}")

# IIT Φ — integrated information (⚠️ see Research Notes below)
iit = IntegratedInformation()
phi = iit.compute_phi(system_states=[[1, 0, 1], [0, 1, 0]])
print(f"Φ (approximate) = {phi:.4f}")
```

> ⚠️ **Research Note on IIT Φ**: The current implementation computes an entropy-difference approximation, not the full TPM-based Φ per Tononi (2014). See [issue #6](https://github.com/web3guru888/asi-build/issues/6) for the fix roadmap.

### Example 3: Cognitive Synergy Metrics

```python
from asi_build.cognitive_synergy import CognitiveSynergyEngine

engine = CognitiveSynergyEngine()

# Measure synergy between two information streams
synergy = engine.compute_synergy(
    stream_a=[0.1, 0.4, 0.7, 0.3, 0.8],
    stream_b=[0.2, 0.5, 0.6, 0.4, 0.9],
)
print(f"Transfer entropy A→B: {synergy['transfer_entropy_ab']:.4f}")
print(f"Mutual information:   {synergy['mutual_information']:.4f}")
```

### Example 4: Full Cognitive Blackboard

```python
from asi_build.integration import CognitiveBlackboard, BlackboardEntry, EntryPriority
from asi_build.integration.adapters import wire_all, ConsciousnessAdapter, KnowledgeGraphAdapter

# Create shared workspace
bb = CognitiveBlackboard()

# Post a finding from one module
bb.post(BlackboardEntry(
    topic="consciousness.phi",
    data={"phi": 2.7, "theory": "IIT", "elements": 3},
    source_module="consciousness",
    priority=EntryPriority.HIGH,
))

# Another module queries it
results = bb.get_by_topic("consciousness")
for entry in results:
    print(f"[{entry.source_module}] {entry.topic}: {entry.data}")
```

---

## Runnable Examples

The `examples/` directory contains complete, runnable scripts:

```
examples/
├── consciousness_demo.py        # GWT broadcast + IIT Φ measurement
├── knowledge_graph_demo.py      # Bi-temporal KG with A* pathfinding
├── synergy_analysis.py          # Information-theoretic synergy metrics
├── graph_intelligence_demo.py   # FastToG reasoning pipeline
├── homomorphic_demo.py          # FHE encrypt → compute → decrypt
└── quantum_hybrid_demo.py       # Quantum circuit + classical postprocessing
```

```bash
python examples/consciousness_demo.py
python examples/knowledge_graph_demo.py
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: asi_build` | Run `pip install -e .` from the repo root |
| `ImportError: qiskit not found` | `pip install qiskit` or skip `quantum` module |
| Tests slow on first run | Normal — first run builds `.pyc` cache |
| `pytest: command not found` | Install dev extras: `pip install -e ".[dev]"` |
| Memgraph connection refused | Memgraph is optional; `graph_intelligence` works without it in mock mode |

---

## Next Steps

- [[Architecture]] — understand how the modules fit together
- [[Module Index]] — browse all 28 modules
- [[Cognitive Blackboard]] — learn the integration layer API
- [[Contributing]] — ready to contribute? Start here
- [Good First Issues](https://github.com/web3guru888/asi-build/labels/good%20first%20issue) — bite-sized contributions
