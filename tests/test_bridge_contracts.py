"""
Bridge Contract Client & Deployer — Python Simulation Tests
=============================================================

Tests :class:`BridgeContractClient` and :class:`BridgeDeployer` by
simulating the onchain bridge contract state entirely in Python.

Since we can't compile Solidity here, ``MockContractManager`` maintains
deposit/withdrawal state, rate limits, pause state, and sync-committee
roots—mirroring the logic that ``RingsBridge.sol`` would enforce.

~57 tests across 7 categories.
"""

from __future__ import annotations

import time
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock

import pytest

# ── Patch ContractInterface before importing the client ────────────────
# The BridgeContractClient constructor imports ContractInterface; we
# provide a lightweight stand-in so the import succeeds even without the
# full blockchain stack.

from dataclasses import dataclass as _dc


@_dc
class _FakeContractInterface:
    name: str = ""
    address: str = ""
    abi: list = field(default_factory=list)


import sys, types

_cm_mod = types.ModuleType(
    "asi_build.blockchain.web3_integration.contract_manager"
)
_cm_mod.ContractInterface = _FakeContractInterface  # type: ignore[attr-defined]
sys.modules.setdefault(
    "asi_build.blockchain.web3_integration.contract_manager", _cm_mod,
)

from asi_build.rings.bridge.contract_client import (  # noqa: E402
    BridgeContractClient,
    BridgeDeployer,
    BRIDGE_ABI,
    VERIFIER_ABI,
    TOKEN_ABI,
    did_to_bytes32,
)


# ======================================================================
# MockContractManager — simulates RingsBridge.sol state
# ======================================================================


@dataclass
class DepositRecord:
    sender: str
    rings_did: bytes
    amount: int
    token: str
    timestamp: int
    nonce: int
    block_num: int
    processed: bool = False


@dataclass
class WithdrawalRecord:
    recipient: str
    rings_did: bytes
    amount: int
    token: str
    timestamp: int
    nonce: int
    executed: bool = False


