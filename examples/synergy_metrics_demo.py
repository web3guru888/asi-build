#!/usr/bin/env python3
"""
Demonstrate cognitive synergy metrics:
- Generate two correlated time series
- Compute all 7 information-theoretic metrics
- Show transfer entropy (directional causality)

Requires: numpy, scipy, scikit-learn
"""

import numpy as np

from asi_build.cognitive_synergy.core.synergy_metrics import SynergyMetrics

print("=" * 60)
print("Cognitive Synergy Metrics Demo")
print("=" * 60)

# Create the metrics calculator.
# window_size = sampling_rate × 10 = 100 samples, so we need ≥ 100 points.
metrics = SynergyMetrics(
    history_length=2000,
    sampling_rate=10.0,      # 10 Hz
    significance_threshold=0.05,
)

# --- Generate two correlated signals ---
# Signal A: sine wave at 1 Hz
# Signal B: sine wave at 1 Hz with π/4 phase lag + noise
# This simulates two brain regions where A drives B with a slight delay.
n_points = 500
t = np.linspace(0, 50, n_points)

signal_a = np.sin(2 * np.pi * 0.5 * t) + 0.2 * np.random.randn(n_points)
signal_b = np.sin(2 * np.pi * 0.5 * t - np.pi / 4) + 0.3 * np.random.randn(n_points)

print(f"\nSignal A: 0.5 Hz sine + noise ({n_points} samples)")
print(f"Signal B: 0.5 Hz sine, π/4 phase lag + noise")

# Feed the time series point by point
pair_name = "regionA_regionB"
for i in range(n_points):
    metrics.add_time_series_data(pair_name, signal_a[i], signal_b[i], timestamp=t[i])

# --- Compute the full synergy profile ---
profile = metrics.compute_synergy_profile(pair_name)

if profile is None:
    print("⚠️  Not enough data for analysis (need ≥ window_size samples).")
else:
    print(f"\n{'Metric':<25s} {'Value':>8s}  Description")
    print("-" * 70)
    print(f"{'Mutual Information':<25s} {profile.mutual_information:8.4f}  "
          f"Statistical dependence (0–1)")
    print(f"{'Transfer Entropy':<25s} {profile.transfer_entropy:8.4f}  "
          f"Directed info flow A→B (0–1)")
    print(f"{'Phase Coupling (PLV)':<25s} {profile.phase_coupling:8.4f}  "
          f"Temporal synchronization (0–1)")
    print(f"{'Coherence':<25s} {profile.coherence:8.4f}  "
          f"Spectral functional connectivity (0–1)")
    print(f"{'Emergence Index':<25s} {profile.emergence_index:8.4f}  "
          f"Novel properties from interaction (0–1)")
    print(f"{'Integration Index':<25s} {profile.integration_index:8.4f}  "
          f"Geometric mean of MI×PLV×Coh (0–1)")
    print(f"{'Complexity Resonance':<25s} {profile.complexity_resonance:8.4f}  "
          f"Matched complexity levels (0–1)")

    # Overall synergy strength (weighted combination)
    strength = metrics.get_synergy_strength(pair_name)
    print(f"\n{'Overall Synergy Strength':<25s} {strength:8.4f}")

    # Check emergence indicators
    indicators = metrics.get_emergence_indicators(pair_name)
    if indicators:
        print(f"Emergence indicators: {', '.join(indicators)}")
    else:
        print("No emergence indicators triggered (thresholds are > 0.8).")

# --- Compare with an uncorrelated pair ---
print("\n--- Comparison: uncorrelated signals ---")
pair2 = "random_pair"
for i in range(n_points):
    metrics.add_time_series_data(pair2, np.random.randn(), np.random.randn(), timestamp=t[i])

profile2 = metrics.compute_synergy_profile(pair2)
if profile2:
    print(f"  Mutual Information : {profile2.mutual_information:.4f}  (expect ≈ 0)")
    print(f"  Transfer Entropy   : {profile2.transfer_entropy:.4f}  (expect ≈ 0)")
    print(f"  Phase Coupling     : {profile2.phase_coupling:.4f}  (expect low)")
    print(f"  Synergy Strength   : {metrics.get_synergy_strength(pair2):.4f}")

# --- Global synergy across all pairs ---
global_syn = metrics.compute_global_synergy()
print(f"\nGlobal synergy (across {len(metrics.synergy_profiles)} pairs):")
for k, v in global_syn.items():
    print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

print("\n✅ Synergy metrics demo complete.")
