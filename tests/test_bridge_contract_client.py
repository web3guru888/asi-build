"""Unit tests for BridgeContractClient and BridgeDeployer.

Tests mock the ContractManager and verify correct function names,
arguments, return-value processing, and error handling.
"""

from __future__ import annotations

import dataclasses
import importlib
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Patch web3.middleware so the stale geth_poa_middleware import in
# web3_client.py succeeds even on web3 >= 7.  We only need
# ContractInterface (a plain dataclass) from that module chain.
# ---------------------------------------------------------------------------
import web3.middleware as _mw  # noqa: E402

if not hasattr(_mw, "geth_poa_middleware"):
    _mw.geth_poa_middleware = None  # type: ignore[attr-defined]

from asi_build.rings.bridge.contract_client import (  # noqa: E402
    BRIDGE_ABI,
    TOKEN_ABI,
    VERIFIER_ABI,
    BridgeContractClient,
    BridgeDeployer,
    did_to_bytes32,
)
from asi_build.blockchain.web3_integration.contract_manager import ContractInterface  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BRIDGE_ADDR = "0x" + "ab" * 20
GUARDIAN_ADDR = "0x" + "cc" * 20
TOKEN_ADDR = "0x" + "dd" * 20
RECIPIENT_ADDR = "0x" + "ee" * 20
VERIFIER_ADDR = "0x" + "ff" * 20
TX_HASH = "0x" + "11" * 32


@pytest.fixture()
def mock_cm():
    """Return a mock ContractManager with async methods and a contracts dict."""
    cm = MagicMock()
    cm.contracts = {}
    cm.call_contract_function = AsyncMock()
    cm.send_contract_transaction = AsyncMock(return_value=TX_HASH)
    cm.get_contract_events = AsyncMock(return_value=[])
    cm.deploy_contract = AsyncMock()
    return cm


@pytest.fixture()
def mock_web3():
    return MagicMock()


@pytest.fixture()
def client(mock_web3, mock_cm):
    return BridgeContractClient(mock_web3, mock_cm, BRIDGE_ADDR)


@pytest.fixture()
def deployer(mock_web3, mock_cm):
    return BridgeDeployer(mock_web3, mock_cm)


# ===================================================================
# 1. Client initialisation
# ===================================================================


class TestClientInit:
    def test_stores_references(self, mock_web3, mock_cm):
        c = BridgeContractClient(mock_web3, mock_cm, BRIDGE_ADDR)
        assert c.web3 is mock_web3
        assert c.cm is mock_cm
        assert c.bridge_address == BRIDGE_ADDR

    def test_registers_bridge_in_contract_manager(self, mock_web3, mock_cm):
        assert "RingsBridge" not in mock_cm.contracts
        BridgeContractClient(mock_web3, mock_cm, BRIDGE_ADDR)
        assert "RingsBridge" in mock_cm.contracts

    def test_contract_interface_has_correct_abi(self, mock_web3, mock_cm):
        BridgeContractClient(mock_web3, mock_cm, BRIDGE_ADDR)
        ci = mock_cm.contracts["RingsBridge"]
        assert isinstance(ci, ContractInterface)
        # ABI may be the inline BRIDGE_ABI or compiled ABI from artifacts
        assert len(ci.abi) > 0
        assert ci.address == BRIDGE_ADDR
        assert ci.name == "RingsBridge"

    def test_repr(self, client):
        assert BRIDGE_ADDR in repr(client)


# ===================================================================
# 2. Deposit operations
# ===================================================================


class TestDeposit:
    @pytest.mark.asyncio
    async def test_deposit_sends_correct_function_and_args(self, client, mock_cm):
        await client.deposit("did:rings:ed25519:abc", 10**18)
        mock_cm.send_contract_transaction.assert_awaited_once_with(
            "RingsBridge", "deposit",
            args=[did_to_bytes32("did:rings:ed25519:abc")],
            value=10**18,
        )

    @pytest.mark.asyncio
    async def test_deposit_sends_value(self, client, mock_cm):
        await client.deposit("did:rings:test", 42)
        _, kwargs = mock_cm.send_contract_transaction.call_args
        assert kwargs["value"] == 42

    @pytest.mark.asyncio
    async def test_deposit_token_sends_correct_args(self, client, mock_cm):
        await client.deposit_token(TOKEN_ADDR, 500, "did:rings:xyz")
        mock_cm.send_contract_transaction.assert_awaited_once_with(
            "RingsBridge", "depositToken",
            args=[TOKEN_ADDR, 500, did_to_bytes32("did:rings:xyz")],
            value=0,
        )

    @pytest.mark.asyncio
    async def test_deposit_returns_tx_hash(self, client):
        result = await client.deposit("did:rings:a", 1)
        assert result == TX_HASH

    @pytest.mark.asyncio
    async def test_deposit_token_returns_tx_hash(self, client):
        result = await client.deposit_token(TOKEN_ADDR, 1, "did:rings:a")
        assert result == TX_HASH


