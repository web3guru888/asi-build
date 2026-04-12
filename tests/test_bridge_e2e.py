"""
End-to-end integration tests for the Bridge Orchestrator.
==========================================================

Tests the full BridgeOrchestrator lifecycle — deposit observation,
attestation, withdrawal, sync-committee updates, health checks,
and the main relay loop — using real BridgeValidator + MockLightClient
with mock contract clients.

55 tests across 7 categories.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asi_build.rings.bridge.e2e import (
    BridgeOrchestrator,
    ProcessedDeposit,
    _mock_public_inputs,
    _mock_zk_proof,
)
from asi_build.rings.bridge.light_client import (
    BeaconHeader,
    MockLightClient,
    SyncCommittee,
)
from asi_build.rings.bridge.protocol import (
    BridgeMessage,
    BridgeProtocol,
    BridgeState,
    BridgeValidator,
    DepositRecord,
    WithdrawalRecord,
)
from asi_build.rings.client import InMemoryTransport, RingsClient

# A valid 20-byte hex Ethereum address for use in withdrawal tests.
_ETH_ADDR = "0xaabbccddee1122334455aabbccddee1122334455"
_ETH_ADDR2 = "0x1234567890abcdef1234567890abcdef12345678"


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


class MockIdentity:
    """Duck-typed identity for BridgeValidator."""

    def __init__(self, seed: str = "test"):
        self._seed = seed
        h = hashlib.sha256(seed.encode()).hexdigest()
        self._did = f"did:rings:secp256k1:{h[:20]}"

    @property
    def rings_did(self) -> str:
        return self._did

    def sign_rings(self, data: bytes) -> bytes:
        return hmac.new(self._seed.encode(), data, hashlib.sha256).digest()


def _make_deposit_event(
    tx_hash: str = "0xdead",
    block: int = 100,
    amount: int = 10**18,
    rings_did: str = "did:rings:ed25519:recipient",
    sender: str = "0xSender",
) -> dict:
    """Build a mock deposit event dict matching contract ABI."""
    return {
        "transactionHash": tx_hash,
        "blockNumber": block,
        "args": {
            "amount": amount,
            "ringsDid": rings_did,
            "sender": sender,
        },
    }


def _make_header(slot: int) -> BeaconHeader:
    """Build a BeaconHeader for a given slot."""
    return BeaconHeader(
        slot=slot,
        proposer_index=42,
        parent_root="0xaa",
        state_root="0xbb",
        body_root="0xcc",
        timestamp=int(time.time()),
    )


def _make_contract_client(**overrides) -> AsyncMock:
    """Build a mock contract client with sensible defaults."""
    cc = AsyncMock()
    cc.get_deposit_events = AsyncMock(return_value=[])
    cc.withdraw = AsyncMock(return_value="0xtxhash_withdraw")
    cc.get_sync_committee_root = AsyncMock(return_value=b"\x00" * 32)
    cc.update_sync_committee = AsyncMock()
    cc.is_paused = AsyncMock(return_value=False)
    cc.get_remaining_daily_limit = AsyncMock(return_value=10**20)
    cc.get_latest_verified_slot = AsyncMock(return_value=8192)
    cc.get_deposit_nonce = AsyncMock(return_value=0)
    cc.get_withdrawal_nonce = AsyncMock(return_value=0)
    cc.web3 = AsyncMock()
    cc.web3.get_block_number = AsyncMock(return_value=18_000_000)
    for k, v in overrides.items():
        setattr(cc, k, v)
    return cc


async def _make_orchestrator(
    seed: str = "v1",
    threshold: int = 1,
    total: int = 1,
    max_deposits: int = 100,
    add_default_header: bool = True,
    **contract_overrides,
) -> tuple[BridgeOrchestrator, BridgeValidator, MockLightClient, AsyncMock]:
    """Create a full orchestrator stack for testing.

    Returns (orchestrator, validator, light_client, contract_client).
    """
    transport = InMemoryTransport()
    client = RingsClient(transport=transport)
    await client.connect()

    identity = MockIdentity(seed)
    validator = BridgeValidator(
        identity, client, threshold=threshold, total=total,
    )
    await validator.join_bridge()

    lc = MockLightClient()
    await lc.sync("0xcheckpoint")
    if add_default_header:
        lc.add_header(_make_header(100))

    cc = _make_contract_client(**contract_overrides)

    orch = BridgeOrchestrator(
        validator, cc, lc, max_deposits_per_batch=max_deposits,
    )
    return orch, validator, lc, cc


# ===================================================================
# 1.  Full deposit flow (10 tests)
# ===================================================================


class TestDepositFlow:
    """End-to-end deposit processing tests."""

    @pytest.mark.asyncio
    async def test_process_single_deposit(self):
        """Single deposit event is processed, verified, and attested."""
        event = _make_deposit_event(tx_hash="0xabc", block=100)
        orch, val, lc, cc = await _make_orchestrator(
            get_deposit_events=AsyncMock(return_value=[event]),
        )
        results = await orch.process_deposits(from_block=90)

        assert len(results) == 1
        pd = results[0]
        assert pd.tx_hash == "0xabc"
        assert pd.verified is True
        assert pd.attested is True
        assert pd.record is not None
        assert pd.error is None

    @pytest.mark.asyncio
    async def test_process_multiple_deposits(self):
        """Multiple deposit events in one batch are all processed."""
        events = [
            _make_deposit_event(tx_hash=f"0x{i:04x}", block=100 + i)
            for i in range(5)
        ]
        orch, val, lc, cc = await _make_orchestrator(
            get_deposit_events=AsyncMock(return_value=events),
        )
        # Add headers for all blocks
        for i in range(5):
            lc.add_header(_make_header(100 + i))

        results = await orch.process_deposits(from_block=90)
        assert len(results) == 5
        assert all(r.verified and r.attested for r in results)

    @pytest.mark.asyncio
    async def test_deposit_missing_header_fails_gracefully(self):
        """Deposit with no light-client header is skipped (not crash)."""
        event = _make_deposit_event(tx_hash="0xnohdr", block=999)
        orch, val, lc, cc = await _make_orchestrator(
            get_deposit_events=AsyncMock(return_value=[event]),
            add_default_header=False,
        )
        results = await orch.process_deposits(from_block=990)
        assert len(results) == 1
        assert results[0].verified is False
        assert results[0].attested is False
        assert "No verified header" in results[0].error

    @pytest.mark.asyncio
    async def test_deposit_verification_via_light_client(self):
        """Deposit verification calls light client get_verified_header."""
        event = _make_deposit_event(block=100)
        orch, val, lc, cc = await _make_orchestrator(
            get_deposit_events=AsyncMock(return_value=[event]),
        )
        results = await orch.process_deposits(from_block=90)
        assert results[0].verified is True

    @pytest.mark.asyncio
    async def test_deposit_attested_after_observation(self):
        """After observation, the deposit's attestations dict is populated."""
        event = _make_deposit_event(tx_hash="0xattest", block=100)
        orch, val, lc, cc = await _make_orchestrator(
            get_deposit_events=AsyncMock(return_value=[event]),
        )
        results = await orch.process_deposits(from_block=90)
        # The record stored in validator.deposits is the post-attestation
        # version (attest_deposit's _fetch_deposit creates a new record from
        # DHT data, so pd.record may be the pre-attestation snapshot).
        live_record = val.deposits["0xattest"]
        assert val.did in live_record.attestations
        assert isinstance(live_record.attestations[val.did], bytes)

    @pytest.mark.asyncio
    async def test_batch_size_limit_respected(self):
        """Only max_deposits_per_batch events are processed."""
        events = [_make_deposit_event(tx_hash=f"0x{i}", block=100) for i in range(20)]
        orch, val, lc, cc = await _make_orchestrator(
            max_deposits=5,
            get_deposit_events=AsyncMock(return_value=events),
        )
        results = await orch.process_deposits(from_block=90)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_stats_updated_after_processing(self):
        """deposits_processed stat incremented for each successful deposit."""
        events = [
            _make_deposit_event(tx_hash=f"0xstat{i}", block=100)
            for i in range(3)
        ]
        orch, val, lc, cc = await _make_orchestrator(
            get_deposit_events=AsyncMock(return_value=events),
        )
        await orch.process_deposits(from_block=90)
        assert orch.stats["deposits_processed"] == 3

    @pytest.mark.asyncio
    async def test_last_processed_block_cursor_updated(self):
        """_last_processed_block moves to the max block in the batch."""
        events = [
            _make_deposit_event(tx_hash="0xa", block=100),
            _make_deposit_event(tx_hash="0xb", block=200),
        ]
        orch, val, lc, cc = await _make_orchestrator(
            get_deposit_events=AsyncMock(return_value=events),
        )
        lc.add_header(_make_header(200))
        await orch.process_deposits(from_block=90)
        assert orch._last_processed_block == 200

    @pytest.mark.asyncio
    async def test_empty_event_list_returns_empty(self):
        """No events → empty list, no stats change."""
        orch, val, lc, cc = await _make_orchestrator(
            get_deposit_events=AsyncMock(return_value=[]),
        )
        results = await orch.process_deposits(from_block=0)
        assert results == []
        assert orch.stats["deposits_processed"] == 0

    @pytest.mark.asyncio
    async def test_processed_deposit_fields_populated(self):
        """All ProcessedDeposit fields are correctly populated."""
        event = _make_deposit_event(
            tx_hash="0xfull",
            block=100,
            amount=42,
            rings_did="did:rings:ed25519:bob",
            sender="0xAlice",
        )
        orch, val, lc, cc = await _make_orchestrator(
            get_deposit_events=AsyncMock(return_value=[event]),
        )
        results = await orch.process_deposits(from_block=90)
        pd = results[0]
        assert pd.tx_hash == "0xfull"
        assert pd.block_number == 100
        assert pd.amount == 42
        assert pd.rings_did == "did:rings:ed25519:bob"
        assert pd.sender == "0xAlice"


