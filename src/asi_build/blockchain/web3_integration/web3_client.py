"""
Web3 Client for Kenny AGI Blockchain Audit Trail

High-level Web3 client that provides connection management,
automatic retry logic, and failover capabilities across multiple RPC endpoints.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
import requests
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import AsyncWeb3, Web3
from web3.middleware import geth_poa_middleware

from .network_config import NetworkConfig, get_network_by_chain_id, get_network_by_name

logger = logging.getLogger(__name__)


class Web3Error(Exception):
    """Custom exception for Web3 operations"""

    pass


@dataclass
class BlockInfo:
    """Information about a blockchain block"""

    number: int
    hash: str
    timestamp: datetime
    transaction_count: int
    gas_used: int
    gas_limit: int


@dataclass
class TransactionInfo:
    """Information about a blockchain transaction"""

    hash: str
    block_number: Optional[int]
    from_address: str
    to_address: Optional[str]
    value: int
    gas: int
    gas_price: int
    nonce: int
    input_data: str
    status: Optional[int] = None
    gas_used: Optional[int] = None
    effective_gas_price: Optional[int] = None


class Web3Client:
    """
    High-level Web3 client with automatic failover and retry logic

    Features:
    - Multiple RPC endpoint support with automatic failover
    - Connection pooling and health monitoring
    - Automatic retry with exponential backoff
    - Account management and transaction signing
    - Gas estimation and optimization
    """

    def __init__(
        self,
        network: Union[NetworkConfig, str, int],
        private_key: Optional[str] = None,
        request_timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        pool_size: int = 10,
    ):
        """
        Initialize Web3 client

        Args:
            network: Network configuration, name, or chain ID
            private_key: Private key for transaction signing
            request_timeout: RPC request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Initial retry delay in seconds
            pool_size: Connection pool size
        """
        # Resolve network configuration
        if isinstance(network, str):
            self.network = get_network_by_name(network)
            if not self.network:
                raise Web3Error(f"Unknown network name: {network}")
        elif isinstance(network, int):
            self.network = get_network_by_chain_id(network)
            if not self.network:
                raise Web3Error(f"Unknown chain ID: {network}")
        elif isinstance(network, NetworkConfig):
            self.network = network
        else:
            raise Web3Error("Invalid network specification")

        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.pool_size = pool_size

        # Connection management
        self.w3_instances = []
        self.current_rpc_index = 0
        self.rpc_health = {}

        # Account management
        self.account = None
        if private_key:
            self.account = Account.from_key(private_key)

        # Session for HTTP requests
        self.session = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self):
        """Initialize Web3 connections to all RPC endpoints"""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.request_timeout)
            )

            # Initialize Web3 instances for each RPC URL
            for i, rpc_url in enumerate(self.network.rpc_urls):
                try:
                    # Create Web3 instance
                    if rpc_url.startswith("ws"):
                        provider = Web3.AsyncHTTPProvider(rpc_url)
                    else:
                        provider = Web3.AsyncHTTPProvider(rpc_url)

                    w3 = AsyncWeb3(provider)

                    # Add middleware for PoA networks
                    if self.network.chain_id in [56, 97, 137, 80001]:  # BSC, Polygon
                        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

                    self.w3_instances.append(w3)
                    self.rpc_health[i] = True

                    logger.info(f"Initialized Web3 connection to {rpc_url}")

                except Exception as e:
                    logger.warning(f"Failed to initialize connection to {rpc_url}: {str(e)}")
                    self.rpc_health[i] = False

            if not self.w3_instances:
                raise Web3Error("Failed to connect to any RPC endpoints")

            # Test connection
            await self._test_connection()

            logger.info(
                f"Connected to {self.network.name} with {len(self.w3_instances)} RPC endpoints"
            )

        except Exception as e:
            raise Web3Error(f"Failed to connect to blockchain: {str(e)}")

    async def disconnect(self):
        """Close all connections"""
        if self.session:
            await self.session.close()
            self.session = None

        self.w3_instances.clear()
        self.rpc_health.clear()

        logger.info("Disconnected from blockchain")

    async def _get_working_w3(self) -> AsyncWeb3:
        """Get a working Web3 instance with failover"""
        if not self.w3_instances:
            raise Web3Error("No Web3 connections available")

        # Try current RPC first
        for attempt in range(len(self.w3_instances)):
            index = (self.current_rpc_index + attempt) % len(self.w3_instances)

            if self.rpc_health.get(index, False):
                try:
                    w3 = self.w3_instances[index]
                    # Quick health check
                    await w3.eth.get_block_number()
                    self.current_rpc_index = index
                    return w3
                except Exception as e:
                    logger.warning(f"RPC endpoint {index} failed: {str(e)}")
                    self.rpc_health[index] = False

        raise Web3Error("All RPC endpoints are unhealthy")

    async def _execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                w3 = await self._get_working_w3()
                return await func(w3, *args, **kwargs)

            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")

                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)

        raise Web3Error(f"All retry attempts failed. Last error: {str(last_exception)}")

    async def _test_connection(self):
        """Test blockchain connection"""

        async def _test(w3):
            block_number = await w3.eth.get_block_number()
            chain_id = await w3.eth.chain_id

            if chain_id != self.network.chain_id:
                raise Web3Error(
                    f"Chain ID mismatch: expected {self.network.chain_id}, got {chain_id}"
                )

            return block_number

        block_number = await self._execute_with_retry(_test)
        logger.info(f"Connection test successful. Current block: {block_number}")

    async def get_block_number(self) -> int:
        """Get current block number"""

        async def _get_block_number(w3):
            return await w3.eth.get_block_number()

        return await self._execute_with_retry(_get_block_number)

    async def get_block(self, block_identifier: Union[int, str, bytes]) -> BlockInfo:
        """Get block information"""

        async def _get_block(w3, block_id):
            block = await w3.eth.get_block(block_id)
            return BlockInfo(
                number=block["number"],
                hash=block["hash"].hex(),
                timestamp=datetime.fromtimestamp(block["timestamp"]),
                transaction_count=len(block["transactions"]),
                gas_used=block["gasUsed"],
                gas_limit=block["gasLimit"],
            )

        return await self._execute_with_retry(_get_block, block_identifier)

    async def get_transaction(self, tx_hash: str) -> TransactionInfo:
        """Get transaction information"""

        async def _get_transaction(w3, hash_str):
            tx = await w3.eth.get_transaction(hash_str)

            # Try to get receipt for additional info
            receipt = None
            try:
                receipt = await w3.eth.get_transaction_receipt(hash_str)
            except Exception:
                pass

            return TransactionInfo(
                hash=tx["hash"].hex(),
                block_number=tx.get("blockNumber"),
                from_address=tx["from"],
                to_address=tx.get("to"),
                value=tx["value"],
                gas=tx["gas"],
                gas_price=tx["gasPrice"],
                nonce=tx["nonce"],
                input_data=tx["input"].hex() if tx["input"] else "0x",
                status=receipt["status"] if receipt else None,
                gas_used=receipt["gasUsed"] if receipt else None,
                effective_gas_price=receipt.get("effectiveGasPrice") if receipt else None,
            )

        return await self._execute_with_retry(_get_transaction, tx_hash)

    async def get_balance(self, address: str, block: str = "latest") -> int:
        """Get account balance in wei"""

        async def _get_balance(w3, addr, block_id):
            return await w3.eth.get_balance(addr, block_id)

        return await self._execute_with_retry(_get_balance, address, block)

    async def get_nonce(self, address: str, block: str = "latest") -> int:
        """Get account nonce"""

        async def _get_nonce(w3, addr, block_id):
            return await w3.eth.get_transaction_count(addr, block_id)

        return await self._execute_with_retry(_get_nonce, address, block)

    async def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """Estimate gas for transaction"""

        async def _estimate_gas(w3, tx):
            return await w3.eth.estimate_gas(tx)

        return await self._execute_with_retry(_estimate_gas, transaction)

    async def get_gas_price(self) -> int:
        """Get current gas price"""

        async def _get_gas_price(w3):
            if self.network.supports_eip1559:
                # Get EIP-1559 fee data
                fee_data = await w3.eth.fee_history(1, "latest", [25, 50, 75])
                base_fee = fee_data["baseFeePerGas"][-1]
                priority_fees = fee_data["reward"][0]

                return {
                    "base_fee": base_fee,
                    "max_priority_fee": priority_fees[1],  # 50th percentile
                    "max_fee_per_gas": base_fee + priority_fees[1],
                }
            else:
                return await w3.eth.gas_price

        return await self._execute_with_retry(_get_gas_price)

    async def send_transaction(
        self, transaction: Dict[str, Any], private_key: Optional[str] = None
    ) -> str:
        """Send signed transaction"""
        if not private_key and not self.account:
            raise Web3Error("No private key available for signing")

        account = Account.from_key(private_key) if private_key else self.account

        async def _send_transaction(w3, tx):
            # Fill in missing transaction fields
            if "nonce" not in tx:
                tx["nonce"] = await w3.eth.get_transaction_count(account.address)

            if "chainId" not in tx:
                tx["chainId"] = await w3.eth.chain_id

            # Handle gas pricing
            if self.network.supports_eip1559:
                if "maxFeePerGas" not in tx and "maxPriorityFeePerGas" not in tx:
                    gas_data = await self.get_gas_price()
                    tx["maxFeePerGas"] = gas_data["max_fee_per_gas"]
                    tx["maxPriorityFeePerGas"] = gas_data["max_priority_fee"]
            else:
                if "gasPrice" not in tx:
                    tx["gasPrice"] = await w3.eth.gas_price

            if "gas" not in tx:
                tx["gas"] = await w3.eth.estimate_gas(tx)

            # Sign and send transaction
            signed_tx = account.sign_transaction(tx)
            tx_hash = await w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            return tx_hash.hex()

        return await self._execute_with_retry(_send_transaction, transaction)

    async def wait_for_transaction(
        self, tx_hash: str, timeout: Optional[int] = None, confirmations: Optional[int] = None
    ) -> TransactionInfo:
        """Wait for transaction confirmation"""
        timeout = timeout or self.network.timeout_seconds
        confirmations = confirmations or self.network.confirmation_blocks

        async def _wait_for_transaction(w3, hash_str):
            receipt = await w3.eth.wait_for_transaction_receipt(hash_str, timeout=timeout)

            # Wait for additional confirmations if required
            if confirmations > 1:
                target_block = receipt["blockNumber"] + confirmations - 1
                current_block = await w3.eth.get_block_number()

                while current_block < target_block:
                    await asyncio.sleep(2)  # Block time estimate
                    current_block = await w3.eth.get_block_number()

            # Get full transaction info
            return await self.get_transaction(hash_str)

        return await self._execute_with_retry(_wait_for_transaction, tx_hash)

    async def call_contract_function(
        self,
        contract_address: str,
        function_abi: Dict[str, Any],
        function_name: str,
        args: List[Any] = None,
        block: str = "latest",
    ) -> Any:
        """Call contract function (read-only)"""

        async def _call_function(w3, addr, abi, func_name, arguments, block_id):
            contract = w3.eth.contract(address=addr, abi=[abi])
            func = getattr(contract.functions, func_name)

            if arguments:
                return await func(*arguments).call(block_identifier=block_id)
            else:
                return await func().call(block_identifier=block_id)

        args = args or []
        return await self._execute_with_retry(
            _call_function, contract_address, function_abi, function_name, args, block
        )

    async def get_logs(
        self,
        contract_address: Optional[str] = None,
        topics: Optional[List[str]] = None,
        from_block: Union[int, str] = "earliest",
        to_block: Union[int, str] = "latest",
    ) -> List[Dict[str, Any]]:
        """Get contract event logs"""

        async def _get_logs(w3, addr, topic_list, from_blk, to_blk):
            filter_params = {"fromBlock": from_blk, "toBlock": to_blk}

            if addr:
                filter_params["address"] = addr
            if topic_list:
                filter_params["topics"] = topic_list

            logs = await w3.eth.get_logs(filter_params)
            return [dict(log) for log in logs]

        return await self._execute_with_retry(
            _get_logs, contract_address, topics, from_block, to_block
        )

    async def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""

        async def _get_network_info(w3):
            chain_id = await w3.eth.chain_id
            block_number = await w3.eth.get_block_number()
            gas_price = await w3.eth.gas_price

            return {
                "chain_id": chain_id,
                "network_name": self.network.name,
                "block_number": block_number,
                "gas_price": gas_price,
                "is_testnet": self.network.is_testnet,
                "supports_eip1559": self.network.supports_eip1559,
            }

        return await self._execute_with_retry(_get_network_info)

    def get_account_address(self) -> Optional[str]:
        """Get address of loaded account"""
        return self.account.address if self.account else None

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        results = {
            "network": self.network.name,
            "chain_id": self.network.chain_id,
            "rpc_endpoints": len(self.network.rpc_urls),
            "healthy_endpoints": sum(self.rpc_health.values()),
            "current_endpoint": self.current_rpc_index,
            "account_loaded": self.account is not None,
        }

        try:
            network_info = await self.get_network_info()
            results.update(network_info)
            results["status"] = "healthy"
        except Exception as e:
            results["status"] = "unhealthy"
            results["error"] = str(e)

        return results
