"""
AGI Reproducibility Platform Manager

Main orchestrator class that coordinates all platform components and provides
a unified interface for AGI research reproducibility operations.
"""

import asyncio
import logging
import sys
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime

from .config import PlatformConfig, get_config
from .exceptions import *
from ..experiment_tracking.tracker import ExperimentTracker
from ..experiment_tracking.versioning import VersionManager
from ..environment_capture.capturer import EnvironmentCapturer
from ..environment_capture.containers import ContainerManager
from ..replay_system.replay_engine import ReplayEngine
from ..replay_system.deterministic_runner import DeterministicRunner
from ..validation.validator import ResultValidator
from ..validation.comparator import ResultComparator
from ..benchmarks.agi_benchmarks import AGIBenchmarkSuite
from ..benchmarks.symbolic_reasoning import SymbolicReasoningBenchmarks
from ..sharing_platform.experiment_package import ExperimentPackage
from ..sharing_platform.peer_review import PeerReviewSystem
from ..formal_verification.theorem_prover import TheoremProver
from ..formal_verification.safety_verifier import SafetyVerifier
from ..hyperon_tools.pln_validator import PLNValidator
from ..hyperon_tools.metta_verifier import MeTTaVerifier
from ..integrations.github_integration import GitHubIntegration
from ..integrations.arxiv_integration import ArXivIntegration
from ..integrations.singularitynet_integration import SingularityNetIntegration


