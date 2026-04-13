# Phase 19.4 — MultiModalEncoder

> **Spec issue:** [#475](https://github.com/web3guru888/asi-build/issues/475) &nbsp;|&nbsp; **Show & Tell:** [#477](https://github.com/web3guru888/asi-build/discussions/477) &nbsp;|&nbsp; **Q&A:** [#478](https://github.com/web3guru888/asi-build/discussions/478)

**Maps heterogeneous inputs (text, images, audio, video, structured data) into a shared embedding space via modality-specific encoders and cross-modal attention fusion.**

| Field | Value |
|---|---|
| **Sub-phase** | 19.4 |
| **Component** | `MultiModalEncoder` |
| **Depends on** | Phase 19.1 SemanticParser (#466), Phase 13.1 WorldModel (#368) |
| **Blocking** | Phase 19.5 CommunicationOrchestrator |
| **Estimated tests** | 12 |

---

## Problem

ASI-Build's cognitive pipeline currently assumes single-modality text streams. Real-world autonomous agents receive **heterogeneous sensory inputs** — natural language instructions, camera frames, audio signals, structured telemetry, and video feeds — often simultaneously. Without a unified embedding space, downstream modules must maintain separate encoding logic for each modality, cross-modal similarity becomes impossible, and the WorldModel (13.1) cannot fuse multi-sensory observations into a coherent state representation.

## Solution

`MultiModalEncoder` provides a modality-agnostic encoding gateway. Each input is routed to a modality-specific backend encoder, and the resulting per-modality vectors are fused into a single `MultiModalEmbedding` via a configurable `FusionStrategy` (concatenation, cross-modal attention, average, or weighted sum). Downstream consumers receive a fixed-dimension vector regardless of which modalities were present, enabling unified similarity search, clustering, and retrieval across the entire sensory surface.

---

## Public API

### 1. `Modality` Enum

```python
from enum import Enum, auto

class Modality(Enum):
    """Supported input modalities."""
    TEXT       = auto()  # Natural language strings / tokenised text
    IMAGE      = auto()  # Raster image data (PNG, JPEG, WebP)
    AUDIO      = auto()  # Waveform / compressed audio (WAV, MP3, FLAC)
    VIDEO      = auto()  # Sequential frames with optional audio track
    STRUCTURED = auto()  # JSON / tabular / key-value telemetry
```

| Modality | Typical MIME types | Backend default | Embedding strategy |
|---|---|---|---|
| `TEXT` | `text/plain`, `text/markdown` | `TRANSFORMER` | Token-level contextual embeddings → [CLS] pooling |
| `IMAGE` | `image/png`, `image/jpeg` | `CNN` | Spatial feature map → global average pooling |
| `AUDIO` | `audio/wav`, `audio/flac` | `SPECTROGRAM` | Mel-spectrogram → 1-D CNN → temporal pooling |
| `VIDEO` | `video/mp4`, `video/webm` | `HYBRID` | Key-frame CNN + temporal attention across frames |
| `STRUCTURED` | `application/json` | `SIMPLE_HASH` | Schema-aware feature hashing → dense projection |

### 2. `EncoderBackend` Enum

```python
class EncoderBackend(Enum):
    """Backend implementation for a single-modality encoder."""
    SIMPLE_HASH   = auto()  # Deterministic feature hash (fast, low quality)
    TRANSFORMER   = auto()  # Attention-based contextual encoder
    CNN           = auto()  # Convolutional feature extractor
    SPECTROGRAM   = auto()  # Mel-spectrogram + 1-D convolution
    HYBRID        = auto()  # Combines multiple backends (e.g. CNN + temporal attention)
```

| Backend | Latency | Quality | GPU required | Best for |
|---|---|---|---|---|
| `SIMPLE_HASH` | ~0.1 ms | Low | No | Structured data, tests, fallback |
| `TRANSFORMER` | ~5 ms | High | Recommended | Text, rich context |
| `CNN` | ~3 ms | High | Recommended | Images, video key-frames |
| `SPECTROGRAM` | ~4 ms | Medium-High | Optional | Audio waveforms |
| `HYBRID` | ~10 ms | Highest | Yes | Video, multi-stream |

### 3. `FusionStrategy` Enum

```python
class FusionStrategy(Enum):
    """Strategy for fusing per-modality embeddings into a single vector."""
    CONCATENATE  = auto()  # Stack vectors → linear projection to target dim
    ATTENTION    = auto()  # Cross-modal multi-head attention → pooled output
    AVERAGE      = auto()  # Element-wise mean of aligned vectors
    WEIGHTED_SUM = auto()  # Learnable per-modality scalar weights → sum
```

| Strategy | Preserves modality detail | Parameter count | Cross-modal interaction | Use case |
|---|---|---|---|---|
| `CONCATENATE` | ✅ High | O(k × d × d) projection | None (post-hoc) | Low-latency, when modalities are independent |
| `ATTENTION` | ✅ High | O(d² × heads) | ✅ Full pairwise | Default — best quality, captures cross-modal correlations |
| `AVERAGE` | ⚠️ Medium | 0 | None | Baseline, no learnable parameters |
| `WEIGHTED_SUM` | ⚠️ Medium | O(k) scalars | Implicit via weights | When modality importance is known a priori |

### 4. `ModalityInput` Frozen Dataclass

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Union

@dataclass(frozen=True, slots=True)
class ModalityInput:
    """Single-modality input payload."""
    modality: Modality
    data: bytes | str                          # Raw bytes or text string
    mime_type: str = "application/octet-stream" # Content type hint
    metadata: dict[str, str] = field(default_factory=dict)  # Arbitrary k/v tags
```

### 5. `MultiModalEmbedding` Frozen Dataclass

```python
import time

@dataclass(frozen=True, slots=True)
class MultiModalEmbedding:
    """Fused embedding vector spanning one or more modalities."""
    vector: tuple[float, ...]                      # The embedding itself
    modality_weights: dict[Modality, float]         # Per-modality contribution [0.0, 1.0]
    source_modalities: frozenset[Modality]          # Which modalities contributed
    dimension: int                                  # len(vector), redundant for validation
    timestamp_ns: int = field(default_factory=time.time_ns)
    norm: float = 0.0                               # L2 norm (set post-init)

    def __post_init__(self) -> None:
        import math
        object.__setattr__(self, "norm", math.sqrt(sum(x * x for x in self.vector)))
        assert self.dimension == len(self.vector), "dimension / vector length mismatch"
```

### 6. `EncoderConfig` Frozen Dataclass

```python
@dataclass(frozen=True, slots=True)
class EncoderConfig:
    """Configuration for MultiModalEncoder."""
    embedding_dim: int = 256                           # Output vector dimensionality
    fusion_strategy: FusionStrategy = FusionStrategy.ATTENTION
    backends: dict[Modality, EncoderBackend] = field(default_factory=lambda: {
        Modality.TEXT:       EncoderBackend.TRANSFORMER,
        Modality.IMAGE:      EncoderBackend.CNN,
        Modality.AUDIO:      EncoderBackend.SPECTROGRAM,
        Modality.VIDEO:      EncoderBackend.HYBRID,
        Modality.STRUCTURED: EncoderBackend.SIMPLE_HASH,
    })
    normalize: bool = True                             # L2-normalize output vectors
    max_input_bytes: int = 10 * 1024 * 1024            # 10 MiB per modality input
```

---

### 7. `MultiModalEncoder` Protocol

```python
from typing import Protocol, runtime_checkable, Sequence

@runtime_checkable
class MultiModalEncoder(Protocol):
    """Encode heterogeneous inputs into a shared embedding space."""

    async def encode(
        self,
        inputs: Sequence[ModalityInput],
    ) -> MultiModalEmbedding:
        """Encode one or more modality inputs into a fused embedding."""
        ...

    async def encode_text(self, text: str) -> MultiModalEmbedding:
        """Convenience: encode a single text string."""
        ...

    async def encode_image(self, data: bytes, mime_type: str = "image/png") -> MultiModalEmbedding:
        """Convenience: encode a single image."""
        ...

    async def similarity(
        self,
        a: MultiModalEmbedding,
        b: MultiModalEmbedding,
    ) -> float:
        """Cosine similarity in [-1.0, 1.0] between two embeddings."""
        ...

    def supported_modalities(self) -> frozenset[Modality]:
        """Return the set of modalities this encoder can handle."""
        ...
```

---

## Implementation: `SimpleMultiModalEncoder`

```python
import asyncio
import hashlib
import math
import struct
from typing import Sequence

class InputTooLargeError(ValueError):
    """Raised when a ModalityInput exceeds max_input_bytes."""

class SimpleMultiModalEncoder:
    """Reference implementation — CPU-only, no ML dependencies."""

    def __init__(self, config: EncoderConfig | None = None) -> None:
        self._config = config or EncoderConfig()
        self._lock = asyncio.Lock()
        self._encode_dispatch: dict[Modality, callable] = {
            Modality.TEXT:       self._encode_text,
            Modality.IMAGE:      self._encode_image,
            Modality.AUDIO:      self._encode_audio,
            Modality.VIDEO:      self._encode_video,
            Modality.STRUCTURED: self._encode_structured,
        }

    # ── per-modality encoders ──────────────────────────────

    def _encode_text(self, data: bytes | str) -> list[float]:
        """Hash-based text encoding: SHA-256 → deterministic float vector."""
        raw = data.encode("utf-8") if isinstance(data, str) else data
        return self._hash_to_vector(raw)

    def _encode_image(self, data: bytes | str) -> list[float]:
        """Pixel-statistics encoding: chunk bytes → mean/variance features."""
        raw = data if isinstance(data, bytes) else data.encode("utf-8")
        dim = self._config.embedding_dim
        chunk_size = max(1, len(raw) // dim)
        vec: list[float] = []
        for i in range(dim):
            chunk = raw[i * chunk_size : (i + 1) * chunk_size]
            if chunk:
                mean_val = sum(chunk) / len(chunk) / 255.0
                vec.append(mean_val)
            else:
                vec.append(0.0)
        return vec

    def _encode_audio(self, data: bytes | str) -> list[float]:
        """Spectral-feature encoding: byte-level frequency analysis."""
        raw = data if isinstance(data, bytes) else data.encode("utf-8")
        # Simple spectral: sliding DFT-like bucketing over byte stream
        dim = self._config.embedding_dim
        vec = [0.0] * dim
        for i, b in enumerate(raw):
            vec[i % dim] += float(b) / 255.0
        total = sum(abs(v) for v in vec) or 1.0
        return [v / total for v in vec]

    def _encode_video(self, data: bytes | str) -> list[float]:
        """Hybrid: treat as image + temporal hash blend."""
        raw = data if isinstance(data, bytes) else data.encode("utf-8")
        img_vec = self._encode_image(raw)
        hash_vec = self._hash_to_vector(raw)
        return [(a + b) / 2.0 for a, b in zip(img_vec, hash_vec)]

    def _encode_structured(self, data: bytes | str) -> list[float]:
        """Schema-aware hash: JSON string → deterministic vector."""
        raw = data.encode("utf-8") if isinstance(data, str) else data
        return self._hash_to_vector(raw)

    # ── fusion layer ───────────────────────────────────────

    def _fuse(
        self,
        per_modality: dict[Modality, list[float]],
    ) -> tuple[list[float], dict[Modality, float]]:
        """Fuse per-modality vectors into a single embedding."""
        strategy = self._config.fusion_strategy
        k = len(per_modality)
        dim = self._config.embedding_dim
        modalities = list(per_modality.keys())
        vectors = [per_modality[m] for m in modalities]

        if strategy == FusionStrategy.AVERAGE:
            fused = [sum(vectors[j][i] for j in range(k)) / k for i in range(dim)]
            weights = {m: 1.0 / k for m in modalities}

        elif strategy == FusionStrategy.CONCATENATE:
            # Concatenate then project down via deterministic hash-based projection
            concat = []
            for v in vectors:
                concat.extend(v)
            # Simple linear projection: take every k-th element
            fused = [concat[i * k % len(concat)] for i in range(dim)]
            weights = {m: 1.0 / k for m in modalities}

        elif strategy == FusionStrategy.WEIGHTED_SUM:
            # Norm-based weighting: higher norm → higher weight
            norms = {m: math.sqrt(sum(x * x for x in per_modality[m])) or 1e-9
                     for m in modalities}
            total_norm = sum(norms.values())
            weights = {m: norms[m] / total_norm for m in modalities}
            fused = [0.0] * dim
            for m in modalities:
                w = weights[m]
                for i in range(dim):
                    fused[i] += w * per_modality[m][i]

        else:  # ATTENTION (default)
            # Cross-modal attention: dot-product attention across modality pairs
            # Compute attention scores as pairwise cosine similarities
            attn_scores: dict[Modality, float] = {}
            for m in modalities:
                score = 0.0
                for m2 in modalities:
                    if m2 != m:
                        dot = sum(a * b for a, b in zip(per_modality[m], per_modality[m2]))
                        score += dot
                attn_scores[m] = math.exp(score / math.sqrt(dim))
            total_attn = sum(attn_scores.values()) or 1.0
            weights = {m: attn_scores[m] / total_attn for m in modalities}
            fused = [0.0] * dim
            for m in modalities:
                w = weights[m]
                for i in range(dim):
                    fused[i] += w * per_modality[m][i]

        # L2 normalize if configured
        if self._config.normalize:
            norm = math.sqrt(sum(x * x for x in fused)) or 1e-9
            fused = [x / norm for x in fused]

        return fused, weights

    # ── public interface ───────────────────────────────────

    async def encode(self, inputs: Sequence[ModalityInput]) -> MultiModalEmbedding:
        async with self._lock:
            per_modality: dict[Modality, list[float]] = {}
            for inp in inputs:
                raw = inp.data if isinstance(inp.data, bytes) else inp.data.encode("utf-8")
                if len(raw) > self._config.max_input_bytes:
                    raise InputTooLargeError(
                        f"{inp.modality.name} input {len(raw)} bytes > "
                        f"max {self._config.max_input_bytes}"
                    )
                encoder_fn = self._encode_dispatch.get(inp.modality)
                if encoder_fn is None:
                    raise ValueError(f"Unsupported modality: {inp.modality}")
                per_modality[inp.modality] = encoder_fn(inp.data)

            fused, weights = self._fuse(per_modality)
            return MultiModalEmbedding(
                vector=tuple(fused),
                modality_weights=weights,
                source_modalities=frozenset(per_modality.keys()),
                dimension=self._config.embedding_dim,
            )

    async def encode_text(self, text: str) -> MultiModalEmbedding:
        return await self.encode([ModalityInput(Modality.TEXT, text, "text/plain")])

    async def encode_image(self, data: bytes, mime_type: str = "image/png") -> MultiModalEmbedding:
        return await self.encode([ModalityInput(Modality.IMAGE, data, mime_type)])

    async def similarity(self, a: MultiModalEmbedding, b: MultiModalEmbedding) -> float:
        dot = sum(x * y for x, y in zip(a.vector, b.vector))
        denom = (a.norm * b.norm) or 1e-9
        return max(-1.0, min(1.0, dot / denom))

    def supported_modalities(self) -> frozenset[Modality]:
        return frozenset(self._encode_dispatch.keys())

    # ── helpers ────────────────────────────────────────────

    def _hash_to_vector(self, data: bytes) -> list[float]:
        dim = self._config.embedding_dim
        vec: list[float] = []
        seed = data
        while len(vec) < dim:
            h = hashlib.sha256(seed).digest()
            for i in range(0, len(h) - 3, 4):
                if len(vec) >= dim:
                    break
                val = struct.unpack("<f", h[i:i+4])[0]
                # Clamp to [-1, 1]
                vec.append(max(-1.0, min(1.0, val / 1e38 if abs(val) > 1.0 else val)))
            seed = h  # Chain for next round
        return vec[:dim]
```

---

## Implementation: `NullMultiModalEncoder`

```python
class NullMultiModalEncoder:
    """No-op encoder returning zero vectors. Used in tests and dry-run pipelines."""

    def __init__(self, config: EncoderConfig | None = None) -> None:
        self._dim = (config or EncoderConfig()).embedding_dim

    async def encode(self, inputs: Sequence[ModalityInput]) -> MultiModalEmbedding:
        modalities = frozenset(inp.modality for inp in inputs)
        k = len(modalities) or 1
        return MultiModalEmbedding(
            vector=tuple(0.0 for _ in range(self._dim)),
            modality_weights={m: 1.0 / k for m in modalities},
            source_modalities=modalities,
            dimension=self._dim,
        )

    async def encode_text(self, text: str) -> MultiModalEmbedding:
        return await self.encode([ModalityInput(Modality.TEXT, text)])

    async def encode_image(self, data: bytes, mime_type: str = "image/png") -> MultiModalEmbedding:
        return await self.encode([ModalityInput(Modality.IMAGE, data, mime_type)])

    async def similarity(self, a: MultiModalEmbedding, b: MultiModalEmbedding) -> float:
        return 0.0

    def supported_modalities(self) -> frozenset[Modality]:
        return frozenset(Modality)
```

---

## Factory

```python
def make_multimodal_encoder(
    config: EncoderConfig | None = None,
    *,
    null: bool = False,
) -> MultiModalEncoder:
    """Create a MultiModalEncoder instance.

    Args:
        config: Encoder configuration. Defaults to ``EncoderConfig()``.
        null: If ``True``, return ``NullMultiModalEncoder`` (zero vectors).

    Returns:
        A ``MultiModalEncoder``-conformant object.
    """
    if null:
        return NullMultiModalEncoder(config)
    return SimpleMultiModalEncoder(config)
```

---

## Data Flow

```
┌───────────┐     ┌──────────────┐
│  Text str  │────▶│ TextEncoder  │──────┐
└───────────┘     └──────────────┘      │
┌───────────┐     ┌──────────────┐      │    ┌─────────────┐    ┌────────────────────┐
│ Image bytes│────▶│ ImageEncoder │──────┼───▶│ FusionLayer │───▶│ MultiModalEmbedding│
└───────────┘     └──────────────┘      │    │ (ATTENTION)  │    │  vector: (256,)    │
┌───────────┐     ┌──────────────┐      │    └─────────────┘    │  modality_weights  │
│ Audio bytes│────▶│ AudioEncoder │──────┘         │             │  source_modalities │
└───────────┘     └──────────────┘            L2 Normalize      └────────────────────┘
┌───────────┐     ┌──────────────┐                 │
│ Video bytes│────▶│ VideoEncoder │─────────────────┘
└───────────┘     └──────────────┘
┌───────────┐     ┌───────────────┐                │
│ JSON struct│────▶│ StructEncoder │────────────────┘
└───────────┘     └───────────────┘
```

### Background Encode Pipeline

```
CommunicationOrchestrator 19.5
    │
    ▼
MultiModalEncoder.encode([text, image, audio])
    │
    ├── _encode_text()  ──────────────────┐
    ├── _encode_image() ──────────────────┤
    └── _encode_audio() ──────────────────┤
                                           ▼
                                    _fuse(per_modality)
                                           │
                              ┌─────────────┼──────────────┐
                              ▼             ▼              ▼
                        SemanticParser   WorldModel   CuriosityModule
                           (19.1)         (13.1)        (13.3)
```

---

## Integration Map

| Upstream / Downstream | Component | Interaction |
|---|---|---|
| **→ SemanticParser 19.1** | `SemanticParser.parse_with_embedding()` | Text embeddings from MultiModalEncoder feed intent matching and slot extraction |
| **→ WorldModel 13.1** | `WorldModel.observe()` | Multi-modal embeddings injected as world-state observations for internal simulation |
| **→ CuriosityModule 13.3** | `CuriosityModule.compute_novelty()` | Embedding distance from known patterns drives curiosity-based exploration |
| **→ CommunicationOrchestrator 19.5** | First pipeline stage | Incoming multi-modal messages encoded before routing to dialogue/action planner |
| **← SurpriseDetector 13.4** | `SurpriseDetector.score()` | Surprise scoring can re-use embedding distances as a novelty signal |
| **← MemoryConsolidator 18.2** | `MemoryConsolidator.sweep()` | Consolidated semantic patterns may include multi-modal embedding fingerprints |

### CommunicationOrchestrator Integration Pattern

```python
# Inside CommunicationOrchestrator._process_incoming()
async def _process_incoming(self, message: IncomingMessage) -> None:
    inputs = [
        ModalityInput(Modality.TEXT, message.text, "text/plain"),
    ]
    if message.image:
        inputs.append(ModalityInput(Modality.IMAGE, message.image, message.image_mime))
    if message.audio:
        inputs.append(ModalityInput(Modality.AUDIO, message.audio, "audio/wav"))

    embedding = await self._encoder.encode(inputs)
    intent = await self._semantic_parser.parse_with_embedding(embedding)
    await self._route(intent, embedding)
```

---

## Prometheus Metrics

| # | Metric | Type | Labels | Description |
|---|---|---|---|---|
| 1 | `multimodal_encode_total` | Counter | `modality`, `backend` | Total encode calls by modality and backend |
| 2 | `multimodal_encode_duration_seconds` | Histogram | `fusion_strategy` | End-to-end encode latency including fusion |
| 3 | `multimodal_input_bytes_total` | Counter | `modality` | Total bytes ingested per modality |
| 4 | `multimodal_fusion_weight` | Gauge | `modality` | Latest per-modality fusion weight (rolling) |
| 5 | `multimodal_similarity_computed_total` | Counter | — | Total similarity computations |

### PromQL Examples

```promql
# Average encode latency by fusion strategy (5 m window)
rate(multimodal_encode_duration_seconds_sum[5m])
  / rate(multimodal_encode_duration_seconds_count[5m])

# Encode throughput by modality
sum by (modality) (rate(multimodal_encode_total[1m]))

# Modality weight drift — detect imbalanced fusion
stddev(multimodal_fusion_weight) > 0.3

# Input volume by modality (MB/s)
sum by (modality) (rate(multimodal_input_bytes_total[5m])) / 1e6
```

### Grafana Alert YAML

```yaml
- alert: MultiModalEncodeLatencyHigh
  expr: |
    histogram_quantile(0.99,
      rate(multimodal_encode_duration_seconds_bucket[5m])
    ) > 0.1
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "MultiModalEncoder p99 latency > 100 ms"

- alert: ModalityWeightDrift
  expr: stddev(multimodal_fusion_weight) > 0.4
  for: 5m
  labels:
    severity: info
  annotations:
    summary: "Fusion weights heavily skewed — one modality dominating"

- alert: InputTooLargeErrors
  expr: rate(multimodal_encode_total{status="error_too_large"}[5m]) > 0
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "InputTooLargeError being raised — check upstream payload sizes"
```

---

## mypy Strict-Mode Compliance

| Pattern | Technique |
|---|---|
| `data: bytes \| str` | `isinstance()` guard before `.encode()` |
| `dict[Modality, float]` | Constructed inline, typed via annotation |
| `frozenset[Modality]` | Literal frozenset construction in return |
| `tuple[float, ...]` | `tuple()` over generator, immutable |
| `callable` dispatch dict | `dict[Modality, Callable[[bytes \| str], list[float]]]` explicit |
| `__post_init__` frozen mutation | `object.__setattr__()` pattern |

---

## Test Targets (12)

| # | Test | Validates |
|---|---|---|
| 1 | `test_encode_text_returns_correct_dimension` | Text encoding → `dimension == embedding_dim` |
| 2 | `test_encode_image_returns_correct_dimension` | Image encoding → `dimension == embedding_dim` |
| 3 | `test_encode_multi_modal_fuses_all_modalities` | Encode [TEXT, IMAGE, AUDIO] → `source_modalities` == 3 |
| 4 | `test_similarity_identical_vectors_is_one` | `similarity(e, e) ≈ 1.0` |
| 5 | `test_similarity_orthogonal_near_zero` | Unrelated inputs → similarity < 0.3 |
| 6 | `test_input_too_large_raises` | Input > `max_input_bytes` → `InputTooLargeError` |
| 7 | `test_unsupported_modality_raises` | Unknown modality enum → `ValueError` |
| 8 | `test_null_encoder_returns_zero_vector` | `NullMultiModalEncoder` → all-zeros vector |
| 9 | `test_fusion_attention_weights_sum_to_one` | `sum(modality_weights.values()) ≈ 1.0` |
| 10 | `test_fusion_average_equal_weights` | `AVERAGE` strategy → all weights equal `1/k` |
| 11 | `test_normalize_produces_unit_vector` | `config.normalize=True` → `norm ≈ 1.0` |
| 12 | `test_factory_null_flag` | `make_multimodal_encoder(null=True)` → `NullMultiModalEncoder` |

### Test Skeleton

```python
import pytest
from asi_build.multimodal_encoder import (
    EncoderConfig,
    FusionStrategy,
    InputTooLargeError,
    Modality,
    ModalityInput,
    MultiModalEmbedding,
    SimpleMultiModalEncoder,
    NullMultiModalEncoder,
    make_multimodal_encoder,
)

@pytest.mark.asyncio
async def test_encode_multi_modal_fuses_all_modalities():
    encoder = SimpleMultiModalEncoder(EncoderConfig(embedding_dim=64))
    inputs = [
        ModalityInput(Modality.TEXT, "hello world", "text/plain"),
        ModalityInput(Modality.IMAGE, b"\x89PNG" + b"\x00" * 100, "image/png"),
        ModalityInput(Modality.AUDIO, b"\x00\xff" * 200, "audio/wav"),
    ]
    emb = await encoder.encode(inputs)
    assert emb.dimension == 64
    assert len(emb.vector) == 64
    assert emb.source_modalities == frozenset({Modality.TEXT, Modality.IMAGE, Modality.AUDIO})
    assert abs(sum(emb.modality_weights.values()) - 1.0) < 1e-6

@pytest.mark.asyncio
async def test_input_too_large_raises():
    config = EncoderConfig(max_input_bytes=100)
    encoder = SimpleMultiModalEncoder(config)
    big_input = ModalityInput(Modality.TEXT, "x" * 200, "text/plain")
    with pytest.raises(InputTooLargeError):
        await encoder.encode([big_input])

@pytest.mark.asyncio
async def test_fusion_attention_weights_sum_to_one():
    encoder = SimpleMultiModalEncoder(
        EncoderConfig(fusion_strategy=FusionStrategy.ATTENTION, embedding_dim=32)
    )
    inputs = [
        ModalityInput(Modality.TEXT, "test text", "text/plain"),
        ModalityInput(Modality.IMAGE, b"\xff" * 50, "image/png"),
    ]
    emb = await encoder.encode(inputs)
    assert abs(sum(emb.modality_weights.values()) - 1.0) < 1e-6
```

---

## Implementation Order (14 Steps)

| Step | Task | File(s) |
|---|---|---|
| 1 | Define `Modality`, `EncoderBackend`, `FusionStrategy` enums | `enums.py` |
| 2 | Define `ModalityInput` frozen dataclass | `models.py` |
| 3 | Define `MultiModalEmbedding` frozen dataclass with `__post_init__` | `models.py` |
| 4 | Define `EncoderConfig` frozen dataclass | `models.py` |
| 5 | Define `MultiModalEncoder` Protocol | `protocol.py` |
| 6 | Implement `_hash_to_vector()` helper | `simple_encoder.py` |
| 7 | Implement `_encode_text()` backend | `simple_encoder.py` |
| 8 | Implement `_encode_image()` backend | `simple_encoder.py` |
| 9 | Implement `_encode_audio()` / `_encode_video()` / `_encode_structured()` | `simple_encoder.py` |
| 10 | Implement `_fuse()` with all four strategies | `simple_encoder.py` |
| 11 | Wire `encode()`, `encode_text()`, `encode_image()`, `similarity()` | `simple_encoder.py` |
| 12 | Implement `NullMultiModalEncoder` | `null_encoder.py` |
| 13 | Implement `make_multimodal_encoder()` factory | `factory.py` |
| 14 | Write 12 pytest tests, register Prometheus metrics | `test_multimodal_encoder.py`, `metrics.py` |

---

## Phase 19 Sub-phase Tracker

| Sub-phase | Component | Issue | Wiki | Status |
|---|---|---|---|---|
| 19.1 | SemanticParser | [#466](https://github.com/web3guru888/asi-build/issues/466) | [Phase-19-Semantic-Parser](Phase-19-Semantic-Parser) | 🟡 Spec'd |
| 19.2 | DialogueManager | [#469](https://github.com/web3guru888/asi-build/issues/469) | [Phase-19-Dialogue-Manager](Phase-19-Dialogue-Manager) | 🟡 Spec'd |
| 19.3 | ResponseSynthesiser | [#472](https://github.com/web3guru888/asi-build/issues/472) | [Phase-19-Response-Synthesiser](Phase-19-Response-Synthesiser) | 🟡 Spec'd |
| **19.4** | **MultiModalEncoder** | [**#475**](https://github.com/web3guru888/asi-build/issues/475) | **Phase-19-Multi-Modal-Encoder** ← you are here | 🟡 Spec'd |
| 19.5 | CommunicationOrchestrator | TBD | TBD | ⬜ Planned |
