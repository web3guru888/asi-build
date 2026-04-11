"""
Network Configuration for Web3 Integration

Defines configuration for various blockchain networks including
Ethereum mainnet, testnets, and Layer 2 solutions like Polygon.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class NetworkConfig:
    """Configuration for a blockchain network"""

    name: str
    chain_id: int
    rpc_urls: List[str]
    block_explorer_url: str
    native_token: str
    is_testnet: bool = False
    gas_price_gwei: Optional[float] = None
    max_priority_fee_gwei: Optional[float] = None
    max_fee_per_gas_gwei: Optional[float] = None
    supports_eip1559: bool = True
    confirmation_blocks: int = 12
    timeout_seconds: int = 300


# Ethereum Networks
ETHEREUM_MAINNET = NetworkConfig(
    name="Ethereum Mainnet",
    chain_id=1,
    rpc_urls=[
        "https://eth-mainnet.alchemyapi.io/v2/",
        "https://mainnet.infura.io/v3/",
        "https://eth-mainnet.g.alchemy.com/v2/",
        "https://rpc.flashbots.net/",
        "https://eth-mainnet.gateway.pokt.network/v1/lb/",
    ],
    block_explorer_url="https://etherscan.io",
    native_token="ETH",
    is_testnet=False,
    gas_price_gwei=20.0,
    max_priority_fee_gwei=2.0,
    max_fee_per_gas_gwei=50.0,
    supports_eip1559=True,
    confirmation_blocks=12,
    timeout_seconds=300,
)

ETHEREUM_GOERLI = NetworkConfig(
    name="Ethereum Goerli Testnet",
    chain_id=5,
    rpc_urls=[
        "https://eth-goerli.alchemyapi.io/v2/",
        "https://goerli.infura.io/v3/",
        "https://rpc.goerli.mudit.blog/",
        "https://ethereum-goerli-rpc.allthatnode.com",
    ],
    block_explorer_url="https://goerli.etherscan.io",
    native_token="GoerliETH",
    is_testnet=True,
    gas_price_gwei=1.0,
    max_priority_fee_gwei=1.0,
    max_fee_per_gas_gwei=5.0,
    supports_eip1559=True,
    confirmation_blocks=3,
    timeout_seconds=180,
)

ETHEREUM_SEPOLIA = NetworkConfig(
    name="Ethereum Sepolia Testnet",
    chain_id=11155111,
    rpc_urls=[
        "https://eth-sepolia.g.alchemy.com/v2/",
        "https://sepolia.infura.io/v3/",
        "https://rpc.sepolia.org/",
        "https://rpc2.sepolia.org/",
    ],
    block_explorer_url="https://sepolia.etherscan.io",
    native_token="SepoliaETH",
    is_testnet=True,
    gas_price_gwei=1.0,
    max_priority_fee_gwei=1.0,
    max_fee_per_gas_gwei=5.0,
    supports_eip1559=True,
    confirmation_blocks=3,
    timeout_seconds=180,
)

# Polygon Networks
POLYGON_MAINNET = NetworkConfig(
    name="Polygon Mainnet",
    chain_id=137,
    rpc_urls=[
        "https://polygon-rpc.com/",
        "https://rpc-mainnet.maticvigil.com/",
        "https://polygon-mainnet.infura.io/v3/",
        "https://polygon-mainnet.g.alchemy.com/v2/",
        "https://matic-mainnet.chainstacklabs.com",
    ],
    block_explorer_url="https://polygonscan.com",
    native_token="MATIC",
    is_testnet=False,
    gas_price_gwei=30.0,
    max_priority_fee_gwei=30.0,
    max_fee_per_gas_gwei=50.0,
    supports_eip1559=True,
    confirmation_blocks=5,
    timeout_seconds=120,
)

POLYGON_MUMBAI = NetworkConfig(
    name="Polygon Mumbai Testnet",
    chain_id=80001,
    rpc_urls=[
        "https://rpc-mumbai.maticvigil.com/",
        "https://polygon-mumbai.g.alchemy.com/v2/",
        "https://polygon-mumbai.infura.io/v3/",
        "https://matic-mumbai.chainstacklabs.com",
    ],
    block_explorer_url="https://mumbai.polygonscan.com",
    native_token="MATIC",
    is_testnet=True,
    gas_price_gwei=1.0,
    max_priority_fee_gwei=1.0,
    max_fee_per_gas_gwei=5.0,
    supports_eip1559=True,
    confirmation_blocks=2,
    timeout_seconds=60,
)

# Arbitrum Networks
ARBITRUM_MAINNET = NetworkConfig(
    name="Arbitrum One",
    chain_id=42161,
    rpc_urls=[
        "https://arb1.arbitrum.io/rpc",
        "https://arbitrum-mainnet.infura.io/v3/",
        "https://arb-mainnet.g.alchemy.com/v2/",
    ],
    block_explorer_url="https://arbiscan.io",
    native_token="ETH",
    is_testnet=False,
    gas_price_gwei=0.1,
    supports_eip1559=True,
    confirmation_blocks=1,
    timeout_seconds=60,
)

ARBITRUM_GOERLI = NetworkConfig(
    name="Arbitrum Goerli Testnet",
    chain_id=421613,
    rpc_urls=[
        "https://goerli-rollup.arbitrum.io/rpc",
        "https://arbitrum-goerli.infura.io/v3/",
    ],
    block_explorer_url="https://testnet.arbiscan.io",
    native_token="ArbGoerliETH",
    is_testnet=True,
    gas_price_gwei=0.1,
    supports_eip1559=True,
    confirmation_blocks=1,
    timeout_seconds=60,
)

# Optimism Networks
OPTIMISM_MAINNET = NetworkConfig(
    name="Optimism Mainnet",
    chain_id=10,
    rpc_urls=[
        "https://mainnet.optimism.io",
        "https://optimism-mainnet.infura.io/v3/",
        "https://opt-mainnet.g.alchemy.com/v2/",
    ],
    block_explorer_url="https://optimistic.etherscan.io",
    native_token="ETH",
    is_testnet=False,
    gas_price_gwei=0.001,
    supports_eip1559=True,
    confirmation_blocks=1,
    timeout_seconds=60,
)

OPTIMISM_GOERLI = NetworkConfig(
    name="Optimism Goerli Testnet",
    chain_id=420,
    rpc_urls=[
        "https://goerli.optimism.io",
        "https://optimism-goerli.infura.io/v3/",
    ],
    block_explorer_url="https://goerli-optimism.etherscan.io",
    native_token="OptGoerliETH",
    is_testnet=True,
    gas_price_gwei=0.001,
    supports_eip1559=True,
    confirmation_blocks=1,
    timeout_seconds=60,
)

# BSC Networks
BSC_MAINNET = NetworkConfig(
    name="Binance Smart Chain",
    chain_id=56,
    rpc_urls=[
        "https://bsc-dataseed1.binance.org/",
        "https://bsc-dataseed2.binance.org/",
        "https://bsc-dataseed3.binance.org/",
        "https://bsc-dataseed4.binance.org/",
    ],
    block_explorer_url="https://bscscan.com",
    native_token="BNB",
    is_testnet=False,
    gas_price_gwei=5.0,
    supports_eip1559=False,
    confirmation_blocks=3,
    timeout_seconds=120,
)

BSC_TESTNET = NetworkConfig(
    name="BSC Testnet",
    chain_id=97,
    rpc_urls=[
        "https://data-seed-prebsc-1-s1.binance.org:8545/",
        "https://data-seed-prebsc-2-s1.binance.org:8545/",
        "https://data-seed-prebsc-1-s2.binance.org:8545/",
    ],
    block_explorer_url="https://testnet.bscscan.com",
    native_token="tBNB",
    is_testnet=True,
    gas_price_gwei=10.0,
    supports_eip1559=False,
    confirmation_blocks=3,
    timeout_seconds=120,
)

# Network registry
NETWORKS = {
    # Ethereum
    1: ETHEREUM_MAINNET,
    5: ETHEREUM_GOERLI,
    11155111: ETHEREUM_SEPOLIA,
    # Polygon
    137: POLYGON_MAINNET,
    80001: POLYGON_MUMBAI,
    # Arbitrum
    42161: ARBITRUM_MAINNET,
    421613: ARBITRUM_GOERLI,
    # Optimism
    10: OPTIMISM_MAINNET,
    420: OPTIMISM_GOERLI,
    # BSC
    56: BSC_MAINNET,
    97: BSC_TESTNET,
}

# Named network registry
NAMED_NETWORKS = {
    "ethereum": ETHEREUM_MAINNET,
    "ethereum-mainnet": ETHEREUM_MAINNET,
    "ethereum-goerli": ETHEREUM_GOERLI,
    "ethereum-sepolia": ETHEREUM_SEPOLIA,
    "goerli": ETHEREUM_GOERLI,
    "sepolia": ETHEREUM_SEPOLIA,
    "polygon": POLYGON_MAINNET,
    "polygon-mainnet": POLYGON_MAINNET,
    "polygon-mumbai": POLYGON_MUMBAI,
    "mumbai": POLYGON_MUMBAI,
    "matic": POLYGON_MAINNET,
    "arbitrum": ARBITRUM_MAINNET,
    "arbitrum-mainnet": ARBITRUM_MAINNET,
    "arbitrum-goerli": ARBITRUM_GOERLI,
    "arb": ARBITRUM_MAINNET,
    "optimism": OPTIMISM_MAINNET,
    "optimism-mainnet": OPTIMISM_MAINNET,
    "optimism-goerli": OPTIMISM_GOERLI,
    "op": OPTIMISM_MAINNET,
    "bsc": BSC_MAINNET,
    "binance": BSC_MAINNET,
    "bsc-mainnet": BSC_MAINNET,
    "bsc-testnet": BSC_TESTNET,
}


def get_network_by_chain_id(chain_id: int) -> Optional[NetworkConfig]:
    """Get network configuration by chain ID"""
    return NETWORKS.get(chain_id)


def get_network_by_name(name: str) -> Optional[NetworkConfig]:
    """Get network configuration by name"""
    return NAMED_NETWORKS.get(name.lower())


def get_testnet_networks() -> List[NetworkConfig]:
    """Get all testnet network configurations"""
    return [network for network in NETWORKS.values() if network.is_testnet]


def get_mainnet_networks() -> List[NetworkConfig]:
    """Get all mainnet network configurations"""
    return [network for network in NETWORKS.values() if not network.is_testnet]


def get_l2_networks() -> List[NetworkConfig]:
    """Get Layer 2 network configurations"""
    l2_chain_ids = [137, 80001, 42161, 421613, 10, 420]  # Polygon, Arbitrum, Optimism
    return [NETWORKS[chain_id] for chain_id in l2_chain_ids if chain_id in NETWORKS]


def validate_network_config(config: NetworkConfig) -> bool:
    """
    Validate network configuration

    Args:
        config: Network configuration to validate

    Returns:
        True if configuration is valid
    """
    try:
        # Basic validation
        assert config.name and isinstance(config.name, str)
        assert isinstance(config.chain_id, int) and config.chain_id > 0
        assert config.rpc_urls and isinstance(config.rpc_urls, list)
        assert all(
            isinstance(url, str) and url.startswith(("http://", "https://"))
            for url in config.rpc_urls
        )
        assert config.block_explorer_url and isinstance(config.block_explorer_url, str)
        assert config.native_token and isinstance(config.native_token, str)
        assert isinstance(config.is_testnet, bool)
        assert isinstance(config.confirmation_blocks, int) and config.confirmation_blocks > 0
        assert isinstance(config.timeout_seconds, int) and config.timeout_seconds > 0

        # Optional field validation
        if config.gas_price_gwei is not None:
            assert isinstance(config.gas_price_gwei, (int, float)) and config.gas_price_gwei >= 0
        if config.max_priority_fee_gwei is not None:
            assert (
                isinstance(config.max_priority_fee_gwei, (int, float))
                and config.max_priority_fee_gwei >= 0
            )
        if config.max_fee_per_gas_gwei is not None:
            assert (
                isinstance(config.max_fee_per_gas_gwei, (int, float))
                and config.max_fee_per_gas_gwei >= 0
            )

        return True

    except (AssertionError, AttributeError):
        return False


def get_network_summary() -> Dict[str, Dict[str, any]]:
    """Get summary of all configured networks"""
    summary = {}

    for chain_id, network in NETWORKS.items():
        summary[network.name] = {
            "chain_id": chain_id,
            "native_token": network.native_token,
            "is_testnet": network.is_testnet,
            "supports_eip1559": network.supports_eip1559,
            "rpc_count": len(network.rpc_urls),
            "confirmation_blocks": network.confirmation_blocks,
        }

    return summary
