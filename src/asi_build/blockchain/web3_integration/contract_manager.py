"""
Contract Manager for Kenny AGI Blockchain Audit Trail

Provides high-level contract deployment and interaction functionality
with support for multiple networks and automated contract verification.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .web3_client import Web3Client, Web3Error

logger = logging.getLogger(__name__)


@dataclass
class ContractInterface:
    """Interface for a deployed smart contract"""

    name: str
    address: str
    abi: List[Dict[str, Any]]
    bytecode: Optional[str] = None
    deployed_at: Optional[datetime] = None
    deployer: Optional[str] = None
    network: Optional[str] = None
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "address": self.address,
            "abi": self.abi,
            "bytecode": self.bytecode,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "deployer": self.deployer,
            "network": self.network,
            "verified": self.verified,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContractInterface":
        """Create from dictionary"""
        data = data.copy()
        if data.get("deployed_at"):
            data["deployed_at"] = datetime.fromisoformat(data["deployed_at"])
        return cls(**data)


class ContractManager:
    """
    High-level contract management system

    Features:
    - Contract compilation and deployment
    - ABI management and function calling
    - Event monitoring and filtering
    - Contract verification
    - Multi-network deployment
    """

    def __init__(
        self,
        web3_client: Web3Client,
        contracts_dir: Optional[str] = None,
        artifacts_dir: Optional[str] = None,
    ):
        """
        Initialize contract manager

        Args:
            web3_client: Web3 client instance
            contracts_dir: Directory containing contract source files
            artifacts_dir: Directory for storing compiled artifacts
        """
        self.web3_client = web3_client
        self.contracts_dir = Path(contracts_dir) if contracts_dir else None
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else None

        # Contract registry
        self.contracts = {}

        # Load existing contracts if artifacts directory exists
        if self.artifacts_dir and self.artifacts_dir.exists():
            self._load_contracts_from_artifacts()

    def _load_contracts_from_artifacts(self):
        """Load contract interfaces from artifacts directory"""
        if not self.artifacts_dir.exists():
            return

        for artifact_file in self.artifacts_dir.glob("*.json"):
            try:
                with open(artifact_file, "r") as f:
                    data = json.load(f)

                contract = ContractInterface.from_dict(data)
                self.contracts[contract.name] = contract

                logger.info(f"Loaded contract interface: {contract.name}")

            except Exception as e:
                logger.warning(f"Failed to load contract from {artifact_file}: {str(e)}")

    def _save_contract_artifact(self, contract: ContractInterface):
        """Save contract interface to artifacts directory"""
        if not self.artifacts_dir:
            return

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        artifact_file = self.artifacts_dir / f"{contract.name}.json"

        with open(artifact_file, "w") as f:
            json.dump(contract.to_dict(), f, indent=2)

        logger.info(f"Saved contract artifact: {artifact_file}")

    async def deploy_contract(
        self,
        contract_name: str,
        abi: List[Dict[str, Any]],
        bytecode: str,
        constructor_args: List[Any] = None,
        gas_limit: Optional[int] = None,
        gas_price: Optional[int] = None,
    ) -> ContractInterface:
        """
        Deploy a smart contract

        Args:
            contract_name: Name of the contract
            abi: Contract ABI
            bytecode: Contract bytecode
            constructor_args: Constructor arguments
            gas_limit: Gas limit for deployment
            gas_price: Gas price for deployment

        Returns:
            Deployed contract interface
        """
        try:
            constructor_args = constructor_args or []

            # Build deployment transaction
            w3 = await self.web3_client._get_working_w3()
            contract = w3.eth.contract(abi=abi, bytecode=bytecode)

            # Build constructor transaction
            if constructor_args:
                constructor_tx = contract.constructor(*constructor_args)
            else:
                constructor_tx = contract.constructor()

            # Prepare transaction
            account_address = self.web3_client.get_account_address()
            if not account_address:
                raise Web3Error("No account available for deployment")

            tx_data = constructor_tx.build_transaction(
                {
                    "from": account_address,
                    "nonce": await self.web3_client.get_nonce(account_address),
                    "chainId": self.web3_client.network.chain_id,
                }
            )

            # Set gas parameters
            if gas_limit:
                tx_data["gas"] = gas_limit
            else:
                tx_data["gas"] = await self.web3_client.estimate_gas(tx_data)

            if self.web3_client.network.supports_eip1559:
                if not gas_price:
                    gas_data = await self.web3_client.get_gas_price()
                    tx_data["maxFeePerGas"] = gas_data["max_fee_per_gas"]
                    tx_data["maxPriorityFeePerGas"] = gas_data["max_priority_fee"]
                else:
                    tx_data["maxFeePerGas"] = gas_price
                    tx_data["maxPriorityFeePerGas"] = gas_price // 10
            else:
                tx_data["gasPrice"] = gas_price or await self.web3_client.get_gas_price()

            # Send deployment transaction
            tx_hash = await self.web3_client.send_transaction(tx_data)
            logger.info(f"Contract deployment transaction sent: {tx_hash}")

            # Wait for deployment confirmation
            tx_info = await self.web3_client.wait_for_transaction(tx_hash)

            if tx_info.status != 1:
                raise Web3Error(f"Contract deployment failed. Transaction status: {tx_info.status}")

            # Get contract address from transaction receipt
            receipt = await w3.eth.get_transaction_receipt(tx_hash)
            contract_address = receipt["contractAddress"]

            # Create contract interface
            contract_interface = ContractInterface(
                name=contract_name,
                address=contract_address,
                abi=abi,
                bytecode=bytecode,
                deployed_at=datetime.now(),
                deployer=account_address,
                network=self.web3_client.network.name,
                verified=False,
            )

            # Register and save contract
            self.contracts[contract_name] = contract_interface
            self._save_contract_artifact(contract_interface)

            logger.info(f"Contract {contract_name} deployed at {contract_address}")
            return contract_interface

        except Exception as e:
            raise Web3Error(f"Failed to deploy contract {contract_name}: {str(e)}")

    async def get_contract(self, name_or_address: str) -> Optional[ContractInterface]:
        """Get contract interface by name or address"""
        # Try by name first
        if name_or_address in self.contracts:
            return self.contracts[name_or_address]

        # Try by address
        for contract in self.contracts.values():
            if contract.address.lower() == name_or_address.lower():
                return contract

        return None

    async def call_contract_function(
        self,
        contract_name_or_address: str,
        function_name: str,
        args: List[Any] = None,
        block: str = "latest",
    ) -> Any:
        """
        Call a contract function (read-only)

        Args:
            contract_name_or_address: Contract name or address
            function_name: Function name to call
            args: Function arguments
            block: Block to call at

        Returns:
            Function return value
        """
        contract = await self.get_contract(contract_name_or_address)
        if not contract:
            raise Web3Error(f"Contract not found: {contract_name_or_address}")

        try:
            w3 = await self.web3_client._get_working_w3()
            contract_instance = w3.eth.contract(address=contract.address, abi=contract.abi)

            # Get function
            func = getattr(contract_instance.functions, function_name)

            # Call function
            if args:
                result = await func(*args).call(block_identifier=block)
            else:
                result = await func().call(block_identifier=block)

            logger.debug(f"Called {contract.name}.{function_name}() -> {result}")
            return result

        except Exception as e:
            raise Web3Error(f"Failed to call {function_name}: {str(e)}")

    async def send_contract_transaction(
        self,
        contract_name_or_address: str,
        function_name: str,
        args: List[Any] = None,
        gas_limit: Optional[int] = None,
        gas_price: Optional[int] = None,
        value: int = 0,
    ) -> str:
        """
        Send a contract transaction (state-changing)

        Args:
            contract_name_or_address: Contract name or address
            function_name: Function name to call
            args: Function arguments
            gas_limit: Gas limit for transaction
            gas_price: Gas price for transaction
            value: ETH value to send (in wei)

        Returns:
            Transaction hash
        """
        contract = await self.get_contract(contract_name_or_address)
        if not contract:
            raise Web3Error(f"Contract not found: {contract_name_or_address}")

        account_address = self.web3_client.get_account_address()
        if not account_address:
            raise Web3Error("No account available for transaction")

        try:
            w3 = await self.web3_client._get_working_w3()
            contract_instance = w3.eth.contract(address=contract.address, abi=contract.abi)

            # Get function
            func = getattr(contract_instance.functions, function_name)

            # Build transaction
            if args:
                tx_data = func(*args).build_transaction(
                    {
                        "from": account_address,
                        "value": value,
                        "nonce": await self.web3_client.get_nonce(account_address),
                        "chainId": self.web3_client.network.chain_id,
                    }
                )
            else:
                tx_data = func().build_transaction(
                    {
                        "from": account_address,
                        "value": value,
                        "nonce": await self.web3_client.get_nonce(account_address),
                        "chainId": self.web3_client.network.chain_id,
                    }
                )

            # Set gas parameters
            if gas_limit:
                tx_data["gas"] = gas_limit
            else:
                tx_data["gas"] = await self.web3_client.estimate_gas(tx_data)

            # Send transaction
            tx_hash = await self.web3_client.send_transaction(tx_data)

            logger.info(f"Sent transaction to {contract.name}.{function_name}(): {tx_hash}")
            return tx_hash

        except Exception as e:
            raise Web3Error(f"Failed to send transaction to {function_name}: {str(e)}")

    async def get_contract_events(
        self,
        contract_name_or_address: str,
        event_name: str,
        from_block: Union[int, str] = "earliest",
        to_block: Union[int, str] = "latest",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get contract events

        Args:
            contract_name_or_address: Contract name or address
            event_name: Event name to filter
            from_block: Starting block
            to_block: Ending block
            filters: Event filters

        Returns:
            List of event logs
        """
        contract = await self.get_contract(contract_name_or_address)
        if not contract:
            raise Web3Error(f"Contract not found: {contract_name_or_address}")

        try:
            w3 = await self.web3_client._get_working_w3()
            contract_instance = w3.eth.contract(address=contract.address, abi=contract.abi)

            # Get event
            event = getattr(contract_instance.events, event_name)

            # Create event filter
            event_filter = event.create_filter(
                fromBlock=from_block, toBlock=to_block, argument_filters=filters or {}
            )

            # Get events
            events = await event_filter.get_all_entries()

            # Convert to dictionaries
            result = []
            for event in events:
                result.append(
                    {
                        "event": event.event,
                        "args": dict(event.args),
                        "blockNumber": event.blockNumber,
                        "transactionHash": event.transactionHash.hex(),
                        "address": event.address,
                        "topics": [topic.hex() for topic in event.topics],
                    }
                )

            logger.info(f"Retrieved {len(result)} {event_name} events from {contract.name}")
            return result

        except Exception as e:
            raise Web3Error(f"Failed to get events {event_name}: {str(e)}")

    async def batch_call(self, calls: List[Tuple[str, str, List[Any]]]) -> List[Any]:
        """
        Execute multiple contract calls in batch

        Args:
            calls: List of (contract_name_or_address, function_name, args) tuples

        Returns:
            List of results in same order as calls
        """
        tasks = []

        for contract_id, function_name, args in calls:
            task = self.call_contract_function(contract_id, function_name, args)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to None or re-raise based on preference
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Batch call {i} failed: {str(result)}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results

    async def estimate_contract_gas(
        self,
        contract_name_or_address: str,
        function_name: str,
        args: List[Any] = None,
        value: int = 0,
    ) -> int:
        """
        Estimate gas for contract function call

        Args:
            contract_name_or_address: Contract name or address
            function_name: Function name
            args: Function arguments
            value: ETH value to send

        Returns:
            Estimated gas amount
        """
        contract = await self.get_contract(contract_name_or_address)
        if not contract:
            raise Web3Error(f"Contract not found: {contract_name_or_address}")

        account_address = self.web3_client.get_account_address()
        if not account_address:
            raise Web3Error("No account available for estimation")

        try:
            w3 = await self.web3_client._get_working_w3()
            contract_instance = w3.eth.contract(address=contract.address, abi=contract.abi)

            # Get function
            func = getattr(contract_instance.functions, function_name)

            # Build transaction for estimation
            if args:
                tx_data = func(*args).build_transaction({"from": account_address, "value": value})
            else:
                tx_data = func().build_transaction({"from": account_address, "value": value})

            # Estimate gas
            gas_estimate = await self.web3_client.estimate_gas(tx_data)

            logger.debug(f"Gas estimate for {contract.name}.{function_name}(): {gas_estimate}")
            return gas_estimate

        except Exception as e:
            raise Web3Error(f"Failed to estimate gas for {function_name}: {str(e)}")

    def list_contracts(self) -> List[ContractInterface]:
        """List all registered contracts"""
        return list(self.contracts.values())

    def remove_contract(self, name: str) -> bool:
        """Remove contract from registry"""
        if name in self.contracts:
            del self.contracts[name]

            # Remove artifact file if it exists
            if self.artifacts_dir:
                artifact_file = self.artifacts_dir / f"{name}.json"
                if artifact_file.exists():
                    artifact_file.unlink()

            logger.info(f"Removed contract: {name}")
            return True

        return False

    async def verify_contract(
        self,
        contract_name: str,
        source_code: str,
        compiler_version: str,
        optimization: bool = True,
        runs: int = 200,
    ) -> bool:
        """
        Verify contract on block explorer (placeholder implementation)

        This is a placeholder for contract verification functionality.
        In a real implementation, this would interact with block explorer APIs
        like Etherscan, Polygonscan, etc.
        """
        contract = await self.get_contract(contract_name)
        if not contract:
            raise Web3Error(f"Contract not found: {contract_name}")

        # Placeholder implementation
        logger.warning("Contract verification not implemented yet")
        return False
