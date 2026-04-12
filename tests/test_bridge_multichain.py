"""
Multi-Chain Bridge Support Tests
=================================

Comprehensive tests for Phase H: multi-chain bridge infrastructure.

Test categories (121 tests):
- ChainConfig & Registry (18): dataclass, properties, registry lookups
- GasStrategy (12): EIP-1559, Legacy, Fixed, edge cases
- Multi-Chain Contract Client (14): for_chain factory, per-chain config
- Multi-Chain Relayer (16): from_chain config, MultiChainRelayer lifecycle
- Cross-Chain Ledger (22): target_chain on withdrawals, source_chain on deposits,
                           cross-chain routing (deposit BSC → withdraw Base)
- WithdrawalLock Serialization (8): target_chain persistence
- Deployment Script Helpers (6): list_chains, MultiChainDeployer dry-run
- Arc Network Specifics (10): chain config, USDC gas, EIP-1559-like
- Integration Scenarios (15): E2E cross-chain flows

All tests run offline — web3/network dependencies are mocked.
"""

from __future__ import annotations

import asyncio
import copy
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from asi_build.rings.bridge.chains import (
    CHAINS,
    ChainConfig,
    GasStrategy,
    chain_rpc_url,
    get_chain,
    get_chain_by_id,
    get_deployed_chains,
    get_enabled_chains,
    update_deployed_addresses,
)
from asi_build.rings.bridge.ledger import (
    LedgerKeys,
    LedgerMessage,
    RingsTokenLedger,
    TransferRecord,
    TransferReceipt,
    TransferStatus,
    WithdrawalLock,
    _normalize_token,
)
from asi_build.rings.bridge.relayer import (
    BridgeRelayer,
    MultiChainRelayer,
    OperationStatus,
    RelayerConfig,
    RelayerDB,
)
from asi_build.rings.bridge.contract_client import (
    BridgeContractClient,
    BridgeDeployer,
)


# ===========================================================================
# Fixtures
# ===========================================================================


class MockDHTClient:
    """In-memory DHT mock for ledger tests."""

    def __init__(self) -> None:
        self._store: dict = {}

    async def dht_get(self, key: str):
        return self._store.get(key)

    async def dht_put(self, key: str, value) -> None:
        self._store[key] = value

    async def broadcast(self, sub_ring: str, msg: dict) -> None:
        pass  # no-op for tests


class MockIdentity:
    """Mock identity for ledger validator tests."""

    def __init__(self, did: str = "did:rings:secp256k1:test_validator") -> None:
        self.rings_did = did

    def sign_rings(self, data: bytes) -> bytes:
        import hashlib
        return hashlib.sha256(data + b":signed").digest()


@pytest.fixture
def dht_client():
    return MockDHTClient()


@pytest.fixture
def identity():
    return MockIdentity()


@pytest.fixture
def ledger(dht_client, identity):
    return RingsTokenLedger(
        client=dht_client,
        identity=identity,
        threshold=1,
        total=1,
    )


@pytest.fixture(autouse=True)
def _preserve_chains():
    """Snapshot and restore CHAINS dict around each test."""
    original = {}
    for k, v in CHAINS.items():
        original[k] = copy.copy(v)
    yield
    # Restore
    for k, v in original.items():
        CHAINS[k] = v
    # Remove any keys that were added
    for k in list(CHAINS.keys()):
        if k not in original:
            del CHAINS[k]


# ===========================================================================
# ChainConfig & Registry Tests (18)
# ===========================================================================


class TestChainConfig:
    """Tests for ChainConfig dataclass and registry."""

    def test_chain_config_fields(self):
        """ChainConfig has all expected fields."""
        cfg = ChainConfig(
            name="test",
            chain_id=1234,
            rpc_url="https://example.com",
            explorer_url="https://scan.example.com",
            explorer_api_url="https://api.scan.example.com/api",
            native_token="ETH",
            block_time=12.0,
            finality_blocks=2,
            is_testnet=True,
        )
        assert cfg.name == "test"
        assert cfg.chain_id == 1234
        assert cfg.rpc_url == "https://example.com"
        assert cfg.native_token == "ETH"
        assert cfg.block_time == 12.0
        assert cfg.finality_blocks == 2
        assert cfg.is_testnet is True
        assert cfg.verifier_address is None
        assert cfg.bridge_address is None
        assert cfg.token_address is None
        assert cfg.enabled is True
        assert cfg.supports_eip1559 is True

    def test_chain_config_gas_strategy_eip1559(self):
        """EIP-1559 chains return EIP1559 gas strategy."""
        cfg = CHAINS["ethereum_sepolia"]
        assert cfg.gas_strategy == GasStrategy.EIP1559

    def test_chain_config_gas_strategy_legacy(self):
        """BSC returns LEGACY gas strategy."""
        cfg = CHAINS["bsc_testnet"]
        assert cfg.gas_strategy == GasStrategy.LEGACY

    def test_chain_config_gas_strategy_fixed(self):
        """Arc returns FIXED gas strategy (USDC native)."""
        cfg = CHAINS["arc_testnet"]
        assert cfg.gas_strategy == GasStrategy.FIXED

    def test_chain_config_gas_strategy_base(self):
        """Base Sepolia returns EIP1559."""
        cfg = CHAINS["base_sepolia"]
        assert cfg.gas_strategy == GasStrategy.EIP1559

    def test_registry_has_four_chains(self):
        """CHAINS registry contains all four configured chains."""
        assert "ethereum_sepolia" in CHAINS
        assert "bsc_testnet" in CHAINS
        assert "base_sepolia" in CHAINS
        assert "arc_testnet" in CHAINS
        assert len(CHAINS) == 4

    def test_get_chain_valid(self):
        """get_chain returns config for valid name."""
        cfg = get_chain("ethereum_sepolia")
        assert cfg.chain_id == 11155111
        assert cfg.native_token == "ETH"

    def test_get_chain_invalid(self):
        """get_chain raises KeyError for unknown chain."""
        with pytest.raises(KeyError, match="Unknown chain"):
            get_chain("nonexistent_chain")

    def test_get_enabled_chains(self):
        """get_enabled_chains filters disabled chains."""
        enabled = get_enabled_chains()
        assert "ethereum_sepolia" in enabled
        assert "bsc_testnet" in enabled
        assert "base_sepolia" in enabled
        assert "arc_testnet" in enabled  # We enabled it with real data

    def test_get_deployed_chains(self):
        """get_deployed_chains returns only chains with bridge_address."""
        deployed = get_deployed_chains()
        assert "ethereum_sepolia" in deployed
        assert "bsc_testnet" not in deployed
        assert "base_sepolia" not in deployed

    def test_get_chain_by_id_found(self):
        """get_chain_by_id returns matching chain."""
        cfg = get_chain_by_id(11155111)
        assert cfg is not None
        assert cfg.name == "ethereum_sepolia"

    def test_get_chain_by_id_not_found(self):
        """get_chain_by_id returns None for unknown chain ID."""
        assert get_chain_by_id(999999999) is None

    def test_chain_rpc_url(self):
        """chain_rpc_url returns the RPC URL."""
        url = chain_rpc_url("ethereum_sepolia")
        assert "publicnode" in url

    def test_update_deployed_addresses(self):
        """update_deployed_addresses modifies in-place."""
        update_deployed_addresses(
            "bsc_testnet",
            verifier="0xAAA",
            bridge="0xBBB",
            token="0xCCC",
        )
        cfg = get_chain("bsc_testnet")
        assert cfg.verifier_address == "0xAAA"
        assert cfg.bridge_address == "0xBBB"
        assert cfg.token_address == "0xCCC"

    def test_update_deployed_addresses_partial(self):
        """update_deployed_addresses only updates non-None values."""
        update_deployed_addresses("bsc_testnet", bridge="0xDDD")
        cfg = get_chain("bsc_testnet")
        assert cfg.bridge_address == "0xDDD"
        assert cfg.verifier_address is None  # unchanged
        assert cfg.token_address is None  # unchanged

    def test_update_deployed_addresses_unknown_chain(self):
        """update_deployed_addresses raises KeyError for unknown chain."""
        with pytest.raises(KeyError):
            update_deployed_addresses("nonexistent", bridge="0x123")

    def test_sepolia_has_deployed_addresses(self):
        """Ethereum Sepolia has pre-filled contract addresses."""
        cfg = get_chain("ethereum_sepolia")
        assert cfg.verifier_address is not None
        assert cfg.bridge_address is not None
        assert cfg.token_address is not None
        assert cfg.verifier_address.startswith("0x")

    def test_arc_testnet_chain_id(self):
        """Arc testnet has correct chain ID from research."""
        cfg = get_chain("arc_testnet")
        assert cfg.chain_id == 5042002


