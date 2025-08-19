#!/usr/bin/env python3
"""
Deployment Script for Kenny AGI Blockchain Audit Trail

Handles smart contract deployment, system initialization,
and environment setup for different networks.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web3_integration import Web3Client, ContractManager, NetworkConfig
from src.web3_integration.network_config import get_network_by_name, NAMED_NETWORKS
from src.ipfs import IPFSClient
from src.crypto import SignatureManager, HashManager
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeploymentManager:
    """
    Comprehensive deployment manager for the audit trail system
    
    Handles:
    - Smart contract compilation and deployment
    - Network configuration
    - System initialization
    - Verification and testing
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize deployment manager"""
        self.config_path = config_path
        self.config = self._load_config()
        self.deployment_record = {
            'timestamp': datetime.now().isoformat(),
            'networks': {},
            'contracts': {},
            'status': 'pending'
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Substitute environment variables
            config = self._substitute_env_vars(config)
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise
            
    def _substitute_env_vars(self, data: Any) -> Any:
        """Recursively substitute environment variables in config"""
        if isinstance(data, dict):
            return {key: self._substitute_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith('${') and data.endswith('}'):
            # Extract variable name and default value
            var_expr = data[2:-1]  # Remove ${ and }
            if ':-' in var_expr:
                var_name, default_value = var_expr.split(':-', 1)
                return os.getenv(var_name, default_value)
            else:
                return os.getenv(var_expr, data)
        else:
            return data
            
    async def deploy_to_network(
        self,
        network_name: str,
        contracts: Optional[List[str]] = None,
        verify_contracts: bool = False
    ) -> Dict[str, Any]:
        """
        Deploy contracts to specified network
        
        Args:
            network_name: Name of the network to deploy to
            contracts: List of contract names to deploy (all if None)
            verify_contracts: Whether to verify contracts on block explorer
            
        Returns:
            Deployment results
        """
        logger.info(f"Starting deployment to {network_name}")
        
        try:
            # Get network configuration
            network_config = get_network_by_name(network_name)
            if not network_config:
                raise ValueError(f"Unknown network: {network_name}")
                
            # Get blockchain config from YAML
            blockchain_config = self.config.get('blockchain', {})
            network_settings = blockchain_config.get('networks', {}).get(network_name, {})
            
            if not network_settings:
                raise ValueError(f"No configuration found for network: {network_name}")
                
            # Initialize Web3 client
            private_key = network_settings.get('private_key')
            if not private_key:
                raise ValueError(f"No private key configured for network: {network_name}")
                
            async with Web3Client(network_config, private_key) as web3_client:
                # Initialize contract manager
                contract_manager = ContractManager(
                    web3_client,
                    contracts_dir="contracts",
                    artifacts_dir="artifacts"
                )
                
                # Deploy contracts
                deployment_results = {}
                
                # Load contract artifacts
                contract_configs = blockchain_config.get('contracts', {})
                contracts_to_deploy = contracts or list(contract_configs.keys())
                
                for contract_name in contracts_to_deploy:
                    if contract_name not in contract_configs:
                        logger.warning(f"No configuration for contract: {contract_name}")
                        continue
                        
                    contract_config = contract_configs[contract_name]
                    deploy_networks = contract_config.get('deploy_on_networks', [])
                    
                    if network_name not in deploy_networks and deploy_networks:
                        logger.info(f"Skipping {contract_name} (not configured for {network_name})")
                        continue
                        
                    logger.info(f"Deploying {contract_name}...")
                    
                    # Load contract ABI and bytecode
                    abi, bytecode = await self._load_contract_artifacts(contract_name)
                    
                    # Deploy contract
                    constructor_args = contract_config.get('constructor_args', [])
                    
                    # For AuditFactory, pass admin address as constructor arg
                    if contract_name == 'AuditFactory' and not constructor_args:
                        admin_address = web3_client.get_account_address()
                        constructor_args = [admin_address]
                        
                    contract_interface = await contract_manager.deploy_contract(
                        contract_name,
                        abi,
                        bytecode,
                        constructor_args,
                        gas_limit=network_settings.get('gas_limit'),
                        gas_price=network_settings.get('gas_price_gwei')
                    )
                    
                    deployment_results[contract_name] = {
                        'address': contract_interface.address,
                        'deployer': contract_interface.deployer,
                        'deployed_at': contract_interface.deployed_at.isoformat(),
                        'network': network_name,
                        'verified': False
                    }
                    
                    logger.info(f"Deployed {contract_name} at {contract_interface.address}")
                    
                    # Verify contract if requested
                    if verify_contracts:
                        try:
                            # This would integrate with block explorer APIs
                            logger.info(f"Contract verification not implemented yet for {contract_name}")
                        except Exception as e:
                            logger.warning(f"Failed to verify {contract_name}: {str(e)}")
                            
                # Record deployment
                self.deployment_record['networks'][network_name] = {
                    'chain_id': network_config.chain_id,
                    'contracts': deployment_results,
                    'deployed_at': datetime.now().isoformat(),
                    'status': 'success'
                }
                
                logger.info(f"Deployment to {network_name} completed successfully")
                return deployment_results
                
        except Exception as e:
            logger.error(f"Deployment to {network_name} failed: {str(e)}")
            self.deployment_record['networks'][network_name] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
            raise
            
    async def _load_contract_artifacts(self, contract_name: str) -> tuple[List[Dict], str]:
        """Load contract ABI and bytecode from compilation artifacts"""
        try:
            # Try to load from Hardhat artifacts first
            artifact_path = Path(f"contracts/artifacts/contracts/{contract_name}.sol/{contract_name}.json")
            
            if artifact_path.exists():
                with open(artifact_path, 'r') as f:
                    artifact = json.load(f)
                return artifact['abi'], artifact['bytecode']
                
            # Try alternative paths
            alternative_paths = [
                Path(f"artifacts/contracts/{contract_name}.json"),
                Path(f"build/contracts/{contract_name}.json"),
                Path(f"contracts/build/{contract_name}.json")
            ]
            
            for path in alternative_paths:
                if path.exists():
                    with open(path, 'r') as f:
                        artifact = json.load(f)
                    return artifact.get('abi', []), artifact.get('bytecode', '')
                    
            raise FileNotFoundError(f"No artifacts found for contract: {contract_name}")
            
        except Exception as e:
            logger.error(f"Failed to load artifacts for {contract_name}: {str(e)}")
            raise
            
    async def compile_contracts(self) -> bool:
        """Compile smart contracts using Hardhat"""
        try:
            logger.info("Compiling smart contracts...")
            
            # Check if hardhat is available
            import subprocess
            
            # Change to contracts directory
            contracts_dir = Path("contracts")
            if not contracts_dir.exists():
                raise FileNotFoundError("Contracts directory not found")
                
            # Run hardhat compile
            result = subprocess.run(
                ["npx", "hardhat", "compile"],
                cwd=contracts_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Contract compilation successful")
                return True
            else:
                logger.error(f"Contract compilation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to compile contracts: {str(e)}")
            return False
            
    async def test_deployment(self, network_name: str) -> Dict[str, Any]:
        """Test deployed contracts"""
        logger.info(f"Testing deployment on {network_name}")
        
        try:
            network_config = get_network_by_name(network_name)
            network_settings = self.config['blockchain']['networks'][network_name]
            
            async with Web3Client(network_config, network_settings['private_key']) as web3_client:
                contract_manager = ContractManager(web3_client)
                
                test_results = {}
                
                # Test AuditTrail contract if deployed
                if network_name in self.deployment_record['networks']:
                    contracts = self.deployment_record['networks'][network_name].get('contracts', {})
                    
                    if 'AuditTrail' in contracts:
                        audit_trail_address = contracts['AuditTrail']['address']
                        
                        # Test basic functionality
                        try:
                            # Get total audit entries (should be 0 for new deployment)
                            total_entries = await contract_manager.call_contract_function(
                                audit_trail_address,
                                "getTotalAuditEntries"
                            )
                            
                            test_results['AuditTrail'] = {
                                'address': audit_trail_address,
                                'total_entries': total_entries,
                                'status': 'working'
                            }
                            
                            logger.info(f"AuditTrail test passed: {total_entries} entries")
                            
                        except Exception as e:
                            test_results['AuditTrail'] = {
                                'address': audit_trail_address,
                                'status': 'failed',
                                'error': str(e)
                            }
                            logger.error(f"AuditTrail test failed: {str(e)}")
                            
                return test_results
                
        except Exception as e:
            logger.error(f"Deployment test failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
            
    async def setup_system(self, network_name: str) -> Dict[str, Any]:
        """Initialize system components after deployment"""
        logger.info(f"Setting up system for {network_name}")
        
        try:
            # Initialize IPFS client
            ipfs_config = self.config.get('ipfs', {})
            async with IPFSClient(ipfs_config.get('api_url')) as ipfs_client:
                # Test IPFS connection
                node_info = await ipfs_client.get_node_info()
                logger.info(f"IPFS node connected: {node_info['id'][:16]}...")
                
            # Initialize cryptographic components
            signature_manager = SignatureManager()
            hash_manager = HashManager()
            
            # Generate default signing key if needed
            if not signature_manager.key_pairs:
                key_pair = signature_manager.generate_key_pair(
                    algorithm=signature_manager.SignatureAlgorithm.ECDSA_SECP256K1,
                    key_id="default"
                )
                logger.info(f"Generated default signing key: {key_pair.key_id}")
                
            setup_results = {
                'network': network_name,
                'ipfs_connected': True,
                'crypto_initialized': True,
                'default_key_generated': True,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("System setup completed successfully")
            return setup_results
            
        except Exception as e:
            logger.error(f"System setup failed: {str(e)}")
            raise
            
    def save_deployment_record(self, filename: Optional[str] = None):
        """Save deployment record to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"deployments/deployment_{timestamp}.json"
            
        # Create directory if needed
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(self.deployment_record, f, indent=2)
            
        logger.info(f"Deployment record saved to {filename}")
        
    def load_deployment_record(self, filename: str):
        """Load deployment record from file"""
        with open(filename, 'r') as f:
            self.deployment_record = json.load(f)
            
        logger.info(f"Deployment record loaded from {filename}")


