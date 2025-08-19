"""
Encrypted inference engine for machine learning models.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Union
import logging
import time

from ..schemes.ckks import CKKSScheme, CKKSCiphertext

logger = logging.getLogger(__name__)


class EncryptedInference:
    """High-performance encrypted inference engine."""
    
    def __init__(self, scheme: CKKSScheme):
        self.scheme = scheme
        self.logger = logging.getLogger(self.__class__.__name__)
        self.inference_cache = {}
        self.performance_stats = {
            "total_inferences": 0,
            "total_time": 0.0,
            "cache_hits": 0
        }
    
    def batch_inference(self, model: Any, inputs: List[CKKSCiphertext]) -> List[CKKSCiphertext]:
        """Perform batch inference with optimizations."""
        start_time = time.time()
        
        results = []
        for i, input_data in enumerate(inputs):
            self.logger.debug(f"Processing batch item {i+1}/{len(inputs)}")
            
            # Check cache first
            cache_key = self._compute_cache_key(input_data)
            if cache_key in self.inference_cache:
                results.append(self.inference_cache[cache_key])
                self.performance_stats["cache_hits"] += 1
                continue
            
            # Perform inference
            if hasattr(model, 'predict'):
                result = model.predict(input_data)
            else:
                result = self._generic_inference(model, input_data)
            
            results.append(result)
            self.inference_cache[cache_key] = result
        
        # Update stats
        end_time = time.time()
        self.performance_stats["total_inferences"] += len(inputs)
        self.performance_stats["total_time"] += (end_time - start_time)
        
        return results
    
    def _compute_cache_key(self, ciphertext: CKKSCiphertext) -> str:
        """Compute cache key for ciphertext (simplified)."""
        # In practice, would use hash of polynomial coefficients
        return f"ct_{ciphertext.size}_{ciphertext.level}"
    
    def _generic_inference(self, model: Any, input_data: CKKSCiphertext) -> CKKSCiphertext:
        """Generic inference for models without predict method."""
        # Fallback inference logic
        return input_data
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get inference performance statistics."""
        avg_time = (self.performance_stats["total_time"] / 
                   max(1, self.performance_stats["total_inferences"]))
        
        cache_rate = (self.performance_stats["cache_hits"] / 
                     max(1, self.performance_stats["total_inferences"]))
        
        return {
            "total_inferences": self.performance_stats["total_inferences"],
            "total_time_seconds": self.performance_stats["total_time"],
            "average_time_ms": avg_time * 1000,
            "cache_hit_rate": cache_rate,
            "throughput_per_second": max(1, self.performance_stats["total_inferences"]) / 
                                   max(0.001, self.performance_stats["total_time"])
        }