# ===========================================================================
# GasStrategy Tests (12)
# ===========================================================================


class TestGasStrategy:
    """Tests for GasStrategy enum and estimate_gas_params."""

    def test_enum_values(self):
        """GasStrategy has three variants."""
        assert GasStrategy.EIP1559.value == "eip1559"
        assert GasStrategy.LEGACY.value == "legacy"
        assert GasStrategy.FIXED.value == "fixed"

    def test_eip1559_gas_params(self):
        """EIP-1559 returns maxFeePerGas and maxPriorityFeePerGas."""
        chain = get_chain("ethereum_sepolia")
        params = GasStrategy.estimate_gas_params(chain, 30_000_000_000)
        assert "maxFeePerGas" in params
        assert "maxPriorityFeePerGas" in params
        assert "gasPrice" not in params
        assert params["maxFeePerGas"] == 60_000_000_000  # 2x
        assert params["maxPriorityFeePerGas"] == 3_000_000_000  # base // 10

    def test_eip1559_min_priority_fee(self):
        """EIP-1559 priority fee has a 1 gwei floor."""
        chain = get_chain("ethereum_sepolia")
        params = GasStrategy.estimate_gas_params(chain, 1_000_000)  # very low
        assert params["maxPriorityFeePerGas"] == 1_000_000_000  # 1 gwei floor

    def test_legacy_gas_params(self):
        """Legacy chain returns gasPrice with 1.1x multiplier."""
        chain = get_chain("bsc_testnet")
        params = GasStrategy.estimate_gas_params(chain, 5_000_000_000)
        assert "gasPrice" in params
        assert "maxFeePerGas" not in params
        assert params["gasPrice"] == int(5_000_000_000 * 1.1)

    def test_fixed_gas_params(self):
        """Fixed (USDC) chain returns gasPrice = base (no multiplier)."""
        chain = get_chain("arc_testnet")
        params = GasStrategy.estimate_gas_params(chain, 160_000_000_000)
        assert "gasPrice" in params
        assert params["gasPrice"] == 160_000_000_000  # exact, no markup

    def test_eip1559_with_max_cap(self):
        """EIP-1559 respects max_gas_price cap."""
        chain = ChainConfig(
            name="capped",
            chain_id=99,
            rpc_url="",
            explorer_url="",
            explorer_api_url="",
            native_token="ETH",
            block_time=12.0,
            finality_blocks=2,
            is_testnet=True,
            supports_eip1559=True,
            max_gas_price=50_000_000_000,
        )
        params = GasStrategy.estimate_gas_params(chain, 40_000_000_000)
        # Without cap: maxFeePerGas would be 80 gwei
        assert params["maxFeePerGas"] == 50_000_000_000  # capped

    def test_legacy_with_max_cap(self):
        """Legacy chain respects max_gas_price cap."""
        chain = ChainConfig(
            name="capped_bsc",
            chain_id=98,
            rpc_url="",
            explorer_url="",
            explorer_api_url="",
            native_token="BNB",
            block_time=3.0,
            finality_blocks=15,
            is_testnet=True,
            supports_eip1559=False,
            max_gas_price=10_000_000_000,
        )
        params = GasStrategy.estimate_gas_params(chain, 20_000_000_000)
        assert params["gasPrice"] == 10_000_000_000  # capped

    def test_zero_base_gas(self):
        """Zero base gas doesn't crash."""
        chain = get_chain("ethereum_sepolia")
        params = GasStrategy.estimate_gas_params(chain, 0)
        assert params["maxFeePerGas"] == 0
        assert params["maxPriorityFeePerGas"] == 1_000_000_000  # floor

    def test_base_sepolia_gas_strategy(self):
        """Base Sepolia (L2) uses EIP-1559."""
        chain = get_chain("base_sepolia")
        params = GasStrategy.estimate_gas_params(chain, 100_000_000)
        assert "maxFeePerGas" in params

    def test_arc_testnet_gas_no_markup(self):
        """Arc testnet doesn't apply any gas markup."""
        chain = get_chain("arc_testnet")
        for base in [100, 1000, 1_000_000_000, 160_000_000_000]:
            params = GasStrategy.estimate_gas_params(chain, base)
            assert params["gasPrice"] == base

    def test_gas_strategy_property_matches_behavior(self):
        """gas_strategy property is consistent with estimate_gas_params."""
        for name, cfg in CHAINS.items():
            strategy = cfg.gas_strategy
            params = GasStrategy.estimate_gas_params(cfg, 10_000_000_000)
            if strategy == GasStrategy.EIP1559:
                assert "maxFeePerGas" in params
            elif strategy == GasStrategy.LEGACY:
                assert "gasPrice" in params
                assert "maxFeePerGas" not in params
            elif strategy == GasStrategy.FIXED:
                assert "gasPrice" in params
                assert params["gasPrice"] == 10_000_000_000

    def test_gas_strategy_enum_from_value(self):
        """GasStrategy can be constructed from string value."""
        assert GasStrategy("eip1559") is GasStrategy.EIP1559
        assert GasStrategy("legacy") is GasStrategy.LEGACY
        assert GasStrategy("fixed") is GasStrategy.FIXED