# ===================================================================
# 2.  Full withdrawal flow (10 tests)
# ===================================================================


class TestWithdrawalFlow:
    """End-to-end withdrawal processing tests."""

    @pytest.mark.asyncio
    async def test_complete_withdrawal_flow(self):
        """Full withdrawal: request → approve → proof → submit."""
        orch, val, lc, cc = await _make_orchestrator()
        tx = await orch.process_withdrawal(
            rings_did="did:rings:ed25519:alice",
            amount=10**18,
            eth_address=_ETH_ADDR,
        )
        assert tx == "0xtxhash_withdraw"
        cc.withdraw.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_withdrawal_zk_proof_length(self):
        """Mock ZK proof is exactly 256 bytes."""
        orch, val, lc, cc = await _make_orchestrator()
        await orch.process_withdrawal(
            rings_did="did:rings:ed25519:alice",
            amount=10**18,
            eth_address=_ETH_ADDR,
        )
        call_kwargs = cc.withdraw.call_args
        proof = call_kwargs.kwargs.get("proof") or call_kwargs[1].get("proof")
        assert len(proof) == 256

    @pytest.mark.asyncio
    async def test_withdrawal_public_inputs_content(self):
        """Public inputs contain amount, nonce, and recipient_hash."""
        orch, val, lc, cc = await _make_orchestrator()
        amount = 5 * 10**18
        await orch.process_withdrawal(
            rings_did="did:rings:ed25519:alice",
            amount=amount,
            eth_address=_ETH_ADDR,
        )
        call_kwargs = cc.withdraw.call_args
        public_inputs = (
            call_kwargs.kwargs.get("public_inputs")
            or call_kwargs[1].get("public_inputs")
        )
        assert public_inputs[0] == amount  # amount
        assert public_inputs[1] == 0  # nonce (first withdrawal)
        assert isinstance(public_inputs[2], int)  # recipient_hash

    @pytest.mark.asyncio
    async def test_withdrawal_stats_incremented(self):
        """withdrawals_submitted stat is incremented."""
        orch, val, lc, cc = await _make_orchestrator()
        await orch.process_withdrawal("did:x", 100, _ETH_ADDR)
        assert orch.stats["withdrawals_submitted"] == 1

    @pytest.mark.asyncio
    async def test_withdrawal_nonce_from_validator(self):
        """The nonce in the contract call comes from the validator."""
        orch, val, lc, cc = await _make_orchestrator()
        await orch.process_withdrawal("did:x", 100, _ETH_ADDR)
        call_kwargs = cc.withdraw.call_args
        nonce = call_kwargs.kwargs.get("nonce") or call_kwargs[1].get("nonce")
        assert nonce == 0

    @pytest.mark.asyncio
    async def test_transaction_hash_returned(self):
        """The on-chain tx hash is returned to the caller."""
        orch, val, lc, cc = await _make_orchestrator(
            withdraw=AsyncMock(return_value="0xMyTxHash"),
        )
        tx = await orch.process_withdrawal("did:x", 100, _ETH_ADDR)
        assert tx == "0xMyTxHash"

    @pytest.mark.asyncio
    async def test_multiple_sequential_withdrawals(self):
        """Sequential withdrawals get incrementing nonces."""
        orch, val, lc, cc = await _make_orchestrator()
        nonces = []
        for i in range(3):
            await orch.process_withdrawal("did:x", 100 * (i + 1), _ETH_ADDR)
            call_kwargs = cc.withdraw.call_args
            n = call_kwargs.kwargs.get("nonce") or call_kwargs[1].get("nonce")
            nonces.append(n)
        assert nonces == [0, 1, 2]
        assert orch.stats["withdrawals_submitted"] == 3

    @pytest.mark.asyncio
    async def test_withdrawal_threshold_not_met_warning(self):
        """Single-validator mode with threshold=2 still proceeds (warning)."""
        orch, val, lc, cc = await _make_orchestrator(threshold=2, total=3)
        # threshold=2 but only 1 validator's self-approval → threshold not met
        # but orchestrator still proceeds (logs a warning, doesn't raise)
        tx = await orch.process_withdrawal("did:x", 100, _ETH_ADDR)
        assert tx == "0xtxhash_withdraw"

    @pytest.mark.asyncio
    async def test_contract_withdraw_called_with_correct_args(self):
        """contract.withdraw receives recipient, amount, nonce, proof, inputs."""
        orch, val, lc, cc = await _make_orchestrator()
        await orch.process_withdrawal("did:x", 999, _ETH_ADDR2)
        cc.withdraw.assert_awaited_once()
        kwargs = cc.withdraw.call_args.kwargs
        assert kwargs["recipient"] == _ETH_ADDR2
        assert kwargs["amount"] == 999
        assert kwargs["nonce"] == 0
        assert len(kwargs["proof"]) == 256
        assert len(kwargs["public_inputs"]) == 3

    @pytest.mark.asyncio
    async def test_withdrawal_error_propagation(self):
        """If the contract raises, the error propagates to the caller."""
        orch, val, lc, cc = await _make_orchestrator(
            withdraw=AsyncMock(side_effect=RuntimeError("tx reverted")),
        )
        with pytest.raises(RuntimeError, match="tx reverted"):
            await orch.process_withdrawal("did:x", 100, _ETH_ADDR)