class MockContractManager:
    """In-memory simulation of deployed bridge contract state.

    Responds to ``call_contract_function``, ``send_contract_transaction``,
    ``get_contract_events``, and ``deploy_contract`` exactly as a real
    ContractManager + EVM would (minus gas accounting).
    """

    DAILY_LIMIT = 100 * 10**18  # 100 ETH
    PER_TX_LIMIT = 10 * 10**18  # 10 ETH
    DAY_SECONDS = 86_400

    def __init__(self) -> None:
        self.contracts: Dict[str, Any] = {}

        # ── bridge state ────────────────────────────────────────────
        self.deposits: Dict[int, DepositRecord] = {}
        self.withdrawals: Dict[int, WithdrawalRecord] = {}
        self.deposit_nonce: int = 0
        self.withdrawal_nonce: int = 0
        self.paused: bool = False
        self.daily_limit: int = self.DAILY_LIMIT
        self.per_tx_limit: int = self.PER_TX_LIMIT
        self.daily_volume: int = 0
        self.last_reset_ts: float = time.time()
        self.sync_committee_root: bytes = b"\x00" * 32
        self.latest_verified_slot: int = 0
        self.processed_withdrawals: Set[int] = set()
        self.guardian: str = "0xGuardian"
        self.admin: str = "0xAdmin"
        self.caller: str = "0xAdmin"  # current tx sender

        # ── event log ───────────────────────────────────────────────
        self.events: List[Dict[str, Any]] = []
        self.block_number: int = 1

        # ── deploy tracking ─────────────────────────────────────────
        self.deployed: List[Dict[str, Any]] = []
        self._deploy_counter: int = 0
        self.sent_transactions: List[Dict[str, Any]] = []

    # ── helpers ──────────────────────────────────────────────────────

    def _maybe_reset_daily(self) -> None:
        now = time.time()
        if now - self.last_reset_ts >= self.DAY_SECONDS:
            self.daily_volume = 0
            self.last_reset_ts = now

    def _emit(self, name: str, data: Dict[str, Any]) -> None:
        self.events.append({
            "event": name,
            "blockNumber": self.block_number,
            "transactionHash": f"0xtx{self.block_number:04d}",
            **data,
        })
        self.block_number += 1

    def _require_not_paused(self) -> None:
        if self.paused:
            raise RuntimeError("Bridge is paused")

    def _check_rate_limit(self, amount: int) -> None:
        self._maybe_reset_daily()
        if amount > self.per_tx_limit:
            raise RuntimeError(
                f"Exceeds per-tx limit: {amount} > {self.per_tx_limit}"
            )
        if self.daily_volume + amount > self.daily_limit:
            raise RuntimeError(
                f"Exceeds daily limit: {self.daily_volume + amount} > {self.daily_limit}"
            )

    # ── call_contract_function (view calls) ─────────────────────────

    async def call_contract_function(
        self, contract_name: str, fn: str, *, args: list = None,
    ) -> Any:
        args = args or []
        if fn == "depositNonce":
            return self.deposit_nonce
        if fn == "withdrawalNonce":
            return self.withdrawal_nonce
        if fn == "paused":
            return self.paused
        if fn == "getRemainingDailyLimit":
            self._maybe_reset_daily()
            return max(0, self.daily_limit - self.daily_volume)
        if fn == "latestVerifiedSlot":
            return self.latest_verified_slot
        if fn == "syncCommitteeRoot":
            return self.sync_committee_root
        if fn == "getDepositInfo":
            nonce = args[0]
            d = self.deposits.get(nonce)
            if d is None:
                return ("", b"\x00" * 32, 0, "", 0, 0)
            return (d.sender, d.rings_did, d.amount, d.token, d.timestamp, d.nonce)
        if fn == "getWithdrawalInfo":
            nonce = args[0]
            w = self.withdrawals.get(nonce)
            if w is None:
                return ("", b"\x00" * 32, 0, "", 0, 0)
            return (w.recipient, w.rings_did, w.amount, w.token, w.timestamp, w.nonce)
        raise ValueError(f"Unknown view function: {fn}")

    # ── send_contract_transaction (state-changing) ──────────────────

    async def send_contract_transaction(
        self,
        contract_name: str,
        fn: str,
        *,
        args: list = None,
        value: int = 0,
    ) -> str:
        args = args or []
        self.sent_transactions.append({
            "contract": contract_name,
            "fn": fn,
            "args": args,
            "value": value,
        })
        tx_hash = f"0xtx{self.block_number:04d}"

        # ── deposit (native ETH) ─────────────────────────────────
        if fn == "deposit":
            self._require_not_paused()
            rings_did = args[0]
            amount = value
            if amount <= 0:
                raise RuntimeError("Zero amount deposit")
            self._check_rate_limit(amount)
            nonce = self.deposit_nonce
            self.deposits[nonce] = DepositRecord(
                sender=self.caller,
                rings_did=rings_did,
                amount=amount,
                token="0x0000000000000000000000000000000000000000",
                timestamp=self.block_number,
                nonce=nonce,
                block_num=self.block_number,
            )
            self.daily_volume += amount
            self.deposit_nonce += 1
            self._emit("Deposited", {
                "nonce": nonce,
                "depositor": self.caller,
                "ringsDID": rings_did,
                "amount": amount,
            })
            return tx_hash

        # ── depositToken (ERC-20) ────────────────────────────────
        if fn == "depositToken":
            self._require_not_paused()
            token_addr, amount, rings_did = args[0], args[1], args[2]
            if amount <= 0:
                raise RuntimeError("Zero amount deposit")
            self._check_rate_limit(amount)
            nonce = self.deposit_nonce
            self.deposits[nonce] = DepositRecord(
                sender=self.caller,
                rings_did=rings_did,
                amount=amount,
                token=token_addr,
                timestamp=self.block_number,
                nonce=nonce,
                block_num=self.block_number,
            )
            self.daily_volume += amount
            self.deposit_nonce += 1
            self._emit("Deposited", {
                "nonce": nonce,
                "depositor": self.caller,
                "ringsDID": rings_did,
                "amount": amount,
            })
            return tx_hash

        # ── withdraw (native ETH) ────────────────────────────────
        if fn == "withdraw":
            self._require_not_paused()
            recipient, rings_did, amount, nonce, proof, public_inputs = (
                args[0], args[1], args[2], args[3], args[4], args[5],
            )
            if amount <= 0:
                raise RuntimeError("Zero amount withdrawal")
            if nonce in self.processed_withdrawals:
                raise RuntimeError(f"Replay: nonce {nonce} already processed")
            if not proof or len(proof) == 0:
                raise RuntimeError("Proof required")
            self._check_rate_limit(amount)
            self.withdrawals[nonce] = WithdrawalRecord(
                recipient=recipient,
                rings_did=rings_did,
                amount=amount,
                token="0x0000000000000000000000000000000000000000",
                timestamp=self.block_number,
                nonce=nonce,
                executed=True,
            )
            self.processed_withdrawals.add(nonce)
            self.daily_volume += amount
            self.withdrawal_nonce = max(self.withdrawal_nonce, nonce + 1)
            self._emit("Withdrawn", {
                "nonce": nonce,
                "recipient": recipient,
                "amount": amount,
            })
            return tx_hash

        # ── withdrawToken (ERC-20) ───────────────────────────────
        if fn == "withdrawToken":
            self._require_not_paused()
            token_addr, recipient, rings_did, amount, nonce, proof, public_inputs = (
                args[0], args[1], args[2], args[3], args[4], args[5], args[6],
            )
            if amount <= 0:
                raise RuntimeError("Zero amount withdrawal")
            if nonce in self.processed_withdrawals:
                raise RuntimeError(f"Replay: nonce {nonce} already processed")
            if not proof or len(proof) == 0:
                raise RuntimeError("Proof required")
            self._check_rate_limit(amount)
            self.withdrawals[nonce] = WithdrawalRecord(
                recipient=recipient,
                rings_did=rings_did,
                amount=amount,
                token=token_addr,
                timestamp=self.block_number,
                nonce=nonce,
                executed=True,
            )
            self.processed_withdrawals.add(nonce)
            self.daily_volume += amount
            self.withdrawal_nonce = max(self.withdrawal_nonce, nonce + 1)
            self._emit("Withdrawn", {
                "nonce": nonce,
                "recipient": recipient,
                "amount": amount,
            })
            return tx_hash

        # ── updateSyncCommittee ──────────────────────────────────
        if fn == "updateSyncCommittee":
            new_root, slot, proof, public_inputs = (
                args[0], args[1], args[2], args[3],
            )
            if not proof or len(proof) == 0:
                raise RuntimeError("Invalid sync committee proof")
            if slot <= self.latest_verified_slot:
                raise RuntimeError(
                    f"Slot must advance: {slot} <= {self.latest_verified_slot}"
                )
            self.sync_committee_root = (
                new_root if isinstance(new_root, bytes) else bytes(new_root)
            )
            self.latest_verified_slot = slot
            self._emit("SyncCommitteeUpdated", {
                "slot": slot,
                "newRoot": new_root,
            })
            return tx_hash

        # ── emergencyPause / unpause ─────────────────────────────
        if fn == "emergencyPause":
            if self.caller != self.guardian and self.caller != self.admin:
                raise RuntimeError("Only guardian can pause")
            self.paused = True
            self._emit("EmergencyPaused", {"guardian": self.caller})
            return tx_hash

        if fn == "unpause":
            if self.caller != self.admin:
                raise RuntimeError("Only admin can unpause")
            self.paused = False
            self._emit("Unpaused", {"account": self.caller})
            return tx_hash

        # ── updateRateLimits ─────────────────────────────────────
        if fn == "updateRateLimits":
            self.daily_limit = args[0]
            self.per_tx_limit = args[1]
            self._emit("RateLimitUpdated", {
                "newDailyLimit": args[0],
                "newPerTxLimit": args[1],
            })
            return tx_hash

        # ── grantRole (for deployer token tests) ────────────────
        if fn == "grantRole":
            # No-op simulation — just record
            return tx_hash

        raise ValueError(f"Unknown state function: {fn}")

    # ── get_contract_events ─────────────────────────────────────────

    async def get_contract_events(
        self,
        contract_name: str,
        event_name: str,
        *,
        from_block: int = 0,
        to_block: Any = "latest",
    ) -> List[Dict[str, Any]]:
        end = self.block_number if to_block == "latest" else to_block
        return [
            e for e in self.events
            if e["event"] == event_name
            and from_block <= e["blockNumber"] <= end
        ]

    # ── deploy_contract ─────────────────────────────────────────────

    async def deploy_contract(
        self,
        contract_name: str,
        abi: list,
        bytecode: str,
        constructor_args: list = None,
    ) -> Any:
        self._deploy_counter += 1
        addr = f"0xDeployed{self._deploy_counter:04d}"
        self.deployed.append({
            "name": contract_name,
            "abi": abi,
            "bytecode": bytecode,
            "constructor_args": constructor_args or [],
            "address": addr,
        })
        ci = _FakeContractInterface(
            name=contract_name, address=addr, abi=abi,
        )
        self.contracts[contract_name] = ci
        return ci


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def mock_cm():
    return MockContractManager()


