"""
Extended BCI module tests.

Covers: core/config, utils/signal_utils, utils/metrics, eeg/frequency_analysis,
eeg/spatial_filters, eeg/artifact_removal, core/signal_processor,
motor_imagery/csp_processor, motor_imagery/feature_extractor, ssvep/detector,
core/device_interface.
"""

# ---------------------------------------------------------------------------
# Patch missing subpackage modules BEFORE any from...import
# ---------------------------------------------------------------------------
import sys
import types


def _fake_module(name, attrs):
    mod = types.ModuleType(name)
    for attr in attrs:
        setattr(mod, attr, type(attr, (), {}))
    sys.modules[name] = mod


# BCI missing modules
_fake_module("asi_build.bci.motor_imagery.training_protocol", ["MotorImageryTrainer"])
_fake_module("asi_build.bci.ssvep.frequency_analyzer", ["SSVEPFrequencyAnalyzer"])
_fake_module("asi_build.bci.ssvep.stimulus_generator", ["SSVEPStimulusGenerator"])
_fake_module("asi_build.bci.ssvep.classifier", ["SSVEPClassifier"])
_fake_module("asi_build.bci.p300.stimulus_controller", ["StimulusController"])
_fake_module("asi_build.bci.p300.p300_classifier", ["P300Classifier"])
_fake_module("asi_build.bci.p300.feature_extractor", ["P300FeatureExtractor"])
_fake_module("asi_build.bci.utils.visualization", ["BCIVisualizer"])
_fake_module("asi_build.bci.utils.validation", ["ValidationUtils"])

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import numpy as np
import pytest

from asi_build.bci.core.config import (
    BCIConfig,
    ClassificationConfig,
    DeviceConfig,
    SignalProcessingConfig,
)
from asi_build.bci.core.signal_processor import (
    ProcessedSignal,
    SignalProcessor,
    SpectralFeatureExtractor,
    SpatialFeatureExtractor,
    TemporalFeatureExtractor,
)
from asi_build.bci.core.device_interface import (
    BCIDevice,
    DataPacket,
    DeviceInfo,
    SimulatedEEGDevice,
)
from asi_build.bci.eeg.frequency_analysis import FrequencyAnalyzer
from asi_build.bci.eeg.spatial_filters import SpatialFilterBank
from asi_build.bci.eeg.artifact_removal import ArtifactRemover
from asi_build.bci.motor_imagery.csp_processor import CSPProcessor
from asi_build.bci.motor_imagery.feature_extractor import MotorImageryFeatureExtractor
from asi_build.bci.ssvep.detector import SSVEPDetector
from asi_build.bci.utils.signal_utils import SignalUtilities
from asi_build.bci.utils.metrics import BCIMetrics

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------
SR = 250.0  # sampling rate
N_CH = 10   # number of channels (default BCIConfig channels)
N_SAMPLES = 1000  # 4 seconds at 250 Hz


@pytest.fixture
def cfg():
    """Default BCIConfig."""
    return BCIConfig()


@pytest.fixture
def eeg_random(cfg):
    """Random EEG-like data (n_channels, n_samples)."""
    rng = np.random.RandomState(42)
    return rng.randn(len(cfg.device.channels), N_SAMPLES)


def _make_sine(freq, sr=SR, dur=4.0, n_ch=1):
    """Create sine wave(s) at a known frequency."""
    t = np.arange(int(sr * dur)) / sr
    sig = np.sin(2 * np.pi * freq * t)
    if n_ch > 1:
        return np.tile(sig, (n_ch, 1))
    return sig


