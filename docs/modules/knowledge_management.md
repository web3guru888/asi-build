# Knowledge Management

> **Maturity**: `alpha` · **Adapter**: `KnowledgeManagementAdapter`

Knowledge engine for predictive synthesis, contextual learning, and knowledge consolidation. Provides utilities for managing the lifecycle of knowledge artifacts — from initial acquisition through synthesis, contextualization, and long-term consolidation.

Uses a dynamic auto-import pattern that loads all callables from sibling Python files at import time.

## Key Classes

| Class | Description |
|-------|-------------|
| `KnowledgeEngine` | Core knowledge lifecycle management |
| `PredictiveSynthesizer` | Predictive knowledge synthesis from multiple sources |
| `ContextualLearner` | Context-aware knowledge acquisition |
| `KnowledgeConsolidator` | Long-term knowledge consolidation and pruning |

## Example Usage

```python
from asi_build.knowledge_management import KnowledgeEngine
engine = KnowledgeEngine()
engine.ingest("solar_physics", source="arxiv", confidence=0.85)
synthesis = engine.synthesize(domain="astrophysics", method="predictive")
```

## Blackboard Integration

KnowledgeManagementAdapter publishes synthesized knowledge, consolidation events, and learning progress; consumes knowledge graph triples and discovery results for contextual learning.
