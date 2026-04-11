"""
Model Compression Utilities

Implementation of model compression techniques including quantization,
pruning, and knowledge distillation for federated learning.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import tensorflow as tf


class ModelCompressor(ABC):
    """Abstract base class for model compression techniques."""

    def __init__(self, compression_config: Dict[str, Any]):
        self.config = compression_config
        self.compression_ratio = 1.0
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def compress(self, weights: List[np.ndarray]) -> Tuple[Any, Dict[str, Any]]:
        """Compress model weights."""
        pass

    @abstractmethod
    def decompress(self, compressed_data: Any, metadata: Dict[str, Any]) -> List[np.ndarray]:
        """Decompress model weights."""
        pass

    def get_compression_ratio(self) -> float:
        """Get compression ratio achieved."""
        return self.compression_ratio


class QuantizationCompressor(ModelCompressor):
    """Quantization-based model compression."""

    def __init__(self, compression_config: Dict[str, Any]):
        super().__init__(compression_config)
        self.bits = self.config.get("quantization_bits", 8)
        self.quantization_method = self.config.get("method", "uniform")

        self.logger.info(f"Quantization compressor initialized with {self.bits} bits")

    def compress(self, weights: List[np.ndarray]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Quantize model weights."""
        compressed_weights = {}
        metadata = {"method": "quantization", "bits": self.bits, "layer_info": {}}

        total_original_size = 0
        total_compressed_size = 0

        for i, weight in enumerate(weights):
            original_size = weight.nbytes
            total_original_size += original_size

            if self.quantization_method == "uniform":
                quantized_weight, layer_meta = self._uniform_quantization(weight)
            elif self.quantization_method == "dynamic":
                quantized_weight, layer_meta = self._dynamic_quantization(weight)
            else:
                raise ValueError(f"Unknown quantization method: {self.quantization_method}")

            compressed_weights[f"layer_{i}"] = quantized_weight
            metadata["layer_info"][f"layer_{i}"] = layer_meta

            compressed_size = quantized_weight["quantized_values"].nbytes + 8  # scale + zero_point
            total_compressed_size += compressed_size

        self.compression_ratio = total_original_size / total_compressed_size
        metadata["compression_ratio"] = self.compression_ratio

        self.logger.info(f"Quantization completed: {self.compression_ratio:.2f}x compression")
        return compressed_weights, metadata

    def decompress(
        self, compressed_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> List[np.ndarray]:
        """Dequantize model weights."""
        weights = []

        for i in range(len(compressed_data)):
            layer_key = f"layer_{i}"
            if layer_key in compressed_data:
                quantized_weight = compressed_data[layer_key]
                layer_meta = metadata["layer_info"][layer_key]

                if metadata.get("method") == "quantization":
                    weight = self._dequantize(quantized_weight, layer_meta)
                    weights.append(weight)

        return weights

    def _uniform_quantization(self, weight: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Uniform quantization of weights."""
        # Compute scale and zero point
        min_val = float(np.min(weight))
        max_val = float(np.max(weight))

        # Handle edge case where min == max
        if min_val == max_val:
            scale = 1.0
            zero_point = 0
        else:
            scale = (max_val - min_val) / (2**self.bits - 1)
            zero_point = int(-min_val / scale)
            zero_point = max(0, min(zero_point, 2**self.bits - 1))

        # Quantize
        quantized = np.round(weight / scale + zero_point)
        quantized = np.clip(quantized, 0, 2**self.bits - 1).astype(
            np.uint8 if self.bits <= 8 else np.uint16
        )

        quantized_data = {
            "quantized_values": quantized,
            "scale": scale,
            "zero_point": zero_point,
            "original_shape": weight.shape,
            "original_dtype": str(weight.dtype),
        }

        metadata = {"quantization_method": "uniform", "min_val": min_val, "max_val": max_val}

        return quantized_data, metadata

    def _dynamic_quantization(self, weight: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Dynamic quantization based on weight distribution."""
        # Use percentiles for dynamic range
        min_percentile = self.config.get("min_percentile", 1.0)
        max_percentile = self.config.get("max_percentile", 99.0)

        min_val = float(np.percentile(weight, min_percentile))
        max_val = float(np.percentile(weight, max_percentile))

        # Clamp outliers
        clamped_weight = np.clip(weight, min_val, max_val)

        # Apply uniform quantization to clamped weights
        return self._uniform_quantization(clamped_weight)

    def _dequantize(self, quantized_data: Dict[str, Any], metadata: Dict[str, Any]) -> np.ndarray:
        """Dequantize weights."""
        quantized_values = quantized_data["quantized_values"]
        scale = quantized_data["scale"]
        zero_point = quantized_data["zero_point"]
        original_shape = quantized_data["original_shape"]

        # Dequantize
        dequantized = (quantized_values.astype(np.float32) - zero_point) * scale
        dequantized = dequantized.reshape(original_shape)

        return dequantized


class PruningCompressor(ModelCompressor):
    """Pruning-based model compression."""

    def __init__(self, compression_config: Dict[str, Any]):
        super().__init__(compression_config)
        self.sparsity_ratio = self.config.get("sparsity_ratio", 0.1)
        self.pruning_method = self.config.get("method", "magnitude")

        self.logger.info(f"Pruning compressor initialized with {self.sparsity_ratio} sparsity")

    def compress(self, weights: List[np.ndarray]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Prune model weights."""
        compressed_weights = {}
        metadata = {"method": "pruning", "sparsity_ratio": self.sparsity_ratio, "layer_info": {}}

        total_original_size = 0
        total_compressed_size = 0

        for i, weight in enumerate(weights):
            original_size = weight.nbytes
            total_original_size += original_size

            if self.pruning_method == "magnitude":
                pruned_weight, layer_meta = self._magnitude_pruning(weight)
            elif self.pruning_method == "random":
                pruned_weight, layer_meta = self._random_pruning(weight)
            else:
                raise ValueError(f"Unknown pruning method: {self.pruning_method}")

            compressed_weights[f"layer_{i}"] = pruned_weight
            metadata["layer_info"][f"layer_{i}"] = layer_meta

            # Estimate compressed size (sparse representation)
            num_nonzero = np.count_nonzero(pruned_weight["values"])
            compressed_size = num_nonzero * (4 + 4)  # value + index (rough estimate)
            total_compressed_size += compressed_size

        self.compression_ratio = total_original_size / max(total_compressed_size, 1)
        metadata["compression_ratio"] = self.compression_ratio

        self.logger.info(f"Pruning completed: {self.compression_ratio:.2f}x compression")
        return compressed_weights, metadata

    def decompress(
        self, compressed_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> List[np.ndarray]:
        """Restore pruned weights."""
        weights = []

        for i in range(len(compressed_data)):
            layer_key = f"layer_{i}"
            if layer_key in compressed_data:
                pruned_weight = compressed_data[layer_key]
                weight = self._restore_pruned_weight(pruned_weight)
                weights.append(weight)

        return weights

    def _magnitude_pruning(self, weight: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Magnitude-based pruning."""
        # Calculate threshold for pruning
        flat_weight = weight.flatten()
        threshold = np.percentile(np.abs(flat_weight), self.sparsity_ratio * 100)

        # Create mask
        mask = np.abs(weight) > threshold
        pruned_values = weight * mask

        # Store in sparse format
        nonzero_indices = np.nonzero(pruned_values)
        nonzero_values = pruned_values[nonzero_indices]

        pruned_data = {
            "values": nonzero_values,
            "indices": nonzero_indices,
            "original_shape": weight.shape,
            "pruning_mask": mask,
        }

        metadata = {
            "pruning_method": "magnitude",
            "threshold": float(threshold),
            "sparsity_achieved": float(np.mean(mask == 0)),
        }

        return pruned_data, metadata

    def _random_pruning(self, weight: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Random pruning."""
        # Create random mask
        mask = np.random.random(weight.shape) > self.sparsity_ratio
        pruned_values = weight * mask

        # Store in sparse format
        nonzero_indices = np.nonzero(pruned_values)
        nonzero_values = pruned_values[nonzero_indices]

        pruned_data = {
            "values": nonzero_values,
            "indices": nonzero_indices,
            "original_shape": weight.shape,
            "pruning_mask": mask,
        }

        metadata = {"pruning_method": "random", "sparsity_achieved": float(np.mean(mask == 0))}

        return pruned_data, metadata

    def _restore_pruned_weight(self, pruned_data: Dict[str, Any]) -> np.ndarray:
        """Restore weight from sparse representation."""
        shape = pruned_data["original_shape"]
        values = pruned_data["values"]
        indices = pruned_data["indices"]

        # Reconstruct dense weight
        restored_weight = np.zeros(shape)
        restored_weight[indices] = values

        return restored_weight


class HuffmanCompressor(ModelCompressor):
    """Huffman coding for weight compression."""

    def __init__(self, compression_config: Dict[str, Any]):
        super().__init__(compression_config)
        self.precision = self.config.get("precision", 1000)  # For weight discretization

    def compress(self, weights: List[np.ndarray]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Compress using Huffman coding."""
        # This is a simplified implementation
        # In practice, you'd implement actual Huffman coding

        compressed_weights = {}
        metadata = {"method": "huffman", "layer_info": {}}

        for i, weight in enumerate(weights):
            # Discretize weights
            discretized = np.round(weight * self.precision).astype(np.int32)

            # Simple compression (placeholder for actual Huffman)
            unique_values, counts = np.unique(discretized, return_counts=True)

            compressed_weights[f"layer_{i}"] = {
                "unique_values": unique_values,
                "counts": counts,
                "original_shape": weight.shape,
            }

            metadata["layer_info"][f"layer_{i}"] = {
                "num_unique": len(unique_values),
                "compression_estimate": len(discretized) / len(unique_values),
            }

        return compressed_weights, metadata

    def decompress(
        self, compressed_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> List[np.ndarray]:
        """Decompress from Huffman coding."""
        weights = []

        for i in range(len(compressed_data)):
            layer_key = f"layer_{i}"
            if layer_key in compressed_data:
                layer_data = compressed_data[layer_key]

                # Simplified decompression
                # In practice, you'd decode actual Huffman tree
                reconstructed = np.zeros(layer_data["original_shape"], dtype=np.float32)
                weights.append(reconstructed)

        return weights


def create_compressor(compression_type: str, config: Dict[str, Any]) -> ModelCompressor:
    """Factory function to create compressors."""
    if compression_type.lower() == "quantization":
        return QuantizationCompressor(config)
    elif compression_type.lower() == "pruning":
        return PruningCompressor(config)
    elif compression_type.lower() == "huffman":
        return HuffmanCompressor(config)
    else:
        raise ValueError(f"Unknown compression type: {compression_type}")


class CompressionManager:
    """Manager for multiple compression techniques."""

    def __init__(self, compression_configs: List[Dict[str, Any]]):
        self.compressors = []

        for config in compression_configs:
            compression_type = config.get("type", "quantization")
            compressor = create_compressor(compression_type, config)
            self.compressors.append(compressor)

        self.logger = logging.getLogger("CompressionManager")
        self.logger.info(f"Initialized {len(self.compressors)} compressors")

    def compress_weights(self, weights: List[np.ndarray]) -> Tuple[Any, Dict[str, Any]]:
        """Apply all compression techniques sequentially."""
        current_weights = weights
        all_metadata = {"compression_stages": []}

        for i, compressor in enumerate(self.compressors):
            compressed_data, metadata = compressor.compress(current_weights)

            all_metadata["compression_stages"].append(
                {"stage": i, "compressor": compressor.__class__.__name__, "metadata": metadata}
            )

            # For next stage, decompress to get weights
            if i < len(self.compressors) - 1:
                current_weights = compressor.decompress(compressed_data, metadata)

        return compressed_data, all_metadata

    def decompress_weights(
        self, compressed_data: Any, metadata: Dict[str, Any]
    ) -> List[np.ndarray]:
        """Decompress weights by reversing compression stages."""
        current_data = compressed_data

        # Apply decompression in reverse order
        for stage_info in reversed(metadata["compression_stages"]):
            stage_idx = stage_info["stage"]
            stage_metadata = stage_info["metadata"]
            compressor = self.compressors[stage_idx]

            current_data = compressor.decompress(current_data, stage_metadata)

        return current_data