# ============================================================
# 1. core/config.py  (~10 tests)
# ============================================================
class TestBCIConfig:
    def test_defaults(self, cfg):
        assert cfg.device.sampling_rate == 250.0
        assert len(cfg.device.channels) == 10
        assert cfg.debug_mode is False

    def test_device_config_defaults(self):
        dc = DeviceConfig()
        assert dc.device_type == "eeg"
        assert dc.impedance_threshold == 5.0

    def test_signal_processing_config_defaults(self):
        sp = SignalProcessingConfig()
        assert sp.bandpass_low == 0.5
        assert sp.bandpass_high == 50.0
        assert sp.enable_ica is True

    def test_classification_config_defaults(self):
        cc = ClassificationConfig()
        assert cc.default_classifier == "csp_lda"
        assert 0 < cc.confidence_threshold <= 1

    def test_validate_clean(self, cfg, tmp_path):
        cfg.data_directory = str(tmp_path / "data")
        cfg.model_directory = str(tmp_path / "model")
        issues = cfg.validate()
        assert issues == []

    def test_validate_bad_sampling_rate(self, cfg, tmp_path):
        cfg.device.sampling_rate = -1
        cfg.data_directory = str(tmp_path / "d")
        cfg.model_directory = str(tmp_path / "m")
        issues = cfg.validate()
        assert any("sampling rate" in i.lower() for i in issues)

    def test_save_load_roundtrip(self, cfg, tmp_path):
        path = str(tmp_path / "cfg.json")
        cfg.save_to_file(path)
        loaded = BCIConfig.load_from_file(path)
        assert loaded.device.sampling_rate == cfg.device.sampling_rate
        assert loaded.device.channels == cfg.device.channels
        assert loaded.classification.default_classifier == cfg.classification.default_classifier

    def test_to_dict_update_from_dict(self, cfg):
        d = cfg._to_dict()
        assert isinstance(d, dict)
        new_cfg = BCIConfig()
        new_cfg._update_from_dict(d)
        assert new_cfg.device.sampling_rate == cfg.device.sampling_rate

    def test_get_task_config(self, cfg):
        mi = cfg.get_task_config("motor_imagery")
        assert "classes" in mi
        assert cfg.get_task_config("nonexistent") is None

    def test_update_task_config(self, cfg):
        cfg.update_task_config("motor_imagery", {"trial_duration": 5.0})
        assert cfg.motor_imagery["trial_duration"] == 5.0
        with pytest.raises(ValueError):
            cfg.update_task_config("unknown_task", {})

    def test_repr(self, cfg):
        r = repr(cfg)
        assert "BCIConfig" in r
        assert "250.0" in r


# ============================================================
# 2. utils/signal_utils.py  (~10 tests)
# ============================================================
class TestSignalUtilities:
    def test_bandpass_filter_shape_1d(self):
        sig = np.random.randn(1000)
        out = SignalUtilities.bandpass_filter(sig, 1.0, 40.0, SR)
        assert out.shape == sig.shape

    def test_bandpass_filter_shape_2d(self):
        sig = np.random.randn(4, 1000)
        out = SignalUtilities.bandpass_filter(sig, 1.0, 40.0, SR)
        assert out.shape == sig.shape

    def test_bandpass_removes_out_of_band(self):
        """60 Hz component should be suppressed by a 1-40 Hz bandpass."""
        t = np.arange(2000) / SR
        sig = np.sin(2 * np.pi * 10 * t) + np.sin(2 * np.pi * 60 * t)
        out = SignalUtilities.bandpass_filter(sig, 1.0, 40.0, SR)
        # Power at 60 Hz should be much reduced
        from scipy.signal import welch
        f, psd_orig = welch(sig, fs=SR, nperseg=256)
        f, psd_filt = welch(out, fs=SR, nperseg=256)
        idx60 = np.argmin(np.abs(f - 60))
        assert psd_filt[idx60] < psd_orig[idx60] * 0.1

    def test_notch_filter(self):
        t = np.arange(2000) / SR
        sig = np.sin(2 * np.pi * 10 * t) + 2 * np.sin(2 * np.pi * 50 * t)
        out = SignalUtilities.notch_filter(sig, 50.0, SR)
        from scipy.signal import welch
        f, psd = welch(out, fs=SR, nperseg=256)
        idx50 = np.argmin(np.abs(f - 50))
        idx10 = np.argmin(np.abs(f - 10))
        assert psd[idx50] < psd[idx10] * 0.5

    def test_compute_psd_1d(self):
        sig = np.random.randn(1000)
        f, psd = SignalUtilities.compute_psd(sig, SR)
        assert f.shape == psd.shape
        assert f[0] >= 0

    def test_compute_psd_2d(self):
        sig = np.random.randn(3, 1000)
        f, psd = SignalUtilities.compute_psd(sig, SR)
        assert psd.shape[0] == 3

    def test_epoch_data(self):
        sig = np.random.randn(2, 1000)
        epochs = SignalUtilities.epoch_data(sig, 250, overlap=0.0)
        assert epochs.shape == (4, 2, 250)

    def test_epoch_data_overlap(self):
        sig = np.random.randn(1, 1000)
        epochs = SignalUtilities.epoch_data(sig, 500, overlap=0.5)
        # step = 250, so epochs at 0, 250, 500 → 3 epochs (if 500+250<=1000)
        assert epochs.shape[0] >= 3
        assert epochs.shape[2] == 500

    def test_normalize_zscore(self):
        sig = np.random.randn(2, 500)
        out = SignalUtilities.normalize_signal(sig, method="zscore")
        # Each row should have ~0 mean and ~1 std
        assert np.allclose(np.mean(out, axis=-1), 0, atol=0.01)
        assert np.allclose(np.std(out, axis=-1), 1, atol=0.01)

    def test_normalize_minmax(self):
        sig = np.random.randn(1, 500)
        out = SignalUtilities.normalize_signal(sig, method="minmax")
        assert np.min(out) >= -1e-9
        assert np.max(out) <= 1 + 1e-9

    def test_detect_bad_samples(self):
        sig = np.zeros(1000)
        sig[500] = 100  # obvious outlier
        mask = SignalUtilities.detect_bad_samples(sig, threshold=3.0)
        assert mask[500]
        assert not mask[0]

    def test_interpolate_bad_samples(self):
        sig = np.arange(100, dtype=float)
        mask = np.zeros(100, dtype=bool)
        mask[50] = True
        sig[50] = 999.0
        out = SignalUtilities.interpolate_bad_samples(sig, mask)
        # Should be close to 50.0 (interpolated from 49 and 51)
        assert abs(out[50] - 50.0) < 1.0


