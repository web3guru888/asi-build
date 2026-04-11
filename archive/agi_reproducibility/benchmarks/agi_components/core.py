"""
Core classes for the AGI Component Benchmark Suite
"""

import time
import logging
import traceback
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os

from .config import BenchmarkConfig


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test"""
    benchmark_name: str
    test_name: str
    score: float
    max_score: float
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def normalized_score(self) -> float:
        """Get normalized score (0-1)"""
        if self.max_score == 0:
            return 0.0
        return self.score / self.max_score
    
    @property
    def percentage_score(self) -> float:
        """Get percentage score (0-100)"""
        return self.normalized_score * 100.0


@dataclass
class BenchmarkSuiteResult:
    """Results from running the full benchmark suite"""
    system_name: str
    system_version: str
    config_hash: str
    start_time: datetime
    end_time: datetime
    results: List[BenchmarkResult] = field(default_factory=list)
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_execution_time(self) -> float:
        """Total execution time in seconds"""
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful tests"""
        if not self.results:
            return 0.0
        successful = sum(1 for r in self.results if r.success)
        return (successful / len(self.results)) * 100.0
    
    @property
    def average_score(self) -> float:
        """Average normalized score across all tests"""
        if not self.results:
            return 0.0
        successful_results = [r for r in self.results if r.success]
        if not successful_results:
            return 0.0
        return sum(r.normalized_score for r in successful_results) / len(successful_results)
    
    def get_category_results(self, category: str) -> List[BenchmarkResult]:
        """Get results for specific benchmark category"""
        return [r for r in self.results if r.benchmark_name.startswith(category)]
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return {
            "total_tests": len(self.results),
            "successful_tests": sum(1 for r in self.results if r.success),
            "success_rate": self.success_rate,
            "average_score": self.average_score,
            "total_time": self.total_execution_time,
            "average_test_time": sum(r.execution_time for r in self.results) / len(self.results) if self.results else 0
        }


