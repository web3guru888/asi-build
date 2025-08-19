# Brain-Computer Interface (BCI) Framework

A comprehensive, production-ready BCI framework for Kenny, providing state-of-the-art brain-computer interface capabilities.

## Overview

This BCI framework implements advanced neural signal processing, classification, and control systems for various BCI applications including motor imagery, P300 spellers, SSVEP detection, neurofeedback, and neural prosthetic control.

## Features

### Core Components
- **Signal Processing**: Advanced EEG signal processing with artifact removal, filtering, and feature extraction
- **Neural Decoding**: Multi-class classification with ensemble learning and online adaptation
- **Device Interface**: Unified interface for various BCI devices (EEG, EMG, fNIRS)
- **Real-time Processing**: Low-latency real-time neural signal analysis

### BCI Applications

#### 1. Motor Imagery Classification
- Common Spatial Patterns (CSP) with filter banks
- Multi-class support (left hand, right hand, feet, tongue)
- Online adaptation and learning
- Ensemble classification methods

#### 2. P300 Speller System
- Complete text input system using P300 responses
- Configurable character matrices (6x6, 8x8)
- Adaptive stimulus timing and repetitions
- Real-time character selection

#### 3. SSVEP Detection
- Steady-State Visual Evoked Potential detection
- Multiple frequency analysis methods (CCA, FBCCA, MSI)
- Harmonic detection and analysis
- High-speed communication interface

#### 4. Neurofeedback Training
- Real-time brain training protocols
- Alpha, beta, theta, and SMR training
- Customizable feedback modalities
- Session management and progress tracking

#### 5. Brain State Decoding
- Attention and workload monitoring
- Emotional state classification
- Cognitive load assessment
- Stress and arousal detection

#### 6. Neural Control
- Direct neural control of external devices
- Cursor control and navigation
- Robotic system integration
- Environmental control systems

#### 7. Thought-to-Text Conversion
- Imagined speech detection
- Language model integration
- Text prediction and autocomplete
- Advanced neural language processing

#### 8. Neural Prosthetic Control
- Prosthetic limb control
- Wheelchair navigation
- Assistive technology integration
- Environmental control systems

## Architecture

```
bci/
├── core/                    # Core BCI framework
│   ├── bci_manager.py      # Central BCI coordination
│   ├── signal_processor.py # Real-time signal processing
│   ├── neural_decoder.py   # Neural signal classification
│   ├── device_interface.py # Hardware abstraction layer
│   └── config.py          # Configuration management
├── eeg/                    # EEG processing modules
│   ├── eeg_processor.py    # Advanced EEG processing
│   ├── artifact_removal.py # Artifact removal techniques
│   ├── frequency_analysis.py # Frequency domain analysis
│   └── spatial_filters.py  # Spatial filtering methods
├── motor_imagery/          # Motor imagery BCI
│   ├── classifier.py       # MI classification
│   ├── csp_processor.py    # Common Spatial Patterns
│   └── feature_extractor.py # MI feature extraction
├── p300/                   # P300 speller system
│   ├── speller.py          # P300 speller implementation
│   ├── stimulus_controller.py # Stimulus presentation
│   └── p300_classifier.py  # P300 classification
├── ssvep/                  # SSVEP detection
│   ├── detector.py         # SSVEP detection algorithms
│   ├── frequency_analyzer.py # Frequency analysis
│   └── stimulus_generator.py # Visual stimulus generation
├── neurofeedback/          # Neurofeedback training
│   ├── trainer.py          # Neurofeedback trainer
│   ├── protocols.py        # Training protocols
│   └── feedback_controller.py # Feedback control
├── brain_state/            # Brain state decoding
│   ├── decoder.py          # Brain state classifier
│   ├── attention_monitor.py # Attention monitoring
│   └── workload_estimator.py # Cognitive workload
├── neural_control/         # Neural control interface
│   ├── controller.py       # Neural controller
│   ├── cursor_control.py   # Cursor control
│   └── device_interface.py # Device control
├── thought_text/           # Thought-to-text conversion
│   ├── converter.py        # Thought-text converter
│   ├── speech_imagery_decoder.py # Speech imagery
│   └── language_model.py   # Language processing
├── prosthetic/             # Neural prosthetic control
│   ├── controller.py       # Prosthetic controller
│   ├── limb_control.py     # Limb control
│   └── wheelchair_controller.py # Wheelchair control
├── datasets/               # Data handling
│   ├── loader.py           # Dataset loading
│   ├── preprocessor.py     # Data preprocessing
│   └── generator.py        # Synthetic data generation
├── models/                 # Machine learning models
│   ├── deep_learning.py    # Deep learning models
│   ├── traditional_ml.py   # Traditional ML models
│   └── ensemble.py         # Ensemble methods
└── utils/                  # Utilities
    ├── signal_utils.py     # Signal processing utilities
    ├── visualization.py    # Visualization tools
    └── metrics.py          # Performance metrics
```

## Quick Start

### Basic Usage

```python
from kenny.src.bci import BCIManager, BCIConfig

# Initialize BCI system
config = BCIConfig()
bci_manager = BCIManager(config)

# Start a motor imagery session
session_id = await bci_manager.start_session(
    device_type="simulated_eeg",
    tasks=["motor_imagery"],
    channels=["C3", "C4", "Cz"]
)

# Add result callback
def handle_results(result):
    print(f"Predicted class: {result.predicted_class}")
    print(f"Confidence: {result.confidence:.2f}")

bci_manager.add_result_callback(handle_results)

# Calibrate motor imagery classifier
calibration_result = await bci_manager.calibrate(
    task_type="motor_imagery",
    duration=60.0,
    trials=20
)

print(f"Calibration accuracy: {calibration_result['accuracy']:.2f}")
```