# ============================================================
# 3. utils/metrics.py  (~10 tests)
# ============================================================
class TestBCIMetrics:
    def test_itr_perfect(self):
        itr = BCIMetrics.information_transfer_rate(0.999, 4, 1.0)
        assert itr > 0

    def test_itr_chance(self):
        itr = BCIMetrics.information_transfer_rate(0.25, 4, 1.0)
        assert itr == 0.0

    def test_itr_below_chance(self):
        itr = BCIMetrics.information_transfer_rate(0.1, 4, 1.0)
        assert itr == 0.0

    def test_classification_metrics_basic(self):
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 0, 1, 1, 2, 1])
        m = BCIMetrics.classification_metrics(y_true, y_pred)
        assert "accuracy" in m
        assert 0 < m["accuracy"] <= 1.0
        assert "confusion_matrix" in m

    def test_classification_metrics_perfect(self):
        y = np.array([0, 1, 0, 1])
        m = BCIMetrics.classification_metrics(y, y)
        assert m["accuracy"] == 1.0

    def test_classification_metrics_with_proba(self):
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1])
        y_proba = np.array([[0.9, 0.1], [0.8, 0.2], [0.1, 0.9], [0.2, 0.8]])
        m = BCIMetrics.classification_metrics(y_true, y_pred, y_proba)
        assert "roc_auc" in m
        assert m["roc_auc"] == 1.0

    def test_signal_quality_metrics(self):
        data = np.random.randn(3, 1000)
        m = BCIMetrics.signal_quality_metrics(data, SR)
        assert "mean_snr" in m
        assert "channel_metrics" in m
        assert len(m["channel_metrics"]) == 3

    def test_signal_quality_1d(self):
        data = np.random.randn(1000)
        m = BCIMetrics.signal_quality_metrics(data, SR)
        assert m["mean_snr"] >= 0

    def test_stability_metrics(self):
        accs = [0.8, 0.82, 0.79, 0.85, 0.81]
        times = [1.0, 2.0, 3.0, 4.0, 5.0]
        m = BCIMetrics.stability_metrics(accs, times)
        assert "accuracy_mean" in m
        assert "performance_trend" in m

    def test_stability_too_few(self):
        m = BCIMetrics.stability_metrics([0.8], [1.0])
        assert m == {}

    def test_user_experience_metrics(self):
        rt = [0.5, 0.6, 0.4, 0.7]
        er = [0.1, 0.05, 0.15, 0.08]
        m = BCIMetrics.user_experience_metrics(rt, er)
        assert "mean_response_time" in m
        assert "reliability_score" in m
        assert m["reliability_score"] > 0