class AGISystem(ABC):
    """Abstract base class for AGI systems to be benchmarked"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.initialized = False
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the AGI system"""
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """Shutdown the AGI system"""
        pass
    
    @abstractmethod
    def process_reasoning_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a reasoning task"""
        pass
    
    @abstractmethod
    def process_learning_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a learning task"""
        pass
    
    @abstractmethod
    def process_memory_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a memory task"""
        pass
    
    @abstractmethod
    def process_creativity_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a creativity task"""
        pass
    
    @abstractmethod
    def process_consciousness_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a consciousness task"""
        pass
    
    @abstractmethod
    def process_symbolic_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a symbolic reasoning task"""
        pass
    
    @abstractmethod
    def process_neural_symbolic_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a neural-symbolic integration task"""
        pass
    
    @abstractmethod
    def process_real_world_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a real-world challenge task"""
        pass
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get information about the system"""
        return {
            "name": self.name,
            "version": self.version,
            "initialized": self.initialized
        }


class BaseBenchmark(ABC):
    """Base class for all benchmarks"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"benchmark.{name}")
    
    @abstractmethod
    def run_tests(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run all tests in this benchmark category"""
        pass
    
    def _create_result(self, test_name: str, score: float, max_score: float, 
                      execution_time: float, success: bool, error_message: str = None,
                      details: Dict[str, Any] = None) -> BenchmarkResult:
        """Helper to create benchmark result"""
        return BenchmarkResult(
            benchmark_name=self.name,
            test_name=test_name,
            score=score,
            max_score=max_score,
            execution_time=execution_time,
            success=success,
            error_message=error_message,
            details=details or {}
        )
    
    def _run_single_test(self, test_func, test_name: str, system: AGISystem, 
                        max_score: float = 1.0) -> BenchmarkResult:
        """Run a single test with error handling and timing"""
        start_time = time.time()
        try:
            result = test_func(system)
            execution_time = time.time() - start_time
            
            if isinstance(result, dict):
                score = result.get("score", 0.0)
                details = result.get("details", {})
                success = result.get("success", score > 0)
            else:
                score = float(result) if result is not None else 0.0
                details = {}
                success = score > 0
            
            return self._create_result(
                test_name=test_name,
                score=score,
                max_score=max_score,
                execution_time=execution_time,
                success=success,
                details=details
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Test {test_name} failed: {str(e)}")
            return self._create_result(
                test_name=test_name,
                score=0.0,
                max_score=max_score,
                execution_time=execution_time,
                success=False,
                error_message=str(e),
                details={"traceback": traceback.format_exc()}
            )


class BenchmarkRunner:
    """Main runner for the AGI benchmark suite"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.logger = logging.getLogger("benchmark_runner")
        self._setup_logging()
        
        # Initialize benchmark categories
        self.benchmarks = {}
        self._initialize_benchmarks()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        level = getattr(logging, self.config.log_level.upper())
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.config.output_dir, "benchmark.log")),
                logging.StreamHandler()
            ]
        )
    
    def _initialize_benchmarks(self):
        """Initialize all benchmark categories"""
        from .reasoning import ReasoningBenchmarks
        from .learning import LearningBenchmarks
        from .memory import MemoryBenchmarks
        from .creativity import CreativityBenchmarks
        from .consciousness import ConsciousnessBenchmarks
        from .symbolic import SymbolicAIBenchmarks
        from .neural_symbolic import NeuralSymbolicBenchmarks
        from .real_world import RealWorldAGIChallenges
        
        if self.config.run_reasoning:
            self.benchmarks["reasoning"] = ReasoningBenchmarks("reasoning", self.config.reasoning_config)
        if self.config.run_learning:
            self.benchmarks["learning"] = LearningBenchmarks("learning", self.config.learning_config)
        if self.config.run_memory:
            self.benchmarks["memory"] = MemoryBenchmarks("memory", self.config.memory_config)
        if self.config.run_creativity:
            self.benchmarks["creativity"] = CreativityBenchmarks("creativity", self.config.creativity_config)
        if self.config.run_consciousness:
            self.benchmarks["consciousness"] = ConsciousnessBenchmarks("consciousness", self.config.consciousness_config)
        if self.config.run_symbolic:
            self.benchmarks["symbolic"] = SymbolicAIBenchmarks("symbolic", self.config.symbolic_config)
        if self.config.run_neural_symbolic:
            self.benchmarks["neural_symbolic"] = NeuralSymbolicBenchmarks("neural_symbolic", self.config.neural_symbolic_config)
        if self.config.run_real_world:
            self.benchmarks["real_world"] = RealWorldAGIChallenges("real_world", self.config.real_world_config)
    
    def run_benchmarks(self, system: AGISystem) -> BenchmarkSuiteResult:
        """Run all enabled benchmarks on the given AGI system"""
        self.logger.info(f"Starting benchmark suite for system: {system.name} v{system.version}")
        
        start_time = datetime.now()
        all_results = []
        
        # Initialize system
        if not system.initialized:
            system.initialize({})
        
        try:
            # Run benchmarks in parallel if configured
            if self.config.max_workers > 1:
                all_results = self._run_benchmarks_parallel(system)
            else:
                all_results = self._run_benchmarks_sequential(system)
        
        finally:
            # Shutdown system
            system.shutdown()
        
        end_time = datetime.now()
        
        # Create suite result
        suite_result = BenchmarkSuiteResult(
            system_name=system.name,
            system_version=system.version,
            config_hash=hash(str(self.config)),
            start_time=start_time,
            end_time=end_time,
            results=all_results,
            system_info=system.get_system_info()
        )
        
        self.logger.info(f"Benchmark suite completed. Success rate: {suite_result.success_rate:.1f}%")
        self.logger.info(f"Average score: {suite_result.average_score:.3f}")
        
        return suite_result
    
    def _run_benchmarks_sequential(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run benchmarks sequentially"""
        all_results = []
        
        for category_name, benchmark in self.benchmarks.items():
            self.logger.info(f"Running {category_name} benchmarks...")
            try:
                results = benchmark.run_tests(system)
                all_results.extend(results)
                self.logger.info(f"Completed {category_name}: {len(results)} tests")
            except Exception as e:
                self.logger.error(f"Failed to run {category_name} benchmarks: {str(e)}")
        
        return all_results
    
    def _run_benchmarks_parallel(self, system: AGISystem) -> List[BenchmarkResult]:
        """Run benchmarks in parallel"""
        all_results = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit benchmark tasks
            future_to_category = {
                executor.submit(benchmark.run_tests, system): category_name
                for category_name, benchmark in self.benchmarks.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_category):
                category_name = future_to_category[future]
                try:
                    results = future.result(timeout=self.config.timeout_seconds)
                    all_results.extend(results)
                    self.logger.info(f"Completed {category_name}: {len(results)} tests")
                except Exception as e:
                    self.logger.error(f"Failed to run {category_name} benchmarks: {str(e)}")
        
        return all_results
    
    def save_results(self, suite_result: BenchmarkSuiteResult, filename: str = None) -> str:
        """Save benchmark results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{suite_result.system_name}_{timestamp}.json"
        
        filepath = os.path.join(self.config.output_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Convert results to serializable format
        results_dict = {
            "system_name": suite_result.system_name,
            "system_version": suite_result.system_version,
            "config_hash": suite_result.config_hash,
            "start_time": suite_result.start_time.isoformat(),
            "end_time": suite_result.end_time.isoformat(),
            "system_info": suite_result.system_info,
            "summary": suite_result.get_summary_stats(),
            "results": [
                {
                    "benchmark_name": r.benchmark_name,
                    "test_name": r.test_name,
                    "score": r.score,
                    "max_score": r.max_score,
                    "normalized_score": r.normalized_score,
                    "execution_time": r.execution_time,
                    "success": r.success,
                    "error_message": r.error_message,
                    "details": r.details,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in suite_result.results
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        self.logger.info(f"Results saved to: {filepath}")
        return filepath


class AGIBenchmarkSuite:
    """Main interface for the AGI Benchmark Suite"""
    
    def __init__(self, config: BenchmarkConfig = None):
        self.config = config or BenchmarkConfig()
        self.runner = BenchmarkRunner(self.config)
        
        # Validate configuration
        issues = self.config.validate_config()
        if issues:
            raise ValueError(f"Configuration validation failed: {issues}")
        
        # Create output directory
        os.makedirs(self.config.output_dir, exist_ok=True)
    
    def benchmark_system(self, system: AGISystem, save_results: bool = True) -> BenchmarkSuiteResult:
        """Benchmark an AGI system and optionally save results"""
        results = self.runner.run_benchmarks(system)
        
        if save_results:
            self.runner.save_results(results)
        
        return results
    
    def load_results(self, filepath: str) -> Dict[str, Any]:
        """Load benchmark results from file"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def compare_systems(self, result_files: List[str]) -> Dict[str, Any]:
        """Compare results from multiple systems"""
        from .analysis import BenchmarkAnalyzer
        analyzer = BenchmarkAnalyzer()
        
        all_results = []
        for filepath in result_files:
            results = self.load_results(filepath)
            all_results.append(results)
        
        return analyzer.compare_results(all_results)