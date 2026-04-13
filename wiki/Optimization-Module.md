# Optimization Module (VLA++)

> **Path**: `src/asi_build/optimization/`  
> **Files**: 12 | **LOC**: ~4,166  
> **Status**: Research / Experimental 🔬  
> **Focus**: Vision-Language-Action model compression for edge/embodied deployment

---

## Overview

The Optimization module implements **VLA++ (Vision-Language-Action++)**, a model compression and training pipeline for deploying large multi-modal models on resource-constrained hardware. Where most ASI:BUILD modules focus on reasoning, consciousness, or communication, this module addresses a complementary problem: *how do you actually run a 217MB VLA model on a mobile robot or edge device?*

The answer: quantization + structured pruning + knowledge distillation + LoRA-efficient training, packaged into a production-grade pipeline with CARLA simulation safety validation.

This module demonstrates a key design philosophy in ASI:BUILD — **every layer of the cognitive stack must eventually run somewhere physical**, and that requires aggressive model efficiency techniques.

---

## Architecture

```
optimization/
├── src/
│   ├── architecture.py      — VLA++ multi-modal model (Vision + Language + Action)
│   ├── model_optimization.py — Quantization, pruning, distillation pipeline
│   ├── training.py          — LoRA + mixed-precision training loop
│   ├── bci_integration.py   — Brain-Computer Interface fusion (EEG → action)
│   └── carla_test_suite.py  — 100K+ scenario safety validation (ISO 26262)
└── scripts/
    ├── download_datasets.py          — dataset acquisition
    └── download_production_datasets.py
```

---

## VLA++ Architecture (`architecture.py`)

VLA++ fuses three modalities through cross-attention into a unified action planning head.

```
VisionModule (ResNet50 + FPN)
      │
      ├── Feature Pyramid Network (4 levels, 256 channels each)
      └── Detection head → object bounding boxes + classes (80 COCO classes)
            │
            ▼
LanguageModule (GPT-2 variant)
      │
      ├── vocab_size: 8192, hidden: 768, layers: 12, heads: 12
      └── Command tokenization + semantic encoding
            │
            ▼
CrossModalFusion (1024-dim, 16 heads, dropout 0.1)
      │
      ▼
ActionModule (Transformer decoder)
      ├── hidden: 512, layers: 6, heads: 8
      └── Outputs: 20 waypoints for trajectory planning
```

**VLAConfig highlights:**

```python
@dataclass
class VLAConfig:
    vision_backbone: str = "resnet50"
    vision_hidden_size: int = 2048
    vision_num_classes: int = 80       # COCO classes
    language_model: str = "gpt2"
    language_vocab_size: int = 8192
    language_hidden_size: int = 768
    language_num_layers: int = 12
    action_hidden_size: int = 512
    action_num_waypoints: int = 20     # trajectory points
    fusion_hidden_size: int = 1024
    fusion_num_heads: int = 16
    use_mixed_precision: bool = True
    gradient_checkpointing: bool = True
```

---

## Model Optimization Pipeline (`model_optimization.py`)

Target: **217MB → <50MB** with ≤1% accuracy loss. Three-stage pipeline:

### Stage 1 — Quantization (`ModelQuantizer`)

**Dynamic quantization** — weights quantized, activations computed in FP32:
```python
# Best for varying input sizes
quantized_model = torch.quantization.quantize_dynamic(
    model,
    qconfig_spec={nn.Linear: default_dynamic_qconfig,
                  nn.Conv2d: default_dynamic_qconfig},
    dtype=torch.qint8,
)
```

**Static quantization** — both weights and activations quantized:
```python
# Best for fixed input sizes, maximum throughput
model.qconfig = torch.quantization.get_default_qconfig("qnnpack")
model_prepared = torch.quantization.prepare(model)
# calibrate with 1000 representative samples
model_quantized = torch.quantization.convert(model_prepared)
```

Backend: `qnnpack` (ARM/mobile optimized).

