"""
Comprehensive tests for the Federated Learning Orchestrator
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
import torch
import numpy as np

from ..core.federated_orchestrator import (
    FederatedOrchestrator, NodeInfo, TrainingRound, ModelUpdate
)

@pytest.fixture
def orchestrator_config():
    """Basic orchestrator configuration for testing"""
    return {
        'max_nodes': 100,
        'min_nodes_per_round': 3,
        'max_nodes_per_round': 10,
        'round_duration': 60,
        'heartbeat_interval': 10
    }

@pytest.fixture
def orchestrator(orchestrator_config):
    """Create orchestrator instance for testing"""
    return FederatedOrchestrator(orchestrator_config)

@pytest.fixture
def sample_node_info():
    """Sample node information for testing"""
    return {
        'ip_address': '127.0.0.1',
        'port': 8080,
        'capabilities': {'gpu': True, 'memory_gb': 16},
        'compute_power': 2.5,
        'stake_amount': 1000.0
    }

class TestFederatedOrchestrator:
    """Test cases for FederatedOrchestrator"""
    
    @pytest.mark.asyncio
    async def test_node_registration(self, orchestrator, sample_node_info):
        """Test node registration process"""
        
        result = await orchestrator.register_node(sample_node_info)
        
        assert result['status'] == 'registered'
        assert 'node_id' in result
        assert result['node_id'] in orchestrator.node_registry
        
        node = orchestrator.node_registry[result['node_id']]
        assert node.ip_address == sample_node_info['ip_address']
        assert node.port == sample_node_info['port']
        assert node.status == 'active'
    
    @pytest.mark.asyncio
    async def test_node_unregistration(self, orchestrator, sample_node_info):
        """Test node unregistration process"""
        
        # Register first
        reg_result = await orchestrator.register_node(sample_node_info)
        node_id = reg_result['node_id']
        
        # Then unregister
        unreg_result = await orchestrator.unregister_node(node_id)
        
        assert unreg_result['status'] == 'unregistered'
        assert node_id not in orchestrator.node_registry
    
    @pytest.mark.asyncio
    async def test_heartbeat_processing(self, orchestrator, sample_node_info):
        """Test heartbeat processing"""
        
        # Register node first
        reg_result = await orchestrator.register_node(sample_node_info)
        node_id = reg_result['node_id']
        
        # Send heartbeat
        status_info = {'compute_power': 3.0, 'capabilities': {'gpu': True}}
        hb_result = await orchestrator.heartbeat(node_id, status_info)
        
        assert hb_result['status'] == 'acknowledged'
        assert 'next_heartbeat' in hb_result
        
        # Check node was updated
        node = orchestrator.node_registry[node_id]
        assert node.compute_power == 3.0
    
    @pytest.mark.asyncio
    async def test_heartbeat_unknown_node(self, orchestrator):
        """Test heartbeat from unknown node"""
        
        result = await orchestrator.heartbeat('unknown_node', {})
        assert result['status'] == 'not_registered'
    
    @pytest.mark.asyncio
    async def test_model_update_submission(self, orchestrator, sample_node_info):
        """Test model update submission"""
        
        # Register node
        reg_result = await orchestrator.register_node(sample_node_info)
        node_id = reg_result['node_id']
        
        # Create a mock training round
        round_id = 'test_round'
        orchestrator.active_rounds[round_id] = TrainingRound(
            round_id=round_id,
            global_model_hash='test_hash',
            participants=[node_id],
            start_time=time.time(),
            deadline=time.time() + 300,
            min_participants=1,
            max_participants=10,
            status='active'
        )
        
        # Submit model update
        update_data = {
            'node_id': node_id,
            'round_id': round_id,
            'model_diff': b'fake_model_diff',
            'data_size': 1000,
            'compute_proof': 'proof',
            'signature': 'signature'
        }
        
        result = await orchestrator.submit_model_update(update_data)
        
        assert result['status'] == 'accepted'
        assert 'update_id' in result
        assert len(orchestrator.model_updates[round_id]) == 1
    
    @pytest.mark.asyncio
    async def test_model_update_invalid_round(self, orchestrator, sample_node_info):
        """Test model update submission with invalid round"""
        
        # Register node
        reg_result = await orchestrator.register_node(sample_node_info)
        node_id = reg_result['node_id']
        
        update_data = {
            'node_id': node_id,
            'round_id': 'invalid_round',
            'model_diff': b'fake_model_diff',
            'data_size': 1000,
            'compute_proof': 'proof',
            'signature': 'signature'
        }
        
        result = await orchestrator.submit_model_update(update_data)
        
        assert result['status'] == 'error'
        assert 'Invalid round' in result['message']
    
    def test_participant_selection(self, orchestrator):
        """Test participant selection logic"""
        
        # Create mock nodes with different reputation and compute power
        nodes = []
        for i in range(5):
            node = NodeInfo(
                node_id=f'node_{i}',
                ip_address='127.0.0.1',
                port=8000 + i,
                capabilities={},
                compute_power=float(i + 1),
                last_heartbeat=time.time(),
                reputation_score=0.5 + (i * 0.1),
                stake_amount=1000.0,
                status='active'
            )
            nodes.append(node)
        
        selected = orchestrator._select_participants(nodes)
        
        assert len(selected) <= orchestrator.max_nodes_per_round
        
        # Check that higher scoring nodes are preferred
        if len(selected) > 1:
            scores = [node.reputation_score * node.compute_power for node in selected]
            assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_status_retrieval(self, orchestrator):
        """Test status retrieval"""
        
        status = orchestrator.get_status()
        
        assert 'total_nodes' in status
        assert 'active_nodes' in status
        assert 'active_rounds' in status
        assert 'global_model_hash' in status
        assert 'uptime' in status

class TestNodeInfo:
    """Test cases for NodeInfo dataclass"""
    
    def test_node_info_creation(self):
        """Test NodeInfo creation"""
        
        node = NodeInfo(
            node_id='test_node',
            ip_address='192.168.1.1',
            port=8080,
            capabilities={'gpu': True},
            compute_power=2.0,
            last_heartbeat=time.time(),
            reputation_score=0.8,
            stake_amount=1500.0,
            status='active'
        )
        
        assert node.node_id == 'test_node'
        assert node.ip_address == '192.168.1.1'
        assert node.port == 8080
        assert node.capabilities['gpu'] is True
        assert node.compute_power == 2.0
        assert node.reputation_score == 0.8
        assert node.stake_amount == 1500.0
        assert node.status == 'active'

class TestTrainingRound:
    """Test cases for TrainingRound dataclass"""
    
    def test_training_round_creation(self):
        """Test TrainingRound creation"""
        
        current_time = time.time()
        round_obj = TrainingRound(
            round_id='round_1',
            global_model_hash='hash123',
            participants=['node_1', 'node_2'],
            start_time=current_time,
            deadline=current_time + 300,
            min_participants=2,
            max_participants=10,
            status='active'
        )
        
        assert round_obj.round_id == 'round_1'
        assert round_obj.global_model_hash == 'hash123'
        assert len(round_obj.participants) == 2
        assert round_obj.status == 'active'
        assert round_obj.deadline > round_obj.start_time

class TestModelUpdate:
    """Test cases for ModelUpdate dataclass"""
    
    def test_model_update_creation(self):
        """Test ModelUpdate creation"""
        
        update = ModelUpdate(
            node_id='node_1',
            round_id='round_1',
            model_diff=b'model_data',
            data_size=1024,
            compute_proof='proof123',
            signature='sig456',
            timestamp=time.time()
        )
        
        assert update.node_id == 'node_1'
        assert update.round_id == 'round_1'
        assert update.model_diff == b'model_data'
        assert update.data_size == 1024
        assert update.compute_proof == 'proof123'
        assert update.signature == 'sig456'

@pytest.mark.integration
class TestFederatedOrchestratorIntegration:
    """Integration tests for the orchestrator"""
    
    @pytest.mark.asyncio
    async def test_full_training_cycle(self, orchestrator, sample_node_info):
        """Test a complete training cycle"""
        
        # Register multiple nodes
        nodes = []
        for i in range(3):
            node_info = sample_node_info.copy()
            node_info['port'] = 8000 + i
            reg_result = await orchestrator.register_node(node_info)
            nodes.append(reg_result['node_id'])
        
        # Wait for nodes to be considered active
        await asyncio.sleep(0.1)
        
        # Simulate starting a training round
        active_nodes = [orchestrator.node_registry[nid] for nid in nodes]
        await orchestrator._start_training_round(active_nodes)
        
        # Check that a round was started
        assert len(orchestrator.active_rounds) == 1
        round_id = list(orchestrator.active_rounds.keys())[0]
        training_round = orchestrator.active_rounds[round_id]
        
        assert training_round.status == 'active'
        assert len(training_round.participants) <= orchestrator.max_nodes_per_round
        
        # Simulate model updates from participants
        for node_id in training_round.participants:
            update_data = {
                'node_id': node_id,
                'round_id': round_id,
                'model_diff': b'fake_model_diff',
                'data_size': 1000,
                'compute_proof': 'proof',
                'signature': 'signature'
            }
            
            result = await orchestrator.submit_model_update(update_data)
            assert result['status'] == 'accepted'
        
        # Complete the round
        await orchestrator._complete_training_round(round_id)
        
        # Check that round was completed
        assert round_id not in orchestrator.active_rounds

@pytest.mark.performance
class TestOrchestratorPerformance:
    """Performance tests for the orchestrator"""
    
    @pytest.mark.asyncio
    async def test_large_scale_node_registration(self, orchestrator):
        """Test registering many nodes"""
        
        start_time = time.time()
        
        # Register 100 nodes
        tasks = []
        for i in range(100):
            node_info = {
                'ip_address': f'192.168.1.{i+1}',
                'port': 8000 + i,
                'capabilities': {'gpu': i % 2 == 0},
                'compute_power': float(i % 5 + 1),
                'stake_amount': 1000.0
            }
            task = asyncio.create_task(orchestrator.register_node(node_info))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        registration_time = time.time() - start_time
        
        # Check all registrations succeeded
        assert len(results) == 100
        assert all(result['status'] == 'registered' for result in results)
        assert len(orchestrator.node_registry) == 100
        
        # Performance assertion (should complete in reasonable time)
        assert registration_time < 5.0  # 5 seconds max
        
        print(f"Registered 100 nodes in {registration_time:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_concurrent_heartbeats(self, orchestrator):
        """Test handling many concurrent heartbeats"""
        
        # Register 50 nodes first
        node_ids = []
        for i in range(50):
            node_info = {
                'ip_address': f'10.0.0.{i+1}',
                'port': 9000 + i,
                'capabilities': {},
                'compute_power': 1.0,
                'stake_amount': 1000.0
            }
            result = await orchestrator.register_node(node_info)
            node_ids.append(result['node_id'])
        
        # Send concurrent heartbeats
        start_time = time.time()
        
        tasks = []
        for node_id in node_ids:
            status_info = {'compute_power': 1.5}
            task = asyncio.create_task(orchestrator.heartbeat(node_id, status_info))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        heartbeat_time = time.time() - start_time
        
        # Check all heartbeats succeeded
        assert len(results) == 50
        assert all(result['status'] == 'acknowledged' for result in results)
        
        # Performance assertion
        assert heartbeat_time < 2.0  # 2 seconds max
        
        print(f"Processed 50 concurrent heartbeats in {heartbeat_time:.2f} seconds")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])