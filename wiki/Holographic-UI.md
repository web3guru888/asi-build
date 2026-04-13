# Holographic UI — Software Stack for Future Display Systems

> **Status**: Research-grade software stack. All subsystems are pure Python simulation — no hardware holographic display is required or targeted yet. This module defines the architecture for what a holographic ASI interface *would* need, giving the framework a place to evolve as display hardware matures.

## Overview

The `holographic` module (8,430 LOC across 12 source files) is ASI:BUILD's software layer for volumetric, light-field, and mixed-reality interfaces. It is **not** a driver for consumer AR headsets or a holographic projector SDK — it is a full-stack simulation of what a capable holographic display system would need: a light field processor, a volumetric voxel renderer, 3D gesture input, spatially-anchored audio, physics for holographic objects, and an AR overlay engine.

The design philosophy is forward-looking: write the right abstractions now so that when capable holographic hardware exists (true volumetric displays, coherent-light projectors, high-FOV spatial computers), the software layer already has principled APIs to hand off to.

### What it provides

| Subsystem | File | LOC | Purpose |
|-----------|------|-----|---------|
| Core engine | `core/engine.py` | 630 | Orchestrates all subsystems, async frame loop |
| Light field | `core/light_field.py` | 680 | Plenoptic camera array, view synthesis, refocus |
| Math utilities | `core/math_utils.py` | 406 | `SpatialMath`: 3D geometry, matrices, distance |
| Event system | `core/event_system.py` | 622 | Async pub/sub, priorities, wildcard matching |
| Configuration | `core/config.py` | 357 | Typed dataclasses for all subsystem configs |
| Base classes | `core/base.py` | 350 | `HolographicBase`, `Vector3D`, `Transform3D`, `HolographicPerformanceMonitor` |
| Volumetric display | `display/volumetric_display.py` | 754 | Voxel-based 3D rendering, transfer functions |
| Spatial audio | `audio/spatial_audio_manager.py` | 800 | HRTF, Doppler, reverb zones, 3D positioned sources |
| Telepresence | `telepresence/telepresence_manager.py` | 846 | Remote holographic presence |
| Hand tracking | `gestures/hand_tracker.py` | 1,002 | 21-joint 3D hand model, stereo triangulation |
| Physics | `physics/physics_manager.py` | 894 | Holographic object physics simulation |
| Mixed reality | `ar_overlay/mixed_reality_engine.py` | 912 | SLAM, AR overlay, spatial anchors |

---

## Architecture

### HolographicEngine — the frame loop

`HolographicEngine` is the root coordinator. On `initialize()`, it spins up all subsystem managers dynamically (to avoid circular imports), subscribes to system-level events, and hands out typed configs to each subsystem:

```python
engine = HolographicEngine(config=HolographicConfig())
await engine.initialize()   # starts all 10 managers
await engine.start()        # enters async frame loop at target_fps (default 120)
```

The main loop calls three phases per frame, all under `asyncio.gather()` for parallelism:

```
_update_frame(Δt)  →  all managers update in parallel
_render_frame(Δt)  →  display_manager.render()
_complete_frame(Δt) → user callbacks + batched event emission (every 30 frames)
```

User code can hook into any phase:

```python
engine.add_update_callback(my_async_update)   # runs every frame
engine.add_render_callback(my_render_hook)    # after display update
engine.add_frame_callback(my_frame_callback)  # receives (Δt, frame_count)
```

`HolographicPerformanceMonitor` tracks per-subsystem timing, frame count, and FPS. Performance metrics are available via `get_performance_metrics()`, including GPU utilization (via `GPUtil` if available).

### Configuration system

`HolographicConfig` is composed of typed sub-configs:

```python
@dataclass
class DisplayConfig:
    resolution_x: int = 1920
    resolution_y: int = 1080
    resolution_z: int = 512       # depth layers
    refresh_rate: float = 60.0
    field_of_view: float = 110.0  # degrees
    display_type: str = "volumetric"  # volumetric | light_field | holographic

@dataclass
class PerformanceConfig:
    max_fps: float = 120.0
    adaptive_quality: bool = True
    level_of_detail: bool = True
    occlusion_culling: bool = True
    gpu_acceleration: bool = True

@dataclass
class GestureConfig:
    sensitivity: float = 0.8
    confidence_threshold: float = 0.7
    interaction_distance: float = 2.0  # metres
    eye_tracking: bool = True
    body_tracking: bool = True
```

---

## The Light Field Model

### What is a light field?