### Motor Imagery Classification

```python
from kenny.src.bci.motor_imagery import MotorImageryClassifier

# Initialize classifier
mi_classifier = MotorImageryClassifier(config)

# Train with EEG epochs and labels
training_result = mi_classifier.train(
    training_epochs=eeg_epochs,  # (n_trials, n_channels, n_samples)
    labels=trial_labels
)

# Real-time prediction
prediction = mi_classifier.predict(single_epoch)
print(f"Predicted movement: {prediction.predicted_class}")
print(f"Confidence: {prediction.confidence:.2f}")
```

### P300 Speller

```python
from kenny.src.bci.p300 import P300Speller

# Initialize P300 speller
speller = P300Speller(config)

# Calibrate with target characters
calibration_result = await speller.calibrate(
    target_characters=['A', 'B', 'C', 'D', 'E'],
    trials_per_character=10
)

# Start spelling session
await speller.start_spelling_session()

# Add character selection callback
def on_character_selected(char, text, result):
    print(f"Selected: {char}, Text: '{text}'")

speller.add_character_callback(on_character_selected)
```

### SSVEP Detection

```python
from kenny.src.bci.ssvep import SSVEPDetector

# Initialize SSVEP detector
ssvep_detector = SSVEPDetector(config)

# Detect SSVEP response
detection_result = ssvep_detector.detect(eeg_data)

print(f"Detected frequency: {detection_result.detected_frequency} Hz")
print(f"Confidence: {detection_result.confidence:.2f}")
print(f"SNR: {detection_result.snr:.2f}")
```

### Neurofeedback Training

```python
from kenny.src.bci.neurofeedback import NeurofeedbackTrainer

# Initialize neurofeedback trainer
nf_trainer = NeurofeedbackTrainer(config)

# Start alpha training session
session_result = await nf_trainer.start_session(
    protocol="alpha_enhancement",
    duration=600,  # 10 minutes
    target_channels=["O1", "O2"]
)

# Monitor real-time feedback
def feedback_callback(feedback_data):
    alpha_power = feedback_data['alpha_power']
    print(f"Alpha power: {alpha_power:.2f}")

nf_trainer.add_feedback_callback(feedback_callback)
```

## Configuration

The BCI system is highly configurable through the `BCIConfig` class:

```python
from kenny.src.bci.core import BCIConfig

config = BCIConfig()

# Device configuration
config.device.sampling_rate = 250.0
config.device.channels = ['C3', 'C4', 'Cz', 'O1', 'O2']

# Signal processing configuration
config.signal_processing.bandpass_low = 0.5
config.signal_processing.bandpass_high = 50.0
config.signal_processing.enable_ica = True

# Classification configuration
config.classification.confidence_threshold = 0.7
config.classification.calibration_trials = 20

# Task-specific configurations
config.motor_imagery['classes'] = ['left_hand', 'right_hand', 'feet']
config.p300['flash_duration'] = 0.1
config.ssvep['frequencies'] = [8.0, 10.0, 12.0, 14.0]
```

## Supported Devices

- **Simulated EEG Device**: For testing and development
- **OpenBCI**: Full support for OpenBCI devices via BrainFlow
- **Emotiv**: Support for Emotiv headsets
- **g.tec**: Support for g.tec amplifiers
- **Custom Devices**: Extensible device interface

## Performance Metrics

The framework provides comprehensive performance monitoring:

- **Accuracy**: Classification accuracy across tasks
- **Latency**: Real-time processing latency
- **Throughput**: Information transfer rate
- **Reliability**: System uptime and error rates
- **Signal Quality**: EEG signal quality assessment

## Testing

Run the BCI test suite:

```bash
# Run all BCI tests
python -m pytest src/bci/tests/

# Run specific module tests
python -m pytest src/bci/tests/test_motor_imagery.py
python -m pytest src/bci/tests/test_p300.py
python -m pytest src/bci/tests/test_ssvep.py

# Run with coverage
python -m pytest --cov=src/bci src/bci/tests/
```

## Integration with Kenny

The BCI framework integrates seamlessly with Kenny's main systems:

```python
# In Kenny's intelligent agent
from kenny.src.bci import BCIManager

class IntelligentAgent:
    def __init__(self):
        self.bci_manager = BCIManager()
        
    async def process_neural_command(self, command):
        # Process BCI commands for Kenny control
        if command.type == "motor_imagery":
            await self.handle_motor_command(command)
        elif command.type == "p300":
            await self.handle_text_input(command)
```

## Extensions and Plugins

The framework supports extensions for:

- Custom signal processing algorithms
- New classification methods
- Additional BCI paradigms
- Device drivers
- Visualization plugins

## License

This BCI framework is part of the Kenny project and follows the same licensing terms.

## Contributing

Contributions are welcome! Please see the main Kenny repository for contribution guidelines.

## References

1. Blankertz, B., et al. (2008). The BCI competition III: Validating alternative approaches to actual BCI problems.
2. Farwell, L. A., & Donchin, E. (1988). Talking off the top of your head: toward a mental prosthesis.
3. Pfurtscheller, G., & Neuper, C. (2001). Motor imagery and direct brain-computer communication.
4. Zhu, D., et al. (2010). A survey of stimulation methods used in SSVEP-based BCIs.

---

For more information, see the Kenny documentation and API reference.