### Stage 2 — Pruning (`ModelPruner`)

**Structured pruning** — removes entire channels/filters (hardware-friendly):

```python
@dataclass
class OptimizationConfig:
    pruning_amount: float = 0.6    # remove 60% of weights
    pruning_type: str = "structured"
    target_model_size_mb: float = 50.0
    target_latency_ms: float = 10.0
    max_accuracy_loss: float = 0.01  # 1% budget
```

Prunes `nn.Linear` and `nn.Conv2d` layers by L1-norm. Structured pruning ensures the resulting sparse model can be accelerated by standard BLAS routines without sparse matrix libraries.

### Stage 3 — Knowledge Distillation (`KnowledgeDistiller`)

Student trained to match teacher's soft probability distributions:

```python
# Distillation loss = α * KL_divergence(teacher_soft, student_soft)
#                   + (1-α) * cross_entropy(student_logits, labels)
teacher_temperature: float = 5.0
student_temperature: float = 3.0
distillation_alpha: float = 0.7     # 70% distillation, 30% hard labels
```

Higher temperatures produce softer probability distributions that carry more information about inter-class relationships — key for transferring reasoning patterns, not just predictions.

---

## Training Pipeline (`training.py`)

**MiniMind-inspired** ultra-efficient training loop targeting 2-hour cycles on consumer hardware.

### Efficiency Stack

| Technique | Speedup / Savings |
|-----------|------------------|
| Mixed precision BF16 (`GradScaler`) | 2× throughput, 50% memory |
| Gradient checkpointing | 40% memory reduction |
| PyTorch 2.0 `torch.compile()` | 10–30% additional throughput |
| LoRA (rank=16, α=32) | Only 10% of parameters trained |
| Gradient accumulation (×4) | Effective batch = 128 on single GPU |

### Training Config

```python
@dataclass
class TrainingConfig:
    batch_size: int = 32
    learning_rate: float = 1e-4
    max_steps: int = 50000
    gradient_accumulation: int = 4
    gradient_clip: float = 1.0
    # LoRA
    use_lora: bool = True
    lora_rank: int = 16
    lora_alpha: float = 32.0
    # Hardware targets
    device: str = "cuda"
    cudo_instance_type: str = "rtx4090"
    cudo_spot_instance: bool = True
    cudo_max_price: float = 1.20    # $/hour
```

