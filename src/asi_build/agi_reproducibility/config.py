"""
Platform Configuration Management

Centralized configuration system for the AGI Reproducibility Platform.
Handles all platform settings, paths, and environment variables.
"""

import json
import os
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class StorageBackend(Enum):
    """Storage backend options for experiment data."""

    LOCAL = "local"
    S3 = "s3"
    IPFS = "ipfs"
    ARWEAVE = "arweave"
    SINGULARITYNET = "singularitynet"


class ContainerRuntime(Enum):
    """Container runtime options."""

    DOCKER = "docker"
    PODMAN = "podman"
    SINGULARITY = "singularity"
    KUBERNETES = "kubernetes"


class ReplicationTarget(Enum):
    """Hardware targets for replication."""

    CPU_X86 = "cpu_x86"
    CPU_ARM = "cpu_arm"
    GPU_NVIDIA = "gpu_nvidia"
    GPU_AMD = "gpu_amd"
    TPU_GOOGLE = "tpu_google"
    QUANTUM_IBM = "quantum_ibm"
    NEUROMORPHIC = "neuromorphic"
    CUSTOM = "custom"


@dataclass
class DatabaseConfig:
    """Database configuration."""

    host: str = "localhost"
    port: int = 5432
    name: str = "agi_reproducibility"
    username: str = "agi_user"
    password: str = "agi_password"
    driver: str = "postgresql"

    def connection_string(self) -> str:
        """Generate database connection string."""
        return (
            f"{self.driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"
        )


@dataclass
class StorageConfig:
    """Storage configuration."""

    backend: StorageBackend = StorageBackend.LOCAL
    local_path: str = "/data/agi_experiments"
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    ipfs_node: Optional[str] = None
    arweave_wallet: Optional[str] = None
    singularitynet_endpoint: Optional[str] = None
    encryption_enabled: bool = True
    compression_enabled: bool = True
    max_file_size: int = 10 * 1024 * 1024 * 1024  # 10GB


@dataclass
class ContainerConfig:
    """Container runtime configuration."""

    runtime: ContainerRuntime = ContainerRuntime.DOCKER
    registry: str = "docker.io"
    namespace: str = "agi-reproducibility"
    resource_limits: Dict[str, str] = None
    network_isolation: bool = True
    security_constraints: Dict[str, Any] = None

    def __post_init__(self):
        if self.resource_limits is None:
            self.resource_limits = {"memory": "8Gi", "cpu": "4", "gpu": "1"}
        if self.security_constraints is None:
            self.security_constraints = {
                "read_only": True,
                "no_new_privileges": True,
                "drop_capabilities": ["ALL"],
            }


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""

    symbolic_reasoning_timeout: int = 3600  # 1 hour
    neural_symbolic_timeout: int = 7200  # 2 hours
    consciousness_metrics_timeout: int = 1800  # 30 minutes
    scalability_max_agents: int = 10000
    safety_verification_timeout: int = 14400  # 4 hours
    performance_tolerance: float = 0.05  # 5% tolerance
    statistical_significance: float = 0.05
    min_replication_runs: int = 10


@dataclass
class IntegrationConfig:
    """External integration configuration."""

    github_token: Optional[str] = None
    gitlab_token: Optional[str] = None
    arxiv_api_key: Optional[str] = None
    singularitynet_private_key: Optional[str] = None
    hyperon_endpoint: Optional[str] = None
    opencog_endpoint: Optional[str] = None
    enable_arxiv_sync: bool = True
    enable_git_sync: bool = True
    enable_singularitynet: bool = False


@dataclass
class SecurityConfig:
    """Security configuration."""

    enable_sandbox: bool = True
    max_execution_time: int = 86400  # 24 hours
    allowed_network_domains: List[str] = None
    blocked_system_calls: List[str] = None
    enable_code_signing: bool = True
    require_peer_review: bool = True
    min_reviewers: int = 2

    def __post_init__(self):
        if self.allowed_network_domains is None:
            self.allowed_network_domains = [
                "github.com",
                "gitlab.com",
                "arxiv.org",
                "pypi.org",
                "docker.io",
                "singularitynet.io",
            ]
        if self.blocked_system_calls is None:
            self.blocked_system_calls = ["ptrace", "mount", "umount", "reboot", "syslog"]