# ===================================================================
# 3.  Multi-validator attestation (8 tests)
# ===================================================================


class TestMultiValidatorAttestation:
    """Tests with multiple BridgeValidators cooperating."""

    async def _make_multi_validators(
        self, n: int = 6, threshold: int = 4,
    ) -> tuple[list[BridgeValidator], InMemoryTransport]:
        """Create n validators sharing the same InMemoryTransport."""
        transport = InMemoryTransport()
        validators = []
        for i in range(n):
            client = RingsClient(transport=transport)
            await client.connect()
            identity = MockIdentity(f"validator_{i}")
            v = BridgeValidator(
                identity, client, threshold=threshold, total=n,
            )
            await v.join_bridge()
            validators.append(v)
        return validators, transport

    @pytest.mark.asyncio
    async def test_setup_multiple_validators(self):
        """6 validators can be created with shared transport."""
        validators, _ = await self._make_multi_validators(6, 4)
        assert len(validators) == 6
        assert all(v.state == BridgeState.ACTIVE for v in validators)

    @pytest.mark.asyncio
    async def test_independent_deposit_observation(self):
        """Each validator independently observes the same deposit."""
        validators, _ = await self._make_multi_validators(6, 4)
        for v in validators:
            await v.observe_deposit(
                tx_hash="0xshared", block=100, amount=10**18,
                sender_eth="0xSender", recipient_did="did:rings:ed25519:recv",
            )
        assert all("0xshared" in v.deposits for v in validators)

    @pytest.mark.asyncio
    async def test_attestation_count_reaches_threshold(self):
        """Attestations from 4+ validators meet threshold=4.

        One validator observes, then 4 attest sequentially.
        Each attest reads DHT (accumulating prior attestations) and writes back.
        """
        validators, _ = await self._make_multi_validators(6, 4)
        # Single observer so DHT record isn't overwritten by later observe()
        await validators[0].observe_deposit(
            tx_hash="0xthresh", block=100, amount=100,
            sender_eth="0xS", recipient_did="did:x",
        )
        for v in validators[:4]:
            await v.attest_deposit("0xthresh")

        met, sigs = await validators[0].collect_attestations("0xthresh")
        assert met is True
        assert len(sigs) >= 4

    @pytest.mark.asyncio
    async def test_finalization_flag_set_at_threshold(self):
        """Deposit is marked finalized once threshold attestations exist."""
        validators, _ = await self._make_multi_validators(4, 4)
        await validators[0].observe_deposit(
            tx_hash="0xfin", block=100, amount=100,
            sender_eth="0xS", recipient_did="did:x",
        )
        for v in validators:
            await v.attest_deposit("0xfin")

        await validators[0].collect_attestations("0xfin")
        record = validators[0].deposits["0xfin"]
        assert record.finalized is True

    @pytest.mark.asyncio
    async def test_below_threshold_not_finalized(self):
        """Fewer than threshold attestations → deposit NOT finalized."""
        validators, _ = await self._make_multi_validators(6, 4)
        # Only 2 validators attest (threshold=4)
        await validators[0].observe_deposit(
            tx_hash="0xbelow", block=100, amount=100,
            sender_eth="0xS", recipient_did="did:x",
        )
        for v in validators[:2]:
            await v.attest_deposit("0xbelow")

        met, sigs = await validators[0].collect_attestations("0xbelow")
        assert met is False
        assert len(sigs) < 4

    @pytest.mark.asyncio
    async def test_approval_collection_for_withdrawals(self):
        """Multiple validators approving a withdrawal reaches threshold."""
        validators, _ = await self._make_multi_validators(6, 4)
        # First validator requests withdrawal
        record = await validators[0].request_withdrawal(1000, _ETH_ADDR)
        nonce = record.nonce

        # 4 validators approve
        for v in validators[:4]:
            await v.approve_withdrawal(nonce)

        met, sigs = await validators[0].collect_approvals(nonce)
        assert met is True
        assert len(sigs) >= 4

    @pytest.mark.asyncio
    async def test_cross_validator_attestation_merge(self):
        """DHT merge: validator 0 sees attestations from validators 1-3."""
        validators, _ = await self._make_multi_validators(4, 4)
        # Only one observe, then all attest — each _fetch_deposit reads
        # DHT and merges, so all attestations accumulate.
        await validators[0].observe_deposit(
            tx_hash="0xmerge", block=100, amount=100,
            sender_eth="0xS", recipient_did="did:x",
        )
        for v in validators:
            await v.attest_deposit("0xmerge")

        met, sigs = await validators[0].collect_attestations("0xmerge")
        assert met is True
        assert len(sigs) >= 4

    @pytest.mark.asyncio
    async def test_five_of_six_achieves_threshold(self):
        """5 out of 6 validators (threshold=4) is sufficient."""
        validators, _ = await self._make_multi_validators(6, 4)
        await validators[0].observe_deposit(
            tx_hash="0x5of6", block=100, amount=100,
            sender_eth="0xS", recipient_did="did:x",
        )
        for v in validators[:5]:
            await v.attest_deposit("0x5of6")

        met, sigs = await validators[0].collect_attestations("0x5of6")
        assert met is True
        assert len(sigs) >= 4


