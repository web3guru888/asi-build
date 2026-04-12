#!/usr/bin/env python3
"""
Rings↔Ethereum Bridge CLI
===========================

Command-line interface for interacting with the deployed RingsBridge contract
suite on Sepolia (or any EVM network).  Supports deposits, withdrawals,
bridge status queries, relayer management, and admin operations.

Usage
-----
::

    # Show overall bridge status
    python scripts/bridge_cli.py status

    # Deposit native ETH into the bridge
    python scripts/bridge_cli.py deposit --amount 0.01 --token ETH

    # Deposit an ERC-20 token
    python scripts/bridge_cli.py deposit --amount 1.0 --token 0x1c7D...7238

    # Withdraw ETH to an address (requires ZK proof — placeholder)
    python scripts/bridge_cli.py withdraw --amount 0.01 --to 0x...

    # Query a specific transaction
    python scripts/bridge_cli.py status --tx 0x...

    # Start the bridge relayer
    python scripts/bridge_cli.py relayer start

    # Check relayer status
    python scripts/bridge_cli.py relayer status

    # Admin: pause / unpause the bridge
    python scripts/bridge_cli.py admin pause
    python scripts/bridge_cli.py admin unpause

    # Admin: update rate limits
    python scripts/bridge_cli.py admin set-limits --daily 100 --per-tx 10

    # Machine-readable JSON output
    python scripts/bridge_cli.py status --json

Environment Variables
---------------------
BRIDGE_RPC_URL
    Ethereum RPC endpoint (default: https://ethereum-sepolia-rpc.publicnode.com).
BRIDGE_ADDRESS
    Address of the deployed RingsBridge contract.
BRIDGE_PRIVATE_KEY
    Private key for signing transactions (hex, with or without 0x prefix).
BRIDGE_TOKEN_ADDRESS
    Address of the BridgedToken (bASI) contract.
BRIDGE_VERIFIER_ADDRESS
    Address of the Groth16Verifier contract.
BRIDGE_DEPLOYMENT_FILE
    Path to a ``sepolia.json`` deployment file.  If set, contract addresses
    are loaded from this file and individual address env vars are optional.
BRIDGE_RINGS_DID
    Rings DID for deposit operations (default: derived from deployer address).

The CLI also reads the canonical deployment config from
``deployments/sepolia.json`` relative to the project root if no env vars
or deployment file are specified.

Author: MemPalace-AGI Research Team
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEPLOYMENTS_DIR = PROJECT_ROOT / "deployments"
ARTIFACTS_DIR = (
    PROJECT_ROOT / "src" / "asi_build" / "rings" / "bridge" / "artifacts"
)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

SEPOLIA_CHAIN_ID = 11155111
DEFAULT_RPC = "https://ethereum-sepolia-rpc.publicnode.com"
FALLBACK_RPC = "https://sepolia.drpc.org"
DEFAULT_DEPLOYMENT_FILE = DEPLOYMENTS_DIR / "sepolia.json"

# Default deployed addresses (Sepolia)
DEFAULT_BRIDGE_ADDRESS = "0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca"
DEFAULT_TOKEN_ADDRESS = "0x257dDA1fa34eb847060EcB743E808B65099FB497"
DEFAULT_VERIFIER_ADDRESS = "0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59"
DEFAULT_DEPLOYER = "0x35C3770470F57560beBd1C6C74366b0297110Bc2"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("bridge_cli")


# ═══════════════════════════════════════════════════════════════════════════
#  Terminal colour helpers
# ═══════════════════════════════════════════════════════════════════════════

def _supports_colour() -> bool:
    """Return True if stdout is a colour-capable terminal."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_COLOUR = _supports_colour()


def _c(text: str, code: str) -> str:
    """Wrap *text* in ANSI colour escape if supported."""
    if not _COLOUR:
        return text
    return f"\033[{code}m{text}\033[0m"


def _green(t: str) -> str:
    return _c(t, "32")


def _red(t: str) -> str:
    return _c(t, "31")


def _yellow(t: str) -> str:
    return _c(t, "33")


def _cyan(t: str) -> str:
    return _c(t, "36")


def _bold(t: str) -> str:
    return _c(t, "1")


def _dim(t: str) -> str:
    return _c(t, "2")


# ═══════════════════════════════════════════════════════════════════════════
#  ABI fragments (inline — mirrors contract_client.py)
# ═══════════════════════════════════════════════════════════════════════════

# We inline the minimal ABI so the CLI works without importing the full
# asi_build package (which may have uninstalled deps).  If the full
# artifact JSON is available we prefer that.

BRIDGE_ABI_INLINE: List[Dict[str, Any]] = [
    # -- State-changing --
    {
        "name": "deposit",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [{"name": "ringsDID", "type": "bytes32"}],
        "outputs": [],
    },
    {
        "name": "depositToken",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "ringsDID", "type": "bytes32"},
        ],
        "outputs": [],
    },
    {
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
    },
    {
        "name": "pause",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [],
        "outputs": [],
    },
    {
        "name": "unpause",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [],
        "outputs": [],
    },
    {
        "name": "setRateLimit",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "dailyLimit", "type": "uint256"},
            {"name": "perTxLimit", "type": "uint256"},
        ],
        "outputs": [],
    },
    # -- View --
    {
        "name": "paused",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "name": "depositNonce",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "withdrawalNonce",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "dailyLimit",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "dailyVolume",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "perTxLimit",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "latestVerifiedSlot",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "deposits",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "uint256"}],
        "outputs": [
            {"name": "depositor", "type": "address"},
            {"name": "ringsDID", "type": "bytes32"},
            {"name": "amount", "type": "uint256"},
            {"name": "token", "type": "address"},
            {"name": "timestamp", "type": "uint256"},
        ],
    },
    # -- Events --
    {
        "name": "Deposited",
        "type": "event",
        "inputs": [
            {"name": "nonce", "type": "uint256", "indexed": True},
            {"name": "depositor", "type": "address", "indexed": True},
            {"name": "ringsDID", "type": "bytes32", "indexed": False},
            {"name": "amount", "type": "uint256", "indexed": False},
        ],
    },
    {
        "name": "Withdrawn",
        "type": "event",
        "inputs": [
            {"name": "nonce", "type": "uint256", "indexed": True},
            {"name": "recipient", "type": "address", "indexed": True},
            {"name": "amount", "type": "uint256", "indexed": False},
        ],
    },
    {
        "name": "Paused",
        "type": "event",
        "inputs": [{"name": "account", "type": "address", "indexed": False}],
    },
    {
        "name": "Unpaused",
        "type": "event",
        "inputs": [{"name": "account", "type": "address", "indexed": False}],
    },
]

