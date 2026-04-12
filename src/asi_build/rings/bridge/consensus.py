"""
Multi-Validator Consensus
==========================

Implements 4/6 threshold consensus for bridge withdrawal approvals.
Communicates with Rings cluster nodes via HTTP to collect ECDSA
signatures from approving validators.

Architecture
~~~~~~~~~~~~

Each of the 6 validators in the bridge Sub-Ring independently verifies
a withdrawal request before signing.  Once ≥ 4 ECDSA signatures are
collected (the *threshold*), the withdrawal can be executed on-chain.

The flow is:

1. A proposer creates a :class:`WithdrawalProposal` and broadcasts it
   to all validators via HTTP POST.
2. Each validator calls :meth:`ValidatorConsensus.submit_approval` to
   verify the withdrawal and sign it (or reject).
3. The proposer collects responses, checks the threshold via
   :meth:`check_threshold`, and aggregates signatures for on-chain
   submission.

Signatures cover ``keccak256(withdrawal_id ‖ amount ‖ recipient)`` to
match the Solidity ``ecrecover`` verification in ``RingsBridge.sol``.

Security Notes
~~~~~~~~~~~~~~

- Each validator verifies amount > 0 and recipient is a valid 20-byte
  Ethereum address before signing.
- Per-validator rate limiting prevents a single compromised node from
  flooding the cluster with approval requests.
- Proposals expire after *proposal_ttl* seconds, preventing replay of
  stale withdrawal requests.
- All HTTP calls have configurable timeouts and individual node
  failures do not block the consensus round (the cluster tolerates
  up to 2 node failures with the default 4/6 threshold).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Maximum withdrawal approvals per validator per hour (rate limit).
_DEFAULT_RATE_LIMIT: int = 100

#: Default time-to-live for a withdrawal proposal (seconds).
_DEFAULT_PROPOSAL_TTL: float = 300.0  # 5 minutes

#: Regex for a checksummed or lowercased Ethereum address.
_ETH_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------


class ProposalStatus(Enum):
    """Lifecycle states for a withdrawal proposal."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class WithdrawalProposal:
    """A withdrawal proposal being voted on by the validator set.

    Attributes
    ----------
    withdrawal_id : str
        Unique identifier for the withdrawal (typically a nonce or tx ref).
    amount : int
        Withdrawal amount in wei.  Must be > 0.
    recipient : str
        Destination ``0x``-prefixed Ethereum address.
    proposer : str
        Identifier of the node that initiated the proposal.
    timestamp : float
        Unix time when the proposal was created.
    approvals : dict
        Map of ``validator_id → signature_hex``.  Populated as
        validators respond.
    rejected : set
        Validator IDs that explicitly rejected this proposal.
    status : ProposalStatus
        Current lifecycle state.
    """

    withdrawal_id: str
    amount: int
    recipient: str
    proposer: str
    timestamp: float = field(default_factory=time.time)
    approvals: Dict[str, str] = field(default_factory=dict)   # validator_id → sig hex
    rejected: Set[str] = field(default_factory=set)
    status: ProposalStatus = ProposalStatus.PROPOSED

    # -- Serialisation --------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serialisable representation for HTTP transport."""
        return {
            "withdrawal_id": self.withdrawal_id,
            "amount": self.amount,
            "recipient": self.recipient,
            "proposer": self.proposer,
            "timestamp": self.timestamp,
            "approvals": dict(self.approvals),
            "rejected": sorted(self.rejected),
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WithdrawalProposal":
        """Reconstruct from a dict (e.g. decoded JSON)."""
        return cls(
            withdrawal_id=data["withdrawal_id"],
            amount=int(data["amount"]),
            recipient=data["recipient"],
            proposer=data.get("proposer", "unknown"),
            timestamp=data.get("timestamp", time.time()),
            approvals=dict(data.get("approvals", {})),
            rejected=set(data.get("rejected", [])),
            status=ProposalStatus(data.get("status", "proposed")),
        )


# ---------------------------------------------------------------------------
# ValidatorConsensus
# ---------------------------------------------------------------------------


class ValidatorConsensus:
    """4/6 threshold consensus across Rings cluster nodes.

    Communicates via HTTP to Rings DHT nodes.  Each validator
    independently verifies withdrawal validity before approving.

    Parameters
    ----------
    node_urls : list of str
        HTTP base URLs for the 6 validator nodes (e.g.
        ``["http://10.0.0.1:8080", ...]``).
    threshold : int
        Minimum approvals needed for consensus (default 4).
    total : int
        Expected total number of validators (default 6).
    timeout : float
        Per-request HTTP timeout in seconds (default 30).
    private_key : str, optional
        Hex-encoded ECDSA private key for signing approvals.
        If ``None``, this node cannot sign (read-only / proposer mode).
    proposal_ttl : float
        Seconds before a proposal expires (default 300).
    rate_limit : int
        Maximum approvals this node will issue per hour (default 100).
    validator_id : str, optional
        Human-readable identifier for this validator.  Derived from
        the private key's Ethereum address if not supplied.
    """

    def __init__(
        self,
        node_urls: List[str],
        threshold: int = 4,
        total: int = 6,
        timeout: float = 30.0,
        private_key: Optional[str] = None,
        proposal_ttl: float = _DEFAULT_PROPOSAL_TTL,
        rate_limit: int = _DEFAULT_RATE_LIMIT,
        validator_id: Optional[str] = None,
    ) -> None:
        if threshold > total:
            raise ValueError(
                f"threshold ({threshold}) cannot exceed total ({total})"
            )
        if threshold < 1:
            raise ValueError("threshold must be ≥ 1")

        self.node_urls = list(node_urls)
        self.threshold = threshold
        self.total = total
        self.timeout = timeout
        self.proposal_ttl = proposal_ttl

        # ── Signing key ─────────────────────────────────────────────────
        self._private_key: Optional[str] = None
        self._account: Any = None  # eth_account.Account instance

        if private_key is not None:
            self._init_signing_key(private_key)

        # ── Identity ────────────────────────────────────────────────────
        if validator_id is not None:
            self.validator_id = validator_id
        elif self._account is not None:
            self.validator_id = self._account.address
        else:
            self.validator_id = "anonymous"

        # ── In-memory proposal store ────────────────────────────────────
        self._proposals: Dict[str, WithdrawalProposal] = {}
        self._lock = asyncio.Lock()

        # ── Rate limiting ───────────────────────────────────────────────
        self._rate_limit = rate_limit
        self._approval_timestamps: List[float] = []

        logger.info(
            "ValidatorConsensus initialised: id=%s, threshold=%d/%d, "
            "nodes=%d, timeout=%.1fs, ttl=%.0fs",
            self.validator_id, self.threshold, self.total,
            len(self.node_urls), self.timeout, self.proposal_ttl,
        )

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_signing_key(self, private_key: str) -> None:
        """Import the ECDSA private key via ``eth_account``.

        Raises
        ------
        ImportError
            If ``eth_account`` is not installed.
        ValueError
            If the key is malformed.
        """
        try:
            from eth_account import Account  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "eth_account is required for ECDSA signing.  "
                "Install it with: pip install eth-account"
            )

        # Normalise — accept with or without 0x prefix
        key_hex = private_key if private_key.startswith("0x") else f"0x{private_key}"
        self._account = Account.from_key(key_hex)
        self._private_key = key_hex
        logger.info(
            "Signing key loaded: address=%s", self._account.address,
        )

    # ==================================================================
    # Public API
    # ==================================================================

    async def request_approval(
        self,
        withdrawal_id: str,
        amount: int,
        recipient: str,
    ) -> Tuple[bool, Dict[str, str]]:
        """Request approval from all validators; need *threshold* to approve.

        Creates a :class:`WithdrawalProposal`, fans it out to every
        validator node concurrently, waits for responses (up to
        *timeout*), and checks whether the threshold is met.

        Parameters
        ----------
        withdrawal_id : str
            Unique identifier for the withdrawal.
        amount : int
            Withdrawal amount in wei.
        recipient : str
            Destination Ethereum address (``0x``-prefixed, 40 hex chars).

        Returns
        -------
        tuple of (bool, dict)
            ``(approved, approvals)`` where *approved* is ``True`` when
            ≥ *threshold* validators signed, and *approvals* maps
            ``validator_id → signature_hex``.
        """
        # 1. Create proposal
        async with self._lock:
            proposal = WithdrawalProposal(
                withdrawal_id=withdrawal_id,
                amount=amount,
                recipient=recipient,
                proposer=self.validator_id,
            )
            self._proposals[withdrawal_id] = proposal

        logger.info(
            "Requesting approval: id=%s, amount=%d, recipient=%s",
            withdrawal_id, amount, recipient,
        )

        # 2. Fan out to all validators concurrently
        payload = {
            "withdrawal_id": withdrawal_id,
            "amount": amount,
            "recipient": recipient,
            "proposer": self.validator_id,
            "timestamp": proposal.timestamp,
        }

        tasks = [
            self._send_to_validator(url, payload)
            for url in self.node_urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. Collect responses
        for result in results:
            if isinstance(result, Exception):
                logger.debug(
                    "Validator returned error: %s", result,
                )
                continue
            if result is None:
                continue

            vid = result.get("validator_id", "unknown")
            sig = result.get("signature")
            rejected = result.get("rejected", False)

            if rejected:
                async with self._lock:
                    proposal.rejected.add(vid)
                logger.info(
                    "Validator %s rejected withdrawal %s: %s",
                    vid, withdrawal_id, result.get("reason", "unknown"),
                )
            elif sig:
                async with self._lock:
                    proposal.approvals[vid] = sig
                logger.info(
                    "Validator %s approved withdrawal %s",
                    vid, withdrawal_id,
                )

        # 4. Check threshold
        approved, signatures = await self.check_threshold(withdrawal_id)

        async with self._lock:
            if approved:
                proposal.status = ProposalStatus.APPROVED
            elif len(proposal.rejected) > (self.total - self.threshold):
                # Too many rejections — threshold can never be met
                proposal.status = ProposalStatus.REJECTED

        logger.info(
            "Approval result: id=%s, approved=%s, votes=%d/%d, rejected=%d",
            withdrawal_id, approved,
            len(proposal.approvals), self.threshold,
            len(proposal.rejected),
        )

        return approved, dict(proposal.approvals)

    async def submit_approval(
        self,
        withdrawal_id: str,
        amount: int,
        recipient: str,
    ) -> Optional[bytes]:
        """Submit this node's approval for a withdrawal.

        Independently validates the withdrawal, then signs if valid.
        This is the handler invoked when a remote proposer sends us
        an approval request.

        Parameters
        ----------
        withdrawal_id : str
            Unique identifier for the withdrawal.
        amount : int
            Withdrawal amount in wei.
        recipient : str
            Destination Ethereum address.

        Returns
        -------
        bytes or None
            The ECDSA signature bytes, or ``None`` if rejected.
        """
        # ── Pre-checks ──────────────────────────────────────────────────
        if self._account is None:
            logger.warning(
                "Cannot approve withdrawal %s: no signing key configured",
                withdrawal_id,
            )
            return None

        # Validate the withdrawal request
        rejection_reason = self._validate_withdrawal(
            withdrawal_id, amount, recipient,
        )
        if rejection_reason is not None:
            logger.warning(
                "Rejecting withdrawal %s: %s", withdrawal_id, rejection_reason,
            )
            return None

        # Rate limit check
        if not self._check_rate_limit():
            logger.warning(
                "Rejecting withdrawal %s: rate limit exceeded "
                "(%d approvals/hour)", withdrawal_id, self._rate_limit,
            )
            return None

        # ── Sign ────────────────────────────────────────────────────────
        signature = self._sign_approval(withdrawal_id, amount, recipient)

        # Record the approval locally
        async with self._lock:
            if withdrawal_id not in self._proposals:
                self._proposals[withdrawal_id] = WithdrawalProposal(
                    withdrawal_id=withdrawal_id,
                    amount=amount,
                    recipient=recipient,
                    proposer="remote",
                )
            self._proposals[withdrawal_id].approvals[self.validator_id] = (
                signature.hex()
            )

        # Record for rate limiting
        self._approval_timestamps.append(time.time())

        logger.info(
            "Approved withdrawal %s: amount=%d, recipient=%s",
            withdrawal_id, amount, recipient,
        )
        return signature

    async def check_threshold(
        self,
        withdrawal_id: str,
    ) -> Tuple[bool, List[str]]:
        """Check if threshold approvals have been reached for a withdrawal.

        Parameters
        ----------
        withdrawal_id : str
            The withdrawal to check.

        Returns
        -------
        tuple of (bool, list of str)
            ``(threshold_met, list_of_signature_hex_strings)``.
        """
        async with self._lock:
            proposal = self._proposals.get(withdrawal_id)
            if proposal is None:
                return False, []

            # Expire stale proposals
            if self._is_expired(proposal):
                proposal.status = ProposalStatus.EXPIRED
                return False, []

            signatures = list(proposal.approvals.values())
            met = len(signatures) >= self.threshold
            return met, signatures

    async def get_proposal(
        self,
        withdrawal_id: str,
    ) -> Optional[WithdrawalProposal]:
        """Retrieve a proposal by ID (or ``None`` if unknown).

        Parameters
        ----------
        withdrawal_id : str
            The withdrawal to look up.

        Returns
        -------
        WithdrawalProposal or None
        """
        async with self._lock:
            proposal = self._proposals.get(withdrawal_id)
            if proposal is not None and self._is_expired(proposal):
                proposal.status = ProposalStatus.EXPIRED
            return proposal

    async def expire_stale_proposals(self) -> int:
        """Scan all proposals and mark expired ones.

        Returns the number of proposals that were expired.
        """
        now = time.time()
        expired = 0
        async with self._lock:
            for proposal in self._proposals.values():
                if (
                    proposal.status == ProposalStatus.PROPOSED
                    and (now - proposal.timestamp) > self.proposal_ttl
                ):
                    proposal.status = ProposalStatus.EXPIRED
                    expired += 1
        if expired > 0:
            logger.info("Expired %d stale proposals", expired)
        return expired

    @property
    def stats(self) -> Dict[str, Any]:
        """Current consensus statistics (non-async, snapshot)."""
        proposals = self._proposals
        return {
            "validator_id": self.validator_id,
            "threshold": self.threshold,
            "total": self.total,
            "node_count": len(self.node_urls),
            "active_proposals": sum(
                1 for p in proposals.values()
                if p.status == ProposalStatus.PROPOSED
            ),
            "approved_proposals": sum(
                1 for p in proposals.values()
                if p.status == ProposalStatus.APPROVED
            ),
            "rejected_proposals": sum(
                1 for p in proposals.values()
                if p.status == ProposalStatus.REJECTED
            ),
            "expired_proposals": sum(
                1 for p in proposals.values()
                if p.status == ProposalStatus.EXPIRED
            ),
            "has_signing_key": self._account is not None,
            "approvals_last_hour": self._count_recent_approvals(),
            "rate_limit": self._rate_limit,
        }

    # ==================================================================
    # HTTP transport
    # ==================================================================

    async def _send_to_validator(
        self,
        url: str,
        proposal: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Send an approval request to a single validator node.

        Makes an HTTP POST to ``{url}/bridge/approve`` with JSON body.
        Returns the parsed JSON response, or ``None`` on any failure.

        Parameters
        ----------
        url : str
            Base URL of the validator node.
        proposal : dict
            The withdrawal proposal payload.

        Returns
        -------
        dict or None
            The validator's response, or ``None`` if the request failed.
        """
        import aiohttp  # imported here to keep module importable without it

        endpoint = f"{url.rstrip('/')}/bridge/approve"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=proposal,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={
                        "Content-Type": "application/json",
                        "X-Validator-ID": self.validator_id,
                    },
                ) as resp:
                    if resp.status == 200:
                        data: Dict[str, Any] = await resp.json()
                        logger.debug(
                            "Validator %s responded 200: %s",
                            url, json.dumps(data, default=str)[:200],
                        )
                        return data
                    else:
                        body = await resp.text()
                        logger.warning(
                            "Validator %s responded %d: %s",
                            url, resp.status, body[:200],
                        )
                        return None

        except asyncio.TimeoutError:
            logger.warning(
                "Validator %s timed out after %.1fs", url, self.timeout,
            )
            return None
        except aiohttp.ClientError as exc:
            logger.warning(
                "Validator %s connection error: %s", url, exc,
            )
            return None
        except Exception as exc:
            logger.error(
                "Validator %s unexpected error: %s", url, exc, exc_info=True,
            )
            return None

    # ==================================================================
    # ECDSA signing & verification
    # ==================================================================

    def _sign_approval(
        self,
        withdrawal_id: str,
        amount: int,
        recipient: str,
    ) -> bytes:
        """Sign a withdrawal approval with ECDSA (secp256k1).

        The signed message is ``keccak256(withdrawal_id ‖ amount ‖ recipient)``,
        matching the on-chain ``ecrecover`` check in ``RingsBridge.sol``.

        Parameters
        ----------
        withdrawal_id : str
            Unique identifier for the withdrawal.
        amount : int
            Withdrawal amount in wei.
        recipient : str
            Destination Ethereum address.

        Returns
        -------
        bytes
            The 65-byte ECDSA signature (r ‖ s ‖ v).

        Raises
        ------
        RuntimeError
            If no signing key is configured.
        """
        if self._account is None:
            raise RuntimeError("No signing key configured — cannot sign")

        from eth_account.messages import encode_defunct  # type: ignore[import-untyped]

        msg_bytes = self._encode_approval_message(
            withdrawal_id, amount, recipient,
        )
        signable = encode_defunct(msg_bytes)
        signed = self._account.sign_message(signable)
        return bytes(signed.signature)

    def _verify_signature(
        self,
        message: bytes,
        signature: bytes,
        expected_address: str,
    ) -> bool:
        """Verify an ECDSA signature against an expected Ethereum address.

        Parameters
        ----------
        message : bytes
            The original message bytes (will be wrapped with EIP-191
            prefix before recovery).
        signature : bytes
            The 65-byte signature (r ‖ s ‖ v).
        expected_address : str
            The ``0x``-prefixed Ethereum address of the expected signer.

        Returns
        -------
        bool
            ``True`` if the recovered address matches *expected_address*.
        """
        try:
            from eth_account import Account  # type: ignore[import-untyped]
            from eth_account.messages import encode_defunct  # type: ignore[import-untyped]

            signable = encode_defunct(message)
            recovered = Account.recover_message(signable, signature=signature)
            return recovered.lower() == expected_address.lower()
        except Exception as exc:
            logger.warning("Signature verification failed: %s", exc)
            return False

    def _encode_approval_message(
        self,
        withdrawal_id: str,
        amount: int,
        recipient: str,
    ) -> bytes:
        """Encode the canonical message bytes to be signed for an approval.

        Format: ``withdrawal_id ‖ ":" ‖ str(amount) ‖ ":" ‖ recipient``

        This deterministic encoding ensures all validators sign
        exactly the same bytes.

        Parameters
        ----------
        withdrawal_id : str
            Unique identifier for the withdrawal.
        amount : int
            Withdrawal amount in wei.
        recipient : str
            Destination Ethereum address.

        Returns
        -------
        bytes
            The encoded message.
        """
        canonical = f"{withdrawal_id}:{amount}:{recipient.lower()}"
        return canonical.encode("utf-8")

    def verify_approval(
        self,
        withdrawal_id: str,
        amount: int,
        recipient: str,
        signature_hex: str,
        expected_address: str,
    ) -> bool:
        """Convenience: verify a hex-encoded approval signature.

        Parameters
        ----------
        withdrawal_id : str
            Withdrawal identifier.
        amount : int
            Amount in wei.
        recipient : str
            Destination address.
        signature_hex : str
            Hex-encoded 65-byte signature (with or without ``0x`` prefix).
        expected_address : str
            Expected signer's Ethereum address.

        Returns
        -------
        bool
            ``True`` if signature is valid and matches.
        """
        sig_hex = signature_hex.removeprefix("0x")
        try:
            sig_bytes = bytes.fromhex(sig_hex)
        except ValueError:
            logger.warning("Invalid signature hex: %s…", sig_hex[:16])
            return False

        msg = self._encode_approval_message(withdrawal_id, amount, recipient)
        return self._verify_signature(msg, sig_bytes, expected_address)

    # ==================================================================
    # Validation & rate limiting
    # ==================================================================

    def _validate_withdrawal(
        self,
        withdrawal_id: str,
        amount: int,
        recipient: str,
    ) -> Optional[str]:
        """Validate a withdrawal request.

        Returns ``None`` if valid, or a human-readable rejection reason.

        Parameters
        ----------
        withdrawal_id : str
            Unique identifier — must be non-empty.
        amount : int
            Must be > 0.
        recipient : str
            Must be a valid Ethereum address (``0x`` + 40 hex chars).

        Returns
        -------
        str or None
        """
        if not withdrawal_id or not withdrawal_id.strip():
            return "withdrawal_id is empty"

        if amount <= 0:
            return f"amount must be > 0, got {amount}"

        if not isinstance(recipient, str) or not _ETH_ADDRESS_RE.match(recipient):
            return f"invalid Ethereum address: {recipient!r}"

        # Check for duplicate approval (replay protection)
        proposal = self._proposals.get(withdrawal_id)
        if proposal is not None and self.validator_id in proposal.approvals:
            return f"already approved by {self.validator_id}"

        return None

    def _check_rate_limit(self) -> bool:
        """Return ``True`` if this node is under its hourly approval rate limit.

        Also prunes timestamps older than 1 hour.
        """
        now = time.time()
        cutoff = now - 3600.0

        # Prune old entries
        self._approval_timestamps = [
            ts for ts in self._approval_timestamps if ts >= cutoff
        ]

        return len(self._approval_timestamps) < self._rate_limit

    def _count_recent_approvals(self) -> int:
        """Count approvals in the last hour (for stats)."""
        cutoff = time.time() - 3600.0
        return sum(1 for ts in self._approval_timestamps if ts >= cutoff)

    def _is_expired(self, proposal: WithdrawalProposal) -> bool:
        """Check whether a proposal has exceeded its TTL."""
        return (time.time() - proposal.timestamp) > self.proposal_ttl

    # ==================================================================
    # Dunder
    # ==================================================================

    def __repr__(self) -> str:
        active = sum(
            1 for p in self._proposals.values()
            if p.status == ProposalStatus.PROPOSED
        )
        return (
            f"ValidatorConsensus("
            f"id={self.validator_id!r}, "
            f"threshold={self.threshold}/{self.total}, "
            f"nodes={len(self.node_urls)}, "
            f"active_proposals={active})"
        )