A standard 2D image stores one colour per pixel — what a single camera at a fixed viewpoint sees. A **light field** stores a colour for every *ray* passing through a volume: for any viewpoint and any direction, it can synthesise what you would see. This is the mathematical foundation of lenticular displays, integral photography, and true holographic systems.

The plenoptic function represents all light as a function of 7 variables: position `(x, y, z)`, direction `(θ, φ)`, wavelength `λ`, and time `t`. For static scenes, this reduces to a 5D function. The two-plane parametrisation (used here) reduces it further to 4D: two planes `(u, v)` and `(s, t)`, where `(u, v)` is the position on the camera/sensor plane and `(s, t)` is where the ray intersects a parallel focal plane.

### LightRay dataclass

```python
@dataclass
class LightRay:
    origin: Vector3D              # where the ray starts (sensor/lens position)
    direction: Vector3D           # normalised direction vector
    color: Tuple[float, float, float]   # RGB in [0.0, 1.0]
    intensity: float
    wavelength: float = 550.0     # nanometres (green default)
    polarization: Optional[Vector3D] = None
    phase: float = 0.0            # wave phase for coherence calculations
```

The `to_plenoptic_coords()` method converts a ray to the `(u, v, s, t)` two-plane representation:

```python
def to_plenoptic_coords(self, focal_length: float) -> Tuple[float, float, float, float]:
    # u, v: ray origin on sensor plane
    # s, t: where ray intersects focal plane at -focal_length
    t_focal = -focal_length / self.direction.z
    focal_x = self.origin.x + t_focal * self.direction.x
    focal_y = self.origin.y + t_focal * self.direction.y
    return self.origin.x, self.origin.y, focal_x, focal_y
```

### LightFieldProcessor

`LightFieldProcessor` simulates a **plenoptic camera array** — an `8×8` grid of 64 virtual cameras arranged in a plane, each separated by `baseline` millimetres. Together they capture the full 4D light field `LF[u, v, s, t, RGB]` where:

- `(u, v)` indexes which camera in the grid (aperture dimension)
- `(s, t)` indexes the pixel within that camera's image (image plane dimension)

```python
processor = LightFieldProcessor(resolution=(8, 8, 512, 512))
# resolution = (u_res, v_res, s_res, t_res)
# Memory: 8 × 8 × 512 × 512 × 3 float32 ≈ 402 MB
```

**Capture**: `capture_light_field(scene_data)` renders all 64 camera views in parallel via `asyncio.gather()`, then integrates the results into the 4D array.

**View synthesis**: `synthesize_view(position, direction, up, output_resolution)` reconstructs what a camera at any position would see. For each output pixel, it traces a ray, identifies the top-4 contributing cameras by angular and distance weight, and blends their images using bilinear interpolation.

**Post-hoc refocus**: `refocus_image(focus_depth, aperture_size, output_resolution)` simulates changing focus *after capture* by shifting and integrating views across the aperture dimension — the key advantage of light field capture over conventional photography.

**Depth estimation**: `estimate_depth_map()` uses block matching (SSD) between adjacent cameras in the grid to estimate disparity, converting it to metric depth via `depth = baseline / disparity`.

---

## The Gesture System

### Hand model

The hand tracker uses a **21-joint skeleton** per hand:

```
Wrist (1)
├── Thumb:  MCP → IP → TIP              (3 joints)
├── Index:  MCP → PIP → DIP → TIP      (4 joints)
├── Middle: MCP → PIP → DIP → TIP      (4 joints)
├── Ring:   MCP → PIP → DIP → TIP      (4 joints)
└── Pinky:  MCP → PIP → DIP → TIP      (4 joints)
                                    Total: 21 joints
```

Each joint is a `Joint3D`:

```python
@dataclass
class Joint3D:
    position: Vector3D    # 3D world position in metres
    confidence: float     # model confidence [0, 1]
    velocity: Vector3D    # joint velocity (smoothed via Kalman filter)
    acceleration: Vector3D
```

The `Finger` dataclass tracks extension state and provides `tip_position` and total `length` computed from joint chain distances. `FingerType` is an enum: `THUMB | INDEX | MIDDLE | RING | PINKY`.

`HandLandmarks` is the top-level hand descriptor:

```python
@dataclass
class HandLandmarks:
    hand_id: str
    side: HandSide              # LEFT | RIGHT | UNKNOWN
    wrist: Joint3D
    fingers: Dict[FingerType, Finger]
    palm_center: Vector3D       # computed from wrist + MCP joints
    palm_normal: Vector3D       # cross product of index/middle/ring MCPs
    confidence: float
    timestamp: float
```

### Built-in gesture primitives