@dataclass
class PlatformConfig:
    """Main platform configuration."""

    # Core settings
    platform_name: str = "AGI Reproducibility Platform"
    version: str = "1.0.0"
    debug_mode: bool = False
    log_level: str = "INFO"

    # Component configurations
    database: DatabaseConfig = DatabaseConfig()
    storage: StorageConfig = StorageConfig()
    containers: ContainerConfig = ContainerConfig()
    benchmarks: BenchmarkConfig = BenchmarkConfig()
    integrations: IntegrationConfig = IntegrationConfig()
    security: SecurityConfig = SecurityConfig()

    # Platform paths
    base_path: str = "/opt/agi_reproducibility"
    experiment_path: str = "experiments"
    benchmark_path: str = "benchmarks"
    verification_path: str = "verification"
    cache_path: str = "cache"

    # Replication targets
    replication_targets: List[ReplicationTarget] = None

    # Formal verification
    enable_formal_verification: bool = True
    theorem_prover_timeout: int = 3600

    # Hyperon/PRIMUS specific
    hyperon_path: Optional[str] = None
    metta_interpreter: str = "hyperon"
    pln_inference_timeout: int = 1800
    atomspace_max_size: int = 1000000

    def __post_init__(self):
        if self.replication_targets is None:
            self.replication_targets = [
                ReplicationTarget.CPU_X86,
                ReplicationTarget.GPU_NVIDIA,
                ReplicationTarget.CPU_ARM,
            ]

    @classmethod
    def load_from_file(cls, config_path: str) -> "PlatformConfig":
        """Load configuration from file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path, "r") as f:
            if path.suffix.lower() == ".json":
                config_data = json.load(f)
            elif path.suffix.lower() in [".yml", ".yaml"]:
                config_data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {path.suffix}")

        return cls(**config_data)

    def save_to_file(self, config_path: str) -> None:
        """Save configuration to file."""
        path = Path(config_path)
        config_data = asdict(self)

        with open(path, "w") as f:
            if path.suffix.lower() == ".json":
                json.dump(config_data, f, indent=2, default=str)
            elif path.suffix.lower() in [".yml", ".yaml"]:
                yaml.dump(config_data, f, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported configuration file format: {path.suffix}")

    def get_full_path(self, relative_path: str) -> str:
        """Get full path from relative path."""
        return os.path.join(self.base_path, relative_path)

    def get_experiment_path(self, experiment_id: str) -> str:
        """Get path for specific experiment."""
        return os.path.join(self.base_path, self.experiment_path, experiment_id)

    def validate(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []

        # Validate paths
        if not os.path.isabs(self.base_path):
            errors.append("base_path must be an absolute path")

        # Validate database config
        if not self.database.host:
            errors.append("database.host cannot be empty")

        if self.database.port < 1 or self.database.port > 65535:
            errors.append("database.port must be between 1 and 65535")

        # Validate storage config
        if self.storage.backend == StorageBackend.S3:
            if not self.storage.s3_bucket:
                errors.append("s3_bucket is required when using S3 backend")

        # Validate security config
        if self.security.min_reviewers < 1:
            errors.append("security.min_reviewers must be at least 1")

        # Validate benchmark config
        if self.benchmarks.scalability_max_agents < 1:
            errors.append("benchmarks.scalability_max_agents must be positive")

        return errors


class ConfigManager:
    """Configuration manager singleton."""

    _instance: Optional["ConfigManager"] = None
    _config: Optional[PlatformConfig] = None

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_config(self, config_path: Optional[str] = None) -> PlatformConfig:
        """Load configuration from file or environment."""
        if config_path:
            self._config = PlatformConfig.load_from_file(config_path)
        else:
            # Try to load from environment variable
            env_config_path = os.environ.get("AGI_REPRODUCIBILITY_CONFIG")
            if env_config_path:
                self._config = PlatformConfig.load_from_file(env_config_path)
            else:
                # Use default configuration
                self._config = PlatformConfig()

        # Override with environment variables
        self._apply_env_overrides()

        # Validate configuration
        errors = self._config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

        return self._config

    def get_config(self) -> PlatformConfig:
        """Get current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        if not self._config:
            return

        # Database overrides
        if os.environ.get("DB_HOST"):
            self._config.database.host = os.environ["DB_HOST"]
        if os.environ.get("DB_PORT"):
            self._config.database.port = int(os.environ["DB_PORT"])
        if os.environ.get("DB_NAME"):
            self._config.database.name = os.environ["DB_NAME"]
        if os.environ.get("DB_USER"):
            self._config.database.username = os.environ["DB_USER"]
        if os.environ.get("DB_PASSWORD"):
            self._config.database.password = os.environ["DB_PASSWORD"]

        # Storage overrides
        if os.environ.get("STORAGE_BACKEND"):
            self._config.storage.backend = StorageBackend(os.environ["STORAGE_BACKEND"])
        if os.environ.get("S3_BUCKET"):
            self._config.storage.s3_bucket = os.environ["S3_BUCKET"]
        if os.environ.get("S3_REGION"):
            self._config.storage.s3_region = os.environ["S3_REGION"]

        # Integration overrides
        if os.environ.get("GITHUB_TOKEN"):
            self._config.integrations.github_token = os.environ["GITHUB_TOKEN"]
        if os.environ.get("GITLAB_TOKEN"):
            self._config.integrations.gitlab_token = os.environ["GITLAB_TOKEN"]
        if os.environ.get("ARXIV_API_KEY"):
            self._config.integrations.arxiv_api_key = os.environ["ARXIV_API_KEY"]
        if os.environ.get("SINGULARITYNET_PRIVATE_KEY"):
            self._config.integrations.singularitynet_private_key = os.environ[
                "SINGULARITYNET_PRIVATE_KEY"
            ]

        # Debug mode override
        if os.environ.get("DEBUG"):
            self._config.debug_mode = os.environ["DEBUG"].lower() in ["true", "1", "yes"]


# Global configuration instance
config_manager = ConfigManager()


def get_config() -> PlatformConfig:
    """Get the global platform configuration."""
    return config_manager.get_config()


def load_config(config_path: str) -> PlatformConfig:
    """Load configuration from specified path."""
    return config_manager.load_config(config_path)
