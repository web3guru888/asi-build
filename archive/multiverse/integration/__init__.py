"""
Multiverse Integration Systems
=============================

Integration modules for connecting the multiverse framework
with Kenny's AI system and autonomous operations.
"""

from .kenny_multiverse_integration import KennyMultiverseIntegration
from .autonomous_multiverse_mode import AutonomousMultiverseMode  
from .multiverse_api import MultiverseAPI, APIEndpoint
from .screen_monitoring_integration import ScreenMonitoringIntegration
from .command_execution_bridge import CommandExecutionBridge
from .reality_aware_automation import RealityAwareAutomation
from .dimensional_task_manager import DimensionalTaskManager
from .quantum_decision_engine import QuantumDecisionEngine

__all__ = [
    'KennyMultiverseIntegration',
    'AutonomousMultiverseMode', 
    'MultiverseAPI', 'APIEndpoint',
    'ScreenMonitoringIntegration',
    'CommandExecutionBridge',
    'RealityAwareAutomation',
    'DimensionalTaskManager',
    'QuantumDecisionEngine'
]