@pytest.fixture
def web3():
    return MagicMock()


@pytest.fixture
def client(web3, mock_cm):
    return BridgeContractClient(web3, mock_cm, "0xBridge0001")


@pytest.fixture
def deployer(web3, mock_cm):
    return BridgeDeployer(web3, mock_cm)


VALID_PROOF = b"\x01" * 256
VALID_INPUTS = [1, 2, 3]
RECIPIENT = "0xRecipient0001"
DID = "did:rings:ed25519:abc"
DID_BYTES = did_to_bytes32(DID)
TOKEN_ADDR = "0xToken0001"
ONE_ETH = 10**18


# ======================================================================
# 1. Deposit tests (10)
# ======================================================================


class TestDeposits:
    @pytest.mark.asyncio
    async def test_eth_deposit(self, client, mock_cm):
        tx = await client.deposit(DID, ONE_ETH)
        assert tx.startswith("0xtx")
        assert mock_cm.deposit_nonce == 1

    @pytest.mark.asyncio
    async def test_erc20_deposit(self, client, mock_cm):
        tx = await client.deposit_token(TOKEN_ADDR, ONE_ETH, DID)
        assert tx.startswith("0xtx")
        assert mock_cm.deposit_nonce == 1
        assert mock_cm.deposits[0].rings_did == DID_BYTES

    @pytest.mark.asyncio
    async def test_nonce_increment(self, client, mock_cm):
        await client.deposit(DID, ONE_ETH)
        await client.deposit(DID, ONE_ETH)
        await client.deposit(DID, ONE_ETH)
        assert mock_cm.deposit_nonce == 3

    @pytest.mark.asyncio
    async def test_deposit_event_emission(self, client, mock_cm):
        await client.deposit(DID, ONE_ETH)
        evts = await client.get_deposit_events(from_block=0)
        assert len(evts) == 1
        assert evts[0]["event"] == "Deposited"
        assert evts[0]["ringsDID"] == DID_BYTES
        assert evts[0]["amount"] == ONE_ETH

    @pytest.mark.asyncio
    async def test_zero_amount_rejected(self, client):
        with pytest.raises(RuntimeError, match="Zero amount"):
            await client.deposit(DID, 0)

    @pytest.mark.asyncio
    async def test_deposit_rate_limit(self, client, mock_cm):
        mock_cm.per_tx_limit = ONE_ETH
        with pytest.raises(RuntimeError, match="per-tx limit"):
            await client.deposit(DID, 2 * ONE_ETH)

    @pytest.mark.asyncio
    async def test_deposit_info_retrieval(self, client, mock_cm):
        await client.deposit(DID, 5 * ONE_ETH)
        info = await client.get_deposit_info(0)
        assert info["ringsDID"] == DID_BYTES
        assert info["amount"] == 5 * ONE_ETH
        assert info["nonce"] == 0

    @pytest.mark.asyncio
    async def test_multiple_deposits(self, client, mock_cm):
        for i in range(5):
            await client.deposit(f"did:rings:{i}", ONE_ETH)
        assert mock_cm.deposit_nonce == 5
        for i in range(5):
            info = await client.get_deposit_info(i)
            assert info["ringsDID"] == did_to_bytes32(f"did:rings:{i}")

    @pytest.mark.asyncio
    async def test_paused_deposit_rejected(self, client, mock_cm):
        mock_cm.paused = True
        with pytest.raises(RuntimeError, match="paused"):
            await client.deposit(DID, ONE_ETH)

    @pytest.mark.asyncio
    async def test_deposit_nonce_query(self, client, mock_cm):
        assert await client.get_deposit_nonce() == 0
        await client.deposit(DID, ONE_ETH)
        assert await client.get_deposit_nonce() == 1


