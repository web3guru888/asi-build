"""
Federated Learning Configuration

Configuration classes for federated learning components.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Union
from enum import Enum


class AggregationType(Enum):
    """Aggregation algorithm types."""
    FEDAVG = "fedavg"
    FEDPROX = "fedprox"
    FEDNOVA = "fednova"
    SCAFFOLD = "scaffold"
    SECURE_AGGREGATION = "secure_aggregation"
    BYZANTINE_ROBUST = "byzantine_robust"


class PrivacyMechanism(Enum):
    """Privacy-preserving mechanisms."""
    NONE = "none"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    SECURE_MULTI_PARTY = "secure_multi_party"
    HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"
    SECRET_SHARING = "secret_sharing"


class CommunicationProtocol(Enum):
    """Communication protocols."""
    HTTP = "http"
    HTTPS = "https"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    MQTT = "mqtt"


@dataclass
class PrivacyConfig:
    """Privacy configuration."""
    mechanism: PrivacyMechanism = PrivacyMechanism.NONE
    epsilon: float = 1.0  # Differential privacy parameter
    delta: float = 1e-5   # Differential privacy parameter
    noise_multiplier: float = 1.0
    max_grad_norm: float = 1.0
    secure_aggregation_threshold: int = 3
    homomorphic_key_size: int = 2048


@dataclass
class SecurityConfig:
    """Security configuration."""
    enable_tls: bool = True
    certificate_path: Optional[str] = None
    private_key_path: Optional[str] = None
    authentication_required: bool = True
    api_key_header: str = "X-API-Key"
    rate_limiting: bool = True
    max_requests_per_minute: int = 100


@dataclass
class CompressionConfig:
    """Model compression configuration."""
    enable_compression: bool = False
    compression_type: str = "quantization"  # quantization, pruning, distillation
    quantization_bits: int = 8
    sparsity_ratio: float = 0.1
    compression_ratio: float = 0.5


@dataclass
class ClientConfig:
    """Client configuration."""
    client_id: str
    local_epochs: int = 1
    batch_size: int = 32
    learning_rate: float = 0.01
    data_path: str = ""
    model_path: str = ""
    max_samples_per_round: Optional[int] = None
    enable_local_validation: bool = True
    validation_split: float = 0.1
    privacy: PrivacyConfig = None
    compression: CompressionConfig = None
    
    def __post_init__(self):
        if self.privacy is None:
            self.privacy = PrivacyConfig()
        if self.compression is None:
            self.compression = CompressionConfig()


@dataclass
class ServerConfig:
    """Server configuration."""
    server_id: str = "federated_server"
    host: str = "localhost"
    port: int = 8080
    max_clients: int = 100
    min_clients: int = 2
    client_fraction: float = 1.0  # Fraction of clients to select per round
    rounds: int = 10
    aggregation_type: AggregationType = AggregationType.FEDAVG
    model_path: str = ""
    checkpoint_path: str = "./checkpoints"
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_port: int = 9090
    communication_protocol: CommunicationProtocol = CommunicationProtocol.HTTP
    privacy: PrivacyConfig = None
    security: SecurityConfig = None
    
    def __post_init__(self):
        if self.privacy is None:
            self.privacy = PrivacyConfig()
        if self.security is None:
            self.security = SecurityConfig()


@dataclass
class FederatedConfig:
    """Main federated learning configuration."""
    experiment_name: str = "federated_experiment"
    description: str = ""
    client: ClientConfig = None
    server: ServerConfig = None
    
    # Training parameters
    global_model_architecture: str = "neural_network"
    loss_function: str = "categorical_crossentropy"
    optimizer: str = "adam"
    
    # Federated learning parameters
    convergence_threshold: float = 0.001
    max_rounds: int = 100
    patience: int = 5  # Early stopping patience
    
    # Data parameters
    dataset_name: str = "custom"
    num_classes: int = 10
    input_shape: List[int] = None
    
    # Advanced features
    enable_personalization: bool = False
    enable_transfer_learning: bool = False
    enable_meta_learning: bool = False
    enable_asynchronous: bool = False
    
    # Cross-silo configuration
    enable_cross_silo: bool = False
    silo_id: Optional[str] = None
    partner_silos: List[str] = None
    
    def __post_init__(self):
        if self.client is None:
            self.client = ClientConfig(client_id="default_client")
        if self.server is None:
            self.server = ServerConfig()
        if self.input_shape is None:
            self.input_shape = [28, 28, 1]
        if self.partner_silos is None:
            self.partner_silos = []
    
    @classmethod
    def from_file(cls, config_path: str) -> 'FederatedConfig':
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'FederatedConfig':
        """Create configuration from dictionary."""
        # Handle nested configurations
        if 'client' in config_dict:
            client_config = config_dict['client']
            if 'privacy' in client_config:
                client_config['privacy'] = PrivacyConfig(**client_config['privacy'])
            if 'compression' in client_config:
                client_config['compression'] = CompressionConfig(**client_config['compression'])
            config_dict['client'] = ClientConfig(**client_config)
        
        if 'server' in config_dict:
            server_config = config_dict['server']
            if 'privacy' in server_config:
                server_config['privacy'] = PrivacyConfig(**server_config['privacy'])
            if 'security' in server_config:
                server_config['security'] = SecurityConfig(**server_config['security'])
            if 'aggregation_type' in server_config:
                server_config['aggregation_type'] = AggregationType(server_config['aggregation_type'])
            if 'communication_protocol' in server_config:
                server_config['communication_protocol'] = CommunicationProtocol(server_config['communication_protocol'])
            config_dict['server'] = ServerConfig(**server_config)
        
        return cls(**config_dict)
    
    def to_file(self, config_path: str):
        """Save configuration to JSON file."""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config_dict = asdict(self)
        
        # Handle enum serialization
        if 'server' in config_dict and config_dict['server']:
            if 'aggregation_type' in config_dict['server']:
                config_dict['server']['aggregation_type'] = config_dict['server']['aggregation_type'].value
            if 'communication_protocol' in config_dict['server']:
                config_dict['server']['communication_protocol'] = config_dict['server']['communication_protocol'].value
            if 'privacy' in config_dict['server'] and config_dict['server']['privacy']:
                if 'mechanism' in config_dict['server']['privacy']:
                    config_dict['server']['privacy']['mechanism'] = config_dict['server']['privacy']['mechanism'].value
            if 'security' in config_dict['server'] and config_dict['server']['security']:
                pass  # No enums in security config
        
        if 'client' in config_dict and config_dict['client']:
            if 'privacy' in config_dict['client'] and config_dict['client']['privacy']:
                if 'mechanism' in config_dict['client']['privacy']:
                    config_dict['client']['privacy']['mechanism'] = config_dict['client']['privacy']['mechanism'].value
        
        return config_dict
    
    def validate(self) -> bool:
        """Validate configuration parameters."""
        if self.server.min_clients > self.server.max_clients:
            raise ValueError("min_clients cannot be greater than max_clients")
        
        if self.server.client_fraction <= 0 or self.server.client_fraction > 1:
            raise ValueError("client_fraction must be between 0 and 1")
        
        if self.client.local_epochs < 1:
            raise ValueError("local_epochs must be at least 1")
        
        if self.client.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        
        if self.client.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        
        return True


# Default configurations for quick setup
DEFAULT_CONFIG = FederatedConfig(
    experiment_name="default_federated_experiment",
    description="Default federated learning configuration"
)

SECURE_CONFIG = FederatedConfig(
    experiment_name="secure_federated_experiment",
    description="Secure federated learning with differential privacy",
    server=ServerConfig(
        privacy=PrivacyConfig(
            mechanism=PrivacyMechanism.DIFFERENTIAL_PRIVACY,
            epsilon=1.0
        ),
        security=SecurityConfig(
            enable_tls=True,
            authentication_required=True
        )
    )
)

CROSS_SILO_CONFIG = FederatedConfig(
    experiment_name="cross_silo_federated_experiment",
    description="Cross-silo federated learning configuration",
    enable_cross_silo=True,
    server=ServerConfig(
        aggregation_type=AggregationType.SECURE_AGGREGATION,
        privacy=PrivacyConfig(
            mechanism=PrivacyMechanism.SECURE_MULTI_PARTY
        )
    )
)