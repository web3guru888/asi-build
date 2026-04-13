# Brain-Computer Interface (BCI) Module

> **Module path**: `src/asi_build/bci/`  
> **Size**: 19 files · 8,294 LOC  
> **Status**: ✅ Functional — EEG processing, motor imagery, P300, SSVEP, neural decoding all operational  
> **Paradigms**: Motor imagery (MI), P300 event-related potentials, SSVEP, thought-to-text, neurofeedback

The `bci` module is ASI:BUILD's sensory bridge between biological neural signals and the cognitive architecture. It reads electrical signals from the brain — EEG channels, event-related potentials, steady-state responses — and converts them into commands, confidence scores, and decoded intentions that can flow into the Cognitive Blackboard, the knowledge graph, or any downstream module.

This is where the architecture becomes truly bidirectional: the brain isn't just a data source, it's a participant in the cognitive loop.

---

## Architecture

```
bci/
├── core/
│   ├── bci_manager.py        # Top-level BCI session manager
│   ├── config.py             # BCIConfig: device, channels, sampling rate
│   ├── device_interface.py   # Hardware abstraction (Emotiv, OpenBCI, LSL)
│   ├── signal_processor.py   # ProcessedSignal dataclass + base filtering
│   └── neural_decoder.py     # Ensemble classifier: LDA, SVM, RF, MLP
├── eeg/
│   ├── eeg_processor.py      # EEGProcessor: epoch extraction, band power
│   ├── artifact_removal.py   # ICA, EOG/EMG/ECG removal, adaptive filters
│   ├── frequency_analysis.py # Delta/theta/alpha/beta/gamma PSD
│   └── spatial_filters.py    # CSP, Laplacian, beamforming
├── motor_imagery/
│   ├── classifier.py         # MotorImageryClassifier (CSP + FBCSP + DL)
│   ├── csp_processor.py      # Common Spatial Patterns w/ multi-band
│   └── feature_extractor.py  # Band power, time-frequency, Riemannian features
├── p300/
│   └── speller.py            # P300Speller: stimulus controller + classifier
├── ssvep/
│   └── detector.py           # SSVEPDetector: CCA, FBCCA, PSD
├── thought_text/             # ThoughtToTextConverter (speech imagery → text)
├── neurofeedback/            # Real-time neurofeedback protocols
├── prosthetic/               # Prosthetic limb control interface
├── neural_control/           # Generic neural control loop
├── brain_state/              # Cognitive state estimation from EEG bands
└── utils/
    ├── metrics.py            # Classification metrics, ITR (bits/min)
    └── signal_utils.py       # Windowing, resampling helpers
```

---

## Core Concepts

### Signal Pipeline

Every BCI interaction follows the same pipeline:

```
EEG electrodes
    → DeviceInterface (hardware abstraction, LSL stream)
    → SignalProcessor (bandpass filter, notch filter, re-reference)
    → ArtifactRemover (ICA decomposition, EOG/EMG/ECG templates)
    → [Paradigm-specific processor: EEGProcessor / CSPProcessor / SSVEPDetector]
    → NeuralDecoder (ensemble: LDA + SVM + RF + MLP → VotingClassifier)
    → DecodingResult(predicted_class, confidence, probabilities, processing_time)
```

The `ProcessedSignal` dataclass passes data between stages:

```python
@dataclass
class ProcessedSignal:
    data: np.ndarray        # (n_channels, n_samples)
    timestamps: np.ndarray  # per-sample timestamps (seconds)
    sampling_rate: float    # Hz
    channels: List[str]     # electrode labels (e.g. ["C3", "Cz", "C4"])
    artifacts_removed: bool
    quality_score: float    # 0.0–1.0
    metadata: Dict[str, Any]
```

### BCIConfig

All BCI components share a single config:

```python
from asi_build.bci.core.config import BCIConfig

config = BCIConfig(
    device=DeviceConfig(
        device_type="openbci",
        sampling_rate=250,        # Hz
        channels=["C3", "Cz", "C4", "Fz", "Pz"],
        n_channels=5,
        buffer_size=2.0,          # seconds
    ),
    processing=ProcessingConfig(
        bandpass_low=0.5,         # Hz
        bandpass_high=40.0,
        notch_frequency=50.0,     # or 60.0 for USA
        epoch_length=1.0,         # seconds
        overlap=0.5,
    )
)
```

