"""
Enhanced Circuit Breaker Tests
===============================

25 tests covering:
- ProofFailureBreaker (5): trip on threshold, window expiration, reset, stats, below-threshold
- VolumeThresholdBreaker (5): warning, critical, pause, daily reset, remaining
- WithdrawalAnomalyDetector (4): normal passes, 10x flagged, min_samples honoured, stats
- AddressRateLimiter (4): rate limiting, window expiration, independent addresses, reset
- CooldownGuard (3): cooldown after unpause, expired cooldown, remaining_seconds
- EnhancedSafetyManager (4): orchestration, check_withdrawal aggregation, health_report, reset_all

All tests are self-contained and fast (< 1s each). No network or crypto deps.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from asi_build.rings.bridge.circuit_breaker import (
    AddressRateLimiter,
    CooldownGuard,
    EnhancedSafetyManager,
    ProofFailureBreaker,
    VolumeThresholdBreaker,
    WithdrawalAnomalyDetector,
)
from asi_build.rings.bridge.safety import AlertSeverity, SafetyAlert


# ===========================================================================
# ProofFailureBreaker Tests (5)
# ===========================================================================


class TestProofFailureBreaker:
    """Tests for the proof-failure sliding-window circuit breaker."""

    def test_trip_on_threshold_failures(self):
        """Should trip after exactly failure_threshold failures in window."""
        pfb = ProofFailureBreaker(failure_threshold=3, window_seconds=3600.0)
        now = time.time()

        assert pfb.is_tripped() is False
        pfb.record_proof_failure(now - 10)
        pfb.record_proof_failure(now - 5)
        assert pfb.is_tripped() is False  # only 2

        tripped = pfb.record_proof_failure(now)
        assert tripped is True
        assert pfb.is_tripped() is True

    def test_window_expiration_clears_failures(self):
        """Failures outside the window should be pruned and not trip."""
        pfb = ProofFailureBreaker(failure_threshold=3, window_seconds=10.0)
        now = time.time()

        # All three failures are older than the 10s window
        pfb.record_proof_failure(now - 100)
        pfb.record_proof_failure(now - 50)
        pfb.record_proof_failure(now - 20)
        # Pruned on next call — only the new one should count
        assert pfb.is_tripped() is False

        # Fresh failure after old ones pruned
        pfb.record_proof_failure(now)
        assert pfb.is_tripped() is False  # only 1 in window
        assert pfb.recent_failure_count == 1

    def test_reset_clears_state(self):
        """reset() should clear tripped state and failure history."""
        pfb = ProofFailureBreaker(failure_threshold=1)
        pfb.record_proof_failure()
        assert pfb.is_tripped() is True

        pfb.reset()
        assert pfb.is_tripped() is False
        assert pfb.recent_failure_count == 0

    def test_stats_snapshot(self):
        """stats property should return diagnostic info."""
        pfb = ProofFailureBreaker(failure_threshold=5, window_seconds=600.0)
        pfb.record_proof_failure()
        pfb.record_proof_failure()

        stats = pfb.stats
        assert stats["threshold"] == 5
        assert stats["window_seconds"] == 600.0
        assert stats["failures_in_window"] == 2
        assert stats["tripped"] is False

    def test_below_threshold_no_trip(self):
        """Fewer than threshold failures should not trip."""
        pfb = ProofFailureBreaker(failure_threshold=10, window_seconds=3600.0)
        for _ in range(9):
            pfb.record_proof_failure()
        assert pfb.is_tripped() is False


# ===========================================================================
# VolumeThresholdBreaker Tests (5)
# ===========================================================================


class TestVolumeThresholdBreaker:
    """Tests for the daily volume threshold breaker."""

    def test_warning_at_80_percent(self):
        """Should return 'warning' when volume hits 80% of daily limit."""
        vtb = VolumeThresholdBreaker(daily_limit=1000, warning_pct=0.80, critical_pct=0.95)
        # First: use 79% — no warning
        level = vtb.record_volume(790)
        assert level is None
        # Push to 80%
        level = vtb.record_volume(10)
        assert level == "warning"

    def test_critical_at_95_percent(self):
        """Should return 'critical' at 95% of daily limit."""
        vtb = VolumeThresholdBreaker(daily_limit=1000, warning_pct=0.80, critical_pct=0.95)
        level = vtb.record_volume(960)
        assert level == "critical"

    def test_pause_at_100_percent(self):
        """Should return 'pause' when daily limit is reached."""
        vtb = VolumeThresholdBreaker(daily_limit=1000, warning_pct=0.80, critical_pct=0.95)
        level = vtb.record_volume(1000)
        assert level == "pause"

    def test_daily_reset(self):
        """reset_daily() should zero the used counter."""
        vtb = VolumeThresholdBreaker(daily_limit=1000)
        vtb.record_volume(500)
        assert vtb.utilisation == pytest.approx(0.5)

        vtb.reset_daily()
        assert vtb.utilisation == 0.0
        assert vtb.remaining == 1000

    def test_remaining_calculation(self):
        """remaining should correctly compute unused capacity."""
        vtb = VolumeThresholdBreaker(daily_limit=1000)
        vtb.record_volume(300)
        assert vtb.remaining == 700

        vtb.record_volume(800)  # total 1100 — over limit
        assert vtb.remaining == 0  # clamped to 0


# ===========================================================================
# WithdrawalAnomalyDetector Tests (4)
# ===========================================================================


class TestWithdrawalAnomalyDetector:
    """Tests for the simple multiplier-based anomaly detector."""

    def test_normal_amounts_pass(self):
        """Normal amounts (within multiplier × avg) should not trigger alerts."""
        wad = WithdrawalAnomalyDetector(multiplier=10.0, min_samples=5)
        # Build baseline: 5 × 100
        for _ in range(5):
            alert = wad.check(100)
            assert alert is None  # still building baseline

        # 500 is only 5× avg (100), below 10× threshold
        alert = wad.check(500)
        assert alert is None

    def test_10x_flagged(self):
        """An amount > 10× the running average should trigger an alert."""
        wad = WithdrawalAnomalyDetector(multiplier=10.0, min_samples=5)
        # Build baseline: 5 × 100 → avg = 100
        for _ in range(5):
            wad.check(100)

        # 1500 is 15× avg → should flag
        alert = wad.check(1500)
        assert alert is not None
        assert alert.source == "withdrawal_anomaly"
        assert alert.severity in (AlertSeverity.WARNING, AlertSeverity.CRITICAL)
        assert "anomaly" in alert.message.lower()

    def test_min_samples_honoured(self):
        """Should NOT flag even huge amounts before min_samples observations."""
        wad = WithdrawalAnomalyDetector(multiplier=2.0, min_samples=10)
        # First 9 observations — detector doesn't have min_samples yet
        for i in range(9):
            alert = wad.check(100)
            assert alert is None

        # 10th call: check sees 9 samples (< 10), so no alert yet
        alert = wad.check(100)
        assert alert is None

        # 11th call: check sees 10 samples (>= 10), huge amount triggers
        alert = wad.check(100_000)
        assert alert is not None  # NOW min_samples is met and amount is anomalous

    def test_stats_snapshot(self):
        """stats property should include sample count and multiplier."""
        wad = WithdrawalAnomalyDetector(multiplier=5.0, min_samples=3)
        wad.check(100)
        wad.check(200)
        stats = wad.stats
        assert stats["samples"] == 2
        assert stats["min_samples"] == 3
        assert stats["multiplier"] == 5.0
        assert stats["total"] == 300


# ===========================================================================
# AddressRateLimiter Tests (4)
# ===========================================================================


class TestAddressRateLimiter:
    """Tests for per-address sliding-window rate limiting."""

    def test_rate_limiting_enforced(self):
        """Should block after max_per_hour operations."""
        arl = AddressRateLimiter(max_per_hour=3, window_seconds=3600.0)
        now = time.time()

        assert arl.check_and_record("0xAlice", now) is True  # 1
        assert arl.check_and_record("0xAlice", now + 1) is True  # 2
        assert arl.check_and_record("0xAlice", now + 2) is True  # 3
        assert arl.check_and_record("0xAlice", now + 3) is False  # blocked!

    def test_window_expiration(self):
        """Old operations should fall off the window, freeing capacity."""
        arl = AddressRateLimiter(max_per_hour=2, window_seconds=60.0)
        now = time.time()

        arl.check_and_record("0xBob", now - 100)  # old — will be pruned
        arl.check_and_record("0xBob", now - 70)   # old — will be pruned

        # Both are outside the 60s window, so Bob should have 2 remaining
        assert arl.get_remaining("0xBob", now) == 2
        assert arl.check_and_record("0xBob", now) is True

    def test_independent_addresses(self):
        """Rate limiting for different addresses should be independent."""
        arl = AddressRateLimiter(max_per_hour=1, window_seconds=3600.0)
        now = time.time()

        assert arl.check_and_record("0xAlice", now) is True
        assert arl.check_and_record("0xAlice", now + 1) is False  # Alice blocked
        assert arl.check_and_record("0xBob", now + 2) is True  # Bob is fine

    def test_reset_address(self):
        """reset(address) should clear only that address."""
        arl = AddressRateLimiter(max_per_hour=1, window_seconds=3600.0)
        now = time.time()

        arl.check_and_record("0xAlice", now)
        arl.check_and_record("0xBob", now)

        arl.reset("0xAlice")
        assert arl.get_remaining("0xAlice") == 1  # reset
        assert arl.get_remaining("0xBob", now) == 0  # untouched


# ===========================================================================
# CooldownGuard Tests (3)
# ===========================================================================


class TestCooldownGuard:
    """Tests for the post-unpause cooldown guard."""

    def test_cooldown_after_unpause(self):
        """Should be in cooldown immediately after unpause."""
        cg = CooldownGuard(cooldown_seconds=300.0)
        now = time.time()

        cg.record_unpause(now)
        assert cg.is_in_cooldown(now + 1) is True
        assert cg.remaining_seconds(now + 1) > 298.0

    def test_cooldown_expired(self):
        """Should NOT be in cooldown after the period expires."""
        cg = CooldownGuard(cooldown_seconds=10.0)
        now = time.time()

        cg.record_unpause(now - 20)  # 20s ago, 10s cooldown
        assert cg.is_in_cooldown(now) is False
        assert cg.remaining_seconds(now) == 0.0

    def test_no_cooldown_without_unpause(self):
        """Without any unpause event, should never be in cooldown."""
        cg = CooldownGuard(cooldown_seconds=300.0)
        assert cg.is_in_cooldown() is False
        assert cg.remaining_seconds() == 0.0


# ===========================================================================
# EnhancedSafetyManager Tests (4)
# ===========================================================================


class TestEnhancedSafetyManager:
    """Tests for the orchestrating EnhancedSafetyManager."""

    def test_check_withdrawal_allowed(self):
        """A normal withdrawal should pass all checks."""
        mgr = EnhancedSafetyManager(daily_limit=10**18, anomaly_min_samples=100)
        allowed, reason = mgr.check_withdrawal(1000, "0x" + "ab" * 20)
        assert allowed is True
        assert reason is None

    def test_check_withdrawal_blocked_by_proof_breaker(self):
        """If proof breaker is tripped, withdrawals should be blocked."""
        mgr = EnhancedSafetyManager(proof_failure_threshold=1)
        mgr.proof_breaker.record_proof_failure()
        assert mgr.proof_breaker.is_tripped() is True

        allowed, reason = mgr.check_withdrawal(1000, "0x" + "ab" * 20)
        assert allowed is False
        assert "proof failure" in reason.lower()

    def test_check_withdrawal_blocked_by_cooldown(self):
        """Withdrawals should be blocked during post-unpause cooldown."""
        mgr = EnhancedSafetyManager(cooldown_seconds=300.0)
        mgr.cooldown.record_unpause(time.time())

        allowed, reason = mgr.check_withdrawal(1000, "0x" + "ab" * 20)
        assert allowed is False
        assert "cooldown" in reason.lower()

    def test_check_withdrawal_blocked_by_volume(self):
        """Withdrawals should be blocked when daily volume is exceeded."""
        mgr = EnhancedSafetyManager(daily_limit=1000, anomaly_min_samples=100)
        # Exhaust the daily limit
        mgr.volume_breaker.record_volume(900)

        allowed, reason = mgr.check_withdrawal(200, "0x" + "ab" * 20)
        # 900 + 200 = 1100 > 1000 → should be paused
        # But note: check_withdrawal calls volume_breaker.record_volume(200)
        # which makes total = 900 + 200 = 1100 → utilisation 1.1 >= 1.0 → "pause"
        assert allowed is False
        assert "volume" in reason.lower() or "paused" in reason.lower()

    def test_health_report_structure(self):
        """health_report should contain all sub-system stats."""
        mgr = EnhancedSafetyManager()
        report = mgr.health_report

        assert "proof_failure_breaker" in report
        assert "volume_threshold_breaker" in report
        assert "withdrawal_anomaly_detector" in report
        assert "address_rate_limiter" in report
        assert "cooldown_guard" in report
        assert "total_alerts" in report

    def test_health_report_with_base_manager(self):
        """health_report should include base manager report when provided."""
        mock_base = MagicMock()
        mock_base.health_report = {"base_status": "ok"}
        mgr = EnhancedSafetyManager(base_manager=mock_base)

        report = mgr.health_report
        assert "base" in report
        assert report["base"]["base_status"] == "ok"

    def test_reset_all_clears_everything(self):
        """reset_all should clear all sub-systems."""
        mgr = EnhancedSafetyManager(proof_failure_threshold=1, daily_limit=100)

        # Trip various breakers
        mgr.proof_breaker.record_proof_failure()
        mgr.volume_breaker.record_volume(50)
        mgr.cooldown.record_unpause()

        assert mgr.proof_breaker.is_tripped() is True
        assert mgr.volume_breaker.utilisation > 0
        assert mgr.cooldown.is_in_cooldown() is True

        mgr.reset_all()

        assert mgr.proof_breaker.is_tripped() is False
        assert mgr.volume_breaker.utilisation == 0.0
        assert mgr.cooldown.is_in_cooldown() is False

    def test_check_withdrawal_address_rate_limited(self):
        """Per-address rate limit should block after max_per_hour."""
        mgr = EnhancedSafetyManager(
            address_max_per_hour=2,
            daily_limit=10**18,
            anomaly_min_samples=100,
        )
        addr = "0x" + "ab" * 20
        allowed1, _ = mgr.check_withdrawal(10, addr)
        allowed2, _ = mgr.check_withdrawal(10, addr)
        assert allowed1 is True
        assert allowed2 is True

        allowed3, reason = mgr.check_withdrawal(10, addr)
        assert allowed3 is False
        assert "rate-limited" in reason.lower() or "rate" in reason.lower()
