"""
Multiverse Configuration Manager
===============================

Manages configuration for all multiverse components, including universe settings,
quantum parameters, temporal constraints, and safety limits.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import numpy as np


@dataclass
class QuantumConfig:
    """Configuration for quantum systems."""
    default_dimension: int = 2
    max_dimension: int = 1024
    decoherence_rate: float = 0.001
    entanglement_threshold: float = 0.1
    measurement_precision: float = 1e-10
    quantum_noise_level: float = 0.01
    coherence_time_default: float = 1000.0
    superposition_states_max: int = 64
    fidelity_threshold: float = 0.95


@dataclass
class TemporalConfig:
    """Configuration for temporal systems."""
    max_timeline_branches: int = 100
    timeline_stability_threshold: float = 0.8
    causal_loop_detection_depth: int = 50
    temporal_resolution: float = 0.001  # seconds
    max_temporal_displacement: float = 3.1536e9  # 100 years in seconds
    temporal_paradox_tolerance: float = 0.1
    convergence_timeout: float = 300.0  # 5 minutes
    temporal_anchor_strength: float = 1.0


@dataclass
class DimensionalConfig:
    """Configuration for dimensional systems."""
    max_dimensions: int = 11  # String theory limit
    portal_stability_threshold: float = 0.7
    portal_energy_requirement: float = 1e15  # Planck scale energy
    dimensional_coordinate_precision: float = 1e-12
    portal_lifetime_default: float = 3600.0  # 1 hour
    gateway_network_max_nodes: int = 1000
    dimensional_barrier_strength: float = 0.9
    portal_generation_cooldown: float = 60.0  # 1 minute


@dataclass
class SafetyConfig:
    """Configuration for safety systems."""
    reality_integrity_threshold: float = 0.9
    paradox_prevention_enabled: bool = True
    emergency_stabilization_enabled: bool = True
    causal_violation_max_severity: float = 0.3
    reality_anchor_redundancy: int = 3
    automatic_universe_quarantine: bool = True
    safety_monitoring_interval: float = 1.0  # seconds
    max_concurrent_operations: int = 10
    ethical_constraint_enforcement: bool = True


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""
    max_worker_threads: int = 8
    monitoring_interval: float = 5.0  # seconds
    cache_size_mb: int = 512
    batch_operation_size: int = 100
    async_operation_timeout: float = 30.0
    memory_usage_threshold: float = 0.8  # 80% of available memory
    cpu_usage_threshold: float = 0.9  # 90% CPU usage
    io_timeout: float = 10.0


@dataclass
class UniverseConfig:
    """Configuration for individual universes."""
    id: str = ""
    name: str = ""
    physics_constants: Dict[str, float] = field(default_factory=dict)
    natural_laws: Dict[str, Any] = field(default_factory=dict)
    dimensional_properties: Dict[str, float] = field(default_factory=dict)
    quantum_properties: Dict[str, float] = field(default_factory=dict)
    temporal_properties: Dict[str, float] = field(default_factory=dict)
    safety_overrides: Dict[str, Any] = field(default_factory=dict)
    custom_parameters: Dict[str, Any] = field(default_factory=dict)


class MultiverseConfig:
    """
    Central configuration manager for the multiverse framework.
    
    Manages all configuration aspects including quantum mechanics,
    temporal dynamics, dimensional physics, safety parameters,
    and performance settings.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize multiverse configuration.
        
        Args:
            config_path: Path to configuration file (JSON or YAML)
        """
        self.logger = logging.getLogger("multiverse.config")
        
        # Default configurations
        self.quantum = QuantumConfig()
        self.temporal = TemporalConfig()
        self.dimensional = DimensionalConfig()
        self.safety = SafetyConfig()
        self.performance = PerformanceConfig()
        
        # Universe configurations
        self.universes: Dict[str, UniverseConfig] = {}
        
        # Global multiverse parameters
        self.max_universes = 1000
        self.branching_threshold = 0.8
        self.collapse_threshold = 0.01
        self.entropy_threshold = 10.0
        self.quantum_anomaly_threshold = 100.0
        self.temporal_deviation_threshold = 0.5
        self.branching_probability_multiplier = 0.1
        self.max_child_universes = 10
        
        # Environment-specific overrides
        self._apply_environment_overrides()
        
        # Load configuration file if provided
        if config_path:
            self.load_from_file(config_path)
        
        self.logger.info("MultiverseConfig initialized")
    
    def _apply_environment_overrides(self):
        """Apply configuration overrides from environment variables."""
        # Quantum overrides
        if os.getenv('MULTIVERSE_QUANTUM_DIMENSION'):
            self.quantum.default_dimension = int(os.getenv('MULTIVERSE_QUANTUM_DIMENSION'))
        
        # Temporal overrides
        if os.getenv('MULTIVERSE_MAX_TIMELINE_BRANCHES'):
            self.temporal.max_timeline_branches = int(os.getenv('MULTIVERSE_MAX_TIMELINE_BRANCHES'))
        
        # Safety overrides
        if os.getenv('MULTIVERSE_PARADOX_PREVENTION'):
            self.safety.paradox_prevention_enabled = os.getenv('MULTIVERSE_PARADOX_PREVENTION').lower() == 'true'
        
        # Performance overrides
        if os.getenv('MULTIVERSE_WORKER_THREADS'):
            self.performance.max_worker_threads = int(os.getenv('MULTIVERSE_WORKER_THREADS'))
        
        # Global overrides
        if os.getenv('MULTIVERSE_MAX_UNIVERSES'):
            self.max_universes = int(os.getenv('MULTIVERSE_MAX_UNIVERSES'))
        
        self.logger.debug("Applied environment variable overrides")
    
    def load_from_file(self, config_path: str):
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to configuration file (JSON or YAML)
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            self.logger.error("Configuration file not found: %s", config_path)
            return
        
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)
            
            self._apply_config_data(config_data)
            self.logger.info("Configuration loaded from: %s", config_path)
            
        except Exception as e:
            self.logger.error("Error loading configuration file %s: %s", config_path, e)
    
    def _apply_config_data(self, config_data: Dict[str, Any]):
        """Apply configuration data from dictionary."""
        # Apply quantum configuration
        if 'quantum' in config_data:
            self._update_dataclass_from_dict(self.quantum, config_data['quantum'])
        
        # Apply temporal configuration
        if 'temporal' in config_data:
            self._update_dataclass_from_dict(self.temporal, config_data['temporal'])
        
        # Apply dimensional configuration
        if 'dimensional' in config_data:
            self._update_dataclass_from_dict(self.dimensional, config_data['dimensional'])
        
        # Apply safety configuration
        if 'safety' in config_data:
            self._update_dataclass_from_dict(self.safety, config_data['safety'])
        
        # Apply performance configuration
        if 'performance' in config_data:
            self._update_dataclass_from_dict(self.performance, config_data['performance'])
        
        # Apply global parameters
        global_params = [
            'max_universes', 'branching_threshold', 'collapse_threshold',
            'entropy_threshold', 'quantum_anomaly_threshold',
            'temporal_deviation_threshold', 'branching_probability_multiplier',
            'max_child_universes'
        ]
        
        for param in global_params:
            if param in config_data:
                setattr(self, param, config_data[param])
        
        # Apply universe configurations
        if 'universes' in config_data:
            for universe_id, universe_config in config_data['universes'].items():
                self.add_universe_config(universe_id, universe_config)
    
    def _update_dataclass_from_dict(self, dataclass_instance, config_dict: Dict[str, Any]):
        """Update dataclass instance from dictionary."""
        for key, value in config_dict.items():
            if hasattr(dataclass_instance, key):
                setattr(dataclass_instance, key, value)
            else:
                self.logger.warning("Unknown configuration parameter: %s", key)
    
    def save_to_file(self, config_path: str, format: str = 'yaml'):
        """
        Save current configuration to file.
        
        Args:
            config_path: Path to save configuration file
            format: File format ('yaml' or 'json')
        """
        config_data = self.to_dict()
        
        try:
            with open(config_path, 'w') as f:
                if format.lower() == 'yaml':
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_data, f, indent=2, default=str)
            
            self.logger.info("Configuration saved to: %s", config_path)
            
        except Exception as e:
            self.logger.error("Error saving configuration to %s: %s", config_path, e)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'quantum': asdict(self.quantum),
            'temporal': asdict(self.temporal),
            'dimensional': asdict(self.dimensional),
            'safety': asdict(self.safety),
            'performance': asdict(self.performance),
            'max_universes': self.max_universes,
            'branching_threshold': self.branching_threshold,
            'collapse_threshold': self.collapse_threshold,
            'entropy_threshold': self.entropy_threshold,
            'quantum_anomaly_threshold': self.quantum_anomaly_threshold,
            'temporal_deviation_threshold': self.temporal_deviation_threshold,
            'branching_probability_multiplier': self.branching_probability_multiplier,
            'max_child_universes': self.max_child_universes,
            'universes': {uid: asdict(config) for uid, config in self.universes.items()}
        }
    
    def add_universe_config(self, universe_id: str, config: Union[Dict[str, Any], UniverseConfig]):
        """
        Add configuration for a specific universe.
        
        Args:
            universe_id: Unique identifier for the universe
            config: Universe configuration (dict or UniverseConfig)
        """
        if isinstance(config, dict):
            universe_config = UniverseConfig(id=universe_id)
            self._update_dataclass_from_dict(universe_config, config)
        else:
            universe_config = config
            universe_config.id = universe_id
        
        self.universes[universe_id] = universe_config
        self.logger.debug("Added universe configuration: %s", universe_id)
    
    def get_universe_config(self, universe_id: str) -> Optional[UniverseConfig]:
        """Get configuration for a specific universe."""
        return self.universes.get(universe_id)
    
    def remove_universe_config(self, universe_id: str) -> bool:
        """Remove configuration for a specific universe."""
        if universe_id in self.universes:
            del self.universes[universe_id]
            self.logger.debug("Removed universe configuration: %s", universe_id)
            return True
        return False
    
    def validate_configuration(self) -> List[str]:
        """
        Validate the current configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate quantum configuration
        if self.quantum.default_dimension < 1:
            errors.append("Quantum default dimension must be positive")
        
        if self.quantum.max_dimension < self.quantum.default_dimension:
            errors.append("Quantum max dimension must be >= default dimension")
        
        if not (0 <= self.quantum.decoherence_rate <= 1):
            errors.append("Quantum decoherence rate must be between 0 and 1")
        
        # Validate temporal configuration
        if self.temporal.max_timeline_branches < 1:
            errors.append("Max timeline branches must be positive")
        
        if not (0 <= self.temporal.timeline_stability_threshold <= 1):
            errors.append("Timeline stability threshold must be between 0 and 1")
        
        # Validate dimensional configuration
        if self.dimensional.max_dimensions < 3:
            errors.append("Max dimensions must be at least 3")
        
        if not (0 <= self.dimensional.portal_stability_threshold <= 1):
            errors.append("Portal stability threshold must be between 0 and 1")
        
        # Validate safety configuration
        if not (0 <= self.safety.reality_integrity_threshold <= 1):
            errors.append("Reality integrity threshold must be between 0 and 1")
        
        if self.safety.reality_anchor_redundancy < 1:
            errors.append("Reality anchor redundancy must be positive")
        
        # Validate performance configuration
        if self.performance.max_worker_threads < 1:
            errors.append("Max worker threads must be positive")
        
        if self.performance.monitoring_interval <= 0:
            errors.append("Monitoring interval must be positive")
        
        # Validate global parameters
        if self.max_universes < 1:
            errors.append("Max universes must be positive")
        
        if not (0 <= self.branching_threshold <= 1):
            errors.append("Branching threshold must be between 0 and 1")
        
        if not (0 <= self.collapse_threshold <= 1):
            errors.append("Collapse threshold must be between 0 and 1")
        
        return errors
    
    def get_effective_config_for_universe(self, universe_id: str) -> Dict[str, Any]:
        """
        Get effective configuration for a specific universe.
        
        Combines global configuration with universe-specific overrides.
        
        Args:
            universe_id: Universe identifier
            
        Returns:
            Effective configuration dictionary
        """
        base_config = self.to_dict()
        
        # Apply universe-specific overrides
        universe_config = self.get_universe_config(universe_id)
        if universe_config:
            # Override physics constants
            if universe_config.physics_constants:
                base_config['physics_constants'] = universe_config.physics_constants
            
            # Override natural laws
            if universe_config.natural_laws:
                base_config['natural_laws'] = universe_config.natural_laws
            
            # Override quantum properties
            if universe_config.quantum_properties:
                for key, value in universe_config.quantum_properties.items():
                    if hasattr(self.quantum, key):
                        base_config['quantum'][key] = value
            
            # Override temporal properties
            if universe_config.temporal_properties:
                for key, value in universe_config.temporal_properties.items():
                    if hasattr(self.temporal, key):
                        base_config['temporal'][key] = value
            
            # Override dimensional properties
            if universe_config.dimensional_properties:
                for key, value in universe_config.dimensional_properties.items():
                    if hasattr(self.dimensional, key):
                        base_config['dimensional'][key] = value
            
            # Apply safety overrides
            if universe_config.safety_overrides:
                for key, value in universe_config.safety_overrides.items():
                    if hasattr(self.safety, key):
                        base_config['safety'][key] = value
            
            # Apply custom parameters
            if universe_config.custom_parameters:
                base_config['custom'] = universe_config.custom_parameters
        
        return base_config
    
    def create_default_universe_config(self, universe_id: str, 
                                     **kwargs) -> UniverseConfig:
        """
        Create a default universe configuration with optional overrides.
        
        Args:
            universe_id: Universe identifier
            **kwargs: Configuration overrides
            
        Returns:
            Universe configuration
        """
        config = UniverseConfig(
            id=universe_id,
            name=kwargs.get('name', f"Universe_{universe_id[:8]}"),
            physics_constants=kwargs.get('physics_constants', {}),
            natural_laws=kwargs.get('natural_laws', {}),
            dimensional_properties=kwargs.get('dimensional_properties', {}),
            quantum_properties=kwargs.get('quantum_properties', {}),
            temporal_properties=kwargs.get('temporal_properties', {}),
            safety_overrides=kwargs.get('safety_overrides', {}),
            custom_parameters=kwargs.get('custom_parameters', {})
        )
        
        self.add_universe_config(universe_id, config)
        return config
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary."""
        errors = self.validate_configuration()
        
        return {
            'quantum_dimension': self.quantum.default_dimension,
            'max_universes': self.max_universes,
            'max_timeline_branches': self.temporal.max_timeline_branches,
            'max_dimensions': self.dimensional.max_dimensions,
            'safety_enabled': self.safety.paradox_prevention_enabled,
            'worker_threads': self.performance.max_worker_threads,
            'universe_configs': len(self.universes),
            'configuration_valid': len(errors) == 0,
            'validation_errors': errors
        }
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return (f"MultiverseConfig("
                f"universes={len(self.universes)}, "
                f"max_universes={self.max_universes}, "
                f"quantum_dim={self.quantum.default_dimension})")


# Global configuration instance
_global_config: Optional[MultiverseConfig] = None


def get_global_config() -> MultiverseConfig:
    """Get the global multiverse configuration."""
    global _global_config
    if _global_config is None:
        _global_config = MultiverseConfig()
    return _global_config


def set_global_config(config: MultiverseConfig):
    """Set the global multiverse configuration."""
    global _global_config
    _global_config = config


def load_global_config(config_path: str):
    """Load global configuration from file."""
    global _global_config
    _global_config = MultiverseConfig(config_path)