---

## Motor Imagery

Motor imagery (MI) is one of the most studied BCI paradigms. When you imagine moving your left hand, the contralateral motor cortex activates — generating a detectable decrease in mu (8–12 Hz) and beta (13–30 Hz) power known as **Event-Related Desynchronization (ERD)**.

### Common Spatial Patterns (CSP)

CSP finds spatial filters that maximize variance for one class while minimizing it for another. For a 2-class problem (left vs right hand imagery):

```
W = CSP(X_left, X_right)   # learns (n_channels, n_components) projection
features = log(var(W.T @ X))  # band power in CSP subspace
```

`CSPProcessor` extends this with **Filter Bank CSP (FBCSP)**: apply CSP independently in multiple frequency sub-bands (mu: 8–12 Hz, beta: 13–30 Hz, low-gamma: 30–40 Hz) and concatenate features. This improves robustness when the discriminative frequencies vary across subjects.

### Feature Extraction

`MotorImageryFeatureExtractor` computes:

| Feature family | Description |
|---|---|
| Band power | Log-variance in delta, theta, alpha, beta, gamma sub-bands |
| FBCSP features | CSP spatial filters per frequency band |
| Riemannian features | Covariance matrices on the SPD manifold |
| Time-frequency | Wavelet coefficients, instantaneous frequency |

### Classification Pipeline

```python
from asi_build.bci.motor_imagery.classifier import MotorImageryClassifier

clf = MotorImageryClassifier(config)
clf.train(X_train, y_train)      # X: (n_trials, n_channels, n_samples)

result = clf.predict(X_test)
# MotorImageryPrediction:
#   predicted_class: "left_hand" | "right_hand" | "feet" | "tongue"
#   confidence: 0.87
#   csp_patterns: np.ndarray  (for visualization)
#   band_powers: {"alpha": 0.23, "beta": 0.45, ...}
```

The classifier pipeline: `StandardScaler → CSPProcessor → FBCSP → SVM (RBF kernel)` with cross-validated hyperparameter search (`GridSearchCV`).

---

## P300 Speller

The P300 speller exploits the **P300 event-related potential** — a positive deflection ~300 ms after a rare, task-relevant stimulus. Flash rows/columns of a character matrix; the row/column containing the target character evokes a P300.

### Information Transfer Rate

The P300 speller's performance is measured in **bits per minute** (ITR):

```
ITR = log2(N) + P·log2(P) + (1-P)·log2((1-P)/(N-1))   [bits/symbol]
bits/min = ITR × (60 / trial_duration_seconds)
```

For a 6×6 matrix (N=36), 100% accuracy, 1s trial: ~53 bits/symbol × 60 = ~53 bpm.

### P300Speller Usage

```python
from asi_build.bci.p300.speller import P300Speller

speller = P300Speller(config)
speller.start()              # initializes stimulus controller

# Epoch collection loop
for epoch in speller.collect_epochs(n_repetitions=5):
    prediction = speller.classify(epoch)
    
result: SpellerResult = speller.get_selection()
# SpellerResult:
#   predicted_character: "A"
#   confidence: 0.92
#   trial_count: 5
#   processing_time: 4.8   (seconds)
```

---

## SSVEP Detection

Steady-State Visual Evoked Potentials (SSVEP) are EEG responses at the frequency of a flickering visual stimulus. Stare at a 15 Hz flickering LED → EEG shows a 15 Hz peak in occipital channels (Oz, O1, O2).

Advantages: no training required per subject (just calibration), high ITR (~100+ bpm for expert users).

### Detection Methods

`SSVEPDetector` implements three methods, ensemble-scored:

| Method | Description |
|---|---|
| **PSD** | Welch power spectral density — peak at target frequency + harmonics |
| **CCA** | Canonical Correlation Analysis between EEG and reference sinusoids |
| **FBCCA** | Filter Bank CCA — CCA in multiple sub-bands, weighted sum |

```python
from asi_build.bci.ssvep.detector import SSVEPDetector

detector = SSVEPDetector(config, target_frequencies=[8.0, 10.0, 12.0, 15.0])
result = detector.detect(processed_signal)

# SSVEPDetection:
#   detected_frequency: 12.0
#   confidence: 0.89
#   snr: 8.4          (dB above noise floor)
#   harmonics_detected: [12.0, 24.0, 36.0]
#   method_scores: {"psd": 0.85, "cca": 0.91, "fbcca": 0.93}
```