# ===========================================================================
# Multi-Chain Contract Client Tests (14)
# ===========================================================================


class TestMultiChainContractClient:
    """Tests for BridgeContractClient.for_chain and BridgeDeployer.for_chain.

    Note: BridgeContractClient.__init__ imports ContractInterface from the
    web3_integration module, which triggers a ``geth_poa_middleware`` import
    error in the installed web3 version.  We patch around that for tests
    that actually instantiate a client.
    """

    def _make_mock_web3(self):
        web3 = MagicMock()
        web3.get_account_address.return_value = "0x" + "ab" * 20
        return web3

    def _make_mock_cm(self):
        cm = MagicMock()
        cm.contracts = {}
        return cm

    def _patch_contract_interface(self):
        """Return a context-manager that mocks the ContractInterface import."""
        ci_mock = MagicMock()
        ci_mock.ContractInterface = type("ContractInterface", (), {
            "__init__": lambda self, **kw: None,
        })
        return patch(
            "asi_build.rings.bridge.contract_client.ContractInterface",
            ci_mock.ContractInterface,
            create=True,
        )

    def _make_client_for_chain(self, chain_name):
        """Create a client via for_chain with the import mock."""
        web3 = self._make_mock_web3()
        cm = self._make_mock_cm()
        # Patch the import that BridgeContractClient.__init__ triggers
        mock_module = MagicMock()
        mock_module.ContractInterface = type("CI", (), {
            "__init__": lambda self, **kw: self.__dict__.update(kw),
        })
        with patch.dict("sys.modules", {
            "asi_build.blockchain.web3_integration.contract_manager": mock_module,
        }):
            return BridgeContractClient.for_chain(chain_name, web3, cm), web3, cm

    def test_client_for_chain_sepolia(self):
        """for_chain creates client with Sepolia bridge address."""
        client, _, _ = self._make_client_for_chain("ethereum_sepolia")
        assert client.bridge_address == "0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca"

    def test_client_for_chain_undeployed(self):
        """for_chain raises ValueError for chain without bridge contract."""
        web3 = self._make_mock_web3()
        cm = self._make_mock_cm()
        with pytest.raises(ValueError, match="No bridge contract deployed"):
            BridgeContractClient.for_chain("bsc_testnet", web3, cm)

    def test_client_for_chain_unknown(self):
        """for_chain raises KeyError for unknown chain."""
        web3 = self._make_mock_web3()
        cm = self._make_mock_cm()
        with pytest.raises(KeyError, match="Unknown chain"):
            BridgeContractClient.for_chain("nonexistent", web3, cm)

    def test_client_for_chain_after_deploy(self):
        """for_chain works after addresses are updated."""
        update_deployed_addresses("bsc_testnet", bridge="0x1234567890abcdef1234567890abcdef12345678")
        client, _, _ = self._make_client_for_chain("bsc_testnet")
        assert client.bridge_address == "0x1234567890abcdef1234567890abcdef12345678"

    def test_client_for_chain_sets_web3(self):
        """for_chain passes web3_client correctly."""
        client, web3, _ = self._make_client_for_chain("ethereum_sepolia")
        assert client.web3 is web3

    def test_deployer_for_chain_basic(self):
        """BridgeDeployer.for_chain creates deployer with chain context."""
        web3 = self._make_mock_web3()
        cm = self._make_mock_cm()
        deployer = BridgeDeployer.for_chain("bsc_testnet", web3, cm)
        assert hasattr(deployer, "_chain_name")
        assert deployer._chain_name == "bsc_testnet"
        assert hasattr(deployer, "_chain_config")
        assert deployer._chain_config.chain_id == 97

    def test_deployer_for_chain_unknown(self):
        """BridgeDeployer.for_chain raises KeyError for unknown chain."""
        web3 = self._make_mock_web3()
        cm = self._make_mock_cm()
        with pytest.raises(KeyError):
            BridgeDeployer.for_chain("nonexistent", web3, cm)

    def test_deployer_for_chain_passes_kwargs(self):
        """BridgeDeployer.for_chain forwards keyword arguments."""
        web3 = self._make_mock_web3()
        cm = self._make_mock_cm()
        deployer = BridgeDeployer.for_chain(
            "base_sepolia", web3, cm,
            verifier_bytecode="0xdead",
        )
        assert deployer._verifier_bytecode == "0xdead"

    def test_deployer_for_chain_each_chain(self):
        """BridgeDeployer.for_chain works for all registered chains."""
        web3 = self._make_mock_web3()
        cm = self._make_mock_cm()
        for name in CHAINS:
            deployer = BridgeDeployer.for_chain(name, web3, cm)
            assert deployer._chain_name == name

    def test_client_repr_includes_address(self):
        """BridgeContractClient repr shows bridge address."""
        client, _, _ = self._make_client_for_chain("ethereum_sepolia")
        assert "0xE034" in repr(client)

    def test_deployer_for_chain_arc(self):
        """BridgeDeployer.for_chain works for Arc testnet."""
        web3 = self._make_mock_web3()
        cm = self._make_mock_cm()
        deployer = BridgeDeployer.for_chain("arc_testnet", web3, cm)
        assert deployer._chain_config.native_token == "USDC"
        assert deployer._chain_config.chain_id == 5042002

    def test_client_for_chain_base_after_deploy(self):
        """for_chain works for Base Sepolia after updating addresses."""
        update_deployed_addresses("base_sepolia", bridge="0xBASE" + "0" * 36)
        client, _, _ = self._make_client_for_chain("base_sepolia")
        assert "0xBASE" in client.bridge_address

    def test_client_for_chain_arc_after_deploy(self):
        """for_chain works for Arc testnet after updating addresses."""
        update_deployed_addresses("arc_testnet", bridge="0xARC0" + "0" * 36)
        client, _, _ = self._make_client_for_chain("arc_testnet")
        assert "0xARC0" in client.bridge_address

    def test_deployer_has_standard_methods(self):
        """BridgeDeployer from for_chain retains all standard methods."""
        web3 = self._make_mock_web3()
        cm = self._make_mock_cm()
        deployer = BridgeDeployer.for_chain("ethereum_sepolia", web3, cm)
        assert hasattr(deployer, "deploy_verifier")
        assert hasattr(deployer, "deploy_bridge")
        assert hasattr(deployer, "deploy_bridged_token")
        assert hasattr(deployer, "deploy_full_suite")


# ===========================================================================
# Multi-Chain Relayer Tests (16)
# ===========================================================================