`HandLandmarks` includes several high-level gesture checks:

```python
hand.is_pinching(threshold=0.03)   # thumb-index tip distance < 3 cm
hand.is_fist()                     # ≤ 1 finger extended
hand.is_open_palm()                # ≥ 4 fingers extended
hand.distance_between_fingers(FingerType.THUMB, FingerType.INDEX)
hand.fingertips                    # Dict[FingerType, Vector3D] — all tip positions
```

### 3D tracking pipeline

`HandTracker` uses a `MultiCameraSystem` with stereo calibration:

1. **Capture**: reads frames from multiple `cv2` camera feeds simultaneously
2. **2D detection**: `HandDetectorModel.detect()` finds hand bounding boxes per frame  
3. **Landmark extraction**: `LandmarkDetectorModel.extract_landmarks()` finds 21 2D joints
4. **Stereo triangulation**: matched joints from left/right cameras are triangulated via `cv2.triangulatePoints()` using the calibrated `fundamental_matrix` / `rotation_matrix` / `translation_vector`
5. **Smoothing**: Kalman filters per hand track position and velocity, suppressing jitter
6. **3D reconstruction**: builds `HandLandmarks` from triangulated `points_3d` array

The palm normal is computed from the cross product of index/middle/ring MCP joint vectors — giving a stable plane orientation even under partial occlusion.

> **Current state**: The detection backend (`HandDetectorModel`, `LandmarkDetectorModel`) is a placeholder. In practice this would use MediaPipe Hands, OpenPose, or a custom model fine-tuned on holographic-context hand poses. The stereo calibration and triangulation math is complete and correct.

---

## The Volumetric Display System

### VoxelData

The fundamental primitive is a voxel:

```python
@dataclass
class VoxelData:
    position: Vector3D
    color: Tuple[float, float, float, float]  # RGBA
    intensity: float
    size: float
    active: bool = True

    def to_array(self) -> np.ndarray:
        # [x, y, z, r, g, b, a, intensity, size, active] — 10 floats
        # Ready for GPU buffer upload
```

### VolumeRenderer

`VolumeRenderer` maintains a 3D RGBA volume array `(W × H × D × 4)` and a density array `(W × H × D)`. Key parameters:

```python
renderer = VolumeRenderer(resolution=(256, 256, 256))
# volume_data: 256³ × 4 float32 ≈ 256 MB

renderer.step_size = 1.0 / max(resolution)  # ray march step
renderer.max_samples = 512                   # max samples per ray
renderer.opacity_threshold = 0.01           # early termination
```

Volume data can be loaded as a 3D scalar field (grayscale) or a pre-labelled RGBA volume. Transfer functions map density values to colour and opacity:

```python
renderer.color_transfer   # shape (256, 4) — colour LUT by density
renderer.opacity_transfer # shape (256,) — opacity LUT by density
```

Individual voxels can be placed by world position:

```python
renderer.add_voxel(
    position=Vector3D(0.1, 0.5, -0.3),
    color=(1.0, 0.5, 0.0, 1.0),  # RGBA orange
    intensity=0.8
)
# Internally maps world position to voxel indices via:
# x = int((pos.x + 1.0) * 0.5 * width)
```

`VolumetricLayer` adds the concept of depth-ordered layers with independent opacity and blend modes (`alpha`, `additive`, `multiply`) — useful for compositing holographic overlays over real-world content.

---

## Spatial Audio

`SpatialAudioManager` (800 LOC, 48 kHz / 24-bit / 8-channel) simulates physically accurate 3D audio:

- **HRTF** (Head-Related Transfer Function): convolves audio with per-direction impulse responses sized to the listener's head model (`head_radius=0.09 m`, `ear_distance=0.17 m`)
- **Distance attenuation**: configurable rolloff factor, max distance, and occlusion factor
- **Doppler effect**: computed from relative velocity of source and listener
- **Reverb zones**: spatial zones with configurable room size, reverb time, damping, and early/late reflection ratios
- **Source types**: `POINT | AMBIENT | DIRECTIONAL | SPATIAL | BINAURAL`

`AudioListener` carries position, orientation (`Transform3D`), velocity, and HRTF profile. Multiple audio sources can be registered; the manager spatialises them all relative to the current listener position on each update tick.

---

## Physics Simulation

`HolographicPhysicsManager` (894 LOC) gives holographic objects simulated physical behaviour. This is not real physics — holograms have no mass — but it provides the dynamics that make interactive holograms feel believable.

### Physics primitives

