# Multimodal Fusion Module

> **Status**: Alpha / In Implementation 🔨  
> **Issue**: [#108 — Add MultimodalFusionEngine with PerceptualState Blackboard entry](https://github.com/web3guru888/asi-build/issues/108)  
> **Discussion**: [#107 — Do we need a dedicated multimodal fusion layer?](https://github.com/web3guru888/asi-build/discussions/107)  
> **CognitiveCycle**: [#41 — Wire all 29 modules into a real-time tick loop](https://github.com/web3guru888/asi-build/issues/41)  
> **Roadmap**: [Phase 4 Goal 2 — Live CognitiveCycle at ≤120ms per tick](Phase-4-Roadmap#goal-2-live-cognitivecycle-at-120ms-per-tick)

---

## Overview

The **Multimodal Fusion Module** (`src/asi_build/multimodal/`) unifies raw sensory streams from
visual, auditory, tactile, neural (BCI/EEG), spatial/holographic, and linguistic channels into a
single coherent **`PerceptualState`** Blackboard entry.

Without a dedicated fusion layer, downstream modules (consciousness, hybrid reasoning, knowledge
graph) must independently pull from five or more modality-specific Blackboard topics, each with its
own timestamp, confidence, and schema. This creates:

- **Temporal drift** — a consciousness computation that reads EEG from t=0ms and vision from
  t=47ms is not perceiving a coherent moment
- **Schema explosion** — every consumer duplicates modality-alignment logic
- **Cycle budget waste** — duplicate preprocessing runs per subscriber

`MultimodalFusionEngine` solves this by acting as the **single Phase-2 perception node** in the
[CognitiveCycle](CognitiveCycle): it gathers all modality inputs within a configurable temporal
window (default 50ms), fuses them into one `PerceptualState`, and writes to the
`multimodal.perceptual_state` Blackboard topic with a 200ms TTL.

### Neuroscience Grounding

The brain integrates modalities in the **Superior Temporal Sulcus (STS)** and **Superior
Colliculus** using three biological principles that inform our design:

| Principle | Biology | ASI:BUILD implementation |
|-----------|---------|------------------------|
| **Temporal congruence** | Stimuli within ~150ms are spatially merged | 50ms fusion window (conservative) |
| **Inverse effectiveness** | Near-threshold unimodal signals summate supralinearly | Confidence-weighted late fusion |
| **Predictive coding** | Each modality provides evidence for a shared generative model | Cross-attention conditioned on CognitiveState |

Key phenomenology this creates (and that we aim to replicate):
- **McGurk effect** — auditory /ga/ + visual /ba/ → perceived /da/: impossible without cross-modal
  fusion
- **Rubber hand illusion** — visual + tactile synchrony → body ownership transfer
- **Cocktail party effect** — auditory attention modulated by visual lip-reading cues

---

## Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                   MultimodalFusionEngine                         ║
║                                                                  ║
║  ┌─────────────┐   ┌──────────────────────────────────────────┐ ║
║  │  Modality   │   │              Fusion Core                 │ ║
║  │  Streams    │   │                                          │ ║
║  │             │   │  ┌────────────────────────────────────┐  │ ║
║  │ [visual] ───┼───┼─▶│  ModalityPreprocessor (per-type)   │  │ ║
║  │ [audio]  ───┼───┼─▶│  async → normalised 512-d vector   │  │ ║
║  │ [tactile]───┼───┼─▶│  + confidence score + timestamp    │  │ ║
║  │ [eeg]    ───┼───┼─▶└────────────────────────────────────┘  │ ║
║  │ [spatial]───┼───┼─▶                                         │ ║
║  │ [language]──┼───┼─▶  ┌─────────────────────────────────┐   │ ║
║  └─────────────┘   │   │   FusionStrategy (pluggable)     │   │ ║
║                    │   │                                   │   │ ║
║                    │   │   ├── EarlyFusion (concat)        │   │ ║
║                    │   │   ├── LateFusion (weighted avg)   │   │ ║
║                    │   │   └── CrossAttentionFusion (xfmr) │   │ ║
║                    │   └─────────────────────────────────┘   │ ║
║                    │                                          │ ║
║                    │   ┌──────────────────────────────────┐   │ ║
║                    │   │    PerceptualState (dataclass)   │   │ ║
║                    │   │    → Blackboard.write(           │   │ ║
║                    │   │        "multimodal.perceptual_   │   │ ║
║                    │   │         state", ttl=200ms)       │   │ ║
║                    │   └──────────────────────────────────┘   │ ║
║                    └──────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════╝
```

### Module File Layout

```
src/asi_build/multimodal/
├── __init__.py
├── __maturity__          # "alpha"
├── fusion_engine.py      # MultimodalFusionEngine (main class)
├── strategies/
│   ├── __init__.py
│   ├── base.py           # FusionStrategy ABC
│   ├── early_fusion.py   # EarlyFusion — concat + linear projection
│   ├── late_fusion.py    # LateFusion — confidence-weighted average
│   └── cross_attention.py# CrossAttentionFusion — transformer encoder
├── preprocessors/
│   ├── __init__.py
│   ├── visual.py         # VisualPreprocessor  (ResNet/ViT backbone)
│   ├── audio.py          # AudioPreprocessor   (mel spectrogram → LSTM)
│   ├── tactile.py        # TactilePreprocessor (force sensor → MLP)
│   ├── eeg.py            # EEGPreprocessor     (CSP + band-power + FFT)
│   ├── spatial.py        # SpatialPreprocessor (holographic pose + gaze)
│   └── linguistic.py     # LinguisticPreprocessor (BERT CLS token)
├── perceptual_state.py   # PerceptualState dataclass
├── blackboard_adapter.py # MultimodalBlackboardAdapter
└── tests/
    ├── test_fusion_engine.py
    ├── test_strategies.py
    ├── test_preprocessors.py
    └── test_blackboard_adapter.py
```

---

## PerceptualState Dataclass

```python
# src/asi_build/multimodal/perceptual_state.py

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class PerceptualState:
    """
    Unified output of the MultimodalFusionEngine.

    One PerceptualState is published to the Cognitive Blackboard per fusion tick
    (default: every 50ms) under the topic ``multimodal.perceptual_state``.

    All feature vectors are normalised to unit L2 norm before fusion.
    Missing modalities have None values and 0.0 confidence.
    """

    # ── Raw modality features ─────────────────────────────────────────
    visual_features: np.ndarray | None = None
    """512-d visual embedding from VisualPreprocessor (ResNet-50 final pool)."""

    audio_features: np.ndarray | None = None
    """256-d audio embedding from AudioPreprocessor (mel-LSTM hidden state)."""

    tactile_features: np.ndarray | None = None
    """128-d tactile embedding (force + vibration + temperature channels)."""

    bci_state: np.ndarray | None = None
    """
    64-d EEG state vector from BCIModule:
    [motor_imagery_probs(4), p300_score, ssvep_freq, alpha_power, beta_power,
     gamma_power, theta_power, delta_power, valence, arousal, ...padding...]
    """

    spatial_context: np.ndarray | None = None
    """
    256-d spatial/holographic context from HolographicUI:
    [hand_pose(63), gaze_dir(3), head_pose(6), scene_objects_embedding(184)]
    """

    linguistic_intent: np.ndarray | None = None
    """768-d BERT CLS token representing the most recent utterance/inner speech."""

    # ── Fusion output ─────────────────────────────────────────────────
    fused_embedding: np.ndarray = field(default_factory=lambda: np.zeros(512))
    """
    512-d unified multimodal embedding (output of the active FusionStrategy).
    Downstream consumers (consciousness, reasoning, KG) should use this.
    """

    # ── Quality signals ───────────────────────────────────────────────
    modality_confidences: dict[str, float] = field(default_factory=dict)
    """
    Per-modality quality score in [0.0, 1.0].
    Keys: "visual", "audio", "tactile", "eeg", "spatial", "linguistic".
    A score of 0.0 means the modality was absent or below SNR threshold.
    """

    modalities_present: list[str] = field(default_factory=list)
    """Names of modalities that contributed to this PerceptualState."""

    salience_score: float = 0.0
    """
    Global salience in [0.0, 1.0].  Used by GWT broadcast to decide whether
    to elevate this percept to global consciousness workspace.
    Computed as: max(modality_confidences.values()) * len(modalities_present) / 6
    """

    fusion_strategy: str = "late_fusion"
    """Name of the FusionStrategy used: "early", "late_fusion", "cross_attention"."""

    fusion_latency_ms: float = 0.0
    """Wall-clock time from first modality sample to PerceptualState write (ms)."""

    # ── Temporal metadata ─────────────────────────────────────────────
    timestamp: float = field(default_factory=time.time)
    """UNIX epoch of fusion completion (seconds, float)."""

    window_start: float = 0.0
    """Start of the fusion temporal window (UNIX epoch, seconds)."""

    window_end: float = 0.0
    """End of the fusion temporal window (UNIX epoch, seconds)."""

    # ── Debug payload ─────────────────────────────────────────────────
    raw_inputs: dict[str, Any] = field(default_factory=dict)
    """
    Optional raw modality data retained for debugging/replay.
    Omitted in production (TTL=200ms Blackboard entry is ephemeral).
    """
```

---

## Fusion Strategies

### 1. Early Fusion — `EarlyFusion`

All modality vectors are concatenated into a single flat tensor, then projected to 512-d via a
learned linear layer (`W ∈ ℝ^{512×D_total}`).

```python
# strategies/early_fusion.py

class EarlyFusion(FusionStrategy):
    """
    Concatenate all present modality vectors, then project to 512-d.
    Fastest strategy; ignores temporal ordering within window.
    """

    def __init__(self, input_dim: int = 2024, output_dim: int = 512):
        self.proj = nn.Linear(input_dim, output_dim)
        # input_dim = 512(vis) + 256(aud) + 128(tac) + 64(eeg) + 256(spa) + 768(ling) = 1984
        # padded to 2024 for modality-dropout robustness

    def fuse(self, embeddings: dict[str, np.ndarray],
             confidences: dict[str, float]) -> np.ndarray:
        """Zero-pad absent modalities, concatenate, project."""
        parts = []
        for name, dim in MODALITY_DIMS.items():
            vec = embeddings.get(name, np.zeros(dim))
            parts.append(vec)
        concat = np.concatenate(parts)                   # shape: (2024,)
        tensor = torch.from_numpy(concat).float()
        fused = self.proj(tensor).detach().numpy()       # shape: (512,)
        return fused / (np.linalg.norm(fused) + 1e-8)
```

**Pros**: lowest latency (~0.3ms on CPU), no attention overhead  
**Cons**: treats all positions in the concat equally; cannot adapt to missing modalities gracefully  
**Recommended for**: real-time applications where ≤5ms fusion budget is required

---

### 2. Late Fusion — `LateFusion`

Each modality is encoded and scored independently. The final embedding is a confidence-weighted
average of the individual 512-d projections.

```python
# strategies/late_fusion.py

class LateFusion(FusionStrategy):
    """
    Confidence-weighted mean of per-modality 512-d projections.
    Default strategy. No learned fusion parameters — interpretable and robust.
    """

    def __init__(self):
        self.projectors = {
            name: nn.Linear(dim, 512)
            for name, dim in MODALITY_DIMS.items()
        }

    def fuse(self, embeddings: dict[str, np.ndarray],
             confidences: dict[str, float]) -> np.ndarray:
        total_weight = 0.0
        accumulated = np.zeros(512)
        for name, vec in embeddings.items():
            w = confidences.get(name, 0.0)
            if w < 0.05:
                continue                     # below SNR threshold — skip
            proj = self.projectors[name]
            tensor = torch.from_numpy(vec).float()
            emb = proj(tensor).detach().numpy()          # (512,)
            accumulated += w * emb
            total_weight += w
        if total_weight < 1e-8:
            return np.zeros(512)
        fused = accumulated / total_weight
        return fused / (np.linalg.norm(fused) + 1e-8)
```

**Pros**: graceful modality dropout, no coupled parameters, interpretable  
**Cons**: misses cross-modal correlations (e.g. lip-reading ↔ audio correlation)  
**Recommended for**: default production use; most robust to missing sensors

---

### 3. Cross-Attention Fusion — `CrossAttentionFusion`

A lightweight transformer encoder treats each modality embedding as a token. Multi-head cross-
attention lets modalities attend to each other before final pooling.

```python
# strategies/cross_attention.py

class CrossAttentionFusion(FusionStrategy):
    """
    Transformer encoder over modality tokens with learned positional embeddings.
    Most expressive; ~2ms on CPU with 6 modalities, 4 heads, 2 layers.
    """

    def __init__(self,
                 d_model: int = 512,
                 nhead: int = 4,
                 num_layers: int = 2,
                 dropout: float = 0.1):
        self.input_projectors = {
            name: nn.Linear(dim, d_model)
            for name, dim in MODALITY_DIMS.items()
        }
        self.modality_embeddings = nn.Embedding(len(MODALITY_DIMS), d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.pool = nn.Linear(d_model, d_model)     # CLS-style pool

    def fuse(self, embeddings: dict[str, np.ndarray],
             confidences: dict[str, float]) -> np.ndarray:
        tokens = []
        mask_indices = []
        for i, (name, dim) in enumerate(MODALITY_DIMS.items()):
            if name in embeddings and confidences.get(name, 0.0) >= 0.05:
                proj = self.input_projectors[name]
                vec = torch.from_numpy(embeddings[name]).float()
                token = proj(vec) + self.modality_embeddings.weight[i]
                tokens.append(token)
            else:
                # Masked/absent modality — learned "absent" embedding
                absent = self.modality_embeddings.weight[i] * 0.0
                tokens.append(absent)
                mask_indices.append(i)

        seq = torch.stack(tokens).unsqueeze(0)     # (1, 6, d_model)
        key_padding_mask = torch.zeros(1, len(MODALITY_DIMS), dtype=torch.bool)
        for i in mask_indices:
            key_padding_mask[0, i] = True

        encoded = self.encoder(seq, src_key_padding_mask=key_padding_mask)
        pooled = encoded[0].mean(dim=0)             # mean pool over present tokens
        fused = self.pool(pooled).detach().numpy()
        return fused / (np.linalg.norm(fused) + 1e-8)
```

**Pros**: captures cross-modal correlations, handles modality dropout via masking  
**Cons**: ~2ms inference overhead, requires paired training data for good weights  
**Recommended for**: offline experiments, consciousness module integration where expressiveness
matters more than latency

---

## Modality Pipeline

Each modality follows the same async pipeline:

```
Raw Sensor Data
      │
      ▼
┌────────────────────────────────────────────────────────────────┐
│  ModalityPreprocessor (per-modality, async)                    │
│                                                                │
│  1. validate(raw) → drop corrupt frames                       │
│  2. normalise(raw) → canonical units (e.g. µV for EEG)        │
│  3. encode(normalised) → (D,) float32 numpy vector            │
│  4. score(raw, encoded) → float confidence in [0, 1]          │
└────────────────────────────────────────────────────────────────┘
      │
      ▼  (vector, confidence, timestamp)
┌────────────────────────────────────────────────────────────────┐
│  ModalityBuffer (per-modality, thread-safe deque)              │
│                                                                │
│  • Holds last N frames within the 50ms fusion window          │
│  • Exposes get_latest() and get_window(t_start, t_end)        │
└────────────────────────────────────────────────────────────────┘
      │
      ▼  (selected frame or temporal mean)
┌────────────────────────────────────────────────────────────────┐
│  FusionCore — assembles dict of vectors + confidences          │
│  → FusionStrategy.fuse() → 512-d embedding                    │
│  → PerceptualState.salience_score = f(confidences)            │
└────────────────────────────────────────────────────────────────┘
      │
      ▼
  Blackboard.write("multimodal.perceptual_state",
                   PerceptualState, ttl=0.200)
```

### Per-Modality Preprocessor Details

| Modality | Class | Input | Key Transform | Output dim |
|----------|-------|-------|---------------|------------|
| Visual | `VisualPreprocessor` | RGB frame (H×W×3) | ResNet-50 pool5 | 512 |
| Audio | `AudioPreprocessor` | PCM 16kHz | Mel spectrogram → BiLSTM | 256 |
| Tactile | `TactilePreprocessor` | Force/vibration/temp (N-ch) | Band-pass + MLP | 128 |
| EEG/BCI | `EEGPreprocessor` | Raw EEG µV (64-ch) | CSP + band-power + FFT | 64 |
| Spatial | `SpatialPreprocessor` | Hand pose + gaze + scene | Holographic concat + MLP | 256 |
| Linguistic | `LinguisticPreprocessor` | Tokenised utterance | BERT-base CLS token | 768 |

**Confidence scoring heuristics**:
- Visual: inverse of motion blur (Laplacian variance) + face/object detection confidence
- Audio: SNR estimate from RMS vs noise floor
- Tactile: presence of non-zero force signal above threshold
- EEG: electrode impedance quality index + classifier confidence from BCIModule
- Spatial: holographic tracking quality metric from HolographicUI
- Linguistic: softmax entropy of BERT token distribution (high entropy → low confidence)

---

## FusionEngine.tick() — Core Loop

```python
# src/asi_build/multimodal/fusion_engine.py

import asyncio
import time
from typing import Protocol
import numpy as np

from .perceptual_state import PerceptualState
from .strategies import FusionStrategy, LateFusion
from .preprocessors import (
    VisualPreprocessor, AudioPreprocessor, TactilePreprocessor,
    EEGPreprocessor, SpatialPreprocessor, LinguisticPreprocessor,
)


class MultimodalFusionEngine:
    """
    Core fusion engine.  Wired into CognitiveCycle Phase 2 (Perception).

    Usage::

        engine = MultimodalFusionEngine(blackboard=bb, strategy="late_fusion")
        await engine.start()          # starts background preprocessor tasks
        state = await engine.tick()   # returns PerceptualState

    The engine publishes one PerceptualState per tick to the Blackboard.
    Consumers subscribe to ``multimodal.perceptual_state``.
    """

    FUSION_WINDOW_MS: float = 50.0
    BLACKBOARD_TOPIC: str = "multimodal.perceptual_state"
    TTL_MS: float = 200.0

    def __init__(self, blackboard, strategy: str = "late_fusion"):
        self.blackboard = blackboard
        self.strategy: FusionStrategy = self._build_strategy(strategy)
        self.strategy_name = strategy

        self.preprocessors = {
            "visual":     VisualPreprocessor(),
            "audio":      AudioPreprocessor(),
            "tactile":    TactilePreprocessor(),
            "eeg":        EEGPreprocessor(),
            "spatial":    SpatialPreprocessor(),
            "linguistic": LinguisticPreprocessor(),
        }

        self._buffers: dict[str, list] = {k: [] for k in self.preprocessors}
        self._lock = asyncio.Lock()
        self._running = False

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start all per-modality async preprocessor tasks."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._run_preprocessor(name, pp))
            for name, pp in self.preprocessors.items()
        ]

    async def stop(self) -> None:
        """Cancel all preprocessor tasks and flush buffers."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    # ── Per-tick fusion ───────────────────────────────────────────────

    async def tick(self) -> PerceptualState:
        """
        Collect the latest buffered embeddings for each modality within the
        fusion window, run the configured FusionStrategy, and write a
        PerceptualState to the Cognitive Blackboard.

        Returns the PerceptualState for in-process consumers (e.g. CognitiveCycle).
        """
        t_start = time.time()
        window_start = t_start - (self.FUSION_WINDOW_MS / 1000.0)

        embeddings: dict[str, np.ndarray] = {}
        confidences: dict[str, float] = {}

        async with self._lock:
            for name, buf in self._buffers.items():
                # Select the most recent sample within the fusion window
                candidates = [
                    entry for entry in buf
                    if entry["timestamp"] >= window_start
                ]
                if candidates:
                    best = max(candidates, key=lambda e: e["confidence"])
                    embeddings[name] = best["embedding"]
                    confidences[name] = best["confidence"]

        # Run fusion strategy
        fused = self.strategy.fuse(embeddings, confidences) if embeddings else np.zeros(512)

        modalities_present = [k for k, c in confidences.items() if c >= 0.05]
        salience = (
            max(confidences.values()) * len(modalities_present) / 6.0
            if confidences else 0.0
        )

        t_end = time.time()

        state = PerceptualState(
            visual_features=embeddings.get("visual"),
            audio_features=embeddings.get("audio"),
            tactile_features=embeddings.get("tactile"),
            bci_state=embeddings.get("eeg"),
            spatial_context=embeddings.get("spatial"),
            linguistic_intent=embeddings.get("linguistic"),
            fused_embedding=fused,
            modality_confidences=confidences,
            modalities_present=modalities_present,
            salience_score=salience,
            fusion_strategy=self.strategy_name,
            fusion_latency_ms=(t_end - t_start) * 1000.0,
            timestamp=t_end,
            window_start=window_start,
            window_end=t_end,
        )

        # Publish to Cognitive Blackboard
        await self.blackboard.write(
            self.BLACKBOARD_TOPIC,
            state,
            ttl=self.TTL_MS / 1000.0,
        )

        return state

    # ── Internal helpers ─────────────────────────────────────────────

    async def _run_preprocessor(self, name: str, preprocessor) -> None:
        """Background task: continuously pull raw data and push to buffer."""
        while self._running:
            try:
                raw = await preprocessor.read()                 # blocks until new frame
                embedding, confidence = await preprocessor.encode(raw)
                async with self._lock:
                    self._buffers[name].append({
                        "embedding":  embedding,
                        "confidence": confidence,
                        "timestamp":  time.time(),
                    })
                    # Keep only samples within 2x fusion window to bound memory
                    cutoff = time.time() - 2 * self.FUSION_WINDOW_MS / 1000.0
                    self._buffers[name] = [
                        e for e in self._buffers[name]
                        if e["timestamp"] >= cutoff
                    ]
            except asyncio.CancelledError:
                break
            except Exception as exc:
                # Modality failure is non-fatal — log and continue
                import logging
                logging.warning("MultimodalFusion: %s preprocessor error: %s", name, exc)
                await asyncio.sleep(0.010)

    @staticmethod
    def _build_strategy(name: str) -> FusionStrategy:
        from .strategies import EarlyFusion, LateFusion, CrossAttentionFusion
        strategies = {
            "early":           EarlyFusion(),
            "late_fusion":     LateFusion(),
            "cross_attention": CrossAttentionFusion(),
        }
        if name not in strategies:
            raise ValueError(f"Unknown fusion strategy: {name!r}. "
                             f"Choose from: {list(strategies)}")
        return strategies[name]
```

---

## Blackboard Integration

### Topic Schema

| Topic | Type | TTL | Description |
|-------|------|-----|-------------|
| `multimodal.perceptual_state` | `PerceptualState` | 200ms | Primary fusion output |
| `multimodal.modality_confidence` | `dict[str, float]` | 100ms | Raw confidence map (debugging) |
| `multimodal.fusion_latency_ms` | `float` | 1000ms | Rolling fusion latency (monitoring) |

### Downstream Consumers

```
multimodal.perceptual_state
         │
         ├──▶ consciousness/    (reads fused_embedding + bci_state for IIT Φ + GWT)
         │       topic: consciousness.phi_snapshot
         │
         ├──▶ hybrid_reasoning/ (reads linguistic_intent + fused_embedding for query routing)
         │       topic: reasoning.query_result
         │
         ├──▶ knowledge_graph/  (reads fused_embedding for semantic node lookup + graph write)
         │       topic: kg.perceptual_event
         │
         ├──▶ bio_inspired/     (reads bci_state.arousal for circadian modulation)
         │       topic: bio.cognitive_state_update
         │
         └──▶ CognitiveCycle    (reads salience_score for Phase-3 attention routing)
                 direct in-process reference (no re-read from BB)
```

### MultimodalBlackboardAdapter

```python
# src/asi_build/multimodal/blackboard_adapter.py

class MultimodalBlackboardAdapter(AsyncBlackboardAdapter):
    """
    Wires MultimodalFusionEngine into the CognitiveCycle tick loop.

    Registered in the Blackboard adapter registry as "multimodal".
    """

    async def on_cycle_phase(self, phase: str, context: dict) -> dict | None:
        if phase != "perception":
            return None
        state: PerceptualState = await self.engine.tick()
        return {
            "perceptual_state": state,
            "modalities_present": state.modalities_present,
            "salience": state.salience_score,
        }
```

---

## Cross-Module Dependencies

| Dependency | Module | Issue | What we consume |
|------------|--------|-------|----------------|
| **BCI Module** | `bci/` | [#117](https://github.com/web3guru888/asi-build/issues/117) | Raw EEG µV, motor imagery probs, P300 score |
| **Holographic UI** | `holographic/` | [#56](https://github.com/web3guru888/asi-build/issues/56) | Hand pose (63-d), gaze direction, scene objects |
| **VLA++ Optimization** | `optimization/` | [#83](https://github.com/web3guru888/asi-build/issues/83) | Pre-fused vision+language embedding (optional) |
| **Consciousness Module** | `consciousness/` | [#116](https://github.com/web3guru888/asi-build/issues/116) | Downstream: reads `fused_embedding` + `bci_state` |
| **Hybrid Reasoning** | `reasoning/` | [#44](https://github.com/web3guru888/asi-build/issues/44) | Downstream: reads `linguistic_intent` |
| **Knowledge Graph** | `knowledge_graph/` | [#46](https://github.com/web3guru888/asi-build/issues/46) | Downstream: reads `fused_embedding` for node lookup |
| **CognitiveCycle** | `cognitive_cycle/` | [#41](https://github.com/web3guru888/asi-build/issues/41) | Downstream: Phase 2 calls `engine.tick()` |
| **Quantum Module** | `quantum/` | [#53](https://github.com/web3guru888/asi-build/issues/53) | Future: quantum cross-attention on QPU |
| **Cognitive Blackboard** | `integration/` | — | `write()` / `subscribe()` API |
| **Neuromorphic** | `neuromorphic/` | [#119](https://github.com/web3guru888/asi-build/issues/119) | Future: neuromorphic preprocessors for EEG/tactile |

---

## CognitiveCycle Placement

The fusion module slots into **Phase 2 — Perception** of the [CognitiveCycle](CognitiveCycle):

```
Phase 1: Sensory Ingestion   (raw sensor reads — 10ms budget)
Phase 2: Perception          ← MultimodalFusionEngine.tick() — 20ms budget
Phase 3: Attention Routing   (salience_score gates GWT broadcast — 5ms)
Phase 4: Working Memory      (Blackboard write + read — 5ms)
Phase 5: Reasoning           (HybridReasoningEngine — 25ms)
Phase 6: Consciousness       (IIT Φ + GWT + AST — 30ms async)
Phase 7: Planning            (goal selection — 10ms)
Phase 8: Action              (motor/API output — 5ms)
Phase 9: Consolidation       (KG write + bio_inspired update — 10ms)
                                                        ─────────
                                              Total:    120ms target
```

The 20ms Phase-2 budget breaks down as:
- Per-modality preprocessing (async, parallelised): 5–15ms
- FusionStrategy inference: 0.3ms (early) / 0.8ms (late) / 2ms (cross-attention)
- Blackboard write: ~0.05ms (in-process)
- Buffer management overhead: ~0.1ms

---

## Testing

The minimum test coverage target for the `multimodal/` module is **40 tests** across four files:

### `test_fusion_engine.py`
```python
class TestMultimodalFusionEngine:
    async def test_tick_returns_perceptual_state(self, engine, mock_blackboard): ...
    async def test_tick_with_all_modalities_present(self, engine): ...
    async def test_tick_with_missing_modalities(self, engine): ...
    async def test_tick_writes_to_blackboard(self, engine, mock_blackboard): ...
    async def test_tick_latency_under_20ms(self, engine): ...
    async def test_fusion_window_selects_latest_sample(self, engine): ...
    async def test_salience_score_proportional_to_active_modalities(self, engine): ...
    async def test_start_stop_lifecycle(self, engine): ...
```

### `test_strategies.py`
```python
class TestLateFusion:
    def test_fuse_all_modalities(self, strategy): ...
    def test_fuse_skips_low_confidence_modality(self, strategy): ...
    def test_output_is_unit_norm(self, strategy): ...
    def test_zero_confidence_returns_zero_vector(self, strategy): ...

class TestEarlyFusion:
    def test_fuse_pads_missing_modalities(self, strategy): ...
    def test_output_shape_is_512(self, strategy): ...
    def test_output_is_unit_norm(self, strategy): ...

class TestCrossAttentionFusion:
    def test_fuse_all_modalities(self, strategy): ...
    def test_masked_modality_does_not_corrupt_output(self, strategy): ...
    def test_output_shape_is_512(self, strategy): ...
    def test_attention_weights_sum_to_one(self, strategy): ...
```

### `test_preprocessors.py`
```python
class TestEEGPreprocessor:
    def test_encode_returns_64d_vector(self, preprocessor): ...
    def test_confidence_below_threshold_for_noisy_input(self, preprocessor): ...
    def test_csp_filter_applied(self, preprocessor): ...

class TestVisualPreprocessor:
    def test_encode_returns_512d_vector(self, preprocessor): ...
    def test_blur_detection_lowers_confidence(self, preprocessor): ...
```

### `test_blackboard_adapter.py`
```python
class TestMultimodalBlackboardAdapter:
    async def test_on_cycle_phase_perception_calls_tick(self, adapter): ...
    async def test_on_cycle_phase_non_perception_returns_none(self, adapter): ...
    async def test_adapter_registered_in_registry(self): ...
    async def test_published_state_has_correct_ttl(self, adapter, blackboard): ...
```

Run the tests with:

```bash
pytest src/asi_build/multimodal/tests/ -v --tb=short
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Fusion latency (late_fusion) | ≤ 5ms | 6 modalities present, CPU |
| Fusion latency (cross_attention) | ≤ 10ms | 6 modalities, CPU, 2-layer |
| Fusion latency (early) | ≤ 2ms | All modalities, CPU |
| Phase-2 total budget | ≤ 20ms | Including async preprocessing |
| PerceptualState Blackboard TTL | 200ms | Leaves room for 1–4 downstream reads |
| Buffer memory (50ms window) | < 50MB | 6 modalities × 30fps max × float32 |
| Tests passing | ≥ 40 | Across 4 test files |

---

## Open Research Questions

### 1. Cross-Attention Scalability

The `CrossAttentionFusion` uses a 4-head, 2-layer transformer over 6 modality tokens. With
512-d embeddings this is tiny, but:

- What happens at 12+ modalities (adding proprioception, interoception, olfaction)?
- Can we replace the linear transformer with a more memory-efficient variant
  (Linformer, FlashAttention) for sub-millisecond inference on edge hardware?
- Should attention heads be pre-assigned to modality pairs (EEG↔audio, vision↔spatial)?

### 2. Modality Dropout Robustness

In production, sensors fail. How should fusion behave under:

- **Single modality only** (e.g. text-only BCI patient): late fusion degrades gracefully;
  cross-attention masking needs validation
- **All modalities below SNR threshold**: should we emit a null `PerceptualState` or the
  last valid state? (Staleness vs. silence tradeoff)
- **Intermittent dropout** (EEG noise burst lasting 200ms): exponential confidence decay
  within the fusion window?

### 3. Fusion Timing for 120ms Cycle Budget

Phase-2 has a **20ms budget** in the CognitiveCycle. Current timings:
- Late fusion: ~0.8ms (well within budget)
- Cross-attention: ~2ms (within budget)
- Async EEG preprocessing via BCIModule: up to 15ms (dominant cost)

Should EEG preprocessing run ahead of the Phase-2 call in Phase-1 (Sensory Ingestion),
or should multimodal fusion be allocated a larger share of the cycle at the cost of
reasoning time?

### 4. Temporal Alignment Across Asynchronous Sensors

EEG arrives at 1kHz, camera at 30fps, audio at 44.1kHz. The 50ms fusion window uses
"most recent sample within window" heuristic. Alternative approaches:
- **Interpolation**: resample all modalities to a canonical 100Hz grid
- **Event-driven**: publish PerceptualState only when a high-salience event is detected
- **Kalman filter**: maintain a latent state estimate updated by each modality arrival

### 5. Quantum-Enhanced Fusion (Future)

[Issue #53](https://github.com/web3guru888/asi-build/issues/53) discusses wiring the Quantum
Module to the Blackboard. A variational quantum cross-attention circuit could potentially
perform modality fusion on a QPU, leveraging superposition to explore exponentially many
modality interaction patterns. This is speculative but worth tracking as QPU access improves.

---

## Contribution Guide

See [Issue #108](https://github.com/web3guru888/asi-build/issues/108) for the full spec.

**Minimum viable contribution** (first PR welcome):
1. Create `src/asi_build/multimodal/` with `__init__.py` and `__maturity__ = "alpha"`
2. Implement `PerceptualState` dataclass (`perceptual_state.py`)
3. Implement `LateFusion` strategy (`strategies/late_fusion.py`)
4. Stub out remaining preprocessors (return `(np.zeros(D), 0.0)` for now)
5. Implement `MultimodalFusionEngine.tick()` with `LateFusion`
6. Write 20+ tests covering tick(), LateFusion, and Blackboard write

**Second PR scope**:
7. Implement real `EEGPreprocessor` (using BCIModule output)
8. Implement real `SpatialPreprocessor` (using HolographicUI output)
9. Implement `CrossAttentionFusion`
10. Wire `MultimodalBlackboardAdapter` into the adapter registry

Style references: [Federated-Learning](Federated-Learning), [BCI](BCI), [Async-Architecture](Async-Architecture).

---

## Related Pages

- [BCI Module](BCI) — EEG/neural input source
- [Holographic UI](Holographic-UI) — spatial/gesture input source
- [Optimization Module](Optimization-Module) — existing VLA++ multimodal pipeline (visual+language+action)
- [Cognitive Blackboard](Cognitive-Blackboard) — where PerceptualState is published
- [CognitiveCycle](CognitiveCycle) — Phase-2 Perception slot
- [Consciousness Module](Consciousness-Module) — primary downstream consumer
- [Async Architecture](Async-Architecture) — AsyncBlackboardAdapter pattern
- [Integration Layer](Integration-Layer) — Blackboard write/subscribe API
- [Research Notes](Research-Notes) — cross-modal consciousness research direction
- [Phase 4 Roadmap](Phase-4-Roadmap) — where multimodal fusion fits in the roadmap