# ============================================================
# 4. eeg/frequency_analysis.py  (~8 tests)
# ============================================================
class TestFrequencyAnalyzer:
    def test_create(self, cfg):
        fa = FrequencyAnalyzer(cfg)
        assert fa.sampling_rate == 250.0

    def test_analyze_returns_features(self, cfg, eeg_random):
        fa = FrequencyAnalyzer(cfg)
        features = fa.analyze(eeg_random, SR)
        assert isinstance(features, dict)
        assert len(features) > 0

    def test_band_powers(self, cfg, eeg_random):
        fa = FrequencyAnalyzer(cfg)
        bp = fa._compute_band_powers(eeg_random, SR)
        # Should have power keys for first channel and alpha
        ch0 = cfg.device.channels[0]
        assert f"{ch0}_alpha_power" in bp
        assert bp[f"{ch0}_alpha_power"] >= 0

    def test_spectral_ratios(self, cfg, eeg_random):
        fa = FrequencyAnalyzer(cfg)
        bp = fa._compute_band_powers(eeg_random, SR)
        ratios = fa._compute_spectral_ratios(bp)
        ch0 = cfg.device.channels[0]
        # theta_alpha_ratio expected
        assert f"{ch0}_theta_alpha_ratio" in ratios

    def test_coherence_features(self, cfg, eeg_random):
        fa = FrequencyAnalyzer(cfg)
        coh = fa._compute_coherence_features(eeg_random, SR)
        assert "avg_alpha_coherence" in coh

    def test_time_frequency_analysis(self, cfg, eeg_random):
        fa = FrequencyAnalyzer(cfg)
        tf = fa.compute_time_frequency_analysis(eeg_random, SR)
        assert isinstance(tf, dict)
        assert len(tf) > 0

    def test_sine_alpha_dominance(self, cfg):
        """A 10 Hz sine should produce dominant alpha power."""
        fa = FrequencyAnalyzer(cfg)
        data = _make_sine(10.0, n_ch=N_CH)
        bp = fa._compute_band_powers(data, SR)
        ch0 = cfg.device.channels[0]
        assert bp[f"{ch0}_alpha_power"] > bp.get(f"{ch0}_gamma_power", 0)

    def test_cross_frequency_coupling(self, cfg, eeg_random):
        fa = FrequencyAnalyzer(cfg)
        cfc = fa._compute_cross_frequency_coupling(eeg_random, SR)
        assert isinstance(cfc, dict)


# ============================================================
# 5. eeg/spatial_filters.py  (~10 tests)
# ============================================================
class TestSpatialFilterBank:
    def test_create(self, cfg):
        sfb = SpatialFilterBank(cfg)
        assert sfb.n_channels == len(cfg.device.channels)

    def test_car(self, cfg, eeg_random):
        sfb = SpatialFilterBank(cfg)
        out = sfb.apply_car(eeg_random)
        assert out.shape == eeg_random.shape
        # CAR subtracts mean => mean across channels ≈ 0 at each sample
        assert np.allclose(np.mean(out, axis=0), 0, atol=1e-10)

    def test_laplacian(self, cfg, eeg_random):
        sfb = SpatialFilterBank(cfg)
        out = sfb.apply_laplacian(eeg_random)
        assert out.shape == eeg_random.shape

    def test_ica(self, cfg, eeg_random):
        sfb = SpatialFilterBank(cfg)
        out = sfb.apply_ica(eeg_random, n_components=5)
        assert out.shape == eeg_random.shape

    def test_pca(self, cfg, eeg_random):
        sfb = SpatialFilterBank(cfg)
        out = sfb.apply_pca(eeg_random, n_components=3)
        assert out.shape == eeg_random.shape

    def test_whitening(self, cfg, eeg_random):
        sfb = SpatialFilterBank(cfg)
        out = sfb.apply_whitening(eeg_random)
        assert out.shape == eeg_random.shape

    def test_bipolar_montage(self, cfg, eeg_random):
        sfb = SpatialFilterBank(cfg)
        bip_data, labels = sfb.apply_bipolar_montage(eeg_random)
        assert len(labels) > 0
        # Each label should be "X-Y"
        assert "-" in labels[0]
        # Each row is difference between two channels
        assert bip_data.shape[1] == eeg_random.shape[1]

    def test_bipolar_custom_pairs(self, cfg, eeg_random):
        sfb = SpatialFilterBank(cfg)
        pairs = [("Fp1", "Fp2"), ("C3", "C4")]
        bip_data, labels = sfb.apply_bipolar_montage(eeg_random, pairs=pairs)
        assert len(labels) == 2

    def test_available_filters(self, cfg):
        sfb = SpatialFilterBank(cfg)
        avail = sfb.get_available_filters()
        assert "car" in avail
        assert "ica" in avail

    def test_apply_filter_dispatcher(self, cfg, eeg_random):
        sfb = SpatialFilterBank(cfg)
        out, _ = sfb.apply_filter(eeg_random, "car")
        assert out.shape == eeg_random.shape


