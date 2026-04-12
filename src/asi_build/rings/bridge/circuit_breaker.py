"""
Enhanced Circuit Breakers
==========================

Production-grade circuit breakers that extend the base safety system
(:mod:`.safety`) with fine-grained protection for bridge operations.

New protections
~~~~~~~~~~~~~~~

- **Proof failure tracking** — auto-trip after 3+ failed proof
  verifications within a sliding 1-hour window.
- **Volume threshold** — auto-pause when daily throughput hits 80 %
  (warning) / 95 % (critical) / 100 % (pause) of the configured limit.
- **Withdrawal anomaly** — flag any single withdrawal that exceeds 10×
  the running average.
- **Per-address rate limiting** — cap each address to *N* withdrawals
  per hour (default 5).
- **Cooldown guard** — enforce a no-withdrawal window (default 5 min)
  after the bridge is unpaused, preventing front-running of the
  unpause transaction.

All classes are fully self-contained, thread-safe (via
:class:`threading.Lock`), and have **zero external dependencies**
beyond the Python standard library.

Integration
~~~~~~~~~~~

:class:`EnhancedSafetyManager` orchestrates every breaker and can
optionally wrap an existing :class:`~.safety.BridgeSafetyManager`
to augment (not replace) the base safety layer.

.. code-block:: python

    from .safety import BridgeSafetyManager
    from .circuit_breaker import EnhancedSafetyManager

    base = BridgeSafetyManager(daily_limit=100 * 10**18)
    mgr  = EnhancedSafetyManager(base_manager=base)

    allowed, reason = mgr.check_withdrawal(amount=5_000, recipient="0xabc...")
    if not allowed:
        print(f"Blocked: {reason}")
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from .safety import AlertSeverity, SafetyAlert

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ProofFailureBreaker
# ---------------------------------------------------------------------------


class ProofFailureBreaker:
    """Trips if *failure_threshold* proof-verification failures occur
    within a sliding *window_seconds* window.

    Once tripped, all operations should be blocked until an operator
    calls :meth:`reset`.

    Parameters
    ----------
    failure_threshold : int
        Number of failures that triggers the breaker (default 3).
    window_seconds : float
        Sliding-window duration in seconds (default 3 600 = 1 hour).
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        window_seconds: float = 3600.0,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")

        self._threshold = failure_threshold
        self._window = window_seconds
        self._failures: List[float] = []
        self._tripped = False
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────

    def record_proof_failure(
        self, timestamp: Optional[float] = None,
    ) -> bool:
        """Record a proof-verification failure.

        Parameters
        ----------
        timestamp : float, optional
            Unix timestamp of the failure (defaults to ``time.time()``).

        Returns
        -------
        bool
            ``True`` if this failure caused the breaker to trip (or it
            was already tripped).
        """
        ts = timestamp if timestamp is not None else time.time()

        with self._lock:
            self._failures.append(ts)
            self._prune(ts)

            if len(self._failures) >= self._threshold and not self._tripped:
                self._tripped = True
                logger.warning(
                    "ProofFailureBreaker TRIPPED: %d failures in %.0fs window",
                    len(self._failures),
                    self._window,
                )

            return self._tripped

    def is_tripped(self) -> bool:
        """Return ``True`` if the breaker is currently tripped."""
        with self._lock:
            return self._tripped

    def reset(self) -> None:
        """Manually reset the breaker and clear the failure history."""
        with self._lock:
            self._tripped = False
            self._failures.clear()
            logger.info("ProofFailureBreaker reset")

    @property
    def recent_failure_count(self) -> int:
        """Number of failures inside the current sliding window."""
        with self._lock:
            self._prune(time.time())
            return len(self._failures)

    @property
    def stats(self) -> dict:
        """Diagnostic snapshot."""
        with self._lock:
            self._prune(time.time())
            return {
                "tripped": self._tripped,
                "failures_in_window": len(self._failures),
                "threshold": self._threshold,
                "window_seconds": self._window,
            }

    # ── Internals ────────────────────────────────────────────────────────

    def _prune(self, now: float) -> None:
        """Remove failures older than the window (caller holds lock)."""
        cutoff = now - self._window
        self._failures = [t for t in self._failures if t >= cutoff]

    def __repr__(self) -> str:
        return (
            f"ProofFailureBreaker(tripped={self._tripped}, "
            f"failures={self.recent_failure_count}/{self._threshold})"
        )


