"""
Bridge Consensus Tests
=======================

22 tests covering:
- WithdrawalProposal (4): creation, to_dict/from_dict, status, round-trip
- ProposalStatus (1): enum values
- ValidatorConsensus.__init__ (3): threshold validation, identity, defaults
- _validate_withdrawal (4): valid/invalid amount, address, empty ID, replay
- _encode_approval_message (2): deterministic encoding, canonical lowercase
- submit_approval (2): happy-path with mock signing, rejection when invalid
- request_approval (2): fan-out + threshold, insufficient approvals
- check_threshold (2): met and not-met cases
- _check_rate_limit (1): sliding window
- expire_stale_proposals (1): TTL expiration

All eth_account / aiohttp calls are mocked — no network or crypto deps.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asi_build.rings.bridge.consensus import (
    ProposalStatus,
    ValidatorConsensus,
    WithdrawalProposal,
)


# ===========================================================================
# ProposalStatus Tests (1)
# ===========================================================================


class TestProposalStatus:
    """Tests for the ProposalStatus enum."""

    def test_all_enum_values(self):
        """All four lifecycle states should be defined."""
        assert ProposalStatus.PROPOSED.value == "proposed"
        assert ProposalStatus.APPROVED.value == "approved"
        assert ProposalStatus.REJECTED.value == "rejected"
        assert ProposalStatus.EXPIRED.value == "expired"


# ===========================================================================
# WithdrawalProposal Tests (4)
# ===========================================================================


class TestWithdrawalProposal:
    """Tests for the WithdrawalProposal dataclass."""

    def test_creation_with_defaults(self):
        """Proposal should have sensible defaults for approvals/rejected/status."""
        p = WithdrawalProposal(
            withdrawal_id="wd-001",
            amount=1000,
            recipient="0x" + "ab" * 20,
            proposer="validator-1",
        )
        assert p.withdrawal_id == "wd-001"
        assert p.amount == 1000
        assert p.status == ProposalStatus.PROPOSED
        assert p.approvals == {}
        assert p.rejected == set()
        assert p.timestamp > 0

    def test_to_dict_serialization(self):
        """to_dict should produce a JSON-serialisable dict."""
        p = WithdrawalProposal(
            withdrawal_id="wd-002",
            amount=5000,
            recipient="0xDeaDbEeF" + "00" * 16,
            proposer="v1",
            timestamp=1700000000.0,
            approvals={"v1": "0xsig1"},
            rejected={"v2"},
        )
        d = p.to_dict()
        assert d["withdrawal_id"] == "wd-002"
        assert d["amount"] == 5000
        assert d["status"] == "proposed"
        assert d["approvals"] == {"v1": "0xsig1"}
        assert d["rejected"] == ["v2"]  # sorted list

    def test_from_dict_deserialization(self):
        """from_dict should reconstruct a proposal from a dict."""
        data = {
            "withdrawal_id": "wd-003",
            "amount": "7000",  # string — should be cast to int
            "recipient": "0x" + "ff" * 20,
            "proposer": "v2",
            "timestamp": 1700000100.0,
            "approvals": {"v1": "sig1", "v3": "sig3"},
            "rejected": ["v4"],
            "status": "approved",
        }
        p = WithdrawalProposal.from_dict(data)
        assert p.amount == 7000
        assert p.status == ProposalStatus.APPROVED
        assert p.approvals == {"v1": "sig1", "v3": "sig3"}
        assert p.rejected == {"v4"}

    def test_round_trip(self):
        """to_dict → from_dict should be lossless."""
        orig = WithdrawalProposal(
            withdrawal_id="rt-001",
            amount=42,
            recipient="0x" + "ab" * 20,
            proposer="me",
            timestamp=1234567890.0,
        )
        reconstructed = WithdrawalProposal.from_dict(orig.to_dict())
        assert reconstructed.withdrawal_id == orig.withdrawal_id
        assert reconstructed.amount == orig.amount
        assert reconstructed.recipient == orig.recipient
        assert reconstructed.proposer == orig.proposer
        assert reconstructed.timestamp == orig.timestamp
        assert reconstructed.status == orig.status


# ===========================================================================
# ValidatorConsensus.__init__ Tests (3)
# ===========================================================================


class TestValidatorConsensusInit:
    """Tests for ValidatorConsensus initialisation and validation."""

    def test_threshold_exceeds_total_raises(self):
        """threshold > total should raise ValueError."""
        with pytest.raises(ValueError, match="threshold.*cannot exceed"):
            ValidatorConsensus(node_urls=[], threshold=7, total=6)

    def test_threshold_zero_raises(self):
        """threshold < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="threshold must be"):
            ValidatorConsensus(node_urls=[], threshold=0, total=6)

    def test_default_identity_anonymous(self):
        """Without a private key or explicit ID, validator_id should be 'anonymous'."""
        vc = ValidatorConsensus(node_urls=["http://n1:8080"], threshold=1, total=1)
        assert vc.validator_id == "anonymous"
        assert vc.threshold == 1
        assert vc.total == 1
        assert len(vc.node_urls) == 1

    def test_explicit_validator_id(self):
        """An explicit validator_id should be used."""
        vc = ValidatorConsensus(
            node_urls=[], threshold=1, total=1, validator_id="my-node"
        )
        assert vc.validator_id == "my-node"