---

## Neural Decoder (Ensemble)

`NeuralDecoder` is a meta-classifier that combines paradigm-specific features:

```python
# Ensemble construction
estimators = [
    ("lda", LinearDiscriminantAnalysis()),
    ("svm", SVC(probability=True, kernel="rbf")),
    ("rf", RandomForestClassifier(n_estimators=100)),
    ("mlp", MLPClassifier(hidden_layer_sizes=(256, 128, 64))),
]
model = VotingClassifier(estimators=estimators, voting="soft")
```

**Soft voting**: each classifier outputs class probabilities; the final prediction is the argmax of the averaged probability vector. This is significantly more robust than hard majority voting when classes are close.

**Online adaptation**: the decoder supports incremental learning via `partial_fit()` — useful when the user's neural patterns drift during a session (common in EEG due to fatigue, electrode impedance changes, cognitive state shifts).

---

## EEG Processing

### Artifact Removal

Real EEG signals are noisy. `ArtifactRemover` handles:

| Artifact | Source | Removal |
|---|---|---|
| EOG | Eye blinks/movements | ICA component classification + template subtraction |
| EMG | Muscle tension | High-frequency threshold + ICA |
| ECG | Heart R-peak | ICA + adaptive filter (heartbeat template) |
| Line noise | Power grid 50/60 Hz | FIR notch filter |
| Movement | Cable movement | Z-score channel rejection |

ICA decomposition:

```python
ica = FastICA(n_components=n_channels, random_state=42)
components = ica.fit_transform(raw_data.T).T   # (n_components, n_samples)
# → classify each component as artifact or signal
# → zero out artifact components
# → reconstruct: cleaned = ica.inverse_transform(...)
```

### Frequency Analysis

`FrequencyAnalyzer` computes band power via Welch's method for all canonical EEG bands:

| Band | Hz range | Cognitive correlate |
|---|---|---|
| Delta | 0.5–4 | Deep sleep, unconscious processing |
| Theta | 4–8 | Drowsiness, memory encoding, meditation |
| Alpha | 8–12 | Relaxed wakefulness, visual suppression |
| Beta | 13–30 | Active thinking, motor control, attention |
| Gamma | 30–100 | Higher cognition, binding, SSVEP |

### Spatial Filtering

`SpatialFilterBank` provides:
- **Laplacian filter**: local surface Laplacian to reduce volume conduction
- **Common Average Reference (CAR)**: subtract mean across all channels
- **CSP**: supervised spatial filter for discrimination (see above)
- **Beamforming**: minimum variance distortionless response (MVDR) for source localization

---

## Thought-to-Text

The `thought_text` sub-module attempts to decode **imagined speech** — neural patterns generated when you silently "think" words without vocalizing. This is one of the hardest open problems in BCI research.

Components:
- `SpeechImageryDecoder`: classifies phonemes/words from EEG during imagined speech
- `ThoughtToTextConverter`: chains phoneme sequences into words using a language model
- `NeuralLanguageModel`: neural LM that constrains word predictions using prior context
- `TextPredictor`: next-word prediction for communication acceleration

**Current limitations**: Imagined speech classification accuracies are low (typically 30–60% for small vocabularies, chance = 1/N). This is reflected in the module's import guards — components that depend on unavailable hardware or large neural models fail gracefully with `None` stubs.

---

## Neurofeedback

The `neurofeedback` sub-module supports real-time feedback protocols:
- **Alpha/theta training**: increase relaxation (used in meditation, PTSD treatment)
- **SMR training**: enhance sensorimotor rhythm for attention/sleep
- **Gamma entrainment**: preliminary evidence for working memory enhancement
- **P300 latency tracking**: cognitive load / reaction time measurement

Neurofeedback creates a closed loop: EEG → decode brain state → render visual/auditory feedback → user adjusts mental state → EEG changes → repeat.

---

## Brain State Module

`brain_state/` estimates high-level cognitive states from the EEG band power profile:

```python
# Hypothetical mapping (simplified)
def estimate_state(band_powers: Dict[str, float]) -> CognitiveState:
    alpha = band_powers["alpha"]
    beta = band_powers["beta"]
    theta = band_powers["theta"]
    
    if alpha > 0.6 and beta < 0.3:
        return CognitiveState.RELAXED
    elif beta > 0.5 and theta < 0.2:
        return CognitiveState.FOCUSED
    elif theta > 0.5:
        return CognitiveState.DROWSY
    ...
```

These cognitive state estimates can feed directly into the `bio_inspired` module's `CognitiveState` enum — a natural integration point (see [Bio-Inspired](Bio-Inspired) wiki page).

---

## Integration with ASI:BUILD

### Cognitive Blackboard

The BCI module can publish decoded intentions as Blackboard entries, making them available to any downstream module:

```python
from asi_build.bci.core.neural_decoder import NeuralDecoder
from asi_build.integration.cognitive_blackboard import CognitiveBlackboard, BlackboardEntry

blackboard = CognitiveBlackboard()
decoder = NeuralDecoder(config)

async def bci_publisher_loop(signal_stream):
    async for signal in signal_stream:
        result = decoder.decode(signal)
        if result.confidence > 0.75:
            entry = BlackboardEntry(
                key=f"bci.intent.{result.predicted_class}",
                value={
                    "class": result.predicted_class,
                    "confidence": result.confidence,
                    "probabilities": result.probabilities,
                    "timestamp": time.time(),
                },
                source="bci",
                ttl=2.0,   # seconds — stale intents expire
            )
            await blackboard.write(entry)
```

Downstream modules like `reasoning`, `safety`, and `agi_communication` can then read `bci.intent.*` keys to understand user intent in real time.

See [Issue #64](https://github.com/web3guru888/asi-build/issues/64) — BCIBlackboardAdapter design.

### Bio-Inspired Module

BCI brain state estimates → `CognitiveState` → bio_inspired module uses state-dependent consolidation and neuromodulation weights. This creates a tight loop: the brain influences the cognitive simulation, which in turn adjusts attention/arousal models.

### CognitiveCycle Integration

In a full [CognitiveCycle](CognitiveCycle), BCI would occupy the **Sensory Encoding** phase (Phase 1):

```
Phase 1: Sensory Encoding
  → BCI reads EEG epoch
  → Decodes intent or cognitive state
  → Writes to Blackboard: bci.intent.*, bci.state.*
Phase 2: Attention Selection
  → attention module reads bci.intent.* — boosts relevance of user-attended concepts
...
```

---

## Open Research Questions

1. **Latency**: Current motor imagery pipelines have ~300–500 ms end-to-end latency. Is 100 ms achievable? What's the minimum for a fluid human-AI interaction loop?

2. **Session transfer**: CSP filters are highly subject-specific and drift within sessions. Can we use Riemannian geometry or domain adaptation to build truly subject-independent classifiers?

3. **Thought-to-text at scale**: Current imagined-speech decoders work on small vocabularies (5–50 words). What would it take to decode free-form thought? Large neural models trained on fMRI + EEG + MEG simultaneously?

4. **Cognitive load as a modulator**: If the BCI detects high cognitive load (elevated theta, reduced alpha), should the cognitive cycle slow down, simplify outputs, or offload computation? Who decides?

5. **Ethical boundary**: If ASI:BUILD can read brain state in real time, what signals should it be allowed to act on? How do we ensure user agency over what the system responds to?

---

## Related Modules

- [Bio-Inspired](Bio-Inspired) — CognitiveState maps to bio_inspired neuromodulation
- [Cognitive Blackboard](Cognitive-Blackboard) — BCI publishes decoded intents
- [CognitiveCycle](CognitiveCycle) — BCI occupies Sensory Encoding phase
- [Safety Module](Safety-Module) — ethical verification of brain-read commands
- [Consciousness Module](Consciousness-Module) — neural correlates of consciousness in EEG

---

## Relevant Issues

- [Issue #64](https://github.com/web3guru888/asi-build/issues/64): BCIBlackboardAdapter — wire neural decoder output to Cognitive Blackboard
- [Issue #13](https://github.com/web3guru888/asi-build/issues/13): Add type hints to bio_inspired module (similar work needed for BCI)
- [Issue #18](https://github.com/web3guru888/asi-build/issues/18): End-to-end scenario tests — BCI could be the sensory input stage
