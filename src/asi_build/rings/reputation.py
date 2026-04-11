"""
Rings Network Reputation — Ranking Protocol Client
=====================================================

Implements the client-side logic of the Ranking Protocol described in
"The Ranking Protocol" paper.  The protocol provides Sybil-resistant,
game-theoretically-sound node reputation via:

1. **Local Ranking**: Each node scores its direct neighbours based on:
   - Request success rate
   - Received request validity rate
   - Total successful interactions

2. **Global Ranking**: Aggregated from local rankings via statistically
   rigorous random sampling (4-phase pipeline):
   - Phase 1: Random seed from decentralized oracle
   - Phase 2: Systematic sampling targets
   - Phase 3: DHT lookup + entropy test (Shannon/Rényi)
   - Phase 4: Kolmogorov-Smirnov test for distribution fairness

3. **Game-Theoretic Incentives**:
   - Median game → honest reporting is Nash Equilibrium
   - Byzantine distributed game → unique NE = all honest (with ≥2/3 honest assumption)

4. **Reward/Slash**: Cryptographic proofs for rank claims; freeze period + slashing.

This client wraps the above logic and provides a simple API for:
- Submitting local observations (scoring neighbours)
- Querying local and global ranks
- Checking trustworthiness thresholds
- Reporting malicious behaviour
"""

from __future__ import annotations

import logging
import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TRUST_THRESHOLD = 0.5
FREEZE_PERIOD_SECONDS = 3600.0  # 1 hour after claiming rank before it can change
LOCAL_SCORE_DECAY = 0.95  # Exponential decay per scoring epoch
MAX_LOCAL_HISTORY = 1000  # Max observations per peer


# ---------------------------------------------------------------------------
# Enums & Data types
# ---------------------------------------------------------------------------


class BehaviourType(Enum):
    """Categories of peer behaviour for local scoring."""

    REQUEST_SUCCESS = "request_success"  # Peer responded correctly
    REQUEST_FAILURE = "request_failure"  # Peer failed to respond
    VALID_REQUEST = "valid_request"  # Peer sent a valid request
    INVALID_REQUEST = "invalid_request"  # Peer sent an invalid request
    BYZANTINE = "byzantine"  # Peer exhibited byzantine behaviour
    CONTRIBUTION = "contribution"  # Peer contributed valuable data


class TrustTier(Enum):
    """Discretized trust levels derived from reputation scores."""

    UNTRUSTED = "untrusted"  # < 0.2
    LOW = "low"  # 0.2 – 0.4
    MEDIUM = "medium"  # 0.4 – 0.6
    HIGH = "high"  # 0.6 – 0.8
    VERIFIED = "verified"  # ≥ 0.8

    @classmethod
    def from_score(cls, score: float) -> "TrustTier":
        """Map a numeric score [0, 1] to a trust tier."""
        if score >= 0.8:
            return cls.VERIFIED
        if score >= 0.6:
            return cls.HIGH
        if score >= 0.4:
            return cls.MEDIUM
        if score >= 0.2:
            return cls.LOW
        return cls.UNTRUSTED


@dataclass
class LocalObservation:
    """A single local scoring observation about a peer."""

    peer_did: str
    behaviour: BehaviourType
    score: float  # 0.0 – 1.0
    timestamp: float = field(default_factory=time.time)
    proof: str = ""  # Optional cryptographic proof
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LocalRankRecord:
    """Aggregated local rank for a specific peer."""

    peer_did: str
    score: float = 0.0  # Weighted running average [0, 1]
    request_success_rate: float = 0.0
    request_validity_rate: float = 0.0
    total_interactions: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class GlobalRankRecord:
    """Global rank for a peer (aggregated from local rankings network-wide)."""

    peer_did: str
    global_score: float = 0.0  # [0, 1]
    sample_count: int = 0
    confidence: float = 0.0  # Statistical confidence in the score
    last_sampled: float = field(default_factory=time.time)
    ks_statistic: float = 0.0  # Kolmogorov-Smirnov test statistic
    frozen_until: float = 0.0  # Freeze period end time