# ===========================================================================
# _validate_withdrawal Tests (4)
# ===========================================================================


class TestValidateWithdrawal:
    """Tests for withdrawal validation logic."""

    def setup_method(self):
        self.vc = ValidatorConsensus(
            node_urls=[], threshold=1, total=1, validator_id="test-val"
        )
        self.valid_addr = "0x" + "aB" * 20

    def test_valid_withdrawal(self):
        """A valid withdrawal should return None (no rejection)."""
        reason = self.vc._validate_withdrawal("wd-ok", 1000, self.valid_addr)
        assert reason is None

    def test_zero_amount_rejected(self):
        """Amount <= 0 should be rejected."""
        reason = self.vc._validate_withdrawal("wd-zero", 0, self.valid_addr)
        assert reason is not None
        assert "amount" in reason

    def test_negative_amount_rejected(self):
        """Negative amount should be rejected."""
        reason = self.vc._validate_withdrawal("wd-neg", -100, self.valid_addr)
        assert reason is not None
        assert "amount" in reason

    def test_invalid_address_rejected(self):
        """Non-Ethereum address should be rejected."""
        reason = self.vc._validate_withdrawal("wd-addr", 1000, "not-an-address")
        assert reason is not None
        assert "address" in reason.lower()

    def test_empty_id_rejected(self):
        """Empty withdrawal_id should be rejected."""
        reason = self.vc._validate_withdrawal("", 1000, self.valid_addr)
        assert reason is not None
        assert "empty" in reason.lower()

    def test_replay_protection(self):
        """Already-approved withdrawal should be rejected."""
        # Simulate a prior approval
        self.vc._proposals["wd-replay"] = WithdrawalProposal(
            withdrawal_id="wd-replay",
            amount=100,
            recipient=self.valid_addr,
            proposer="remote",
        )
        self.vc._proposals["wd-replay"].approvals["test-val"] = "0xsig"

        reason = self.vc._validate_withdrawal("wd-replay", 100, self.valid_addr)
        assert reason is not None
        assert "already approved" in reason.lower()


# ===========================================================================
# _encode_approval_message Tests (2)
# ===========================================================================


