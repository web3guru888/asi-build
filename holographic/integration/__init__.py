"""
Integration with Kenny's existing systems
"""

from .kenny_integration import KennyHolographicIntegration
from .screen_monitor_integration import ScreenMonitorIntegration
from .ai_command_integration import AICommandIntegration
from .workflow_integration import WorkflowIntegration

__all__ = [
    'KennyHolographicIntegration',
    'ScreenMonitorIntegration',
    'AICommandIntegration',
    'WorkflowIntegration'
]