class AGIReproducibilityPlatform:
    """
    Main platform manager that orchestrates all AGI reproducibility components.
    
    This class provides a unified interface for:
    - Experiment tracking and versioning
    - Environment capture and containerization
    - Deterministic replay and validation
    - Benchmark execution and comparison
    - Formal verification and safety checks
    - Peer review and collaboration
    - Integration with external platforms
    """
    
    def __init__(self, config: Optional[PlatformConfig] = None):
        """Initialize the AGI Reproducibility Platform."""
        self.config = config or get_config()
        self.logger = self._setup_logging()
        
        # Initialize core components
        self.experiment_tracker = None
        self.version_manager = None
        self.environment_capturer = None
        self.container_manager = None
        self.replay_engine = None
        self.deterministic_runner = None
        self.result_validator = None
        self.result_comparator = None
        self.benchmark_suite = None
        self.symbolic_benchmarks = None
        self.experiment_package = None
        self.peer_review = None
        self.theorem_prover = None
        self.safety_verifier = None
        self.pln_validator = None
        self.metta_verifier = None
        
        # Integration components
        self.github_integration = None
        self.arxiv_integration = None
        self.singularitynet_integration = None
        
        # Platform state
        self.is_initialized = False
        self.startup_time = datetime.now()
        self.active_experiments: Dict[str, Any] = {}
        self.resource_usage: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize all platform components asynchronously."""
        try:
            self.logger.info("Initializing AGI Reproducibility Platform...")
            
            # Initialize core components
            await self._initialize_core_components()
            
            # Initialize integrations
            await self._initialize_integrations()
            
            # Setup platform directories
            await self._setup_platform_directories()
            
            # Validate platform health
            await self._validate_platform_health()
            
            self.is_initialized = True
            self.logger.info("AGI Reproducibility Platform initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize platform: {str(e)}")
            raise ConfigurationError(f"Platform initialization failed: {str(e)}")
    
    async def _initialize_core_components(self) -> None:
        """Initialize core platform components."""
        # Experiment tracking
        self.experiment_tracker = ExperimentTracker(self.config)
        await self.experiment_tracker.initialize()
        
        self.version_manager = VersionManager(self.config)
        await self.version_manager.initialize()
        
        # Environment capture
        self.environment_capturer = EnvironmentCapturer(self.config)
        await self.environment_capturer.initialize()
        
        self.container_manager = ContainerManager(self.config)
        await self.container_manager.initialize()
        
        # Replay system
        self.replay_engine = ReplayEngine(self.config)
        await self.replay_engine.initialize()
        
        self.deterministic_runner = DeterministicRunner(self.config)
        await self.deterministic_runner.initialize()
        
        # Validation
        self.result_validator = ResultValidator(self.config)
        await self.result_validator.initialize()
        
        self.result_comparator = ResultComparator(self.config)
        await self.result_comparator.initialize()
        
        # Benchmarks
        self.benchmark_suite = AGIBenchmarkSuite(self.config)
        await self.benchmark_suite.initialize()
        
        self.symbolic_benchmarks = SymbolicReasoningBenchmarks(self.config)
        await self.symbolic_benchmarks.initialize()
        
        # Sharing platform
        self.experiment_package = ExperimentPackage(self.config)
        await self.experiment_package.initialize()
        
        self.peer_review = PeerReviewSystem(self.config)
        await self.peer_review.initialize()
        
        # Formal verification
        if self.config.enable_formal_verification:
            self.theorem_prover = TheoremProver(self.config)
            await self.theorem_prover.initialize()
            
            self.safety_verifier = SafetyVerifier(self.config)
            await self.safety_verifier.initialize()
        
        # Hyperon tools
        if self.config.hyperon_path:
            self.pln_validator = PLNValidator(self.config)
            await self.pln_validator.initialize()
            
            self.metta_verifier = MeTTaVerifier(self.config)
            await self.metta_verifier.initialize()
    
    async def _initialize_integrations(self) -> None:
        """Initialize external integrations."""
        # GitHub integration
        if self.config.integrations.github_token:
            self.github_integration = GitHubIntegration(self.config)
            await self.github_integration.initialize()
        
        # arXiv integration
        if self.config.integrations.enable_arxiv_sync:
            self.arxiv_integration = ArXivIntegration(self.config)
            await self.arxiv_integration.initialize()
        
        # SingularityNET integration
        if self.config.integrations.enable_singularitynet:
            self.singularitynet_integration = SingularityNetIntegration(self.config)
            await self.singularitynet_integration.initialize()
    
    async def _setup_platform_directories(self) -> None:
        """Setup required platform directories."""
        directories = [
            self.config.get_full_path(self.config.experiment_path),
            self.config.get_full_path(self.config.benchmark_path),
            self.config.get_full_path(self.config.verification_path),
            self.config.get_full_path(self.config.cache_path),
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {directory}")
    
    async def _validate_platform_health(self) -> None:
        """Validate that all platform components are healthy."""
        health_checks = []
        
        # Check core components
        if self.experiment_tracker:
            health_checks.append(self.experiment_tracker.health_check())
        if self.container_manager:
            health_checks.append(self.container_manager.health_check())
        if self.replay_engine:
            health_checks.append(self.replay_engine.health_check())
        
        # Run all health checks
        results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        failed_checks = [r for r in results if isinstance(r, Exception)]
        if failed_checks:
            raise ConfigurationError(f"Health check failures: {failed_checks}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup platform logging."""
        logger = logging.getLogger("agi_reproducibility")
        logger.setLevel(getattr(logging, self.config.log_level))
        
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    # Experiment Management Methods
    async def create_experiment(self, experiment_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new experiment with tracking and versioning."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Validate experiment ID
            validate_experiment_id(experiment_id)
            
            # Check if experiment already exists
            if await self.experiment_tracker.experiment_exists(experiment_id):
                raise ExperimentAlreadyExistsError(f"Experiment {experiment_id} already exists")
            
            # Create experiment record
            experiment = await self.experiment_tracker.create_experiment(experiment_id, metadata)
            
            # Initialize version control
            version = await self.version_manager.initialize_experiment_versioning(experiment_id)
            
            # Capture initial environment
            environment = await self.environment_capturer.capture_environment(experiment_id)
            
            # Add to active experiments
            self.active_experiments[experiment_id] = {
                'experiment': experiment,
                'version': version,
                'environment': environment,
                'created_at': datetime.now(),
                'status': 'created'
            }
            
            self.logger.info(f"Created experiment: {experiment_id}")
            return experiment
            
        except Exception as e:
            self.logger.error(f"Failed to create experiment {experiment_id}: {str(e)}")
            raise
    
    async def run_experiment(self, experiment_id: str, code_path: str, 
                           parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run an experiment with full reproducibility tracking."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Get experiment info
            if experiment_id not in self.active_experiments:
                experiment = await self.experiment_tracker.get_experiment(experiment_id)
                if not experiment:
                    raise ExperimentNotFoundError(f"Experiment {experiment_id} not found")
            else:
                experiment = self.active_experiments[experiment_id]['experiment']
            
            # Update experiment status
            await self.experiment_tracker.update_experiment_status(experiment_id, 'running')
            
            # Create container for execution
            container = await self.container_manager.create_experiment_container(
                experiment_id, code_path, parameters or {}
            )
            
            # Run experiment in deterministic mode
            results = await self.deterministic_runner.run_experiment(
                container, experiment_id, parameters or {}
            )
            
            # Validate results
            validation_results = await self.result_validator.validate_results(
                experiment_id, results
            )
            
            # Update experiment with results
            await self.experiment_tracker.update_experiment_results(
                experiment_id, results, validation_results
            )
            
            # Update status
            await self.experiment_tracker.update_experiment_status(experiment_id, 'completed')
            
            self.logger.info(f"Completed experiment: {experiment_id}")
            return {
                'experiment_id': experiment_id,
                'results': results,
                'validation': validation_results,
                'status': 'completed'
            }
            
        except Exception as e:
            await self.experiment_tracker.update_experiment_status(experiment_id, 'failed')
            self.logger.error(f"Failed to run experiment {experiment_id}: {str(e)}")
            raise
    
    async def replay_experiment(self, experiment_id: str, version: str = None) -> Dict[str, Any]:
        """Replay an experiment to verify reproducibility."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Get experiment and version info
            experiment = await self.experiment_tracker.get_experiment(experiment_id)
            if not experiment:
                raise ExperimentNotFoundError(f"Experiment {experiment_id} not found")
            
            # Get specific version or latest
            if version:
                experiment_version = await self.version_manager.get_version(experiment_id, version)
            else:
                experiment_version = await self.version_manager.get_latest_version(experiment_id)
            
            # Replay experiment
            replay_results = await self.replay_engine.replay_experiment(
                experiment_id, experiment_version
            )
            
            # Compare with original results
            if experiment.get('results'):
                comparison = await self.result_comparator.compare_results(
                    experiment['results'], replay_results
                )
                
                # Check for non-deterministic behavior
                if not comparison['is_deterministic']:
                    raise NonDeterministicBehaviorError(
                        f"Non-deterministic behavior detected in experiment {experiment_id}"
                    )
            
            self.logger.info(f"Successfully replayed experiment: {experiment_id}")
            return replay_results
            
        except Exception as e:
            self.logger.error(f"Failed to replay experiment {experiment_id}: {str(e)}")
            raise
    
    # Benchmark Methods
    async def run_agi_benchmarks(self, experiment_id: str, 
                                benchmark_types: List[str] = None) -> Dict[str, Any]:
        """Run standardized AGI benchmarks on an experiment."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            benchmark_types = benchmark_types or [
                'symbolic_reasoning',
                'neural_symbolic', 
                'consciousness_metrics',
                'scalability',
                'safety_alignment'
            ]
            
            benchmark_results = {}
            
            # Run each benchmark type
            for benchmark_type in benchmark_types:
                if benchmark_type == 'symbolic_reasoning':
                    result = await self.symbolic_benchmarks.run_benchmark(experiment_id)
                    benchmark_results[benchmark_type] = result
                elif benchmark_type in ['neural_symbolic', 'consciousness_metrics', 
                                      'scalability', 'safety_alignment']:
                    result = await self.benchmark_suite.run_benchmark(experiment_id, benchmark_type)
                    benchmark_results[benchmark_type] = result
            
            # Store benchmark results
            await self.experiment_tracker.update_experiment_benchmarks(
                experiment_id, benchmark_results
            )
            
            self.logger.info(f"Completed benchmarks for experiment: {experiment_id}")
            return benchmark_results
            
        except Exception as e:
            self.logger.error(f"Failed to run benchmarks for {experiment_id}: {str(e)}")
            raise
    
    # Formal Verification Methods
    async def verify_experiment_safety(self, experiment_id: str) -> Dict[str, Any]:
        """Perform formal safety verification on an experiment."""
        if not self.is_initialized:
            await self.initialize()
        
        if not self.safety_verifier:
            raise FormalVerificationError("Safety verifier not initialized")
        
        try:
            # Get experiment code and properties
            experiment = await self.experiment_tracker.get_experiment(experiment_id)
            
            # Run safety verification
            verification_results = await self.safety_verifier.verify_safety(experiment)
            
            # Store verification results
            await self.experiment_tracker.update_experiment_verification(
                experiment_id, verification_results
            )
            
            self.logger.info(f"Completed safety verification for: {experiment_id}")
            return verification_results
            
        except Exception as e:
            self.logger.error(f"Failed to verify safety for {experiment_id}: {str(e)}")
            raise
    
    # Hyperon/PRIMUS Methods
    async def validate_pln_rules(self, experiment_id: str) -> Dict[str, Any]:
        """Validate PLN rules in a Hyperon experiment."""
        if not self.is_initialized:
            await self.initialize()
        
        if not self.pln_validator:
            raise HyperonError("PLN validator not initialized")
        
        try:
            # Get experiment with PLN rules
            experiment = await self.experiment_tracker.get_experiment(experiment_id)
            
            # Validate PLN rules
            validation_results = await self.pln_validator.validate_rules(experiment)
            
            self.logger.info(f"Completed PLN validation for: {experiment_id}")
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Failed to validate PLN rules for {experiment_id}: {str(e)}")
            raise
    
    async def verify_metta_code(self, experiment_id: str) -> Dict[str, Any]:
        """Verify MeTTa code correctness."""
        if not self.is_initialized:
            await self.initialize()
        
        if not self.metta_verifier:
            raise HyperonError("MeTTa verifier not initialized")
        
        try:
            # Get experiment with MeTTa code
            experiment = await self.experiment_tracker.get_experiment(experiment_id)
            
            # Verify MeTTa code
            verification_results = await self.metta_verifier.verify_code(experiment)
            
            self.logger.info(f"Completed MeTTa verification for: {experiment_id}")
            return verification_results
            
        except Exception as e:
            self.logger.error(f"Failed to verify MeTTa code for {experiment_id}: {str(e)}")
            raise
    
    # Sharing and Collaboration Methods
    async def package_experiment(self, experiment_id: str, 
                                include_data: bool = True) -> Dict[str, Any]:
        """Package experiment for sharing."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Create experiment package
            package = await self.experiment_package.create_package(
                experiment_id, include_data
            )
            
            self.logger.info(f"Created package for experiment: {experiment_id}")
            return package
            
        except Exception as e:
            self.logger.error(f"Failed to package experiment {experiment_id}: {str(e)}")
            raise
    
    async def submit_for_peer_review(self, experiment_id: str, 
                                   reviewers: List[str] = None) -> Dict[str, Any]:
        """Submit experiment for peer review."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Submit for review
            review_request = await self.peer_review.submit_for_review(
                experiment_id, reviewers
            )
            
            self.logger.info(f"Submitted experiment for review: {experiment_id}")
            return review_request
            
        except Exception as e:
            self.logger.error(f"Failed to submit for review {experiment_id}: {str(e)}")
            raise
    
    # Platform Status and Monitoring
    async def get_platform_status(self) -> Dict[str, Any]:
        """Get current platform status and health."""
        return {
            'platform_name': self.config.platform_name,
            'version': self.config.version,
            'initialized': self.is_initialized,
            'startup_time': self.startup_time.isoformat(),
            'active_experiments': len(self.active_experiments),
            'components': {
                'experiment_tracker': self.experiment_tracker is not None,
                'container_manager': self.container_manager is not None,
                'replay_engine': self.replay_engine is not None,
                'benchmark_suite': self.benchmark_suite is not None,
                'theorem_prover': self.theorem_prover is not None,
                'pln_validator': self.pln_validator is not None,
            },
            'integrations': {
                'github': self.github_integration is not None,
                'arxiv': self.arxiv_integration is not None,
                'singularitynet': self.singularitynet_integration is not None,
            },
            'resource_usage': self.resource_usage
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the platform."""
        self.logger.info("Shutting down AGI Reproducibility Platform...")
        
        # Stop active experiments
        for experiment_id in self.active_experiments:
            try:
                await self.experiment_tracker.update_experiment_status(
                    experiment_id, 'interrupted'
                )
            except Exception as e:
                self.logger.error(f"Error stopping experiment {experiment_id}: {e}")
        
        # Cleanup components
        cleanup_tasks = []
        if self.container_manager:
            cleanup_tasks.append(self.container_manager.cleanup())
        if self.replay_engine:
            cleanup_tasks.append(self.replay_engine.cleanup())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.is_initialized = False
        self.logger.info("Platform shutdown complete")


# Global platform instance
_platform_instance: Optional[AGIReproducibilityPlatform] = None

def get_platform(config: Optional[PlatformConfig] = None) -> AGIReproducibilityPlatform:
    """Get the global platform instance."""
    global _platform_instance
    if _platform_instance is None:
        _platform_instance = AGIReproducibilityPlatform(config)
    return _platform_instance

async def initialize_platform(config: Optional[PlatformConfig] = None) -> AGIReproducibilityPlatform:
    """Initialize the global platform instance."""
    platform = get_platform(config)
    if not platform.is_initialized:
        await platform.initialize()
    return platform