# ======================================================================
# 2. Withdrawal tests (12)
# ======================================================================


class TestWithdrawals:
    @pytest.mark.asyncio
    async def test_valid_withdrawal(self, client, mock_cm):
        tx = await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 0, VALID_PROOF, VALID_INPUTS)
        assert tx.startswith("0xtx")
        assert 0 in mock_cm.processed_withdrawals

    @pytest.mark.asyncio
    async def test_replay_protection(self, client, mock_cm):
        await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 0, VALID_PROOF, VALID_INPUTS)
        with pytest.raises(RuntimeError, match="Replay"):
            await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 0, VALID_PROOF, VALID_INPUTS)

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, client, mock_cm):
        mock_cm.daily_limit = 2 * ONE_ETH
        await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 0, VALID_PROOF, VALID_INPUTS)
        await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 1, VALID_PROOF, VALID_INPUTS)
        with pytest.raises(RuntimeError, match="daily limit"):
            await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 2, VALID_PROOF, VALID_INPUTS)

    @pytest.mark.asyncio
    async def test_per_tx_limit(self, client, mock_cm):
        mock_cm.per_tx_limit = ONE_ETH
        with pytest.raises(RuntimeError, match="per-tx limit"):
            await client.withdraw(
                RECIPIENT, DID_BYTES, 2 * ONE_ETH, 0, VALID_PROOF, VALID_INPUTS,
            )

    @pytest.mark.asyncio
    async def test_daily_reset_after_24h(self, client, mock_cm):
        mock_cm.daily_limit = 2 * ONE_ETH
        await client.withdraw(RECIPIENT, DID_BYTES, 2 * ONE_ETH, 0, VALID_PROOF, VALID_INPUTS)
        # Simulate time passing beyond 24h
        mock_cm.last_reset_ts -= mock_cm.DAY_SECONDS + 1
        # Should succeed after daily reset
        tx = await client.withdraw(RECIPIENT, DID_BYTES, 2 * ONE_ETH, 1, VALID_PROOF, VALID_INPUTS)
        assert tx.startswith("0xtx")

    @pytest.mark.asyncio
    async def test_proof_required(self, client):
        with pytest.raises(RuntimeError, match="Proof required"):
            await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 0, b"", VALID_INPUTS)

    @pytest.mark.asyncio
    async def test_invalid_proof_rejected(self, client):
        """Empty proof is rejected."""
        with pytest.raises(RuntimeError, match="Proof required"):
            await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 0, b"", [])

    @pytest.mark.asyncio
    async def test_zero_amount_withdrawal(self, client):
        with pytest.raises(RuntimeError, match="Zero amount"):
            await client.withdraw(RECIPIENT, DID_BYTES, 0, 0, VALID_PROOF, VALID_INPUTS)

    @pytest.mark.asyncio
    async def test_nonce_tracking(self, client, mock_cm):
        await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 0, VALID_PROOF, VALID_INPUTS)
        await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 1, VALID_PROOF, VALID_INPUTS)
        assert mock_cm.withdrawal_nonce >= 2
        assert 0 in mock_cm.processed_withdrawals
        assert 1 in mock_cm.processed_withdrawals

    @pytest.mark.asyncio
    async def test_withdrawal_info_retrieval(self, client, mock_cm):
        await client.withdraw(RECIPIENT, DID_BYTES, 3 * ONE_ETH, 0, VALID_PROOF, VALID_INPUTS)
        info = await client.get_withdrawal_info(0)
        assert info["recipient"] == RECIPIENT
        assert info["amount"] == 3 * ONE_ETH
        assert info["ringsDID"] == DID_BYTES

    @pytest.mark.asyncio
    async def test_erc20_withdrawal(self, client, mock_cm):
        tx = await client.withdraw_token(
            TOKEN_ADDR, RECIPIENT, DID_BYTES, ONE_ETH, 0, VALID_PROOF, VALID_INPUTS,
        )
        assert tx.startswith("0xtx")
        assert 0 in mock_cm.processed_withdrawals

    @pytest.mark.asyncio
    async def test_multiple_withdrawals(self, client, mock_cm):
        for i in range(5):
            await client.withdraw(
                f"0xRecip{i}", DID_BYTES, ONE_ETH, i, VALID_PROOF, VALID_INPUTS,
            )
        assert len(mock_cm.processed_withdrawals) == 5
        evts = await client.get_withdrawal_events(from_block=0)
        assert len(evts) == 5