# ===================================================================
# 3. Withdrawal operations
# ===================================================================


class TestWithdraw:
    PROOF = b"\xde\xad" * 128  # 256 bytes
    INPUTS = [1, 2, 3]
    DID_BYTES = did_to_bytes32("did:rings:ed25519:test")

    @pytest.mark.asyncio
    async def test_withdraw_sends_correct_args(self, client, mock_cm):
        await client.withdraw(RECIPIENT_ADDR, self.DID_BYTES, 10**18, 7, self.PROOF, self.INPUTS)
        mock_cm.send_contract_transaction.assert_awaited_once_with(
            "RingsBridge", "withdraw",
            args=[RECIPIENT_ADDR, self.DID_BYTES, 10**18, 7, self.PROOF, self.INPUTS],
            value=0,
        )

    @pytest.mark.asyncio
    async def test_withdraw_token_sends_all_seven_args(self, client, mock_cm):
        await client.withdraw_token(
            TOKEN_ADDR, RECIPIENT_ADDR, self.DID_BYTES, 200, 3, self.PROOF, self.INPUTS,
        )
        mock_cm.send_contract_transaction.assert_awaited_once_with(
            "RingsBridge", "withdrawToken",
            args=[TOKEN_ADDR, RECIPIENT_ADDR, self.DID_BYTES, 200, 3, self.PROOF, self.INPUTS],
            value=0,
        )

    @pytest.mark.asyncio
    async def test_withdraw_returns_tx_hash(self, client):
        result = await client.withdraw(RECIPIENT_ADDR, self.DID_BYTES, 1, 0, b"", [])
        assert result == TX_HASH

    @pytest.mark.asyncio
    async def test_proof_bytes_passed_through(self, client, mock_cm):
        proof = b"\x01\x02\x03"
        await client.withdraw(RECIPIENT_ADDR, self.DID_BYTES, 1, 0, proof, [])
        args_list = mock_cm.send_contract_transaction.call_args[1]["args"]
        assert args_list[4] is proof

    @pytest.mark.asyncio
    async def test_public_inputs_passed_as_list(self, client, mock_cm):
        inputs = [10, 20, 30, 40]
        await client.withdraw(RECIPIENT_ADDR, self.DID_BYTES, 1, 0, b"", inputs)
        args_list = mock_cm.send_contract_transaction.call_args[1]["args"]
        assert args_list[5] == [10, 20, 30, 40]


# ===================================================================
# 4. Sync committee
# ===================================================================


class TestSyncCommittee:
    ROOT = b"\xaa" * 32
    PROOF = b"\xbb" * 256

    @pytest.mark.asyncio
    async def test_update_sends_correct_args(self, client, mock_cm):
        await client.update_sync_committee(self.ROOT, 999, self.PROOF, [5, 6])
        mock_cm.send_contract_transaction.assert_awaited_once_with(
            "RingsBridge", "updateSyncCommittee",
            args=[self.ROOT, 999, self.PROOF, [5, 6]],
            value=0,
        )

    @pytest.mark.asyncio
    async def test_new_root_bytes_passed(self, client, mock_cm):
        await client.update_sync_committee(self.ROOT, 0, b"", [])
        args_list = mock_cm.send_contract_transaction.call_args[1]["args"]
        assert args_list[0] is self.ROOT

    @pytest.mark.asyncio
    async def test_slot_value_passed(self, client, mock_cm):
        await client.update_sync_committee(b"\x00" * 32, 12345, b"", [])
        args_list = mock_cm.send_contract_transaction.call_args[1]["args"]
        assert args_list[1] == 12345