class TestEncodeApprovalMessage:
    """Tests for canonical message encoding."""

    def setup_method(self):
        self.vc = ValidatorConsensus(node_urls=[], threshold=1, total=1)

    def test_deterministic_encoding(self):
        """Same inputs should always produce the same bytes."""
        addr = "0x" + "AB" * 20
        msg1 = self.vc._encode_approval_message("wd-1", 1000, addr)
        msg2 = self.vc._encode_approval_message("wd-1", 1000, addr)
        assert msg1 == msg2

    def test_canonical_lowercase(self):
        """Recipient address should be lowercased in the encoding."""
        addr_upper = "0x" + "AB" * 20
        addr_lower = "0x" + "ab" * 20
        msg_upper = self.vc._encode_approval_message("wd-1", 1000, addr_upper)
        msg_lower = self.vc._encode_approval_message("wd-1", 1000, addr_lower)
        assert msg_upper == msg_lower
        # Verify it contains lowercase
        assert addr_lower.encode("utf-8") in msg_upper


# ===========================================================================
# submit_approval Tests (2)
# ===========================================================================


class TestSubmitApproval:
    """Tests for the submit_approval method (ECDSA signing mocked)."""

    def _make_consensus_with_mock_account(self):
        """Create a ValidatorConsensus with a mocked signing key."""
        vc = ValidatorConsensus(
            node_urls=[], threshold=1, total=1, validator_id="mock-signer"
        )
        # Mock the account and signing
        mock_account = MagicMock()
        mock_account.address = "0xMockAddress"
        mock_signed = MagicMock()
        mock_signed.signature = b"\xaa" * 65
        mock_account.sign_message.return_value = mock_signed
        vc._account = mock_account
        vc._private_key = "0xfakekey"
        return vc

    @pytest.mark.asyncio
    async def test_submit_approval_happy_path(self):
        """submit_approval should return signature bytes when valid."""
        vc = self._make_consensus_with_mock_account()
        addr = "0x" + "ab" * 20

        with patch(
            "asi_build.rings.bridge.consensus.encode_defunct",
            create=True,
        ):
            # Mock encode_defunct at the point of import inside _sign_approval
            with patch.dict(
                "sys.modules",
                {
                    "eth_account": MagicMock(),
                    "eth_account.messages": MagicMock(
                        encode_defunct=MagicMock(return_value="signable-msg")
                    ),
                },
            ):
                sig = await vc.submit_approval("wd-happy", 1000, addr)

        assert sig is not None
        assert isinstance(sig, bytes)
        assert len(sig) == 65

    @pytest.mark.asyncio
    async def test_submit_approval_no_key_returns_none(self):
        """submit_approval should return None when no signing key is configured."""
        vc = ValidatorConsensus(
            node_urls=[], threshold=1, total=1, validator_id="no-key"
        )
        addr = "0x" + "ab" * 20
        sig = await vc.submit_approval("wd-nokey", 1000, addr)
        assert sig is None


# ===========================================================================
# request_approval Tests (2)
# ===========================================================================


class TestRequestApproval:
    """Tests for the request_approval fan-out method."""

    @pytest.mark.asyncio
    async def test_request_approval_threshold_met(self):
        """Fan-out should collect approvals and detect threshold met."""
        vc = ValidatorConsensus(
            node_urls=["http://v1", "http://v2", "http://v3", "http://v4"],
            threshold=3,
            total=4,
            validator_id="proposer",
        )

        # Mock _send_to_validator to return approvals from 3/4 validators
        async def mock_send(url, payload):
            if url == "http://v4":
                return {"rejected": True, "validator_id": "v4", "reason": "too high"}
            vid = url.split("//")[1]
            return {"validator_id": vid, "signature": f"sig-{vid}"}

        with patch.object(vc, "_send_to_validator", side_effect=mock_send):
            approved, signatures = await vc.request_approval(
                "wd-thresh", 1000, "0x" + "ab" * 20
            )

        assert approved is True
        assert len(signatures) == 3

    @pytest.mark.asyncio
    async def test_request_approval_insufficient(self):
        """When too few validators approve, the result should be False."""
        vc = ValidatorConsensus(
            node_urls=["http://v1", "http://v2", "http://v3", "http://v4"],
            threshold=4,
            total=4,
            validator_id="proposer",
        )

        async def mock_send(url, payload):
            # Only 2 approve, 2 fail
            if url in ("http://v1", "http://v2"):
                vid = url.split("//")[1]
                return {"validator_id": vid, "signature": f"sig-{vid}"}
            return None

        with patch.object(vc, "_send_to_validator", side_effect=mock_send):
            approved, signatures = await vc.request_approval(
                "wd-insuf", 1000, "0x" + "ab" * 20
            )

        assert approved is False
        assert len(signatures) == 2