# ---------------------------------------------------------------------------
# VolumeThresholdBreaker
# ---------------------------------------------------------------------------


class VolumeThresholdBreaker:
    """Auto-pause when daily volume exceeds configurable thresholds.

    Three alert levels:

    - **warning** — volume ≥ *warning_pct* of *daily_limit*.
    - **critical** — volume ≥ *critical_pct* of *daily_limit*.
    - **pause** — volume ≥ 100 % of *daily_limit* (should halt ops).

    Parameters
    ----------
    daily_limit : int
        Maximum allowed daily volume (e.g. in wei).
    warning_pct : float
        Fraction that triggers a ``"warning"`` (default 0.80).
    critical_pct : float
        Fraction that triggers a ``"critical"`` (default 0.95).
    """

    def __init__(
        self,
        daily_limit: int,
        warning_pct: float = 0.80,
        critical_pct: float = 0.95,
    ) -> None:
        if daily_limit <= 0:
            raise ValueError("daily_limit must be > 0")
        if not (0 < warning_pct < critical_pct <= 1.0):
            raise ValueError(
                "Must have 0 < warning_pct < critical_pct <= 1.0"
            )

        self._daily_limit = daily_limit
        self._warning_pct = warning_pct
        self._critical_pct = critical_pct
        self._used: int = 0
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────

    def record_volume(self, amount: int) -> Optional[str]:
        """Record *amount* of throughput and return the alert level.

        Parameters
        ----------
        amount : int
            Volume to add (must be non-negative).

        Returns
        -------
        str or None
            ``None`` if below warning, otherwise one of
            ``"warning"``, ``"critical"``, or ``"pause"``.
        """
        if amount < 0:
            raise ValueError("amount must be >= 0")

        with self._lock:
            self._used += amount
            utilisation = self._used / self._daily_limit

            if utilisation >= 1.0:
                level = "pause"
            elif utilisation >= self._critical_pct:
                level = "critical"
            elif utilisation >= self._warning_pct:
                level = "warning"
            else:
                level = None

            if level is not None:
                logger.log(
                    logging.CRITICAL if level == "pause" else logging.WARNING,
                    "VolumeThresholdBreaker: %s — %.1f%% of daily limit "
                    "(%d / %d)",
                    level,
                    utilisation * 100,
                    self._used,
                    self._daily_limit,
                )

            return level

    def reset_daily(self) -> None:
        """Reset the daily counter (call at the start of each day)."""
        with self._lock:
            self._used = 0
            logger.info("VolumeThresholdBreaker: daily counter reset")

    @property
    def utilisation(self) -> float:
        """Current utilisation as a fraction (0.0–…)."""
        with self._lock:
            return self._used / self._daily_limit

    @property
    def remaining(self) -> int:
        """Remaining volume before the daily limit is hit."""
        with self._lock:
            return max(0, self._daily_limit - self._used)

    @property
    def stats(self) -> dict:
        """Diagnostic snapshot."""
        with self._lock:
            return {
                "daily_limit": self._daily_limit,
                "used": self._used,
                "utilisation": round(self._used / self._daily_limit, 4),
                "warning_pct": self._warning_pct,
                "critical_pct": self._critical_pct,
            }

    def __repr__(self) -> str:
        return (
            f"VolumeThresholdBreaker("
            f"used={self._used}/{self._daily_limit}, "
            f"{self.utilisation:.1%})"
        )


# ---------------------------------------------------------------------------
# WithdrawalAnomalyDetector
# ---------------------------------------------------------------------------


