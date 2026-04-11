"""
Test BCI Manager functionality
"""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch

from ..core.bci_manager import BCIManager
from ..core.config import BCIConfig


class TestBCIManager:
    """Test BCI Manager"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        config = BCIConfig()
        config.device.sampling_rate = 250.0
        config.device.channels = ['C3', 'C4', 'Cz']
        return config
    
    @pytest.fixture
    def bci_manager(self, config):
        """Create BCI manager instance"""
        return BCIManager(config)
    
    @pytest.mark.asyncio
    async def test_start_session(self, bci_manager):
        """Test starting a BCI session"""
        session_id = await bci_manager.start_session(
            device_type="simulated_eeg",
            tasks=["motor_imagery"]
        )
        
        assert session_id is not None
        assert session_id in bci_manager.active_sessions
        
        session_info = bci_manager.get_session_info(session_id)
        assert session_info['device_type'] == 'simulated_eeg'
        assert 'motor_imagery' in session_info['tasks']
        
        # Cleanup
        await bci_manager.stop_session(session_id)
    
    @pytest.mark.asyncio
    async def test_stop_session(self, bci_manager):
        """Test stopping a BCI session"""
        session_id = await bci_manager.start_session(
            device_type="simulated_eeg",
            tasks=["motor_imagery"]
        )
        
        success = await bci_manager.stop_session(session_id)
        assert success is True
        
        session_info = bci_manager.get_session_info(session_id)
        assert session_info['status'] == 'stopped'
    
    @pytest.mark.asyncio
    async def test_calibration(self, bci_manager):
        """Test BCI calibration"""
        await bci_manager.start_session(
            device_type="simulated_eeg",
            tasks=["motor_imagery"]
        )
        
        # Mock calibration data
        with patch.object(bci_manager, '_collect_calibration_trial') as mock_collect:
            mock_collect.return_value = {
                'task_type': 'motor_imagery',
                'raw_data': [np.random.randn(3, 250)],
                'processed_data': [{'features': {'test_feature': 1.0}}]
            }
            
            result = await bci_manager.calibrate(
                task_type="motor_imagery",
                duration=10.0,
                trials=2
            )
            
            assert 'accuracy' in result
            assert result['task'] == 'motor_imagery'
    
    def test_get_system_status(self, bci_manager):
        """Test system status retrieval"""
        status = bci_manager.get_system_status()
        
        assert 'active_sessions' in status
        assert 'device_connected' in status
        assert 'is_processing' in status
        assert 'uptime' in status
    
    @pytest.mark.asyncio
    async def test_shutdown(self, bci_manager):
        """Test BCI manager shutdown"""
        await bci_manager.start_session(
            device_type="simulated_eeg",
            tasks=["motor_imagery"]
        )
        
        await bci_manager.shutdown()
        
        assert len(bci_manager.active_sessions) == 0
        assert not bci_manager.is_running