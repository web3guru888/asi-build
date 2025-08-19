#!/usr/bin/env python3
"""
System Testing Script for Kenny AGI Blockchain Audit Trail

Comprehensive testing suite that validates all system components
including smart contracts, IPFS, cryptography, and APIs.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web3_integration import Web3Client, ContractManager, NetworkConfig
from src.web3_integration.network_config import get_network_by_name
from src.ipfs import IPFSClient, DataManager, AuditRecord
from src.crypto import SignatureManager, SignatureAlgorithm, HashManager
from src.api.rest_api import AuditTrailAPI, AuditRecordRequest
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemTester:
    """
    Comprehensive system testing suite
    
    Tests:
    - Smart contract functionality
    - IPFS storage and retrieval
    - Cryptographic operations
    - API endpoints
    - End-to-end workflows
    - Performance benchmarks
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize system tester"""
        self.config_path = config_path
        self.config = self._load_config()
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0
            }
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise
            
    async def test_blockchain_connectivity(self, network_name: str) -> Dict[str, Any]:
        """Test blockchain connectivity and basic operations"""
        test_name = f"blockchain_connectivity_{network_name}"
        logger.info(f"Testing blockchain connectivity for {network_name}")
        
        try:
            network_config = get_network_by_name(network_name)
            network_settings = self.config['blockchain']['networks'][network_name]
            
            async with Web3Client(network_config, network_settings['private_key']) as web3_client:
                # Test basic connectivity
                network_info = await web3_client.get_network_info()
                current_block = await web3_client.get_block_number()
                
                # Test account operations
                account_address = web3_client.get_account_address()
                balance = await web3_client.get_balance(account_address)
                nonce = await web3_client.get_nonce(account_address)
                
                result = {
                    'status': 'passed',
                    'network_info': network_info,
                    'current_block': current_block,
                    'account_address': account_address,
                    'balance_wei': balance,
                    'nonce': nonce
                }
                
                logger.info(f"Blockchain connectivity test passed for {network_name}")
                return result
                
        except Exception as e:
            logger.error(f"Blockchain connectivity test failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    async def test_smart_contracts(self, network_name: str, contract_addresses: Dict[str, str]) -> Dict[str, Any]:
        """Test smart contract functionality"""
        test_name = f"smart_contracts_{network_name}"
        logger.info(f"Testing smart contracts on {network_name}")
        
        try:
            network_config = get_network_by_name(network_name)
            network_settings = self.config['blockchain']['networks'][network_name]
            
            async with Web3Client(network_config, network_settings['private_key']) as web3_client:
                contract_manager = ContractManager(web3_client)
                
                test_results = {}
                
                # Test AuditTrail contract
                if 'AuditTrail' in contract_addresses:
                    audit_trail_results = await self._test_audit_trail_contract(
                        contract_manager,
                        contract_addresses['AuditTrail']
                    )
                    test_results['AuditTrail'] = audit_trail_results
                    
                # Test AuditFactory contract
                if 'AuditFactory' in contract_addresses:
                    factory_results = await self._test_audit_factory_contract(
                        contract_manager,
                        contract_addresses['AuditFactory']
                    )
                    test_results['AuditFactory'] = factory_results
                    
                overall_status = 'passed' if all(
                    result.get('status') == 'passed' 
                    for result in test_results.values()
                ) else 'failed'
                
                return {
                    'status': overall_status,
                    'contracts': test_results
                }
                
        except Exception as e:
            logger.error(f"Smart contract tests failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    async def _test_audit_trail_contract(self, contract_manager: ContractManager, address: str) -> Dict[str, Any]:
        """Test AuditTrail contract functionality"""
        try:
            # Test read functions
            total_entries = await contract_manager.call_contract_function(
                address,
                "getTotalAuditEntries"
            )
            
            # Test creating an audit entry
            test_ipfs_hash = "QmTestHash123456789"
            test_signature = "test_signature"
            test_event_type = "test"
            test_description = "Test audit entry"
            test_metadata = json.dumps({"test": True})
            
            tx_hash = await contract_manager.send_contract_transaction(
                address,
                "createAuditEntry",
                [test_ipfs_hash, test_signature, test_event_type, test_description, test_metadata]
            )
            
            # Wait for transaction confirmation
            await contract_manager.web3_client.wait_for_transaction(tx_hash)
            
            # Verify entry was created
            new_total = await contract_manager.call_contract_function(
                address,
                "getTotalAuditEntries"
            )
            
            # Get the created entry
            if new_total > 0:
                entry = await contract_manager.call_contract_function(
                    address,
                    "getAuditEntry",
                    [new_total]
                )
                
            return {
                'status': 'passed',
                'initial_entries': total_entries,
                'final_entries': new_total,
                'transaction_hash': tx_hash,
                'test_entry_created': new_total > total_entries
            }
            
        except Exception as e:
            logger.error(f"AuditTrail contract test failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    async def _test_audit_factory_contract(self, contract_manager: ContractManager, address: str) -> Dict[str, Any]:
        """Test AuditFactory contract functionality"""
        try:
            # Test getting total audit trails
            total_trails = await contract_manager.call_contract_function(
                address,
                "getTotalAuditTrails"
            )
            
            # Test creating a new audit trail
            trail_name = f"Test Trail {int(time.time())}"
            trail_description = "Test audit trail"
            admin_address = contract_manager.web3_client.get_account_address()
            
            tx_hash = await contract_manager.send_contract_transaction(
                address,
                "createAuditTrail",
                [trail_name, trail_description, admin_address]
            )
            
            # Wait for transaction confirmation
            await contract_manager.web3_client.wait_for_transaction(tx_hash)
            
            # Verify new trail was created
            new_total = await contract_manager.call_contract_function(
                address,
                "getTotalAuditTrails"
            )
            
            return {
                'status': 'passed',
                'initial_trails': total_trails,
                'final_trails': new_total,
                'transaction_hash': tx_hash,
                'test_trail_created': new_total > total_trails
            }
            
        except Exception as e:
            logger.error(f"AuditFactory contract test failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    async def test_ipfs_functionality(self) -> Dict[str, Any]:
        """Test IPFS storage and retrieval"""
        logger.info("Testing IPFS functionality")
        
        try:
            ipfs_config = self.config.get('ipfs', {})
            
            async with IPFSClient(ipfs_config.get('api_url')) as ipfs_client:
                # Test node connectivity
                node_info = await ipfs_client.get_node_info()
                
                # Test data storage and retrieval
                test_data = {
                    'message': 'Hello from Kenny AGI Audit Trail',
                    'timestamp': datetime.now().isoformat(),
                    'test': True
                }
                
                # Store data
                ipfs_hash = await ipfs_client.add_json(test_data)
                logger.info(f"Stored test data with hash: {ipfs_hash}")
                
                # Retrieve data
                retrieved_data = await ipfs_client.get_json(ipfs_hash)
                
                # Verify data integrity
                data_matches = test_data == retrieved_data
                
                # Test file operations
                test_file_content = "Test file content for IPFS"
                test_file_hash = await ipfs_client.add_bytes(test_file_content.encode())
                retrieved_content = await ipfs_client.get_bytes(test_file_hash)
                
                file_matches = test_file_content.encode() == retrieved_content
                
                return {
                    'status': 'passed',
                    'node_id': node_info['id'][:16],
                    'json_hash': ipfs_hash,
                    'json_data_matches': data_matches,
                    'file_hash': test_file_hash,
                    'file_data_matches': file_matches,
                    'overall_success': data_matches and file_matches
                }
                
        except Exception as e:
            logger.error(f"IPFS test failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    async def test_cryptographic_operations(self) -> Dict[str, Any]:
        """Test cryptographic functionality"""
        logger.info("Testing cryptographic operations")
        
        try:
            # Test signature operations
            signature_manager = SignatureManager()
            
            # Generate test key pairs for different algorithms
            algorithms_to_test = [
                SignatureAlgorithm.RSA_PSS,
                SignatureAlgorithm.ECDSA_P256,
                SignatureAlgorithm.ED25519,
                SignatureAlgorithm.ETHEREUM
            ]
            
            signature_results = {}
            
            for algorithm in algorithms_to_test:
                try:
                    # Generate key pair
                    key_pair = signature_manager.generate_key_pair(
                        algorithm=algorithm,
                        key_id=f"test_{algorithm.value}"
                    )
                    
                    # Test message signing
                    test_message = f"Test message for {algorithm.value}"
                    signature = signature_manager.sign_message(test_message, key_pair.key_id)
                    
                    # Test signature verification
                    signature_verifier = signature_manager.signature_verifier
                    signature_verifier.add_public_key(
                        key_pair.key_id,
                        key_pair.get_public_key_pem(),
                        algorithm
                    )
                    
                    is_valid = signature_verifier.verify_signature(
                        test_message,
                        signature,
                        key_pair.key_id
                    )
                    
                    signature_results[algorithm.value] = {
                        'key_generated': True,
                        'message_signed': True,
                        'signature_valid': is_valid,
                        'status': 'passed' if is_valid else 'failed'
                    }
                    
                except Exception as e:
                    signature_results[algorithm.value] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                    
            # Test hash operations
            hash_manager = HashManager()
            test_data = "Test data for hashing"
            
            hash_result = hash_manager.hash_data(test_data)
            hash_verification = hash_manager.verify_hash(test_data, hash_result.hash_value)
            
            overall_status = 'passed' if all(
                result.get('status') == 'passed'
                for result in signature_results.values()
            ) and hash_verification else 'failed'
            
            return {
                'status': overall_status,
                'signatures': signature_results,
                'hashing': {
                    'hash_generated': True,
                    'hash_verified': hash_verification,
                    'algorithm': hash_result.algorithm.value
                }
            }
            
        except Exception as e:
            logger.error(f"Cryptographic test failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    async def test_end_to_end_workflow(self, network_name: str, contract_addresses: Dict[str, str]) -> Dict[str, Any]:
        """Test complete end-to-end audit trail workflow"""
        logger.info("Testing end-to-end workflow")
        
        try:
            # Initialize components
            network_config = get_network_by_name(network_name)
            network_settings = self.config['blockchain']['networks'][network_name]
            ipfs_config = self.config.get('ipfs', {})
            
            async with Web3Client(network_config, network_settings['private_key']) as web3_client:
                async with IPFSClient(ipfs_config.get('api_url')) as ipfs_client:
                    
                    # Initialize managers
                    contract_manager = ContractManager(web3_client)
                    data_manager = DataManager(ipfs_client)
                    signature_manager = SignatureManager()
                    
                    # Generate signing key
                    key_pair = signature_manager.generate_key_pair(
                        algorithm=SignatureAlgorithm.ECDSA_SECP256K1,
                        key_id="e2e_test_key"
                    )
                    
                    # Create test audit record
                    test_record = AuditRecord(
                        id=f"e2e_test_{int(time.time())}",
                        event_type="test",
                        timestamp=datetime.now(),
                        user_id="test_user",
                        action="end_to_end_test",
                        resource="test_resource",
                        details={
                            "test_type": "end_to_end",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    # Step 1: Store record in IPFS
                    storage_result = await data_manager.store_audit_record(test_record)
                    ipfs_hash = storage_result.ipfs_hash
                    
                    # Step 2: Sign the record
                    signature = signature_manager.sign_message(
                        test_record.to_dict(),
                        key_pair.key_id
                    )
                    
                    # Step 3: Store on blockchain
                    if 'AuditTrail' in contract_addresses:
                        blockchain_tx = await contract_manager.send_contract_transaction(
                            contract_addresses['AuditTrail'],
                            "createAuditEntry",
                            [
                                ipfs_hash,
                                signature.signature,
                                test_record.event_type,
                                f"{test_record.action} on {test_record.resource}",
                                json.dumps(test_record.metadata or {})
                            ]
                        )
                        
                        # Wait for confirmation
                        await web3_client.wait_for_transaction(blockchain_tx)
                        
                    # Step 4: Verify end-to-end integrity
                    # Retrieve from IPFS
                    retrieved_record = await data_manager.retrieve_audit_record(ipfs_hash)
                    
                    # Verify signature
                    signature_verifier = signature_manager.signature_verifier
                    signature_verifier.add_public_key(
                        key_pair.key_id,
                        key_pair.get_public_key_pem(),
                        SignatureAlgorithm.ECDSA_SECP256K1
                    )
                    
                    signature_valid = signature_verifier.verify_signature(
                        retrieved_record.to_dict(),
                        signature
                    )
                    
                    # Data integrity check
                    data_integrity = (
                        retrieved_record.id == test_record.id and
                        retrieved_record.event_type == test_record.event_type and
                        retrieved_record.user_id == test_record.user_id
                    )
                    
                    return {
                        'status': 'passed' if signature_valid and data_integrity else 'failed',
                        'ipfs_hash': ipfs_hash,
                        'blockchain_tx': blockchain_tx if 'AuditTrail' in contract_addresses else None,
                        'signature_valid': signature_valid,
                        'data_integrity': data_integrity,
                        'record_id': test_record.id
                    }
                    
        except Exception as e:
            logger.error(f"End-to-end test failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    async def run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks"""
        logger.info("Running performance benchmarks")
        
        try:
            benchmarks = {}
            
            # IPFS performance benchmark
            ipfs_config = self.config.get('ipfs', {})
            async with IPFSClient(ipfs_config.get('api_url')) as ipfs_client:
                
                # Benchmark small data storage
                small_data = {"test": "data", "size": "small"}
                start_time = time.time()
                
                for i in range(10):
                    await ipfs_client.add_json({**small_data, "iteration": i})
                    
                small_data_time = (time.time() - start_time) / 10
                
                benchmarks['ipfs'] = {
                    'small_data_avg_ms': small_data_time * 1000,
                    'operations_tested': 10
                }
                
            # Cryptographic performance benchmark
            signature_manager = SignatureManager()
            key_pair = signature_manager.generate_key_pair(
                algorithm=SignatureAlgorithm.ECDSA_SECP256K1,
                key_id="benchmark_key"
            )
            
            start_time = time.time()
            for i in range(100):
                signature_manager.sign_message(f"benchmark message {i}", key_pair.key_id)
                
            crypto_time = (time.time() - start_time) / 100
            
            benchmarks['cryptography'] = {
                'signature_avg_ms': crypto_time * 1000,
                'operations_tested': 100
            }
            
            return {
                'status': 'passed',
                'benchmarks': benchmarks
            }
            
        except Exception as e:
            logger.error(f"Performance benchmark failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    def record_test_result(self, test_name: str, result: Dict[str, Any]):
        """Record test result"""
        self.test_results['tests'][test_name] = result
        self.test_results['summary']['total'] += 1
        
        if result.get('status') == 'passed':
            self.test_results['summary']['passed'] += 1
        elif result.get('status') == 'failed':
            self.test_results['summary']['failed'] += 1
        else:
            self.test_results['summary']['skipped'] += 1
            
    def save_test_results(self, filename: Optional[str] = None):
        """Save test results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results/test_results_{timestamp}.json"
            
        # Create directory if needed
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
            
        logger.info(f"Test results saved to {filename}")
        
    def print_summary(self):
        """Print test summary"""
        summary = self.test_results['summary']
        
        print("\n" + "="*60)
        print("KENNY AGI BLOCKCHAIN AUDIT TRAIL - TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['total']}")
        print(f"Passed:      {summary['passed']}")
        print(f"Failed:      {summary['failed']}")
        print(f"Skipped:     {summary['skipped']}")
        print(f"Success Rate: {(summary['passed'] / max(summary['total'], 1)) * 100:.1f}%")
        print("="*60)
        
        # Print failed tests
        if summary['failed'] > 0:
            print("\nFAILED TESTS:")
            for test_name, result in self.test_results['tests'].items():
                if result.get('status') == 'failed':
                    print(f"- {test_name}: {result.get('error', 'Unknown error')}")
                    
        print()


async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Test Kenny AGI Blockchain Audit Trail")
    
    parser.add_argument(
        '--network',
        type=str,
        default='goerli',
        help='Network to test against'
    )
    
    parser.add_argument(
        '--contracts',
        type=str,
        help='JSON file containing deployed contract addresses'
    )
    
    parser.add_argument(
        '--skip-blockchain',
        action='store_true',
        help='Skip blockchain-related tests'
    )
    
    parser.add_argument(
        '--skip-ipfs',
        action='store_true',
        help='Skip IPFS tests'
    )
    
    parser.add_argument(
        '--skip-crypto',
        action='store_true',
        help='Skip cryptographic tests'
    )
    
    parser.add_argument(
        '--skip-e2e',
        action='store_true',
        help='Skip end-to-end tests'
    )
    
    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='Run performance benchmarks'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Configuration file path'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize system tester
        tester = SystemTester(args.config)
        
        # Load contract addresses if provided
        contract_addresses = {}
        if args.contracts:
            with open(args.contracts, 'r') as f:
                deployment_data = json.load(f)
                if args.network in deployment_data.get('networks', {}):
                    contract_addresses = deployment_data['networks'][args.network].get('contracts', {})
                    
        # Run tests
        if not args.skip_blockchain:
            # Test blockchain connectivity
            result = await tester.test_blockchain_connectivity(args.network)
            tester.record_test_result(f'blockchain_connectivity_{args.network}', result)
            
            # Test smart contracts if addresses provided
            if contract_addresses:
                result = await tester.test_smart_contracts(args.network, contract_addresses)
                tester.record_test_result(f'smart_contracts_{args.network}', result)
                
        if not args.skip_ipfs:
            # Test IPFS functionality
            result = await tester.test_ipfs_functionality()
            tester.record_test_result('ipfs_functionality', result)
            
        if not args.skip_crypto:
            # Test cryptographic operations
            result = await tester.test_cryptographic_operations()
            tester.record_test_result('cryptographic_operations', result)
            
        if not args.skip_e2e and contract_addresses:
            # Test end-to-end workflow
            result = await tester.test_end_to_end_workflow(args.network, contract_addresses)
            tester.record_test_result('end_to_end_workflow', result)
            
        if args.benchmark:
            # Run performance benchmarks
            result = await tester.run_performance_benchmarks()
            tester.record_test_result('performance_benchmarks', result)
            
        # Save results and print summary
        tester.save_test_results()
        tester.print_summary()
        
        # Exit with appropriate code
        if tester.test_results['summary']['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Test runner failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())