# ======================================================================
# 3. Sync committee tests (6)
# ======================================================================


class TestSyncCommittee:
    @pytest.mark.asyncio
    async def test_update_with_valid_proof(self, client, mock_cm):
        root = b"\xab" * 32
        tx = await client.update_sync_committee(root, 100, VALID_PROOF, VALID_INPUTS)
        assert tx.startswith("0xtx")
        assert mock_cm.latest_verified_slot == 100

    @pytest.mark.asyncio
    async def test_slot_must_advance(self, client, mock_cm):
        await client.update_sync_committee(b"\xaa" * 32, 100, VALID_PROOF, VALID_INPUTS)
        with pytest.raises(RuntimeError, match="Slot must advance"):
            await client.update_sync_committee(
                b"\xbb" * 32, 50, VALID_PROOF, VALID_INPUTS,
            )

    @pytest.mark.asyncio
    async def test_invalid_proof_rejected(self, client):
        with pytest.raises(RuntimeError, match="Invalid sync committee proof"):
            await client.update_sync_committee(b"\xaa" * 32, 100, b"", VALID_INPUTS)

    @pytest.mark.asyncio
    async def test_event_emission(self, client, mock_cm):
        await client.update_sync_committee(b"\xcc" * 32, 200, VALID_PROOF, VALID_INPUTS)
        evts = await client.get_sync_committee_events(from_block=0)
        assert len(evts) == 1
        assert evts[0]["slot"] == 200

    @pytest.mark.asyncio
    async def test_root_storage(self, client, mock_cm):
        root = b"\xdd" * 32
        await client.update_sync_committee(root, 300, VALID_PROOF, VALID_INPUTS)
        stored = await client.get_sync_committee_root()
        assert stored == root

    @pytest.mark.asyncio
    async def test_slot_storage(self, client, mock_cm):
        await client.update_sync_committee(b"\xee" * 32, 500, VALID_PROOF, VALID_INPUTS)
        slot = await client.get_latest_verified_slot()
        assert slot == 500


