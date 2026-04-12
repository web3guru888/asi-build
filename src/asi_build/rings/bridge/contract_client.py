"""
Bridge Contract Client & Deployer
===================================

Python client for interacting with deployed ``RingsBridge.sol`` and
related contracts (``Groth16Verifier``, ``BridgedToken``).  Also
provides :class:`BridgeDeployer` for deterministic deployment of the
full bridge contract suite.

The ABI fragments are defined inline so we don't need Solidity
compilation tooling at import time.  Each fragment describes exactly
one function or event, matching the on-chain ABI encoding.

Typical usage::

    from asi_build.rings.bridge.contract_client import (
        BridgeContractClient,
        BridgeDeployer,
    )

    deployer = BridgeDeployer(web3_client, contract_manager)
    addrs = await deployer.deploy_full_suite(
        daily_limit=100 * 10**18,
        per_tx_limit=10 * 10**18,
        guardian="0x...",
        vk_params=verifier_keys,
    )

    client = BridgeContractClient(
        web3_client=web3_client,
        contract_manager=contract_manager,
        bridge_address=addrs["bridge"],
    )
    tx = await client.deposit(rings_did="did:rings:ed25519:abc", amount_wei=10**18)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ABI fragments — inline so we skip Solidity compilation
# ---------------------------------------------------------------------------

# Each fragment is a single ABI entry (function or event).  We group them
# by contract for clarity, then compose them into full ABIs at the bottom.

# ── RingsBridge.sol ──────────────────────────────────────────────────────

_BRIDGE_DEPOSIT_FN = {
    "name": "deposit",
    "type": "function",
    "stateMutability": "payable",
    "inputs": [{"name": "ringsDid", "type": "string"}],
    "outputs": [],
}

_BRIDGE_DEPOSIT_TOKEN_FN = {
    "name": "depositToken",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "token", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "ringsDid", "type": "string"},
    ],
    "outputs": [],
}

_BRIDGE_WITHDRAW_FN = {
    "name": "withdraw",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "recipient", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "proof", "type": "bytes"},
        {"name": "publicInputs", "type": "uint256[]"},
    ],
    "outputs": [],
}

_BRIDGE_WITHDRAW_TOKEN_FN = {
    "name": "withdrawToken",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "token", "type": "address"},
        {"name": "recipient", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "proof", "type": "bytes"},
        {"name": "publicInputs", "type": "uint256[]"},
    ],
    "outputs": [],
}

_BRIDGE_UPDATE_SYNC_COMMITTEE_FN = {
    "name": "updateSyncCommittee",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "newRoot", "type": "bytes32"},
        {"name": "slot", "type": "uint256"},
        {"name": "proof", "type": "bytes"},
        {"name": "publicInputs", "type": "uint256[]"},
    ],
    "outputs": [],
}

_BRIDGE_PAUSE_FN = {
    "name": "pause",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [],
    "outputs": [],
}

_BRIDGE_UNPAUSE_FN = {
    "name": "unpause",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [],
    "outputs": [],
}

_BRIDGE_SET_RATE_LIMIT_FN = {
    "name": "setRateLimit",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "dailyLimit", "type": "uint256"},
        {"name": "perTxLimit", "type": "uint256"},
    ],
    "outputs": [],
}

# ── RingsBridge view functions ───────────────────────────────────────────

_BRIDGE_GET_DEPOSIT_INFO_FN = {
    "name": "getDepositInfo",
    "type": "function",
    "stateMutability": "view",
    "inputs": [{"name": "nonce", "type": "uint256"}],
    "outputs": [
        {"name": "sender", "type": "address"},
        {"name": "ringsDid", "type": "string"},
        {"name": "amount", "type": "uint256"},
        {"name": "blockNum", "type": "uint256"},
        {"name": "processed", "type": "bool"},
    ],
}

_BRIDGE_GET_WITHDRAWAL_INFO_FN = {
    "name": "getWithdrawalInfo",
    "type": "function",
    "stateMutability": "view",
    "inputs": [{"name": "nonce", "type": "uint256"}],
    "outputs": [
        {"name": "recipient", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "executed", "type": "bool"},
    ],
}

_BRIDGE_REMAINING_DAILY_LIMIT_FN = {
    "name": "remainingDailyLimit",
    "type": "function",
    "stateMutability": "view",
    "inputs": [],
    "outputs": [{"name": "", "type": "uint256"}],
}

_BRIDGE_LATEST_VERIFIED_SLOT_FN = {
    "name": "latestVerifiedSlot",
    "type": "function",
    "stateMutability": "view",
    "inputs": [],
    "outputs": [{"name": "", "type": "uint256"}],
}

_BRIDGE_SYNC_COMMITTEE_ROOT_FN = {
    "name": "syncCommitteeRoot",
    "type": "function",
    "stateMutability": "view",
    "inputs": [],
    "outputs": [{"name": "", "type": "bytes32"}],
}

_BRIDGE_PAUSED_FN = {
    "name": "paused",
    "type": "function",
    "stateMutability": "view",
    "inputs": [],
    "outputs": [{"name": "", "type": "bool"}],
}

_BRIDGE_DEPOSIT_NONCE_FN = {
    "name": "depositNonce",
    "type": "function",
    "stateMutability": "view",
    "inputs": [],
    "outputs": [{"name": "", "type": "uint256"}],
}

_BRIDGE_WITHDRAWAL_NONCE_FN = {
    "name": "withdrawalNonce",
    "type": "function",
    "stateMutability": "view",
    "inputs": [],
    "outputs": [{"name": "", "type": "uint256"}],
}

# ── RingsBridge events ───────────────────────────────────────────────────

_BRIDGE_DEPOSITED_EVT = {
    "name": "Deposited",
    "type": "event",
    "inputs": [
        {"name": "nonce", "type": "uint256", "indexed": True},
        {"name": "sender", "type": "address", "indexed": True},
        {"name": "ringsDid", "type": "string", "indexed": False},
        {"name": "amount", "type": "uint256", "indexed": False},
    ],
}

_BRIDGE_WITHDRAWN_EVT = {
    "name": "Withdrawn",
    "type": "event",
    "inputs": [
        {"name": "nonce", "type": "uint256", "indexed": True},
        {"name": "recipient", "type": "address", "indexed": True},
        {"name": "amount", "type": "uint256", "indexed": False},
    ],
}

_BRIDGE_SYNC_COMMITTEE_UPDATED_EVT = {
    "name": "SyncCommitteeUpdated",
    "type": "event",
    "inputs": [
        {"name": "slot", "type": "uint256", "indexed": True},
        {"name": "newRoot", "type": "bytes32", "indexed": False},
    ],
}

_BRIDGE_PAUSED_EVT = {
    "name": "Paused",
    "type": "event",
    "inputs": [{"name": "account", "type": "address", "indexed": False}],
}

_BRIDGE_UNPAUSED_EVT = {
    "name": "Unpaused",
    "type": "event",
    "inputs": [{"name": "account", "type": "address", "indexed": False}],
}

# ── Groth16Verifier.sol ──────────────────────────────────────────────────

_VERIFIER_VERIFY_FN = {
    "name": "verifyProof",
    "type": "function",
    "stateMutability": "view",
    "inputs": [
        {"name": "a", "type": "uint256[2]"},
        {"name": "b", "type": "uint256[2][2]"},
        {"name": "c", "type": "uint256[2]"},
        {"name": "input", "type": "uint256[]"},
    ],
    "outputs": [{"name": "", "type": "bool"}],
}

# ── BridgedToken.sol ─────────────────────────────────────────────────────

_TOKEN_MINT_FN = {
    "name": "mint",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "to", "type": "address"},
        {"name": "amount", "type": "uint256"},
    ],
    "outputs": [],
}

_TOKEN_BURN_FN = {
    "name": "burn",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "from", "type": "address"},
        {"name": "amount", "type": "uint256"},
    ],
    "outputs": [],
}

_TOKEN_GRANT_ROLE_FN = {
    "name": "grantRole",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "role", "type": "bytes32"},
        {"name": "account", "type": "address"},
    ],
    "outputs": [],
}

# ── Composed ABIs ────────────────────────────────────────────────────────

BRIDGE_ABI: List[Dict[str, Any]] = [
    _BRIDGE_DEPOSIT_FN,
    _BRIDGE_DEPOSIT_TOKEN_FN,
    _BRIDGE_WITHDRAW_FN,
    _BRIDGE_WITHDRAW_TOKEN_FN,
    _BRIDGE_UPDATE_SYNC_COMMITTEE_FN,
    _BRIDGE_PAUSE_FN,
    _BRIDGE_UNPAUSE_FN,
    _BRIDGE_SET_RATE_LIMIT_FN,
    _BRIDGE_GET_DEPOSIT_INFO_FN,
    _BRIDGE_GET_WITHDRAWAL_INFO_FN,
    _BRIDGE_REMAINING_DAILY_LIMIT_FN,
    _BRIDGE_LATEST_VERIFIED_SLOT_FN,
    _BRIDGE_SYNC_COMMITTEE_ROOT_FN,
    _BRIDGE_PAUSED_FN,
    _BRIDGE_DEPOSIT_NONCE_FN,
    _BRIDGE_WITHDRAWAL_NONCE_FN,
    _BRIDGE_DEPOSITED_EVT,
    _BRIDGE_WITHDRAWN_EVT,
    _BRIDGE_SYNC_COMMITTEE_UPDATED_EVT,
    _BRIDGE_PAUSED_EVT,
    _BRIDGE_UNPAUSED_EVT,
]

VERIFIER_ABI: List[Dict[str, Any]] = [_VERIFIER_VERIFY_FN]

TOKEN_ABI: List[Dict[str, Any]] = [
    _TOKEN_MINT_FN,
    _TOKEN_BURN_FN,
    _TOKEN_GRANT_ROLE_FN,
]


# ---------------------------------------------------------------------------
# BridgeContractClient
# ---------------------------------------------------------------------------


class BridgeContractClient:
    """Python client for interacting with a deployed ``RingsBridge.sol``.

    Wraps the project's existing :class:`Web3Client` and
    :class:`ContractManager` to provide bridge-specific high-level
    methods for deposits, withdrawals, sync-committee updates, event
    fetching, and admin operations.

    Parameters
    ----------
    web3_client : Web3Client
        A connected :class:`~asi_build.blockchain.web3_integration.Web3Client`.
    contract_manager : ContractManager
        A :class:`~asi_build.blockchain.web3_integration.ContractManager`
        that has the bridge contract registered (or we register it here).
    bridge_address : str
        The ``0x``-prefixed address of the deployed ``RingsBridge`` contract.
    """

    CONTRACT_NAME = "RingsBridge"

    def __init__(
        self,
        web3_client: Any,
        contract_manager: Any,
        bridge_address: str,
    ) -> None:
        self.web3 = web3_client
        self.cm = contract_manager
        self.bridge_address = bridge_address

        # Register the bridge in ContractManager if not already present
        from asi_build.blockchain.web3_integration.contract_manager import (
            ContractInterface,
        )

        if not self.cm.contracts.get(self.CONTRACT_NAME):
            ci = ContractInterface(
                name=self.CONTRACT_NAME,
                address=bridge_address,
                abi=BRIDGE_ABI,
            )
            self.cm.contracts[self.CONTRACT_NAME] = ci

    # ── helpers ──────────────────────────────────────────────────────────

    async def _call(self, fn: str, args: Optional[list] = None) -> Any:
        """Read-only contract call."""
        return await self.cm.call_contract_function(
            self.CONTRACT_NAME, fn, args=args or [],
        )

    async def _send(
        self,
        fn: str,
        args: Optional[list] = None,
        value: int = 0,
    ) -> str:
        """State-changing contract transaction.  Returns tx hash."""
        return await self.cm.send_contract_transaction(
            self.CONTRACT_NAME, fn, args=args or [], value=value,
        )

    async def _events(
        self,
        event_name: str,
        from_block: int,
        to_block: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch filtered contract events."""
        return await self.cm.get_contract_events(
            self.CONTRACT_NAME,
            event_name,
            from_block=from_block,
            to_block=to_block if to_block is not None else "latest",
        )

    # ── Deposit operations ───────────────────────────────────────────────

    async def deposit(self, rings_did: str, amount_wei: int) -> str:
        """Deposit native ETH into the bridge.

        Parameters
        ----------
        rings_did : str
            The Rings DID that should be credited.
        amount_wei : int
            Amount to deposit in wei (sent as ``msg.value``).

        Returns
        -------
        str
            Transaction hash.
        """
        logger.info("Depositing %d wei for %s", amount_wei, rings_did)
        return await self._send("deposit", [rings_did], value=amount_wei)

    async def deposit_token(
        self,
        token_address: str,
        amount: int,
        rings_did: str,
    ) -> str:
        """Deposit an ERC-20 token into the bridge.

        The caller must have previously approved the bridge contract to
        spend at least *amount* of the token.

        Parameters
        ----------
        token_address : str
            ERC-20 token contract address.
        amount : int
            Token amount (smallest unit).
        rings_did : str
            The Rings DID that should be credited.

        Returns
        -------
        str
            Transaction hash.
        """
        logger.info(
            "Depositing %d of token %s for %s",
            amount, token_address, rings_did,
        )
        return await self._send("depositToken", [token_address, amount, rings_did])

    # ── Withdrawal operations ────────────────────────────────────────────

    async def withdraw(
        self,
        recipient: str,
        amount: int,
        nonce: int,
        proof: bytes,
        public_inputs: List[int],
    ) -> str:
        """Submit a native-ETH withdrawal with ZK proof.

        Parameters
        ----------
        recipient : str
            Ethereum address to receive the ETH.
        amount : int
            Amount in wei.
        nonce : int
            Monotonic withdrawal nonce.
        proof : bytes
            Serialized Groth16 proof (A||B||C, 256 bytes).
        public_inputs : list of int
            Public inputs for the verifier circuit.

        Returns
        -------
        str
            Transaction hash.
        """
        logger.info(
            "Withdrawing %d wei to %s (nonce=%d)", amount, recipient, nonce,
        )
        return await self._send(
            "withdraw", [recipient, amount, nonce, proof, public_inputs],
        )

    async def withdraw_token(
        self,
        token_address: str,
        recipient: str,
        amount: int,
        nonce: int,
        proof: bytes,
        public_inputs: List[int],
    ) -> str:
        """Submit an ERC-20 withdrawal with ZK proof.

        Parameters
        ----------
        token_address : str
            ERC-20 token contract address.
        recipient : str
            Ethereum address to receive the tokens.
        amount : int
            Token amount (smallest unit).
        nonce : int
            Monotonic withdrawal nonce.
        proof : bytes
            Serialized Groth16 proof.
        public_inputs : list of int
            Public inputs for the verifier circuit.

        Returns
        -------
        str
            Transaction hash.
        """
        logger.info(
            "Withdrawing %d of token %s to %s (nonce=%d)",
            amount, token_address, recipient, nonce,
        )
        return await self._send(
            "withdrawToken",
            [token_address, recipient, amount, nonce, proof, public_inputs],
        )

    # ── Sync committee ───────────────────────────────────────────────────

    async def update_sync_committee(
        self,
        new_root: bytes,
        slot: int,
        proof: bytes,
        public_inputs: List[int],
    ) -> str:
        """Submit a sync-committee rotation proof on-chain.

        Parameters
        ----------
        new_root : bytes
            The new 32-byte sync committee root (Poseidon hash of pubkeys).
        slot : int
            Beacon slot at which the new committee takes effect.
        proof : bytes
            Serialized Groth16 proof of committee validity.
        public_inputs : list of int
            Public inputs for the verifier circuit.

        Returns
        -------
        str
            Transaction hash.
        """
        logger.info("Updating sync committee at slot %d", slot)
        return await self._send(
            "updateSyncCommittee", [new_root, slot, proof, public_inputs],
        )

    # ── Query (view) functions ───────────────────────────────────────────

    async def get_deposit_info(self, nonce: int) -> Dict[str, Any]:
        """Fetch on-chain deposit info by nonce.

        Returns
        -------
        dict
            Keys: ``sender``, ``ringsDid``, ``amount``, ``blockNum``,
            ``processed``.
        """
        result = await self._call("getDepositInfo", [nonce])
        # ContractManager returns a tuple — map to names
        if isinstance(result, (tuple, list)):
            return {
                "sender": result[0],
                "ringsDid": result[1],
                "amount": result[2],
                "blockNum": result[3],
                "processed": result[4],
            }
        return result  # already a dict if web3 decoded it

    async def get_withdrawal_info(self, nonce: int) -> Dict[str, Any]:
        """Fetch on-chain withdrawal info by nonce.

        Returns
        -------
        dict
            Keys: ``recipient``, ``amount``, ``executed``.
        """
        result = await self._call("getWithdrawalInfo", [nonce])
        if isinstance(result, (tuple, list)):
            return {
                "recipient": result[0],
                "amount": result[1],
                "executed": result[2],
            }
        return result

    async def get_remaining_daily_limit(self) -> int:
        """Return the remaining daily bridge throughput limit (wei)."""
        return await self._call("remainingDailyLimit")

    async def get_latest_verified_slot(self) -> int:
        """Return the latest verified Beacon slot number."""
        return await self._call("latestVerifiedSlot")

    async def get_sync_committee_root(self) -> bytes:
        """Return the current on-chain sync committee root (32 bytes)."""
        result = await self._call("syncCommitteeRoot")
        if isinstance(result, str):
            # Hex-encoded — strip 0x and decode
            return bytes.fromhex(result.replace("0x", ""))
        return bytes(result) if not isinstance(result, bytes) else result

    async def is_paused(self) -> bool:
        """Whether the bridge contract is currently paused."""
        return await self._call("paused")

    async def get_deposit_nonce(self) -> int:
        """Return the current (next) deposit nonce."""
        return await self._call("depositNonce")

    async def get_withdrawal_nonce(self) -> int:
        """Return the current (next) withdrawal nonce."""
        return await self._call("withdrawalNonce")

    # ── Event fetching ───────────────────────────────────────────────────

    async def get_deposit_events(
        self, from_block: int, to_block: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch ``Deposited`` events in a block range.

        Each event dict contains ``nonce``, ``sender``, ``ringsDid``,
        ``amount``, ``blockNumber``, and ``transactionHash``.
        """
        return await self._events("Deposited", from_block, to_block)

    async def get_withdrawal_events(
        self, from_block: int, to_block: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch ``Withdrawn`` events in a block range."""
        return await self._events("Withdrawn", from_block, to_block)

    async def get_sync_committee_events(
        self, from_block: int, to_block: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch ``SyncCommitteeUpdated`` events in a block range."""
        return await self._events("SyncCommitteeUpdated", from_block, to_block)

    # ── Admin operations ─────────────────────────────────────────────────

    async def pause(self) -> str:
        """Pause the bridge contract (guardian only).  Returns tx hash."""
        logger.warning("Pausing bridge contract at %s", self.bridge_address)
        return await self._send("pause")

    async def unpause(self) -> str:
        """Unpause the bridge contract (guardian only).  Returns tx hash."""
        logger.info("Unpausing bridge contract at %s", self.bridge_address)
        return await self._send("unpause")

    async def set_rate_limit(self, daily_limit: int, per_tx_limit: int) -> str:
        """Update rate-limiting parameters.

        Parameters
        ----------
        daily_limit : int
            Maximum total wei that can flow through the bridge per day.
        per_tx_limit : int
            Maximum wei per single transaction.

        Returns
        -------
        str
            Transaction hash.
        """
        logger.info(
            "Setting rate limits: daily=%d, per_tx=%d",
            daily_limit, per_tx_limit,
        )
        return await self._send("setRateLimit", [daily_limit, per_tx_limit])

    # ── repr ─────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"BridgeContractClient(bridge={self.bridge_address})"


# ---------------------------------------------------------------------------
# BridgeDeployer
# ---------------------------------------------------------------------------

# Placeholder bytecodes — in production these would be compiled from
# Solidity sources.  We use deterministic hex stubs so that the deployer
# class can be tested end-to-end without a Solidity compiler.
_VERIFIER_BYTECODE_STUB = "0x60806040523480156100105760"  # truncated
_BRIDGE_BYTECODE_STUB = "0x60806040523480156100105761"
_TOKEN_BYTECODE_STUB = "0x60806040523480156100105762"


class BridgeDeployer:
    """Deploy bridge contracts to any EVM network.

    Uses the project's :class:`ContractManager` under the hood to deploy
    ``Groth16Verifier``, ``RingsBridge``, and ``BridgedToken``.  In
    production, the ``bytecode`` fields should be replaced with actual
    compiled bytecode.

    Parameters
    ----------
    web3_client : Web3Client
        A connected :class:`Web3Client`.
    contract_manager : ContractManager
        A :class:`ContractManager` instance.
    verifier_bytecode : str, optional
        Hex-encoded bytecode for the verifier contract.
    bridge_bytecode : str, optional
        Hex-encoded bytecode for the bridge contract.
    token_bytecode : str, optional
        Hex-encoded bytecode for the bridged token contract.
    """

    def __init__(
        self,
        web3_client: Any,
        contract_manager: Any,
        *,
        verifier_bytecode: str = _VERIFIER_BYTECODE_STUB,
        bridge_bytecode: str = _BRIDGE_BYTECODE_STUB,
        token_bytecode: str = _TOKEN_BYTECODE_STUB,
    ) -> None:
        self.web3 = web3_client
        self.cm = contract_manager
        self._verifier_bytecode = verifier_bytecode
        self._bridge_bytecode = bridge_bytecode
        self._token_bytecode = token_bytecode

    async def deploy_verifier(
        self,
        vk_alpha: List[int],
        vk_beta: List[List[int]],
        vk_gamma: List[List[int]],
        vk_delta: List[List[int]],
        vk_ic: List[List[int]],
    ) -> str:
        """Deploy the ``Groth16Verifier`` contract.

        Parameters
        ----------
        vk_alpha, vk_beta, vk_gamma, vk_delta, vk_ic :
            Verification key parameters (curve points).

        Returns
        -------
        str
            Deployed contract address.
        """
        logger.info("Deploying Groth16Verifier...")
        ci = await self.cm.deploy_contract(
            contract_name="Groth16Verifier",
            abi=VERIFIER_ABI,
            bytecode=self._verifier_bytecode,
            constructor_args=[vk_alpha, vk_beta, vk_gamma, vk_delta, vk_ic],
        )
        logger.info("Groth16Verifier deployed at %s", ci.address)
        return ci.address

    async def deploy_bridge(
        self,
        daily_limit: int,
        per_tx_limit: int,
        guardian: str,
        verifier_address: str,
    ) -> str:
        """Deploy the ``RingsBridge`` contract.

        Parameters
        ----------
        daily_limit : int
            Maximum daily throughput in wei.
        per_tx_limit : int
            Maximum per-transaction amount in wei.
        guardian : str
            Address of the guardian (can pause the bridge).
        verifier_address : str
            Address of the deployed ``Groth16Verifier``.

        Returns
        -------
        str
            Deployed contract address.
        """
        logger.info("Deploying RingsBridge (guardian=%s, verifier=%s)...",
                     guardian, verifier_address)
        ci = await self.cm.deploy_contract(
            contract_name="RingsBridge",
            abi=BRIDGE_ABI,
            bytecode=self._bridge_bytecode,
            constructor_args=[daily_limit, per_tx_limit, guardian, verifier_address],
        )
        logger.info("RingsBridge deployed at %s", ci.address)
        return ci.address

    async def deploy_bridged_token(
        self,
        name: str,
        symbol: str,
        bridge_address: str,
    ) -> str:
        """Deploy a ``BridgedToken`` and grant ``BRIDGE_ROLE`` to the bridge.

        Parameters
        ----------
        name : str
            Token name (e.g. ``"Bridged ASI"``).
        symbol : str
            Token symbol (e.g. ``"bASI"``).
        bridge_address : str
            Address of the bridge contract to grant minting privileges.

        Returns
        -------
        str
            Deployed token contract address.
        """
        logger.info("Deploying BridgedToken(%s, %s)...", name, symbol)
        ci = await self.cm.deploy_contract(
            contract_name=f"BridgedToken_{symbol}",
            abi=TOKEN_ABI,
            bytecode=self._token_bytecode,
            constructor_args=[name, symbol],
        )
        # Grant BRIDGE_ROLE (keccak256("BRIDGE_ROLE")) to the bridge
        bridge_role = bytes.fromhex(
            "52ba824bfabc2bcfcdf7f0edbb486ebb05e1836c90e78047efeb949990f72e5f"
        )  # keccak256("BRIDGE_ROLE")
        await self.cm.send_contract_transaction(
            f"BridgedToken_{symbol}",
            "grantRole",
            args=[bridge_role, bridge_address],
        )
        logger.info("BridgedToken deployed at %s, BRIDGE_ROLE granted to %s",
                     ci.address, bridge_address)
        return ci.address

    async def deploy_full_suite(
        self,
        daily_limit: int,
        per_tx_limit: int,
        guardian: str,
        vk_params: Dict[str, Any],
        token_name: str = "Bridged ASI",
        token_symbol: str = "bASI",
    ) -> Dict[str, str]:
        """Deploy the complete bridge contract suite.

        Deploys: ``Groth16Verifier`` → ``RingsBridge`` → ``BridgedToken``.

        Parameters
        ----------
        daily_limit : int
            Maximum daily throughput in wei.
        per_tx_limit : int
            Maximum per-transaction amount in wei.
        guardian : str
            Address of the guardian.
        vk_params : dict
            Verification key dict with keys ``alpha``, ``beta``,
            ``gamma``, ``delta``, ``ic``.
        token_name : str
            Bridged token name.
        token_symbol : str
            Bridged token symbol.

        Returns
        -------
        dict
            ``{"verifier": addr, "bridge": addr, "token": addr}``.
        """
        logger.info("Deploying full bridge suite...")

        # 1. Verifier
        verifier_addr = await self.deploy_verifier(
            vk_alpha=vk_params.get("alpha", [0, 0]),
            vk_beta=vk_params.get("beta", [[0, 0], [0, 0]]),
            vk_gamma=vk_params.get("gamma", [[0, 0], [0, 0]]),
            vk_delta=vk_params.get("delta", [[0, 0], [0, 0]]),
            vk_ic=vk_params.get("ic", [[0, 0]]),
        )

        # 2. Bridge
        bridge_addr = await self.deploy_bridge(
            daily_limit=daily_limit,
            per_tx_limit=per_tx_limit,
            guardian=guardian,
            verifier_address=verifier_addr,
        )

        # 3. Bridged Token
        token_addr = await self.deploy_bridged_token(
            name=token_name,
            symbol=token_symbol,
            bridge_address=bridge_addr,
        )

        result = {
            "verifier": verifier_addr,
            "bridge": bridge_addr,
            "token": token_addr,
        }
        logger.info("Full bridge suite deployed: %s", result)
        return result

    def __repr__(self) -> str:
        return "BridgeDeployer()"