# ===================================================================
# 5. View functions
# ===================================================================


class TestViewFunctions:
    @pytest.mark.asyncio
    async def test_get_deposit_info_parses_tuple(self, client, mock_cm):
        did_bytes = did_to_bytes32("did:rings:test")
        mock_cm.call_contract_function.return_value = (
            "0xsender", did_bytes, 100, "0xToken", 42, 1,
        )
        info = await client.get_deposit_info(1)
        assert info == {
            "depositor": "0xsender",
            "ringsDID": did_bytes,
            "amount": 100,
            "token": "0xToken",
            "timestamp": 42,
            "nonce": 1,
        }

    @pytest.mark.asyncio
    async def test_get_deposit_info_handles_dict_return(self, client, mock_cm):
        expected = {
            "depositor": "0x1", "ringsDID": b"\x00" * 32,
            "amount": 1, "token": "0x0", "timestamp": 2, "nonce": 0,
        }
        mock_cm.call_contract_function.return_value = expected
        info = await client.get_deposit_info(0)
        assert info is expected

    @pytest.mark.asyncio
    async def test_get_withdrawal_info_parses_tuple(self, client, mock_cm):
        did_bytes = did_to_bytes32("did:rings:recip")
        mock_cm.call_contract_function.return_value = (
            "0xrecip", did_bytes, 500, "0xToken", 99, 3,
        )
        info = await client.get_withdrawal_info(3)
        assert info == {
            "recipient": "0xrecip",
            "ringsDID": did_bytes,
            "amount": 500,
            "token": "0xToken",
            "timestamp": 99,
            "nonce": 3,
        }

    @pytest.mark.asyncio
    async def test_get_remaining_daily_limit(self, client, mock_cm):
        mock_cm.call_contract_function.return_value = 10**20
        result = await client.get_remaining_daily_limit()
        assert result == 10**20
        mock_cm.call_contract_function.assert_awaited_with(
            "RingsBridge", "getRemainingDailyLimit", args=[],
        )

    @pytest.mark.asyncio
    async def test_get_latest_verified_slot(self, client, mock_cm):
        mock_cm.call_contract_function.return_value = 8192
        result = await client.get_latest_verified_slot()
        assert result == 8192
        mock_cm.call_contract_function.assert_awaited_with(
            "RingsBridge", "latestVerifiedSlot", args=[],
        )

    @pytest.mark.asyncio
    async def test_get_sync_committee_root_hex_string(self, client, mock_cm):
        hex_root = "0x" + "ab" * 32
        mock_cm.call_contract_function.return_value = hex_root
        result = await client.get_sync_committee_root()
        assert isinstance(result, bytes)
        assert result == bytes.fromhex("ab" * 32)
        assert len(result) == 32

    @pytest.mark.asyncio
    async def test_get_sync_committee_root_bytes_passthrough(self, client, mock_cm):
        raw = b"\xcd" * 32
        mock_cm.call_contract_function.return_value = raw
        result = await client.get_sync_committee_root()
        assert result is raw

    @pytest.mark.asyncio
    async def test_is_paused(self, client, mock_cm):
        mock_cm.call_contract_function.return_value = True
        assert await client.is_paused() is True
        mock_cm.call_contract_function.assert_awaited_with(
            "RingsBridge", "paused", args=[],
        )

    @pytest.mark.asyncio
    async def test_get_deposit_nonce(self, client, mock_cm):
        mock_cm.call_contract_function.return_value = 17
        assert await client.get_deposit_nonce() == 17

    @pytest.mark.asyncio
    async def test_get_withdrawal_nonce(self, client, mock_cm):
        mock_cm.call_contract_function.return_value = 5
        assert await client.get_withdrawal_nonce() == 5


# ===================================================================
# 6. Event fetching
# ===================================================================