class WithdrawalAnomalyDetector:
    """Flag withdrawals that exceed *multiplier* × the running average.

    This is a simpler, deterministic check complementing the
    EWMA-based :class:`~.safety.AnomalyDetector`.  It requires
    *min_samples* observations before it starts flagging.

    Parameters
    ----------
    multiplier : float
        Threshold multiplier (default 10.0 → flag anything > 10× avg).
    min_samples : int
        Minimum observations before detection activates (default 5).
    """

    def __init__(
        self,
        multiplier: float = 10.0,
        min_samples: int = 5,
    ) -> None:
        if multiplier <= 0:
            raise ValueError("multiplier must be > 0")
        if min_samples < 1:
            raise ValueError("min_samples must be >= 1")

        self._multiplier = multiplier
        self._min_samples = min_samples
        self._history: List[int] = []
        self._total: int = 0
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────

    def check(self, amount: int) -> Optional[SafetyAlert]:
        """Check whether *amount* is anomalous.

        The observation is always recorded regardless of whether an
        alert is generated.

        Parameters
        ----------
        amount : int
            Withdrawal amount.

        Returns
        -------
        SafetyAlert or None
            An alert if the amount exceeds the threshold.
        """
        with self._lock:
            alert: Optional[SafetyAlert] = None

            if len(self._history) >= self._min_samples:
                avg = self._total / len(self._history)
                threshold = avg * self._multiplier

                if amount > threshold and avg > 0:
                    ratio = amount / avg
                    severity = (
                        AlertSeverity.CRITICAL
                        if ratio >= self._multiplier * 2
                        else AlertSeverity.WARNING
                    )
                    alert = SafetyAlert(
                        timestamp=time.time(),
                        severity=severity,
                        source="withdrawal_anomaly",
                        message=(
                            f"Withdrawal anomaly: amount={amount} is "
                            f"{ratio:.1f}× the average ({avg:.0f}), "
                            f"threshold={self._multiplier}×"
                        ),
                        metrics={
                            "amount": amount,
                            "average": round(avg, 2),
                            "ratio": round(ratio, 2),
                            "multiplier": self._multiplier,
                        },
                    )
                    logger.warning(
                        "WithdrawalAnomalyDetector: %s", alert.message,
                    )

            # Always record the observation
            self._history.append(amount)
            self._total += amount

            return alert

    @property
    def average(self) -> float:
        """Running average of all recorded withdrawals."""
        with self._lock:
            if not self._history:
                return 0.0
            return self._total / len(self._history)

    @property
    def stats(self) -> dict:
        """Diagnostic snapshot."""
        with self._lock:
            return {
                "samples": len(self._history),
                "min_samples": self._min_samples,
                "total": self._total,
                "average": round(
                    self._total / len(self._history), 2,
                ) if self._history else 0.0,
                "multiplier": self._multiplier,
            }

    def __repr__(self) -> str:
        return (
            f"WithdrawalAnomalyDetector("
            f"samples={len(self._history)}, "
            f"avg={self.average:.0f}, "
            f"threshold={self._multiplier}×)"
        )


# ---------------------------------------------------------------------------
# AddressRateLimiter
# ---------------------------------------------------------------------------


