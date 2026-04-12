#!/usr/bin/env python3
"""
Rotate Guardian Role
====================

Safely rotate the ``GUARDIAN_ROLE`` on the RingsBridge contract to a new
address.  The caller must hold ``DEFAULT_ADMIN_ROLE`` (or the role-admin
of ``GUARDIAN_ROLE``).

Workflow:
  1. Read ``GUARDIAN_ROLE`` bytes32 from the contract.
  2. Enumerate current guardian(s) by checking ``hasRole`` for the
     caller and the new address.
  3. Grant ``GUARDIAN_ROLE`` to the new guardian.
  4. Revoke ``GUARDIAN_ROLE`` from the old guardian (caller or explicit
     ``--old-guardian``).
  5. Verify the rotation succeeded on-chain.

Environment Variables
---------------------
BRIDGE_RPC_URL
    Ethereum JSON-RPC endpoint (default: Sepolia public node).
BRIDGE_ADDRESS
    Deployed ``RingsBridge`` contract address.
BRIDGE_PRIVATE_KEY
    Hex private key of the admin account (with or without ``0x``).

Usage
-----
::

    python scripts/rotate_guardian.py --new-guardian 0xNewAddr
    python scripts/rotate_guardian.py --new-guardian 0xNewAddr --old-guardian 0xOldAddr --yes
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rotate_guardian")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_RPC = "https://ethereum-sepolia-rpc.publicnode.com"
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "src" / "asi_build" / "rings" / "bridge" / "artifacts"

# ---------------------------------------------------------------------------
# ABI — only the fragments we need
# ---------------------------------------------------------------------------

ROTATE_ABI = [
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
    {
        "name": "getRoleAdmin",
        "type": "function",
        "inputs": [{"name": "role", "type": "bytes32"}],
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
    },
    {
        "name": "grantRole",
        "type": "function",
        "inputs": [
            {"name": "role", "type": "bytes32"},
            {"name": "account", "type": "address"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "name": "revokeRole",
        "type": "function",
        "inputs": [
            {"name": "role", "type": "bytes32"},
            {"name": "account", "type": "address"},
        ],
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
]


def _load_full_abi() -> list:
    """Try loading the full ABI from artifacts; fall back to inline fragments."""
    abi_path = ARTIFACTS_DIR / "RingsBridge.json"
    if abi_path.exists():
        try:
            with open(abi_path) as f:
                data = json.load(f)
            return data.get("abi", ROTATE_ABI)
        except Exception:
            pass
    return ROTATE_ABI


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

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        logger.error("Cannot connect to RPC: %s", rpc_url)
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


def _wait_for_tx(w3: Any, tx_hash: Any, timeout: int = 120) -> Any:
    """Wait for a transaction receipt with timeout."""
    logger.info("  Waiting for tx %s ...", tx_hash.hex() if hasattr(tx_hash, "hex") else tx_hash)
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


def rotate_guardian(
    rpc_url: str,
    bridge_address: str,
    private_key: str,
    new_guardian: str,
    old_guardian: Optional[str] = None,
    skip_confirm: bool = False,
) -> bool:
    """
    Rotate the GUARDIAN_ROLE to a new address.

    Parameters
    ----------
    rpc_url : str
        Ethereum JSON-RPC URL.
    bridge_address : str
        RingsBridge contract address.
    private_key : str
        Hex private key of the admin account.
    new_guardian : str
        Address to grant GUARDIAN_ROLE to.
    old_guardian : str, optional
        Address to revoke GUARDIAN_ROLE from.  Defaults to the caller.
    skip_confirm : bool
        Skip interactive confirmation (--yes flag).

    Returns
    -------
    bool
        True on success.
    """
    from web3 import Web3

    w3, contract, account = _connect(rpc_url, private_key, bridge_address)

    # ── 1. Read on-chain state ──────────────────────────────────────────
    guardian_role: bytes = contract.functions.GUARDIAN_ROLE().call()
    admin_role: bytes = contract.functions.DEFAULT_ADMIN_ROLE().call()
    role_admin: bytes = contract.functions.getRoleAdmin(guardian_role).call()
    is_paused: bool = contract.functions.paused().call()
    chain_id: int = w3.eth.chain_id

    new_guardian_cs = Web3.to_checksum_address(new_guardian)
    old_guardian_addr = Web3.to_checksum_address(old_guardian) if old_guardian else account.address

    caller_is_admin = contract.functions.hasRole(role_admin, account.address).call()
    old_has_guardian = contract.functions.hasRole(guardian_role, old_guardian_addr).call()
    new_has_guardian = contract.functions.hasRole(guardian_role, new_guardian_cs).call()

    # ── 2. Print current state ──────────────────────────────────────────
    print()
    print("=" * 60)
    print("  Guardian Role Rotation")
    print("=" * 60)
    print(f"  Chain ID:         {chain_id}")
    print(f"  Bridge:           {bridge_address}")
    print(f"  Bridge paused:    {'YES ⚠️' if is_paused else 'no'}")
    print(f"  GUARDIAN_ROLE:     {guardian_role.hex()}")
    print(f"  Role admin:       {role_admin.hex()}")
    print()
    print(f"  Caller:           {account.address}")
    print(f"  Caller is admin:  {'✅ YES' if caller_is_admin else '❌ NO'}")
    print()
    print(f"  Old guardian:     {old_guardian_addr}")
    print(f"  Has GUARDIAN_ROLE: {'YES' if old_has_guardian else 'NO'}")
    print()
    print(f"  New guardian:     {new_guardian_cs}")
    print(f"  Already has role: {'YES (skip grant)' if new_has_guardian else 'no'}")
    print("=" * 60)
    print()

    # ── 3. Pre-flight checks ───────────────────────────────────────────
    if not caller_is_admin:
        logger.error(
            "Caller %s does not have the role-admin for GUARDIAN_ROLE.  "
            "Cannot rotate.",
            account.address,
        )
        return False

    if new_guardian_cs == old_guardian_addr and old_has_guardian:
        logger.error("New guardian == old guardian — nothing to do.")
        return False

    if new_guardian_cs == "0x" + "0" * 40:
        logger.error("Refusing to set guardian to the zero address.")
        return False

    # ── 4. Confirm ─────────────────────────────────────────────────────
    if not skip_confirm:
        answer = input("Proceed with guardian rotation? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            logger.info("Aborted by user.")
            return False

    # ── 5. Grant GUARDIAN_ROLE to new guardian ──────────────────────────
    if not new_has_guardian:
        logger.info("Granting GUARDIAN_ROLE to %s ...", new_guardian_cs)
        tx_hash = contract.functions.grantRole(
            guardian_role, new_guardian_cs
        ).transact()
        receipt = _wait_for_tx(w3, tx_hash)
        if receipt["status"] != 1:
            logger.error("grantRole transaction FAILED (status=0).  Tx: %s", tx_hash.hex())
            return False
        logger.info("  ✅ grantRole confirmed in block %d", receipt["blockNumber"])
    else:
        logger.info("New guardian already has GUARDIAN_ROLE — skipping grant.")

    # ── 6. Revoke GUARDIAN_ROLE from old guardian ──────────────────────
    if old_has_guardian:
        logger.info("Revoking GUARDIAN_ROLE from %s ...", old_guardian_addr)
        tx_hash = contract.functions.revokeRole(
            guardian_role, old_guardian_addr
        ).transact()
        receipt = _wait_for_tx(w3, tx_hash)
        if receipt["status"] != 1:
            logger.error(
                "revokeRole transaction FAILED (status=0).  Tx: %s\n"
                "⚠️  WARNING: New guardian was already granted — both addresses "
                "now hold GUARDIAN_ROLE!  Revoke manually.",
                tx_hash.hex(),
            )
            return False
        logger.info("  ✅ revokeRole confirmed in block %d", receipt["blockNumber"])
    else:
        logger.info("Old guardian did not hold GUARDIAN_ROLE — skipping revoke.")

    # ── 7. Verify ──────────────────────────────────────────────────────
    new_ok = contract.functions.hasRole(guardian_role, new_guardian_cs).call()
    old_ok = contract.functions.hasRole(guardian_role, old_guardian_addr).call()

    print()
    print("── Verification ──────────────────────────────────────────")
    print(f"  New guardian {new_guardian_cs}: hasRole = {new_ok}  {'✅' if new_ok else '❌'}")
    print(f"  Old guardian {old_guardian_addr}: hasRole = {old_ok}  {'✅ revoked' if not old_ok else '⚠️ STILL HAS ROLE'}")
    print()

    if new_ok and not old_ok:
        logger.info("🎉 Guardian rotation complete!")
        return True
    else:
        logger.warning("Rotation verification FAILED — inspect on-chain state.")
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rotate the GUARDIAN_ROLE on RingsBridge to a new address.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive (asks for confirmation):
  python scripts/rotate_guardian.py --new-guardian 0xNewAddr

  # Non-interactive:
  python scripts/rotate_guardian.py --new-guardian 0xNewAddr --yes

  # Explicit old guardian (if not the caller):
  python scripts/rotate_guardian.py --new-guardian 0xNew --old-guardian 0xOld --yes
        """,
    )
    parser.add_argument(
        "--new-guardian",
        required=True,
        help="Address to receive GUARDIAN_ROLE",
    )
    parser.add_argument(
        "--old-guardian",
        default=None,
        help="Address to revoke GUARDIAN_ROLE from (default: caller)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip interactive confirmation",
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
        help="Admin private key (default: BRIDGE_PRIVATE_KEY env)",
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

    success = rotate_guardian(
        rpc_url=rpc_url,
        bridge_address=bridge_address,
        private_key=private_key,
        new_guardian=args.new_guardian,
        old_guardian=args.old_guardian,
        skip_confirm=args.yes,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
