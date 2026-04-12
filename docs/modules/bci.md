# BCI (Brain-Computer Interface)

> **Maturity**: `experimental` · **Adapter**: `BCIBlackboardAdapter`

Brain-computer interface integration for neural signal acquisition and decoding. Supports EEG and fNIRS signal processing pipelines, motor imagery classification using CSP+LDA, P300 speller detection, and SSVEP detection via canonical correlation analysis. Uses lazy loading for heavy optional dependencies (MNE-Python, PyTorch).

## Key Classes

| Class | Description |
|-------|-------------|
| `BCIManager` | Core BCI session manager |
| `SignalProcessor` | Raw signal filtering and artifact removal |
| `NeuralDecoder` | Neural signal → intent decoding |
| `EEGProcessor` | EEG-specific processing pipeline |
| `MotorImageryClassifier` | CSP+LDA motor imagery |
| `P300Speller` | P300 evoked potential detection |
| `SSVEPDetector` | CCA-based SSVEP detection |
| `BCIConfig` | Configuration dataclass |

## Example Usage

```python
from asi_build.bci import BCIManager, BCIConfig
config = BCIConfig(sample_rate=256, channels=["C3", "C4", "Cz"])
bci = BCIManager(config=config)
bci.start_session()
decoded = bci.decode_intent(signal_data)
```

## Blackboard Integration

BCIBlackboardAdapter publishes decoded neural intents, signal quality metrics, and BCI session state; integrates with the consciousness module for neural-cognitive bridging.
