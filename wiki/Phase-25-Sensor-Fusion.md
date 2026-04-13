# Phase 25.1 — SensorFusion

> Multi-modal sensor data integration and preprocessing engine using Extended Kalman Filtering.

| Property | Value |
|----------|-------|
| **Phase** | 25.1 |
| **Component** | `SensorFusion` |
| **Type** | Protocol + `KalmanSensorFusion` impl |
| **Issue** | [#562](https://github.com/web3guru888/asi-build/issues/562) |
| **Depends on** | MultiModalEncoder 19.4, WorldModel 13.1 |
| **Consumers** | AffordanceDetector 25.2, SpatialReasoner 25.4, EmbodiedOrchestrator 25.5 |

## Theoretical Basis

Based on O'Regan & Noë's sensorimotor contingency theory — perception is active, prediction-driven, and multi-modal. Sensor fusion combines uncertain measurements from multiple modalities into a coherent state estimate.

## Data Structures

### Enums

- `SensorModality` — VISION, PROPRIOCEPTION, TACTILE, AUDITORY, VESTIBULAR
- `FusionStrategy` — KALMAN, PARTICLE, BAYESIAN, WEIGHTED_AVERAGE

### Frozen Dataclasses

- `SensorReading(sensor_id, modality, timestamp_ms, data, confidence, noise_covariance)`
- `FusedState(timestamp_ms, state_vector, covariance_matrix, contributing_sensors, confidence)`
- `SensorConfig(strategy, max_latency_ms, min_confidence, calibration_samples, prediction_horizon_ms)`

## Protocol

```python
@runtime_checkable
class SensorFusion(Protocol):
    async def fuse(self, readings: Sequence[SensorReading]) -> FusedState: ...
    async def calibrate(self, sensor_id: str, samples: Sequence[SensorReading]) -> None: ...
    async def get_fused_state(self) -> FusedState: ...
    async def register_sensor(self, sensor_id: str, modality: SensorModality) -> None: ...
    async def predict(self, horizon_ms: int) -> FusedState: ...
```

## Architecture

```
Vision ──────┐
Propriocept. ─┤
Tactile ──────┼→ KalmanSensorFusion → FusedState → AffordanceDetector 25.2
Auditory ─────┤    ├─ EKF predict      │            SpatialReasoner 25.4
Vestibular ───┘    ├─ EKF update        │            WorldModel 13.1
                   ├─ Multi-rate align  │
                   └─ Mahalanobis gate  │
                                        └→ EmbodiedOrchestrator 25.5
```

## Key Algorithms

### Extended Kalman Filter

- **Predict**: `x̂ = F·x + B·u`, `P̂ = F·P·Fᵀ + Q`
- **Update**: `K = P̂·Hᵀ·(H·P̂·Hᵀ + R)⁻¹`, `x = x̂ + K·(z - H·x̂)`
- **Mahalanobis gating**: `d² = (z - H·x̂)ᵀ · S⁻¹ · (z - H·x̂)`, reject if `d² > χ²`

### Multi-Rate Alignment

Sensors at different frequencies → temporal interpolation + prediction fill.

### Confidence Decay

Offline sensors: `confidence *= exp(-λ · Δt)` with configurable decay rate.

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sensor_fusion_fuse_total` | Counter | Total fusion operations |
| `sensor_fusion_fuse_seconds` | Histogram | Fusion latency |
| `sensor_fusion_confidence` | Gauge | Current fused state confidence |
| `sensor_fusion_sensors_active` | Gauge | Active sensor count |
| `sensor_fusion_outliers_rejected_total` | Counter | Mahalanobis rejections |

## Test Targets (12)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_sensor_reading_frozen` | Immutability |
| 2 | `test_fused_state_frozen` | Immutability |
| 3 | `test_kalman_fuse_single_sensor` | Single sensor |
| 4 | `test_kalman_fuse_multi_sensor` | Multi-modal |
| 5 | `test_kalman_predict_horizon` | Prediction |
| 6 | `test_calibrate_updates_noise_model` | Calibration |
| 7 | `test_register_sensor_new_modality` | Registration |
| 8 | `test_outlier_rejection_mahalanobis` | Gating |
| 9 | `test_multi_rate_alignment` | Interpolation |
| 10 | `test_confidence_decay_offline_sensor` | Degradation |
| 11 | `test_null_sensor_fusion_noop` | Null impl |
| 12 | `test_factory_returns_kalman` | Factory |

## References

- Welch & Bishop (1995) — "An Introduction to the Kalman Filter"
- Thrun, Burgard & Fox (2005) — "Probabilistic Robotics"
- O'Regan & Noë (2001) — "A sensorimotor account of vision and visual consciousness"

---

### Phase 25 Sub-phase Tracker

| # | Component | Status |
|---|-----------|--------|
| 25.1 | SensorFusion | 📋 Spec'd |
| 25.2 | AffordanceDetector | 📋 Spec'd |
| 25.3 | MotorPlanner | 📋 Spec'd |
| 25.4 | SpatialReasoner | 📋 Spec'd |
| 25.5 | EmbodiedOrchestrator | 📋 Spec'd |