# ===================================================================
# 4.  Sync committee updates (8 tests)
# ===================================================================


class TestSyncCommitteeUpdates:
    """Tests for sync committee rotation detection and submission."""

    def _add_committee(self, lc: MockLightClient, period: int, slot: int):
        """Add a header and committee at the given slot/period."""
        lc.add_header(_make_header(slot))
        lc.add_sync_committee(SyncCommittee(
            period=period,
            pubkeys=["0xpub1", "0xpub2"],
            aggregate_pubkey=f"0xagg_{period}",
        ))

    @pytest.mark.asyncio
    async def test_committee_rotation_detected_and_submitted(self):
        """When on-chain root differs, update_sync_committee is called."""
        orch, val, lc, cc = await _make_orchestrator()
        self._add_committee(lc, period=0, slot=4000)
        # Default on-chain root is b"\x00"*32 which won't match
        result = await orch.sync_committee_update()
        assert result is True
        cc.update_sync_committee.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_update_when_committee_matches(self):
        """When on-chain root matches, no update is submitted."""
        orch, val, lc, cc = await _make_orchestrator()
        self._add_committee(lc, period=0, slot=4000)

        # Compute the expected root and set it on-chain
        expected_root = hashlib.sha256(b"0xagg_0").digest()
        cc.get_sync_committee_root = AsyncMock(return_value=expected_root)

        result = await orch.sync_committee_update()
        assert result is False
        cc.update_sync_committee.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_period_calculation(self):
        """Period = slot // 8192."""
        orch, val, lc, cc = await _make_orchestrator()
        slot = 16384  # period = 2
        self._add_committee(lc, period=2, slot=slot)
        result = await orch.sync_committee_update()
        assert result is True
        call_kwargs = cc.update_sync_committee.call_args.kwargs
        assert call_kwargs["public_inputs"][0] == 2  # period
        assert call_kwargs["public_inputs"][1] == slot

    @pytest.mark.asyncio
    async def test_mock_proof_generated(self):
        """The committee update includes a 256-byte proof."""
        orch, val, lc, cc = await _make_orchestrator()
        self._add_committee(lc, period=0, slot=4000)
        await orch.sync_committee_update()
        call_kwargs = cc.update_sync_committee.call_args.kwargs
        assert len(call_kwargs["proof"]) == 256

    @pytest.mark.asyncio
    async def test_contract_update_called_with_correct_args(self):
        """update_sync_committee receives new_root, slot, proof, inputs."""
        orch, val, lc, cc = await _make_orchestrator()
        self._add_committee(lc, period=0, slot=4000)
        await orch.sync_committee_update()
        call_kwargs = cc.update_sync_committee.call_args.kwargs
        assert "new_root" in call_kwargs
        assert "slot" in call_kwargs
        assert "proof" in call_kwargs
        assert "public_inputs" in call_kwargs
        assert isinstance(call_kwargs["new_root"], bytes)
        assert len(call_kwargs["new_root"]) == 32

    @pytest.mark.asyncio
    async def test_stats_incremented_on_update(self):
        """sync_updates stat is incremented on successful update."""
        orch, val, lc, cc = await _make_orchestrator()
        self._add_committee(lc, period=0, slot=4000)
        await orch.sync_committee_update()
        assert orch.stats["sync_updates"] == 1

    @pytest.mark.asyncio
    async def test_error_when_light_client_missing_committee(self):
        """Returns False when light client has no committee for the period."""
        orch, val, lc, cc = await _make_orchestrator()
        # Header exists (slot=100, period=0) but no committee added
        result = await orch.sync_committee_update()
        assert result is False

    @pytest.mark.asyncio
    async def test_error_when_contract_query_fails(self):
        """On-chain root query failure defaults to zero root (update proceeds)."""
        orch, val, lc, cc = await _make_orchestrator()
        self._add_committee(lc, period=0, slot=4000)
        cc.get_sync_committee_root = AsyncMock(
            side_effect=ConnectionError("RPC down"),
        )
        # Should still submit because fallback is b"\x00"*32
        result = await orch.sync_committee_update()
        assert result is True