class AddressRateLimiter:
    """Per-address rate limiting with a sliding time window.

    Each unique address is allowed at most *max_per_hour* operations
    within a *window_seconds* sliding window.

    Parameters
    ----------
    max_per_hour : int
        Maximum operations per address per window (default 5).
    window_seconds : float
        Sliding-window duration in seconds (default 3 600 = 1 hour).
    """

    def __init__(
        self,
        max_per_hour: int = 5,
        window_seconds: float = 3600.0,
    ) -> None:
        if max_per_hour < 1:
            raise ValueError("max_per_hour must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")

        self._max = max_per_hour
        self._window = window_seconds
        self._windows: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────

    def check_and_record(
        self,
        address: str,
        timestamp: Optional[float] = None,
    ) -> bool:
        """Check rate limit for *address* and record the attempt.

        Parameters
        ----------
        address : str
            The address (e.g. Ethereum address) to check.
        timestamp : float, optional
            Current time (defaults to ``time.time()``).

        Returns
        -------
        bool
            ``True`` if the operation is allowed, ``False`` if the
            address has exceeded its rate limit.
        """
        ts = timestamp if timestamp is not None else time.time()

        with self._lock:
            if address not in self._windows:
                self._windows[address] = []

            window = self._windows[address]
            self._prune_window(window, ts)

            if len(window) >= self._max:
                logger.warning(
                    "AddressRateLimiter: %s rate-limited "
                    "(%d/%d in %.0fs window)",
                    address, len(window), self._max, self._window,
                )
                return False

            window.append(ts)
            return True

    def get_remaining(
        self,
        address: str,
        timestamp: Optional[float] = None,
    ) -> int:
        """Return how many operations *address* has left in the window.

        Parameters
        ----------
        address : str
            The address to query.
        timestamp : float, optional
            Current time.

        Returns
        -------
        int
            Remaining allowed operations (≥ 0).
        """
        ts = timestamp if timestamp is not None else time.time()

        with self._lock:
            if address not in self._windows:
                return self._max

            window = self._windows[address]
            self._prune_window(window, ts)
            return max(0, self._max - len(window))

    def reset(self, address: Optional[str] = None) -> None:
        """Reset rate-limit state.

        Parameters
        ----------
        address : str, optional
            If given, reset only that address.  Otherwise reset all.
        """
        with self._lock:
            if address is not None:
                self._windows.pop(address, None)
            else:
                self._windows.clear()

    @property
    def tracked_addresses(self) -> int:
        """Number of addresses currently tracked."""
        with self._lock:
            return len(self._windows)

    @property
    def stats(self) -> dict:
        """Diagnostic snapshot."""
        with self._lock:
            return {
                "max_per_hour": self._max,
                "window_seconds": self._window,
                "tracked_addresses": len(self._windows),
            }

    # ── Internals ────────────────────────────────────────────────────────

    def _prune_window(self, window: List[float], now: float) -> None:
        """Remove timestamps older than the sliding window (in-place)."""
        cutoff = now - self._window
        # Remove from the front (oldest first) — O(n) but window is small
        while window and window[0] < cutoff:
            window.pop(0)

    def __repr__(self) -> str:
        return (
            f"AddressRateLimiter(max={self._max}, "
            f"window={self._window}s, "
            f"tracking={self.tracked_addresses} addrs)"
        )


# ---------------------------------------------------------------------------
# CooldownGuard
# ---------------------------------------------------------------------------