# ======================================================================
# 4. Rate limiting tests (8)
# ======================================================================


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_daily_limit_enforcement(self, client, mock_cm):
        mock_cm.daily_limit = 3 * ONE_ETH
        await client.deposit(DID, ONE_ETH)
        await client.deposit(DID, ONE_ETH)
        await client.deposit(DID, ONE_ETH)
        with pytest.raises(RuntimeError, match="daily limit"):
            await client.deposit(DID, ONE_ETH)

    @pytest.mark.asyncio
    async def test_per_tx_limit_blocks(self, client, mock_cm):
        mock_cm.per_tx_limit = 5 * ONE_ETH
        with pytest.raises(RuntimeError, match="per-tx limit"):
            await client.deposit(DID, 6 * ONE_ETH)

    @pytest.mark.asyncio
    async def test_daily_reset(self, client, mock_cm):
        mock_cm.daily_limit = ONE_ETH
        await client.deposit(DID, ONE_ETH)
        mock_cm.last_reset_ts -= mock_cm.DAY_SECONDS + 1
        # After reset, should succeed
        tx = await client.deposit(DID, ONE_ETH)
        assert tx.startswith("0xtx")

    @pytest.mark.asyncio
    async def test_multiple_txs_accumulate(self, client, mock_cm):
        mock_cm.daily_limit = 5 * ONE_ETH
        for _ in range(5):
            await client.deposit(DID, ONE_ETH)
        assert mock_cm.daily_volume == 5 * ONE_ETH
        with pytest.raises(RuntimeError, match="daily limit"):
            await client.deposit(DID, ONE_ETH)

    @pytest.mark.asyncio
    async def test_remaining_limit_calculation(self, client, mock_cm):
        mock_cm.daily_limit = 10 * ONE_ETH
        remaining = await client.get_remaining_daily_limit()
        assert remaining == 10 * ONE_ETH
        await client.deposit(DID, 3 * ONE_ETH)
        remaining = await client.get_remaining_daily_limit()
        assert remaining == 7 * ONE_ETH

    @pytest.mark.asyncio
    async def test_admin_can_update_limits(self, client, mock_cm):
        tx = await client.set_rate_limit(50 * ONE_ETH, 5 * ONE_ETH)
        assert tx.startswith("0xtx")
        assert mock_cm.daily_limit == 50 * ONE_ETH
        assert mock_cm.per_tx_limit == 5 * ONE_ETH

    @pytest.mark.asyncio
    async def test_zero_limits_block_all(self, client, mock_cm):
        await client.set_rate_limit(0, 0)
        with pytest.raises(RuntimeError):
            await client.deposit(DID, 1)

    @pytest.mark.asyncio
    async def test_limits_persist_across_calls(self, client, mock_cm):
        await client.set_rate_limit(20 * ONE_ETH, 20 * ONE_ETH)
        # Deposit should work up to new limits
        await client.deposit(DID, 15 * ONE_ETH)
        remaining = await client.get_remaining_daily_limit()
        assert remaining == 5 * ONE_ETH


# ======================================================================
# 5. Safety tests (8)
# ======================================================================