The `cudo_*` fields reference [Cudo Compute](https://www.cudocompute.com/) for spot GPU instances — the training pipeline is designed to be economically self-managing: if spot price exceeds $1.20/hr, training pauses and resumes.

---

## Brain-Computer Interface Fusion (`bci_integration.py`)

VLA++ extends to **VL-BCI-A** (Vision-Language-Brain-Action): EEG motor imagery signals augment the action module, enabling direct neural control of robot actions.

### Signal Processing Pipeline

```
64-channel EEG (250 Hz)
      │
      ▼
Band-pass filter (8-30 Hz — mu + beta bands)
      │
      ▼
Common Spatial Patterns (CSP, 8 components)
      │
      ├── LDA classifier (4 classes)
      └── Feature extraction → BCI embedding
            │
            ▼
Multi-modal fusion with VLA++ (bci_weight: 0.3)
      │
      ▼
Final action output
```

**BCIConfig:**

```python
@dataclass
class BCIConfig:
    n_channels: int = 64        # EEG electrodes
    sampling_rate: int = 250    # Hz
    n_classes: int = 4          # motor imagery classes
    csp_components: int = 8     # spatial filters
    window_size: int = 1000     # ms epoch
    latency_target: int = 100   # ms end-to-end
    bci_weight: float = 0.3     # fusion weight

    action_map: Dict[str, str] = {
        "left_hand":  "grasp_object",
        "right_hand": "release_object",
        "feet":       "move_forward",
        "tongue":     "emergency_stop",   # important!
    }
```

`CommonSpatialPatterns` uses generalized eigendecomposition (`scipy.linalg.eigh`) to find filters that maximize inter-class variance while minimizing intra-class variance — the standard approach for motor imagery BCI.

The 100ms latency target is critical: motor imagery → robot response in under one reaction time window.

---

## Safety Validation — CARLA Test Suite (`carla_test_suite.py`)

Before deployment, VLA++ must pass **100,000+ simulation scenarios** in CARLA for ISO 26262 ASIL-D compliance.

### Scenario Categories

| Type | Examples |
|------|----------|
| `HIGHWAY` | Lane changes, merges, high-speed following |
| `URBAN` | Intersections, pedestrian crossings, cyclists |
| `PARKING` | Tight maneuvers, reversing, obstacle avoidance |
| `WEATHER` | Rain (light/heavy), fog, snow, storm |
| `NIGHT` | Reduced visibility, headlight glare |
| `EMERGENCY` | Sudden pedestrian, vehicle cut-off, tire blowout |
| `SENSOR_FAILURE` | Camera dropout, LiDAR occlusion, GPS denial |
| `CONSTRUCTION` | Altered lane markings, reduced-speed zones |
| `EDGE_CASE` | Unusual but legal scenarios (e.g., reversed traffic flow) |

### Safety Metrics

```python
@dataclass
class SafetyMetrics:
    collision_free_rate: float   # target: >99.99%
    traffic_compliance_rate: float
    comfort_score: float         # jerk/acceleration bounds
    intervention_rate: float     # human takeovers per 1000 km
    response_time_ms: float      # sensor→action latency
    minimum_distance_m: float    # closest approach to obstacles
    max_acceleration_ms2: float
    max_jerk_ms3: float
```

The suite generates test scenarios programmatically using `TestScenario` dataclasses, runs them in CARLA, and aggregates `SafetyMetrics` across the full distribution.

---

## Integration with ASI:BUILD

| Module | Integration |
|--------|-------------|
| `bci` | BCI motor imagery classification used in `bci_integration.py` |
| `consciousness` | Action planning could be gated by GWT workspace (attended goals) |
| `safety` | CARLA suite complements AGSSL formal proofs with empirical evidence |
| `cognitive_blackboard` | Not yet wired — see Issue #83 |

### Blackboard Integration (Planned — Issue #83)

`VLAPlusPlus` inference results (action waypoints, confidence) are natural Blackboard entries. A `VLABlackboardAdapter` would:

1. Subscribe to `PERCEPTION_UPDATED` events (camera frames, language commands)
2. Run VLA++ inference
3. Write `ActionPlan` to Blackboard (waypoints, confidence, latency)
4. Trigger `ACTION_PLANNED` event for downstream modules

---

## Open Questions

1. **Real vs. simulated**: CARLA validation is comprehensive, but how does VLA++ generalize to real-world sensor noise distributions not captured in simulation?
2. **BCI calibration drift**: CSP filters degrade over time as EEG signal characteristics change (fatigue, electrode impedance) — what's the recalibration protocol?
3. **LoRA rank selection**: Rank=16 is a reasonable default, but is it optimal for the multi-modal cross-attention layers? Should vision, language, and action adapters have different ranks?
4. **CUDO spot interruptions**: How should the training pipeline checkpoint and resume gracefully when a spot instance is preempted mid-gradient-accumulation?
5. **Multi-robot coordination**: When multiple VLA++ agents share a space, how do they avoid conflicting action plans? Does `agi_communication`'s goal negotiation apply here?

---

## Related Issues & Discussions

- **Issue #83**: Wire VLA++ to Cognitive Blackboard (VLABlackboardAdapter) *(planned)*
- **Issue #15**: Update docs/modules/ for all 29 modules *(includes this module)*
- **Issue #39**: Design CognitiveCycle — action module is the final output stage
- **Discussion #40**: Show & Tell on CognitiveCycle design — covers action planning integration

---

*Last updated: 2026-04-12 — ASI:BUILD v0.1.0-alpha*