@dataclass
class SlashReport:
    """Report of malicious behaviour (for slashing)."""

    target_did: str
    reporter_did: str
    reason: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    report_id: str = ""


# ---------------------------------------------------------------------------
# ReputationClient
# ---------------------------------------------------------------------------


class ReputationClient:
    """Client for the Rings Ranking Protocol.

    Maintains local scoring of peers and can query / compute global ranks.

    Parameters
    ----------
    client : object, optional
        A :class:`~asi_build.rings.client.RingsClient` instance for
        network queries. If ``None``, operates in local-only mode.
    local_did : str, optional
        The DID of the local node (scorer).
    default_threshold : float
        Default trust threshold for :meth:`is_trustworthy`.
    """

    def __init__(
        self,
        client: Any = None,
        *,
        local_did: str = "",
        default_threshold: float = DEFAULT_TRUST_THRESHOLD,
    ) -> None:
        self._client = client
        self._local_did = local_did
        self._default_threshold = default_threshold

        # Local scoring state
        self._observations: Dict[str, List[LocalObservation]] = defaultdict(list)
        self._local_ranks: Dict[str, LocalRankRecord] = {}

        # Cached global ranks
        self._global_cache: Dict[str, GlobalRankRecord] = {}

        # Slash reports submitted by this node
        self._slash_reports: List[SlashReport] = []

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def local_did(self) -> str:
        return self._local_did

    @local_did.setter
    def local_did(self, value: str) -> None:
        self._local_did = value

    @property
    def peer_count(self) -> int:
        """Number of peers with local observations."""
        return len(self._observations)

    @property
    def total_observations(self) -> int:
        """Total local observations recorded."""
        return sum(len(obs) for obs in self._observations.values())

    # ── Local Scoring ─────────────────────────────────────────────────────

    def report_behaviour(
        self,
        peer_did: str,
        behaviour: BehaviourType,
        score: float,
        *,
        proof: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LocalObservation:
        """Record a local observation about a peer's behaviour.

        This is the fundamental operation of the Ranking Protocol's
        local scoring system.

        Parameters
        ----------
        peer_did : str
            DID of the peer being scored.
        behaviour : BehaviourType
            Category of behaviour observed.
        score : float
            Quality score for this observation (0.0 = worst, 1.0 = best).
        proof : str
            Optional cryptographic proof of the observation.
        metadata : dict, optional
            Additional context.

        Returns
        -------
        LocalObservation
            The recorded observation.
        """
        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

        obs = LocalObservation(
            peer_did=peer_did,
            behaviour=behaviour,
            score=score,
            proof=proof,
            metadata=metadata or {},
        )

        # Append observation (with history cap)
        history = self._observations[peer_did]
        history.append(obs)
        if len(history) > MAX_LOCAL_HISTORY:
            self._observations[peer_did] = history[-MAX_LOCAL_HISTORY:]

        # Recompute local rank
        self._recompute_local_rank(peer_did)

        return obs

    def _recompute_local_rank(self, peer_did: str) -> None:
        """Recompute the aggregated local rank for a peer.

        Uses the three-factor scoring from the Ranking Protocol:
        1. Request success rate (weight 0.4)
        2. Request validity rate (weight 0.3)
        3. Interaction-volume-normalized contribution (weight 0.3)

        Scores are exponentially decayed by age.
        """
        observations = self._observations.get(peer_did, [])
        if not observations:
            return

        now = time.time()
        successes = 0
        failures = 0
        valid_requests = 0
        invalid_requests = 0
        weighted_sum = 0.0
        weight_total = 0.0

        for obs in observations:
            # Exponential decay: more recent observations weigh more
            age_seconds = max(0, now - obs.timestamp)
            age_hours = age_seconds / 3600.0
            decay = LOCAL_SCORE_DECAY ** age_hours

            weighted_sum += obs.score * decay
            weight_total += decay

            if obs.behaviour == BehaviourType.REQUEST_SUCCESS:
                successes += 1
            elif obs.behaviour == BehaviourType.REQUEST_FAILURE:
                failures += 1
            elif obs.behaviour == BehaviourType.VALID_REQUEST:
                valid_requests += 1
            elif obs.behaviour == BehaviourType.INVALID_REQUEST:
                invalid_requests += 1
            elif obs.behaviour == BehaviourType.BYZANTINE:
                # Byzantine behaviour has a strong penalty
                failures += 3  # Triple-counted

        total_requests = successes + failures
        success_rate = successes / total_requests if total_requests > 0 else 0.5

        total_received = valid_requests + invalid_requests
        validity_rate = valid_requests / total_received if total_received > 0 else 0.5

        # Weighted average of observations
        avg_score = weighted_sum / weight_total if weight_total > 0 else 0.5

        # Three-factor composite: the paper's local scoring formula
        composite = (
            0.4 * success_rate
            + 0.3 * validity_rate
            + 0.3 * avg_score
        )

        self._local_ranks[peer_did] = LocalRankRecord(
            peer_did=peer_did,
            score=composite,
            request_success_rate=success_rate,
            request_validity_rate=validity_rate,
            total_interactions=len(observations),
            last_updated=now,
        )

    # ── Local Rank Queries ────────────────────────────────────────────────

    def get_local_rank(self, peer_did: str) -> Optional[LocalRankRecord]:
        """Get the local rank record for a peer.

        Returns ``None`` if no observations have been recorded for the peer.
        """
        return self._local_ranks.get(peer_did)

    def get_local_score(self, peer_did: str) -> float:
        """Get just the numeric local score (0.0 if unknown)."""
        rec = self._local_ranks.get(peer_did)
        return rec.score if rec is not None else 0.0

    def get_all_local_ranks(self) -> Dict[str, LocalRankRecord]:
        """Return all local rank records."""
        return dict(self._local_ranks)

    def get_top_peers(self, n: int = 10) -> List[LocalRankRecord]:
        """Return the top-N highest-ranked local peers."""
        ranked = sorted(self._local_ranks.values(), key=lambda r: r.score, reverse=True)
        return ranked[:n]

    # ── Global Rank Queries ───────────────────────────────────────────────

    async def get_global_rank(self, peer_did: str) -> float:
        """Query the global rank for a peer.

        In a real network, this triggers the 4-phase sampling protocol.
        For now, we check the local cache, then query the network if
        available, falling back to local score.

        Returns a score in [0, 1].
        """
        # Check cache (if not stale — 5 min TTL)
        cached = self._global_cache.get(peer_did)
        if cached is not None and (time.time() - cached.last_sampled) < 300:
            return cached.global_score

        # Try network query
        if self._client is not None:
            try:
                raw = await self._client.dht_get(f"ranking:global:{peer_did}")
                if raw is not None and isinstance(raw, dict):
                    record = GlobalRankRecord(
                        peer_did=peer_did,
                        global_score=raw.get("score", 0.0),
                        sample_count=raw.get("samples", 0),
                        confidence=raw.get("confidence", 0.0),
                        ks_statistic=raw.get("ks_stat", 0.0),
                    )
                    self._global_cache[peer_did] = record
                    return record.global_score
            except Exception:
                logger.debug("Failed to get global rank for %s", peer_did, exc_info=True)

        # Fall back to local score
        return self.get_local_score(peer_did)

    async def get_global_rank_record(self, peer_did: str) -> Optional[GlobalRankRecord]:
        """Get the full global rank record including confidence and KS statistic."""
        await self.get_global_rank(peer_did)  # Ensure cache is populated
        return self._global_cache.get(peer_did)

    # ── Trustworthiness Checks ────────────────────────────────────────────

    def is_trustworthy_local(
        self,
        peer_did: str,
        threshold: Optional[float] = None,
    ) -> bool:
        """Check if a peer meets the reputation threshold (local rank only).

        Parameters
        ----------
        peer_did : str
            The DID to check.
        threshold : float, optional
            Override the default threshold.

        Returns
        -------
        bool
        """
        threshold = threshold if threshold is not None else self._default_threshold
        return self.get_local_score(peer_did) >= threshold

    async def is_trustworthy(
        self,
        peer_did: str,
        threshold: Optional[float] = None,
    ) -> bool:
        """Check trustworthiness using global rank (async network query).

        Falls back to local rank if the network is unavailable.
        """
        threshold = threshold if threshold is not None else self._default_threshold
        score = await self.get_global_rank(peer_did)
        return score >= threshold

    def get_trust_tier(self, peer_did: str) -> TrustTier:
        """Map a peer's local score to a discretized trust tier."""
        score = self.get_local_score(peer_did)
        return TrustTier.from_score(score)

    # ── Slash / Report ────────────────────────────────────────────────────

    def report_slash(
        self,
        target_did: str,
        reason: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> SlashReport:
        """Submit a slash report for malicious behaviour.

        In the Ranking Protocol, slash reports trigger:
        1. Freeze of the target's rank
        2. Investigation by sampling protocol
        3. If confirmed: token slashing

        Parameters
        ----------
        target_did : str
            DID of the malicious peer.
        reason : str
            Description of the misbehaviour.
        evidence : dict, optional
            Supporting evidence.

        Returns
        -------
        SlashReport
        """
        import uuid as _uuid

        report = SlashReport(
            target_did=target_did,
            reporter_did=self._local_did,
            reason=reason,
            evidence=evidence or {},
            report_id=_uuid.uuid4().hex[:12],
        )

        self._slash_reports.append(report)

        # Also record as a strong negative observation
        self.report_behaviour(
            peer_did=target_did,
            behaviour=BehaviourType.BYZANTINE,
            score=0.0,
            metadata={"slash_report": report.report_id, "reason": reason},
        )

        logger.warning(
            "Slash report filed: %s → %s (reason: %s)",
            self._local_did,
            target_did,
            reason,
        )

        return report

    # ── Statistics ────────────────────────────────────────────────────────

    def compute_network_statistics(self) -> Dict[str, Any]:
        """Compute aggregate statistics from local observations.

        Returns a dict with: mean_score, median_score, std_score,
        peer_count, total_observations, tier_distribution.
        """
        scores = [r.score for r in self._local_ranks.values()]
        if not scores:
            return {
                "mean_score": 0.0,
                "median_score": 0.0,
                "std_score": 0.0,
                "peer_count": 0,
                "total_observations": 0,
                "tier_distribution": {},
            }

        tier_dist: Dict[str, int] = defaultdict(int)
        for r in self._local_ranks.values():
            tier_dist[TrustTier.from_score(r.score).value] += 1

        return {
            "mean_score": statistics.mean(scores),
            "median_score": statistics.median(scores),
            "std_score": statistics.stdev(scores) if len(scores) >= 2 else 0.0,
            "peer_count": len(scores),
            "total_observations": self.total_observations,
            "tier_distribution": dict(tier_dist),
        }

    # ── Internal: Median Game (from Ranking Protocol) ─────────────────────

    @staticmethod
    def median_game_reward(scores: List[float], my_score: float) -> float:
        """Compute reward based on the Ranking Protocol's median game.

        Nodes closest to the median receive the highest reward.
        Nash Equilibrium = reporting honestly.

        Parameters
        ----------
        scores : list of float
            All submitted scores from sampling.
        my_score : float
            This node's submitted score.

        Returns
        -------
        float
            Reward multiplier (higher is better; 1.0 = at the median).
        """
        if not scores:
            return 0.0
        med = statistics.median(scores)
        distance = abs(my_score - med)
        # Reward decays exponentially with distance from median
        return math.exp(-3.0 * distance)

    # ── Serialization ─────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        """Serialize the current reputation state (for persistence)."""
        return {
            "local_did": self._local_did,
            "local_ranks": {
                did: {
                    "score": r.score,
                    "success_rate": r.request_success_rate,
                    "validity_rate": r.request_validity_rate,
                    "interactions": r.total_interactions,
                    "updated": r.last_updated,
                }
                for did, r in self._local_ranks.items()
            },
            "slash_reports": len(self._slash_reports),
            "statistics": self.compute_network_statistics(),
        }

    def __repr__(self) -> str:
        return (
            f"ReputationClient(local_did={self._local_did!r}, "
            f"peers={self.peer_count}, obs={self.total_observations})"
        )
