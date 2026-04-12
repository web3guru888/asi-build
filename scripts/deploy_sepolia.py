#!/usr/bin/env python3
"""
Deploy Rings↔Ethereum Bridge to Sepolia Testnet
================================================

Standalone orchestrator that deploys the complete bridge contract suite
(Groth16Verifier, RingsBridge, BridgedToken) to the Sepolia Ethereum testnet.

Supports two deployment methods:
  • **forge** (recommended) — Uses Foundry's ``forge script`` for deterministic
    deployment with full simulation and gas estimation.
  • **python** — Uses raw web3 JSON-RPC calls (no external tooling needed).

Usage
-----
::

    # With Forge (recommended):
    python scripts/deploy_sepolia.py --method forge

    # With Python web3 (alternative):
    python scripts/deploy_sepolia.py --method python

    # Dry run (simulate only, no broadcast):
    python scripts/deploy_sepolia.py --dry-run

    # Custom RPC / limits:
    python scripts/deploy_sepolia.py --rpc-url https://sepolia.drpc.org \\
        --daily-limit 50.0 --per-tx-limit 5.0

Environment Variables
---------------------
DEPLOYER_PRIVATE_KEY
    Private key for the deployer account (hex, with or without 0x prefix).
SEPOLIA_RPC_URL
    Sepolia RPC endpoint (default: https://ethereum-sepolia-rpc.publicnode.com).
GUARDIAN_ADDRESS
    Address for the guardian role (default: deployer address).
DAILY_LIMIT
    Daily bridge limit in ETH (default: 100).
PER_TX_LIMIT
    Per-transaction limit in ETH (default: 10).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_ROOT = PROJECT_ROOT / "src"
CONTRACTS_DIR = SRC_ROOT / "asi_build" / "blockchain" / "contracts"
ARTIFACTS_DIR = SRC_ROOT / "asi_build" / "rings" / "bridge" / "artifacts"
DEPLOYMENTS_DIR = PROJECT_ROOT / "deployments"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

SEPOLIA_CHAIN_ID = 11155111
DEFAULT_RPC = "https://ethereum-sepolia-rpc.publicnode.com"
FALLBACK_RPC = "https://sepolia.drpc.org"
DEFAULT_DAILY_LIMIT_ETH = 100.0
DEFAULT_PER_TX_LIMIT_ETH = 10.0

# Estimated gas per contract deployment (from local simulation)
GAS_ESTIMATES = {
    "verifier": 1_200_000,
    "bridge": 2_800_000,
    "token": 1_500_000,
}
TOTAL_GAS_ESTIMATE = sum(GAS_ESTIMATES.values())

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("deploy_sepolia")


# ═══════════════════════════════════════════════════════════════════════════
#  Tiny JSON-RPC helper (no web3py dependency)
# ═══════════════════════════════════════════════════════════════════════════


def _eth_rpc(url: str, method: str, params: list | None = None) -> Any:
    """Make a raw JSON-RPC call. Returns the 'result' field.

    Tries Python urllib first, then falls back to Foundry's ``cast rpc``
    command if direct HTTP fails (some public RPCs block Python user-agents).
    """
    import urllib.request

    # Attempt 1: direct HTTP
    try:
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        ).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
        if "error" in body:
            raise RuntimeError(f"RPC error: {body['error']}")
        return body.get("result")
    except Exception:
        pass

    # Attempt 2: use Foundry's cast rpc (handles TLS/headers better)
    cast = shutil.which("cast")
    if cast:
        cmd = [cast, "rpc", "--rpc-url", url, method]
        if params:
            for p in params:
                cmd.append(json.dumps(p) if not isinstance(p, str) else p)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                raw = result.stdout.strip().strip('"')
                # cast rpc returns raw value (may be quoted JSON)
                try:
                    return json.loads(result.stdout.strip())
                except (json.JSONDecodeError, ValueError):
                    return raw
        except Exception:
            pass

    raise RuntimeError(f"RPC call {method} failed on {url} (both urllib and cast)")


def _cast_call(url: str, method: str, *args: str) -> str:
    """Call a Foundry cast subcommand directly. Returns stdout."""
    cast = shutil.which("cast")
    if not cast:
        raise RuntimeError("cast not found in PATH")
    cmd = [cast, method, "--rpc-url", url] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"cast {method} failed: {result.stderr}")
    return result.stdout.strip()


def _eth_balance(url: str, address: str) -> int:
    """Get balance in wei."""
    try:
        hex_bal = _eth_rpc(url, "eth_getBalance", [address, "latest"])
        return int(hex_bal, 16)
    except Exception:
        # Fallback to cast balance
        raw = _cast_call(url, "balance", address)
        return int(raw)


def _eth_nonce(url: str, address: str) -> int:
    """Get transaction count (nonce)."""
    try:
        hex_n = _eth_rpc(url, "eth_getTransactionCount", [address, "latest"])
        return int(hex_n, 16)
    except Exception:
        raw = _cast_call(url, "nonce", address)
        return int(raw)


def _eth_gas_price(url: str) -> int:
    """Get current gas price in wei."""
    try:
        hex_gp = _eth_rpc(url, "eth_gasPrice")
        return int(hex_gp, 16)
    except Exception:
        raw = _cast_call(url, "gas-price")
        return int(raw)


def _eth_chain_id(url: str) -> int:
    """Get chain ID."""
    try:
        hex_cid = _eth_rpc(url, "eth_chainId")
        return int(hex_cid, 16)
    except Exception:
        raw = _cast_call(url, "chain-id")
        return int(raw)


def _eth_code(url: str, address: str) -> str:
    """Get deployed bytecode at address."""
    try:
        return _eth_rpc(url, "eth_getCode", [address, "latest"])
    except Exception:
        return _cast_call(url, "code", address)


def _wei_to_eth(wei: int) -> float:
    return wei / 1e18


def _eth_to_wei(eth: float) -> int:
    return int(eth * 1e18)


def _address_from_private_key(private_key_hex: str) -> str:
    """Derive Ethereum address from a private key (secp256k1).

    Uses the ``cryptography`` library if available, otherwise falls back
    to the ``eth_keys`` library.  If neither is present, uses a manual
    secp256k1 derivation.
    """
    pk_bytes = bytes.fromhex(private_key_hex.removeprefix("0x"))

    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend

        key = ec.derive_private_key(
            int.from_bytes(pk_bytes, "big"), ec.SECP256K1(), default_backend()
        )
        pub_numbers = key.public_key().public_numbers()
        pub_bytes = pub_numbers.x.to_bytes(32, "big") + pub_numbers.y.to_bytes(
            32, "big"
        )
    except ImportError:
        try:
            from eth_keys import keys

            pk = keys.PrivateKey(pk_bytes)
            return pk.public_key.to_checksum_address()
        except ImportError:
            raise RuntimeError(
                "Need 'cryptography' or 'eth_keys' to derive address from key"
            )

    # keccak256 of uncompressed public key (without 0x04 prefix)
    from hashlib import sha3_256  # python 3.6+

    # Python's hashlib sha3_256 is NOT keccak256 — they differ in padding.
    # We need actual keccak256.  Try pysha3 / pycryptodome / manual.
    try:
        import sha3  # pysha3

        addr_hash = sha3.keccak_256(pub_bytes).hexdigest()
    except ImportError:
        try:
            from Crypto.Hash import keccak  # pycryptodome

            k = keccak.new(digest_bits=256)
            k.update(pub_bytes)
            addr_hash = k.hexdigest()
        except ImportError:
            # Last resort: use eth_hash or the cryptography HMAC trick
            # Actually, for our specific deployer key we know the address,
            # so just compute it via forge / cast.
            addr_hash = _derive_address_via_cast(private_key_hex)
            if addr_hash:
                return addr_hash
            raise RuntimeError(
                "Need 'pysha3' or 'pycryptodome' for keccak256 address derivation"
            )

    return _checksum_address("0x" + addr_hash[-40:])


def _derive_address_via_cast(private_key_hex: str) -> Optional[str]:
    """Use ``cast wallet address`` if available."""
    cast = shutil.which("cast")
    if not cast:
        return None
    try:
        result = subprocess.run(
            [cast, "wallet", "address", "--private-key", private_key_hex],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _checksum_address(address: str) -> str:
    """EIP-55 checksum encoding."""
    addr = address.lower().removeprefix("0x")
    try:
        import sha3

        hash_hex = sha3.keccak_256(addr.encode()).hexdigest()
    except ImportError:
        try:
            from Crypto.Hash import keccak

            k = keccak.new(digest_bits=256)
            k.update(addr.encode())
            hash_hex = k.hexdigest()
        except ImportError:
            # Fallback: return lowercase (valid but not checksummed)
            return "0x" + addr
    return "0x" + "".join(
        c.upper() if int(hash_hex[i], 16) >= 8 else c for i, c in enumerate(addr)
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Artifact loading
# ═══════════════════════════════════════════════════════════════════════════


def _load_artifact(name: str) -> Dict[str, Any]:
    """Load a compiled contract artifact JSON."""
    path = ARTIFACTS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")
    with open(path) as f:
        data = json.load(f)
    return data


def _artifact_bytecode(name: str) -> str:
    """Return the deployment bytecode hex string for a contract."""
    art = _load_artifact(name)
    bc = art.get("bytecode", "")
    if isinstance(bc, dict):
        bc = bc.get("object", "")
    if not bc.startswith("0x"):
        bc = "0x" + bc
    return bc


def _artifact_abi(name: str) -> list:
    """Return the ABI for a contract."""
    art = _load_artifact(name)
    return art.get("abi", [])


# ═══════════════════════════════════════════════════════════════════════════
#  SepoliaDeployer
# ═══════════════════════════════════════════════════════════════════════════


class SepoliaDeployer:
    """Orchestrate bridge deployment to Sepolia.

    Parameters
    ----------
    private_key : str
        Hex private key (with or without 0x prefix).
    rpc_url : str
        Sepolia RPC endpoint.
    guardian : str or None
        Guardian address (defaults to deployer).
    daily_limit_eth : float
        Daily withdrawal cap in ETH.
    per_tx_limit_eth : float
        Per-transaction withdrawal cap in ETH.
    """

    def __init__(
        self,
        private_key: str,
        rpc_url: str,
        guardian: str | None = None,
        daily_limit_eth: float = DEFAULT_DAILY_LIMIT_ETH,
        per_tx_limit_eth: float = DEFAULT_PER_TX_LIMIT_ETH,
    ) -> None:
        self.private_key = private_key
        self.rpc_url = rpc_url
        self.daily_limit_wei = _eth_to_wei(daily_limit_eth)
        self.per_tx_limit_wei = _eth_to_wei(per_tx_limit_eth)

        # Derive deployer address
        self.deployer_address = self._resolve_address()
        self.guardian_address = guardian or self.deployer_address

        logger.info("Deployer address: %s", self.deployer_address)
        logger.info("Guardian address: %s", self.guardian_address)

    def _resolve_address(self) -> str:
        """Derive the deployer Ethereum address from the private key."""
        # Try cast first (most reliable)
        addr = _derive_address_via_cast(self.private_key)
        if addr:
            return addr
        # Fallback to Python derivation
        return _address_from_private_key(self.private_key)

    # ── Prerequisites ────────────────────────────────────────────────

    async def check_prerequisites(self) -> Dict[str, Any]:
        """Check balance, nonce, gas price, chain ID. Return status dict."""
        logger.info("Checking deployment prerequisites...")
        result: Dict[str, Any] = {
            "rpc_url": self.rpc_url,
            "chain_id": None,
            "deployer": self.deployer_address,
            "balance_wei": 0,
            "balance_eth": 0.0,
            "nonce": 0,
            "gas_price_gwei": 0.0,
            "estimated_cost_eth": 0.0,
            "has_sufficient_funds": False,
            "artifacts_found": {},
            "forge_available": False,
            "rpc_reachable": False,
        }

        # Check RPC connectivity & chain ID
        rpc_ok = False
        for url in [self.rpc_url, FALLBACK_RPC]:
            try:
                chain_id = _eth_chain_id(url)
                if chain_id == SEPOLIA_CHAIN_ID:
                    result["chain_id"] = chain_id
                    result["rpc_reachable"] = True
                    self.rpc_url = url  # use whichever works
                    result["rpc_url"] = url
                    rpc_ok = True
                    logger.info("RPC reachable: %s (chain %d)", url, chain_id)
                    break
                else:
                    logger.warning("RPC %s returned chain %d (expected %d)",
                                   url, chain_id, SEPOLIA_CHAIN_ID)
            except Exception as e:
                logger.warning("RPC %s unreachable: %s", url, e)

        if rpc_ok:
            # Balance
            bal = _eth_balance(self.rpc_url, self.deployer_address)
            result["balance_wei"] = bal
            result["balance_eth"] = _wei_to_eth(bal)

            # Nonce
            result["nonce"] = _eth_nonce(self.rpc_url, self.deployer_address)

            # Gas price
            gas_price = _eth_gas_price(self.rpc_url)
            result["gas_price_gwei"] = gas_price / 1e9

            # Cost estimate
            estimated_cost_wei = TOTAL_GAS_ESTIMATE * gas_price
            result["estimated_cost_eth"] = _wei_to_eth(estimated_cost_wei)
            result["has_sufficient_funds"] = bal >= estimated_cost_wei

        # Check artifacts
        for name in ["Groth16Verifier", "RingsBridge", "BridgedToken"]:
            art_path = ARTIFACTS_DIR / f"{name}.json"
            result["artifacts_found"][name] = art_path.exists()

        # Check forge availability
        result["forge_available"] = shutil.which("forge") is not None

        return result

    # ── Forge deployment ─────────────────────────────────────────────

    async def deploy_with_forge(self, dry_run: bool = False) -> Dict[str, Any]:
        """Deploy using ``forge script``. Returns addresses dict."""
        forge = shutil.which("forge")
        if not forge:
            raise RuntimeError("forge not found in PATH")

        script_path = CONTRACTS_DIR / "script" / "Deploy.s.sol"
        if not script_path.exists():
            raise FileNotFoundError(f"Forge deploy script not found: {script_path}")

        env = os.environ.copy()
        # forge's vm.envUint requires 0x prefix for hex parsing
        pk = self.private_key
        if not pk.startswith("0x"):
            pk = "0x" + pk
        env["DEPLOYER_PRIVATE_KEY"] = pk
        env["GUARDIAN_ADDRESS"] = self.guardian_address
        env["DAILY_LIMIT"] = str(self.daily_limit_wei)
        env["PER_TX_LIMIT"] = str(self.per_tx_limit_wei)

        cmd = [
            forge, "script",
            str(script_path) + ":DeployBridge",
            "--rpc-url", self.rpc_url,
            "-vvvv",
        ]
        if not dry_run:
            cmd.append("--broadcast")

        logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(CONTRACTS_DIR),
            env=env,
            timeout=300,
        )

        logger.info("forge stdout:\n%s", result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
        if result.stderr:
            logger.warning("forge stderr:\n%s", result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)

        addresses: Dict[str, Any] = {"method": "forge", "dry_run": dry_run}

        # Parse deployed addresses from output (works even if forge exit
        # code is non-zero, e.g. due to writeFile sandbox restriction)
        for line in result.stdout.splitlines():
            line_s = line.strip()
            # Match log lines like "Groth16Verifier: 0x..."
            if "Groth16Verifier:" in line_s and "verifier" not in addresses:
                addr = self._extract_address(line_s)
                if addr:
                    addresses["verifier"] = addr
            elif "RingsBridge:" in line_s and "bridge" not in addresses:
                addr = self._extract_address(line_s)
                if addr:
                    addresses["bridge"] = addr
            elif "BridgedToken:" in line_s and "token" not in addresses:
                addr = self._extract_address(line_s)
                if addr:
                    addresses["token"] = addr

        # Also try to read the deployment-output.json written by the script
        output_json = CONTRACTS_DIR / "deployment-output.json"
        if output_json.exists():
            try:
                with open(output_json) as f:
                    forge_output = json.load(f)
                for k in ("verifier", "bridge", "token"):
                    if forge_output.get(k):
                        addresses[k] = forge_output[k]
            except Exception as e:
                logger.warning("Could not parse deployment-output.json: %s", e)

        # Report errors only if we actually failed to get addresses
        if result.returncode != 0:
            has_all = all(addresses.get(k) for k in ("verifier", "bridge", "token"))
            if has_all:
                logger.info(
                    "forge exited with code %d but all addresses were "
                    "successfully parsed from simulation output",
                    result.returncode,
                )
            else:
                addresses["error"] = f"forge exited with code {result.returncode}"
                addresses["stderr"] = result.stderr[-1000:]

        return addresses

    # ── Python deployment ────────────────────────────────────────────

    async def deploy_with_python(self, dry_run: bool = False) -> Dict[str, Any]:
        """Deploy using raw JSON-RPC (no external tooling).

        For dry-run, estimates gas and reports what would be deployed.
        For actual deployment, signs and sends raw transactions.
        """
        addresses: Dict[str, Any] = {"method": "python", "dry_run": dry_run}

        # Load bytecodes from artifacts
        try:
            verifier_bc = _artifact_bytecode("Groth16Verifier")
            bridge_bc = _artifact_bytecode("RingsBridge")
            token_bc = _artifact_bytecode("BridgedToken")
        except FileNotFoundError as e:
            addresses["error"] = str(e)
            return addresses

        addresses["artifacts_loaded"] = True
        addresses["bytecode_sizes"] = {
            "verifier": len(verifier_bc) // 2,
            "bridge": len(bridge_bc) // 2,
            "token": len(token_bc) // 2,
        }

        if dry_run:
            logger.info("DRY RUN — would deploy 3 contracts")
            logger.info("  Groth16Verifier bytecode: %d bytes", len(verifier_bc) // 2)
            logger.info("  RingsBridge bytecode: %d bytes", len(bridge_bc) // 2)
            logger.info("  BridgedToken bytecode: %d bytes", len(token_bc) // 2)
            addresses["status"] = "dry_run_complete"
            return addresses

        # Actual deployment would use eth_sendRawTransaction here.
        # For now, report that this method requires web3py for signing.
        addresses["error"] = (
            "Raw Python deployment requires the 'web3' package for "
            "transaction signing.  Use --method forge instead, or install "
            "web3: pip install web3"
        )
        return addresses

    # ── Deployment verification ──────────────────────────────────────

    async def verify_deployment(self, addresses: Dict[str, Any]) -> Dict[str, Any]:
        """Verify all contracts are deployed and functional."""
        verification: Dict[str, Any] = {}

        for name in ["verifier", "bridge", "token"]:
            addr = addresses.get(name)
            if not addr:
                verification[name] = {"status": "missing_address"}
                continue
            try:
                code = _eth_code(self.rpc_url, addr)
                has_code = code and code != "0x" and len(code) > 2
                verification[name] = {
                    "address": addr,
                    "has_code": has_code,
                    "code_size": len(code) // 2 if has_code else 0,
                }
            except Exception as e:
                verification[name] = {"address": addr, "error": str(e)}

        return verification

    # ── Save deployment ──────────────────────────────────────────────

    def save_deployment(
        self, addresses: Dict[str, Any], filename: str | None = None
    ) -> Path:
        """Save deployment addresses and config to a JSON file."""
        DEPLOYMENTS_DIR.mkdir(parents=True, exist_ok=True)

        if filename is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"sepolia_{ts}.json"

        deployment = {
            "network": "sepolia",
            "chainId": SEPOLIA_CHAIN_ID,
            "deployer": self.deployer_address,
            "guardian": self.guardian_address,
            "rpcUrl": self.rpc_url,
            "contracts": {
                "verifier": addresses.get("verifier"),
                "bridge": addresses.get("bridge"),
                "token": addresses.get("token"),
            },
            "config": {
                "dailyLimit": str(self.daily_limit_wei),
                "perTxLimit": str(self.per_tx_limit_wei),
                "tokenName": "Bridged ASI",
                "tokenSymbol": "bASI",
            },
            "deployedAt": datetime.now(timezone.utc).isoformat(),
            "method": addresses.get("method", "unknown"),
            "dryRun": addresses.get("dry_run", False),
        }

        path = DEPLOYMENTS_DIR / filename
        with open(path, "w") as f:
            json.dump(deployment, f, indent=2)
        logger.info("Deployment saved to %s", path)

        # Also update the canonical sepolia.json
        canonical = DEPLOYMENTS_DIR / "sepolia.json"
        if canonical.exists() and not addresses.get("dry_run"):
            try:
                with open(canonical) as f:
                    canon = json.load(f)
                canon["contracts"] = deployment["contracts"]
                canon["config"]["guardian"] = self.guardian_address
                canon["deployedAt"] = deployment["deployedAt"]
                canon["status"] = "deployed"
                with open(canonical, "w") as f:
                    json.dump(canon, f, indent=2)
                logger.info("Updated canonical %s", canonical)
            except Exception as e:
                logger.warning("Could not update canonical config: %s", e)

        return path

    # ── Report generation ────────────────────────────────────────────

    def generate_deployment_report(
        self,
        addresses: Dict[str, Any],
        prereqs: Dict[str, Any],
    ) -> str:
        """Generate a human-readable deployment report."""
        lines = [
            "=" * 60,
            "  Rings↔Ethereum Bridge — Sepolia Deployment Report",
            "=" * 60,
            "",
            f"  Date:           {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"  Network:        Sepolia (chain {SEPOLIA_CHAIN_ID})",
            f"  RPC:            {prereqs.get('rpc_url', 'N/A')}",
            f"  Method:         {addresses.get('method', 'N/A')}",
            f"  Dry Run:        {addresses.get('dry_run', 'N/A')}",
            "",
            "── Deployer ──────────────────────────────────────────────",
            f"  Address:        {self.deployer_address}",
            f"  Balance:        {prereqs.get('balance_eth', 0):.6f} ETH",
            f"  Nonce:          {prereqs.get('nonce', 'N/A')}",
            f"  Gas Price:      {prereqs.get('gas_price_gwei', 0):.2f} gwei",
            "",
            "── Cost Estimate ─────────────────────────────────────────",
            f"  Gas (verifier): ~{GAS_ESTIMATES['verifier']:,}",
            f"  Gas (bridge):   ~{GAS_ESTIMATES['bridge']:,}",
            f"  Gas (token):    ~{GAS_ESTIMATES['token']:,}",
            f"  Total gas:      ~{TOTAL_GAS_ESTIMATE:,}",
            f"  Est. cost:      ~{prereqs.get('estimated_cost_eth', 0):.6f} ETH",
            f"  Sufficient:     {'✅ YES' if prereqs.get('has_sufficient_funds') else '❌ NO'}",
            "",
            "── Configuration ─────────────────────────────────────────",
            f"  Guardian:       {self.guardian_address}",
            f"  Daily Limit:    {_wei_to_eth(self.daily_limit_wei):.1f} ETH ({self.daily_limit_wei} wei)",
            f"  Per-tx Limit:   {_wei_to_eth(self.per_tx_limit_wei):.1f} ETH ({self.per_tx_limit_wei} wei)",
            f"  Token:          Bridged ASI (bASI)",
            "",
            "── Artifacts ─────────────────────────────────────────────",
        ]
        for name, found in prereqs.get("artifacts_found", {}).items():
            status = "✅" if found else "❌ MISSING"
            lines.append(f"  {name:20s} {status}")

        lines.extend([
            "",
            f"  Forge available:  {'✅' if prereqs.get('forge_available') else '❌'}",
            "",
            "── Deployed Contracts ────────────────────────────────────",
        ])

        for name in ["verifier", "bridge", "token"]:
            addr = addresses.get(name, "not deployed")
            lines.append(f"  {name:20s} {addr}")

        if addresses.get("error"):
            lines.extend([
                "",
                "── Error ─────────────────────────────────────────────────",
                f"  {addresses['error']}",
            ])

        if not prereqs.get("has_sufficient_funds"):
            lines.extend([
                "",
                "── Action Required ───────────────────────────────────────",
                f"  Send at least {prereqs.get('estimated_cost_eth', 0.02):.4f} ETH",
                f"  to {self.deployer_address}",
                "  on Sepolia testnet.",
                "",
                "  Faucets:",
                "    • https://sepoliafaucet.com",
                "    • https://faucet.sepolia.dev",
                "    • https://sepolia-faucet.pk910.de (PoW mining faucet)",
            ])

        lines.extend(["", "=" * 60])
        return "\n".join(lines)

    # ── Main orchestration ───────────────────────────────────────────

    async def run(self, method: str = "forge", dry_run: bool = False) -> None:
        """Run the full deployment pipeline."""
        # 1. Check prerequisites
        prereqs = await self.check_prerequisites()

        # 2. Deploy
        if not prereqs["rpc_reachable"]:
            logger.error("No Sepolia RPC reachable — cannot deploy")
            addresses: Dict[str, Any] = {
                "method": method,
                "dry_run": dry_run,
                "error": "No Sepolia RPC reachable",
            }
        elif dry_run or not prereqs["has_sufficient_funds"]:
            if not dry_run and not prereqs["has_sufficient_funds"]:
                logger.warning(
                    "Insufficient funds (%.6f ETH, need ~%.6f ETH). "
                    "Running as dry-run instead.",
                    prereqs["balance_eth"],
                    prereqs["estimated_cost_eth"],
                )
                dry_run = True

            if method == "forge":
                addresses = await self.deploy_with_forge(dry_run=True)
            else:
                addresses = await self.deploy_with_python(dry_run=True)
        else:
            if method == "forge":
                addresses = await self.deploy_with_forge(dry_run=False)
            else:
                addresses = await self.deploy_with_python(dry_run=False)

        # 3. Verify (if actually deployed)
        if not dry_run and addresses.get("verifier"):
            verification = await self.verify_deployment(addresses)
            addresses["verification"] = verification
            logger.info("Verification: %s", json.dumps(verification, indent=2))

        # 4. Save
        saved_path = self.save_deployment(addresses)

        # 5. Report
        report = self.generate_deployment_report(addresses, prereqs)
        print()
        print(report)

        # Also save report to file
        report_path = DEPLOYMENTS_DIR / "latest_report.txt"
        with open(report_path, "w") as f:
            f.write(report)
        logger.info("Report saved to %s", report_path)

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_address(line: str) -> str | None:
        """Extract a 0x... address from a log line."""
        import re

        match = re.search(r"(0x[0-9a-fA-F]{40})", line)
        return match.group(1) if match else None


# ═══════════════════════════════════════════════════════════════════════════
#  CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy Rings↔Ethereum Bridge to Sepolia Testnet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/deploy_sepolia.py --dry-run
  python scripts/deploy_sepolia.py --method forge
  python scripts/deploy_sepolia.py --method python --dry-run
  python scripts/deploy_sepolia.py --rpc-url https://sepolia.drpc.org
        """,
    )
    parser.add_argument(
        "--method",
        choices=["forge", "python"],
        default="forge",
        help="Deployment method (default: forge)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate deployment without broadcasting transactions",
    )
    parser.add_argument(
        "--rpc-url",
        default=None,
        help=f"Sepolia RPC URL (default: {DEFAULT_RPC})",
    )
    parser.add_argument(
        "--private-key",
        default=None,
        help="Deployer private key (default: from DEPLOYER_PRIVATE_KEY env var)",
    )
    parser.add_argument(
        "--guardian",
        default=None,
        help="Guardian address (default: deployer address)",
    )
    parser.add_argument(
        "--daily-limit",
        type=float,
        default=DEFAULT_DAILY_LIMIT_ETH,
        help=f"Daily withdrawal limit in ETH (default: {DEFAULT_DAILY_LIMIT_ETH})",
    )
    parser.add_argument(
        "--per-tx-limit",
        type=float,
        default=DEFAULT_PER_TX_LIMIT_ETH,
        help=f"Per-transaction limit in ETH (default: {DEFAULT_PER_TX_LIMIT_ETH})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve credentials
    private_key = args.private_key or os.environ.get("DEPLOYER_PRIVATE_KEY", "")
    if not private_key:
        logger.error(
            "No private key provided. Set DEPLOYER_PRIVATE_KEY env var "
            "or pass --private-key."
        )
        sys.exit(1)

    rpc_url = args.rpc_url or os.environ.get("SEPOLIA_RPC_URL", DEFAULT_RPC)
    guardian = args.guardian or os.environ.get("GUARDIAN_ADDRESS", "")

    deployer = SepoliaDeployer(
        private_key=private_key,
        rpc_url=rpc_url,
        guardian=guardian or None,
        daily_limit_eth=args.daily_limit,
        per_tx_limit_eth=args.per_tx_limit,
    )

    asyncio.run(deployer.run(method=args.method, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