class CooldownGuard:
    """Enforces a no-withdrawal cooldown after the bridge is unpaused.

    Prevents front-running of the unpause transaction by blocking all
    withdrawals for *cooldown_seconds* after each unpause event.

    Parameters
    ----------
    cooldown_seconds : float
        Duration of the cooldown period (default 300.0 = 5 minutes).
    """

    def __init__(self, cooldown_seconds: float = 300.0) -> None:
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")

        self._cooldown = cooldown_seconds
        self._unpause_time: Optional[float] = None
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────

    def record_unpause(self, timestamp: Optional[float] = None) -> None:
        """Record that the bridge was just unpaused.

        Parameters
        ----------
        timestamp : float, optional
            Time of the unpause event (defaults to ``time.time()``).
        """
        ts = timestamp if timestamp is not None else time.time()
        with self._lock:
            self._unpause_time = ts
            logger.info(
                "CooldownGuard: unpause recorded, cooldown %.0fs",
                self._cooldown,
            )

    def is_in_cooldown(self, timestamp: Optional[float] = None) -> bool:
        """Return ``True`` if the bridge is still in its cooldown period.

        Parameters
        ----------
        timestamp : float, optional
            Current time (defaults to ``time.time()``).
        """
        ts = timestamp if timestamp is not None else time.time()
        with self._lock:
            if self._unpause_time is None:
                return False
            return (ts - self._unpause_time) < self._cooldown

    def remaining_seconds(self, timestamp: Optional[float] = None) -> float:
        """Seconds remaining in the cooldown (0.0 if not active).

        Parameters
        ----------
        timestamp : float, optional
            Current time (defaults to ``time.time()``).
        """
        ts = timestamp if timestamp is not None else time.time()
        with self._lock:
            if self._unpause_time is None:
                return 0.0
            remaining = self._cooldown - (ts - self._unpause_time)
            return max(0.0, remaining)

    def reset(self) -> None:
        """Clear the cooldown state entirely."""
        with self._lock:
            self._unpause_time = None

    @property
    def stats(self) -> dict:
        """Diagnostic snapshot."""
        with self._lock:
            now = time.time()
            active = (
                self._unpause_time is not None
                and (now - self._unpause_time) < self._cooldown
            )
            return {
                "cooldown_seconds": self._cooldown,
                "active": active,
                "remaining": round(
                    max(0.0, self._cooldown - (now - self._unpause_time))
                    if self._unpause_time is not None
                    else 0.0,
                    1,
                ),
                "unpause_time": self._unpause_time,
            }

    def __repr__(self) -> str:
        rem = self.remaining_seconds()
        return (
            f"CooldownGuard(cooldown={self._cooldown}s, "
            f"remaining={rem:.0f}s)"
        )


# ---------------------------------------------------------------------------
# EnhancedSafetyManager
# ---------------------------------------------------------------------------