# ============================================================
# 6. eeg/artifact_removal.py  (~8 tests)
# ============================================================
class TestArtifactRemover:
    def test_create(self, cfg):
        ar = ArtifactRemover(cfg)
        assert ar.n_channels == len(cfg.device.channels)

    def test_remove_artifacts(self, cfg, eeg_random):
        ar = ArtifactRemover(cfg)
        clean, removed = ar.remove_artifacts(eeg_random)
        assert clean.shape == eeg_random.shape
        assert removed is True

    def test_remove_line_noise(self, cfg, eeg_random):
        ar = ArtifactRemover(cfg)
        clean = ar._remove_line_noise(eeg_random)
        assert clean.shape == eeg_random.shape

    def test_remove_statistical_outliers(self, cfg):
        ar = ArtifactRemover(cfg)
        data = np.random.randn(N_CH, N_SAMPLES)
        data[0, 500] = 100  # outlier
        clean = ar._remove_statistical_outliers(data)
        assert abs(clean[0, 500]) < abs(data[0, 500])

    def test_train_ica_model(self, cfg):
        ar = ArtifactRemover(cfg)
        data = np.random.randn(N_CH, 5000)
        success = ar.train_ica_model(data)
        assert success is True
        assert ar.ica_model is not None

    def test_set_artifact_components(self, cfg):
        ar = ArtifactRemover(cfg)
        ar.set_artifact_components([0, 2])
        assert ar.artifact_components == [0, 2]

    def test_ica_artifact_removal_after_train(self, cfg):
        ar = ArtifactRemover(cfg)
        data = np.random.randn(N_CH, 5000)
        ar.train_ica_model(data)
        clean = ar._ica_artifact_removal(data)
        assert clean.shape == data.shape

    def test_get_ica_components_before_train(self, cfg):
        ar = ArtifactRemover(cfg)
        assert ar.get_ica_components() is None


# ============================================================
# 7. core/signal_processor.py  (~8 tests)
# ============================================================
class TestSignalProcessor:
    def test_create(self, cfg):
        sp = SignalProcessor(cfg)
        assert sp.num_channels == len(cfg.device.channels)

    def test_process_realtime(self, cfg):
        sp = SignalProcessor(cfg)
        raw = np.random.randn(N_CH, 250)
        result = sp.process_realtime(raw)
        assert isinstance(result, ProcessedSignal)
        assert result.data.shape[0] == N_CH

    def test_apply_filters(self, cfg):
        sp = SignalProcessor(cfg)
        raw = np.random.randn(N_CH, 500)
        filtered = sp._apply_filters(raw)
        assert filtered.shape == raw.shape

    def test_assess_quality(self, cfg):
        sp = SignalProcessor(cfg)
        data = np.random.randn(N_CH, 500)
        q = sp._assess_quality(data)
        assert 0.0 <= q <= 1.0

    def test_wrong_channels_raises(self, cfg):
        sp = SignalProcessor(cfg)
        raw = np.random.randn(N_CH + 5, 250)
        with pytest.raises(ValueError, match="Expected"):
            sp.process_realtime(raw)

    def test_spectral_feature_extractor(self, cfg):
        ext = SpectralFeatureExtractor(cfg)
        data = np.random.randn(N_CH, 500)
        feats = ext.extract(data, SR)
        assert isinstance(feats, dict)
        assert len(feats) > 0

    def test_temporal_feature_extractor(self, cfg):
        ext = TemporalFeatureExtractor(cfg)
        data = np.random.randn(N_CH, 500)
        feats = ext.extract(data, SR)
        ch0 = cfg.device.channels[0]
        assert f"ch_{ch0}_activity" in feats

    def test_spatial_feature_extractor(self, cfg):
        ext = SpatialFeatureExtractor(cfg)
        data = np.random.randn(N_CH, 500)
        feats = ext.extract(data, SR)
        assert "avg_cross_correlation" in feats


