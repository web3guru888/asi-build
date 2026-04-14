#!/usr/bin/env python3
"""
Cross-Chain E2E Integration Test — Sepolia ↔ Base Sepolia ↔ ARC Testnet

Proves multi-chain bridge operations work with REAL on-chain transactions.
Uses ``cast`` (Foundry) for tx submission and reads, and the Python
:class:`RingsTokenLedger` for off-chain balance simulation.

Deployed contracts (same CREATE2 addresses on all 3 chains):
  - Groth16Verifier: 0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59
  - RingsBridge:     0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca
  - BridgedToken:    0x257dDA1fa34eb847060EcB743E808B65099FB497

Usage:
    python3 scripts/cross_chain_e2e.py          # run full suite
    python3 scripts/cross_chain_e2e.py --dry     # read-only (no deposits)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from hashlib import sha3_256
from typing import Dict, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────────────────────────────

BRIDGE_ADDR = "0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca"
VERIFIER_ADDR = "0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59"
TOKEN_ADDR = "0x257dDA1fa34eb847060EcB743E808B65099FB497"

DEPLOYER = "0x35C3770470F57560beBd1C6C74366b0297110Bc2"

# DID used for all cross-chain test deposits
DID_STRING = "did:rings:crosschain_test_agent"

# Pre-compute the bytes32 DID (keccak256 of the UTF-8 string).
# Python's hashlib doesn't have keccak-256, so we use sha3_256
# and also verify with cast.
DID_BYTES32: Optional[str] = None  # set at runtime via cast

CHAINS = {
    "sepolia": {
        "chain_id": 11155111,
        "rpc": "https://ethereum-sepolia-rpc.publicnode.com",
        "native": "ETH",
        "deposit_value": "0.0001ether",      # ~0.0001 ETH
        "deposit_wei": 100_000_000_000_000,  # 1e14
        "explorer": "https://sepolia.etherscan.io/tx/",
    },
    "base_sepolia": {
        "chain_id": 84532,
        "rpc": "https://sepolia.base.org",
        "native": "ETH",
        "deposit_value": "0.0001ether",
        "deposit_wei": 100_000_000_000_000,
        "explorer": "https://sepolia.basescan.org/tx/",
    },
    "arc_testnet": {
        "chain_id": 5042002,
        "rpc": "https://rpc.testnet.arc.network",
        "native": "USDC",
        "deposit_value": "0.01ether",         # 0.01 USDC (18 dec)
        "deposit_wei": 10_000_000_000_000_000,  # 1e16
        "explorer": "https://testnet.arcscan.app/tx/",
    },
}

# ──────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────

def _cast(*args: str, timeout: int = 60) -> str:
    """Run a cast command and return stdout."""
    cmd = ["/root/.foundry/bin/cast"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"cast {' '.join(args[:4])}... failed:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def _cast_no_fail(*args: str, timeout: int = 60) -> Tuple[bool, str]:
    """Run cast, return (success, output_or_error)."""
    cmd = ["/root/.foundry/bin/cast"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, result.stdout.strip()


def _private_key() -> str:
    """Fetch deployer private key from env."""
    key = os.environ.get("DEPLOYER_PRIVATE_KEY", "")
    if not key:
        print("ERROR: DEPLOYER_PRIVATE_KEY not set")
        sys.exit(1)
    return key


def compute_did_bytes32() -> str:
    """Compute keccak256(abi.encodePacked(DID_STRING)) via cast."""
    raw = _cast("keccak", DID_STRING)
    return raw.strip()


def banner(msg: str) -> None:
    width = max(len(msg) + 4, 60)
    print(f"\n{'═' * width}")
    print(f"  {msg}")
    print(f"{'═' * width}")


def step(num: int, msg: str) -> None:
    print(f"\n┌─ Step {num}: {msg}")


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def info(msg: str) -> None:
    print(f"  ℹ️  {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def fail(msg: str) -> None:
    print(f"  ❌ {msg}")


# ──────────────────────────────────────────────────────────────────────
#  Step 0: Pre-flight checks
# ──────────────────────────────────────────────────────────────────────

def preflight() -> Dict[str, int]:
    """Check balances and code on all chains. Returns balances."""
    banner("Pre-flight Checks")

    balances = {}
    for name, chain in CHAINS.items():
        step(0, f"Checking {name} (chain {chain['chain_id']})")

        # Balance
        raw_bal = _cast("balance", DEPLOYER, "--rpc-url", chain["rpc"])
        bal = int(raw_bal)
        balances[name] = bal

        if chain["native"] == "ETH":
            human = f"{bal / 1e18:.6f} ETH"
        else:
            human = f"{bal / 1e18:.6f} USDC"
        info(f"Balance: {human} ({bal} wei)")

        # Check bridge contract has code
        code = _cast("code", BRIDGE_ADDR, "--rpc-url", chain["rpc"])
        if code and code != "0x" and len(code) > 10:
            ok(f"RingsBridge has code ({len(code)//2 - 1} bytes)")
        else:
            fail(f"RingsBridge has NO code at {BRIDGE_ADDR}")
            sys.exit(1)

        # Check deposit nonce
        nonce = _cast(
            "call", BRIDGE_ADDR,
            "depositNonce()(uint256)",
            "--rpc-url", chain["rpc"],
        )
        info(f"Current depositNonce: {nonce}")

    return balances


# ──────────────────────────────────────────────────────────────────────
#  Step 1-3: Deposits on each chain
# ──────────────────────────────────────────────────────────────────────

def deposit_on_chain(
    name: str, chain: dict, did_bytes32: str, pk: str
) -> Optional[str]:
    """Send a deposit tx on *name*. Returns the tx hash or None on failure."""
    step_num = {"sepolia": 1, "base_sepolia": 2, "arc_testnet": 3}[name]
    step(step_num, f"Deposit on {name} ({chain['deposit_value']})")

    nonce_before = int(
        _cast("call", BRIDGE_ADDR, "depositNonce()(uint256)",
               "--rpc-url", chain["rpc"])
    )
    info(f"depositNonce before: {nonce_before}")

    # Build cast send command
    args = [
        "send", BRIDGE_ADDR,
        "deposit(bytes32)",
        did_bytes32,
        "--value", chain["deposit_value"],
        "--rpc-url", chain["rpc"],
        "--private-key", pk,
    ]

    # ARC uses EIP-1559 with USDC gas; Sepolia/Base use EIP-1559 natively
    # Let cast auto-detect gas pricing

    info(f"Sending deposit tx...")
    t0 = time.time()
    success, output = _cast_no_fail(*args, timeout=120)
    elapsed = time.time() - t0

    if not success:
        fail(f"Deposit failed on {name}: {output[:200]}")
        return None

    # Parse tx hash from cast send output
    tx_hash = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("transactionHash"):
            tx_hash = line.split()[-1]
            break
    if not tx_hash:
        # Sometimes cast outputs just the hash
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("0x") and len(line) == 66:
                tx_hash = line
                break

    if tx_hash:
        ok(f"TX: {tx_hash} ({elapsed:.1f}s)")
        ok(f"Explorer: {chain['explorer']}{tx_hash}")
    else:
        warn(f"TX sent but couldn't parse hash from output ({elapsed:.1f}s)")
        info(f"Raw output: {output[:300]}")

    # Verify nonce incremented
    time.sleep(2)  # wait for finality
    nonce_after = int(
        _cast("call", BRIDGE_ADDR, "depositNonce()(uint256)",
               "--rpc-url", chain["rpc"])
    )
    if nonce_after > nonce_before:
        ok(f"depositNonce incremented: {nonce_before} → {nonce_after}")
    else:
        warn(f"depositNonce unchanged: {nonce_before} → {nonce_after}")

    return tx_hash


# ──────────────────────────────────────────────────────────────────────
#  Step 4: Read deposit nonces on all chains
# ──────────────────────────────────────────────────────────────────────

def read_all_nonces() -> Dict[str, int]:
    """Read depositNonce() on every chain."""
    step(4, "Reading deposit nonces on all chains")
    nonces = {}
    for name, chain in CHAINS.items():
        nonce = int(
            _cast("call", BRIDGE_ADDR, "depositNonce()(uint256)",
                   "--rpc-url", chain["rpc"])
        )
        nonces[name] = nonce
        info(f"{name:15s}  depositNonce = {nonce}")
    ok("All nonces read successfully")
    return nonces


# ──────────────────────────────────────────────────────────────────────
#  Step 5: Ledger simulation
# ──────────────────────────────────────────────────────────────────────

class MockDHTClient:
    """Minimal mock DHT client for ledger simulation.

    Stores data in memory — no real Rings DHT needed.
    """

    def __init__(self) -> None:
        self._store: Dict[str, str] = {}

    async def dht_put(self, key: str, value: str) -> None:
        self._store[key] = value

    async def dht_get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def broadcast(self, topic: str, data: str) -> None:
        pass  # no-op for simulation


async def ledger_simulation(deposit_results: Dict[str, Optional[str]]) -> bool:
    """Credit deposits from each chain, verify chain-agnostic balances."""
    step(5, "Ledger simulation — chain-agnostic balance aggregation")

    # Add the project to sys.path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

    from asi_build.rings.bridge.ledger import RingsTokenLedger

    client = MockDHTClient()
    ledger = RingsTokenLedger(client, threshold=1, total=1)

    did = f"did:rings:crosschain_test_agent"

    # Credit from each chain where deposit succeeded
    credit_map = {
        "sepolia": ("ETH", CHAINS["sepolia"]["deposit_wei"]),
        "base_sepolia": ("ETH", CHAINS["base_sepolia"]["deposit_wei"]),
        "arc_testnet": ("USDC", CHAINS["arc_testnet"]["deposit_wei"]),
    }

    total_eth = 0
    total_usdc = 0
    credits_done = 0

    for chain_name, (token, amount) in credit_map.items():
        # Credit even if on-chain deposit was skipped (dry run) for
        # demonstration, but mark clearly
        was_real = deposit_results.get(chain_name) is not None
        tag = "REAL" if was_real else "SIMULATED"

        await ledger.credit_from_bridge(
            did=did, token=token, amount=amount,
            source_chain=chain_name,
        )
        credits_done += 1

        if token == "ETH":
            total_eth += amount
        else:
            total_usdc += amount

        info(f"Credited {amount} {token} from {chain_name} [{tag}]")

    # Check balances — ETH is aggregated from Sepolia + Base
    eth_balance = await ledger.balance(did, "ETH")
    usdc_balance = await ledger.balance(did, "USDC")

    info(f"ETH  balance: {eth_balance} wei ({eth_balance / 1e18:.6f} ETH)")
    info(f"USDC balance: {usdc_balance} wei ({usdc_balance / 1e18:.6f} USDC)")

    passed = True
    if eth_balance == total_eth:
        ok(f"ETH balance correct — chain-agnostic aggregation works "
           f"({total_eth} from 2 chains)")
    else:
        fail(f"ETH balance mismatch: expected {total_eth}, got {eth_balance}")
        passed = False

    if usdc_balance == total_usdc:
        ok(f"USDC balance correct — {total_usdc} from ARC")
    else:
        fail(f"USDC balance mismatch: expected {total_usdc}, got {usdc_balance}")
        passed = False

    # Check stats
    stats = ledger.stats
    info(f"Ledger stats: {stats}")
    if stats.get("credits", 0) == credits_done:
        ok(f"Credit count matches: {credits_done}")
    else:
        warn(f"Credit count mismatch: expected {credits_done}, got {stats}")

    return passed


# ──────────────────────────────────────────────────────────────────────
#  Step 6: Cross-chain withdrawal lock
# ──────────────────────────────────────────────────────────────────────

async def cross_chain_withdrawal(deposit_results: Dict[str, Optional[str]]) -> bool:
    """Lock funds for withdrawal targeting a different chain than deposit."""
    step(6, "Cross-chain withdrawal — deposit on Sepolia, withdraw to Base")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from asi_build.rings.bridge.ledger import RingsTokenLedger

    client = MockDHTClient()
    ledger = RingsTokenLedger(client, threshold=1, total=1)

    did = "did:rings:crosschain_test_agent"

    # Simulate: user deposited on Sepolia
    deposit_amount = CHAINS["sepolia"]["deposit_wei"]
    await ledger.credit_from_bridge(
        did=did, token="ETH", amount=deposit_amount,
        source_chain="ethereum_sepolia",
    )
    ok(f"Credited {deposit_amount} ETH from Sepolia")

    bal_before = await ledger.balance(did, "ETH")
    info(f"Balance before withdrawal lock: {bal_before}")

    # Lock for withdrawal targeting Base Sepolia (different chain!)
    withdrawal_amount = deposit_amount // 2  # withdraw half
    lock = await ledger.debit_for_withdrawal(
        did=did, token="ETH", amount=withdrawal_amount,
        target_chain="base_sepolia",  # ← cross-chain!
    )

    ok(f"Withdrawal lock created: {lock.lock_id}")
    info(f"  Amount: {lock.amount} ETH")
    info(f"  Target chain: {lock.target_chain}")
    info(f"  DID: {lock.did}")

    # Verify available balance decreased
    available = await ledger.available_balance(did, "ETH")
    expected_available = deposit_amount - withdrawal_amount
    if available == expected_available:
        ok(f"Available balance correct: {available} "
           f"({deposit_amount} - {withdrawal_amount} locked)")
    else:
        fail(f"Available balance wrong: {available} != {expected_available}")
        return False

    # Total balance should still be full (locked, not deducted yet)
    total_bal = await ledger.balance(did, "ETH")
    if total_bal == deposit_amount:
        ok("Total balance unchanged (funds locked, not released)")
    else:
        warn(f"Total balance: {total_bal} (expected {deposit_amount})")

    # Release the lock (simulates successful on-chain withdrawal)
    await ledger.release_withdrawal_lock(lock.lock_id)
    ok("Withdrawal lock released (simulates on-chain withdrawal)")

    # Now the balance should be reduced
    final_bal = await ledger.balance(did, "ETH")
    if final_bal == expected_available:
        ok(f"Final balance after withdrawal: {final_bal} ✓")
    else:
        fail(f"Final balance: {final_bal}, expected {expected_available}")
        return False

    return True


# ──────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-chain E2E bridge test")
    parser.add_argument(
        "--dry", action="store_true",
        help="Dry run — skip on-chain deposits, run ledger simulation only",
    )
    args = parser.parse_args()

    banner("Cross-Chain E2E Integration Test")
    print(f"  Bridge:   {BRIDGE_ADDR}")
    print(f"  Verifier: {VERIFIER_ADDR}")
    print(f"  Token:    {TOKEN_ADDR}")
    print(f"  Deployer: {DEPLOYER}")
    print(f"  DID:      {DID_STRING}")
    print(f"  Mode:     {'DRY RUN' if args.dry else 'LIVE'}")
    print(f"  Time:     {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")

    # Compute DID bytes32
    global DID_BYTES32
    DID_BYTES32 = compute_did_bytes32()
    info(f"DID bytes32: {DID_BYTES32}")

    # Pre-flight
    balances = preflight()

    # ── On-chain deposits ────────────────────────────────────────────
    deposit_results: Dict[str, Optional[str]] = {}

    if args.dry:
        banner("DRY RUN — Skipping On-chain Deposits")
        for name in CHAINS:
            deposit_results[name] = None
    else:
        pk = _private_key()
        banner("On-chain Deposits (3 chains)")

        for name, chain in CHAINS.items():
            # Check minimum balance
            bal = balances[name]
            needed = chain["deposit_wei"] * 2  # 2x for gas margin
            if bal < needed:
                warn(f"Skipping {name}: balance too low "
                     f"({bal} < {needed} needed)")
                deposit_results[name] = None
                continue

            tx_hash = deposit_on_chain(name, chain, DID_BYTES32, pk)
            deposit_results[name] = tx_hash

            # Brief pause between chains to avoid nonce issues
            time.sleep(1)

    # ── Read all nonces ──────────────────────────────────────────────
    nonces = read_all_nonces()

    # ── Ledger simulation ────────────────────────────────────────────
    banner("Ledger Simulation")
    ledger_ok = asyncio.run(ledger_simulation(deposit_results))

    # ── Cross-chain withdrawal ───────────────────────────────────────
    banner("Cross-Chain Withdrawal")
    withdrawal_ok = asyncio.run(cross_chain_withdrawal(deposit_results))

    # ── Summary ──────────────────────────────────────────────────────
    banner("RESULTS SUMMARY")

    chains_deposited = sum(1 for v in deposit_results.values() if v)
    chains_total = len(CHAINS)

    print(f"\n  On-chain deposits: {chains_deposited}/{chains_total} succeeded")
    for name, tx in deposit_results.items():
        status = f"✅ {tx[:18]}..." if tx else "⏭️  skipped"
        print(f"    {name:15s}: {status}")

    print(f"\n  Deposit nonces (post-test):")
    for name, nonce in nonces.items():
        print(f"    {name:15s}: {nonce}")

    print(f"\n  Ledger simulation: {'✅ PASS' if ledger_ok else '❌ FAIL'}")
    print(f"  Cross-chain withdrawal: {'✅ PASS' if withdrawal_ok else '❌ FAIL'}")

    all_pass = ledger_ok and withdrawal_ok
    if not args.dry:
        all_pass = all_pass and chains_deposited >= 2  # at least 2/3 chains

    print(f"\n  {'🎉 ALL TESTS PASSED' if all_pass else '⚠️  SOME TESTS FAILED'}")
    print()

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