# ===================================================================
# 5.  Health check (6 tests)
# ===================================================================


class TestHealthCheck:
    """Tests for the health_check endpoint."""

    @pytest.mark.asyncio
    async def test_all_fields_populated(self):
        """Health check returns all expected keys."""
        orch, val, lc, cc = await _make_orchestrator()
        health = await orch.health_check()
        expected_keys = {
            "validator_did", "validator_state", "light_client_synced",
            "last_processed_block", "stats", "paused",
            "remaining_daily_limit", "latest_verified_slot",
            "deposit_nonce", "withdrawal_nonce",
        }
        assert expected_keys.issubset(health.keys())

    @pytest.mark.asyncio
    async def test_validator_did_included(self):
        """Health check includes the validator's DID."""
        orch, val, lc, cc = await _make_orchestrator()
        health = await orch.health_check()
        assert health["validator_did"] == val.did
        assert health["validator_did"].startswith("did:rings:")

    @pytest.mark.asyncio
    async def test_light_client_sync_status(self):
        """Light client sync status is reported."""
        orch, val, lc, cc = await _make_orchestrator()
        health = await orch.health_check()
        assert health["light_client_synced"] is True

    @pytest.mark.asyncio
    async def test_contract_errors_handled_gracefully(self):
        """Contract query errors produce string error messages, not crashes."""
        orch, val, lc, cc = await _make_orchestrator(
            is_paused=AsyncMock(side_effect=ConnectionError("RPC offline")),
            get_remaining_daily_limit=AsyncMock(
                side_effect=TimeoutError("timeout"),
            ),
            get_latest_verified_slot=AsyncMock(
                side_effect=ValueError("decode error"),
            ),
        )
        health = await orch.health_check()
        assert "error:" in health["paused"]
        assert "error:" in health["remaining_daily_limit"]
        assert "error:" in health["latest_verified_slot"]

    @pytest.mark.asyncio
    async def test_stats_included(self):
        """Stats dict is present with initial zero values."""
        orch, val, lc, cc = await _make_orchestrator()
        health = await orch.health_check()
        assert health["stats"]["deposits_processed"] == 0
        assert health["stats"]["withdrawals_submitted"] == 0

    @pytest.mark.asyncio
    async def test_last_processed_block_reported(self):
        """last_processed_block starts at 0 and updates after deposits."""
        orch, val, lc, cc = await _make_orchestrator()
        health = await orch.health_check()
        assert health["last_processed_block"] == 0

        # Process a deposit to advance the cursor
        event = _make_deposit_event(tx_hash="0xhc", block=100)
        cc.get_deposit_events = AsyncMock(return_value=[event])
        await orch.process_deposits(from_block=90)

        health = await orch.health_check()
        assert health["last_processed_block"] == 100