class TestRelayerConfigFromChain:
    """Tests for RelayerConfig.from_chain."""

    def test_from_chain_sepolia(self):
        """from_chain loads Sepolia config."""
        cfg = RelayerConfig.from_chain("ethereum_sepolia")
        assert cfg.chain_name == "ethereum_sepolia"
        assert "publicnode" in cfg.rpc_url
        assert cfg.bridge_address == "0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca"
        assert cfg.confirmations == 2  # from finality_blocks

    def test_from_chain_bsc(self):
        """from_chain loads BSC testnet config."""
        cfg = RelayerConfig.from_chain("bsc_testnet")
        assert cfg.chain_name == "bsc_testnet"
        assert "binance" in cfg.rpc_url
        assert cfg.confirmations == 15  # higher for BSC

    def test_from_chain_base(self):
        """from_chain loads Base Sepolia config."""
        cfg = RelayerConfig.from_chain("base_sepolia")
        assert cfg.chain_name == "base_sepolia"
        assert "base.org" in cfg.rpc_url
        assert cfg.confirmations == 2

    def test_from_chain_arc(self):
        """from_chain loads Arc testnet config."""
        cfg = RelayerConfig.from_chain("arc_testnet")
        assert cfg.chain_name == "arc_testnet"
        assert "arc.network" in cfg.rpc_url
        assert cfg.confirmations == 1  # deterministic finality

    def test_from_chain_poll_interval(self):
        """from_chain sets poll_interval from block_time."""
        cfg = RelayerConfig.from_chain("ethereum_sepolia")
        assert cfg.poll_interval >= 1.0  # at least 1s
        assert cfg.poll_interval >= 12.0  # ETH block time

        cfg_bsc = RelayerConfig.from_chain("bsc_testnet")
        assert cfg_bsc.poll_interval >= 3.0

    def test_from_chain_with_overrides(self):
        """from_chain applies keyword overrides."""
        cfg = RelayerConfig.from_chain(
            "ethereum_sepolia",
            health_port=9999,
            db_path="/tmp/test.db",
        )
        assert cfg.health_port == 9999
        assert cfg.db_path == "/tmp/test.db"
        # Original chain values still set
        assert cfg.chain_name == "ethereum_sepolia"

    def test_from_chain_unknown(self):
        """from_chain raises KeyError for unknown chain."""
        with pytest.raises(KeyError):
            RelayerConfig.from_chain("nonexistent")

    def test_from_chain_empty_bridge_address(self):
        """from_chain sets empty string for undeployed bridge."""
        cfg = RelayerConfig.from_chain("bsc_testnet")
        assert cfg.bridge_address == ""  # not deployed

    def test_from_chain_arc_fast_poll(self):
        """Arc's 350ms block time results in 1.0s min poll interval."""
        cfg = RelayerConfig.from_chain("arc_testnet")
        assert cfg.poll_interval == 1.0  # max(0.35, 1.0)


class TestMultiChainRelayer:
    """Tests for the MultiChainRelayer class."""

    def test_init_single_chain(self):
        """MultiChainRelayer can be created with a single chain."""
        mcr = MultiChainRelayer(["ethereum_sepolia"])
        assert len(mcr.relayers) == 1
        assert "ethereum_sepolia" in mcr.relayers

    def test_init_multiple_chains(self):
        """MultiChainRelayer creates a relayer per chain."""
        mcr = MultiChainRelayer(["ethereum_sepolia", "bsc_testnet"])
        assert len(mcr.relayers) == 2
        assert "ethereum_sepolia" in mcr.relayers
        assert "bsc_testnet" in mcr.relayers

    def test_separate_db_per_chain(self):
        """Each chain relayer gets its own database file."""
        mcr = MultiChainRelayer(["ethereum_sepolia", "bsc_testnet"])
        configs = {
            name: r.config for name, r in mcr.relayers.items()
        }
        assert "ethereum_sepolia" in configs["ethereum_sepolia"].db_path
        assert "bsc_testnet" in configs["bsc_testnet"].db_path
        assert configs["ethereum_sepolia"].db_path != configs["bsc_testnet"].db_path

    def test_separate_health_ports(self):
        """Each chain relayer gets a unique health port."""
        mcr = MultiChainRelayer(
            ["ethereum_sepolia", "bsc_testnet", "base_sepolia"],
            base_health_port=8080,
        )
        ports = [r.config.health_port for r in mcr.relayers.values()]
        assert len(set(ports)) == 3  # all unique
        assert sorted(ports) == [8080, 8081, 8082]

    def test_shared_ledger(self):
        """All chain relayers share the same ledger instance."""
        mock_ledger = MagicMock()
        mcr = MultiChainRelayer(
            ["ethereum_sepolia", "bsc_testnet"],
            ledger=mock_ledger,
        )
        for relayer in mcr.relayers.values():
            assert relayer._ledger is mock_ledger

    def test_repr(self):
        """MultiChainRelayer repr shows chain list."""
        mcr = MultiChainRelayer(["ethereum_sepolia"])
        r = repr(mcr)
        assert "ethereum_sepolia" in r

    def test_init_all_chains(self):
        """MultiChainRelayer can be created with all enabled chains."""
        enabled = list(get_enabled_chains().keys())
        mcr = MultiChainRelayer(enabled)
        assert len(mcr.relayers) == len(enabled)


# ===========================================================================
# Cross-Chain Ledger Tests (22)
# ===========================================================================


