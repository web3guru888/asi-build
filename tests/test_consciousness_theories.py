"""
Tests for cherry-picked consciousness theory files from archive/consciousness_complete/.

Covers:
- tensor_iit.py (IIT 3.0 Φ computation) — 4 tests
- biological_markers.py (biological consciousness benchmarks) — 3 tests
- consciousness_evolution.py (longitudinal tracking) — 2 tests
- higher_order_thought.py (HOT theory with graph analysis) — 3 tests
- predictive_processing_tensor.py (free energy minimization) — 2 tests
- Module import smoke tests — 3 tests

All tests handle torch gracefully — skip if torch is unavailable.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import numpy as np
import pytest

# ---------- optional torch ---------
try:
    import torch

    HAS_TORCH = True
except (ImportError, OSError):
    HAS_TORCH = False
    torch = None  # type: ignore[assignment]

requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")


# ===================================================================
# Helpers
# ===================================================================


def _make_activations(batch=2, time=6, neurons=16):
    """Create a small random activation tensor."""
    if not HAS_TORCH:
        raise RuntimeError("torch not available")
    return torch.randn(batch, time, neurons)


def _make_connectivity(n=16):
    """Create a small random connectivity matrix."""
    if not HAS_TORCH:
        raise RuntimeError("torch not available")
    c = torch.randn(n, n)
    return (c + c.T) / 2  # symmetric


@dataclass
class _FakeProfile:
    """Minimal stand-in for a consciousness assessment profile."""

    timestamp: datetime = datetime(2026, 4, 11, 0, 0)
    phi_score: float = 0.6
    gwt_coherence: float = 0.7
    attention_schema_score: float = 0.5
    metacognitive_accuracy: float = 0.4
    predictive_accuracy: float = 0.75
    agency_strength: float = 0.5
    predictive_error: float = 0.25
    hot_complexity: float = 0.5
    qualia_dimensionality: int = 12
    self_model_sophistication: float = 0.4
    overall_consciousness_score: float = 0.55
    training_step: Optional[int] = None


# ===================================================================
# 1. tensor_iit.py  (4 tests)
# ===================================================================


@requires_torch
class TestTensorIIT:
    """Tests for the IIT 3.0 implementation (tensor_iit.py)."""

    def setup_method(self):
        from asi_build.consciousness.theories.tensor_iit import IITCalculator

        self.calc = IITCalculator(device="cpu")

    def test_compute_phi_small_system(self):
        """Compute Φ on a small 4-neuron system — must return non-negative float."""
        activations = _make_activations(batch=1, time=6, neurons=4)
        phi = self.calc.compute_phi(activations)
        assert isinstance(phi, float)
        assert phi >= 0.0

    def test_mip_search_finds_minimum_partition(self):
        """MIP info should be ≤ whole-system info for any partition."""
        activations = _make_activations(batch=1, time=6, neurons=3)
        conn = _make_connectivity(3)
        whole = self.calc._compute_system_information(activations, conn)
        mip = self.calc._compute_mip_information(activations, conn)
        assert mip <= whole + 1e-6  # MIP ≤ whole (with tolerance)

    def test_mutual_information_known_distributions(self):
        """MI of identical signals should be positive; MI of independent ~0."""
        n = 200
        x = torch.randn(n)
        y = x.clone()  # identical → high MI
        mi_same = self.calc._compute_mutual_information(x, y)
        assert mi_same > 0.0

        y_indep = torch.randn(n)  # independent → MI ≈ 0
        mi_indep = self.calc._compute_mutual_information(x, y_indep)
        assert mi_indep < mi_same  # independent has less MI

    def test_phi_spectrum_frequency_bands(self):
        """Phi spectrum should return values for each requested band."""
        activations = _make_activations(batch=1, time=32, neurons=4)
        bands = [(0.0, 0.1), (0.1, 0.3), (0.3, 0.5)]
        spectrum = self.calc.compute_phi_spectrum(activations, bands)
        assert len(spectrum) == len(bands)
        for key in spectrum:
            assert isinstance(spectrum[key], float)
            assert spectrum[key] >= 0.0


# ===================================================================
# 2. biological_markers.py  (3 tests)
# ===================================================================


class TestBiologicalMarkers:
    """Tests for biological consciousness markers (no torch needed)."""

    def setup_method(self):
        from asi_build.consciousness.benchmarks.biological_markers import (
            BiologicalConsciousnessMarkers,
        )

        self.markers = BiologicalConsciousnessMarkers()

    def test_compare_metric_to_benchmark_range(self):
        """A value within human range should yield human_similarity=1.0."""
        benchmark = self.markers.benchmarks["phi_score"]
        comparison = self.markers._compare_metric_to_benchmark(0.7, benchmark)
        assert comparison["human_similarity"] == 1.0
        assert comparison["above_threshold"] is True

    def test_classify_consciousness_level(self):
        """Various likelihoods should map to expected tiers."""
        assert "Human" in self.markers._classify_consciousness_level(0.90)
        assert "primate" in self.markers._classify_consciousness_level(0.72).lower()
        assert "Moderate" in self.markers._classify_consciousness_level(0.55)
        assert "Basic" in self.markers._classify_consciousness_level(0.35)
        assert "Minimal" in self.markers._classify_consciousness_level(0.18)
        assert "Pre-conscious" in self.markers._classify_consciousness_level(0.05)

    def test_biological_similarity_score(self):
        """Full comparison should produce similarity scores for all categories."""
        profile = _FakeProfile()
        result = self.markers.compare_to_biological_markers(profile)

        # Must have biological similarity for at least human + some animals
        sim_scores = result["biological_similarity_scores"]
        assert "human" in sim_scores
        assert "primates" in sim_scores
        # Scores should be between 0 and 1
        for cat, score in sim_scores.items():
            assert 0.0 <= score <= 1.0, f"{cat} out of range: {score}"


# ===================================================================
# 3. consciousness_evolution.py  (2 tests)
# ===================================================================


class TestConsciousnessEvolution:
    """Tests for the evolution tracker (no torch needed)."""

    def setup_method(self):
        from asi_build.consciousness.trackers.consciousness_evolution import (
            ConsciousnessEvolutionTracker,
        )

        self.tracker = ConsciousnessEvolutionTracker()

    def _record_n(self, n=10):
        for i in range(n):
            p = _FakeProfile(
                timestamp=datetime(2026, 4, 11, 0, i),
                phi_score=0.3 + 0.02 * i,
                gwt_coherence=0.5 + 0.01 * i,
                attention_schema_score=0.4 + 0.01 * i,
                hot_complexity=0.3 + 0.015 * i,
                predictive_error=0.5 - 0.02 * i,
                qualia_dimensionality=10 + i,
                self_model_sophistication=0.3 + 0.02 * i,
                metacognitive_accuracy=0.3 + 0.01 * i,
                agency_strength=0.4 + 0.01 * i,
                overall_consciousness_score=0.4 + 0.02 * i,
            )
            self.tracker.record_assessment(p)

    def test_record_and_retrieve_assessments(self):
        """Recording N assessments stores N snapshots with correct values."""
        self._record_n(5)
        assert len(self.tracker.snapshots) == 5
        assert self.tracker.snapshots[0].phi_score == pytest.approx(0.3, abs=1e-6)
        assert self.tracker.snapshots[4].phi_score == pytest.approx(0.38, abs=1e-6)

    def test_trend_analysis_linear_regression(self):
        """With steadily increasing scores, trend should be positive."""
        self._record_n(10)
        analysis = self.tracker.analyze_consciousness_emergence()
        assert "insufficient_data" not in analysis
        traj = analysis["consciousness_trajectory"]
        assert traj["growth_rate"] > 0  # scores are increasing
        assert traj["final_score"] > traj["initial_score"]

        # IIT emergence should also show positive trend
        iit = analysis["IIT_emergence"]
        assert iit["trend"] > 0


# ===================================================================
# 4. higher_order_thought.py  (3 tests)
# ===================================================================


@requires_torch
class TestHigherOrderThought:
    """Tests for HOT theory implementation."""

    def setup_method(self):
        from asi_build.consciousness.theories.higher_order_thought import (
            HOTTheoryImplementation,
            MentalState,
        )

        self.MentalState = MentalState
        self.hot = HOTTheoryImplementation(device="cpu")

    def test_transitivity_chain_analysis(self):
        """Build a small chain manually and verify analysis runs without error."""
        s0 = self.MentalState(
            content=torch.randn(128),
            order=1,
            confidence=0.8,
            temporal_persistence=0.9,
            referential_target=None,
        )
        s1 = self.MentalState(
            content=torch.randn(128),
            order=2,
            confidence=0.7,
            temporal_persistence=0.8,
            referential_target=s0,
        )
        s2 = self.MentalState(
            content=torch.randn(128),
            order=3,
            confidence=0.6,
            temporal_persistence=0.7,
            referential_target=s1,
        )
        hots = [s1, s2]
        chains = self.hot._analyze_transitivity_chains(hots)
        assert isinstance(chains, list)

    def test_introspective_depth_computation(self):
        """Introspective depth should increase with deeper referential chains."""
        s1 = self.MentalState(
            content=torch.randn(128),
            order=2,
            confidence=0.8,
            temporal_persistence=0.8,
            referential_target=None,
        )
        depth_0 = self.hot._compute_introspective_depth([s1])
        assert depth_0 == 0  # No chain → depth 0

        # Chain: s3 → s2 → s1 (s2 and s1 are HOTs with order > 1)
        s2 = self.MentalState(
            content=torch.randn(128),
            order=3,
            confidence=0.7,
            temporal_persistence=0.7,
            referential_target=s1,
        )
        s3 = self.MentalState(
            content=torch.randn(128),
            order=4,
            confidence=0.6,
            temporal_persistence=0.6,
            referential_target=s2,
        )
        depth_deep = self.hot._compute_introspective_depth([s1, s2, s3])
        assert depth_deep >= 1

    def test_assess_higher_order_thoughts_returns_float(self):
        """Full assessment pipeline should run and return a float in [0, 1]."""
        activations = _make_activations(batch=1, time=4, neurons=512)
        score = self.hot.assess_higher_order_thoughts(activations)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# ===================================================================
# 5. predictive_processing_tensor.py  (2 tests)
# ===================================================================


@requires_torch
class TestPredictiveProcessingTensor:
    """Tests for the predictive processing / free energy implementation."""

    def setup_method(self):
        from asi_build.consciousness.theories.predictive_processing_tensor import (
            PredictiveProcessingMetrics,
        )

        self.pp = PredictiveProcessingMetrics(device="cpu")

    def test_free_energy_minimization_assessment(self):
        """Free energy assessment should return all expected keys."""
        activations = _make_activations(batch=1, time=10, neurons=512)
        result = self.pp.assess_free_energy_minimization(activations)
        expected_keys = {
            "mean_free_energy",
            "free_energy_trend",
            "free_energy_minimization",
            "free_energy_stability",
        }
        assert expected_keys.issubset(result.keys())
        assert result["free_energy_minimization"] >= 0.0

    def test_compute_prediction_metrics_returns_float(self):
        """Full prediction metrics pipeline should return a float."""
        activations = _make_activations(batch=1, time=10, neurons=512)
        error = self.pp.compute_prediction_metrics(activations)
        assert isinstance(error, float)


# ===================================================================
# 6. Smoke: __init__.py imports  (3 tests)
# ===================================================================


class TestModuleImports:
    """Verify that __init__.py files import correctly."""

    def test_benchmarks_init(self):
        from asi_build.consciousness.benchmarks import (
            BiologicalBenchmark,
            BiologicalConsciousnessMarkers,
        )

        markers = BiologicalConsciousnessMarkers()
        assert "phi_score" in markers.benchmarks

    def test_trackers_init(self):
        from asi_build.consciousness.trackers import (
            ConsciousnessEvolutionTracker,
            ConsciousnessSnapshot,
        )

        tracker = ConsciousnessEvolutionTracker()
        assert tracker.snapshots == []

    @requires_torch
    def test_theories_init(self):
        from asi_build.consciousness.theories import (
            HOTTheoryImplementation,
            PredictiveProcessingTensor,
            TensorIITCalculator,
        )

        calc = TensorIITCalculator(device="cpu")
        assert calc.phi_threshold == pytest.approx(1e-6)
