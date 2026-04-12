#!/usr/bin/env python3
"""
Emergency Pause / Unpause
=========================

One-command emergency pause for the RingsBridge contract.  Designed for
incident response — **no confirmation required** for pause operations.

The script calls ``emergencyPause()`` (guardian-only, bypasses admin) or
``unpause()`` (admin-only) on the deployed bridge contract.

Every invocation is logged to ``logs/emergency_pause.log`` with timestamps,
tx hashes, and outcome for post-incident audit trails.

Environment Variables
---------------------
BRIDGE_RPC_URL
    Ethereum JSON-RPC endpoint (default: Sepolia public node).
BRIDGE_ADDRESS
    Deployed ``RingsBridge`` contract address.
BRIDGE_PRIVATE_KEY
    Hex private key of the guardian/admin account.

Usage
-----
::

    # PAUSE — immediate, no confirmation:
    python scripts/emergency_pause.py

    # UNPAUSE:
    python scripts/emergency_pause.py --unpause

    # With explicit config:
    BRIDGE_RPC_URL=https://sepolia.drpc.org \\
    BRIDGE_ADDRESS=0x... \\
    BRIDGE_PRIVATE_KEY=0x... \\
    python scripts/emergency_pause.py

Exit Codes
----------
0 — success
1 — failure (tx reverted, connectivity, missing config)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths & defaults
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "emergency_pause.log"
ARTIFACTS_DIR = PROJECT_ROOT / "src" / "asi_build" / "rings" / "bridge" / "artifacts"

DEFAULT_RPC = "https://ethereum-sepolia-rpc.publicnode.com"
TX_TIMEOUT_SECONDS = 120

# ---------------------------------------------------------------------------
# Logging — console + file
# ---------------------------------------------------------------------------

LOG_DIR.mkdir(parents=True, exist_ok=True)

# Console handler
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
)

# File handler (append mode — never lose history)
file_handler = logging.FileHandler(str(LOG_FILE), mode="a", encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)

logger = logging.getLogger("emergency_pause")
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# ---------------------------------------------------------------------------
# ABI — minimal fragments for pause/unpause
# ---------------------------------------------------------------------------

PAUSE_ABI = [
    {
        "name": "emergencyPause",
        "type": "function",
        "inputs": [],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "name": "pause",
        "type": "function",
        "inputs": [],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "name": "unpause",
        "type": "function",
        "inputs": [],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "name": "paused",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
    },
    {
        "name": "GUARDIAN_ROLE",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
    },
    {
        "name": "DEFAULT_ADMIN_ROLE",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
    },
    {
        "name": "hasRole",
        "type": "function",
        "inputs": [
            {"name": "role", "type": "bytes32"},
            {"name": "account", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
    },
]


def _load_full_abi() -> list:
    """Try loading the full ABI from artifacts; fall back to inline fragments."""
    abi_path = ARTIFACTS_DIR / "RingsBridge.json"
    if abi_path.exists():
        try:
            with open(abi_path) as f:
                data = json.load(f)
            return data.get("abi", PAUSE_ABI)
        except Exception:
            pass
    return PAUSE_ABI


def _log_to_file(event: dict) -> None:
    """Append a structured JSON event to the log file for audit."""
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def _connect(rpc_url: str, private_key: str, bridge_address: str) -> tuple:
    """
    Connect to the RPC and return (w3, contract, account).

    Returns
    -------
    tuple
        (web3.Web3, web3.Contract, web3.Account)
    """
    try:
        from web3 import Web3
        from web3.middleware import SignAndSendRawMiddlewareBuilder
    except ImportError:
        logger.error("web3 is required.  Install with: pip install web3")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        logger.error("Cannot connect to RPC: %s", rpc_url)
        _log_to_file({"event": "connection_failed", "rpc_url": rpc_url})
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    w3.middleware_onion.inject(
        SignAndSendRawMiddlewareBuilder.build(account),
        layer=0,
    )
    w3.eth.default_account = account.address

    abi = _load_full_abi()
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(bridge_address),
        abi=abi,
    )
    return w3, contract, account


def _wait_for_tx(w3: Any, tx_hash: Any, timeout: int = TX_TIMEOUT_SECONDS) -> Any:
    """Wait for a transaction receipt with timeout."""
    logger.info("  Tx submitted: %s", tx_hash.hex() if hasattr(tx_hash, "hex") else tx_hash)
    logger.info("  Waiting for confirmation (up to %ds) ...", timeout)
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt is not None:
                return receipt
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"Transaction {tx_hash} not mined within {timeout}s")


def emergency_pause(
    rpc_url: str,
    bridge_address: str,
    private_key: str,
    do_unpause: bool = False,
) -> bool:
    """
    Emergency pause or unpause the bridge.

    Parameters
    ----------
    rpc_url : str
        Ethereum JSON-RPC URL.
    bridge_address : str
        RingsBridge contract address.
    private_key : str
        Hex private key (guardian for pause, admin for unpause).
    do_unpause : bool
        If True, unpause instead of pause.

    Returns
    -------
    bool
        True on success.
    """
    operation = "unpause" if do_unpause else "emergency_pause"

    logger.info("=" * 60)
    logger.info("  BRIDGE %s", "UNPAUSE" if do_unpause else "EMERGENCY PAUSE")
    logger.info("=" * 60)

    _log_to_file({
        "event": f"{operation}_initiated",
        "bridge_address": bridge_address,
        "rpc_url": rpc_url,
    })

    # ── Connect ────────────────────────────────────────────────────────
    w3, contract, account = _connect(rpc_url, private_key, bridge_address)
    chain_id = w3.eth.chain_id

    logger.info("  Chain ID:    %d", chain_id)
    logger.info("  Bridge:      %s", bridge_address)
    logger.info("  Caller:      %s", account.address)

    # ── Check current state ───────────────────────────────────────────
    try:
        is_paused = contract.functions.paused().call()
    except Exception as e:
        logger.error("Failed to read paused() state: %s", e)
        _log_to_file({"event": f"{operation}_failed", "error": str(e)})
        return False

    logger.info("  Paused now:  %s", "YES ⛔" if is_paused else "no ✅")

    if do_unpause and not is_paused:
        logger.info("Bridge is already unpaused — nothing to do.")
        _log_to_file({"event": "unpause_skipped", "reason": "already_unpaused"})
        return True

    if not do_unpause and is_paused:
        logger.info("Bridge is already paused — nothing to do.")
        _log_to_file({"event": "emergency_pause_skipped", "reason": "already_paused"})
        return True

    # ── Check caller role ─────────────────────────────────────────────
    try:
        guardian_role = contract.functions.GUARDIAN_ROLE().call()
        admin_role = contract.functions.DEFAULT_ADMIN_ROLE().call()
        is_guardian = contract.functions.hasRole(guardian_role, account.address).call()
        is_admin = contract.functions.hasRole(admin_role, account.address).call()
        logger.info("  Is guardian: %s", "YES" if is_guardian else "NO")
        logger.info("  Is admin:    %s", "YES" if is_admin else "NO")
    except Exception as e:
        logger.warning("Could not check roles (proceeding anyway): %s", e)
        is_guardian = True  # Assume and let the tx revert if wrong
        is_admin = True

    # ── Execute ───────────────────────────────────────────────────────
    try:
        if do_unpause:
            logger.info("Calling unpause() ...")
            tx_hash = contract.functions.unpause().transact()
        else:
            # Prefer emergencyPause() (guardian-specific, emits EmergencyPaused)
            # Fall back to pause() if emergencyPause isn't available
            try:
                logger.info("Calling emergencyPause() ...")
                tx_hash = contract.functions.emergencyPause().transact()
            except Exception:
                logger.info("emergencyPause() not available, falling back to pause() ...")
                tx_hash = contract.functions.pause().transact()

        tx_hex = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
        _log_to_file({
            "event": f"{operation}_tx_sent",
            "tx_hash": tx_hex,
            "caller": account.address,
        })

    except Exception as e:
        logger.error("Transaction submission FAILED: %s", e)
        _log_to_file({"event": f"{operation}_failed", "error": str(e), "stage": "submit"})
        return False

    # ── Wait for confirmation ─────────────────────────────────────────
    try:
        receipt = _wait_for_tx(w3, tx_hash)
    except TimeoutError as e:
        logger.error("Transaction NOT confirmed within timeout: %s", e)
        _log_to_file({
            "event": f"{operation}_timeout",
            "tx_hash": tx_hex,
        })
        return False

    gas_used = receipt.get("gasUsed", 0)
    block_number = receipt.get("blockNumber", 0)
    status = receipt.get("status", -1)

    if status != 1:
        logger.error(
            "Transaction REVERTED (status=0).  Tx: %s  Block: %d  Gas: %d",
            tx_hex, block_number, gas_used,
        )
        _log_to_file({
            "event": f"{operation}_reverted",
            "tx_hash": tx_hex,
            "block": block_number,
            "gas_used": gas_used,
        })
        return False

    logger.info(
        "  ✅ Confirmed in block %d  (gas: %d)", block_number, gas_used,
    )

    # ── Verify final state ────────────────────────────────────────────
    try:
        final_paused = contract.functions.paused().call()
    except Exception as e:
        logger.warning("Could not verify final state: %s", e)
        final_paused = None

    expected = not do_unpause  # pause → True, unpause → False
    if final_paused is not None and final_paused != expected:
        logger.error(
            "State verification FAILED: expected paused=%s, got paused=%s",
            expected, final_paused,
        )
        _log_to_file({
            "event": f"{operation}_verify_failed",
            "expected_paused": expected,
            "actual_paused": final_paused,
        })
        return False

    # ── Success ───────────────────────────────────────────────────────
    logger.info("")
    if do_unpause:
        logger.info("🟢 Bridge UNPAUSED successfully.")
    else:
        logger.info("🔴 Bridge PAUSED successfully.")
    logger.info("  Tx:    %s", tx_hex)
    logger.info("  Block: %d", block_number)
    logger.info("  Gas:   %d", gas_used)
    logger.info("  Log:   %s", LOG_FILE)

    _log_to_file({
        "event": f"{operation}_success",
        "tx_hash": tx_hex,
        "block": block_number,
        "gas_used": gas_used,
        "chain_id": chain_id,
        "caller": account.address,
        "bridge": bridge_address,
    })

    return True


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emergency pause/unpause the RingsBridge contract.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Emergency pause (immediate, no confirmation):
  python scripts/emergency_pause.py

  # Unpause after incident resolution:
  python scripts/emergency_pause.py --unpause

  # With explicit config:
  python scripts/emergency_pause.py \\
      --rpc-url https://sepolia.drpc.org \\
      --bridge-address 0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca
        """,
    )
    parser.add_argument(
        "--unpause",
        action="store_true",
        help="Unpause the bridge instead of pausing it",
    )
    parser.add_argument(
        "--rpc-url",
        default=None,
        help="Ethereum RPC URL (default: BRIDGE_RPC_URL env or Sepolia public node)",
    )
    parser.add_argument(
        "--bridge-address",
        default=None,
        help="RingsBridge contract address (default: BRIDGE_ADDRESS env)",
    )
    parser.add_argument(
        "--private-key",
        default=None,
        help="Guardian/admin private key (default: BRIDGE_PRIVATE_KEY env)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    rpc_url = args.rpc_url or os.environ.get("BRIDGE_RPC_URL", DEFAULT_RPC)
    bridge_address = args.bridge_address or os.environ.get("BRIDGE_ADDRESS", "")
    private_key = args.private_key or os.environ.get("BRIDGE_PRIVATE_KEY", "")

    if not bridge_address:
        logger.error("Bridge address required.  Set BRIDGE_ADDRESS env or pass --bridge-address.")
        sys.exit(1)
    if not private_key:
        logger.error("Private key required.  Set BRIDGE_PRIVATE_KEY env or pass --private-key.")
        sys.exit(1)

    success = emergency_pause(
        rpc_url=rpc_url,
        bridge_address=bridge_address,
        private_key=private_key,
        do_unpause=args.unpause,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