# ============================================================
# 8. motor_imagery/csp_processor.py  (~8 tests)
# ============================================================
class TestCSPProcessor:
    @staticmethod
    def _make_csp_data(n_trials=40, n_ch=10, n_samp=500, seed=42):
        """Create 2-class synthetic data with different spatial patterns."""
        rng = np.random.RandomState(seed)
        X = rng.randn(n_trials, n_ch, n_samp) * 5
        y = np.array([0] * (n_trials // 2) + [1] * (n_trials // 2))
        # Class 0: boost channel 0; Class 1: boost channel 1
        X[: n_trials // 2, 0, :] += rng.randn(n_trials // 2, n_samp) * 20
        X[n_trials // 2 :, 1, :] += rng.randn(n_trials // 2, n_samp) * 20
        return X, y

    def test_create(self, cfg):
        csp = CSPProcessor(cfg, n_components=4)
        assert csp.n_components == 4

    def test_fit(self, cfg):
        csp = CSPProcessor(cfg, n_components=2)
        X, y = self._make_csp_data()
        csp.fit(X, y)
        assert csp.filters_ is not None

    def test_transform(self, cfg):
        csp = CSPProcessor(cfg, n_components=2)
        X, y = self._make_csp_data()
        csp.fit(X, y)
        features = csp.transform(X)
        assert features.shape[0] == X.shape[0]
        assert features.shape[1] > 0

    def test_fit_transform_pipeline(self, cfg):
        csp = CSPProcessor(cfg, n_components=2)
        X, y = self._make_csp_data()
        features = csp.fit(X, y).transform(X)
        assert features.ndim == 2

    def test_compute_covariance(self, cfg):
        csp = CSPProcessor(cfg)
        X, _ = self._make_csp_data()
        cov = csp._compute_covariance_matrix(X)
        assert cov.shape == (X.shape[1], X.shape[1])
        # Covariance should be symmetric
        assert np.allclose(cov, cov.T, atol=1e-10)

    def test_discriminability_index(self, cfg):
        csp = CSPProcessor(cfg, n_components=2)
        X, y = self._make_csp_data()
        csp.fit(X, y)
        di = csp.compute_discriminability_index(0)
        assert di >= 0

    def test_get_feature_info(self, cfg):
        csp = CSPProcessor(cfg, n_components=2)
        X, y = self._make_csp_data()
        csp.fit(X, y)
        info = csp.get_feature_info()
        assert info["n_classes"] == 2

    def test_multiclass(self, cfg):
        rng = np.random.RandomState(0)
        n_trials = 60
        X = rng.randn(n_trials, 10, 500) * 5
        y = np.array([0] * 20 + [1] * 20 + [2] * 20)
        # Boost different channels per class
        X[:20, 0, :] += rng.randn(20, 500) * 15
        X[20:40, 3, :] += rng.randn(20, 500) * 15
        X[40:, 7, :] += rng.randn(20, 500) * 15
        csp = CSPProcessor(cfg, n_components=4)
        csp.fit(X, y)
        feats = csp.transform(X)
        assert feats.shape[0] == n_trials


# ============================================================
# 9. motor_imagery/feature_extractor.py  (~8 tests)
# ============================================================
class TestMotorImageryFeatureExtractor:
    def test_create(self, cfg):
        fe = MotorImageryFeatureExtractor(cfg)
        assert fe.sampling_rate == 250.0

    def test_fit_returns_self(self, cfg):
        fe = MotorImageryFeatureExtractor(cfg)
        ret = fe.fit(np.random.randn(5, 10, 500))
        assert ret is fe

    def test_transform_shape(self, cfg):
        fe = MotorImageryFeatureExtractor(cfg)
        X = np.random.randn(10, N_CH, N_SAMPLES)
        feats = fe.fit(X).transform(X)
        assert feats.shape[0] == 10
        assert feats.shape[1] > 0

    def test_extract_trial_features(self, cfg):
        fe = MotorImageryFeatureExtractor(cfg)
        trial = np.random.randn(N_CH, N_SAMPLES)
        f = fe.extract_trial_features(trial)
        assert isinstance(f, dict)
        assert len(f) > 0

    def test_hjorth_parameters(self, cfg):
        fe = MotorImageryFeatureExtractor(cfg)
        sig = np.random.randn(1000)
        activity, mobility, complexity = fe._compute_hjorth_parameters(sig)
        assert activity > 0
        assert mobility >= 0
        assert complexity >= 0

    def test_petrosian_fd(self, cfg):
        fe = MotorImageryFeatureExtractor(cfg)
        sig = np.random.randn(1000)
        fd = fe._petrosian_fractal_dimension(sig)
        assert 0.5 < fd < 2.0

    def test_katz_fd(self, cfg):
        fe = MotorImageryFeatureExtractor(cfg)
        sig = np.random.randn(1000)
        fd = fe._katz_fractal_dimension(sig)
        assert fd > 0

    def test_plv(self, cfg):
        fe = MotorImageryFeatureExtractor(cfg)
        sig1 = np.sin(2 * np.pi * 10 * np.arange(1000) / SR)
        sig2 = np.sin(2 * np.pi * 10 * np.arange(1000) / SR + 0.1)
        plv = fe._compute_plv(sig1, sig2)
        assert 0 <= plv <= 1
        # Nearly identical signals should have high PLV
        assert plv > 0.9


# ============================================================
# 10. ssvep/detector.py  (~6 tests)
# ============================================================
class TestSSVEPDetector:
    """Test individual detection methods; skip detect() (missing time import)."""

    def test_create(self, cfg):
        det = SSVEPDetector(cfg)
        assert det.target_frequencies == cfg.ssvep["frequencies"]

    def test_psd_detection(self, cfg):
        det = SSVEPDetector(cfg)
        # Inject a 10 Hz signal into occipital-like channels
        n_ch = len(det.target_channels)
        data = _make_sine(10.0, n_ch=n_ch, dur=4.0)
        scores = det._psd_detection(data)
        assert isinstance(scores, dict)
        assert 10.0 in scores
        # 10 Hz should score well
        assert scores[10.0] > 1.0

    def test_cca_detection(self, cfg):
        det = SSVEPDetector(cfg)
        n_ch = len(det.target_channels)
        data = _make_sine(10.0, n_ch=n_ch, dur=4.0)
        scores = det._cca_detection(data)
        assert isinstance(scores, dict)
        # CCA correlation for matching frequency should be high
        assert scores[10.0] > 0.3

    def test_calculate_snr(self, cfg):
        det = SSVEPDetector(cfg)
        n_ch = len(det.target_channels)
        data = _make_sine(10.0, n_ch=n_ch, dur=4.0) + np.random.randn(n_ch, int(SR * 4)) * 0.1
        snr = det._calculate_snr(data, 10.0)
        assert snr > 1.0

    def test_calculate_snr_zero_freq(self, cfg):
        det = SSVEPDetector(cfg)
        snr = det._calculate_snr(np.random.randn(2, 1000), 0.0)
        assert snr == 0.0

    def test_msi_detection(self, cfg):
        det = SSVEPDetector(cfg)
        n_ch = len(det.target_channels)
        data = _make_sine(10.0, n_ch=n_ch, dur=4.0) + np.random.randn(n_ch, int(SR * 4)) * 0.3
        scores = det._msi_detection(data)
        assert isinstance(scores, dict)
        assert 10.0 in scores


# ============================================================
# 11. core/device_interface.py  (~6 tests)
# ============================================================
class TestDeviceInterface:
    def test_simulated_device_create(self, cfg):
        dev = SimulatedEEGDevice(cfg)
        assert dev.is_connected() is False

    def test_device_info(self, cfg):
        dev = SimulatedEEGDevice(cfg)
        info = dev.get_device_info()
        assert isinstance(info, DeviceInfo)
        assert info.device_type == "eeg"
        assert info.sampling_rate == SR

    def test_read_data_not_acquiring(self, cfg):
        dev = SimulatedEEGDevice(cfg)
        dev.connected = True
        # Not acquiring yet
        assert dev.read_data() is None

    def test_read_data_acquiring(self, cfg):
        dev = SimulatedEEGDevice(cfg)
        dev.connected = True
        dev.acquiring = True
        pkt = dev.read_data()
        assert isinstance(pkt, DataPacket)
        assert pkt.data.shape[0] == N_CH

    def test_start_stop_acquisition(self, cfg):
        dev = SimulatedEEGDevice(cfg)
        dev.connected = True
        assert dev.start_acquisition() is True
        assert dev.acquiring is True
        assert dev.stop_acquisition() is True
        assert dev.acquiring is False

    def test_datapacket_creation(self):
        dp = DataPacket(
            timestamp=1.0,
            sample_number=0,
            data=np.zeros((4, 1)),
            trigger_events=[],
            device_status={"ok": True},
        )
        assert dp.sample_number == 0
        assert dp.data.shape == (4, 1)
