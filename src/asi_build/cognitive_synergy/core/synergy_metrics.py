"""
Synergy Metrics - Mathematical Formalization
============================================

Mathematical formalization of synergy metrics for cognitive processes based on
information theory, dynamical systems theory, and complexity science.
"""

import time
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
from scipy.signal import find_peaks
from scipy.stats import entropy
from sklearn.feature_selection import mutual_info_regression
from sklearn.metrics import normalized_mutual_info_score

warnings.filterwarnings("ignore")


@dataclass
class SynergyMeasurement:
    """Individual synergy measurement"""

    measurement_type: str
    value: float
    confidence: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SynergyProfile:
    """Complete synergy profile for a process pair"""

    pair_name: str
    mutual_information: float = 0.0
    transfer_entropy: float = 0.0
    phase_coupling: float = 0.0
    coherence: float = 0.0
    emergence_index: float = 0.0
    integration_index: float = 0.0
    complexity_resonance: float = 0.0
    last_updated: float = field(default_factory=time.time)
    measurements: List[SynergyMeasurement] = field(default_factory=list)


class SynergyMetrics:
    """
    Mathematical formalization of cognitive synergy metrics.

    Implements multiple synergy measures:
    1. Mutual Information - Statistical dependence
    2. Transfer Entropy - Directed information flow
    3. Phase Coupling - Temporal synchronization
    4. Coherence - Functional connectivity
    5. Emergence Index - Novel property detection
    6. Integration Index - Binding measure
    7. Complexity Resonance - Matched complexity levels
    """

    def __init__(
        self,
        history_length: int = 1000,
        sampling_rate: float = 10.0,
        significance_threshold: float = 0.05,
    ):
        """
        Initialize synergy metrics calculator.

        Args:
            history_length: Length of time series history to maintain
            sampling_rate: Sampling rate for time series analysis (Hz)
            significance_threshold: Statistical significance threshold
        """
        self.history_length = history_length
        self.sampling_rate = sampling_rate
        self.significance_threshold = significance_threshold

        # Time series storage for each process pair
        self.time_series_data: Dict[str, Dict[str, List[float]]] = {}
        self.synergy_profiles: Dict[str, SynergyProfile] = {}

        # Sliding window parameters
        self.window_size = int(sampling_rate * 10)  # 10 second windows
        self.overlap = int(self.window_size * 0.5)  # 50% overlap

    def add_time_series_data(
        self, pair_name: str, process_a_data: float, process_b_data: float, timestamp: float = None
    ):
        """Add time series data point for a process pair"""
        if timestamp is None:
            timestamp = time.time()

        if pair_name not in self.time_series_data:
            self.time_series_data[pair_name] = {"process_a": [], "process_b": [], "timestamps": []}

        # Add data points
        data = self.time_series_data[pair_name]
        data["process_a"].append(process_a_data)
        data["process_b"].append(process_b_data)
        data["timestamps"].append(timestamp)

        # Maintain history length
        if len(data["process_a"]) > self.history_length:
            data["process_a"].pop(0)
            data["process_b"].pop(0)
            data["timestamps"].pop(0)

    def compute_synergy_profile(self, pair_name: str) -> Optional[SynergyProfile]:
        """Compute comprehensive synergy profile for a process pair"""
        if pair_name not in self.time_series_data:
            return None

        data = self.time_series_data[pair_name]

        # Need sufficient data
        if len(data["process_a"]) < self.window_size:
            return None

        # Get time series
        x = np.array(data["process_a"])
        y = np.array(data["process_b"])

        # Compute synergy metrics
        profile = SynergyProfile(pair_name=pair_name)

        try:
            # 1. Mutual Information
            profile.mutual_information = self._compute_mutual_information(x, y)

            # 2. Transfer Entropy
            profile.transfer_entropy = self._compute_transfer_entropy(x, y)

            # 3. Phase Coupling
            profile.phase_coupling = self._compute_phase_coupling(x, y)

            # 4. Coherence
            profile.coherence = self._compute_coherence(x, y)

            # 5. Emergence Index
            profile.emergence_index = self._compute_emergence_index(x, y)

            # 6. Integration Index
            profile.integration_index = self._compute_integration_index(x, y)

            # 7. Complexity Resonance
            profile.complexity_resonance = self._compute_complexity_resonance(x, y)

            profile.last_updated = time.time()

            # Store profile
            self.synergy_profiles[pair_name] = profile

            return profile

        except Exception as e:
            # Return default profile on error
            return profile

    def _compute_mutual_information(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute mutual information I(X;Y) = H(X) + H(Y) - H(X,Y)

        Measures statistical dependence between two processes.
        """
        try:
            # Discretize continuous data
            x_discrete = self._discretize_signal(x)
            y_discrete = self._discretize_signal(y)

            # Compute normalized mutual information
            mi = normalized_mutual_info_score(x_discrete, y_discrete)
            return max(0.0, min(1.0, mi))

        except Exception:
            return 0.0

    def _compute_transfer_entropy(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute transfer entropy TE(X→Y) measuring directed information flow.

        TE(X→Y) = H(Y_{t+1} | Y_t) - H(Y_{t+1} | Y_t, X_t)
        """
        try:
            if len(x) < 10 or len(y) < 10:
                return 0.0

            # Create time-delayed versions
            x_t = x[:-1]  # X at time t
            y_t = y[:-1]  # Y at time t
            y_t1 = y[1:]  # Y at time t+1

            # Discretize
            x_t_disc = self._discretize_signal(x_t)
            y_t_disc = self._discretize_signal(y_t)
            y_t1_disc = self._discretize_signal(y_t1)

            # Compute conditional entropies using approximation
            # H(Y_{t+1} | Y_t)
            h_y_t1_given_y_t = self._conditional_entropy(y_t1_disc, y_t_disc)

            # H(Y_{t+1} | Y_t, X_t) - approximate using joint distribution
            joint_yx = np.column_stack([y_t_disc, x_t_disc])
            h_y_t1_given_yx_t = self._conditional_entropy(y_t1_disc, joint_yx)

            te = h_y_t1_given_y_t - h_y_t1_given_yx_t
            return max(0.0, min(1.0, te))

        except Exception:
            return 0.0

    def _compute_phase_coupling(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute phase coupling between two signals using Hilbert transform.

        Measures temporal synchronization between processes.
        """
        try:
            from scipy.signal import hilbert

            # Compute analytic signals
            x_analytic = hilbert(x - np.mean(x))
            y_analytic = hilbert(y - np.mean(y))

            # Extract phases
            x_phase = np.angle(x_analytic)
            y_phase = np.angle(y_analytic)

            # Phase difference
            phase_diff = x_phase - y_phase

            # Phase locking value (PLV)
            plv = np.abs(np.mean(np.exp(1j * phase_diff)))

            return max(0.0, min(1.0, plv))

        except Exception:
            return 0.0

    def _compute_coherence(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute spectral coherence between two signals.

        Measures functional connectivity in frequency domain.
        """
        try:
            from scipy.signal import coherence

            # Compute coherence
            freqs, coh = coherence(x, y, fs=self.sampling_rate, nperseg=min(64, len(x) // 4))

            # Mean coherence across frequencies
            mean_coherence = np.mean(coh)

            return max(0.0, min(1.0, mean_coherence))

        except Exception:
            return 0.0

    def _compute_emergence_index(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute emergence index measuring novel properties from interaction.

        EI = I(X;Y) - max(H(X), H(Y)) + C(X,Y)
        where C(X,Y) is the complexity of the joint system.
        """
        try:
            # Mutual information
            mi = self._compute_mutual_information(x, y)

            # Individual entropies
            h_x = self._entropy(self._discretize_signal(x))
            h_y = self._entropy(self._discretize_signal(y))

            # Joint complexity (approximated by joint entropy)
            xy_joint = np.column_stack([self._discretize_signal(x), self._discretize_signal(y)])
            joint_complexity = self._complexity_measure(xy_joint)

            # Emergence index
            ei = mi - max(h_x, h_y) + joint_complexity

            # Normalize to [0, 1]
            return max(0.0, min(1.0, (ei + 2.0) / 4.0))  # Rough normalization

        except Exception:
            return 0.0

    def _compute_integration_index(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute integration index measuring binding between processes.

        II = MI(X;Y) * PC(X,Y) * Coherence(X,Y)
        """
        try:
            mi = self._compute_mutual_information(x, y)
            pc = self._compute_phase_coupling(x, y)
            coh = self._compute_coherence(x, y)

            # Geometric mean for balanced integration
            ii = (mi * pc * coh) ** (1 / 3)

            return max(0.0, min(1.0, ii))

        except Exception:
            return 0.0

    def _compute_complexity_resonance(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute complexity resonance measuring matched complexity levels.

        CR = 1 - |C(X) - C(Y)| / (C(X) + C(Y))
        """
        try:
            # Lempel-Ziv complexity approximation
            c_x = self._lempel_ziv_complexity(self._discretize_signal(x))
            c_y = self._lempel_ziv_complexity(self._discretize_signal(y))

            if c_x + c_y == 0:
                return 1.0  # Both have zero complexity

            cr = 1.0 - abs(c_x - c_y) / (c_x + c_y)

            return max(0.0, min(1.0, cr))

        except Exception:
            return 0.0

    def _discretize_signal(self, signal: np.ndarray, n_bins: int = 10) -> np.ndarray:
        """Discretize continuous signal into bins"""
        if len(signal) == 0:
            return np.array([])

        # Handle constant signals
        if np.std(signal) < 1e-10:
            return np.zeros(len(signal), dtype=int)

        # Quantile-based discretization
        try:
            bins = np.quantile(signal, np.linspace(0, 1, n_bins + 1))
            bins = np.unique(bins)  # Remove duplicates
            if len(bins) <= 1:
                return np.zeros(len(signal), dtype=int)

            discretized = np.digitize(signal, bins[1:-1])
            return discretized
        except Exception:
            return np.zeros(len(signal), dtype=int)

    def _entropy(self, discrete_signal: np.ndarray) -> float:
        """Compute Shannon entropy of discrete signal"""
        if len(discrete_signal) == 0:
            return 0.0

        try:
            # Count occurrences
            unique, counts = np.unique(discrete_signal, return_counts=True)

            if len(counts) <= 1:
                return 0.0

            # Probability distribution
            probabilities = counts / len(discrete_signal)

            # Shannon entropy
            h = entropy(probabilities, base=2)

            return h if not np.isnan(h) else 0.0

        except Exception:
            return 0.0

    def _conditional_entropy(self, y: np.ndarray, x: np.ndarray) -> float:
        """Compute conditional entropy H(Y|X)"""
        try:
            if isinstance(x, np.ndarray) and len(x.shape) > 1:
                # For joint X, create combined labels
                x_combined = []
                for i in range(len(x)):
                    label = tuple(x[i]) if hasattr(x[i], "__iter__") else x[i]
                    x_combined.append(str(label))
                x = np.array(x_combined)

            # H(Y|X) = H(Y,X) - H(X)
            joint_entropy = self._joint_entropy(y, x)
            x_entropy = self._entropy(
                x if len(x.shape) == 1 else self._discretize_signal(np.arange(len(x)))
            )

            conditional_h = joint_entropy - x_entropy
            return max(0.0, conditional_h)

        except Exception:
            return 0.0

    def _joint_entropy(self, x: np.ndarray, y: np.ndarray) -> float:
        """Compute joint entropy H(X,Y)"""
        try:
            # Create joint distribution
            if len(x) != len(y):
                min_len = min(len(x), len(y))
                x, y = x[:min_len], y[:min_len]

            # Combine into joint outcomes
            joint_outcomes = []
            for i in range(len(x)):
                joint_outcomes.append(f"{x[i]}_{y[i]}")

            joint_array = np.array(joint_outcomes)

            return self._entropy(joint_array)

        except Exception:
            return 0.0

    def _complexity_measure(self, data: np.ndarray) -> float:
        """Compute complexity measure of data"""
        try:
            if len(data.shape) > 1:
                # For multi-dimensional data, flatten
                data_flat = []
                for row in data:
                    data_flat.append(str(tuple(row)))
                data = np.array(data_flat)

            # Use entropy as complexity measure
            return self._entropy(data)

        except Exception:
            return 0.0

    def _lempel_ziv_complexity(self, sequence: np.ndarray) -> float:
        """Compute Lempel-Ziv complexity (LZ76).

        Scans the sequence left-to-right, counting the number of new patterns.
        Normalized by n/log2(n) to give a value in [0, 1] range.
        """
        try:
            if len(sequence) < 2:
                return 0.0

            s = "".join(map(str, sequence.astype(int)))
            n = len(s)

            # LZ76 algorithm: count distinct new patterns
            complexity = 1  # first symbol is always new
            i = 0  # start of current pattern
            k = 1  # length of current extension

            while i + k <= n:
                # Check if s[i:i+k] has been seen in s[0:i+k-1]
                substring = s[i:i + k]
                prefix = s[:i + k - 1]  # everything before current position

                if substring in prefix:
                    k += 1  # extend current pattern
                else:
                    complexity += 1  # new pattern found
                    i += k  # advance past current pattern
                    k = 1  # reset extension length

            # Normalize: theoretical max for binary string is n/log2(n)
            import math
            if n > 1:
                normalizer = n / math.log2(n)
                return min(1.0, complexity / normalizer)
            return 0.0

        except Exception:
            return 0.0

    def get_synergy_strength(self, pair_name: str) -> float:
        """Get overall synergy strength for a process pair"""
        profile = self.synergy_profiles.get(pair_name)
        if not profile:
            return 0.0

        # Weighted combination of synergy measures
        weights = {
            "mutual_information": 0.25,
            "transfer_entropy": 0.20,
            "phase_coupling": 0.15,
            "coherence": 0.15,
            "emergence_index": 0.15,
            "integration_index": 0.10,
        }

        synergy_strength = (
            weights["mutual_information"] * profile.mutual_information
            + weights["transfer_entropy"] * profile.transfer_entropy
            + weights["phase_coupling"] * profile.phase_coupling
            + weights["coherence"] * profile.coherence
            + weights["emergence_index"] * profile.emergence_index
            + weights["integration_index"] * profile.integration_index
        )

        return max(0.0, min(1.0, synergy_strength))

    def get_emergence_indicators(self, pair_name: str) -> List[str]:
        """Get emergence indicators for a process pair"""
        profile = self.synergy_profiles.get(pair_name)
        if not profile:
            return []

        indicators = []

        # Check thresholds for emergence
        if profile.emergence_index > 0.8:
            indicators.append("high_emergence_index")

        if profile.mutual_information > 0.8:
            indicators.append("strong_statistical_coupling")

        if profile.phase_coupling > 0.8:
            indicators.append("phase_synchronization")

        if profile.complexity_resonance > 0.8:
            indicators.append("complexity_matching")

        if profile.integration_index > 0.8:
            indicators.append("strong_integration")

        # Complex emergence patterns
        if (
            profile.mutual_information > 0.7
            and profile.emergence_index > 0.7
            and profile.integration_index > 0.7
        ):
            indicators.append("synergistic_emergence")

        return indicators

    def get_all_profiles(self) -> Dict[str, SynergyProfile]:
        """Get all synergy profiles"""
        return self.synergy_profiles.copy()

    def compute_global_synergy(self) -> Dict[str, float]:
        """Compute global synergy metrics across all pairs"""
        if not self.synergy_profiles:
            return {"global_synergy": 0.0, "total_emergence": 0.0, "integration_coherence": 0.0}

        profiles = list(self.synergy_profiles.values())

        # Global synergy as average of individual synergies
        synergy_strengths = [self.get_synergy_strength(p.pair_name) for p in profiles]
        global_synergy = np.mean(synergy_strengths) if synergy_strengths else 0.0

        # Total emergence across all pairs
        emergence_indices = [p.emergence_index for p in profiles]
        total_emergence = np.mean(emergence_indices) if emergence_indices else 0.0

        # Integration coherence
        integration_indices = [p.integration_index for p in profiles]
        integration_coherence = np.mean(integration_indices) if integration_indices else 0.0

        return {
            "global_synergy": global_synergy,
            "total_emergence": total_emergence,
            "integration_coherence": integration_coherence,
            "num_synergistic_pairs": len([s for s in synergy_strengths if s > 0.6]),
        }
