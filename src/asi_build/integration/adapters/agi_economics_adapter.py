"""
AGI Economics ↔ Blackboard Adapter
====================================

Bridges the AGI Economics module (``TokenEconomicsEngine``,
``BondingCurveEngine``, ``ReputationSystem``, ``GameTheoryAnalyzer``,
``MarketplaceDynamics``, ``ValueAlignmentEngine``) with the Cognitive
Blackboard.

Topics produced
~~~~~~~~~~~~~~~
- ``economics.token.metrics``          — Market cap, prices, supply info
- ``economics.token.transfer``         — Token transfer events
- ``economics.staking.event``          — Stake/unstake events
- ``economics.market.trade``           — Order matching events
- ``economics.market.data``            — Order book snapshots, spread
- ``economics.reputation.update``      — Reputation score changes
- ``economics.reputation.trust``       — Trust network updates
- ``economics.game_theory.analysis``   — Equilibria, Pareto, Shapley
- ``economics.value_alignment.score``  — Agent alignment scores
- ``economics.bonding_curve.price``    — Bonding curve price updates

Topics consumed
~~~~~~~~~~~~~~~
- ``reasoning.*``       — Strategic reasoning for market decisions
- ``agi_comm.*``        — Communication protocol for economic negotiations
- ``consciousness.*``   — Consciousness metrics for value alignment
- ``safety.*``          — Safety constraints on economic actions

Events emitted
~~~~~~~~~~~~~~
- ``economics.token.transfer.completed``       — Token transfer finalized
- ``economics.market.trade.executed``           — Trade executed on marketplace
- ``economics.reputation.threshold.crossed``    — Reputation crossed tier boundary
- ``economics.value_alignment.alert``           — Alignment score dropped below threshold
- ``economics.bonding_curve.price.changed``     — Significant price movement

Events listened
~~~~~~~~~~~~~~~
- ``reasoning.inference.completed``             — Feed into strategic analysis
- ``agi_comm.negotiation.completed``            — Update economic positions
- ``consciousness.state.changed``               — Adjust value alignment weights
- ``safety.ethics.verification``                — Apply safety constraints
"""

from __future__ import annotations