class TestEventFetching:
    @pytest.mark.asyncio
    async def test_get_deposit_events_calls_correct_name(self, client, mock_cm):
        await client.get_deposit_events(100)
        mock_cm.get_contract_events.assert_awaited_once_with(
            "RingsBridge", "Deposited", from_block=100, to_block="latest",
        )

    @pytest.mark.asyncio
    async def test_get_withdrawal_events_calls_correct_name(self, client, mock_cm):
        await client.get_withdrawal_events(0)
        mock_cm.get_contract_events.assert_awaited_once_with(
            "RingsBridge", "Withdrawn", from_block=0, to_block="latest",
        )

    @pytest.mark.asyncio
    async def test_get_sync_committee_events_calls_correct_name(self, client, mock_cm):
        await client.get_sync_committee_events(50)
        mock_cm.get_contract_events.assert_awaited_once_with(
            "RingsBridge", "SyncCommitteeUpdated", from_block=50, to_block="latest",
        )

    @pytest.mark.asyncio
    async def test_from_and_to_block_passed(self, client, mock_cm):
        await client.get_deposit_events(10, to_block=20)
        mock_cm.get_contract_events.assert_awaited_once_with(
            "RingsBridge", "Deposited", from_block=10, to_block=20,
        )

    @pytest.mark.asyncio
    async def test_to_block_defaults_to_latest_when_none(self, client, mock_cm):
        await client.get_withdrawal_events(0, to_block=None)
        mock_cm.get_contract_events.assert_awaited_once_with(
            "RingsBridge", "Withdrawn", from_block=0, to_block="latest",
        )


# ===================================================================
# 7. Admin operations
# ===================================================================


class TestAdmin:
    @pytest.mark.asyncio
    async def test_pause(self, client, mock_cm):
        result = await client.pause()
        assert result == TX_HASH
        mock_cm.send_contract_transaction.assert_awaited_once_with(
            "RingsBridge", "emergencyPause", args=[], value=0,
        )

    @pytest.mark.asyncio
    async def test_unpause(self, client, mock_cm):
        result = await client.unpause()
        assert result == TX_HASH
        mock_cm.send_contract_transaction.assert_awaited_once_with(
            "RingsBridge", "unpause", args=[], value=0,
        )

    @pytest.mark.asyncio
    async def test_set_rate_limit(self, client, mock_cm):
        result = await client.set_rate_limit(10**20, 10**18)
        assert result == TX_HASH
        mock_cm.send_contract_transaction.assert_awaited_once_with(
            "RingsBridge", "updateRateLimits",
            args=[10**20, 10**18],
            value=0,
        )

    @pytest.mark.asyncio
    async def test_admin_ops_return_tx_hash(self, client, mock_cm):
        mock_cm.send_contract_transaction.return_value = "0xadmin_tx"
        for coro in [client.pause(), client.unpause()]:
            result = await coro
            assert result == "0xadmin_tx"


# ===================================================================
# 8. Deployer tests
# ===================================================================