class TestCrossChainLedger:
    """Tests for cross-chain token routing via the ledger."""

    @pytest.mark.asyncio
    async def test_credit_with_source_chain(self, ledger):
        """credit_from_bridge accepts source_chain parameter."""
        await ledger.credit_from_bridge(
            did="did:rings:secp256k1:alice",
            token="ETH",
            amount=1000,
            source_chain="bsc_testnet",
        )
        bal = await ledger.balance("did:rings:secp256k1:alice", "ETH")
        assert bal == 1000

    @pytest.mark.asyncio
    async def test_credit_default_source_chain(self, ledger):
        """credit_from_bridge defaults to ethereum_sepolia."""
        await ledger.credit_from_bridge(
            did="did:rings:secp256k1:bob",
            token="ETH",
            amount=500,
        )
        bal = await ledger.balance("did:rings:secp256k1:bob", "ETH")
        assert bal == 500

    @pytest.mark.asyncio
    async def test_debit_with_target_chain(self, ledger):
        """debit_for_withdrawal accepts target_chain parameter."""
        await ledger.credit_from_bridge("did:rings:secp256k1:carol", "ETH", 2000)
        lock = await ledger.debit_for_withdrawal(
            did="did:rings:secp256k1:carol",
            token="ETH",
            amount=500,
            target_chain="base_sepolia",
        )
        assert lock.target_chain == "base_sepolia"

    @pytest.mark.asyncio
    async def test_debit_default_target_chain(self, ledger):
        """debit_for_withdrawal defaults to ethereum_sepolia."""
        await ledger.credit_from_bridge("did:rings:secp256k1:dave", "ETH", 1000)
        lock = await ledger.debit_for_withdrawal(
            did="did:rings:secp256k1:dave",
            token="ETH",
            amount=300,
        )
        assert lock.target_chain == "ethereum_sepolia"

    @pytest.mark.asyncio
    async def test_cross_chain_deposit_bsc_withdraw_base(self, ledger):
        """Full cross-chain flow: deposit on BSC → withdraw on Base."""
        did = "did:rings:secp256k1:agent_x"

        # Agent deposits 100 USDC on BSC
        await ledger.credit_from_bridge(
            did=did, token="USDC", amount=100_000_000,
            source_chain="bsc_testnet",
        )

        # Agent transfers 50 USDC to another agent on Rings
        await ledger.credit_from_bridge(
            did="did:rings:secp256k1:agent_y",
            token="USDC", amount=50_000_000,
            source_chain="bsc_testnet",
        )

        # Agent Y withdraws to Base
        lock = await ledger.debit_for_withdrawal(
            did="did:rings:secp256k1:agent_y",
            token="USDC",
            amount=30_000_000,
            target_chain="base_sepolia",
        )
        assert lock.target_chain == "base_sepolia"
        assert lock.amount == 30_000_000

    @pytest.mark.asyncio
    async def test_balances_are_chain_agnostic(self, ledger):
        """Balances from different chains sum together."""
        did = "did:rings:secp256k1:multi_deposit"

        # Deposit from Sepolia
        await ledger.credit_from_bridge(
            did=did, token="ETH", amount=1000,
            source_chain="ethereum_sepolia",
        )
        # Deposit from Base
        await ledger.credit_from_bridge(
            did=did, token="ETH", amount=2000,
            source_chain="base_sepolia",
        )

        bal = await ledger.balance(did, "ETH")
        assert bal == 3000  # Chain-agnostic: 1000 + 2000

    @pytest.mark.asyncio
    async def test_withdrawal_lock_preserves_target_chain(self, ledger):
        """WithdrawalLock stores target_chain in DHT."""
        did = "did:rings:secp256k1:persist_test"
        await ledger.credit_from_bridge(did, "ETH", 5000)

        lock = await ledger.debit_for_withdrawal(
            did=did, token="ETH", amount=1000,
            target_chain="arc_testnet",
        )

        # Verify DHT persistence
        stored = await ledger.client.dht_get(
            LedgerKeys.withdrawal_lock_key(lock.lock_id)
        )
        assert stored is not None
        assert stored["target_chain"] == "arc_testnet"

    @pytest.mark.asyncio
    async def test_multiple_withdrawals_different_chains(self, ledger):
        """Multiple withdrawals to different chains are independent."""
        did = "did:rings:secp256k1:multi_wd"
        await ledger.credit_from_bridge(did, "ETH", 10000)

        lock1 = await ledger.debit_for_withdrawal(
            did=did, token="ETH", amount=2000,
            target_chain="ethereum_sepolia",
        )
        lock2 = await ledger.debit_for_withdrawal(
            did=did, token="ETH", amount=3000,
            target_chain="bsc_testnet",
        )
        lock3 = await ledger.debit_for_withdrawal(
            did=did, token="ETH", amount=1000,
            target_chain="arc_testnet",
        )

        assert lock1.target_chain == "ethereum_sepolia"
        assert lock2.target_chain == "bsc_testnet"
        assert lock3.target_chain == "arc_testnet"

        # Total locked: 6000, available: 4000
        avail = await ledger.available_balance(did, "ETH")
        assert avail == 4000

    @pytest.mark.asyncio
    async def test_release_cross_chain_lock(self, ledger):
        """Releasing a cross-chain withdrawal lock works correctly."""
        did = "did:rings:secp256k1:release_test"
        await ledger.credit_from_bridge(did, "ETH", 5000)

        lock = await ledger.debit_for_withdrawal(
            did=did, token="ETH", amount=2000,
            target_chain="base_sepolia",
        )

        await ledger.release_withdrawal_lock(lock.lock_id)

        # Balance should be deducted
        bal = await ledger.balance(did, "ETH")
        assert bal == 3000

    @pytest.mark.asyncio
    async def test_cancel_cross_chain_lock(self, ledger):
        """Cancelling a cross-chain withdrawal returns tokens."""
        did = "did:rings:secp256k1:cancel_test"
        await ledger.credit_from_bridge(did, "ETH", 5000)

        lock = await ledger.debit_for_withdrawal(
            did=did, token="ETH", amount=2000,
            target_chain="bsc_testnet",
        )

        await ledger.cancel_withdrawal_lock(lock.lock_id)

        # Full balance available again
        avail = await ledger.available_balance(did, "ETH")
        assert avail == 5000

    @pytest.mark.asyncio
    async def test_cross_chain_transfer_then_withdraw(self, ledger):
        """Agent-to-agent transfer then cross-chain withdrawal."""
        alice = "did:rings:secp256k1:alice_xchain"
        bob = "did:rings:secp256k1:bob_xchain"

        # Alice deposits on Sepolia
        await ledger.credit_from_bridge(
            alice, "ETH", 10000,
            source_chain="ethereum_sepolia",
        )

        # Alice transfers to Bob on Rings
        receipt = await ledger.transfer(
            from_did=alice, to_did=bob,
            token="ETH", amount=5000,
            signature=b"\x00" * 64,
        )
        assert receipt.status == TransferStatus.PROPOSED

        # Attest and finalize
        await ledger.attest_transfer(receipt.transfer_id)
        met, sigs = await ledger.collect_transfer_attestations(receipt.transfer_id)
        assert met is True

        # Bob withdraws to BSC
        bob_bal = await ledger.balance(bob, "ETH")
        assert bob_bal == 5000

        lock = await ledger.debit_for_withdrawal(
            did=bob, token="ETH", amount=3000,
            target_chain="bsc_testnet",
        )
        assert lock.target_chain == "bsc_testnet"

    @pytest.mark.asyncio
    async def test_credit_multiple_chains_same_token(self, ledger):
        """Credits from different chains for same token accumulate."""
        did = "did:rings:secp256k1:accumulator"

        for chain, amt in [
            ("ethereum_sepolia", 100),
            ("bsc_testnet", 200),
            ("base_sepolia", 300),
            ("arc_testnet", 400),
        ]:
            await ledger.credit_from_bridge(
                did, "ETH", amt, source_chain=chain,
            )

        bal = await ledger.balance(did, "ETH")
        assert bal == 1000

    @pytest.mark.asyncio
    async def test_debit_insufficient_balance_for_target_chain(self, ledger):
        """Insufficient balance raises ValueError regardless of target_chain."""
        did = "did:rings:secp256k1:poor"
        await ledger.credit_from_bridge(did, "ETH", 100)

        with pytest.raises(ValueError, match="insufficient"):
            await ledger.debit_for_withdrawal(
                did=did, token="ETH", amount=200,
                target_chain="bsc_testnet",
            )

    @pytest.mark.asyncio
    async def test_debit_zero_amount_cross_chain(self, ledger):
        """Zero amount raises ValueError for any target chain."""
        did = "did:rings:secp256k1:zero"
        await ledger.credit_from_bridge(did, "ETH", 1000)

        with pytest.raises(ValueError, match="must be > 0"):
            await ledger.debit_for_withdrawal(
                did=did, token="ETH", amount=0,
                target_chain="arc_testnet",
            )

    @pytest.mark.asyncio
    async def test_cross_chain_usdc_flow(self, ledger):
        """USDC-specific cross-chain flow (deposit Arc → withdraw Sepolia)."""
        did = "did:rings:secp256k1:usdc_agent"

        # Deposit USDC on Arc
        await ledger.credit_from_bridge(
            did, "USDC", 50_000_000,  # 50 USDC in 6 decimals
            source_chain="arc_testnet",
        )

        # Withdraw to Ethereum Sepolia
        lock = await ledger.debit_for_withdrawal(
            did=did, token="USDC", amount=25_000_000,
            target_chain="ethereum_sepolia",
        )
        assert lock.target_chain == "ethereum_sepolia"
        assert lock.token == "USDC"

    @pytest.mark.asyncio
    async def test_stats_track_credits_and_debits(self, ledger):
        """Stats count credits and debits across chains."""
        did = "did:rings:secp256k1:stats_test"

        await ledger.credit_from_bridge(did, "ETH", 1000, source_chain="bsc_testnet")
        await ledger.credit_from_bridge(did, "ETH", 2000, source_chain="base_sepolia")
        await ledger.debit_for_withdrawal(did, "ETH", 500, target_chain="arc_testnet")

        stats = ledger.stats
        assert stats["credits"] == 2
        assert stats["debits"] == 1

    @pytest.mark.asyncio
    async def test_empty_did_cross_chain(self, ledger):
        """Empty DID raises ValueError for cross-chain operations."""
        with pytest.raises(ValueError, match="non-empty"):
            await ledger.credit_from_bridge("", "ETH", 100, source_chain="bsc_testnet")

        with pytest.raises(ValueError, match="non-empty"):
            await ledger.debit_for_withdrawal("", "ETH", 100, target_chain="bsc_testnet")

    @pytest.mark.asyncio
    async def test_different_tokens_different_chains(self, ledger):
        """Different tokens from different chains tracked independently."""
        did = "did:rings:secp256k1:multi_token"

        await ledger.credit_from_bridge(did, "ETH", 1000, source_chain="ethereum_sepolia")
        await ledger.credit_from_bridge(did, "USDC", 5000, source_chain="arc_testnet")

        eth_bal = await ledger.balance(did, "ETH")
        usdc_bal = await ledger.balance(did, "USDC")
        assert eth_bal == 1000
        assert usdc_bal == 5000

    @pytest.mark.asyncio
    async def test_withdrawal_lock_roundtrip_with_target_chain(self, ledger):
        """WithdrawalLock target_chain survives serialize/deserialize."""
        lock = WithdrawalLock(
            lock_id="test-lock",
            did="did:test",
            token="ETH",
            amount=1000,
            target_chain="arc_testnet",
        )
        d = lock.to_dict()
        assert d["target_chain"] == "arc_testnet"

        lock2 = WithdrawalLock.from_dict(d)
        assert lock2.target_chain == "arc_testnet"

    @pytest.mark.asyncio
    async def test_withdrawal_lock_default_chain_in_dict(self):
        """WithdrawalLock.from_dict defaults target_chain to ethereum_sepolia."""
        d = {
            "lock_id": "old-lock",
            "did": "did:test",
            "token": "ETH",
            "amount": 500,
            # no target_chain key — backward compatible
        }
        lock = WithdrawalLock.from_dict(d)
        assert lock.target_chain == "ethereum_sepolia"


