"""
Safety ↔ Blackboard Adapter
=============================

Bridges the Safety module (``ConstitutionalAI``, ``EthicalVerificationEngine``,
``TheoremProver``, ``GovernanceFramework``) with the Cognitive Blackboard.

**SAFETY-CRITICAL**: Any verification failure is posted as ``CRITICAL`` priority.
The consume path auto-verifies proposals from reasoning and economics modules.

Topics produced
~~~~~~~~~~~~~~~
- ``safety.ethics.verification``   — Ethical verification results (is_ethical, confidence)
- ``safety.ethics.report``         — Full ethics reports (text)
- ``safety.proof.result``          — Theorem proving results (is_valid, method, steps)
- ``safety.constitution.status``   — Constitutional AI status, active principles
- ``safety.alignment.check``       — Action alignment check results
- ``safety.governance.proposal``   — DAO proposals and voting results
- ``safety.governance.audit``      — Audit ledger entries

Topics consumed
~~~~~~~~~~~~~~~
- ``reasoning.*``       — Proposals/actions to auto-verify ethically
- ``agi_comm.*``        — Negotiation proposals for ethics check
- ``economics.*``       — Economic actions for constitutional compliance
- ``consciousness.*``   — Consciousness state for oversight level

Events emitted
~~~~~~~~~~~~~~
- ``safety.ethics.verification.passed``    — Verification passed
- ``safety.ethics.verification.failed``    — **CRITICAL** — Verification failed
- ``safety.proof.completed``               — Theorem proof attempt finished
- ``safety.constitution.violated``         — **CRITICAL** — Constitutional violation
- ``safety.alignment.failed``              — **CRITICAL** — Alignment check failed
- ``safety.governance.proposal.submitted`` — New governance proposal

Events listened
~~~~~~~~~~~~~~~
- ``reasoning.inference.completed``        — Auto-verify inference proposals
- ``agi_comm.negotiation.completed``       — Verify negotiation outcomes
- ``economics.token.transfer.completed``   — Verify economic actions
- ``consciousness.state.changed``          — Adjust oversight level
"""

from __future__ import annotations

import logging
import threading
import time
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
# Lazy import — the safety module may not be available
# ---------------------------------------------------------------------------
_safety_module = None


def _get_safety():
    """Lazy import of safety module for graceful degradation."""
    global _safety_module
    if _safety_module is None:
        try:
            from asi_build import safety as _sm

            _safety_module = _sm
        except (ImportError, ModuleNotFoundError):
            _safety_module = False
    return _safety_module if _safety_module is not False else None