class TestDeployer:
    VK = {
        "alpha": [1, 2],
        "beta": [[3, 4], [5, 6]],
        "gamma": [[7, 8], [9, 10]],
        "delta": [[11, 12], [13, 14]],
        "ic": [[15, 16]],
    }

    def _make_ci(self, name: str, address: str) -> ContractInterface:
        return ContractInterface(name=name, address=address, abi=[])

    @pytest.mark.asyncio
    async def test_deploy_verifier(self, deployer, mock_cm):
        mock_cm.deploy_contract.return_value = self._make_ci("Groth16Verifier", VERIFIER_ADDR)
        addr = await deployer.deploy_verifier(
            self.VK["alpha"], self.VK["beta"],
            self.VK["gamma"], self.VK["delta"], self.VK["ic"],
        )
        assert addr == VERIFIER_ADDR
        mock_cm.deploy_contract.assert_awaited_once()
        call_kwargs = mock_cm.deploy_contract.call_args[1]
        assert call_kwargs["contract_name"] == "Groth16Verifier"
        assert len(call_kwargs["abi"]) > 0  # compiled or inline ABI
        assert call_kwargs["constructor_args"] == [
            self.VK["alpha"], self.VK["beta"],
            self.VK["gamma"], self.VK["delta"], self.VK["ic"],
        ]

    @pytest.mark.asyncio
    async def test_deploy_bridge(self, deployer, mock_cm):
        mock_cm.deploy_contract.return_value = self._make_ci("RingsBridge", BRIDGE_ADDR)
        addr = await deployer.deploy_bridge(10**20, 10**18, GUARDIAN_ADDR, VERIFIER_ADDR)
        assert addr == BRIDGE_ADDR
        call_kwargs = mock_cm.deploy_contract.call_args[1]
        assert call_kwargs["contract_name"] == "RingsBridge"
        assert len(call_kwargs["abi"]) > 0  # compiled or inline ABI
        # Constructor: (initialAdmin, guardian, dailyLimit, perTxLimit, verifier)
        args = call_kwargs["constructor_args"]
        assert args[1] == GUARDIAN_ADDR   # guardian
        assert args[2] == 10**20          # daily limit
        assert args[3] == 10**18          # per-tx limit
        assert args[4] == VERIFIER_ADDR   # verifier

    @pytest.mark.asyncio
    async def test_deploy_bridged_token_deploys_and_grants_role(self, deployer, mock_cm):
        mock_cm.deploy_contract.return_value = self._make_ci("BridgedToken_bASI", TOKEN_ADDR)
        addr = await deployer.deploy_bridged_token("Bridged ASI", "bASI", BRIDGE_ADDR)
        assert addr == TOKEN_ADDR
        # deploy was called
        call_kwargs = mock_cm.deploy_contract.call_args[1]
        assert call_kwargs["contract_name"] == "BridgedToken_bASI"
        assert call_kwargs["constructor_args"] == ["Bridged ASI", "bASI"]
        # grantRole was called
        mock_cm.send_contract_transaction.assert_awaited_once()
        grant_args = mock_cm.send_contract_transaction.call_args
        assert grant_args[0][0] == "BridgedToken_bASI"
        assert grant_args[0][1] == "grantRole"

    @pytest.mark.asyncio
    async def test_deploy_full_suite_calls_all_three(self, deployer, mock_cm):
        mock_cm.deploy_contract.side_effect = [
            self._make_ci("Groth16Verifier", VERIFIER_ADDR),
            self._make_ci("RingsBridge", BRIDGE_ADDR),
            self._make_ci("BridgedToken_bASI", TOKEN_ADDR),
        ]
        result = await deployer.deploy_full_suite(
            daily_limit=10**20, per_tx_limit=10**18,
            guardian=GUARDIAN_ADDR, vk_params=self.VK,
        )
        assert mock_cm.deploy_contract.await_count == 3

    @pytest.mark.asyncio
    async def test_deploy_full_suite_returns_address_dict(self, deployer, mock_cm):
        mock_cm.deploy_contract.side_effect = [
            self._make_ci("Groth16Verifier", VERIFIER_ADDR),
            self._make_ci("RingsBridge", BRIDGE_ADDR),
            self._make_ci("BridgedToken_bASI", TOKEN_ADDR),
        ]
        result = await deployer.deploy_full_suite(
            daily_limit=10**20, per_tx_limit=10**18,
            guardian=GUARDIAN_ADDR, vk_params=self.VK,
        )
        assert result == {
            "verifier": VERIFIER_ADDR,
            "bridge": BRIDGE_ADDR,
            "token": TOKEN_ADDR,
        }

    @pytest.mark.asyncio
    async def test_deploy_bridged_token_grants_bridge_role_hash(self, deployer, mock_cm):
        mock_cm.deploy_contract.return_value = self._make_ci("BridgedToken_bASI", TOKEN_ADDR)
        await deployer.deploy_bridged_token("Bridged ASI", "bASI", BRIDGE_ADDR)
        grant_kwargs = mock_cm.send_contract_transaction.call_args[1]
        role_bytes = grant_kwargs["args"][0]
        # keccak256("BRIDGE_ROLE") = 0x52ba824b...
        assert role_bytes == bytes.fromhex(
            "52ba824bfabc2bcfcdf7f0edbb486ebb05e1836c90e78047efeb949990f72e5f"
        )
        assert grant_kwargs["args"][1] == BRIDGE_ADDR


# ===================================================================
# 9. ABI validation
# ===================================================================


class TestABIValidation:
    def test_bridge_abi_has_all_expected_functions(self):
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

    def test_verifier_abi_has_verify(self):
        fn_names = {e["name"] for e in VERIFIER_ABI if e["type"] == "function"}
        assert "verifyProof" in fn_names

    def test_token_abi_has_mint_and_burn(self):
        fn_names = {e["name"] for e in TOKEN_ABI if e["type"] == "function"}
        assert "mint" in fn_names
        assert "burn" in fn_names
        assert "grantRole" in fn_names