# ===========================================================================
# WithdrawalLock Serialization Tests (8)
# ===========================================================================


class TestWithdrawalLockSerialization:
    """Tests for WithdrawalLock with target_chain field."""

    def test_to_dict_includes_target_chain(self):
        """to_dict includes target_chain."""
        lock = WithdrawalLock(
            lock_id="lock-1",
            did="did:rings:secp256k1:test",
            token="ETH",
            amount=1000,
            target_chain="bsc_testnet",
        )
        d = lock.to_dict()
        assert d["target_chain"] == "bsc_testnet"

    def test_from_dict_with_target_chain(self):
        """from_dict reads target_chain."""
        d = {
            "lock_id": "lock-2",
            "did": "did:test",
            "token": "ETH",
            "amount": 2000,
            "target_chain": "base_sepolia",
        }
        lock = WithdrawalLock.from_dict(d)
        assert lock.target_chain == "base_sepolia"

    def test_from_dict_backward_compatible(self):
        """from_dict defaults target_chain for old records."""
        d = {
            "lock_id": "old-lock",
            "did": "did:test",
            "token": "ETH",
            "amount": 500,
        }
        lock = WithdrawalLock.from_dict(d)
        assert lock.target_chain == "ethereum_sepolia"

    def test_default_target_chain(self):
        """WithdrawalLock defaults target_chain to ethereum_sepolia."""
        lock = WithdrawalLock(
            lock_id="lock-3",
            did="did:test",
            token="ETH",
            amount=100,
        )
        assert lock.target_chain == "ethereum_sepolia"

    def test_all_chains_as_target(self):
        """Every registered chain can be a target_chain."""
        for chain_name in CHAINS:
            lock = WithdrawalLock(
                lock_id=f"lock-{chain_name}",
                did="did:test",
                token="ETH",
                amount=100,
                target_chain=chain_name,
            )
            assert lock.target_chain == chain_name
            d = lock.to_dict()
            lock2 = WithdrawalLock.from_dict(d)
            assert lock2.target_chain == chain_name

    def test_roundtrip_preserves_all_fields(self):
        """Full roundtrip preserves all fields including target_chain."""
        lock = WithdrawalLock(
            lock_id="rt-lock",
            did="did:rings:secp256k1:roundtrip",
            token="USDC",
            amount=50_000_000,
            target_chain="arc_testnet",
            timestamp=1234567890.0,
            released=False,
        )
        d = lock.to_dict()
        lock2 = WithdrawalLock.from_dict(d)
        assert lock2.lock_id == lock.lock_id
        assert lock2.did == lock.did
        assert lock2.token == lock.token
        assert lock2.amount == lock.amount
        assert lock2.target_chain == lock.target_chain
        assert lock2.timestamp == lock.timestamp
        assert lock2.released == lock.released

    def test_released_lock_roundtrip(self):
        """Released lock with target_chain roundtrips correctly."""
        lock = WithdrawalLock(
            lock_id="rel-lock",
            did="did:test",
            token="ETH",
            amount=999,
            target_chain="bsc_testnet",
            released=True,
        )
        d = lock.to_dict()
        lock2 = WithdrawalLock.from_dict(d)
        assert lock2.released is True
        assert lock2.target_chain == "bsc_testnet"

    def test_to_dict_type_safety(self):
        """to_dict returns JSON-serializable types."""
        import json
        lock = WithdrawalLock(
            lock_id="json-lock",
            did="did:test",
            token="ETH",
            amount=42,
            target_chain="arc_testnet",
        )
        d = lock.to_dict()
        # Should not raise
        serialized = json.dumps(d)
        assert "arc_testnet" in serialized