# ===================================================================
# 6.  Bridge loop (6 tests)
# ===================================================================


class TestBridgeLoop:
    """Tests for the main bridge relay loop."""

    @pytest.mark.asyncio
    async def test_loop_starts_and_stops(self):
        """Loop can be started and stopped via stop()."""
        orch, val, lc, cc = await _make_orchestrator()

        async def stop_soon():
            await asyncio.sleep(0.05)
            orch.stop()

        task = asyncio.create_task(stop_soon())
        await orch.run_bridge_loop(poll_interval=0.01)
        await task
        assert orch._loop_running is False

    @pytest.mark.asyncio
    async def test_loop_processes_deposits_and_sync(self):
        """Loop calls process_deposits and sync_committee_update."""
        orch, val, lc, cc = await _make_orchestrator()
        cc.get_deposit_events = AsyncMock(return_value=[])
        call_count = 0

        orig_process = orch.process_deposits

        async def counting_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                orch.stop()
            return await orig_process(*args, **kwargs)

        orch.process_deposits = counting_process
        await orch.run_bridge_loop(poll_interval=0.01, start_block=100)
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_loop_handles_iteration_errors(self):
        """Loop continues after an error in one iteration."""
        orch, val, lc, cc = await _make_orchestrator()
        call_count = 0

        async def failing_events(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("temporary failure")
            if call_count >= 3:
                orch.stop()
            return []

        cc.get_deposit_events = failing_events
        await orch.run_bridge_loop(poll_interval=0.01, start_block=100)
        assert call_count >= 3  # Kept running after the error

    @pytest.mark.asyncio
    async def test_loop_cursor_advances(self):
        """Cursor advances as deposits are processed."""
        orch, val, lc, cc = await _make_orchestrator()
        call_num = 0

        async def progressive_events(from_block, to_block=None):
            nonlocal call_num
            call_num += 1
            if call_num == 1:
                return [_make_deposit_event(tx_hash="0x1", block=200)]
            if call_num >= 2:
                orch.stop()
            return []

        cc.get_deposit_events = progressive_events
        lc.add_header(_make_header(200))
        await orch.run_bridge_loop(poll_interval=0.01, start_block=100)
        assert orch._last_processed_block == 200

    @pytest.mark.asyncio
    async def test_loop_start_block_parameter_respected(self):
        """start_block parameter is used as the initial cursor."""
        orch, val, lc, cc = await _make_orchestrator()
        first_from_block = None

        async def capture_from_block(from_block, to_block=None):
            nonlocal first_from_block
            if first_from_block is None:
                first_from_block = from_block
            orch.stop()
            return []

        cc.get_deposit_events = capture_from_block
        await orch.run_bridge_loop(poll_interval=0.01, start_block=42_000)
        assert first_from_block == 42_000

    @pytest.mark.asyncio
    async def test_loop_uses_last_processed_block(self):
        """When no start_block, loop uses _last_processed_block + 1."""
        orch, val, lc, cc = await _make_orchestrator()
        orch._last_processed_block = 500
        first_from_block = None

        async def capture_from_block(from_block, to_block=None):
            nonlocal first_from_block
            if first_from_block is None:
                first_from_block = from_block
            orch.stop()
            return []

        cc.get_deposit_events = capture_from_block
        await orch.run_bridge_loop(poll_interval=0.01)
        assert first_from_block == 501


# ===================================================================
# 7.  Rate limit & emergency scenarios (7 tests)
# ===================================================================


class TestRateLimitAndEmergency:
    """Tests for rate limits, emergency halt, and error resilience."""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """Batch size limit applies across repeated calls."""
        orch, val, lc, cc = await _make_orchestrator(max_deposits=3)
        events = [
            _make_deposit_event(tx_hash=f"0xrl{i}", block=100)
            for i in range(10)
        ]
        cc.get_deposit_events = AsyncMock(return_value=events)
        results = await orch.process_deposits(from_block=90)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_emergency_pause_halts_validator(self):
        """After emergency_halt(), the validator refuses deposits."""
        orch, val, lc, cc = await _make_orchestrator()
        await val.emergency_halt("suspicious activity")
        assert val.state == BridgeState.HALTED

        # Deposits should fail because the validator is halted
        event = _make_deposit_event(tx_hash="0xhalted", block=100)
        cc.get_deposit_events = AsyncMock(return_value=[event])
        results = await orch.process_deposits(from_block=90)
        assert len(results) == 1
        assert results[0].error is not None
        assert results[0].attested is False

    @pytest.mark.asyncio
    async def test_recovery_from_validator_failure(self):
        """Validator can resume after being halted (manual recovery)."""
        orch, val, lc, cc = await _make_orchestrator()
        await val.emergency_halt("test")
        assert val.state == BridgeState.HALTED

        # Manual recovery
        val.state = BridgeState.ACTIVE
        event = _make_deposit_event(tx_hash="0xrecovered", block=100)
        cc.get_deposit_events = AsyncMock(return_value=[event])
        results = await orch.process_deposits(from_block=90)
        assert results[0].attested is True

    @pytest.mark.asyncio
    async def test_error_resilience_in_deposit_processing(self):
        """Individual deposit errors don't crash the batch."""
        orch, val, lc, cc = await _make_orchestrator()
        events = [
            _make_deposit_event(tx_hash="0xgood", block=100),
            _make_deposit_event(tx_hash="0xbad", block=999),  # no header
            _make_deposit_event(tx_hash="0xgood2", block=100),
        ]
        cc.get_deposit_events = AsyncMock(return_value=events)
        results = await orch.process_deposits(from_block=90)
        assert len(results) == 3
        assert results[0].verified is True
        assert results[1].verified is False
        assert results[1].error is not None
        assert results[2].verified is True

    @pytest.mark.asyncio
    async def test_partial_batch_success(self):
        """Stats reflect both successes and failures in a batch."""
        orch, val, lc, cc = await _make_orchestrator()
        events = [
            _make_deposit_event(tx_hash="0xok1", block=100),
            _make_deposit_event(tx_hash="0xfail", block=777),
            _make_deposit_event(tx_hash="0xok2", block=100),
        ]
        cc.get_deposit_events = AsyncMock(return_value=events)
        await orch.process_deposits(from_block=90)
        assert orch.stats["deposits_processed"] == 2
        assert orch.stats["deposits_failed"] == 1

    @pytest.mark.asyncio
    async def test_contract_client_error_propagation(self):
        """Contract client errors in withdrawal propagate to caller."""
        orch, val, lc, cc = await _make_orchestrator(
            withdraw=AsyncMock(side_effect=ConnectionError("RPC down")),
        )
        with pytest.raises(ConnectionError, match="RPC down"):
            await orch.process_withdrawal("did:x", 100, _ETH_ADDR)

    @pytest.mark.asyncio
    async def test_orchestrator_repr(self):
        """repr includes validator DID, last block, running status."""
        orch, val, lc, cc = await _make_orchestrator()
        r = repr(orch)
        assert "BridgeOrchestrator" in r
        assert val.did in r
        assert "last_block=0" in r
        assert "running=False" in r
