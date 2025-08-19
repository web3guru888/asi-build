"""
Utility functions and helpers for homomorphic encryption operations.
"""

import numpy as np
import time
import json
import pickle
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import logging

from .base import FHEConfiguration, SecurityLevel, SchemeType
from .parameters import FHEParameters
from .encryption import Ciphertext, Plaintext

logger = logging.getLogger(__name__)


class HomomorphicUtils:
    """
    Utility functions for homomorphic encryption operations.
    
    Provides helper functions for data conversion, serialization,
    benchmarking, and configuration management.
    """
    
    @staticmethod
    def create_config(scheme_type: SchemeType,
                     security_level: SecurityLevel,
                     poly_modulus_degree: Optional[int] = None,
                     coefficient_modulus: Optional[List[int]] = None,
                     plaintext_modulus: Optional[int] = None,
                     scale: Optional[float] = None) -> FHEConfiguration:
        """
        Create an FHE configuration with recommended parameters.
        
        Args:
            scheme_type: Type of FHE scheme
            security_level: Security level
            poly_modulus_degree: Polynomial modulus degree (auto if None)
            coefficient_modulus: Coefficient modulus (auto if None)
            plaintext_modulus: Plaintext modulus for BFV/BGV
            scale: Scale for CKKS
        
        Returns:
            FHE configuration
        """
        from .parameters import ParameterGenerator
        
        # Generate recommended parameters if not provided
        if not poly_modulus_degree or not coefficient_modulus:
            param_gen = ParameterGenerator()
            params = param_gen.generate_parameters(scheme_type, security_level)
            
            if not poly_modulus_degree:
                poly_modulus_degree = params.polynomial_modulus_degree
            if not coefficient_modulus:
                coefficient_modulus = params.coefficient_modulus
            if not plaintext_modulus and scheme_type in [SchemeType.BFV, SchemeType.BGV]:
                plaintext_modulus = params.plaintext_modulus
            if not scale and scheme_type == SchemeType.CKKS:
                scale = params.scale
        
        return FHEConfiguration(
            scheme_type=scheme_type,
            security_level=security_level,
            polynomial_modulus_degree=poly_modulus_degree,
            coefficient_modulus=coefficient_modulus,
            plaintext_modulus=plaintext_modulus,
            scale=scale
        )
    
    @staticmethod
    def encode_data(data: Union[List, np.ndarray], 
                   scheme_type: SchemeType,
                   scale: Optional[float] = None,
                   encoding: str = "packed") -> List[Plaintext]:
        """
        Encode data into plaintexts for encryption.
        
        Args:
            data: Data to encode (numbers or vectors)
            scheme_type: FHE scheme type
            scale: Scale factor for CKKS
            encoding: Encoding method
        
        Returns:
            List of encoded plaintexts
        """
        data_array = np.array(data)
        
        if data_array.ndim == 0:
            # Single value
            return [Plaintext([data_array.item()], scale=scale, encoding="single")]
        
        elif data_array.ndim == 1:
            # Vector
            if scheme_type == SchemeType.CKKS:
                return [Plaintext(data_array, scale=scale, encoding=encoding)]
            else:
                # For BFV/BGV, ensure integer values
                int_data = data_array.astype(int)
                return [Plaintext(int_data, encoding=encoding)]
        
        else:
            # Matrix or higher dimensions - flatten and batch
            flattened = data_array.flatten()
            plaintexts = []
            
            # Determine batch size based on scheme
            if scheme_type == SchemeType.CKKS:
                batch_size = 4096  # Common CKKS slot count
            else:
                batch_size = 1024  # Conservative for BFV/BGV
            
            for i in range(0, len(flattened), batch_size):
                batch = flattened[i:i + batch_size]
                if scheme_type == SchemeType.CKKS:
                    plaintexts.append(Plaintext(batch, scale=scale, encoding=encoding))
                else:
                    int_batch = batch.astype(int)
                    plaintexts.append(Plaintext(int_batch, encoding=encoding))
            
            return plaintexts
    
    @staticmethod
    def decode_data(plaintexts: List[Plaintext], 
                   original_shape: Optional[Tuple] = None) -> Union[np.ndarray, List]:
        """
        Decode plaintexts back to original data format.
        
        Args:
            plaintexts: List of plaintexts to decode
            original_shape: Original shape to restore (if applicable)
        
        Returns:
            Decoded data
        """
        if len(plaintexts) == 1 and plaintexts[0].encoding == "single":
            # Single value
            return plaintexts[0].data[0]
        
        # Concatenate all plaintext data
        all_data = []
        for pt in plaintexts:
            all_data.extend(pt.data)
        
        result = np.array(all_data)
        
        if original_shape:
            # Reshape to original dimensions
            total_elements = np.prod(original_shape)
            result = result[:total_elements].reshape(original_shape)
        
        return result
    
    @staticmethod
    def serialize_ciphertext(ciphertext: Ciphertext) -> bytes:
        """
        Serialize a ciphertext to bytes.
        
        Args:
            ciphertext: Ciphertext to serialize
        
        Returns:
            Serialized ciphertext
        """
        data = {
            'polynomials': [poly.coefficients for poly in ciphertext.polynomials],
            'scale': ciphertext.scale,
            'level': ciphertext.level,
            'is_ntt_form': ciphertext.is_ntt_form,
            'size': ciphertext.size
        }
        return pickle.dumps(data)
    
    @staticmethod
    def deserialize_ciphertext(data: bytes, poly_ring) -> Ciphertext:
        """
        Deserialize a ciphertext from bytes.
        
        Args:
            data: Serialized ciphertext data
            poly_ring: Polynomial ring for reconstruction
        
        Returns:
            Deserialized ciphertext
        """
        obj = pickle.loads(data)
        
        from .polynomial import Polynomial
        polynomials = [Polynomial(coeffs, poly_ring) for coeffs in obj['polynomials']]
        
        return Ciphertext(
            polynomials,
            obj['scale'],
            obj['level'],
            obj['is_ntt_form']
        )
    
    @staticmethod
    def save_ciphertext(ciphertext: Ciphertext, filepath: Union[str, Path]) -> None:
        """
        Save a ciphertext to file.
        
        Args:
            ciphertext: Ciphertext to save
            filepath: Output file path
        """
        serialized = HomomorphicUtils.serialize_ciphertext(ciphertext)
        
        with open(filepath, 'wb') as f:
            f.write(serialized)
        
        logger.info(f"Saved ciphertext to {filepath}")
    
    @staticmethod
    def load_ciphertext(filepath: Union[str, Path], poly_ring) -> Ciphertext:
        """
        Load a ciphertext from file.
        
        Args:
            filepath: Input file path
            poly_ring: Polynomial ring for reconstruction
        
        Returns:
            Loaded ciphertext
        """
        with open(filepath, 'rb') as f:
            data = f.read()
        
        ciphertext = HomomorphicUtils.deserialize_ciphertext(data, poly_ring)
        logger.info(f"Loaded ciphertext from {filepath}")
        
        return ciphertext
    
    @staticmethod
    def estimate_memory_usage(parameters: FHEParameters, num_ciphertexts: int = 1) -> Dict[str, float]:
        """
        Estimate memory usage for given parameters.
        
        Args:
            parameters: FHE parameters
            num_ciphertexts: Number of ciphertexts to estimate for
        
        Returns:
            Memory usage estimates in MB
        """
        n = parameters.polynomial_modulus_degree
        num_moduli = len(parameters.coefficient_modulus)
        
        # Estimate polynomial size (64-bit coefficients)
        poly_size_bytes = n * num_moduli * 8
        
        # Ciphertext size (typically 2 polynomials)
        ciphertext_size_mb = (poly_size_bytes * 2) / (1024 * 1024)
        
        # Key sizes
        public_key_size_mb = ciphertext_size_mb  # 2 polynomials
        secret_key_size_mb = poly_size_bytes / (1024 * 1024)  # 1 polynomial
        
        # Relinearization keys (approximate)
        relin_keys_size_mb = ciphertext_size_mb * num_moduli * 2
        
        # Galois keys (estimate for common rotations)
        galois_keys_size_mb = ciphertext_size_mb * 10  # ~10 rotation keys
        
        return {
            "single_ciphertext_mb": ciphertext_size_mb,
            "total_ciphertexts_mb": ciphertext_size_mb * num_ciphertexts,
            "public_key_mb": public_key_size_mb,
            "secret_key_mb": secret_key_size_mb,
            "relinearization_keys_mb": relin_keys_size_mb,
            "galois_keys_mb": galois_keys_size_mb,
            "total_keys_mb": public_key_size_mb + secret_key_size_mb + relin_keys_size_mb + galois_keys_size_mb
        }
    
    @staticmethod
    def benchmark_operation(operation_func, *args, num_trials: int = 10) -> Dict[str, float]:
        """
        Benchmark a homomorphic operation.
        
        Args:
            operation_func: Function to benchmark
            *args: Arguments to pass to the function
            num_trials: Number of trials to run
        
        Returns:
            Benchmark results
        """
        times = []
        
        for _ in range(num_trials):
            start_time = time.perf_counter()
            result = operation_func(*args)
            end_time = time.perf_counter()
            
            times.append(end_time - start_time)
        
        times = np.array(times)
        
        return {
            "mean_time_ms": float(np.mean(times) * 1000),
            "std_time_ms": float(np.std(times) * 1000),
            "min_time_ms": float(np.min(times) * 1000),
            "max_time_ms": float(np.max(times) * 1000),
            "num_trials": num_trials
        }
    
    @staticmethod
    def generate_test_data(data_type: str, size: int, **kwargs) -> np.ndarray:
        """
        Generate test data for homomorphic encryption experiments.
        
        Args:
            data_type: Type of data ("random", "sequential", "sparse", "structured")
            size: Size of data
            **kwargs: Additional parameters
        
        Returns:
            Generated test data
        """
        if data_type == "random":
            if kwargs.get("integer", False):
                max_val = kwargs.get("max_value", 1000)
                return np.random.randint(0, max_val, size)
            else:
                scale = kwargs.get("scale", 1.0)
                return np.random.random(size) * scale
        
        elif data_type == "sequential":
            start = kwargs.get("start", 0)
            return np.arange(start, start + size)
        
        elif data_type == "sparse":
            density = kwargs.get("density", 0.1)
            data = np.zeros(size)
            num_nonzero = int(size * density)
            indices = np.random.choice(size, num_nonzero, replace=False)
            data[indices] = np.random.random(num_nonzero)
            return data
        
        elif data_type == "structured":
            pattern = kwargs.get("pattern", "sine")
            if pattern == "sine":
                freq = kwargs.get("frequency", 1.0)
                x = np.linspace(0, 2 * np.pi * freq, size)
                return np.sin(x)
            elif pattern == "polynomial":
                degree = kwargs.get("degree", 2)
                x = np.linspace(-1, 1, size)
                return x ** degree
        
        else:
            raise ValueError(f"Unknown data type: {data_type}")
    
    @staticmethod
    def validate_computation_result(expected: np.ndarray, 
                                  actual: np.ndarray,
                                  tolerance: float = 1e-6) -> Dict[str, Any]:
        """
        Validate the result of a homomorphic computation.
        
        Args:
            expected: Expected result
            actual: Actual result from homomorphic computation
            tolerance: Tolerance for floating-point comparisons
        
        Returns:
            Validation results
        """
        expected = np.array(expected)
        actual = np.array(actual)
        
        if expected.shape != actual.shape:
            return {
                "valid": False,
                "error": f"Shape mismatch: expected {expected.shape}, got {actual.shape}",
                "max_error": float('inf'),
                "mean_error": float('inf')
            }
        
        errors = np.abs(expected - actual)
        max_error = np.max(errors)
        mean_error = np.mean(errors)
        
        is_valid = max_error <= tolerance
        
        return {
            "valid": is_valid,
            "max_error": float(max_error),
            "mean_error": float(mean_error),
            "tolerance": tolerance,
            "relative_error": float(max_error / np.max(np.abs(expected))) if np.max(np.abs(expected)) > 0 else 0.0
        }
    
    @staticmethod
    def export_config(config: FHEConfiguration, filepath: Union[str, Path]) -> None:
        """
        Export FHE configuration to JSON file.
        
        Args:
            config: Configuration to export
            filepath: Output file path
        """
        config_dict = {
            "scheme_type": config.scheme_type.value,
            "security_level": config.security_level.value,
            "polynomial_modulus_degree": config.polynomial_modulus_degree,
            "coefficient_modulus": config.coefficient_modulus,
            "plaintext_modulus": config.plaintext_modulus,
            "scale": config.scale,
            "enable_batching": config.enable_batching,
            "enable_relinearization": config.enable_relinearization,
            "enable_galois_keys": config.enable_galois_keys
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Exported configuration to {filepath}")
    
    @staticmethod
    def import_config(filepath: Union[str, Path]) -> FHEConfiguration:
        """
        Import FHE configuration from JSON file.
        
        Args:
            filepath: Input file path
        
        Returns:
            Imported configuration
        """
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        
        config = FHEConfiguration(
            scheme_type=SchemeType(config_dict["scheme_type"]),
            security_level=SecurityLevel(config_dict["security_level"]),
            polynomial_modulus_degree=config_dict["polynomial_modulus_degree"],
            coefficient_modulus=config_dict["coefficient_modulus"],
            plaintext_modulus=config_dict.get("plaintext_modulus"),
            scale=config_dict.get("scale"),
            enable_batching=config_dict.get("enable_batching", True),
            enable_relinearization=config_dict.get("enable_relinearization", True),
            enable_galois_keys=config_dict.get("enable_galois_keys", True)
        )
        
        logger.info(f"Imported configuration from {filepath}")
        return config
    
    @staticmethod
    def compare_schemes(schemes: List[Dict[str, Any]], 
                       test_data: np.ndarray,
                       operations: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Compare different FHE schemes on the same test data.
        
        Args:
            schemes: List of scheme configurations
            test_data: Test data to use
            operations: List of operations to test
        
        Returns:
            Comparison results
        """
        results = {}
        
        for scheme_info in schemes:
            scheme_name = scheme_info["name"]
            config = scheme_info["config"]
            
            try:
                # Initialize scheme
                from ..schemes import get_scheme_class
                scheme_class = get_scheme_class(config.scheme_type)
                scheme = scheme_class(config)
                
                # Generate keys
                keys = scheme.generate_keys()
                
                # Encode and encrypt test data
                plaintexts = HomomorphicUtils.encode_data(
                    test_data, 
                    config.scheme_type,
                    scale=config.scale
                )
                ciphertexts = [scheme.encrypt(pt, keys["public_key"]) for pt in plaintexts]
                
                # Benchmark operations
                operation_results = {}
                for op in operations:
                    if op == "add" and len(ciphertexts) >= 2:
                        benchmark = HomomorphicUtils.benchmark_operation(
                            scheme.add, ciphertexts[0], ciphertexts[1]
                        )
                        operation_results[op] = benchmark
                    
                    elif op == "multiply" and len(ciphertexts) >= 2:
                        benchmark = HomomorphicUtils.benchmark_operation(
                            scheme.multiply, ciphertexts[0], ciphertexts[1]
                        )
                        operation_results[op] = benchmark
                
                results[scheme_name] = {
                    "config": config,
                    "operations": operation_results,
                    "memory_usage": HomomorphicUtils.estimate_memory_usage(
                        scheme.parameters, len(ciphertexts)
                    ),
                    "success": True
                }
                
            except Exception as e:
                results[scheme_name] = {
                    "error": str(e),
                    "success": False
                }
        
        return results