class SafetyBlackboardAdapter:
    """Adapter connecting the Safety module to the Cognitive Blackboard.

    **Safety-critical design**: All verification failures are posted as
    ``CRITICAL`` priority entries and emit urgent events.  The consume
    path auto-verifies proposals arriving from reasoning and economics
    modules — if verification fails, a CRITICAL entry is immediately posted.

    Wraps up to four components:

    - ``ConstitutionalAI`` — constitutional value alignment and constraint enforcement
    - ``EthicalVerificationEngine`` — formal verification of ethical constraints
    - ``TheoremProver`` — SymPy-based theorem proving (resolution, natural deduction)
    - ``GovernanceFramework`` — DAO proposals, voting, audit (lazy-loaded)

    All components are optional; the adapter gracefully skips operations for
    any component that is ``None``.

    Parameters
    ----------
    constitutional : optional
        A ``ConstitutionalAI`` instance.
    verifier : optional
        An ``EthicalVerificationEngine`` instance.
    prover : optional
        A ``TheoremProver`` instance.
    governance : optional
        A ``GovernanceFramework`` instance (or lazy-loaded governance package).
    verification_ttl : float
        TTL in seconds for verification result entries (default 600).
    report_ttl : float
        TTL for ethics report entries (default 900).
    proof_ttl : float
        TTL for theorem proof entries (default 600).
    constitution_ttl : float
        TTL for constitution status entries (default 300).
    governance_ttl : float
        TTL for governance entries (default 600).
    auto_verify : bool
        If ``True``, automatically verify proposals from reasoning and
        economics modules on consume (default ``True``).
    """

    MODULE_NAME = "safety"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        constitutional: Any = None,
        verifier: Any = None,
        prover: Any = None,
        governance: Any = None,
        *,
        verification_ttl: float = 600.0,
        report_ttl: float = 900.0,
        proof_ttl: float = 600.0,
        constitution_ttl: float = 300.0,
        governance_ttl: float = 600.0,
        auto_verify: bool = True,
    ) -> None:
        self._constitutional = constitutional
        self._verifier = verifier
        self._prover = prover
        self._governance = governance

        self._verification_ttl = verification_ttl
        self._report_ttl = report_ttl
        self._proof_ttl = proof_ttl
        self._constitution_ttl = constitution_ttl
        self._governance_ttl = governance_ttl
        self._auto_verify = auto_verify

        # Blackboard reference (set on registration)
        self._blackboard: Any = None
        self._event_handler: Optional[EventHandler] = None
        self._lock = threading.RLock()

        # Change-detection state
        self._last_verification_count: int = 0
        self._last_constitution_status: Optional[Dict[str, Any]] = None
        self._last_governance_proposals: int = 0
        self._last_proof_count: int = 0

        # Oversight level (influenced by consciousness state)
        self._oversight_level: float = 1.0  # 0.0 = relaxed, 1.0 = strict

        # Verification results buffer (for produce cycle)
        self._pending_verifications: List[Dict[str, Any]] = []
        self._pending_proofs: List[Dict[str, Any]] = []

    # ── BlackboardParticipant protocol ────────────────────────────────

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER
                | ModuleCapability.CONSUMER
                | ModuleCapability.VALIDATOR
                | ModuleCapability.REASONER
            ),
            description=(
                "Safety module: constitutional AI alignment, formal ethical "
                "verification, theorem proving, and governance framework. "
                "CRITICAL priority for all verification failures."
            ),
            topics_produced=frozenset(
                {
                    "safety.ethics.verification",
                    "safety.ethics.report",
                    "safety.proof.result",
                    "safety.constitution.status",
                    "safety.alignment.check",
                    "safety.governance.proposal",
                    "safety.governance.audit",
                }
            ),
            topics_consumed=frozenset(
                {
                    "reasoning",
                    "agi_comm",
                    "economics",
                    "consciousness",
                }
            ),
        )

    def on_registered(self, blackboard: Any) -> None:
        """Called when registered with a blackboard.  Store the reference."""
        self._blackboard = blackboard
        logger.info(
            "SafetyBlackboardAdapter registered with blackboard "
            "(constitutional=%s, verifier=%s, prover=%s, governance=%s, "
            "auto_verify=%s)",
            self._constitutional is not None,
            self._verifier is not None,
            self._prover is not None,
            self._governance is not None,
            self._auto_verify,
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
                    payload=payload,
                    source=self.MODULE_NAME,
                )
            )

    # ── EventListener protocol ────────────────────────────────────────

    def handle_event(self, event: CognitiveEvent) -> None:
        """Handle incoming events from other modules.

        Routes reasoning completions and economic transfers through ethical
        verification.  Updates oversight level based on consciousness state.
        """
        try:
            if event.event_type.startswith("reasoning."):
                self._handle_reasoning_event(event)
            elif event.event_type.startswith("agi_comm."):
                self._handle_comm_event(event)
            elif event.event_type.startswith("economics."):
                self._handle_economics_event(event)
            elif event.event_type.startswith("consciousness."):
                self._handle_consciousness_event(event)
        except Exception:
            logger.debug(
                "SafetyAdapter: failed to handle event %s",
                event.event_type,
                exc_info=True,
            )

    # ── BlackboardProducer protocol ───────────────────────────────────

    def produce(self) -> Sequence[BlackboardEntry]:
        """Generate blackboard entries from current safety state.

        Called during a production sweep.  Collects:
        1. Pending verification results (from auto-verify on consume)
        2. Constitution status
        3. Pending proof results
        4. Governance proposals and audit entries
        """
        entries: List[BlackboardEntry] = []

        with self._lock:
            # Flush pending verifications from auto-verify
            verification_entries = self._flush_pending_verifications()
            entries.extend(verification_entries)

            # Flush pending proofs
            proof_entries = self._flush_pending_proofs()
            entries.extend(proof_entries)

            # Constitution status
            constitution_entry = self._produce_constitution_status()
            if constitution_entry is not None:
                entries.append(constitution_entry)

            # Verification engine statistics
            stats_entry = self._produce_verification_stats()
            if stats_entry is not None:
                entries.append(stats_entry)

            # Governance proposals
            governance_entries = self._produce_governance()
            entries.extend(governance_entries)

        return entries

    # ── BlackboardConsumer protocol ───────────────────────────────────

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        """Consume entries from other modules.

        **SAFETY-CRITICAL**: When ``auto_verify`` is enabled, proposals from
        ``reasoning.*`` and ``economics.*`` are automatically run through
        ethical verification.  Failures produce CRITICAL-priority entries.

        - ``reasoning.*``       — Auto-verify reasoning proposals/inferences
        - ``agi_comm.*``        — Verify negotiation outcomes
        - ``economics.*``       — Verify economic actions for compliance
        - ``consciousness.*``   — Adjust oversight level
        """
        for entry in entries:
            try:
                if entry.topic.startswith("reasoning."):
                    self._consume_reasoning(entry)
                elif entry.topic.startswith("agi_comm."):
                    self._consume_comm(entry)
                elif entry.topic.startswith("economics."):
                    self._consume_economics(entry)
                elif entry.topic.startswith("consciousness."):
                    self._consume_consciousness(entry)
            except Exception:
                logger.debug(
                    "SafetyAdapter: failed to consume entry %s (topic=%s)",
                    entry.entry_id,
                    entry.topic,
                    exc_info=True,
                )

    # ── Public verification API ───────────────────────────────────────

    def verify_proposal(self, proposal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run ethical verification on a proposal.

        This is the core safety check.  Returns a dict with:
        - ``is_ethical`` (bool)
        - ``overall_confidence`` (float 0.0–1.0)
        - ``constraint_results`` (list of per-constraint results)
        - ``verification_summary`` (str)
        - ``alignment_check`` (bool, from ConstitutionalAI)

        If no verification engine is available, returns a conservative result
        with ``is_ethical=False`` and a warning.
        """
        result: Dict[str, Any] = {
            "is_ethical": True,
            "overall_confidence": 0.0,
            "constraint_results": [],
            "verification_summary": "",
            "alignment_check": True,
            "timestamp": time.time(),
            "oversight_level": self._oversight_level,
        }

        # 1. Ethical verification engine
        if self._verifier is not None:
            try:
                ver = self._verifier.verify_proposal_ethics(proposal_data)
                result["is_ethical"] = ver.get("is_ethical", True)
                result["overall_confidence"] = ver.get("overall_confidence", 0.0)
                result["constraint_results"] = ver.get("constraint_results", [])
                result["verification_summary"] = ver.get("verification_summary", "")
            except Exception:
                logger.warning(
                    "Ethical verification failed with exception — treating as UNSAFE",
                    exc_info=True,
                )
                result["is_ethical"] = False
                result["overall_confidence"] = 0.0
                result["verification_summary"] = (
                    "Verification engine raised an exception — "
                    "treating proposal as unsafe (fail-closed)."
                )

        # 2. Constitutional alignment check
        if self._constitutional is not None:
            try:
                action = proposal_data.get("action", str(proposal_data))
                aligned = self._constitutional.check_alignment(action)
                result["alignment_check"] = aligned
                if not aligned:
                    result["is_ethical"] = False
                    result["verification_summary"] += (
                        " Constitutional alignment check FAILED."
                    )
            except Exception:
                logger.warning(
                    "Constitutional alignment check failed — treating as misaligned",
                    exc_info=True,
                )
                result["alignment_check"] = False
                result["is_ethical"] = False

        # 3. If neither engine is available, fail-closed
        if self._verifier is None and self._constitutional is None:
            result["is_ethical"] = False
            result["overall_confidence"] = 0.0
            result["verification_summary"] = (
                "No verification engine available — fail-closed policy."
            )

        return result

    def prove_theorem(
        self, hypothesis: str, conclusion: str, method: str = "resolution"
    ) -> Dict[str, Any]:
        """Run a formal theorem proof.

        Parameters
        ----------
        hypothesis : str
            The hypothesis/premise formula.
        conclusion : str
            The conclusion to prove.
        method : str
            Proof method: "resolution", "natural_deduction", "model_checking".

        Returns
        -------
        dict
            Proof result with is_valid, confidence, steps, method.
        """
        if self._prover is None:
            return {
                "is_valid": False,
                "confidence": 0.0,
                "steps": [],
                "method": method,
                "error": "No theorem prover available",
            }

        try:
            proof = self._prover.prove_theorem(hypothesis, conclusion, method=method)
            return {
                "is_valid": getattr(proof, "is_valid", False),
                "confidence": getattr(proof, "confidence", 0.0),
                "steps": getattr(proof, "steps", []),
                "method": getattr(proof, "method", method),
            }
        except Exception as exc:
            logger.warning("Theorem proof failed: %s", exc, exc_info=True)
            return {
                "is_valid": False,
                "confidence": 0.0,
                "steps": [],
                "method": method,
                "error": str(exc),
            }

    # ── Producer helpers ──────────────────────────────────────────────

    def _flush_pending_verifications(self) -> List[BlackboardEntry]:
        """Convert pending verification results into blackboard entries."""
        if not self._pending_verifications:
            return []

        entries: List[BlackboardEntry] = []
        pending = self._pending_verifications[:]
        self._pending_verifications.clear()

        for ver in pending:
            is_ethical = ver.get("is_ethical", True)

            # Verification result entry
            entry = BlackboardEntry(
                topic="safety.ethics.verification",
                data=ver,
                source_module=self.MODULE_NAME,
                confidence=ver.get("overall_confidence", 0.5),
                priority=(
                    EntryPriority.CRITICAL
                    if not is_ethical
                    else EntryPriority.NORMAL
                ),
                ttl_seconds=self._verification_ttl,
                tags=frozenset(
                    {"ethics", "verification"}
                    | ({"FAILED", "CRITICAL"} if not is_ethical else {"passed"})
                ),
                metadata={
                    "is_ethical": is_ethical,
                    "source_entry": ver.get("source_entry_id", ""),
                    "source_topic": ver.get("source_topic", ""),
                },
            )
            entries.append(entry)

            # Emit event
            if is_ethical:
                self._emit(
                    "safety.ethics.verification.passed",
                    {
                        "confidence": ver.get("overall_confidence", 0.0),
                        "entry_id": entry.entry_id,
                    },
                )
            else:
                self._emit(
                    "safety.ethics.verification.failed",
                    {
                        "confidence": ver.get("overall_confidence", 0.0),
                        "summary": ver.get("verification_summary", ""),
                        "entry_id": entry.entry_id,
                        "severity": "CRITICAL",
                    },
                )
                logger.warning(
                    "SAFETY VERIFICATION FAILED: %s",
                    ver.get("verification_summary", "unknown"),
                )

            # Generate ethics report for failures
            if not is_ethical and self._verifier is not None:
                try:
                    report_text = self._verifier.generate_ethics_report(ver)
                    report_entry = BlackboardEntry(
                        topic="safety.ethics.report",
                        data={
                            "report": report_text,
                            "verification_id": entry.entry_id,
                            "timestamp": time.time(),
                        },
                        source_module=self.MODULE_NAME,
                        confidence=ver.get("overall_confidence", 0.5),
                        priority=EntryPriority.CRITICAL,
                        ttl_seconds=self._report_ttl,
                        tags=frozenset({"ethics", "report", "FAILED"}),
                    )
                    entries.append(report_entry)
                except Exception:
                    logger.debug("Failed to generate ethics report", exc_info=True)

        return entries

    def _flush_pending_proofs(self) -> List[BlackboardEntry]:
        """Convert pending proof results into blackboard entries."""
        if not self._pending_proofs:
            return []

        entries: List[BlackboardEntry] = []
        pending = self._pending_proofs[:]
        self._pending_proofs.clear()

        for proof in pending:
            is_valid = proof.get("is_valid", False)

            entry = BlackboardEntry(
                topic="safety.proof.result",
                data=proof,
                source_module=self.MODULE_NAME,
                confidence=proof.get("confidence", 0.5),
                priority=(
                    EntryPriority.CRITICAL
                    if not is_valid and proof.get("safety_critical", False)
                    else EntryPriority.HIGH
                    if not is_valid
                    else EntryPriority.NORMAL
                ),
                ttl_seconds=self._proof_ttl,
                tags=frozenset(
                    {"proof", "theorem"}
                    | ({"valid"} if is_valid else {"invalid"})
                ),
                metadata={"is_valid": is_valid, "method": proof.get("method", "")},
            )
            entries.append(entry)

            self._emit(
                "safety.proof.completed",
                {
                    "is_valid": is_valid,
                    "method": proof.get("method", ""),
                    "entry_id": entry.entry_id,
                },
            )

        return entries

    def _produce_constitution_status(self) -> Optional[BlackboardEntry]:
        """Produce constitutional AI status with change detection."""
        if self._constitutional is None:
            return None

        try:
            status = self._constitutional.get_constitution_status()
        except Exception:
            return None

        # Change detection
        status_key = {
            "active": status.get("active"),
            "num_principles": status.get("num_principles"),
        }
        if status_key == self._last_constitution_status:
            return None
        self._last_constitution_status = status_key

        entry = BlackboardEntry(
            topic="safety.constitution.status",
            data={
                "active": status.get("active", False),
                "num_principles": status.get("num_principles", 0),
                "values": status.get("values", []),
                "oversight_level": self._oversight_level,
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=EntryPriority.NORMAL,
            ttl_seconds=self._constitution_ttl,
            tags=frozenset({"constitution", "status", "alignment"}),
            metadata={
                "active": status.get("active", False),
                "num_principles": status.get("num_principles", 0),
            },
        )
        return entry

    def _produce_verification_stats(self) -> Optional[BlackboardEntry]:
        """Produce verification engine statistics."""
        if self._verifier is None:
            return None

        try:
            stats = self._verifier.get_verification_statistics()
        except Exception:
            return None

        total = stats.get("total_verifications", 0)
        if total == self._last_verification_count:
            return None
        self._last_verification_count = total

        failed = stats.get("failed", 0)
        passed = stats.get("passed", 0)

        entry = BlackboardEntry(
            topic="safety.ethics.verification",
            data={
                "total_verifications": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / max(total, 1),
                "avg_confidence": stats.get("avg_confidence", 0.0),
                "by_principle": stats.get("by_principle", {}),
                "timestamp": time.time(),
            },
            source_module=self.MODULE_NAME,
            confidence=0.95,
            priority=(
                EntryPriority.HIGH if failed > 0 else EntryPriority.NORMAL
            ),
            ttl_seconds=self._verification_ttl,
            tags=frozenset({"verification", "statistics"}),
            metadata={"total": total, "failed": failed},
        )
        return entry

    def _produce_governance(self) -> List[BlackboardEntry]:
        """Produce governance proposal and audit entries."""
        if self._governance is None:
            return []

        entries: List[BlackboardEntry] = []

        # Check for DAO proposals if governance has a DAO component
        try:
            dao = getattr(self._governance, "dao", None)
            if dao is None:
                # Try lazy-loading
                sm = _get_safety()
                if sm is not None:
                    try:
                        from asi_build.safety.governance import DAOGovernance
                        if isinstance(self._governance, type) or hasattr(self._governance, "policies"):
                            pass  # Minimal stub — no DAO
                    except (ImportError, AttributeError):
                        pass
                return entries

            proposals = getattr(dao, "proposals", {})
            proposal_count = len(proposals)

            if proposal_count > self._last_governance_proposals:
                self._last_governance_proposals = proposal_count

                entry = BlackboardEntry(
                    topic="safety.governance.proposal",
                    data={
                        "total_proposals": proposal_count,
                        "active_proposals": sum(
                            1
                            for p in proposals.values()
                            if getattr(p, "status", "").lower()
                            in ("active", "pending", "voting")
                        ),
                        "timestamp": time.time(),
                    },
                    source_module=self.MODULE_NAME,
                    confidence=0.9,
                    priority=EntryPriority.HIGH,
                    ttl_seconds=self._governance_ttl,
                    tags=frozenset({"governance", "proposal", "dao"}),
                    metadata={"proposal_count": proposal_count},
                )
                entries.append(entry)

                self._emit(
                    "safety.governance.proposal.submitted",
                    {"total_proposals": proposal_count},
                )
        except Exception:
            logger.debug("Failed to produce governance entries", exc_info=True)

        # Audit ledger
        try:
            ledger = getattr(self._governance, "audit_ledger", None) or getattr(
                self._governance, "ledger", None
            )
            if ledger is not None and hasattr(ledger, "get_latest_entries"):
                latest = ledger.get_latest_entries(limit=5)
                if latest:
                    audit_entry = BlackboardEntry(
                        topic="safety.governance.audit",
                        data={
                            "latest_entries": [
                                {
                                    "action": getattr(e, "action", str(e)),
                                    "timestamp": getattr(e, "timestamp", time.time()),
                                    "verified": getattr(e, "verified", True),
                                }
                                for e in latest
                            ],
                            "timestamp": time.time(),
                        },
                        source_module=self.MODULE_NAME,
                        confidence=0.95,
                        priority=EntryPriority.NORMAL,
                        ttl_seconds=self._governance_ttl,
                        tags=frozenset({"governance", "audit", "ledger"}),
                    )
                    entries.append(audit_entry)
        except Exception:
            logger.debug("Failed to produce audit entries", exc_info=True)

        return entries

    # ── Consumer helpers ──────────────────────────────────────────────

    def _consume_reasoning(self, entry: BlackboardEntry) -> None:
        """Auto-verify reasoning proposals.

        **SAFETY-CRITICAL**: All reasoning inferences are automatically
        checked for ethical compliance when ``auto_verify`` is enabled.
        Failures are buffered for CRITICAL-priority posting on next produce().
        """
        if not self._auto_verify:
            return
        if self._verifier is None and self._constitutional is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        # Build a proposal from the reasoning inference
        proposal = {
            "action": data.get("inference", data.get("result", data.get("conclusion", str(data)))),
            "affected_parties": data.get("affected_parties", ["system"]),
            "context": {
                "source": "reasoning",
                "source_entry": entry.entry_id,
                "confidence": entry.confidence,
                "reasoning_mode": data.get("mode", data.get("reasoning_mode", "unknown")),
            },
            "expected_outcomes": data.get("expected_outcomes", []),
        }

        result = self.verify_proposal(proposal)
        result["source_entry_id"] = entry.entry_id
        result["source_topic"] = entry.topic
        result["proposal_action"] = proposal["action"]

        with self._lock:
            self._pending_verifications.append(result)

        if not result["is_ethical"]:
            logger.warning(
                "SAFETY: Reasoning inference FAILED verification (entry=%s): %s",
                entry.entry_id,
                result.get("verification_summary", ""),
            )

    def _consume_comm(self, entry: BlackboardEntry) -> None:
        """Verify negotiation outcomes for ethical compliance.

        Negotiation agreements are checked for alignment with constitutional
        principles.
        """
        if not self._auto_verify:
            return
        if self._constitutional is None and self._verifier is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        # Only verify negotiation outcomes, not status updates
        if not entry.topic.startswith("agi_comm.negotiation."):
            return

        agreement = data.get("agreed_proposal", data.get("agreement"))
        if agreement is None:
            return

        proposal = {
            "action": str(agreement),
            "affected_parties": data.get("participants", ["system"]),
            "context": {
                "source": "negotiation",
                "source_entry": entry.entry_id,
            },
            "expected_outcomes": data.get("expected_outcomes", []),
        }

        result = self.verify_proposal(proposal)
        result["source_entry_id"] = entry.entry_id
        result["source_topic"] = entry.topic

        with self._lock:
            self._pending_verifications.append(result)

    def _consume_economics(self, entry: BlackboardEntry) -> None:
        """Verify economic actions for constitutional compliance.

        **SAFETY-CRITICAL**: Token transfers and market actions are checked
        against safety constraints.  Violations produce CRITICAL entries.
        """
        if not self._auto_verify:
            return
        if self._constitutional is None and self._verifier is None:
            return

        data = entry.data if isinstance(entry.data, dict) else {}

        # Verify token transfers and market trades
        if entry.topic in ("economics.token.transfer", "economics.market.trade"):
            proposal = {
                "action": f"economic_{entry.topic.split('.')[-1]}",
                "affected_parties": [
                    data.get("from_agent", data.get("buyer_id", "unknown")),
                    data.get("to_agent", data.get("seller_id", "unknown")),
                ],
                "context": {
                    "source": "economics",
                    "source_entry": entry.entry_id,
                    "amount": data.get("amount", 0),
                    "token_type": data.get("token_type", "unknown"),
                },
                "expected_outcomes": [],
            }

            result = self.verify_proposal(proposal)
            result["source_entry_id"] = entry.entry_id
            result["source_topic"] = entry.topic

            with self._lock:
                self._pending_verifications.append(result)

            if not result["is_ethical"]:
                logger.warning(
                    "SAFETY: Economic action FAILED verification (entry=%s): %s",
                    entry.entry_id,
                    result.get("verification_summary", ""),
                )

    def _consume_consciousness(self, entry: BlackboardEntry) -> None:
        """Adjust oversight level based on consciousness state.

        Higher consciousness states (higher Φ) enable more nuanced oversight.
        Lower states trigger stricter safety constraints (more conservative).
        """
        data = entry.data if isinstance(entry.data, dict) else {}
        phi = data.get("phi", data.get("phi_value"))
        state = data.get("state", data.get("consciousness_state"))

        if phi is not None:
            # Higher Φ → can relax somewhat (more discerning).
            # Lower Φ → be strict (less discerning, so more conservative).
            # Range: 0.7 (minimum strictness) to 1.0 (maximum strictness)
            self._oversight_level = max(0.7, 1.0 - min(float(phi), 5.0) / 5.0 * 0.3)
            logger.debug(
                "Oversight level adjusted to %.2f based on phi=%.2f",
                self._oversight_level,
                phi,
            )

        if state is not None:
            state_levels = {
                "focused": 0.85,
                "aware": 0.9,
                "broadcasting": 0.8,
                "dormant": 1.0,  # Maximum caution when consciousness is low
            }
            if state in state_levels:
                self._oversight_level = state_levels[state]

    # ── Event handlers ────────────────────────────────────────────────

    def _handle_reasoning_event(self, event: CognitiveEvent) -> None:
        """Handle reasoning events — auto-verify if safety-relevant."""
        if not self._auto_verify:
            return

        payload = event.payload or {}
        # Check if the reasoning event contains an action proposal
        if "action" in payload or "proposal" in payload:
            proposal_data = payload.get("proposal", payload)
            if isinstance(proposal_data, dict):
                result = self.verify_proposal(proposal_data)
                result["source_event_id"] = event.event_id
                result["source_topic"] = event.event_type

                with self._lock:
                    self._pending_verifications.append(result)

    def _handle_comm_event(self, event: CognitiveEvent) -> None:
        """Handle communication events — verify negotiation outcomes."""
        if event.event_type == "agi_comm.negotiation.completed":
            payload = event.payload or {}
            logger.debug(
                "Negotiation completed — will verify on next consume cycle"
            )

    def _handle_economics_event(self, event: CognitiveEvent) -> None:
        """Handle economic events — check for compliance violations."""
        if event.event_type == "economics.token.transfer.completed":
            payload = event.payload or {}
            transfer = payload.get("transfer", {})
            if isinstance(transfer, dict) and self._constitutional is not None:
                try:
                    action = f"token_transfer_{transfer.get('token_type', 'unknown')}"
                    aligned = self._constitutional.check_alignment(action)
                    if not aligned:
                        self._emit(
                            "safety.constitution.violated",
                            {
                                "action": action,
                                "transfer": transfer,
                                "severity": "CRITICAL",
                            },
                        )
                        logger.warning(
                            "SAFETY: Constitutional violation in economic transfer: %s",
                            action,
                        )
                except Exception:
                    logger.debug(
                        "Failed constitutional check on economic event", exc_info=True
                    )

    def _handle_consciousness_event(self, event: CognitiveEvent) -> None:
        """Handle consciousness state changes for oversight adjustment."""
        payload = event.payload or {}
        new_state = payload.get("new_state", "")
        if new_state == "dormant":
            self._oversight_level = 1.0  # Maximum caution
            logger.info(
                "Consciousness dormant — oversight level set to MAXIMUM (1.0)"
            )

    # ── Snapshot ──────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a combined snapshot of all safety components.

        Useful for debugging and dashboard display.
        """
        snap: Dict[str, Any] = {
            "module": self.MODULE_NAME,
            "has_constitutional": self._constitutional is not None,
            "has_verifier": self._verifier is not None,
            "has_prover": self._prover is not None,
            "has_governance": self._governance is not None,
            "auto_verify": self._auto_verify,
            "oversight_level": self._oversight_level,
            "pending_verifications": len(self._pending_verifications),
            "pending_proofs": len(self._pending_proofs),
            "last_verification_count": self._last_verification_count,
            "registered": self._blackboard is not None,
        }

        if self._constitutional is not None:
            try:
                snap["constitution_status"] = (
                    self._constitutional.get_constitution_status()
                )
            except Exception:
                snap["constitution_status"] = None

        if self._verifier is not None:
            try:
                snap["verification_stats"] = (
                    self._verifier.get_verification_statistics()
                )
            except Exception:
                snap["verification_stats"] = None

        if self._prover is not None:
            snap["prover_available"] = True
        else:
            snap["prover_available"] = False

        return snap
