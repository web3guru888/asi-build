#!/usr/bin/env python3
"""
Deploy Rings↔Ethereum Bridge to Any Supported EVM Chain
========================================================

Chain-agnostic deployment orchestrator that wraps the Sepolia deployer logic
to support any EVM-compatible chain registered in the chain registry.

Usage
-----
::

    # List all supported chains:
    python scripts/deploy_multichain.py --list-chains

    # Deploy to BSC testnet (dry run):
    python scripts/deploy_multichain.py --chain bsc_testnet --dry-run

    # Deploy to Polygon with Forge:
    python scripts/deploy_multichain.py --chain polygon --method forge

    # Deploy to all enabled chains:
    python scripts/deploy_multichain.py --chain all --dry-run

    # Verify contracts on block explorer after deploy:
    python scripts/deploy_multichain.py --chain bsc_testnet --verify

Environment Variables
---------------------
DEPLOYER_PRIVATE_KEY
    Private key for the deployer account (hex, with or without 0x prefix).
GUARDIAN_ADDRESS
    Address for the guardian role (default: deployer address).
<CHAIN>_RPC_URL
    Per-chain RPC override, e.g. BSC_TESTNET_RPC_URL, POLYGON_RPC_URL.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_ROOT = PROJECT_ROOT / "src"
CONTRACTS_DIR = SRC_ROOT / "asi_build" / "blockchain" / "contracts"
ARTIFACTS_DIR = SRC_ROOT / "asi_build" / "rings" / "bridge" / "artifacts"
DEPLOYMENTS_DIR = PROJECT_ROOT / "deployments"

sys.path.insert(0, str(SRC_ROOT))

from asi_build.rings.bridge.chains import (
    ChainConfig,
    CHAINS,
    GasStrategy,
    get_chain,
    get_enabled_chains,
    update_deployed_addresses,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("deploy_multichain")

# ---------------------------------------------------------------------------
# Gas estimates per contract (from Sepolia simulation)
# ---------------------------------------------------------------------------

GAS_ESTIMATES = {
    "verifier": 1_200_000,
    "bridge": 2_800_000,
    "token": 1_500_000,
}
TOTAL_GAS_ESTIMATE = sum(GAS_ESTIMATES.values())


# ═══════════════════════════════════════════════════════════════════════════
#  JSON-RPC helpers (adapted from deploy_sepolia.py)
# ═══════════════════════════════════════════════════════════════════════════


def _eth_rpc(url: str, method: str, params: list | None = None) -> Any:
    """Make a raw JSON-RPC call.  Tries urllib, then ``cast rpc``."""
    import urllib.request

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

    cast = shutil.which("cast")
    if cast:
        cmd = [cast, "rpc", "--rpc-url", url, method]
        if params:
            for p in params:
                cmd.append(json.dumps(p) if not isinstance(p, str) else p)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout.strip())
                except (json.JSONDecodeError, ValueError):
                    return result.stdout.strip().strip('"')
        except Exception:
            pass

    raise RuntimeError(f"RPC call {method} failed on {url}")


def _cast_call(url: str, method: str, *args: str) -> str:
    """Call a Foundry ``cast`` subcommand. Returns stdout."""
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


def _derive_address_via_cast(private_key_hex: str) -> Optional[str]:
    """Use ``cast wallet address`` if available."""
    cast = shutil.which("cast")
    if not cast:
        return None
    try:
        result = subprocess.run(
            [cast, "wallet", "address", "--private-key", private_key_hex],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _address_from_private_key(private_key_hex: str) -> str:
    """Derive Ethereum address from a private key (secp256k1)."""
    pk_bytes = bytes.fromhex(private_key_hex.removeprefix("0x"))
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend

        key = ec.derive_private_key(
            int.from_bytes(pk_bytes, "big"), ec.SECP256K1(), default_backend()
        )
        pub_numbers = key.public_key().public_numbers()
        pub_bytes = (
            pub_numbers.x.to_bytes(32, "big") + pub_numbers.y.to_bytes(32, "big")
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

    try:
        import sha3
        addr_hash = sha3.keccak_256(pub_bytes).hexdigest()
    except ImportError:
        try:
            from Crypto.Hash import keccak
            k = keccak.new(digest_bits=256)
            k.update(pub_bytes)
            addr_hash = k.hexdigest()
        except ImportError:
            addr_hash_str = _derive_address_via_cast(private_key_hex)
            if addr_hash_str:
                return addr_hash_str
            raise RuntimeError(
                "Need 'pysha3' or 'pycryptodome' for keccak256 address derivation"
            )

    return _checksum_address("0x" + addr_hash[-40:])


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
            return "0x" + addr
    return "0x" + "".join(
        c.upper() if int(hash_hex[i], 16) >= 8 else c for i, c in enumerate(addr)
    )


def _extract_address(line: str) -> Optional[str]:
    """Extract a 0x... address from a log line."""
    match = re.search(r"(0x[0-9a-fA-F]{40})", line)
    return match.group(1) if match else None


# ═══════════════════════════════════════════════════════════════════════════
#  Artifact loading
# ═══════════════════════════════════════════════════════════════════════════


def _load_artifact(name: str) -> Dict[str, Any]:
    """Load a compiled contract artifact JSON."""
    path = ARTIFACTS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")
    with open(path) as f:
        return json.load(f)


def _artifact_bytecode(name: str) -> str:
    """Return the deployment bytecode hex string for a contract."""
    art = _load_artifact(name)
    bc = art.get("bytecode", "")
    if isinstance(bc, dict):
        bc = bc.get("object", "")
    if not bc.startswith("0x"):
        bc = "0x" + bc
    return bc


# ═══════════════════════════════════════════════════════════════════════════
#  Chain listing
# ═══════════════════════════════════════════════════════════════════════════


def list_chains() -> None:
    """Print a formatted table of all registered chains."""
    header = (
        f"{'Name':<20} {'Chain ID':>10} {'Type':<10} "
        f"{'Gas Strategy':<12} {'Enabled':<8} {'Native':<6} {'Explorer'}"
    )
    print()
    print("=" * len(header))
    print("  Registered EVM Chains")
    print("=" * len(header))
    print()
    print(header)
    print("-" * len(header))

    for name, cfg in sorted(CHAINS.items(), key=lambda x: x[1].chain_id):
        enabled = "✅" if cfg.enabled else "—"
        chain_type = "testnet" if cfg.is_testnet else "mainnet"
        gas_str = cfg.gas_strategy.value if hasattr(cfg.gas_strategy, "value") else str(cfg.gas_strategy)
        explorer = cfg.explorer_url or "—"
        print(
            f"{name:<20} {cfg.chain_id:>10} {chain_type:<10} "
            f"{gas_str:<12} {enabled:<8} {cfg.native_symbol:<6} {explorer}"
        )

    total = len(CHAINS)
    enabled = len([c for c in CHAINS.values() if c.enabled])
    print()
    print(f"  Total: {total} chains ({enabled} enabled)")
    print()


# ═══════════════════════════════════════════════════════════════════════════
#  MultiChainDeployer
# ═══════════════════════════════════════════════════════════════════════════


class MultiChainDeployer:
    """Chain-agnostic deployer for the Rings↔Ethereum bridge suite.

    Wraps the Sepolia deployer pattern but uses :class:`ChainConfig` from the
    chain registry for RPC URLs, gas strategies, chain IDs, and explorer URLs.

    Parameters
    ----------
    private_key : str
        Deployer private key (hex, with or without 0x prefix).
    guardian : str or None
        Guardian address (defaults to deployer).
    daily_limit_eth : float
        Daily withdrawal cap in ETH-equivalent (native token).
    per_tx_limit_eth : float
        Per-transaction withdrawal cap.
    """

    def __init__(
        self,
        private_key: str,
        guardian: Optional[str] = None,
        daily_limit_eth: float = 100.0,
        per_tx_limit_eth: float = 10.0,
    ) -> None:
        self.private_key = private_key
        self.daily_limit_wei = _eth_to_wei(daily_limit_eth)
        self.per_tx_limit_wei = _eth_to_wei(per_tx_limit_eth)

        # Derive deployer address
        self.deployer_address = self._resolve_address()
        self.guardian_address = guardian or self.deployer_address

        logger.info("Deployer:  %s", self.deployer_address)
        logger.info("Guardian:  %s", self.guardian_address)

    def _resolve_address(self) -> str:
        """Derive the deployer Ethereum address from the private key."""
        addr = _derive_address_via_cast(self.private_key)
        if addr:
            return addr
        return _address_from_private_key(self.private_key)

    # ── RPC URL resolution ──────────────────────────────────────────

    @staticmethod
    def _resolve_rpc(chain: ChainConfig) -> str:
        """Pick the best RPC URL for a chain.

        Priority:
        1. Environment variable ``<CHAIN_NAME>_RPC_URL`` (uppercased).
        2. ``chain.rpc_urls[0]`` (primary from registry).
        """
        env_key = f"{chain.name.upper()}_RPC_URL"
        env_val = os.environ.get(env_key)
        if env_val:
            return env_val
        if chain.rpc_urls:
            return chain.rpc_urls[0]
        raise RuntimeError(f"No RPC URL available for chain '{chain.name}'")

    # ── Gas price with strategy ─────────────────────────────────────

    @staticmethod
    def _get_gas_price(rpc_url: str, chain: ChainConfig) -> int:
        """Fetch gas price and apply the chain's gas strategy multiplier."""
        base_price = _eth_gas_price(rpc_url)

        if chain.gas_strategy == GasStrategy.LEGACY:
            return base_price
        elif chain.gas_strategy == GasStrategy.EIP1559:
            # For EIP-1559 chains, the reported gas price is already
            # baseFee + priorityFee; add a small buffer for inclusion.
            return int(base_price * 1.1)
        elif chain.gas_strategy == GasStrategy.FIXED:
            # Some L2s have fixed gas; use the chain's fixed value if set,
            # otherwise fall back to the reported price.
            return getattr(chain, "fixed_gas_price", None) or base_price
        else:
            return base_price

    # ── Prerequisites ───────────────────────────────────────────────

    async def check_prerequisites(
        self, chain: ChainConfig, rpc_url: str
    ) -> Dict[str, Any]:
        """Check balance, gas, chain ID, and artifacts for a chain."""
        logger.info("Checking prerequisites for %s (chain %d)...", chain.name, chain.chain_id)
        result: Dict[str, Any] = {
            "chain_name": chain.name,
            "chain_id": chain.chain_id,
            "rpc_url": rpc_url,
            "native_symbol": chain.native_symbol,
            "deployer": self.deployer_address,
            "balance_wei": 0,
            "balance_eth": 0.0,
            "nonce": 0,
            "gas_price_gwei": 0.0,
            "gas_strategy": chain.gas_strategy.value if hasattr(chain.gas_strategy, "value") else str(chain.gas_strategy),
            "estimated_cost_eth": 0.0,
            "has_sufficient_funds": False,
            "artifacts_found": {},
            "forge_available": False,
            "rpc_reachable": False,
        }

        # Attempt RPC connectivity with fallbacks
        urls_to_try = [rpc_url] + [u for u in chain.rpc_urls if u != rpc_url]
        for url in urls_to_try:
            try:
                cid = _eth_chain_id(url)
                if cid == chain.chain_id:
                    result["rpc_reachable"] = True
                    result["rpc_url"] = url
                    rpc_url = url
                    logger.info("  RPC reachable: %s (chain %d)", url, cid)
                    break
                else:
                    logger.warning(
                        "  RPC %s returned chain %d (expected %d)",
                        url, cid, chain.chain_id,
                    )
            except Exception as e:
                logger.warning("  RPC %s unreachable: %s", url, e)

        if result["rpc_reachable"]:
            bal = _eth_balance(rpc_url, self.deployer_address)
            result["balance_wei"] = bal
            result["balance_eth"] = _wei_to_eth(bal)
            result["nonce"] = _eth_nonce(rpc_url, self.deployer_address)

            gas_price = self._get_gas_price(rpc_url, chain)
            result["gas_price_gwei"] = gas_price / 1e9

            estimated_cost_wei = TOTAL_GAS_ESTIMATE * gas_price
            result["estimated_cost_eth"] = _wei_to_eth(estimated_cost_wei)
            result["has_sufficient_funds"] = bal >= estimated_cost_wei

        for name in ["Groth16Verifier", "RingsBridge", "BridgedToken"]:
            art_path = ARTIFACTS_DIR / f"{name}.json"
            result["artifacts_found"][name] = art_path.exists()

        result["forge_available"] = shutil.which("forge") is not None
        return result

    # ── Forge deployment ────────────────────────────────────────────

    async def _deploy_forge(
        self,
        chain: ChainConfig,
        rpc_url: str,
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Deploy using ``forge script``."""
        forge = shutil.which("forge")
        if not forge:
            raise RuntimeError("forge not found in PATH")

        script_path = CONTRACTS_DIR / "script" / "Deploy.s.sol"
        if not script_path.exists():
            raise FileNotFoundError(f"Forge deploy script not found: {script_path}")

        env = os.environ.copy()
        pk = self.private_key if self.private_key.startswith("0x") else "0x" + self.private_key
        env["DEPLOYER_PRIVATE_KEY"] = pk
        env["GUARDIAN_ADDRESS"] = self.guardian_address
        env["DAILY_LIMIT"] = str(self.daily_limit_wei)
        env["PER_TX_LIMIT"] = str(self.per_tx_limit_wei)

        cmd = [
            forge, "script",
            str(script_path) + ":DeployBridge",
            "--rpc-url", rpc_url,
            "--chain-id", str(chain.chain_id),
            "-vvvv",
        ]

        # Chain-specific gas flags
        if chain.gas_strategy == GasStrategy.LEGACY:
            cmd.append("--legacy")
        elif chain.gas_strategy == GasStrategy.FIXED:
            # USDC-native chains (Arc): EIP-1559-like base fee is present,
            # but the gas price is stable.  Let forge use EIP-1559 defaults;
            # add --slow for extra reliability on fast-finality chains.
            cmd.append("--slow")
        elif chain.gas_strategy == GasStrategy.EIP1559:
            # forge defaults to EIP-1559, no extra flag needed
            pass

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

        logger.info("forge stdout (last 3000 chars):\n%s", result.stdout[-3000:])
        if result.stderr:
            logger.warning("forge stderr (last 2000 chars):\n%s", result.stderr[-2000:])

        addresses: Dict[str, Any] = {"method": "forge", "dry_run": dry_run}

        for line in result.stdout.splitlines():
            line_s = line.strip()
            if "Groth16Verifier:" in line_s and "verifier" not in addresses:
                addr = _extract_address(line_s)
                if addr:
                    addresses["verifier"] = addr
            elif "RingsBridge:" in line_s and "bridge" not in addresses:
                addr = _extract_address(line_s)
                if addr:
                    addresses["bridge"] = addr
            elif "BridgedToken:" in line_s and "token" not in addresses:
                addr = _extract_address(line_s)
                if addr:
                    addresses["token"] = addr

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

        if result.returncode != 0:
            has_all = all(addresses.get(k) for k in ("verifier", "bridge", "token"))
            if has_all:
                logger.info(
                    "forge exited with code %d but all addresses parsed successfully",
                    result.returncode,
                )
            else:
                addresses["error"] = f"forge exited with code {result.returncode}"
                addresses["stderr"] = result.stderr[-1000:]

        return addresses

    # ── Python deployment ───────────────────────────────────────────

    async def _deploy_python(
        self,
        chain: ChainConfig,
        rpc_url: str,
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Deploy using raw JSON-RPC (artifact bytecodes)."""
        addresses: Dict[str, Any] = {"method": "python", "dry_run": dry_run}

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
            logger.info("DRY RUN — would deploy 3 contracts to %s", chain.name)
            logger.info("  Groth16Verifier bytecode: %d bytes", len(verifier_bc) // 2)
            logger.info("  RingsBridge bytecode:     %d bytes", len(bridge_bc) // 2)
            logger.info("  BridgedToken bytecode:    %d bytes", len(token_bc) // 2)
            addresses["status"] = "dry_run_complete"
            return addresses

        addresses["error"] = (
            "Raw Python deployment requires the 'web3' package for "
            "transaction signing.  Use --method forge instead, or install "
            "web3: pip install web3"
        )
        return addresses

    # ── Verification ────────────────────────────────────────────────

    async def verify_deployment(
        self,
        chain: ChainConfig,
        rpc_url: str,
        addresses: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Verify contracts are deployed on-chain."""
        verification: Dict[str, Any] = {}
        for name in ("verifier", "bridge", "token"):
            addr = addresses.get(name)
            if not addr:
                verification[name] = {"status": "missing_address"}
                continue
            try:
                code = _eth_code(rpc_url, addr)
                has_code = bool(code and code != "0x" and len(code) > 2)
                verification[name] = {
                    "address": addr,
                    "has_code": has_code,
                    "code_size": len(code) // 2 if has_code else 0,
                }
            except Exception as e:
                verification[name] = {"address": addr, "error": str(e)}
        return verification

    def _explorer_verify_urls(
        self, chain: ChainConfig, addresses: Dict[str, Any]
    ) -> List[str]:
        """Generate block-explorer verification URLs (informational)."""
        if not chain.explorer_url:
            return []
        base = chain.explorer_url.rstrip("/")
        urls = []
        for name in ("verifier", "bridge", "token"):
            addr = addresses.get(name)
            if addr:
                urls.append(f"{base}/address/{addr}#code")
        return urls

    # ── Save deployment ─────────────────────────────────────────────

    def save_deployment(
        self,
        chain: ChainConfig,
        addresses: Dict[str, Any],
        prereqs: Dict[str, Any],
    ) -> Path:
        """Save deployment result to ``deployments/<chain_name>.json``."""
        DEPLOYMENTS_DIR.mkdir(parents=True, exist_ok=True)

        deployment = {
            "network": chain.name,
            "chainId": chain.chain_id,
            "isTestnet": chain.is_testnet,
            "nativeSymbol": chain.native_symbol,
            "deployer": self.deployer_address,
            "guardian": self.guardian_address,
            "rpcUrl": prereqs.get("rpc_url", ""),
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
            "gasStrategy": prereqs.get("gas_strategy", "unknown"),
            "status": "deployed" if not addresses.get("dry_run") else "dry_run",
        }

        if addresses.get("error"):
            deployment["error"] = addresses["error"]

        # Timestamped file
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        ts_path = DEPLOYMENTS_DIR / f"{chain.name}_{ts}.json"
        with open(ts_path, "w") as f:
            json.dump(deployment, f, indent=2)
        logger.info("Deployment saved: %s", ts_path)

        # Canonical file (overwrite)
        canonical = DEPLOYMENTS_DIR / f"{chain.name}.json"
        with open(canonical, "w") as f:
            json.dump(deployment, f, indent=2)
        logger.info("Canonical config: %s", canonical)

        return canonical

    # ── Report generation ───────────────────────────────────────────

    def generate_report(
        self,
        chain: ChainConfig,
        addresses: Dict[str, Any],
        prereqs: Dict[str, Any],
    ) -> str:
        """Generate a human-readable deployment report."""
        sym = chain.native_symbol
        net_type = "TESTNET" if chain.is_testnet else "MAINNET"
        lines = [
            "=" * 64,
            f"  Rings↔Ethereum Bridge — {chain.name} Deployment Report",
            "=" * 64,
            "",
            f"  Date:           {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"  Network:        {chain.name} ({net_type}, chain {chain.chain_id})",
            f"  RPC:            {prereqs.get('rpc_url', 'N/A')}",
            f"  Gas Strategy:   {prereqs.get('gas_strategy', 'N/A')}",
            f"  Method:         {addresses.get('method', 'N/A')}",
            f"  Dry Run:        {addresses.get('dry_run', 'N/A')}",
            "",
            "── Deployer ──────────────────────────────────────────────────",
            f"  Address:        {self.deployer_address}",
            f"  Balance:        {prereqs.get('balance_eth', 0):.6f} {sym}",
            f"  Nonce:          {prereqs.get('nonce', 'N/A')}",
            f"  Gas Price:      {prereqs.get('gas_price_gwei', 0):.2f} gwei",
            "",
            "── Cost Estimate ─────────────────────────────────────────────",
            f"  Gas (verifier): ~{GAS_ESTIMATES['verifier']:,}",
            f"  Gas (bridge):   ~{GAS_ESTIMATES['bridge']:,}",
            f"  Gas (token):    ~{GAS_ESTIMATES['token']:,}",
            f"  Total gas:      ~{TOTAL_GAS_ESTIMATE:,}",
            f"  Est. cost:      ~{prereqs.get('estimated_cost_eth', 0):.6f} {sym}",
            f"  Sufficient:     {'✅ YES' if prereqs.get('has_sufficient_funds') else '❌ NO'}",
            "",
            "── Configuration ─────────────────────────────────────────────",
            f"  Guardian:       {self.guardian_address}",
            f"  Daily Limit:    {_wei_to_eth(self.daily_limit_wei):.1f} {sym}",
            f"  Per-tx Limit:   {_wei_to_eth(self.per_tx_limit_wei):.1f} {sym}",
            f"  Token:          Bridged ASI (bASI)",
            "",
            "── Artifacts ─────────────────────────────────────────────────",
        ]
        for name, found in prereqs.get("artifacts_found", {}).items():
            status = "✅" if found else "❌ MISSING"
            lines.append(f"  {name:20s} {status}")

        lines.extend([
            "",
            f"  Forge available:  {'✅' if prereqs.get('forge_available') else '❌'}",
            "",
            "── Deployed Contracts ────────────────────────────────────────",
        ])

        for name in ("verifier", "bridge", "token"):
            addr = addresses.get(name, "not deployed")
            lines.append(f"  {name:20s} {addr}")

        # Explorer links
        explorer_urls = self._explorer_verify_urls(chain, addresses)
        if explorer_urls:
            lines.extend(["", "── Explorer Links ────────────────────────────────────────────"])
            for url in explorer_urls:
                lines.append(f"  {url}")

        if addresses.get("error"):
            lines.extend([
                "",
                "── Error ─────────────────────────────────────────────────────",
                f"  {addresses['error']}",
            ])

        if not prereqs.get("has_sufficient_funds"):
            lines.extend([
                "",
                "── Action Required ───────────────────────────────────────────",
                f"  Send at least {prereqs.get('estimated_cost_eth', 0.02):.4f} {sym}",
                f"  to {self.deployer_address}",
                f"  on the {chain.name} network.",
            ])
            if chain.is_testnet and hasattr(chain, "faucet_url") and chain.faucet_url:
                lines.append(f"  Faucet: {chain.faucet_url}")

        lines.extend(["", "=" * 64])
        return "\n".join(lines)

    # ── Main deploy entrypoint ──────────────────────────────────────

    async def deploy(
        self,
        chain_name: str,
        method: str = "forge",
        dry_run: bool = False,
        verify: bool = False,
    ) -> Dict[str, Any]:
        """Deploy bridge contracts to a single chain.

        Parameters
        ----------
        chain_name : str
            Registry key for the target chain (e.g. ``"bsc_testnet"``).
        method : str
            ``"forge"`` or ``"python"``.
        dry_run : bool
            If True, simulate without broadcasting.
        verify : bool
            If True, log explorer verification URLs after deployment.

        Returns
        -------
        dict
            Deployment result including addresses, prereqs, and report.
        """
        chain = get_chain(chain_name)
        if chain is None:
            raise ValueError(
                f"Unknown chain '{chain_name}'. Use --list-chains to see available chains."
            )
        if not chain.enabled:
            raise ValueError(
                f"Chain '{chain_name}' is disabled in the registry. "
                f"Enable it in chains.py first."
            )

        logger.info("━" * 60)
        logger.info("Deploying to %s (chain ID %d)", chain.name, chain.chain_id)
        logger.info("━" * 60)

        rpc_url = self._resolve_rpc(chain)

        # 1. Prerequisites
        prereqs = await self.check_prerequisites(chain, rpc_url)
        rpc_url = prereqs["rpc_url"]  # may have been updated to fallback

        # 2. Deploy
        if not prereqs["rpc_reachable"]:
            logger.error("No RPC reachable for %s — cannot deploy", chain.name)
            addresses: Dict[str, Any] = {
                "method": method,
                "dry_run": dry_run,
                "error": f"No RPC reachable for {chain.name}",
            }
        elif dry_run or not prereqs["has_sufficient_funds"]:
            if not dry_run and not prereqs["has_sufficient_funds"]:
                logger.warning(
                    "Insufficient funds (%.6f %s, need ~%.6f %s). "
                    "Running as dry-run.",
                    prereqs["balance_eth"], chain.native_symbol,
                    prereqs["estimated_cost_eth"], chain.native_symbol,
                )
                dry_run = True

            if method == "forge":
                addresses = await self._deploy_forge(chain, rpc_url, dry_run=True)
            else:
                addresses = await self._deploy_python(chain, rpc_url, dry_run=True)
        else:
            if method == "forge":
                addresses = await self._deploy_forge(chain, rpc_url, dry_run=False)
            else:
                addresses = await self._deploy_python(chain, rpc_url, dry_run=False)

        # 3. Verify on-chain
        if not dry_run and addresses.get("verifier"):
            verification = await self.verify_deployment(chain, rpc_url, addresses)
            addresses["verification"] = verification
            logger.info("Verification: %s", json.dumps(verification, indent=2))

        # 4. Update chain registry in-memory
        deployed_addrs: Dict[str, str] = {}
        for k in ("verifier", "bridge", "token"):
            if addresses.get(k):
                deployed_addrs[k] = addresses[k]
        if deployed_addrs and not dry_run:
            try:
                update_deployed_addresses(chain_name, deployed_addrs)
                logger.info("Updated in-memory chain registry for %s", chain_name)
            except Exception as e:
                logger.warning("Could not update chain registry: %s", e)

        # 5. Save
        saved_path = self.save_deployment(chain, addresses, prereqs)

        # 6. Report
        report = self.generate_report(chain, addresses, prereqs)
        print()
        print(report)

        report_path = DEPLOYMENTS_DIR / f"{chain.name}_latest_report.txt"
        with open(report_path, "w") as f:
            f.write(report)

        # 7. Explorer verification URLs
        if verify:
            urls = self._explorer_verify_urls(chain, addresses)
            if urls:
                logger.info("Contract verification URLs:")
                for url in urls:
                    logger.info("  %s", url)
            else:
                logger.info("No explorer URL configured for %s", chain.name)

        return {
            "chain": chain_name,
            "addresses": addresses,
            "prereqs": prereqs,
            "report_path": str(report_path),
            "deployment_path": str(saved_path),
        }

    # ── Deploy to all enabled chains ────────────────────────────────

    async def deploy_all(
        self,
        method: str = "forge",
        dry_run: bool = False,
        verify: bool = False,
    ) -> List[Dict[str, Any]]:
        """Deploy sequentially to all enabled chains.

        Returns a list of per-chain deployment results.
        """
        enabled = get_enabled_chains()
        if not enabled:
            logger.error("No enabled chains found in registry")
            return []

        logger.info("Deploying to %d enabled chains: %s",
                     len(enabled), ", ".join(c.name for c in enabled))

        results: List[Dict[str, Any]] = []
        for chain in enabled:
            try:
                result = await self.deploy(
                    chain.name, method=method, dry_run=dry_run, verify=verify,
                )
                results.append(result)
            except Exception as e:
                logger.error("Deployment to %s failed: %s", chain.name, e)
                results.append({
                    "chain": chain.name,
                    "error": str(e),
                })

        # Summary
        print()
        print("=" * 64)
        print("  Multi-Chain Deployment Summary")
        print("=" * 64)
        print()
        for r in results:
            name = r.get("chain", "unknown")
            if r.get("error") and "addresses" not in r:
                print(f"  {name:<20} ❌ FAILED: {r['error']}")
            else:
                addrs = r.get("addresses", {})
                has_all = all(addrs.get(k) for k in ("verifier", "bridge", "token"))
                if addrs.get("dry_run"):
                    print(f"  {name:<20} 🔍 DRY RUN")
                elif has_all:
                    print(f"  {name:<20} ✅ DEPLOYED")
                elif addrs.get("error"):
                    print(f"  {name:<20} ⚠️  PARTIAL: {addrs['error'][:50]}")
                else:
                    print(f"  {name:<20} ⚠️  INCOMPLETE")
        print()
        print("=" * 64)

        return results


# ═══════════════════════════════════════════════════════════════════════════
#  CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy Rings↔Ethereum Bridge to any supported EVM chain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/deploy_multichain.py --list-chains
  python scripts/deploy_multichain.py --chain bsc_testnet --dry-run
  python scripts/deploy_multichain.py --chain polygon --method forge
  python scripts/deploy_multichain.py --chain all --dry-run
  python scripts/deploy_multichain.py --chain sepolia --verify
        """,
    )
    parser.add_argument(
        "--chain",
        type=str,
        default=None,
        help="Target chain name, or 'all' for all enabled chains",
    )
    parser.add_argument(
        "--list-chains",
        action="store_true",
        help="List all registered chains and exit",
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
        help="Simulate deployment without broadcasting",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Log block explorer verification URLs after deploy",
    )
    parser.add_argument(
        "--private-key",
        default=None,
        help="Deployer private key (default: DEPLOYER_PRIVATE_KEY env)",
    )
    parser.add_argument(
        "--guardian",
        default=None,
        help="Guardian address (default: deployer address)",
    )
    parser.add_argument(
        "--daily-limit",
        type=float,
        default=100.0,
        help="Daily withdrawal limit in native token (default: 100)",
    )
    parser.add_argument(
        "--per-tx-limit",
        type=float,
        default=10.0,
        help="Per-transaction limit in native token (default: 10)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # --list-chains: print and exit
    if args.list_chains:
        list_chains()
        sys.exit(0)

    # Require --chain for deployment
    if not args.chain:
        parser.error("--chain is required (or use --list-chains)")

    # Resolve credentials
    private_key = args.private_key or os.environ.get("DEPLOYER_PRIVATE_KEY", "")
    if not private_key:
        logger.error(
            "No private key provided. Set DEPLOYER_PRIVATE_KEY env var "
            "or pass --private-key."
        )
        sys.exit(1)

    guardian = args.guardian or os.environ.get("GUARDIAN_ADDRESS", "")

    deployer = MultiChainDeployer(
        private_key=private_key,
        guardian=guardian or None,
        daily_limit_eth=args.daily_limit,
        per_tx_limit_eth=args.per_tx_limit,
    )

    if args.chain.lower() == "all":
        asyncio.run(
            deployer.deploy_all(
                method=args.method,
                dry_run=args.dry_run,
                verify=args.verify,
            )
        )
    else:
        asyncio.run(
            deployer.deploy(
                chain_name=args.chain,
                method=args.method,
                dry_run=args.dry_run,
                verify=args.verify,
            )
        )


if __name__ == "__main__":
    main()