import logging
import threading
import time
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..protocols import (
    BlackboardEntry,
    BlackboardQuery,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    EventHandler,
    ModuleCapability,
    ModuleInfo,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy import — the agi_economics module may not be available
# ---------------------------------------------------------------------------
_economics_module = None


def _get_economics():
    """Lazy import of agi_economics module for graceful degradation."""
    global _economics_module
    if _economics_module is None:
        try:
            from asi_build import agi_economics as _em

            _economics_module = _em
        except (ImportError, ModuleNotFoundError):
            _economics_module = False
    return _economics_module if _economics_module is not False else None


def _decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal values to floats for JSON-safe payloads."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_decimal_to_float(v) for v in obj]
    return obj


class AGIEconomicsBlackboardAdapter:
    """Adapter connecting the AGI Economics module to the Cognitive Blackboard.

    Wraps up to six components:

    - ``TokenEconomicsEngine`` — token management, staking, transfers, inflation
    - ``BondingCurveEngine`` — automated market makers with bonding curves
    - ``ReputationSystem`` — multi-dimensional reputation with trust networks
    - ``GameTheoryAnalyzer`` — game-theoretic analysis of market interactions
    - ``MarketplaceDynamics`` — order book matching, auctions, market simulation
    - ``ValueAlignmentEngine`` — value alignment measurement with incentives

    All components are optional; the adapter gracefully skips operations for
    any component that is ``None``.

    Parameters
    ----------
    token_engine : optional
        A ``TokenEconomicsEngine`` instance.
    bonding_engine : optional
        A ``BondingCurveEngine`` instance.
    reputation : optional
        A ``ReputationSystem`` instance.
    game_theory : optional
        A ``GameTheoryAnalyzer`` instance.
    marketplace : optional
        A ``MarketplaceDynamics`` instance.
    value_alignment : optional
        A ``ValueAlignmentEngine`` instance.
    token_ttl : float
        TTL in seconds for token metric entries (default 120).
    market_ttl : float
        TTL for market data entries (default 60).
    reputation_ttl : float
        TTL for reputation entries (default 300).
    analysis_ttl : float
        TTL for game-theory analysis entries (default 600).
    alignment_ttl : float
        TTL for value alignment entries (default 300).
    """

    MODULE_NAME = "agi_economics"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        token_engine: Any = None,
        bonding_engine: Any = None,
        reputation: Any = None,
        game_theory: Any = None,
        marketplace: Any = None,
        value_alignment: Any = None,
        *,
        token_ttl: float = 120.0,
        market_ttl: float = 60.0,
        reputation_ttl: float = 300.0,
        analysis_ttl: float = 600.0,
        alignment_ttl: float = 300.0,
    ) -> None:
        self._token_engine = token_engine
        self._bonding_engine = bonding_engine
        self._reputation = reputation
        self._game_theory = game_theory
        self._marketplace = marketplace
        self._value_alignment = value_alignment

        self._token_ttl = token_ttl
        self._market_ttl = market_ttl
        self._reputation_ttl = reputation_ttl
        self._analysis_ttl = analysis_ttl
        self._alignment_ttl = alignment_ttl

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change-detection state
        self._last_token_metrics: Optional[Dict[str, Any]] = None
        self._last_bonding_prices: Optional[Dict[str, float]] = None
        self._last_reputation_metrics: Optional[Dict[str, Any]] = None
        self._last_market_data: Optional[Dict[str, Any]] = None
        self._last_alignment_scores: Optional[Dict[str, float]] = None

        # Safety constraint cache
        self._safety_constraints: Dict[str, Any] = {}

    # ── BlackboardParticipant protocol ────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER
                | ModuleCapability.CONSUMER
                | ModuleCapability.TRANSFORMER
                | ModuleCapability.VALIDATOR
            ),
            description=(
                "AGI Economics module: token economics, bonding curves, "
                "reputation systems, game-theoretic analysis, marketplace "
                "dynamics, and value alignment scoring."
            ),
            topics_produced=frozenset(
                {
                    "economics.token.metrics",
                    "economics.token.transfer",
                    "economics.staking.event",
                    "economics.market.trade",
                    "economics.market.data",
                    "economics.reputation.update",
                    "economics.reputation.trust",
                    "economics.game_theory.analysis",
                    "economics.value_alignment.score",
                    "economics.bonding_curve.price",
                }
            ),
            topics_consumed=frozenset(
                {
                    "reasoning",
                    "agi_comm",
                    "consciousness",
                    "safety",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "AGIEconomicsBlackboardAdapter registered with blackboard "
            "(token=%s, bonding=%s, reputation=%s, game_theory=%s, "
            "marketplace=%s, value_alignment=%s)",
            self._token_engine is not None,
            self._bonding_engine is not None,
            self._reputation is not None,
            self._game_theory is not None,
            self._marketplace is not None,
            self._value_alignment is not None,
        )

    # ── EventEmitter protocol ─────────────────────────────────────────

    def set_event_handler(self, handler: EventHandler) -> None:
        self._event_handler = handler

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit an event via the injected handler."""
        if self._event_handler is not None:
            self._event_handler(
                CognitiveEvent(
                    event_type=event_type,
                    payload=_decimal_to_float(payload),
                    source=self.MODULE_NAME,
                )
            )

    # ── EventListener protocol ────────────────────────────────────────

    def handle_event(self, event: CognitiveEvent) -> None:
        """Handle incoming events from other modules."""
        try:
            if event.event_type.startswith("reasoning."):
                self._handle_reasoning_event(event)
            elif event.event_type.startswith("agi_comm."):
                self._handle_comm_event(event)
            elif event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
            elif event.event_type.startswith("safety."):
                self._handle_safety_event(event)
        except Exception:
            logger.debug(
                "AGIEconomicsAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current economic state.

        Called during a production sweep.  Collects:
        1. Token metrics (prices, supply, market cap)
        2. Bonding curve prices
        3. Reputation metrics
        4. Marketplace data
        5. Value alignment scores
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            token_entry = self._produce_token_metrics()
            if token_entry is not None:
                entries.append(token_entry)

            bonding_entry = self._produce_bonding_prices()
            if bonding_entry is not None:
                entries.append(bonding_entry)

            reputation_entries = self._produce_reputation()
            entries.extend(reputation_entries)

            market_entry = self._produce_market_data()
            if market_entry is not None:
                entries.append(market_entry)

            alignment_entry = self._produce_alignment()
            if alignment_entry is not None:
                entries.append(alignment_entry)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        - ``reasoning.*``       — Strategic reasoning for market decisions
        - ``agi_comm.*``        — Economic negotiations
        - ``consciousness.*``   — Value alignment recalibration
        - ``safety.*``          — Apply safety constraints to economic actions
        """
        for entry in entries:
            try:
                if entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("agi_comm."):
                    self._consume_comm(entry)
                elif entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
                elif entry.topic.startswith("safety."):
                    self._consume_safety(entry)
            except Exception:
                logger.debug(
                    "AGIEconomicsAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── BlackboardTransformer protocol ────────────────────────────────

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        """Enrich entries with economic context.

        Adds token prices and reputation scores to entries passing through
        this adapter.
        """
        if self._token_engine is None and self._reputation is None:
            return entries

        enriched: List[BlackboardEntry] = []
        for entry in entries:
            try:
                metadata = dict(entry.metadata) if entry.metadata else {}

                # Add token price context
                if self._token_engine is not None:
                    try:
                        asi_price = self._token_engine.get_token_price("ASI", "USD")
                        metadata["asi_token_price"] = float(asi_price)
                    except Exception:
                        pass

                # Add reputation context if the entry references an agent
                if self._reputation is not None:
                    agent_id = entry.data.get("agent_id") if isinstance(entry.data, dict) else None
                    if agent_id:
                        try:
                            rep = self._reputation.get_agent_reputation(agent_id)
                            metadata["agent_reputation_score"] = rep.get(
                                "overall_score", 0.0
                            )
                        except Exception:
                            pass

                enriched.append(
                    BlackboardEntry(
                        topic=entry.topic,
                        data=entry.data,
                        source_module=entry.source_module,
                        confidence=entry.confidence,
                        priority=entry.priority,
                        ttl_seconds=entry.ttl_seconds,
                        tags=entry.tags,
                        metadata=metadata,
                    )
                )
            except Exception:
                enriched.append(entry)

        return enriched

    # ── Producer helpers ──────────────────────────────────────────────

    def _produce_token_metrics(self) -> Optional[BlackboardEntry]:
        """Produce token metrics entry with change detection."""
        if self._token_engine is None:
            return None

        try:
            # Collect metrics for the primary ASI token
            metrics = self._token_engine.get_token_metrics("ASI")
            metrics_safe = _decimal_to_float(metrics)

            # Change detection — compare price and supply
            metrics_key = {
                "price": metrics_safe.get("price"),
                "total_supply": metrics_safe.get("total_supply"),
                "market_cap": metrics_safe.get("market_cap"),
            }
            if metrics_key == self._last_token_metrics:
                return None
            self._last_token_metrics = metrics_key

            entry = BlackboardEntry(
                topic="economics.token.metrics",
                data={
                    "token": "ASI",
                    "price": metrics_safe.get("price", 0.0),
                    "total_supply": metrics_safe.get("total_supply", 0),
                    "market_cap": metrics_safe.get("market_cap", 0.0),
                    "staked_amount": metrics_safe.get("staked_amount", 0.0),
                    "inflation_rate": metrics_safe.get("inflation_rate", 0.0),
                    "timestamp": time.time(),
                },
                source_module=self.MODULE_NAME,
                confidence=0.95,
                priority=EntryPriority.NORMAL,
                ttl_seconds=self._token_ttl,
                tags=frozenset({"token", "metrics", "ASI", "economics"}),
                metadata={"token_type": "ASI"},
            )
            return entry
        except Exception:
            logger.debug("Failed to produce token metrics", exc_info=True)
            return None

    def _produce_bonding_prices(self) -> Optional[BlackboardEntry]:
        """Produce bonding curve price entries with change detection."""
        if self._bonding_engine is None:
            return None

        try:
            market_data = self._bonding_engine.get_all_market_data()
            prices = {}
            for token, data in market_data.items():
                price = getattr(data, "price", None) or data.get("price") if isinstance(data, dict) else None
                if price is not None:
                    prices[token] = float(price) if isinstance(price, Decimal) else price

            if not prices:
                return None

            # Change detection — >0.1% price movement
            if self._last_bonding_prices is not None:
                changed = False
                for token, price in prices.items():
                    last = self._last_bonding_prices.get(token, 0.0)
                    if last == 0.0 or abs(price - last) / max(abs(last), 1e-9) > 0.001:
                        changed = True
                        break
                if not changed:
                    return None

            old_prices = self._last_bonding_prices or {}
            self._last_bonding_prices = prices

            entry = BlackboardEntry(
                topic="economics.bonding_curve.price",
                data={
                    "prices": prices,
                    "price_changes": {
                        t: prices[t] - old_prices.get(t, prices[t])
                        for t in prices
                    },
                    "timestamp": time.time(),
                },
                source_module=self.MODULE_NAME,
                confidence=0.95,
                priority=EntryPriority.HIGH,
                ttl_seconds=self._market_ttl,
                tags=frozenset({"bonding_curve", "price", "market"}),
            )

            # Emit event for significant price changes (>5%)
            for token, price in prices.items():
                last = old_prices.get(token, price)
                if last > 0 and abs(price - last) / last > 0.05:
                    self._emit(
                        "economics.bonding_curve.price.changed",
                        {
                            "token": token,
                            "old_price": last,
                            "new_price": price,
                            "change_pct": (price - last) / last * 100,
                        },
                    )

            return entry
        except Exception:
            logger.debug("Failed to produce bonding curve prices", exc_info=True)
            return None

    def _produce_reputation(self) -> List[BlackboardEntry]:
        """Produce reputation metric and trust network entries."""
        if self._reputation is None:
            return []

        entries: List[BlackboardEntry] = []

        try:
            sys_metrics = self._reputation.get_system_reputation_metrics()
            sys_metrics_safe = _decimal_to_float(sys_metrics)

            # Change detection
            metrics_key = {
                "total_agents": sys_metrics_safe.get("total_agents"),
                "avg_score": sys_metrics_safe.get("avg_overall_score"),
            }
            if metrics_key == self._last_reputation_metrics:
                return []
            self._last_reputation_metrics = metrics_key

            # System-level reputation update
            entry = BlackboardEntry(
                topic="economics.reputation.update",
                data={
                    "total_agents": sys_metrics_safe.get("total_agents", 0),
                    "avg_overall_score": sys_metrics_safe.get("avg_overall_score", 0.0),
                    "dimension_averages": sys_metrics_safe.get("dimension_averages", {}),
                    "total_events": sys_metrics_safe.get("total_events", 0),
                    "timestamp": time.time(),
                },
                source_module=self.MODULE_NAME,
                confidence=0.9,
                priority=EntryPriority.NORMAL,
                ttl_seconds=self._reputation_ttl,
                tags=frozenset({"reputation", "system", "metrics"}),
                metadata={"total_agents": sys_metrics_safe.get("total_agents", 0)},
            )
            entries.append(entry)

            # Trust network summary
            trust_data = sys_metrics_safe.get("trust_network", {})
            if trust_data:
                trust_entry = BlackboardEntry(
                    topic="economics.reputation.trust",
                    data={
                        "total_relationships": trust_data.get("total_relationships", 0),
                        "avg_trust_score": trust_data.get("avg_trust_score", 0.0),
                        "network_density": trust_data.get("network_density", 0.0),
                        "timestamp": time.time(),
                    },
                    source_module=self.MODULE_NAME,
                    confidence=0.85,
                    priority=EntryPriority.NORMAL,
                    ttl_seconds=self._reputation_ttl,
                    tags=frozenset({"reputation", "trust", "network"}),
                )
                entries.append(trust_entry)

        except Exception:
            logger.debug("Failed to produce reputation entries", exc_info=True)

        return entries

    def _produce_market_data(self) -> Optional[BlackboardEntry]:
        """Produce marketplace data (order book snapshots)."""
        if self._marketplace is None:
            return None

        try:
            # Get data for primary service market
            market_data = self._marketplace.get_market_data("compute")
            if market_data is None:
                return None

            data_dict = (
                market_data
                if isinstance(market_data, dict)
                else {
                    "best_bid": getattr(market_data, "best_bid", None),
                    "best_ask": getattr(market_data, "best_ask", None),
                    "spread": getattr(market_data, "spread", None),
                    "volume_24h": getattr(market_data, "volume_24h", None),
                    "last_trade_price": getattr(market_data, "last_trade_price", None),
                }
            )
            data_safe = _decimal_to_float(data_dict)

            # Change detection — check volume and spread
            market_key = {
                "volume": data_safe.get("volume_24h"),
                "spread": data_safe.get("spread"),
            }
            if market_key == self._last_market_data:
                return None
            self._last_market_data = market_key

            entry = BlackboardEntry(
                topic="economics.market.data",
                data={
                    "service_type": "compute",
                    **data_safe,
                    "timestamp": time.time(),
                },
                source_module=self.MODULE_NAME,
                confidence=0.9,
                priority=EntryPriority.NORMAL,
                ttl_seconds=self._market_ttl,
                tags=frozenset({"market", "order_book", "compute"}),
            )
            return entry
        except Exception:
            logger.debug("Failed to produce market data", exc_info=True)
            return None

    def _produce_alignment(self) -> Optional[BlackboardEntry]:
        """Produce value alignment scores."""
        if self._value_alignment is None:
            return None

        try:
            sys_metrics = self._value_alignment.get_system_value_metrics()
            sys_metrics_safe = _decimal_to_float(sys_metrics)

            # Change detection
            scores_key = {
                "avg_alignment": sys_metrics_safe.get("avg_alignment_score"),
                "total_agents": sys_metrics_safe.get("total_agents"),
            }
            if scores_key == self._last_alignment_scores:
                return None
            self._last_alignment_scores = scores_key

            avg_score = sys_metrics_safe.get("avg_alignment_score", 0.0)

            entry = BlackboardEntry(
                topic="economics.value_alignment.score",
                data={
                    "avg_alignment_score": avg_score,
                    "total_agents": sys_metrics_safe.get("total_agents", 0),
                    "dimension_scores": sys_metrics_safe.get("dimension_scores", {}),
                    "total_measurements": sys_metrics_safe.get("total_measurements", 0),
                    "timestamp": time.time(),
                },
                source_module=self.MODULE_NAME,
                confidence=0.85,
                priority=(
                    EntryPriority.HIGH
                    if avg_score < 0.5
                    else EntryPriority.NORMAL
                ),
                ttl_seconds=self._alignment_ttl,
                tags=frozenset({"value_alignment", "ethics", "alignment"}),
                metadata={"avg_alignment_score": avg_score},
            )

            # Alert if alignment is dangerously low
            if avg_score < 0.3:
                self._emit(
                    "economics.value_alignment.alert",
                    {
                        "avg_alignment_score": avg_score,
                        "severity": "critical" if avg_score < 0.1 else "warning",
                        "entry_id": entry.entry_id,
                    },
                )

            return entry
        except Exception:
            logger.debug("Failed to produce alignment scores", exc_info=True)
            return None

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Feed reasoning results into game-theory analysis.

        When strategic reasoning results arrive, use the game theory
        analyzer to evaluate optimal economic responses.
        """
        if self._game_theory is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        strategy = data.get("strategy", data.get("inference", data.get("result")))
        if strategy is None:
            return

        # Game-theory analysis results get posted on next produce() cycle
        logger.debug(
            "Received reasoning result for economic strategy analysis: %s",
            str(strategy)[:100],
        )

    def _consume_comm(self, entry: BlackboardEntry) -> None:
        """Process negotiation outcomes into economic positions.

        When a negotiation completes, update economic positions based on
        agreed-upon terms.
        """
        if self._token_engine is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        # Handle negotiation outcomes that involve token transfers
        if entry.topic.startswith("agi_comm.negotiation."):
            agreement = data.get("agreed_proposal", data.get("agreement"))
            if agreement and isinstance(agreement, dict):
                transfers = agreement.get("token_transfers", [])
                for transfer in transfers:
                    try:
                        result = self._token_engine.transfer_tokens(
                            from_agent=transfer.get("from", ""),
                            to_agent=transfer.get("to", ""),
                            token_type=transfer.get("token_type", "ASI"),
                            amount=Decimal(str(transfer.get("amount", 0))),
                        )
                        if result is not None:
                            self._emit(
                                "economics.token.transfer.completed",
                                {
                                    "transfer": _decimal_to_float(transfer),
                                    "result": str(result),
                                },
                            )
                    except Exception:
                        logger.debug(
                            "Failed to execute negotiated transfer", exc_info=True
                        )

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Adjust value alignment weights based on consciousness state.

        Higher consciousness states may require stricter alignment checks.
        """
        if self._value_alignment is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}
        phi = data.get("phi", data.get("phi_value"))
        if phi is not None:
            logger.debug(
                "Consciousness phi=%s noted for value alignment calibration", phi
            )

    def _consume_safety(self, entry: BlackboardEntry) -> None:
        """Apply safety constraints to economic actions.

        Safety verification results may restrict certain economic operations.
        """
        data = entry.data if isinstance(entry.data, dict) else {}

        # Cache safety constraints for use in future economic operations
        if entry.topic.startswith("safety.ethics."):
            is_ethical = data.get("is_ethical", True)
            if not is_ethical:
                constraint = {
                    "source_entry": entry.entry_id,
                    "blocked_actions": data.get("blocked_actions", []),
                    "reason": data.get("verification_summary", ""),
                    "timestamp": time.time(),
                }
                self._safety_constraints[entry.entry_id] = constraint
                logger.warning(
                    "Safety constraint received — blocking actions: %s",
                    constraint.get("blocked_actions", []),
                )

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_reasoning_event(self, event: CognitiveEvent) -> None:
        """Handle reasoning events for strategic economic analysis."""
        if self._game_theory is None:
            return

        payload = event.payload or {}
        # If reasoning produced an optimization result, evaluate it
        if "strategy" in payload or "optimization" in payload:
            logger.debug(
                "Reasoning event with strategy content received for game-theory eval"
            )

    def _handle_comm_event(self, event: CognitiveEvent) -> None:
        """Handle communication events for economic position updates."""
        if event.event_type == "agi_comm.negotiation.completed":
            payload = event.payload or {}
            agreement_rate = payload.get("agreement_rate", 0.0)
            logger.debug(
                "Negotiation completed (agreement_rate=%.2f) — "
                "evaluating economic implications",
                agreement_rate,
            )

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Handle consciousness state changes for alignment recalibration."""
        if self._value_alignment is None:
            return

        payload = event.payload or {}
        new_state = payload.get("new_state", "")
        logger.debug(
            "Consciousness state changed to '%s' — alignment weights may adjust",
            new_state,
        )

    def _handle_safety_event(self, event: CognitiveEvent) -> None:
        """Handle safety events — cache constraints on economic operations."""
        payload = event.payload or {}
        if payload.get("is_ethical") is False:
            constraint = {
                "event_id": event.event_id,
                "blocked_actions": payload.get("blocked_actions", []),
                "reason": payload.get("reason", ""),
                "timestamp": time.time(),
            }
            self._safety_constraints[event.event_id] = constraint
            logger.warning(
                "Safety event constraint: %s", constraint.get("reason", "unknown")
            )

    # ── Snapshot ──────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all economic components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_token_engine": self._token_engine is not None,
            "has_bonding_engine": self._bonding_engine is not None,
            "has_reputation": self._reputation is not None,
            "has_game_theory": self._game_theory is not None,
            "has_marketplace": self._marketplace is not None,
            "has_value_alignment": self._value_alignment is not None,
            "active_safety_constraints": len(self._safety_constraints),
            "registered": self._blackboard is not None,
        }

        if self._token_engine is not None:
            try:
                snap["token_metrics"] = _decimal_to_float(
                    self._token_engine.get_token_metrics("ASI")
                )
            except Exception:
                snap["token_metrics"] = None

        if self._bonding_engine is not None:
            try:
                md = self._bonding_engine.get_all_market_data()
                snap["bonding_markets"] = len(md) if md else 0
            except Exception:
                snap["bonding_markets"] = None

        if self._reputation is not None:
            try:
                snap["reputation_metrics"] = _decimal_to_float(
                    self._reputation.get_system_reputation_metrics()
                )
            except Exception:
                snap["reputation_metrics"] = None

        if self._marketplace is not None:
            try:
                snap["marketplace_data"] = _decimal_to_float(
                    self._marketplace.get_market_data("compute")
                )
            except Exception:
                snap["marketplace_data"] = None

        if self._value_alignment is not None:
            try:
                snap["alignment_metrics"] = _decimal_to_float(
                    self._value_alignment.get_system_value_metrics()
                )
            except Exception:
                snap["alignment_metrics"] = None

        return snap