```python
class PhysicsBodyType(Enum):
    STATIC = "static"       # immovable anchor
    KINEMATIC = "kinematic" # script-controlled
    DYNAMIC = "dynamic"     # fully simulated
    GHOST = "ghost"         # collision detection only, no response

@dataclass
class PhysicsProperties:
    mass: float = 1.0
    restitution: float = 0.5   # bounciness
    friction: float = 0.5
    air_resistance: float = 0.01
    # Hologram-specific:
    coherence_stability: float = 1.0      # disruption tolerance
    interference_sensitivity: float = 0.1  # sensitivity to EM interference
    quantum_entanglement: float = 0.0     # for entangled hologram pairs
```

`Force` objects specify type (`GRAVITY | ELECTROMAGNETIC | SPRING | DAMPING | CUSTOM`), magnitude vector, point of application, and optional duration. Forces are accumulated and integrated on each physics tick.

---

## Mixed Reality Engine

`MixedRealityEngine` (912 LOC) handles the overlay of virtual objects onto real-world camera feeds.

### Reality modes

```python
class RealityMode(Enum):
    PURE_VR        # fully synthetic view
    AR_OVERLAY     # virtual objects composited onto camera feed
    MIXED_REALITY  # occlusion-aware blending
    PASSTHROUGH    # camera feed with minimal overlay
    HYBRID         # adaptive mode switching
```

### SLAM

The embedded `SLAM` class uses ORB feature extraction (via `cv2`) for visual SLAM — Simultaneous Localisation and Mapping:

- **Map points**: 3D feature point cloud built incrementally
- **Keyframes**: stored reference frames with associated feature descriptors
- **Loop closure**: detects when the camera returns to a previously visited location
- **Bundle adjustment**: globally refines camera poses and map point positions

### Tracking methods

```python
class TrackingMethod(Enum):
    MARKER_BASED  # ArUco / QR marker detection
    MARKERLESS    # feature-based (ORB, SIFT)
    SLAM          # full visual SLAM
    INSIDE_OUT    # headset-mounted cameras
    OUTSIDE_IN    # external camera array
```

### Spatial anchors

`SpatialAnchor` objects persist virtual-to-world alignments:

```python
@dataclass
class SpatialAnchor:
    anchor_id: str
    world_position: Vector3D
    world_orientation: Transform3D
    confidence: float
    tracking_quality: float = 1.0
    persistence_data: bytes   # serialised anchor for cross-session recovery
```

`VirtualObject` carries visibility, scale, occlusion flag, shadow casting, and per-object material properties. `RealWorldObject` tracks detected real-world items with bounding boxes and per-detection confidence.

---

## Event System

`HolographicEventSystem` is the internal message bus connecting all subsystems. It is separate from (but compatible with) the Cognitive Blackboard's `EventBus`.

### Architecture

- **Async-first**: `emit()` is `async`, queued for processing by the background `_process_events()` coroutine. `emit_sync()` is available for synchronous callers.
- **Priority levels**: `LOW | NORMAL | HIGH | CRITICAL` — subscribers sorted and called in priority order.
- **Wildcard matching**: event names support `fnmatch` patterns (e.g. `"engine.*"` matches all engine events).
- **Weak references**: optional `weak_ref=True` on `subscribe()` prevents memory leaks from anonymous lambda subscribers.
- **History**: last 1,000 events are stored and queryable by name.
- **Network distribution**: stub for distributing events across a holographic node network (not yet implemented).

### Built-in system events

```
system.startup / shutdown / pause / resume / error
engine.initialized / started / stopped / paused / resumed / error / frame_batch
config.updated
display.calibrated
gesture.detected
hologram.created / updated / destroyed
```

### Example subscriber

```python
engine.event_system.subscribe(
    "gesture.detected",
    handle_gesture,
    priority=EventPriority.HIGH
)

async def handle_gesture(event_data: dict):
    if event_data.get("gesture") == "pinch":
        await engine.ar_manager.select_object(event_data["position"])
```

---

## Integration: Connecting to the Cognitive Blackboard