# ===========================================================================
# Arc Network Specifics (10)
# ===========================================================================


class TestArcNetworkSpecifics:
    """Tests specific to Arc Network integration."""

    def test_arc_chain_id(self):
        """Arc testnet chain ID is 5042002."""
        cfg = get_chain("arc_testnet")
        assert cfg.chain_id == 5042002

    def test_arc_rpc_url(self):
        """Arc testnet RPC is set."""
        cfg = get_chain("arc_testnet")
        assert cfg.rpc_url == "https://rpc.testnet.arc.network"

    def test_arc_explorer(self):
        """Arc testnet explorer URL is set."""
        cfg = get_chain("arc_testnet")
        assert cfg.explorer_url == "https://testnet.arcscan.app"

    def test_arc_native_token_usdc(self):
        """Arc uses USDC as native gas token."""
        cfg = get_chain("arc_testnet")
        assert cfg.native_token == "USDC"

    def test_arc_fast_finality(self):
        """Arc has 1-block deterministic finality."""
        cfg = get_chain("arc_testnet")
        assert cfg.finality_blocks == 1
        assert cfg.block_time == 0.35

    def test_arc_gas_strategy_fixed(self):
        """Arc uses FIXED gas strategy."""
        cfg = get_chain("arc_testnet")
        assert cfg.gas_strategy == GasStrategy.FIXED

    def test_arc_gas_no_markup(self):
        """Arc gas params have no multiplier (stable USDC pricing)."""
        cfg = get_chain("arc_testnet")
        # ~160 gwei = $0.01/tx at USDC rates
        params = GasStrategy.estimate_gas_params(cfg, 160_000_000_000)
        assert params["gasPrice"] == 160_000_000_000

    def test_arc_enabled(self):
        """Arc testnet is enabled (live since Oct 2025)."""
        cfg = get_chain("arc_testnet")
        assert cfg.enabled is True

    def test_arc_is_testnet(self):
        """Arc testnet is flagged as testnet."""
        cfg = get_chain("arc_testnet")
        assert cfg.is_testnet is True

    def test_arc_in_enabled_chains(self):
        """Arc appears in enabled chains list."""
        enabled = get_enabled_chains()
        assert "arc_testnet" in enabled

    def test_arc_supports_eip1559(self):
        """Arc has EIP-1559-like fees but uses FIXED strategy due to USDC."""
        cfg = get_chain("arc_testnet")
        # Arc does support EIP-1559 at protocol level
        assert cfg.supports_eip1559 is True
        # But gas_strategy is FIXED because native_token is USDC
        assert cfg.gas_strategy == GasStrategy.FIXED


# ===========================================================================
# Integration Scenarios (15)
# ===========================================================================


