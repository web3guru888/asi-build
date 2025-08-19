"""
Kenny Federated Learning Integration

Integrates the federated learning framework with Kenny's existing systems,
including database, monitoring, and UI automation capabilities.
"""

import logging
import time
from typing import Dict, Any, List, Optional
import json
import os

from ..core.config import FederatedConfig
from ..core.manager import FederatedManager
from ..utils.metrics import FederatedMetrics, PerformanceTracker


class KennyFederatedIntegration:
    """
    Integration layer between Kenny systems and federated learning framework.
    
    Provides seamless integration with Kenny's existing infrastructure
    including databases, monitoring, and automation systems.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.kenny_config_path = config.get("kenny_config_path", "/home/ubuntu/code/kenny/src")
        
        # Initialize federated learning components
        self.federated_config = None
        self.federated_manager = None
        self.metrics = FederatedMetrics()
        self.performance_tracker = PerformanceTracker()
        
        # Kenny integration state
        self.kenny_database_connected = False
        self.kenny_monitoring_enabled = False
        self.integration_history = []
        
        self.logger = logging.getLogger("KennyFederatedIntegration")
        self.logger.info("Kenny federated learning integration initialized")
    
    def setup_federated_config(self, federated_config: FederatedConfig):
        """Setup federated learning configuration."""
        self.federated_config = federated_config
        self.federated_manager = FederatedManager(federated_config)
        
        self.logger.info(f"Federated config setup: {federated_config.experiment_name}")
    
    def connect_to_kenny_database(self) -> bool:
        """Connect to Kenny's database system."""
        try:
            # Import Kenny's database manager
            kenny_db_path = os.path.join(self.kenny_config_path, "database_manager.py")
            if os.path.exists(kenny_db_path):
                # In a real implementation, we would import and use Kenny's database
                self.kenny_database_connected = True
                self.logger.info("Connected to Kenny database")
                return True
            else:
                self.logger.warning("Kenny database manager not found")
                return False
        except Exception as e:
            self.logger.error(f"Failed to connect to Kenny database: {str(e)}")
            return False
    
    def enable_kenny_monitoring(self) -> bool:
        """Enable integration with Kenny's monitoring systems."""
        try:
            # Import Kenny's monitoring components
            kenny_monitor_path = os.path.join(self.kenny_config_path, "performance_monitor.py")
            if os.path.exists(kenny_monitor_path):
                self.kenny_monitoring_enabled = True
                self.logger.info("Kenny monitoring integration enabled")
                return True
            else:
                self.logger.warning("Kenny monitoring system not found")
                return False
        except Exception as e:
            self.logger.error(f"Failed to enable Kenny monitoring: {str(e)}")
            return False
    
    def setup_with_kenny_systems(self) -> Dict[str, Any]:
        """Setup complete integration with Kenny systems."""
        setup_results = {
            "database_connected": self.connect_to_kenny_database(),
            "monitoring_enabled": self.enable_kenny_monitoring(),
            "timestamp": time.time()
        }
        
        # Store integration history
        self.integration_history.append({
            "action": "setup_integration",
            "results": setup_results,
            "timestamp": time.time()
        })
        
        return setup_results
    
    def run_federated_training_with_kenny(self, training_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run federated learning integrated with Kenny systems."""
        if not self.federated_manager:
            raise ValueError("Federated manager not initialized. Call setup_federated_config first.")
        
        training_start_time = time.time()
        
        # Record start in Kenny database if connected
        if self.kenny_database_connected:
            self._record_to_kenny_database("federated_training_start", {
                "experiment_name": self.federated_config.experiment_name,
                "start_time": training_start_time,
                "config": training_config
            })
        
        try:
            # Run federated training
            training_results = self.federated_manager.run_training(
                training_config.get("max_rounds", 10)
            )
            
            # Collect comprehensive metrics
            training_metrics = {
                "federated_results": training_results,
                "performance_metrics": self.performance_tracker.get_current_performance(),
                "kenny_integration_status": {
                    "database_connected": self.kenny_database_connected,
                    "monitoring_enabled": self.kenny_monitoring_enabled
                }
            }
            
            # Record completion in Kenny database
            if self.kenny_database_connected:
                self._record_to_kenny_database("federated_training_complete", {
                    "experiment_name": self.federated_config.experiment_name,
                    "duration": time.time() - training_start_time,
                    "results": training_metrics
                })
            
            # Send to Kenny monitoring if enabled
            if self.kenny_monitoring_enabled:
                self._send_to_kenny_monitoring(training_metrics)
            
            self.logger.info("Federated training completed with Kenny integration")
            return training_metrics
            
        except Exception as e:
            # Record error in Kenny database
            if self.kenny_database_connected:
                self._record_to_kenny_database("federated_training_error", {
                    "experiment_name": self.federated_config.experiment_name,
                    "error": str(e),
                    "timestamp": time.time()
                })
            
            self.logger.error(f"Federated training failed: {str(e)}")
            raise
    
    def _record_to_kenny_database(self, event_type: str, data: Dict[str, Any]):
        """Record federated learning events to Kenny's database."""
        # In a real implementation, this would use Kenny's database manager
        record = {
            "event_type": event_type,
            "data": data,
            "timestamp": time.time(),
            "source": "federated_learning_framework"
        }
        
        # Simulate database insertion
        self.logger.debug(f"Recording to Kenny database: {event_type}")
    
    def _send_to_kenny_monitoring(self, metrics: Dict[str, Any]):
        """Send metrics to Kenny's monitoring system."""
        # In a real implementation, this would integrate with Kenny's monitoring
        monitoring_data = {
            "system": "federated_learning",
            "metrics": metrics,
            "timestamp": time.time()
        }
        
        # Simulate sending to monitoring
        self.logger.debug("Sending metrics to Kenny monitoring")
    
    def get_kenny_federated_status(self) -> Dict[str, Any]:
        """Get comprehensive status of Kenny-federated learning integration."""
        status = {
            "integration_active": True,
            "kenny_database_connected": self.kenny_database_connected,
            "kenny_monitoring_enabled": self.kenny_monitoring_enabled,
            "federated_manager_initialized": self.federated_manager is not None,
            "integration_history": len(self.integration_history),
            "last_integration_action": (
                self.integration_history[-1] if self.integration_history else None
            )
        }
        
        if self.federated_manager:
            status["federated_training_status"] = self.federated_manager.get_training_status()
        
        return status
    
    def export_integration_report(self, filepath: str):
        """Export comprehensive integration report."""
        report = {
            "integration_summary": self.get_kenny_federated_status(),
            "federated_metrics": self.metrics.get_performance_summary(),
            "performance_tracking": self.performance_tracker.get_current_performance(),
            "integration_history": self.integration_history,
            "export_timestamp": time.time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Integration report exported to {filepath}")


def create_kenny_federated_setup(kenny_config_path: str, 
                                experiment_name: str) -> KennyFederatedIntegration:
    """
    Quick setup function for Kenny-federated learning integration.
    
    Args:
        kenny_config_path: Path to Kenny's configuration
        experiment_name: Name of the federated learning experiment
        
    Returns:
        Configured KennyFederatedIntegration instance
    """
    # Create integration configuration
    integration_config = {
        "kenny_config_path": kenny_config_path,
        "experiment_name": experiment_name,
        "enable_database_integration": True,
        "enable_monitoring_integration": True
    }
    
    # Initialize integration
    kenny_fl = KennyFederatedIntegration(integration_config)
    
    # Setup Kenny systems
    setup_results = kenny_fl.setup_with_kenny_systems()
    
    logging.info(f"Kenny federated learning setup completed: {setup_results}")
    
    return kenny_fl


# Example usage with Kenny integration
def example_kenny_federated_learning():
    """Example of running federated learning with Kenny integration."""
    
    # Initialize Kenny-federated integration
    kenny_fl = create_kenny_federated_setup(
        kenny_config_path="/home/ubuntu/code/kenny/src",
        experiment_name="kenny_federated_demo"
    )
    
    # Create federated learning configuration
    from ..core.config import FederatedConfig, ClientConfig, ServerConfig
    
    federated_config = FederatedConfig(
        experiment_name="kenny_federated_demo",
        client=ClientConfig(
            client_id="kenny_client",
            local_epochs=3,
            batch_size=32
        ),
        server=ServerConfig(
            rounds=10,
            min_clients=2
        )
    )
    
    # Setup federated configuration
    kenny_fl.setup_federated_config(federated_config)
    
    # Run federated training with Kenny integration
    training_config = {
        "max_rounds": 10,
        "enable_kenny_monitoring": True,
        "save_to_kenny_database": True
    }
    
    results = kenny_fl.run_federated_training_with_kenny(training_config)
    
    # Export integration report
    kenny_fl.export_integration_report("kenny_federated_report.json")
    
    return results


if __name__ == "__main__":
    # Run example
    example_results = example_kenny_federated_learning()
    print("Kenny federated learning integration example completed!")
    print(f"Results summary: {example_results.keys()}")