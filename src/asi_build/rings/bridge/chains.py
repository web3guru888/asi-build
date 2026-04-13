"""
Multi-chain configuration for the Rings↔EVM bridge.

Defines chain configs, gas strategies, and helper functions for managing
multi-chain bridge deployments.  Each ``ChainConfig`` carries RPC endpoints,
explorer URLs, timing parameters, and (optionally) the addresses of
already-deployed bridge contracts.

Usage::

    from asi_build.rings.bridge.chains import (
        get_chain, get_enabled_chains, get_deployed_chains,
        get_chain_by_id, chain_rpc_url, update_deployed_addresses,
        GasStrategy,
    )

    sepolia = get_chain("ethereum_sepolia")
    gas = GasStrategy.estimate_gas_params(sepolia, base_gas_price=30_000_000_000)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Gas strategy enum
# ---------------------------------------------------------------------------


class GasStrategy(enum.Enum):
    """Gas pricing strategy for a chain.

    Used by the deployment script and relayer to determine how to
    construct transaction fee parameters.
    """

    EIP1559 = "eip1559"     #: EIP-1559 dynamic fee (Ethereum, Base)
    LEGACY = "legacy"       #: Legacy gasPrice (BSC)
    FIXED = "fixed"         #: Stable/fixed gas (Arc — USDC native gas)

    @staticmethod
    def estimate_gas_params(chain: "ChainConfig", base_gas_price: int) -> Dict[str, int]:
        """Return gas-price fields appropriate for *chain*.

        Parameters
        ----------
        chain : ChainConfig
            Target chain configuration.
        base_gas_price : int
            Current base gas price in wei (or equivalent native unit).

        Returns
        -------
        dict
            A dict suitable for unpacking into a transaction:

            * **EIP1559**: ``{"maxFeePerGas": ..., "maxPriorityFeePerGas": ...}``
            * **LEGACY**: ``{"gasPrice": int(base * 1.1)}``
            * **FIXED** (USDC-native): ``{"gasPrice": base}`` — stable, no multiplier.
        """
        strategy = chain.gas_strategy

        if strategy == GasStrategy.FIXED:
            return {"gasPrice": base_gas_price}

        if strategy == GasStrategy.EIP1559:
            max_fee = base_gas_price * 2
            max_priority = max(base_gas_price // 10, 1_000_000_000)

            if chain.max_gas_price is not None:
                max_fee = min(max_fee, chain.max_gas_price)
                max_priority = min(max_priority, chain.max_gas_price)

            return {
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": max_priority,
            }

        # LEGACY
        gas_price = int(base_gas_price * 1.1)
        if chain.max_gas_price is not None:
            gas_price = min(gas_price, chain.max_gas_price)
        return {"gasPrice": gas_price}


# ---------------------------------------------------------------------------
# Chain configuration
# ---------------------------------------------------------------------------

@dataclass
class ChainConfig:
    """Configuration for a single EVM-compatible chain.

    Parameters
    ----------
    name : str
        Human-readable chain identifier (e.g. ``"ethereum_sepolia"``).
    chain_id : int
        EIP-155 chain ID.
    rpc_url : str
        Default public JSON-RPC endpoint.
    explorer_url : str
        Block explorer base URL (for human-readable links).
    explorer_api_url : str
        Block explorer API base URL (for programmatic queries).
    native_token : str
        Symbol of the chain's native gas token.
    block_time : float
        Average block time in seconds.
    finality_blocks : int
        Number of blocks to wait for probabilistic finality.
    is_testnet : bool
        Whether this is a test network.
    max_gas_price : int | None
        Optional hard cap on gas price (wei). ``None`` means no cap.
    supports_eip1559 : bool
        Whether the chain supports EIP-1559 dynamic fee transactions.
    enabled : bool
        Whether the chain is active for bridge operations.
    verifier_address : str | None
        Deployed Groth16Verifier (or equivalent) contract address.
    bridge_address : str | None
        Deployed RingsBridge contract address.
    token_address : str | None
        Deployed BridgedToken (e.g. bASI) contract address.
    """

    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    explorer_api_url: str
    native_token: str
    block_time: float
    finality_blocks: int
    is_testnet: bool
    max_gas_price: Optional[int] = None
    supports_eip1559: bool = True
    enabled: bool = True

    # Deployed contract addresses (populated after deployment)
    verifier_address: Optional[str] = None
    bridge_address: Optional[str] = None
    token_address: Optional[str] = None

    @property
    def native_symbol(self) -> str:
        """Alias for :attr:`native_token` — used by deployment scripts."""
        return self.native_token

    @property
    def rpc_urls(self) -> list:
        """Return a list of RPC URLs (primary only for now).

        The deployment script iterates over this list to find a reachable
        endpoint.  Future: add fallback URLs per chain.
        """
        return [self.rpc_url]

    @property
    def gas_strategy(self) -> GasStrategy:
        """Infer the gas pricing strategy from chain properties.

        * USDC-native chains → :attr:`GasStrategy.FIXED`
        * EIP-1559 chains    → :attr:`GasStrategy.EIP1559`
        * Everything else    → :attr:`GasStrategy.LEGACY`
        """
        if self.native_token == "USDC":
            return GasStrategy.FIXED
        if self.supports_eip1559:
            return GasStrategy.EIP1559
        return GasStrategy.LEGACY


# ---------------------------------------------------------------------------
# Chain registry
# ---------------------------------------------------------------------------

CHAINS: Dict[str, ChainConfig] = {
    "ethereum_sepolia": ChainConfig(
        name="ethereum_sepolia",
        chain_id=11155111,
        rpc_url="https://ethereum-sepolia-rpc.publicnode.com",
        explorer_url="https://sepolia.etherscan.io",
        explorer_api_url="https://api-sepolia.etherscan.io/api",
        native_token="ETH",
        block_time=12.0,
        finality_blocks=2,
        is_testnet=True,
        supports_eip1559=True,
        # Contracts deployed during Phase A-D
        verifier_address="0xf7D6eb1e746bE1f907beA49660cC0F86be3b350e",
        bridge_address="0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca",
        token_address="0x257dDA1fa34eb847060EcB743E808B65099FB497",
    ),
    "bsc_testnet": ChainConfig(
        name="bsc_testnet",
        chain_id=97,
        rpc_url="https://data-seed-prebsc-1-s1.binance.org:8545/",
        explorer_url="https://testnet.bscscan.com",
        explorer_api_url="https://api-testnet.bscscan.com/api",
        native_token="BNB",
        block_time=3.0,
        finality_blocks=15,
        is_testnet=True,
        supports_eip1559=False,
    ),
    "base_sepolia": ChainConfig(
        name="base_sepolia",
        chain_id=84532,
        rpc_url="https://sepolia.base.org",
        explorer_url="https://sepolia.basescan.org",
        explorer_api_url="https://api-sepolia.basescan.org/api",
        native_token="ETH",
        block_time=2.0,
        finality_blocks=2,
        is_testnet=True,
        supports_eip1559=True,
    ),
    # Circle Arc Network — USDC native gas, Malachite BFT, ~350ms
    # deterministic finality.  Testnet live since Oct 2025.
    # NOTE: Native USDC uses 18 decimals (like wei); the ERC-20 USDC
    # interface at 0x3600...0000 uses 6 decimals.  Do NOT mix them.
    # ERC-8183 (Agentic Commerce) and ERC-8004 (AI Identity) are
    # deployed on Arc testnet — relevant for autonomous agent economies.
    "arc_testnet": ChainConfig(
        name="arc_testnet",
        chain_id=5042002,
        rpc_url="https://rpc.testnet.arc.network",
        explorer_url="https://testnet.arcscan.app",
        explorer_api_url="https://testnet.arcscan.app/api",
        native_token="USDC",
        block_time=0.35,
        finality_blocks=1,  # deterministic finality (Malachite BFT)
        is_testnet=True,
        supports_eip1559=True,  # EIP-1559-like base fee with EWMA smoothing
        enabled=True,
        # Deployed 2026-04-13 — blocks 36924357-36924365
        verifier_address="0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59",
        bridge_address="0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca",
        token_address="0x257dDA1fa34eb847060EcB743E808B65099FB497",
    ),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_chain(name: str) -> ChainConfig:
    """Return the :class:`ChainConfig` for *name*.

    Raises
    ------
    KeyError
        If the chain name is not in the registry.
    """
    try:
        return CHAINS[name]
    except KeyError:
        available = ", ".join(sorted(CHAINS))
        raise KeyError(
            f"Unknown chain {name!r}. Available chains: {available}"
        ) from None


def get_enabled_chains() -> Dict[str, ChainConfig]:
    """Return all chains where ``enabled`` is ``True``."""
    return {name: cfg for name, cfg in CHAINS.items() if cfg.enabled}


def get_deployed_chains() -> Dict[str, ChainConfig]:
    """Return all chains that have a deployed bridge contract address."""
    return {
        name: cfg
        for name, cfg in CHAINS.items()
        if cfg.bridge_address is not None
    }


def get_chain_by_id(chain_id: int) -> Optional[ChainConfig]:
    """Find a chain config by its EIP-155 chain ID.

    Returns ``None`` if no chain with the given ID is registered.
    """
    for cfg in CHAINS.values():
        if cfg.chain_id == chain_id:
            return cfg
    return None


def chain_rpc_url(name: str) -> str:
    """Convenience: return the RPC URL for the named chain.

    Raises
    ------
    KeyError
        If the chain name is not in the registry.
    """
    return get_chain(name).rpc_url


def update_deployed_addresses(
    name: str,
    *,
    verifier: Optional[str] = None,
    bridge: Optional[str] = None,
    token: Optional[str] = None,
) -> None:
    """Update in-memory deployed contract addresses for a chain.

    Only non-``None`` arguments are applied; the rest are left unchanged.

    Parameters
    ----------
    name : str
        Chain registry key.
    verifier : str | None
        New verifier contract address.
    bridge : str | None
        New bridge contract address.
    token : str | None
        New bridged-token contract address.

    Raises
    ------
    KeyError
        If the chain name is not in the registry.
    """
    cfg = get_chain(name)
    if verifier is not None:
        cfg.verifier_address = verifier
    if bridge is not None:
        cfg.bridge_address = bridge
    if token is not None:
        cfg.token_address = token