class TestSafety:
    @pytest.mark.asyncio
    async def test_pause_blocks_deposits(self, client, mock_cm):
        mock_cm.paused = True
        with pytest.raises(RuntimeError, match="paused"):
            await client.deposit(DID, ONE_ETH)

    @pytest.mark.asyncio
    async def test_pause_blocks_withdrawals(self, client, mock_cm):
        mock_cm.paused = True
        with pytest.raises(RuntimeError, match="paused"):
            await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 0, VALID_PROOF, VALID_INPUTS)

    @pytest.mark.asyncio
    async def test_guardian_can_pause(self, client, mock_cm):
        mock_cm.caller = mock_cm.guardian
        tx = await client.pause()
        assert mock_cm.paused is True
        assert tx.startswith("0xtx")

    @pytest.mark.asyncio
    async def test_non_guardian_cannot_pause(self, client, mock_cm):
        mock_cm.caller = "0xRandomUser"
        with pytest.raises(RuntimeError, match="Only guardian"):
            await client.pause()

    @pytest.mark.asyncio
    async def test_admin_can_unpause(self, client, mock_cm):
        mock_cm.paused = True
        mock_cm.caller = mock_cm.admin
        tx = await client.unpause()
        assert mock_cm.paused is False
        assert tx.startswith("0xtx")

    @pytest.mark.asyncio
    async def test_non_admin_cannot_unpause(self, client, mock_cm):
        mock_cm.paused = True
        mock_cm.caller = "0xRandomUser"
        with pytest.raises(RuntimeError, match="Only admin"):
            await client.unpause()

    @pytest.mark.asyncio
    async def test_emergency_pause_blocks_all(self, client, mock_cm):
        """Simulate emergency: pause, then verify both ops fail."""
        mock_cm.caller = mock_cm.guardian
        await client.pause()
        with pytest.raises(RuntimeError, match="paused"):
            await client.deposit(DID, ONE_ETH)
        with pytest.raises(RuntimeError, match="paused"):
            await client.withdraw(RECIPIENT, DID_BYTES, ONE_ETH, 0, VALID_PROOF, VALID_INPUTS)

    @pytest.mark.asyncio
    async def test_pause_unpause_cycle(self, client, mock_cm):
        """Pause → can't deposit → unpause → can deposit."""
        mock_cm.caller = mock_cm.guardian
        await client.pause()
        with pytest.raises(RuntimeError, match="paused"):
            await client.deposit(DID, ONE_ETH)
        mock_cm.caller = mock_cm.admin
        await client.unpause()
        tx = await client.deposit(DID, ONE_ETH)
        assert tx.startswith("0xtx")


# ======================================================================
# 6. Deployer tests (8)
# ======================================================================


VK_PARAMS = {
    "alpha": [1, 2],
    "beta": [[3, 4], [5, 6]],
    "gamma": [[7, 8], [9, 10]],
    "delta": [[11, 12], [13, 14]],
    "ic": [[15, 16]],
}