# Minimal ERC-20 ABI for approve + balanceOf
ERC20_ABI_INLINE: List[Dict[str, Any]] = [
    {
        "name": "approve",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "name": "balanceOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "decimals",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}],
    },
    {
        "name": "symbol",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "string"}],
    },
    {
        "name": "name",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "string"}],
    },
    {
        "name": "totalSupply",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]


# ═══════════════════════════════════════════════════════════════════════════
#  Utility helpers
# ═══════════════════════════════════════════════════════════════════════════


def _wei_to_eth(wei: int) -> float:
    """Convert wei to ETH (float)."""
    return wei / 1e18


def _eth_to_wei(eth: float) -> int:
    """Convert ETH (float) to wei."""
    return int(eth * 1e18)


def _short_addr(addr: str) -> str:
    """Abbreviate an address: 0x1234...abcd."""
    if len(addr) > 12:
        return addr[:6] + "..." + addr[-4:]
    return addr


def _load_bridge_abi() -> List[Dict[str, Any]]:
    """Load the RingsBridge ABI from artifact file, or fall back to inline."""
    artifact_path = ARTIFACTS_DIR / "RingsBridge.json"
    if artifact_path.exists():
        try:
            with open(artifact_path) as f:
                data = json.load(f)
            abi = data.get("abi", [])
            if abi:
                return abi
        except Exception:
            pass
    return BRIDGE_ABI_INLINE