# ===========================================================================
# check_threshold Tests (2)
# ===========================================================================


class TestCheckThreshold:
    """Tests for the check_threshold method."""

    @pytest.mark.asyncio
    async def test_threshold_met(self):
        """check_threshold should return True when enough approvals exist."""
        vc = ValidatorConsensus(
            node_urls=[], threshold=4, total=6, validator_id="checker"
        )
        # Manually insert a proposal with 4 approvals
        proposal = WithdrawalProposal(
            withdrawal_id="wd-met",
            amount=100,
            recipient="0x" + "ab" * 20,
            proposer="test",
        )
        proposal.approvals = {f"v{i}": f"sig{i}" for i in range(4)}
        vc._proposals["wd-met"] = proposal

        met, sigs = await vc.check_threshold("wd-met")
        assert met is True
        assert len(sigs) == 4

    @pytest.mark.asyncio
    async def test_threshold_not_met(self):
        """check_threshold should return False when not enough approvals."""
        vc = ValidatorConsensus(
            node_urls=[], threshold=4, total=6, validator_id="checker"
        )
        proposal = WithdrawalProposal(
            withdrawal_id="wd-notmet",
            amount=100,
            recipient="0x" + "ab" * 20,
            proposer="test",
        )
        proposal.approvals = {"v1": "sig1", "v2": "sig2"}  # only 2
        vc._proposals["wd-notmet"] = proposal

        met, sigs = await vc.check_threshold("wd-notmet")
        assert met is False
        assert len(sigs) == 2


# ===========================================================================
# _check_rate_limit Tests (1)
# ===========================================================================


class TestRateLimit:
    """Tests for the sliding-window rate limiter."""

    def test_rate_limit_sliding_window(self):
        """Rate limit should prune old timestamps and enforce limit."""
        vc = ValidatorConsensus(
            node_urls=[], threshold=1, total=1, rate_limit=3
        )

        now = time.time()
        # 3 approvals within the window — should all be allowed
        vc._approval_timestamps = [now - 10, now - 5, now - 1]
        assert vc._check_rate_limit() is False  # 3 >= 3 → at limit

        # After pruning old entries (> 1 hour), should be allowed again
        vc._approval_timestamps = [now - 7200, now - 3700, now - 1]
        result = vc._check_rate_limit()
        assert result is True  # only 1 recent timestamp


# ===========================================================================
# expire_stale_proposals Tests (1)
# ===========================================================================


class TestExpireStaleProposals:
    """Tests for proposal TTL expiration."""

    @pytest.mark.asyncio
    async def test_expire_stale(self):
        """Proposals older than TTL should be expired."""
        vc = ValidatorConsensus(
            node_urls=[], threshold=1, total=1, proposal_ttl=60.0
        )

        # Fresh proposal — should NOT be expired
        fresh = WithdrawalProposal(
            withdrawal_id="wd-fresh",
            amount=100,
            recipient="0x" + "ab" * 20,
            proposer="test",
            timestamp=time.time(),
        )
        # Stale proposal — 200s old, TTL is 60s
        stale = WithdrawalProposal(
            withdrawal_id="wd-stale",
            amount=100,
            recipient="0x" + "ab" * 20,
            proposer="test",
            timestamp=time.time() - 200,
        )
        vc._proposals = {"wd-fresh": fresh, "wd-stale": stale}

        expired_count = await vc.expire_stale_proposals()
        assert expired_count == 1
        assert stale.status == ProposalStatus.EXPIRED
        assert fresh.status == ProposalStatus.PROPOSED
