"""
Neuromorphic Computing Manager

Central coordinator for all neuromorphic computing components.
Manages system lifecycle, resource allocation, and coordination between subsystems.
"""

import os
import time
import threading
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from pathlib import Path
import json
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
import psutil

from .config import NeuromorphicConfig
from .event_processor import EventProcessor
from .temporal_dynamics import TemporalDynamics
from .spike_monitor import SpikeMonitor

@dataclass
class SystemStatus:
    """System status information."""
    is_running: bool = False
    current_time: float = 0.0
    total_neurons: int = 0
    total_synapses: int = 0
    active_components: int = 0
    events_processed: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class PerformanceMetrics:
    """Performance monitoring metrics."""
    simulation_speed: float = 0.0  # Simulation time / real time
    events_per_second: int = 0
    spikes_per_second: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    energy_consumption: float = 0.0  # Estimated joules
    computation_efficiency: float = 0.0  # Operations per joule

class NeuromorphicManager:
    """
    Central manager for neuromorphic computing system.
    
    Responsibilities:
    - System initialization and configuration
    - Component lifecycle management
    - Resource monitoring and optimization
    - Event coordination and synchronization
    - Performance tracking and reporting
    - Integration with Kenny's AI system
    """
    
    def __init__(self, config: Optional[NeuromorphicConfig] = None):
        """Initialize neuromorphic manager."""
        # Configuration
        self.config = config or NeuromorphicConfig()
        
        # System state
        self.status = SystemStatus()
        self.metrics = PerformanceMetrics()
        
        # Core components
        self.event_processor = EventProcessor(self.config)
        self.temporal_dynamics = TemporalDynamics(self.config)
        self.spike_monitor = SpikeMonitor(self.config)
        
        # Component registry
        self.networks = {}
        self.processors = {}
        self.interfaces = {}
        
        # Simulation control
        self.time_step = self.config.hardware.time_step
        self.max_simulation_time = 3600.0  # 1 hour max
        self.real_time_factor = 1.0
        
        # Threading
        self._simulation_thread = None
        self._monitoring_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # Callbacks
        self.event_callbacks = {}
        self.update_callbacks = []
        
        # Logging
        self.logger = logging.getLogger("neuromorphic.manager")
        self.performance_log = []
        
        # Resource monitoring
        self.process = psutil.Process()
        self.start_time = time.time()
        
        # Integration hooks
        self.kenny_integration = None
        
        self.logger.info("Neuromorphic Manager initialized")
    
    def initialize(self) -> bool:
        """Initialize the neuromorphic computing system."""
        try:
            self.logger.info("Initializing neuromorphic computing system...")
            
            # Validate configuration
            if not self.config.validate():
                raise RuntimeError("Configuration validation failed")
            
            # Initialize core components
            self.event_processor.initialize()
            self.temporal_dynamics.initialize()
            self.spike_monitor.initialize()
            
            # Setup monitoring
            self._setup_monitoring()
            
            # Initialize subsystems
            self._initialize_subsystems()
            
            # Start monitoring thread
            self._start_monitoring()
            
            self.status.is_running = True
            self.logger.info("Neuromorphic system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize neuromorphic system: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the neuromorphic computing system."""
        self.logger.info("Shutting down neuromorphic system...")
        
        # Stop simulation
        self.stop_simulation()
        
        # Signal shutdown
        self._stop_event.set()
        
        # Wait for threads to complete
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)
        
        # Shutdown components
        self.spike_monitor.shutdown()
        self.temporal_dynamics.shutdown()
        self.event_processor.shutdown()
        
        # Clear registries
        self.networks.clear()
        self.processors.clear()
        self.interfaces.clear()
        
        self.status.is_running = False
        self.logger.info("Neuromorphic system shutdown complete")
    
    def register_network(self, name: str, network: Any) -> bool:
        """Register a neural network."""
        try:
            with self._lock:
                if name in self.networks:
                    self.logger.warning(f"Network '{name}' already registered, replacing")
                
                self.networks[name] = network
                self.status.total_neurons += getattr(network, 'num_neurons', 0)
                self.status.total_synapses += getattr(network, 'num_synapses', 0)
                
            self.logger.info(f"Registered network: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register network {name}: {e}")
            return False
    
    def register_processor(self, name: str, processor: Any) -> bool:
        """Register a processing component."""
        try:
            with self._lock:
                self.processors[name] = processor
                
            self.logger.info(f"Registered processor: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register processor {name}: {e}")
            return False
    
    def register_interface(self, name: str, interface: Any) -> bool:
        """Register an interface component."""
        try:
            with self._lock:
                self.interfaces[name] = interface
                
            self.logger.info(f"Registered interface: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register interface {name}: {e}")
            return False
    
    def start_simulation(self, duration: Optional[float] = None, 
                        real_time: bool = False) -> bool:
        """Start neuromorphic simulation."""
        try:
            if self._simulation_thread and self._simulation_thread.is_alive():
                self.logger.warning("Simulation already running")
                return False
            
            # Setup simulation parameters
            sim_duration = min(duration or self.max_simulation_time, 
                              self.max_simulation_time)
            
            # Start simulation thread
            self._simulation_thread = threading.Thread(
                target=self._simulation_loop,
                args=(sim_duration, real_time),
                daemon=True
            )
            self._simulation_thread.start()
            
            self.logger.info(f"Started simulation (duration: {sim_duration}s, "
                           f"real_time: {real_time})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start simulation: {e}")
            return False
    
    def stop_simulation(self) -> None:
        """Stop neuromorphic simulation."""
        if self._simulation_thread and self._simulation_thread.is_alive():
            self._stop_event.set()
            self._simulation_thread.join(timeout=10.0)
            
            if self._simulation_thread.is_alive():
                self.logger.warning("Simulation thread did not stop gracefully")
            
            self.logger.info("Simulation stopped")
    
    def step(self) -> None:
        """Execute one simulation step."""
        start_time = time.perf_counter()
        
        try:
            # Update temporal dynamics
            self.temporal_dynamics.update(self.time_step)
            
            # Process events
            events_processed = self.event_processor.process_events(self.time_step)
            self.status.events_processed += events_processed
            
            # Update all registered networks
            for network in self.networks.values():
                if hasattr(network, 'step'):
                    network.step()
            
            # Update all processors
            for processor in self.processors.values():
                if hasattr(processor, 'update'):
                    processor.update(self.time_step)
            
            # Update spike monitoring
            self.spike_monitor.update(self.time_step)
            
            # Update time
            self.status.current_time += self.time_step
            
            # Call update callbacks
            for callback in self.update_callbacks:
                try:
                    callback(self.status.current_time, self.time_step)
                except Exception as e:
                    self.logger.warning(f"Update callback failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Simulation step failed: {e}")
            raise
        
        # Update performance metrics
        step_duration = time.perf_counter() - start_time
        self._update_performance_metrics(step_duration)
    
    def add_event_callback(self, event_type: str, callback: Callable) -> None:
        """Add callback for specific event types."""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
    
    def add_update_callback(self, callback: Callable) -> None:
        """Add callback for simulation updates."""
        self.update_callbacks.append(callback)
    
    def get_system_status(self) -> SystemStatus:
        """Get current system status."""
        with self._lock:
            # Update active components count
            self.status.active_components = (
                len(self.networks) + len(self.processors) + len(self.interfaces)
            )
            
            # Update resource usage
            try:
                self.status.cpu_usage = self.process.cpu_percent()
                self.status.memory_usage = self.process.memory_info().rss / 1024 / 1024
            except:
                pass
            
            self.status.last_update = datetime.now()
            
        return self.status
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.metrics
    
    def get_component_info(self) -> Dict[str, Any]:
        """Get information about all registered components."""
        info = {
            'networks': {},
            'processors': {},
            'interfaces': {}
        }
        
        # Network information
        for name, network in self.networks.items():
            if hasattr(network, 'get_network_state'):
                info['networks'][name] = network.get_network_state()
            else:
                info['networks'][name] = {'type': type(network).__name__}
        
        # Processor information
        for name, processor in self.processors.items():
            if hasattr(processor, 'get_info'):
                info['processors'][name] = processor.get_info()
            else:
                info['processors'][name] = {'type': type(processor).__name__}
        
        # Interface information
        for name, interface in self.interfaces.items():
            if hasattr(interface, 'get_status'):
                info['interfaces'][name] = interface.get_status()
            else:
                info['interfaces'][name] = {'type': type(interface).__name__}
        
        return info
    
    def save_state(self, filepath: Union[str, Path]) -> bool:
        """Save current system state to file."""
        try:
            state_data = {
                'timestamp': datetime.now().isoformat(),
                'status': self.status.__dict__,
                'metrics': self.metrics.__dict__,
                'config': self.config.to_dict(),
                'components': self.get_component_info(),
                'performance_log': self.performance_log[-1000:]  # Last 1000 entries
            }
            
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
            
            self.logger.info(f"System state saved to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False
    
    def load_state(self, filepath: Union[str, Path]) -> bool:
        """Load system state from file."""
        try:
            filepath = Path(filepath)
            if not filepath.exists():
                raise FileNotFoundError(f"State file not found: {filepath}")
            
            with open(filepath, 'r') as f:
                state_data = json.load(f)
            
            # Load configuration
            if 'config' in state_data:
                self.config._update_from_dict(state_data['config'])
            
            # Load performance log
            if 'performance_log' in state_data:
                self.performance_log = state_data['performance_log']
            
            self.logger.info(f"System state loaded from {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            return False
    
    def set_kenny_integration(self, integration_handler: Any) -> None:
        """Set Kenny AI integration handler."""
        self.kenny_integration = integration_handler
        self.logger.info("Kenny AI integration enabled")
    
    def _simulation_loop(self, duration: float, real_time: bool) -> None:
        """Main simulation loop."""
        start_real_time = time.time()
        start_sim_time = self.status.current_time
        target_steps = int(duration / self.time_step)
        
        self.logger.info(f"Starting simulation loop: {target_steps} steps")
        
        try:
            for step_idx in range(target_steps):
                if self._stop_event.is_set():
                    break
                
                # Execute simulation step
                self.step()
                
                # Real-time synchronization
                if real_time:
                    elapsed_real = time.time() - start_real_time
                    elapsed_sim = self.status.current_time - start_sim_time
                    target_real = elapsed_sim / self.real_time_factor
                    
                    if elapsed_real < target_real:
                        time.sleep(target_real - elapsed_real)
                
                # Periodic status updates
                if step_idx % 1000 == 0:
                    self.logger.debug(f"Simulation step {step_idx}/{target_steps}")
                    
        except Exception as e:
            self.logger.error(f"Simulation loop error: {e}")
        finally:
            self._stop_event.clear()
            self.logger.info("Simulation loop completed")
    
    def _setup_monitoring(self) -> None:
        """Setup system monitoring."""
        # Configure performance logging
        self.performance_log = []
        
        # Setup resource monitoring
        self.process = psutil.Process()
    
    def _start_monitoring(self) -> None:
        """Start monitoring thread."""
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self._monitoring_thread.start()
        self.logger.debug("Monitoring thread started")
    
    def _monitoring_loop(self) -> None:
        """Monitoring loop for system metrics."""
        while not self._stop_event.is_set():
            try:
                # Update system metrics
                self._update_system_metrics()
                
                # Sleep for monitoring interval
                time.sleep(1.0)  # Update every second
                
            except Exception as e:
                self.logger.warning(f"Monitoring error: {e}")
    
    def _update_system_metrics(self) -> None:
        """Update system resource metrics."""
        try:
            # CPU and memory usage
            self.metrics.cpu_usage_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            self.metrics.memory_usage_mb = memory_info.rss / 1024 / 1024
            
            # Simulation speed
            if self.status.current_time > 0:
                real_elapsed = time.time() - self.start_time
                sim_elapsed = self.status.current_time
                self.metrics.simulation_speed = sim_elapsed / real_elapsed
            
            # Energy estimation (rough approximation)
            power_estimate = self.metrics.cpu_usage_percent / 100.0 * 100.0  # Watts
            self.metrics.energy_consumption += power_estimate  # Joules
            
        except Exception as e:
            self.logger.warning(f"Failed to update metrics: {e}")
    
    def _update_performance_metrics(self, step_duration: float) -> None:
        """Update performance metrics from simulation step."""
        # Events per second
        if step_duration > 0:
            self.metrics.events_per_second = int(1.0 / step_duration)
        
        # Log performance data
        perf_entry = {
            'time': self.status.current_time,
            'step_duration': step_duration,
            'cpu_usage': self.metrics.cpu_usage_percent,
            'memory_usage': self.metrics.memory_usage_mb,
            'events_processed': self.status.events_processed
        }
        
        self.performance_log.append(perf_entry)
        
        # Keep only recent entries
        if len(self.performance_log) > 10000:
            self.performance_log = self.performance_log[-5000:]
    
    def _initialize_subsystems(self) -> None:
        """Initialize neuromorphic subsystems."""
        # This will be expanded as subsystems are implemented
        pass
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()