class TestDeployer:
    @pytest.mark.asyncio
    async def test_deploy_verifier(self, deployer, mock_cm):
        addr = await deployer.deploy_verifier(
            vk_alpha=[1, 2],
            vk_beta=[[3, 4], [5, 6]],
            vk_gamma=[[7, 8], [9, 10]],
            vk_delta=[[11, 12], [13, 14]],
            vk_ic=[[15, 16]],
        )
        assert addr.startswith("0xDeployed")
        assert "Groth16Verifier" in mock_cm.contracts

    @pytest.mark.asyncio
    async def test_deploy_bridge(self, deployer, mock_cm):
        addr = await deployer.deploy_bridge(
            daily_limit=100 * ONE_ETH,
            per_tx_limit=10 * ONE_ETH,
            guardian="0xGuardian",
            verifier_address="0xVerifier",
        )
        assert addr.startswith("0xDeployed")
        assert "RingsBridge" in mock_cm.contracts

    @pytest.mark.asyncio
    async def test_deploy_token(self, deployer, mock_cm):
        addr = await deployer.deploy_bridged_token(
            name="Bridged ASI",
            symbol="bASI",
            bridge_address="0xBridge",
        )
        assert addr.startswith("0xDeployed")
        assert "BridgedToken_bASI" in mock_cm.contracts

    @pytest.mark.asyncio
    async def test_deploy_full_suite(self, deployer, mock_cm):
        result = await deployer.deploy_full_suite(
            daily_limit=100 * ONE_ETH,
            per_tx_limit=10 * ONE_ETH,
            guardian="0xGuardian",
            vk_params=VK_PARAMS,
        )
        assert "verifier" in result
        assert "bridge" in result
        assert "token" in result
        assert len(mock_cm.deployed) == 3

    @pytest.mark.asyncio
    async def test_correct_constructor_args(self, deployer, mock_cm):
        await deployer.deploy_bridge(
            daily_limit=50 * ONE_ETH,
            per_tx_limit=5 * ONE_ETH,
            guardian="0xG",
            verifier_address="0xV",
        )
        bridge_deploy = next(
            d for d in mock_cm.deployed if d["name"] == "RingsBridge"
        )
        args = bridge_deploy["constructor_args"]
        # Constructor: (initialAdmin, guardian, dailyLimit, perTxLimit, verifier)
        assert len(args) == 5
        # args[0] is the auto-resolved admin (MagicMock in tests)
        assert args[1] == "0xG"          # guardian
        assert args[2] == 50 * ONE_ETH   # daily limit
        assert args[3] == 5 * ONE_ETH    # per-tx limit
        assert args[4] == "0xV"          # verifier

    @pytest.mark.asyncio
    async def test_role_granting(self, deployer, mock_cm):
        """deploy_bridged_token sends a grantRole transaction."""
        await deployer.deploy_bridged_token("T", "TT", "0xBridge")
        grant_txs = [
            t for t in mock_cm.sent_transactions if t["fn"] == "grantRole"
        ]
        assert len(grant_txs) == 1
        assert grant_txs[0]["args"][1] == "0xBridge"

    @pytest.mark.asyncio
    async def test_address_returned(self, deployer, mock_cm):
        addr = await deployer.deploy_verifier([0, 0], [[0, 0]], [[0, 0]], [[0, 0]], [[0, 0]])
        assert isinstance(addr, str)
        assert addr.startswith("0x")

    @pytest.mark.asyncio
    async def test_deployment_order(self, deployer, mock_cm):
        """Full suite deploys verifier → bridge → token (in order)."""
        await deployer.deploy_full_suite(
            daily_limit=ONE_ETH,
            per_tx_limit=ONE_ETH,
            guardian="0xG",
            vk_params=VK_PARAMS,
        )
        names = [d["name"] for d in mock_cm.deployed]
        assert names[0] == "Groth16Verifier"
        assert names[1] == "RingsBridge"
        assert names[2].startswith("BridgedToken_")


# ======================================================================
# 7. ABI tests (5)
# ======================================================================


class TestABI:
    def test_abi_structure_validity(self):
        """Every ABI entry has 'name' and 'type'."""
        for entry in BRIDGE_ABI:
            assert "name" in entry
            assert "type" in entry
            assert entry["type"] in ("function", "event")

    def test_function_signatures(self):
        """All expected functions are in the ABI."""
        fn_names = {e["name"] for e in BRIDGE_ABI if e["type"] == "function"}
        expected = {
            "deposit", "depositToken", "withdraw", "withdrawToken",
            "updateSyncCommittee", "emergencyPause", "unpause",
            "updateRateLimits", "getDepositInfo", "getWithdrawalInfo",
            "getRemainingDailyLimit", "latestVerifiedSlot",
            "syncCommitteeRoot", "paused", "depositNonce",
            "withdrawalNonce",
        }
        assert expected.issubset(fn_names)

    def test_event_signatures(self):
        """All expected events are in the ABI."""
        evt_names = {e["name"] for e in BRIDGE_ABI if e["type"] == "event"}
        expected = {
            "Deposited", "Withdrawn", "SyncCommitteeUpdated",
            "Paused", "Unpaused", "EmergencyPaused", "RateLimitUpdated",
        }
        assert expected == evt_names

    def test_all_functions_have_abi_entry(self):
        """Verifier and token ABIs also have entries."""
        assert len(VERIFIER_ABI) >= 1
        assert VERIFIER_ABI[0]["name"] == "verifyProof"
        assert len(TOKEN_ABI) >= 3
        token_fns = {e["name"] for e in TOKEN_ABI}
        assert {"mint", "burn", "grantRole"}.issubset(token_fns)

    def test_deposit_abi_has_payable(self):
        """The deposit function must be payable (accepts msg.value)."""
        deposit_fn = next(
            e for e in BRIDGE_ABI
            if e["name"] == "deposit" and e["type"] == "function"
        )
        assert deposit_fn["stateMutability"] == "payable"