class EnhancedSafetyManager:
    """Orchestrates all enhanced circuit breakers.

    Wraps an optional base :class:`~.safety.BridgeSafetyManager` and
    layers the new breakers on top.  Every withdrawal or proof event
    is checked against **all** sub-systems; the most restrictive
    result wins.

    Parameters
    ----------
    base_manager : object, optional
        An existing ``BridgeSafetyManager`` (or duck-typed equivalent).
        If provided, its :meth:`health_report` is merged into ours.
    daily_limit : int
        Daily volume limit for :class:`VolumeThresholdBreaker`
        (default 100 × 10¹⁸ = 100 ETH in wei).
    warning_pct : float
        Warning threshold for volume breaker (default 0.80).
    critical_pct : float
        Critical threshold for volume breaker (default 0.95).
    proof_failure_threshold : int
        Failures that trip :class:`ProofFailureBreaker` (default 3).
    proof_failure_window : float
        Sliding window for proof failures in seconds (default 3 600).
    anomaly_multiplier : float
        Threshold for :class:`WithdrawalAnomalyDetector` (default 10.0).
    anomaly_min_samples : int
        Minimum samples before anomaly detection fires (default 5).
    address_max_per_hour : int
        Per-address hourly cap (default 5).
    cooldown_seconds : float
        Cooldown after unpause (default 300.0).
    """

    def __init__(
        self,
        base_manager: Any = None,
        *,
        daily_limit: int = 100 * 10**18,
        warning_pct: float = 0.80,
        critical_pct: float = 0.95,
        proof_failure_threshold: int = 3,
        proof_failure_window: float = 3600.0,
        anomaly_multiplier: float = 10.0,
        anomaly_min_samples: int = 5,
        address_max_per_hour: int = 5,
        cooldown_seconds: float = 300.0,
    ) -> None:
        self.base_manager = base_manager

        self.proof_breaker = ProofFailureBreaker(
            failure_threshold=proof_failure_threshold,
            window_seconds=proof_failure_window,
        )
        self.volume_breaker = VolumeThresholdBreaker(
            daily_limit=daily_limit,
            warning_pct=warning_pct,
            critical_pct=critical_pct,
        )
        self.anomaly_detector = WithdrawalAnomalyDetector(
            multiplier=anomaly_multiplier,
            min_samples=anomaly_min_samples,
        )
        self.address_limiter = AddressRateLimiter(
            max_per_hour=address_max_per_hour,
        )
        self.cooldown = CooldownGuard(
            cooldown_seconds=cooldown_seconds,
        )

        self._alerts: List[SafetyAlert] = []
        self._lock = threading.Lock()

    # ── Pre-flight checks ────────────────────────────────────────────────

    def check_withdrawal(
        self,
        amount: int,
        recipient: str,
    ) -> Tuple[bool, Optional[str]]:
        """Run all enhanced checks for a withdrawal.

        This is the primary entry point.  All sub-systems are queried
        in order; the **first** failing check short-circuits.

        Parameters
        ----------
        amount : int
            Withdrawal amount.
        recipient : str
            Recipient address.

        Returns
        -------
        tuple of (bool, str or None)
            ``(True, None)`` if allowed, or ``(False, reason)`` if
            blocked.
        """
        # 1. Proof failure breaker
        if self.proof_breaker.is_tripped():
            reason = (
                "Proof failure circuit breaker is TRIPPED — "
                f"{self.proof_breaker.recent_failure_count} failures "
                f"in window"
            )
            self._record_block(amount, recipient, reason)
            return False, reason

        # 2. Cooldown guard
        if self.cooldown.is_in_cooldown():
            remaining = self.cooldown.remaining_seconds()
            reason = (
                f"Bridge is in post-unpause cooldown — "
                f"{remaining:.0f}s remaining"
            )
            self._record_block(amount, recipient, reason)
            return False, reason

        # 3. Per-address rate limit
        if not self.address_limiter.check_and_record(recipient):
            remaining = self.address_limiter.get_remaining(recipient)
            reason = (
                f"Address {recipient} rate-limited — "
                f"{remaining} withdrawals remaining this hour"
            )
            self._record_block(amount, recipient, reason)
            return False, reason

        # 4. Withdrawal anomaly
        alert = self.anomaly_detector.check(amount)
        if alert is not None:
            with self._lock:
                self._alerts.append(alert)
            if alert.severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY):
                reason = f"Anomalous withdrawal blocked: {alert.message}"
                return False, reason
            # WARNING-level anomalies are logged but allowed through
            logger.warning(
                "Withdrawal anomaly (allowed): %s", alert.message,
            )

        # 5. Volume threshold
        level = self.volume_breaker.record_volume(amount)
        if level == "pause":
            reason = (
                "Daily volume limit reached — bridge auto-paused "
                f"({self.volume_breaker.utilisation:.1%} utilisation)"
            )
            self._record_block(amount, recipient, reason)
            return False, reason
        if level == "critical":
            # Critical but not yet at 100% — allow with warning
            logger.warning(
                "Withdrawal allowed at critical volume level "
                "(%s utilisation)",
                f"{self.volume_breaker.utilisation:.1%}",
            )

        return True, None

    # ── Event recording ──────────────────────────────────────────────────

    def record_proof_failure(
        self, timestamp: Optional[float] = None,
    ) -> bool:
        """Record a proof-verification failure.

        Returns ``True`` if the proof failure breaker trips.
        """
        tripped = self.proof_breaker.record_proof_failure(timestamp)
        if tripped:
            alert = SafetyAlert(
                timestamp=timestamp if timestamp is not None else time.time(),
                severity=AlertSeverity.CRITICAL,
                source="proof_failure_breaker",
                message=(
                    f"Proof failure breaker TRIPPED: "
                    f"{self.proof_breaker.recent_failure_count} failures "
                    f"in sliding window"
                ),
                metrics=self.proof_breaker.stats,
            )
            with self._lock:
                self._alerts.append(alert)
        return tripped

    def record_withdrawal(self, amount: int, recipient: str) -> None:
        """Record a successfully completed withdrawal.

        This updates the anomaly detector history (the observation was
        already recorded during :meth:`check_withdrawal`, so this is a
        no-op for the anomaly detector, but can be extended in the
        future).
        """
        # Volume is already recorded during check_withdrawal.
        # This hook exists for future audit-trail or post-hoc
        # accounting extensions.
        logger.debug(
            "Withdrawal recorded: amount=%d, recipient=%s",
            amount, recipient,
        )

    def record_unpause(self, timestamp: Optional[float] = None) -> None:
        """Record a bridge unpause event, starting the cooldown."""
        self.cooldown.record_unpause(timestamp)
        alert = SafetyAlert(
            timestamp=timestamp if timestamp is not None else time.time(),
            severity=AlertSeverity.INFO,
            source="cooldown_guard",
            message=(
                f"Bridge unpaused — cooldown active for "
                f"{self.cooldown._cooldown:.0f}s"
            ),
            metrics=self.cooldown.stats,
        )
        with self._lock:
            self._alerts.append(alert)

    # ── Query ────────────────────────────────────────────────────────────

    def get_alerts(
        self,
        since: float = 0,
        severity: Optional[AlertSeverity] = None,
    ) -> List[SafetyAlert]:
        """Return alerts, optionally filtered by time and severity.

        Parameters
        ----------
        since : float
            Only return alerts after this Unix timestamp.
        severity : AlertSeverity, optional
            Only return alerts of this severity.

        Returns
        -------
        list of SafetyAlert
        """
        with self._lock:
            alerts: List[SafetyAlert] = list(self._alerts)

        if since > 0:
            alerts = [a for a in alerts if a.timestamp >= since]
        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    @property
    def health_report(self) -> dict:
        """Comprehensive health report from all enhanced breakers.

        If a *base_manager* was provided and has a ``health_report``
        property, its report is included under the ``"base"`` key.
        """
        report: dict = {
            "proof_failure_breaker": self.proof_breaker.stats,
            "volume_threshold_breaker": self.volume_breaker.stats,
            "withdrawal_anomaly_detector": self.anomaly_detector.stats,
            "address_rate_limiter": self.address_limiter.stats,
            "cooldown_guard": self.cooldown.stats,
            "total_alerts": len(self._alerts),
        }

        if self.base_manager is not None:
            base_report = getattr(self.base_manager, "health_report", None)
            if base_report is not None:
                if callable(base_report):
                    report["base"] = base_report()
                else:
                    report["base"] = base_report

        return report

    def reset_all(self) -> None:
        """Reset every sub-system (for testing or full recovery)."""
        self.proof_breaker.reset()
        self.volume_breaker.reset_daily()
        self.address_limiter.reset()
        self.cooldown.reset()
        # Anomaly detector: recreate to clear history
        self.anomaly_detector = WithdrawalAnomalyDetector(
            multiplier=self.anomaly_detector._multiplier,
            min_samples=self.anomaly_detector._min_samples,
        )
        with self._lock:
            self._alerts.clear()

        if self.base_manager is not None:
            reset_fn = getattr(self.base_manager, "reset_all", None)
            if reset_fn is not None and callable(reset_fn):
                reset_fn()

        logger.info("EnhancedSafetyManager: all sub-systems reset")

    # ── Internals ────────────────────────────────────────────────────────

    def _record_block(
        self, amount: int, recipient: str, reason: str,
    ) -> None:
        """Log a blocked withdrawal and create an alert."""
        logger.warning(
            "Withdrawal BLOCKED: amount=%d, recipient=%s, reason=%s",
            amount, recipient, reason,
        )
        alert = SafetyAlert(
            timestamp=time.time(),
            severity=AlertSeverity.WARNING,
            source="enhanced_safety_manager",
            message=reason,
            metrics={
                "amount": amount,
                "recipient": recipient,
            },
        )
        with self._lock:
            self._alerts.append(alert)

    def __repr__(self) -> str:
        return (
            f"EnhancedSafetyManager("
            f"alerts={len(self._alerts)}, "
            f"proof_tripped={self.proof_breaker.is_tripped()}, "
            f"volume={self.volume_breaker.utilisation:.1%}, "
            f"cooldown={self.cooldown.is_in_cooldown()})"
        )
