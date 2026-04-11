"""
Optimization techniques for homomorphic encryption operations.
"""

import numpy as np
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
import logging

from .parameters import FHEParameters
from .encryption import Ciphertext, Plaintext
from .polynomial import Polynomial

logger = logging.getLogger(__name__)


@dataclass
class OptimizationProfile:
    """Profile for optimization settings and metrics."""
    enable_ntt_optimization: bool = True
    enable_lazy_relinearization: bool = True
    enable_ciphertext_packing: bool = True
    enable_operation_batching: bool = True
    memory_constraint_mb: Optional[float] = None
    time_constraint_seconds: Optional[float] = None


class OptimizationEngine:
    """
    Optimization engine for homomorphic encryption operations.
    
    Provides various optimization techniques including NTT acceleration,
    lazy evaluation, operation batching, and memory management.
    """
    
    def __init__(self, parameters: FHEParameters, profile: OptimizationProfile = None):
        """
        Initialize the optimization engine.
        
        Args:
            parameters: FHE parameters
            profile: Optimization profile
        """
        self.parameters = parameters
        self.profile = profile or OptimizationProfile()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Operation cache
        self.operation_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Lazy evaluation queue
        self.lazy_queue = []
        self.relinearization_threshold = 5  # Number of operations before forced relin
        
        # Batching state
        self.pending_operations = []
        self.batch_size = 100
        
        # Performance tracking
        self.operation_times = {}
        self.memory_usage = {}
    
    def optimize_ntt_operations(self, polynomials: List[Polynomial]) -> List[Polynomial]:
        """
        Optimize polynomial operations using NTT.
        
        Args:
            polynomials: List of polynomials to optimize
        
        Returns:
            NTT-optimized polynomials
        """
        if not self.profile.enable_ntt_optimization:
            return polynomials
        
        try:
            optimized = []
            
            for poly in polynomials:
                # Convert to NTT form for faster operations
                ntt_coeffs = poly.ring.to_ntt_form(poly.coefficients)
                
                # Create optimized polynomial representation
                optimized_poly = Polynomial(ntt_coeffs, poly.ring)
                optimized_poly._is_ntt_form = True
                optimized.append(optimized_poly)
            
            self.logger.debug(f"Converted {len(polynomials)} polynomials to NTT form")
            return optimized
            
        except Exception as e:
            self.logger.warning(f"NTT optimization failed: {e}, using standard form")
            return polynomials
    
    def lazy_relinearization_manager(self, ciphertext: Ciphertext, 
                                   force_relinearize: bool = False) -> Ciphertext:
        """
        Manage lazy relinearization to reduce computational overhead.
        
        Args:
            ciphertext: Input ciphertext
            force_relinearize: Force immediate relinearization
        
        Returns:
            Potentially relinearized ciphertext
        """
        if not self.profile.enable_lazy_relinearization:
            # Always relinearize immediately
            from .evaluation import Evaluator
            evaluator = Evaluator(self.parameters)
            return evaluator.relinearize(ciphertext)
        
        # Add to lazy queue
        self.lazy_queue.append(ciphertext)
        
        # Check if we should relinearize now
        should_relinearize = (
            force_relinearize or
            len(self.lazy_queue) >= self.relinearization_threshold or
            ciphertext.size > 3  # Don't let size grow too large
        )
        
        if should_relinearize:
            return self._flush_lazy_relinearization()
        
        return ciphertext
    
    def _flush_lazy_relinearization(self) -> Ciphertext:
        """Flush the lazy relinearization queue."""
        if not self.lazy_queue:
            return None
        
        from .evaluation import Evaluator
        evaluator = Evaluator(self.parameters)
        
        # Relinearize all pending ciphertexts
        result = self.lazy_queue[-1]  # Take the most recent
        result = evaluator.relinearize(result)
        
        self.lazy_queue.clear()
        self.logger.debug("Flushed lazy relinearization queue")
        
        return result
    
    def batch_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """
        Batch multiple operations for improved efficiency.
        
        Args:
            operations: List of operation descriptions
        
        Returns:
            Results of batched operations
        """
        if not self.profile.enable_operation_batching:
            # Execute operations individually
            return [self._execute_single_operation(op) for op in operations]
        
        # Group operations by type
        operation_groups = {}
        for i, op in enumerate(operations):
            op_type = op.get("type", "unknown")
            if op_type not in operation_groups:
                operation_groups[op_type] = []
            operation_groups[op_type].append((i, op))
        
        # Execute batched operations
        results = [None] * len(operations)
        
        for op_type, ops in operation_groups.items():
            if op_type == "add":
                batch_results = self._batch_add_operations(ops)
            elif op_type == "multiply":
                batch_results = self._batch_multiply_operations(ops)
            else:
                # Execute individually for unknown types
                batch_results = [self._execute_single_operation(op[1]) for op in ops]
            
            # Place results in correct positions
            for (original_index, _), result in zip(ops, batch_results):
                results[original_index] = result
        
        return results
    
    def _batch_add_operations(self, operations: List[Tuple[int, Dict]]) -> List[Ciphertext]:
        """Batch addition operations."""
        results = []
        
        # Group by compatible ciphertexts
        for _, op in operations:
            # For now, execute individually
            # In practice, would optimize for vectorized operations
            result = self._execute_single_operation(op)
            results.append(result)
        
        return results
    
    def _batch_multiply_operations(self, operations: List[Tuple[int, Dict]]) -> List[Ciphertext]:
        """Batch multiplication operations."""
        results = []
        
        for _, op in operations:
            # Optimize multiplication with NTT if possible
            result = self._execute_single_operation(op)
            results.append(result)
        
        return results
    
    def _execute_single_operation(self, operation: Dict[str, Any]) -> Any:
        """Execute a single operation."""
        op_type = operation.get("type")
        
        # This would interface with the actual evaluator
        # For now, return a placeholder
        return f"Result of {op_type} operation"
    
    def optimize_memory_usage(self, ciphertexts: List[Ciphertext]) -> List[Ciphertext]:
        """
        Optimize memory usage through compression and smart allocation.
        
        Args:
            ciphertexts: List of ciphertexts to optimize
        
        Returns:
            Memory-optimized ciphertexts
        """
        if not self.profile.memory_constraint_mb:
            return ciphertexts  # No constraint
        
        # Estimate current memory usage
        current_usage = self._estimate_memory_usage(ciphertexts)
        
        if current_usage <= self.profile.memory_constraint_mb:
            return ciphertexts  # Within constraint
        
        # Apply memory optimizations
        optimized = []
        
        for ct in ciphertexts:
            # Convert to compressed representation if possible
            compressed_ct = self._compress_ciphertext(ct)
            optimized.append(compressed_ct)
        
        final_usage = self._estimate_memory_usage(optimized)
        self.logger.info(f"Memory optimization: {current_usage:.1f}MB -> {final_usage:.1f}MB")
        
        return optimized
    
    def _estimate_memory_usage(self, ciphertexts: List[Ciphertext]) -> float:
        """Estimate memory usage in MB."""
        total_bytes = 0
        
        for ct in ciphertexts:
            # Estimate polynomial storage
            for poly in ct.polynomials:
                # 8 bytes per coefficient (64-bit)
                poly_bytes = len(poly.coefficients) * 8
                total_bytes += poly_bytes
        
        return total_bytes / (1024 * 1024)  # Convert to MB
    
    def _compress_ciphertext(self, ciphertext: Ciphertext) -> Ciphertext:
        """Compress a ciphertext representation."""
        # Placeholder for compression techniques
        # Could include coefficient packing, sparse representation, etc.
        return ciphertext
    
    def cache_operation_result(self, operation_key: str, result: Any) -> None:
        """
        Cache the result of an expensive operation.
        
        Args:
            operation_key: Unique key for the operation
            result: Operation result to cache
        """
        # Implement size-limited LRU cache
        max_cache_size = 1000
        
        if len(self.operation_cache) >= max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.operation_cache))
            del self.operation_cache[oldest_key]
        
        self.operation_cache[operation_key] = {
            "result": result,
            "timestamp": time.time()
        }
    
    def get_cached_result(self, operation_key: str) -> Optional[Any]:
        """
        Retrieve a cached operation result.
        
        Args:
            operation_key: Operation key to look up
        
        Returns:
            Cached result if available, None otherwise
        """
        if operation_key in self.operation_cache:
            self.cache_hits += 1
            return self.operation_cache[operation_key]["result"]
        
        self.cache_misses += 1
        return None
    
    def optimize_circuit_evaluation(self, circuit: List[Dict], 
                                   inputs: Dict[str, Ciphertext]) -> Dict[str, Ciphertext]:
        """
        Optimize the evaluation of a computation circuit.
        
        Args:
            circuit: List of operation descriptions
            inputs: Input ciphertexts
        
        Returns:
            Circuit evaluation results
        """
        # Analyze circuit for optimization opportunities
        analysis = self._analyze_circuit(circuit)
        
        # Apply optimizations based on analysis
        optimized_circuit = self._optimize_circuit_structure(circuit, analysis)
        
        # Execute optimized circuit
        return self._execute_optimized_circuit(optimized_circuit, inputs)
    
    def _analyze_circuit(self, circuit: List[Dict]) -> Dict[str, Any]:
        """Analyze circuit structure for optimization opportunities."""
        analysis = {
            "total_operations": len(circuit),
            "operation_types": {},
            "dependency_graph": {},
            "critical_path_length": 0,
            "parallelizable_ops": []
        }
        
        # Count operation types
        for op in circuit:
            op_type = op.get("type", "unknown")
            analysis["operation_types"][op_type] = analysis["operation_types"].get(op_type, 0) + 1
        
        # Build dependency graph
        for i, op in enumerate(circuit):
            inputs = op.get("inputs", [])
            analysis["dependency_graph"][i] = inputs
        
        # Find parallelizable operations
        analysis["parallelizable_ops"] = self._find_parallelizable_operations(circuit)
        
        return analysis
    
    def _find_parallelizable_operations(self, circuit: List[Dict]) -> List[List[int]]:
        """Find groups of operations that can be executed in parallel."""
        # Simplified implementation - would use topological sorting in practice
        parallel_groups = []
        
        # Group operations that don't depend on each other
        independent_ops = []
        for i, op in enumerate(circuit):
            inputs = op.get("inputs", [])
            if not any(inp.startswith("temp_") for inp in inputs):
                independent_ops.append(i)
        
        if independent_ops:
            parallel_groups.append(independent_ops)
        
        return parallel_groups
    
    def _optimize_circuit_structure(self, circuit: List[Dict], 
                                   analysis: Dict[str, Any]) -> List[Dict]:
        """Optimize circuit structure based on analysis."""
        optimized = circuit.copy()
        
        # Reorder operations to minimize relinearizations
        if analysis["operation_types"].get("multiply", 0) > 1:
            optimized = self._minimize_relinearizations(optimized)
        
        # Insert rescaling operations for CKKS
        if self.parameters.scheme_type.value == "CKKS":
            optimized = self._insert_optimal_rescaling(optimized)
        
        return optimized
    
    def _minimize_relinearizations(self, circuit: List[Dict]) -> List[Dict]:
        """Minimize the number of relinearization operations."""
        # Group consecutive multiplications to reduce relinearizations
        optimized = []
        multiplication_group = []
        
        for op in circuit:
            if op.get("type") == "multiply":
                multiplication_group.append(op)
            else:
                if multiplication_group:
                    # Process accumulated multiplications
                    optimized.extend(self._optimize_multiplication_group(multiplication_group))
                    multiplication_group = []
                optimized.append(op)
        
        if multiplication_group:
            optimized.extend(self._optimize_multiplication_group(multiplication_group))
        
        return optimized
    
    def _optimize_multiplication_group(self, group: List[Dict]) -> List[Dict]:
        """Optimize a group of multiplication operations."""
        # For now, just add explicit relinearization after the group
        optimized = group.copy()
        
        if len(group) > 1:
            # Add a relinearization operation after the group
            relin_op = {
                "type": "relinearize",
                "inputs": [group[-1].get("output", "temp")],
                "output": f"{group[-1].get('output', 'temp')}_relin"
            }
            optimized.append(relin_op)
        
        return optimized
    
    def _insert_optimal_rescaling(self, circuit: List[Dict]) -> List[Dict]:
        """Insert optimal rescaling operations for CKKS."""
        optimized = []
        noise_level = 1.0  # Simplified noise tracking
        
        for op in circuit:
            optimized.append(op)
            
            # Update noise estimate
            if op.get("type") == "multiply":
                noise_level *= 2  # Simplified noise growth
            
            # Insert rescaling if noise is high
            if noise_level > 4 and op.get("type") in ["multiply", "add"]:
                rescale_op = {
                    "type": "rescale",
                    "inputs": [op.get("output", "temp")],
                    "output": f"{op.get('output', 'temp')}_rescaled"
                }
                optimized.append(rescale_op)
                noise_level /= 2  # Rescaling reduces noise
        
        return optimized
    
    def _execute_optimized_circuit(self, circuit: List[Dict], 
                                  inputs: Dict[str, Ciphertext]) -> Dict[str, Ciphertext]:
        """Execute the optimized circuit."""
        variables = inputs.copy()
        
        for op in circuit:
            op_type = op.get("type")
            op_inputs = op.get("inputs", [])
            op_output = op.get("output", f"temp_{len(variables)}")
            
            # Execute operation (simplified)
            if op_type == "add" and len(op_inputs) >= 2:
                # Would use actual evaluator here
                variables[op_output] = variables[op_inputs[0]]  # Placeholder
            elif op_type == "multiply" and len(op_inputs) >= 2:
                variables[op_output] = variables[op_inputs[0]]  # Placeholder
            elif op_type == "relinearize" and len(op_inputs) >= 1:
                variables[op_output] = variables[op_inputs[0]]  # Placeholder
            elif op_type == "rescale" and len(op_inputs) >= 1:
                variables[op_output] = variables[op_inputs[0]]  # Placeholder
        
        return variables
    
    def benchmark_optimization(self, operation: Callable, *args, **kwargs) -> Dict[str, float]:
        """
        Benchmark an operation with and without optimizations.
        
        Args:
            operation: Operation to benchmark
            *args: Operation arguments
            **kwargs: Operation keyword arguments
        
        Returns:
            Benchmark results
        """
        # Benchmark without optimizations
        original_profile = self.profile
        self.profile = OptimizationProfile(
            enable_ntt_optimization=False,
            enable_lazy_relinearization=False,
            enable_ciphertext_packing=False,
            enable_operation_batching=False
        )
        
        start_time = time.perf_counter()
        result_unoptimized = operation(*args, **kwargs)
        unoptimized_time = time.perf_counter() - start_time
        
        # Benchmark with optimizations
        self.profile = original_profile
        
        start_time = time.perf_counter()
        result_optimized = operation(*args, **kwargs)
        optimized_time = time.perf_counter() - start_time
        
        speedup = unoptimized_time / optimized_time if optimized_time > 0 else float('inf')
        
        return {
            "unoptimized_time_ms": unoptimized_time * 1000,
            "optimized_time_ms": optimized_time * 1000,
            "speedup": speedup,
            "improvement_percent": (1 - optimized_time / unoptimized_time) * 100 if unoptimized_time > 0 else 0
        }
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Get statistics about optimization effectiveness."""
        total_cache_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0
        
        return {
            "cache_hit_rate": cache_hit_rate,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "lazy_queue_size": len(self.lazy_queue),
            "pending_operations": len(self.pending_operations),
            "operation_times": self.operation_times.copy(),
            "memory_usage": self.memory_usage.copy()
        }
    
    def reset_statistics(self) -> None:
        """Reset optimization statistics."""
        self.cache_hits = 0
        self.cache_misses = 0
        self.operation_times.clear()
        self.memory_usage.clear()
        self.lazy_queue.clear()
        self.pending_operations.clear()
        self.operation_cache.clear()
        
        self.logger.info("Reset optimization statistics")