async def main():
    """Main deployment script"""
    parser = argparse.ArgumentParser(description="Deploy Kenny AGI Blockchain Audit Trail")
    
    parser.add_argument(
        '--network',
        type=str,
        required=True,
        choices=list(NAMED_NETWORKS.keys()),
        help='Network to deploy to'
    )
    
    parser.add_argument(
        '--contracts',
        type=str,
        nargs='*',
        help='Specific contracts to deploy (default: all)'
    )
    
    parser.add_argument(
        '--compile',
        action='store_true',
        help='Compile contracts before deployment'
    )
    
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify contracts on block explorer'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test deployment after completion'
    )
    
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Initialize system components'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Configuration file path'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize deployment manager
        deployment_manager = DeploymentManager(args.config)
        
        # Compile contracts if requested
        if args.compile:
            success = await deployment_manager.compile_contracts()
            if not success:
                logger.error("Contract compilation failed")
                sys.exit(1)
                
        # Deploy contracts
        logger.info(f"Deploying to {args.network}...")
        deployment_results = await deployment_manager.deploy_to_network(
            args.network,
            contracts=args.contracts,
            verify_contracts=args.verify
        )
        
        # Test deployment if requested
        if args.test:
            test_results = await deployment_manager.test_deployment(args.network)
            logger.info(f"Test results: {test_results}")
            
        # Setup system if requested
        if args.setup:
            setup_results = await deployment_manager.setup_system(args.network)
            logger.info(f"Setup results: {setup_results}")
            
        # Save deployment record
        deployment_manager.save_deployment_record()
        
        logger.info("Deployment completed successfully!")
        print(f"Deployment results: {json.dumps(deployment_results, indent=2)}")
        
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())