def _load_deployment_config() -> Dict[str, Any]:
    """Load deployment config from file or defaults."""
    # 1. Try BRIDGE_DEPLOYMENT_FILE env var
    deploy_file = os.environ.get("BRIDGE_DEPLOYMENT_FILE", "")
    if deploy_file and Path(deploy_file).exists():
        with open(deploy_file) as f:
            return json.load(f)

    # 2. Try canonical deployments/sepolia.json
    if DEFAULT_DEPLOYMENT_FILE.exists():
        with open(DEFAULT_DEPLOYMENT_FILE) as f:
            return json.load(f)

    # 3. Return defaults
    return {
        "contracts": {
            "bridge": DEFAULT_BRIDGE_ADDRESS,
            "token": DEFAULT_TOKEN_ADDRESS,
            "verifier": DEFAULT_VERIFIER_ADDRESS,
        },
        "rpcUrl": DEFAULT_RPC,
        "deployer": DEFAULT_DEPLOYER,
        "config": {
            "dailyLimit": str(_eth_to_wei(100.0)),
            "perTxLimit": str(_eth_to_wei(10.0)),
            "guardian": DEFAULT_DEPLOYER,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  BridgeCLI — core class
# ═══════════════════════════════════════════════════════════════════════════


class BridgeCLI:
    """Core CLI handler for bridge operations.

    Loads configuration from environment variables and/or deployment
    config files, sets up a web3 connection, and provides methods for
    each CLI subcommand.
    """

    def __init__(
        self,
        *,
        rpc_url: Optional[str] = None,
        bridge_address: Optional[str] = None,
        token_address: Optional[str] = None,
        verifier_address: Optional[str] = None,
        private_key: Optional[str] = None,
        rings_did: Optional[str] = None,
        json_output: bool = False,
    ) -> None:
        # Load deployment config as base
        deploy_cfg = _load_deployment_config()
        contracts = deploy_cfg.get("contracts", {})

        # Resolve config: env > explicit args > deployment file > defaults
        self.rpc_url = (
            rpc_url
            or os.environ.get("BRIDGE_RPC_URL")
            or deploy_cfg.get("rpcUrl", DEFAULT_RPC)
        )
        self.bridge_address = (
            bridge_address
            or os.environ.get("BRIDGE_ADDRESS")
            or contracts.get("bridge", DEFAULT_BRIDGE_ADDRESS)
        )
        self.token_address = (
            token_address
            or os.environ.get("BRIDGE_TOKEN_ADDRESS")
            or contracts.get("token", DEFAULT_TOKEN_ADDRESS)
        )
        self.verifier_address = (
            verifier_address
            or os.environ.get("BRIDGE_VERIFIER_ADDRESS")
            or contracts.get("verifier", DEFAULT_VERIFIER_ADDRESS)
        )
        self.private_key = (
            private_key
            or os.environ.get("BRIDGE_PRIVATE_KEY", "")
        )
        self.rings_did = (
            rings_did
            or os.environ.get("BRIDGE_RINGS_DID", "")
        )
        self.json_output = json_output

        # Lazy-loaded web3 objects
        self._w3 = None
        self._account = None
        self._bridge_contract = None

    # ── Web3 setup (lazy) ───────────────────────────────────────────────

    def _ensure_web3(self) -> None:
        """Lazily initialize web3 connection."""
        if self._w3 is not None:
            return
        try:
            from web3 import Web3
        except ImportError:
            self._error(
                "web3.py is required but not installed.\n"
                "  Install it:  pip install web3"
            )
            sys.exit(1)

        self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self._w3.is_connected():
            self._error(f"Cannot connect to RPC: {self.rpc_url}")
            sys.exit(1)

    def _ensure_account(self) -> None:
        """Ensure we have a signing account from the private key."""
        self._ensure_web3()
        if self._account is not None:
            return
        if not self.private_key:
            self._error(
                "No private key configured.\n"
                "  Set BRIDGE_PRIVATE_KEY env var or pass --private-key."
            )
            sys.exit(1)
        pk = self.private_key
        if not pk.startswith("0x"):
            pk = "0x" + pk
        self._account = self._w3.eth.account.from_key(pk)

    def _get_bridge_contract(self):
        """Return the bridge contract instance."""
        if self._bridge_contract is not None:
            return self._bridge_contract
        self._ensure_web3()
        abi = _load_bridge_abi()
        self._bridge_contract = self._w3.eth.contract(
            address=self._w3.to_checksum_address(self.bridge_address),
            abi=abi,
        )
        return self._bridge_contract

    def _get_token_contract(self, token_address: Optional[str] = None):
        """Return an ERC-20 contract instance."""
        self._ensure_web3()
        addr = token_address or self.token_address
        return self._w3.eth.contract(
            address=self._w3.to_checksum_address(addr),
            abi=ERC20_ABI_INLINE,
        )

    # ── Transaction helpers ─────────────────────────────────────────────

    def _send_tx(self, tx_dict: Dict[str, Any]) -> str:
        """Sign and send a transaction. Returns tx hash hex."""
        self._ensure_account()
        w3 = self._w3

        # Fill in defaults
        if "from" not in tx_dict:
            tx_dict["from"] = self._account.address
        if "nonce" not in tx_dict:
            tx_dict["nonce"] = w3.eth.get_transaction_count(
                self._account.address
            )
        if "chainId" not in tx_dict:
            tx_dict["chainId"] = w3.eth.chain_id

        # Gas estimation
        if "gas" not in tx_dict:
            try:
                tx_dict["gas"] = w3.eth.estimate_gas(tx_dict)
            except Exception as e:
                self._error(f"Gas estimation failed: {e}")
                sys.exit(1)

        # Gas price (EIP-1559 if supported, fallback to legacy)
        if "maxFeePerGas" not in tx_dict and "gasPrice" not in tx_dict:
            try:
                latest = w3.eth.get_block("latest")
                if hasattr(latest, "baseFeePerGas") and latest.baseFeePerGas:
                    base_fee = latest.baseFeePerGas
                    tx_dict["maxFeePerGas"] = base_fee * 2
                    tx_dict["maxPriorityFeePerGas"] = w3.to_wei(1, "gwei")
                else:
                    tx_dict["gasPrice"] = w3.eth.gas_price
            except Exception:
                tx_dict["gasPrice"] = w3.eth.gas_price

        signed = self._account.sign_transaction(tx_dict)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def _wait_for_receipt(self, tx_hash: str, timeout: int = 120) -> Dict:
        """Wait for a transaction receipt."""
        self._ensure_web3()
        receipt = self._w3.eth.wait_for_transaction_receipt(
            tx_hash, timeout=timeout,
        )
        return dict(receipt)

    # ── Output helpers ──────────────────────────────────────────────────

    def _output(self, data: Any, label: str = "") -> None:
        """Print output — JSON or pretty-printed."""
        if self.json_output:
            # Make data JSON-serializable
            print(json.dumps(_make_serializable(data), indent=2))
        else:
            if label:
                print(_bold(label))
            if isinstance(data, dict):
                _print_dict(data)
            elif isinstance(data, str):
                print(data)
            else:
                print(data)

    def _success(self, msg: str) -> None:
        print(_green(f"✅ {msg}"))

    def _error(self, msg: str) -> None:
        print(_red(f"❌ {msg}"), file=sys.stderr)

    def _warn(self, msg: str) -> None:
        print(_yellow(f"⚠️  {msg}"))

    def _info(self, msg: str) -> None:
        print(_cyan(f"ℹ️  {msg}"))

    # ═══════════════════════════════════════════════════════════════════
    #  SUBCOMMAND: status
    # ═══════════════════════════════════════════════════════════════════

    def cmd_status(self, tx_hash: Optional[str] = None) -> None:
        """Show bridge status or query a specific transaction."""
        if tx_hash:
            self._status_tx(tx_hash)
            return

        self._ensure_web3()
        w3 = self._w3
        bridge = self._get_bridge_contract()

        result: Dict[str, Any] = {
            "network": {},
            "bridge": {},
            "limits": {},
            "contracts": {},
        }

        # Network info
        try:
            chain_id = w3.eth.chain_id
            block = w3.eth.block_number
            result["network"] = {
                "rpc": self.rpc_url,
                "chainId": chain_id,
                "blockNumber": block,
                "connected": True,
            }
        except Exception as e:
            result["network"] = {"rpc": self.rpc_url, "error": str(e)}

        # Bridge contract state
        try:
            is_paused = bridge.functions.paused().call()
            dep_nonce = bridge.functions.depositNonce().call()
            w_nonce = bridge.functions.withdrawalNonce().call()
            result["bridge"] = {
                "address": self.bridge_address,
                "paused": is_paused,
                "status": _red("PAUSED") if is_paused else _green("ACTIVE"),
                "totalDeposits": dep_nonce,
                "totalWithdrawals": w_nonce,
            }
        except Exception as e:
            result["bridge"] = {"address": self.bridge_address, "error": str(e)}

        # Rate limits
        try:
            daily_limit = bridge.functions.dailyLimit().call()
            daily_vol = bridge.functions.dailyVolume().call()
            per_tx = bridge.functions.perTxLimit().call()
            remaining = daily_limit - daily_vol if daily_limit > daily_vol else 0
            result["limits"] = {
                "dailyLimit": f"{_wei_to_eth(daily_limit):.4f} ETH",
                "dailyVolume": f"{_wei_to_eth(daily_vol):.4f} ETH",
                "remaining": f"{_wei_to_eth(remaining):.4f} ETH",
                "perTxLimit": f"{_wei_to_eth(per_tx):.4f} ETH",
                "dailyLimit_wei": daily_limit,
                "dailyVolume_wei": daily_vol,
                "perTxLimit_wei": per_tx,
            }
        except Exception as e:
            result["limits"] = {"error": str(e)}

        # Contract addresses & code checks
        for name, addr in [
            ("bridge", self.bridge_address),
            ("token", self.token_address),
            ("verifier", self.verifier_address),
        ]:
            try:
                code = w3.eth.get_code(w3.to_checksum_address(addr))
                has_code = len(code) > 0
                result["contracts"][name] = {
                    "address": addr,
                    "deployed": has_code,
                    "codeSize": len(code),
                }
            except Exception as e:
                result["contracts"][name] = {"address": addr, "error": str(e)}

        # Account info (if key available)
        if self.private_key:
            try:
                self._ensure_account()
                bal = w3.eth.get_balance(self._account.address)
                result["account"] = {
                    "address": self._account.address,
                    "balance": f"{_wei_to_eth(bal):.6f} ETH",
                    "balance_wei": bal,
                }
            except Exception:
                pass

        if self.json_output:
            # Strip colour codes for JSON
            clean = _make_serializable(result)
            print(json.dumps(clean, indent=2))
        else:
            self._print_status(result)

    def _print_status(self, data: Dict) -> None:
        """Pretty-print bridge status."""
        print()
        print(_bold("═══ Rings↔Ethereum Bridge Status ═══"))
        print()

        # Network
        net = data.get("network", {})
        if net.get("connected"):
            print(f"  {_dim('Network:')}     {_green('Connected')}")
            print(f"  {_dim('RPC:')}         {net['rpc']}")
            print(f"  {_dim('Chain ID:')}    {net['chainId']}")
            print(f"  {_dim('Block:')}       {net['blockNumber']:,}")
        else:
            print(f"  {_dim('Network:')}     {_red('Disconnected')}")
            if net.get("error"):
                print(f"  {_dim('Error:')}       {net['error']}")
        print()

        # Bridge
        br = data.get("bridge", {})
        if br.get("error"):
            print(f"  {_dim('Bridge:')}      {_red('Error: ' + br['error'])}")
        else:
            print(f"  {_dim('Bridge:')}      {br.get('address', 'N/A')}")
            print(f"  {_dim('Status:')}      {br.get('status', 'Unknown')}")
            print(f"  {_dim('Deposits:')}    {br.get('totalDeposits', 'N/A')}")
            print(f"  {_dim('Withdrawals:')} {br.get('totalWithdrawals', 'N/A')}")
        print()

        # Limits
        lim = data.get("limits", {})
        if lim.get("error"):
            print(f"  {_dim('Limits:')}      {_red('Error: ' + lim['error'])}")
        else:
            print(f"  {_dim('Daily Limit:')}  {lim.get('dailyLimit', 'N/A')}")
            print(f"  {_dim('Daily Used:')}   {lim.get('dailyVolume', 'N/A')}")
            print(f"  {_dim('Remaining:')}    {lim.get('remaining', 'N/A')}")
            print(f"  {_dim('Per-TX Max:')}   {lim.get('perTxLimit', 'N/A')}")
        print()

        # Contracts
        cs = data.get("contracts", {})
        print(f"  {_dim('Contracts:')}")
        for name, info in cs.items():
            addr = info.get("address", "N/A")
            if info.get("deployed"):
                status = _green(f"✓ deployed ({info.get('codeSize', '?')} bytes)")
            elif info.get("error"):
                status = _red(f"✗ error: {info['error']}")
            else:
                status = _red("✗ no code")
            print(f"    {name:12s} {_short_addr(addr)}  {status}")
        print()

        # Account
        acct = data.get("account")
        if acct:
            print(f"  {_dim('Account:')}     {acct['address']}")
            print(f"  {_dim('Balance:')}     {acct['balance']}")
            print()

    def _status_tx(self, tx_hash: str) -> None:
        """Query a specific transaction."""
        self._ensure_web3()
        w3 = self._w3

        try:
            tx = w3.eth.get_transaction(tx_hash)
        except Exception as e:
            self._error(f"Transaction not found: {e}")
            return

        result: Dict[str, Any] = {
            "hash": tx_hash,
            "from": tx.get("from", ""),
            "to": tx.get("to", ""),
            "value": f"{_wei_to_eth(tx.get('value', 0)):.6f} ETH",
            "value_wei": tx.get("value", 0),
            "gasPrice": tx.get("gasPrice", 0),
            "blockNumber": tx.get("blockNumber"),
            "status": "pending" if tx.get("blockNumber") is None else "mined",
        }

        # Try to get receipt
        if tx.get("blockNumber") is not None:
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                result["gasUsed"] = receipt.get("gasUsed", 0)
                result["status"] = (
                    "success" if receipt.get("status") == 1 else "reverted"
                )
                result["logs"] = len(receipt.get("logs", []))
            except Exception:
                pass

        self._output(result, f"Transaction {_short_addr(tx_hash)}")

    # ═══════════════════════════════════════════════════════════════════
    #  SUBCOMMAND: deposit
    # ═══════════════════════════════════════════════════════════════════

    def cmd_deposit(self, amount: float, token: str = "ETH") -> None:
        """Deposit ETH or an ERC-20 token into the bridge."""
        self._ensure_account()
        w3 = self._w3
        bridge = self._get_bridge_contract()

        # Resolve Rings DID
        rings_did = self.rings_did
        if not rings_did:
            # Default: pad deployer address into bytes32
            addr_hex = self._account.address.lower().removeprefix("0x")
            rings_did = "0x" + addr_hex.zfill(64)

        # Ensure rings_did is bytes32
        if isinstance(rings_did, str):
            if rings_did.startswith("0x") and len(rings_did) == 66:
                did_bytes32 = bytes.fromhex(rings_did[2:])
            else:
                # Hash it into bytes32
                import hashlib
                did_bytes32 = hashlib.sha256(rings_did.encode()).digest()
        else:
            did_bytes32 = rings_did

        if token.upper() == "ETH":
            # Native ETH deposit
            amount_wei = _eth_to_wei(amount)
            self._info(f"Depositing {amount:.6f} ETH into bridge...")
            self._info(f"  Bridge:   {self.bridge_address}")
            self._info(f"  Rings DID: {rings_did}")

            try:
                tx = bridge.functions.deposit(did_bytes32).build_transaction({
                    "from": self._account.address,
                    "value": amount_wei,
                    "nonce": w3.eth.get_transaction_count(self._account.address),
                    "chainId": w3.eth.chain_id,
                })
                tx["gas"] = w3.eth.estimate_gas(tx)
                tx_hash = self._send_tx(tx)
                self._success(f"Deposit TX sent: {tx_hash}")
                self._info("Waiting for confirmation...")

                receipt = self._wait_for_receipt(tx_hash)
                if receipt.get("status") == 1:
                    self._success(
                        f"Deposit confirmed in block {receipt.get('blockNumber')}"
                    )
                    result = {
                        "txHash": tx_hash,
                        "blockNumber": receipt.get("blockNumber"),
                        "gasUsed": receipt.get("gasUsed"),
                        "amount": f"{amount} ETH",
                        "amount_wei": amount_wei,
                        "ringsDID": rings_did,
                        "status": "confirmed",
                    }
                else:
                    self._error("Deposit transaction reverted!")
                    result = {"txHash": tx_hash, "status": "reverted"}
            except Exception as e:
                self._error(f"Deposit failed: {e}")
                result = {"error": str(e)}

        else:
            # ERC-20 token deposit
            token_addr = w3.to_checksum_address(token)
            token_contract = self._get_token_contract(token_addr)

            # Get token info
            try:
                symbol = token_contract.functions.symbol().call()
                decimals = token_contract.functions.decimals().call()
            except Exception:
                symbol = "TOKEN"
                decimals = 18

            amount_raw = int(amount * (10 ** decimals))
            self._info(
                f"Depositing {amount} {symbol} ({token_addr}) into bridge..."
            )

            # Step 1: Approve bridge to spend tokens
            self._info("Step 1/2: Approving bridge to spend tokens...")
            try:
                approve_tx = token_contract.functions.approve(
                    w3.to_checksum_address(self.bridge_address),
                    amount_raw,
                ).build_transaction({
                    "from": self._account.address,
                    "nonce": w3.eth.get_transaction_count(self._account.address),
                    "chainId": w3.eth.chain_id,
                })
                approve_tx["gas"] = w3.eth.estimate_gas(approve_tx)
                approve_hash = self._send_tx(approve_tx)
                self._wait_for_receipt(approve_hash)
                self._success("Approval confirmed")
            except Exception as e:
                self._error(f"Token approval failed: {e}")
                result = {"error": f"Approval failed: {e}"}
                self._output(result)
                return

            # Step 2: Deposit token
            self._info("Step 2/2: Depositing token...")
            try:
                dep_tx = bridge.functions.depositToken(
                    token_addr, amount_raw, did_bytes32,
                ).build_transaction({
                    "from": self._account.address,
                    "nonce": w3.eth.get_transaction_count(self._account.address),
                    "chainId": w3.eth.chain_id,
                })
                dep_tx["gas"] = w3.eth.estimate_gas(dep_tx)
                tx_hash = self._send_tx(dep_tx)
                self._success(f"Deposit TX sent: {tx_hash}")
                self._info("Waiting for confirmation...")

                receipt = self._wait_for_receipt(tx_hash)
                if receipt.get("status") == 1:
                    self._success(
                        f"Token deposit confirmed in block "
                        f"{receipt.get('blockNumber')}"
                    )
                    result = {
                        "txHash": tx_hash,
                        "approveTxHash": approve_hash,
                        "blockNumber": receipt.get("blockNumber"),
                        "gasUsed": receipt.get("gasUsed"),
                        "amount": f"{amount} {symbol}",
                        "token": token_addr,
                        "ringsDID": rings_did,
                        "status": "confirmed",
                    }
                else:
                    self._error("Token deposit transaction reverted!")
                    result = {"txHash": tx_hash, "status": "reverted"}
            except Exception as e:
                self._error(f"Token deposit failed: {e}")
                result = {"error": str(e)}

        if self.json_output:
            print(json.dumps(_make_serializable(result), indent=2))

    # ═══════════════════════════════════════════════════════════════════
    #  SUBCOMMAND: withdraw
    # ═══════════════════════════════════════════════════════════════════

    def cmd_withdraw(
        self,
        amount: float,
        to_address: str,
        nonce: Optional[int] = None,
    ) -> None:
        """Submit a withdrawal (requires ZK proof — demo/placeholder)."""
        self._ensure_account()
        w3 = self._w3
        bridge = self._get_bridge_contract()

        amount_wei = _eth_to_wei(amount)
        recipient = w3.to_checksum_address(to_address)

        # Get current withdrawal nonce if not specified
        if nonce is None:
            try:
                nonce = bridge.functions.withdrawalNonce().call()
            except Exception:
                nonce = 0

        self._info(f"Preparing withdrawal of {amount:.6f} ETH to {recipient}...")
        self._warn(
            "ZK proof generation is not yet integrated in the CLI.\n"
            "   This command constructs a placeholder proof for testing.\n"
            "   In production, use the bridge relayer for automated withdrawals."
        )

        # Placeholder ZK proof (will revert on mainnet — works on test contracts
        # that skip verification, or for dry-run demonstration)
        proof = b"\x00" * 256  # 256 bytes of zeros
        public_inputs = [amount_wei, nonce, int(recipient, 16) % (2**128)]

        try:
            tx = bridge.functions.withdraw(
                recipient, amount_wei, nonce, proof, public_inputs,
            ).build_transaction({
                "from": self._account.address,
                "nonce": w3.eth.get_transaction_count(self._account.address),
                "chainId": w3.eth.chain_id,
            })
            tx["gas"] = w3.eth.estimate_gas(tx)
            tx_hash = self._send_tx(tx)
            self._success(f"Withdrawal TX sent: {tx_hash}")
            self._info("Waiting for confirmation...")

            receipt = self._wait_for_receipt(tx_hash)
            if receipt.get("status") == 1:
                self._success(
                    f"Withdrawal confirmed in block {receipt.get('blockNumber')}"
                )
                result = {
                    "txHash": tx_hash,
                    "blockNumber": receipt.get("blockNumber"),
                    "gasUsed": receipt.get("gasUsed"),
                    "amount": f"{amount} ETH",
                    "recipient": recipient,
                    "nonce": nonce,
                    "status": "confirmed",
                }
            else:
                self._error("Withdrawal transaction reverted!")
                self._warn(
                    "This is expected if ZK proof verification is enabled.\n"
                    "   Use the bridge relayer for proper ZK-proven withdrawals."
                )
                result = {"txHash": tx_hash, "status": "reverted"}
        except Exception as e:
            self._error(f"Withdrawal failed: {e}")
            self._warn(
                "This is expected if ZK proof verification is enabled on-chain.\n"
                "   Use the bridge relayer for proper ZK-proven withdrawals."
            )
            result = {"error": str(e)}

        if self.json_output:
            print(json.dumps(_make_serializable(result), indent=2))

    # ═══════════════════════════════════════════════════════════════════
    #  SUBCOMMAND: relayer
    # ═══════════════════════════════════════════════════════════════════

    def cmd_relayer(self, action: str) -> None:
        """Start or check the bridge relayer."""
        if action == "start":
            self._relayer_start()
        elif action == "status":
            self._relayer_status()
        else:
            self._error(f"Unknown relayer action: {action}")

    def _relayer_start(self) -> None:
        """Start the bridge relayer (BridgeOrchestrator run loop)."""
        self._ensure_account()
        self._info("Starting bridge relayer...")
        self._info(f"  RPC:    {self.rpc_url}")
        self._info(f"  Bridge: {self.bridge_address}")
        self._info(f"  Signer: {self._account.address}")

        try:
            # Try to import the BridgeOrchestrator
            sys.path.insert(0, str(PROJECT_ROOT / "src"))
            from asi_build.rings.bridge.e2e import BridgeOrchestrator
            from asi_build.rings.bridge.protocol import BridgeValidator
            from asi_build.rings.bridge.light_client import MockLightClient

            self._info("BridgeOrchestrator loaded successfully")

            # Create a minimal identity for the validator
            class _CLIIdentity:
                def __init__(self, address: str):
                    self.rings_did = f"did:rings:eth:{address}"

                def sign_rings(self, data: bytes) -> bytes:
                    import hashlib
                    return hashlib.sha256(data + b"cli-signer").digest()

            # Create mock objects (in production these would be real)
            class _MockClient:
                async def join_sub_ring(self, name):
                    pass

                async def dht_put(self, key, val):
                    pass

                async def dht_get(self, key):
                    return None

                async def broadcast(self, ring, msg):
                    pass

            identity = _CLIIdentity(self._account.address)
            client = _MockClient()
            validator = BridgeValidator(
                identity=identity,
                client=client,
                threshold=1,
                total=1,
            )

            light_client = MockLightClient()
            orchestrator = BridgeOrchestrator(
                validator=validator,
                contract_client=None,  # Would be BridgeContractClient
                light_client=light_client,
            )

            self._success("Relayer initialized")
            self._info(
                "Starting relay loop (poll every 12s)...\n"
                "  Press Ctrl+C to stop."
            )
            print()

            asyncio.run(orchestrator.run_bridge_loop(
                poll_interval=12.0,
                start_block=None,
            ))

        except ImportError as e:
            self._error(
                f"Cannot import bridge modules: {e}\n"
                "  Make sure the asi-build package is installed:\n"
                "    pip install -e /path/to/asi-build"
            )
        except KeyboardInterrupt:
            print()
            self._info("Relayer stopped by user")
        except Exception as e:
            self._error(f"Relayer error: {e}")

    def _relayer_status(self) -> None:
        """Show relayer status (bridge contract state as proxy)."""
        self._ensure_web3()
        bridge = self._get_bridge_contract()

        result: Dict[str, Any] = {"relayer": {}}

        try:
            is_paused = bridge.functions.paused().call()
            dep_nonce = bridge.functions.depositNonce().call()
            w_nonce = bridge.functions.withdrawalNonce().call()

            result["relayer"] = {
                "bridgePaused": is_paused,
                "totalDeposits": dep_nonce,
                "totalWithdrawals": w_nonce,
                "note": (
                    "Relayer status is inferred from on-chain state. "
                    "For live relayer process status, check the process manager."
                ),
            }
        except Exception as e:
            result["relayer"] = {"error": str(e)}

        self._output(result, "Relayer Status")

    # ═══════════════════════════════════════════════════════════════════
    #  SUBCOMMAND: admin
    # ═══════════════════════════════════════════════════════════════════

    def cmd_admin(
        self,
        action: str,
        daily_limit: Optional[float] = None,
        per_tx_limit: Optional[float] = None,
    ) -> None:
        """Execute admin operations (pause, unpause, set-limits)."""
        if action == "pause":
            self._admin_pause()
        elif action == "unpause":
            self._admin_unpause()
        elif action == "set-limits":
            self._admin_set_limits(daily_limit, per_tx_limit)
        else:
            self._error(f"Unknown admin action: {action}")

    def _admin_pause(self) -> None:
        """Pause the bridge contract."""
        self._ensure_account()
        w3 = self._w3
        bridge = self._get_bridge_contract()

        # Check if already paused
        try:
            if bridge.functions.paused().call():
                self._warn("Bridge is already paused")
                return
        except Exception:
            pass

        self._info("Pausing bridge contract...")
        try:
            tx = bridge.functions.pause().build_transaction({
                "from": self._account.address,
                "nonce": w3.eth.get_transaction_count(self._account.address),
                "chainId": w3.eth.chain_id,
            })
            tx["gas"] = w3.eth.estimate_gas(tx)
            tx_hash = self._send_tx(tx)
            self._success(f"Pause TX sent: {tx_hash}")

            receipt = self._wait_for_receipt(tx_hash)
            if receipt.get("status") == 1:
                self._success("Bridge paused successfully")
                result = {
                    "txHash": tx_hash,
                    "blockNumber": receipt.get("blockNumber"),
                    "action": "pause",
                    "status": "confirmed",
                }
            else:
                self._error("Pause transaction reverted (not guardian?)")
                result = {"txHash": tx_hash, "status": "reverted"}
        except Exception as e:
            self._error(f"Pause failed: {e}")
            result = {"error": str(e)}

        if self.json_output:
            print(json.dumps(_make_serializable(result), indent=2))

    def _admin_unpause(self) -> None:
        """Unpause the bridge contract."""
        self._ensure_account()
        w3 = self._w3
        bridge = self._get_bridge_contract()

        # Check if already unpaused
        try:
            if not bridge.functions.paused().call():
                self._warn("Bridge is already active (not paused)")
                return
        except Exception:
            pass

        self._info("Unpausing bridge contract...")
        try:
            tx = bridge.functions.unpause().build_transaction({
                "from": self._account.address,
                "nonce": w3.eth.get_transaction_count(self._account.address),
                "chainId": w3.eth.chain_id,
            })
            tx["gas"] = w3.eth.estimate_gas(tx)
            tx_hash = self._send_tx(tx)
            self._success(f"Unpause TX sent: {tx_hash}")

            receipt = self._wait_for_receipt(tx_hash)
            if receipt.get("status") == 1:
                self._success("Bridge unpaused successfully")
                result = {
                    "txHash": tx_hash,
                    "blockNumber": receipt.get("blockNumber"),
                    "action": "unpause",
                    "status": "confirmed",
                }
            else:
                self._error("Unpause transaction reverted (not guardian?)")
                result = {"txHash": tx_hash, "status": "reverted"}
        except Exception as e:
            self._error(f"Unpause failed: {e}")
            result = {"error": str(e)}

        if self.json_output:
            print(json.dumps(_make_serializable(result), indent=2))

    def _admin_set_limits(
        self,
        daily_limit: Optional[float],
        per_tx_limit: Optional[float],
    ) -> None:
        """Update bridge rate limits."""
        self._ensure_account()
        w3 = self._w3
        bridge = self._get_bridge_contract()

        if daily_limit is None or per_tx_limit is None:
            self._error(
                "Both --daily and --per-tx are required for set-limits.\n"
                "  Example: bridge_cli.py admin set-limits --daily 100 --per-tx 10"
            )
            return

        daily_wei = _eth_to_wei(daily_limit)
        per_tx_wei = _eth_to_wei(per_tx_limit)

        if per_tx_wei > daily_wei:
            self._error("Per-TX limit cannot exceed daily limit")
            return

        self._info(
            f"Setting rate limits:\n"
            f"  Daily:  {daily_limit} ETH ({daily_wei} wei)\n"
            f"  Per-TX: {per_tx_limit} ETH ({per_tx_wei} wei)"
        )

        try:
            tx = bridge.functions.setRateLimit(
                daily_wei, per_tx_wei,
            ).build_transaction({
                "from": self._account.address,
                "nonce": w3.eth.get_transaction_count(self._account.address),
                "chainId": w3.eth.chain_id,
            })
            tx["gas"] = w3.eth.estimate_gas(tx)
            tx_hash = self._send_tx(tx)
            self._success(f"Set limits TX sent: {tx_hash}")

            receipt = self._wait_for_receipt(tx_hash)
            if receipt.get("status") == 1:
                self._success(
                    f"Rate limits updated: daily={daily_limit} ETH, "
                    f"per-tx={per_tx_limit} ETH"
                )
                result = {
                    "txHash": tx_hash,
                    "blockNumber": receipt.get("blockNumber"),
                    "action": "set-limits",
                    "dailyLimit": f"{daily_limit} ETH",
                    "perTxLimit": f"{per_tx_limit} ETH",
                    "status": "confirmed",
                }
            else:
                self._error("Set limits transaction reverted (not admin?)")
                result = {"txHash": tx_hash, "status": "reverted"}
        except Exception as e:
            self._error(f"Set limits failed: {e}")
            result = {"error": str(e)}

        if self.json_output:
            print(json.dumps(_make_serializable(result), indent=2))


# ═══════════════════════════════════════════════════════════════════════════
#  Output formatting helpers
# ═══════════════════════════════════════════════════════════════════════════


def _make_serializable(obj: Any) -> Any:
    """Recursively convert an object to be JSON-serializable."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, bytes):
        return "0x" + obj.hex()
    if isinstance(obj, int) and obj > 2**53:
        return str(obj)
    if hasattr(obj, "hex"):
        return obj.hex() if callable(obj.hex) else str(obj)
    # Strip ANSI colour codes for JSON
    if isinstance(obj, str):
        import re
        return re.sub(r"\033\[\d+m", "", obj)
    return obj


def _print_dict(data: Dict, indent: int = 2) -> None:
    """Pretty-print a dict with alignment."""
    if not data:
        print(f"{' ' * indent}(empty)")
        return
    max_key_len = max(len(str(k)) for k in data.keys()) if data else 0
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{' ' * indent}{_dim(str(key) + ':')}")
            _print_dict(value, indent + 2)
        else:
            print(
                f"{' ' * indent}{_dim(str(key) + ':')}"
                f"{'.' * (max_key_len - len(str(key)) + 2)} {value}"
            )


# ═══════════════════════════════════════════════════════════════════════════
#  CLI entry point
# ═══════════════════════════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="bridge_cli",
        description=(
            "Rings↔Ethereum Bridge CLI — interact with the deployed bridge "
            "contracts on Sepolia testnet."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                              Show bridge status
  %(prog)s status --tx 0xabc...                Query a transaction
  %(prog)s deposit --amount 0.01 --token ETH   Deposit 0.01 ETH
  %(prog)s deposit --amount 1.0 --token 0x...  Deposit ERC-20 token
  %(prog)s withdraw --amount 0.01 --to 0x...   Withdraw ETH
  %(prog)s relayer start                       Start the bridge relayer
  %(prog)s relayer status                      Check relayer status
  %(prog)s admin pause                         Pause the bridge
  %(prog)s admin unpause                       Unpause the bridge
  %(prog)s admin set-limits --daily 100 --per-tx 10

Environment:
  BRIDGE_RPC_URL          RPC endpoint
  BRIDGE_ADDRESS          Bridge contract address
  BRIDGE_PRIVATE_KEY      Private key for signing
  BRIDGE_TOKEN_ADDRESS    BridgedToken address
  BRIDGE_VERIFIER_ADDRESS Groth16Verifier address
  BRIDGE_DEPLOYMENT_FILE  Path to deployment JSON
  BRIDGE_RINGS_DID        Rings DID for deposits
        """,
    )

    # Global options
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output in machine-readable JSON format",
    )
    parser.add_argument(
        "--rpc-url",
        default=None,
        help="Ethereum RPC URL (overrides BRIDGE_RPC_URL)",
    )
    parser.add_argument(
        "--bridge-address",
        default=None,
        help="RingsBridge contract address (overrides BRIDGE_ADDRESS)",
    )
    parser.add_argument(
        "--private-key",
        default=None,
        help="Private key for signing (overrides BRIDGE_PRIVATE_KEY)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── status ──────────────────────────────────────────────────────────
    p_status = subparsers.add_parser(
        "status",
        help="Show bridge status or query a transaction",
        description="Display the current state of the bridge contract.",
    )
    p_status.add_argument(
        "--tx",
        default=None,
        metavar="TX_HASH",
        help="Query a specific transaction hash",
    )

    # ── deposit ─────────────────────────────────────────────────────────
    p_deposit = subparsers.add_parser(
        "deposit",
        help="Deposit ETH or tokens into the bridge",
        description=(
            "Deposit native ETH or ERC-20 tokens into the RingsBridge. "
            "For ERC-20 deposits, the CLI automatically handles approval."
        ),
    )
    p_deposit.add_argument(
        "--amount",
        type=float,
        required=True,
        help="Amount to deposit (in ETH or token units)",
    )
    p_deposit.add_argument(
        "--token",
        default="ETH",
        help=(
            "Token to deposit: 'ETH' for native ETH, or a 0x... address "
            "for ERC-20 tokens (default: ETH)"
        ),
    )
    p_deposit.add_argument(
        "--rings-did",
        default=None,
        help="Rings DID to credit (default: derived from signer address)",
    )

    # ── withdraw ────────────────────────────────────────────────────────
    p_withdraw = subparsers.add_parser(
        "withdraw",
        help="Withdraw ETH from the bridge",
        description=(
            "Submit a withdrawal from the bridge. Note: this requires a "
            "valid ZK proof. The CLI uses a placeholder proof for testing; "
            "use the relayer for production withdrawals."
        ),
    )
    p_withdraw.add_argument(
        "--amount",
        type=float,
        required=True,
        help="Amount to withdraw in ETH",
    )
    p_withdraw.add_argument(
        "--to",
        required=True,
        dest="to_address",
        metavar="ADDRESS",
        help="Recipient Ethereum address (0x...)",
    )
    p_withdraw.add_argument(
        "--nonce",
        type=int,
        default=None,
        help="Withdrawal nonce (default: auto from contract)",
    )

    # ── relayer ─────────────────────────────────────────────────────────
    p_relayer = subparsers.add_parser(
        "relayer",
        help="Manage the bridge relayer",
        description="Start or check the status of the bridge relayer daemon.",
    )
    p_relayer.add_argument(
        "action",
        choices=["start", "status"],
        help="'start' to run the relayer, 'status' to check state",
    )

    # ── admin ───────────────────────────────────────────────────────────
    p_admin = subparsers.add_parser(
        "admin",
        help="Admin operations (pause, unpause, set-limits)",
        description=(
            "Administrative operations on the bridge contract. "
            "Requires guardian/admin role."
        ),
    )
    p_admin.add_argument(
        "action",
        choices=["pause", "unpause", "set-limits"],
        help="Admin action to perform",
    )
    p_admin.add_argument(
        "--daily",
        type=float,
        default=None,
        dest="daily_limit",
        help="Daily bridge limit in ETH (for set-limits)",
    )
    p_admin.add_argument(
        "--per-tx",
        type=float,
        default=None,
        dest="per_tx_limit",
        help="Per-transaction limit in ETH (for set-limits)",
    )

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Build CLI instance
    cli = BridgeCLI(
        rpc_url=args.rpc_url,
        bridge_address=args.bridge_address,
        private_key=args.private_key,
        json_output=args.json_output,
    )

    # Dispatch
    try:
        if args.command == "status":
            cli.cmd_status(tx_hash=args.tx)
        elif args.command == "deposit":
            cli.cmd_deposit(
                amount=args.amount,
                token=args.token,
            )
        elif args.command == "withdraw":
            cli.cmd_withdraw(
                amount=args.amount,
                to_address=args.to_address,
                nonce=args.nonce,
            )
        elif args.command == "relayer":
            cli.cmd_relayer(action=args.action)
        elif args.command == "admin":
            cli.cmd_admin(
                action=args.action,
                daily_limit=getattr(args, "daily_limit", None),
                per_tx_limit=getattr(args, "per_tx_limit", None),
            )
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print()
        sys.exit(130)
    except Exception as e:
        if args.json_output:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(_red(f"\n❌ Error: {e}"), file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