The holographic module does not yet have a Blackboard adapter, but the integration path is clear. The natural pattern (as seen in the [Quantum Blackboard Adapter design](Quantum-Computing#open-research-questions) in Issue #53) would be a `HolographicBlackboardAdapter`:

```python
class HolographicBlackboardAdapter:
    """Bridge: HolographicEventSystem → Cognitive Blackboard"""

    def __init__(self, engine: HolographicEngine, blackboard: CognitiveBlackboard):
        self.engine = engine
        self.blackboard = blackboard

    async def register(self):
        # Forward gesture events to Blackboard
        self.engine.event_system.subscribe(
            "gesture.detected",
            self._on_gesture,
            priority=EventPriority.HIGH,
        )
        # Forward render-ready frames for downstream processing
        self.engine.add_frame_callback(self._on_frame)

    async def _on_gesture(self, event_data: dict):
        await self.blackboard.write(
            key="holographic.gesture",
            value=event_data,
            source="holographic_engine",
            tags=["gesture", "interaction", "spatial"],
        )

    async def _on_frame(self, delta_time: float, frame_count: int):
        # Publish frame metadata — not raw pixels (too large)
        if frame_count % 30 == 0:
            await self.blackboard.write(
                key="holographic.frame_stats",
                value=self.engine.get_performance_metrics(),
                source="holographic_engine",
                tags=["performance", "display"],
            )
```

The Blackboard's subscriber system could then feed gesture events to the [CognitiveCycle](CognitiveCycle)'s perception phase, allowing downstream modules (reasoning, safety, consciousness) to respond to holographic interaction.

---

## Open Research Questions

### 1. What physical display hardware would this target?

The module currently simulates volumetric rendering in software. Real display options span a wide range:

- **Swept-volume displays** (spinning mirror + projector): true 3D voxels, limited FOV, mechanical
- **Static-volume displays** (photopolymer, two-photon absorption): no moving parts, very low resolution
- **Light field displays** (lenticular arrays, directional backlights): 2D screen + depth cues, no true occlusion
- **Coherent holographic displays** (SLMs, spatial light modulators): true wavefront reconstruction, requires laser illumination and enormous computational bandwidth (≈ teraflops for real-time CGH)

The module's `display_type` config already distinguishes `volumetric | light_field | holographic` — the right path depends on which hardware direction matures first.

### 2. Neural rendering and implicit representations?

The current light field processor uses a 4D array (explicit representation). Neural radiance fields (NeRF) and related implicit neural representations learn a continuous 5D scene function from sparse views. Could the `LightFieldProcessor` be extended with a NeRF backend for:
- More compact scene storage (a few MB vs. 400+ MB for a dense 4D array)
- View-dependent lighting effects
- Continuous (not grid-quantised) refocus

The `synthesize_view()` interface is the right abstraction — the backend could swap from bilinear array lookup to neural inference without changing the API.

### 3. Coherent holography vs. incoherent simulation

The current `LightRay` has `wavelength`, `polarization`, and `phase` fields — the building blocks of wave optics — but the rendering path does not use them (intensity is purely ray-based). True holographic reconstruction requires computing the **interference pattern** of coherent wavefronts on a diffraction-limited spatial light modulator. This is computer-generated holography (CGH):

```
Hologram(x, y) = Σ_points  A_i · exp(i · k · r_i(x, y))
```

where `k = 2π/λ` and `r_i` is the distance from scene point `i` to hologram pixel `(x, y)`. Real-time CGH for a scene with millions of points requires hardware acceleration (GPU/FPGA) or approximate algorithms (point-cloud decomposition, FFT-based methods, neural CGH).

### 4. Gesture recognition model

The hand tracker's detection backend is a stub. What model family is best for 3D holographic-context gesture input?

- **MediaPipe Hands**: 21-landmark, real-time, CPU-capable, well-tested — good baseline
- **Custom depth-based models**: depth cameras (structured light / ToF) give direct 3D without stereo triangulation, but add hardware dependency
- **Event cameras**: ultra-low latency, high temporal resolution — ideal for fast gesture tracking but require new model architectures

### 5. Physics semantics for "holograms"

`PhysicsProperties` includes `coherence_stability`, `interference_sensitivity`, and `quantum_entanglement` — properties that have no classical counterpart. What do these mean in practice?

- `coherence_stability` could model how disruption (ambient light, vibration) degrades hologram fidelity
- `interference_sensitivity` could gate whether two overlapping holograms destructively interfere
- `quantum_entanglement` is currently `0.0` everywhere — a placeholder for correlated hologram pairs that update together

---

## See Also

- [Architecture](Architecture) — how the holographic module fits into the layered ASI stack
- [Cognitive Blackboard](Cognitive-Blackboard) — the integration target for gesture/display events
- [CognitiveCycle](CognitiveCycle) — the 9-phase loop that holographic output would feed into
- [Module Index](Module-Index) — all 29 modules with LOC and status
- [Issue #53](https://github.com/web3guru888/asi-build/issues/53) — Wire quantum module into Blackboard (same adapter pattern)
- [Roadmap](Roadmap) — Phase 3/4 plans for interface layer development