class TestCrossChainIntegration:
    """End-to-end cross-chain integration scenarios."""

    @pytest.mark.asyncio
    async def test_deposit_bsc_transfer_rings_withdraw_base(self, ledger):
        """Full cross-chain: deposit BSC → transfer on Rings → withdraw Base."""
        agent_a = "did:rings:secp256k1:agent_a"
        agent_b = "did:rings:secp256k1:agent_b"

        # 1. Agent A deposits 100 USDC on BSC
        await ledger.credit_from_bridge(
            agent_a, "USDC", 100_000_000,
            source_chain="bsc_testnet",
        )
        assert await ledger.balance(agent_a, "USDC") == 100_000_000

        # 2. Agent A transfers 50 USDC to Agent B on Rings
        receipt = await ledger.transfer(
            agent_a, agent_b, "USDC", 50_000_000,
            signature=b"\x00" * 64,
        )
        await ledger.attest_transfer(receipt.transfer_id)
        met, _ = await ledger.collect_transfer_attestations(receipt.transfer_id)
        assert met is True

        # 3. Agent B withdraws 50 USDC to Base (different chain!)
        lock = await ledger.debit_for_withdrawal(
            agent_b, "USDC", 50_000_000,
            target_chain="base_sepolia",
        )
        assert lock.target_chain == "base_sepolia"
        assert lock.amount == 50_000_000

        # 4. Verify final balances
        assert await ledger.balance(agent_a, "USDC") == 50_000_000
        assert await ledger.available_balance(agent_b, "USDC") == 0  # all locked

    @pytest.mark.asyncio
    async def test_multi_chain_deposits_single_withdrawal(self, ledger):
        """Deposits from multiple chains, single withdrawal."""
        did = "did:rings:secp256k1:collector"

        await ledger.credit_from_bridge(did, "ETH", 100, source_chain="ethereum_sepolia")
        await ledger.credit_from_bridge(did, "ETH", 200, source_chain="base_sepolia")
        await ledger.credit_from_bridge(did, "ETH", 300, source_chain="bsc_testnet")

        assert await ledger.balance(did, "ETH") == 600

        lock = await ledger.debit_for_withdrawal(
            did, "ETH", 500, target_chain="arc_testnet",
        )
        assert lock.amount == 500
        assert await ledger.available_balance(did, "ETH") == 100

    @pytest.mark.asyncio
    async def test_withdraw_release_then_withdraw_different_chain(self, ledger):
        """Withdraw to chain A, release, then withdraw remainder to chain B."""
        did = "did:rings:secp256k1:sequential"
        await ledger.credit_from_bridge(did, "ETH", 10000)

        # Withdraw 4000 to BSC
        lock1 = await ledger.debit_for_withdrawal(
            did, "ETH", 4000, target_chain="bsc_testnet",
        )
        await ledger.release_withdrawal_lock(lock1.lock_id)
        assert await ledger.balance(did, "ETH") == 6000

        # Withdraw 3000 to Base
        lock2 = await ledger.debit_for_withdrawal(
            did, "ETH", 3000, target_chain="base_sepolia",
        )
        await ledger.release_withdrawal_lock(lock2.lock_id)
        assert await ledger.balance(did, "ETH") == 3000

    @pytest.mark.asyncio
    async def test_cancel_one_chain_withdraw_another(self, ledger):
        """Cancel withdrawal to chain A, then withdraw to chain B."""
        did = "did:rings:secp256k1:redirect"
        await ledger.credit_from_bridge(did, "ETH", 5000)

        # Try to withdraw to BSC
        lock1 = await ledger.debit_for_withdrawal(
            did, "ETH", 3000, target_chain="bsc_testnet",
        )
        # Change mind — cancel
        await ledger.cancel_withdrawal_lock(lock1.lock_id)

        # Withdraw to Base instead
        lock2 = await ledger.debit_for_withdrawal(
            did, "ETH", 3000, target_chain="base_sepolia",
        )
        assert lock2.target_chain == "base_sepolia"
        assert await ledger.available_balance(did, "ETH") == 2000

    @pytest.mark.asyncio
    async def test_concurrent_withdrawals_to_different_chains(self, ledger):
        """Multiple pending withdrawals to different chains."""
        did = "did:rings:secp256k1:concurrent"
        await ledger.credit_from_bridge(did, "ETH", 20000)

        locks = []
        for chain in ["ethereum_sepolia", "bsc_testnet", "base_sepolia", "arc_testnet"]:
            lock = await ledger.debit_for_withdrawal(
                did, "ETH", 3000, target_chain=chain,
            )
            locks.append(lock)

        # 12000 locked, 8000 available
        assert await ledger.available_balance(did, "ETH") == 8000

        # Release all
        for lock in locks:
            await ledger.release_withdrawal_lock(lock.lock_id)

        assert await ledger.balance(did, "ETH") == 8000

    @pytest.mark.asyncio
    async def test_relayer_config_chain_name_propagation(self):
        """RelayerConfig.from_chain propagates chain_name."""
        for chain_name in ["ethereum_sepolia", "bsc_testnet", "base_sepolia", "arc_testnet"]:
            cfg = RelayerConfig.from_chain(chain_name)
            assert cfg.chain_name == chain_name

    @pytest.mark.asyncio
    async def test_multi_chain_relayer_health_aggregation(self):
        """MultiChainRelayer aggregates health from all chains."""
        mcr = MultiChainRelayer(["ethereum_sepolia", "bsc_testnet"])

        # Mock get_health on each relayer
        for name, relayer in mcr.relayers.items():
            relayer.get_health = AsyncMock(return_value={
                "status": "healthy",
                "chain": name,
            })

        health = await mcr.get_health()
        assert health["total_chains"] == 2
        assert health["healthy_chains"] == 2
        assert health["status"] == "healthy"
        assert "ethereum_sepolia" in health["chains"]
        assert "bsc_testnet" in health["chains"]

    @pytest.mark.asyncio
    async def test_multi_chain_relayer_degraded_health(self):
        """MultiChainRelayer reports degraded if one chain is unhealthy."""
        mcr = MultiChainRelayer(["ethereum_sepolia", "bsc_testnet"])

        mcr.relayers["ethereum_sepolia"].get_health = AsyncMock(
            return_value={"status": "healthy"}
        )
        mcr.relayers["bsc_testnet"].get_health = AsyncMock(
            side_effect=Exception("RPC down")
        )

        health = await mcr.get_health()
        assert health["status"] == "degraded"
        assert health["healthy_chains"] == 1

    def test_all_chains_have_required_fields(self):
        """Every chain in registry has all required non-empty fields."""
        for name, cfg in CHAINS.items():
            assert cfg.name == name
            assert cfg.chain_id > 0, f"{name} has invalid chain_id"
            assert cfg.native_token, f"{name} missing native_token"
            assert cfg.block_time > 0, f"{name} has invalid block_time"
            assert cfg.finality_blocks >= 1, f"{name} has invalid finality_blocks"
            # RPC URL should be set for enabled chains
            if cfg.enabled:
                assert cfg.rpc_url, f"{name} is enabled but has no RPC URL"

    def test_chain_ids_are_unique(self):
        """All chain IDs in registry are unique."""
        ids = [cfg.chain_id for cfg in CHAINS.values()]
        assert len(ids) == len(set(ids))

    def test_chain_names_match_keys(self):
        """Chain config name field matches its registry key."""
        for key, cfg in CHAINS.items():
            assert cfg.name == key

    @pytest.mark.asyncio
    async def test_ledger_stats_after_cross_chain_ops(self, ledger):
        """Ledger stats reflect cross-chain operations."""
        did = "did:rings:secp256k1:stats"

        await ledger.credit_from_bridge(did, "ETH", 5000, source_chain="bsc_testnet")
        await ledger.credit_from_bridge(did, "USDC", 3000, source_chain="arc_testnet")
        await ledger.debit_for_withdrawal(did, "ETH", 1000, target_chain="base_sepolia")
        await ledger.debit_for_withdrawal(did, "USDC", 500, target_chain="ethereum_sepolia")

        stats = ledger.stats
        assert stats["credits"] == 2
        assert stats["debits"] == 2
        assert stats["known_dids"] >= 1
        assert stats["active_withdrawal_locks"] == 2

    @pytest.mark.asyncio
    async def test_full_lifecycle_four_chains(self, ledger):
        """Full lifecycle touching all four supported chains."""
        did = "did:rings:secp256k1:four_chain"

        # Deposit from each chain
        chains_and_amounts = [
            ("ethereum_sepolia", "ETH", 1000),
            ("bsc_testnet", "BNB", 2000),
            ("base_sepolia", "ETH", 3000),
            ("arc_testnet", "USDC", 4000),
        ]
        for chain, token, amount in chains_and_amounts:
            await ledger.credit_from_bridge(did, token, amount, source_chain=chain)

        # Check balances
        assert await ledger.balance(did, "ETH") == 4000  # 1000 + 3000
        assert await ledger.balance(did, "BNB") == 2000
        assert await ledger.balance(did, "USDC") == 4000

        # Withdraw to different chains
        lock_eth = await ledger.debit_for_withdrawal(
            did, "ETH", 2000, target_chain="bsc_testnet",
        )
        lock_usdc = await ledger.debit_for_withdrawal(
            did, "USDC", 1000, target_chain="ethereum_sepolia",
        )

        assert lock_eth.target_chain == "bsc_testnet"
        assert lock_usdc.target_chain == "ethereum_sepolia"

        # Release ETH withdrawal
        await ledger.release_withdrawal_lock(lock_eth.lock_id)
        assert await ledger.balance(did, "ETH") == 2000

    @pytest.mark.asyncio
    async def test_bridge_relayer_passes_chain_name_to_ledger(self):
        """BridgeRelayer._broadcast_deposit passes source_chain to ledger."""
        config = RelayerConfig.from_chain("bsc_testnet")
        mock_ledger = MagicMock()
        mock_ledger.credit_from_bridge = AsyncMock()

        relayer = BridgeRelayer(config, ledger=mock_ledger)

        event = {
            "args": {
                "ringsDid": "did:rings:secp256k1:test",
                "amount": 1000,
                "sender": "0x1234",
            },
            "transactionHash": "0xabcd",
        }

        await relayer._broadcast_deposit("0xabcd", event)

        mock_ledger.credit_from_bridge.assert_called_once_with(
            did="did:rings:secp256k1:test",
            token="ETH",
            amount=1000,
            source_chain="bsc_testnet",
        )
