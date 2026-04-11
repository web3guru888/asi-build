"""
Gradient Compression and Communication Optimization
Implements various compression techniques to reduce communication overhead
"""

import asyncio
import logging
import pickle
import struct
import time
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import brotli
import lz4
import numpy as np
import torch
import torch.nn as nn
from scipy.sparse import csc_matrix, csr_matrix


@dataclass
class CompressionStats:
    """Statistics for compression operations"""

    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_time: float
    decompression_time: float
    algorithm: str


class GradientCompressor(ABC):
    """Abstract base class for gradient compression"""

    @abstractmethod
    async def compress(self, gradients: Dict[str, torch.Tensor]) -> Tuple[bytes, Dict[str, Any]]:
        """Compress gradients and return compressed data with metadata"""
        pass

    @abstractmethod
    async def decompress(
        self, compressed_data: bytes, metadata: Dict[str, Any]
    ) -> Dict[str, torch.Tensor]:
        """Decompress data back to gradients"""
        pass

    @abstractmethod
    def get_compression_ratio(self) -> float:
        """Get theoretical compression ratio"""
        pass


class TopKSparsification(GradientCompressor):
    """Top-K sparsification compression"""

    def __init__(self, k_ratio: float = 0.1, error_feedback: bool = True):
        self.k_ratio = k_ratio
        self.error_feedback = error_feedback
        self.error_memory: Dict[str, torch.Tensor] = {}

        self.logger = logging.getLogger(__name__)

    async def compress(self, gradients: Dict[str, torch.Tensor]) -> Tuple[bytes, Dict[str, Any]]:
        """Compress using top-k sparsification"""
        start_time = time.time()

        compressed_gradients = {}
        metadata = {"algorithm": "topk", "k_ratio": self.k_ratio, "shapes": {}, "dtypes": {}}

        for name, grad in gradients.items():
            # Apply error feedback if enabled
            if self.error_feedback and name in self.error_memory:
                grad = grad + self.error_memory[name]

            # Flatten gradient
            flat_grad = grad.flatten()
            k = max(1, int(len(flat_grad) * self.k_ratio))

            # Get top-k elements
            values, indices = torch.topk(torch.abs(flat_grad), k)
            top_k_values = flat_grad[indices]

            # Store compressed representation
            compressed_gradients[name] = {
                "values": top_k_values.cpu().numpy(),
                "indices": indices.cpu().numpy(),
                "size": len(flat_grad),
            }

            # Update error memory
            if self.error_feedback:
                sparse_grad = torch.zeros_like(flat_grad)
                sparse_grad[indices] = top_k_values
                self.error_memory[name] = flat_grad - sparse_grad

            metadata["shapes"][name] = list(grad.shape)
            metadata["dtypes"][name] = str(grad.dtype)

        # Serialize compressed data
        compressed_data = pickle.dumps(compressed_gradients)
        compressed_data = zlib.compress(compressed_data)

        compression_time = time.time() - start_time

        self.logger.debug(f"Top-K compression completed in {compression_time:.3f}s")

        return compressed_data, metadata

    async def decompress(
        self, compressed_data: bytes, metadata: Dict[str, Any]
    ) -> Dict[str, torch.Tensor]:
        """Decompress top-k sparsified gradients"""
        start_time = time.time()

        # Deserialize
        decompressed = zlib.decompress(compressed_data)
        compressed_gradients = pickle.loads(decompressed)

        gradients = {}
        shapes = metadata["shapes"]
        dtypes = metadata["dtypes"]

        for name, compressed_grad in compressed_gradients.items():
            # Reconstruct sparse gradient
            size = compressed_grad["size"]
            sparse_grad = torch.zeros(size, dtype=torch.float32)

            values = torch.from_numpy(compressed_grad["values"])
            indices = torch.from_numpy(compressed_grad["indices"])

            sparse_grad[indices] = values

            # Reshape to original shape
            original_shape = shapes[name]
            gradients[name] = sparse_grad.reshape(original_shape)

        decompression_time = time.time() - start_time
        self.logger.debug(f"Top-K decompression completed in {decompression_time:.3f}s")

        return gradients

    def get_compression_ratio(self) -> float:
        """Get theoretical compression ratio"""
        return self.k_ratio


class QuantizationCompressor(GradientCompressor):
    """Quantization-based compression"""

    def __init__(self, num_bits: int = 8, stochastic: bool = True):
        self.num_bits = num_bits
        self.stochastic = stochastic
        self.num_levels = 2**num_bits

        self.logger = logging.getLogger(__name__)

    async def compress(self, gradients: Dict[str, torch.Tensor]) -> Tuple[bytes, Dict[str, Any]]:
        """Compress using quantization"""
        start_time = time.time()

        compressed_gradients = {}
        metadata = {
            "algorithm": "quantization",
            "num_bits": self.num_bits,
            "shapes": {},
            "scales": {},
            "zero_points": {},
        }

        for name, grad in gradients.items():
            flat_grad = grad.flatten()

            # Calculate quantization parameters
            min_val = torch.min(flat_grad)
            max_val = torch.max(flat_grad)

            scale = (max_val - min_val) / (self.num_levels - 1)
            zero_point = -min_val / scale

            # Quantize
            if self.stochastic:
                # Stochastic quantization
                quantized = torch.floor((flat_grad - min_val) / scale + torch.rand_like(flat_grad))
            else:
                # Deterministic quantization
                quantized = torch.round((flat_grad - min_val) / scale)

            quantized = torch.clamp(quantized, 0, self.num_levels - 1)

            # Convert to appropriate integer type
            if self.num_bits <= 8:
                quantized_int = quantized.to(torch.uint8)
            elif self.num_bits <= 16:
                quantized_int = quantized.to(torch.int16)
            else:
                quantized_int = quantized.to(torch.int32)

            compressed_gradients[name] = quantized_int.cpu().numpy()

            metadata["shapes"][name] = list(grad.shape)
            metadata["scales"][name] = scale.item()
            metadata["zero_points"][name] = zero_point.item()

        # Serialize and compress
        compressed_data = pickle.dumps(compressed_gradients)
        compressed_data = lz4.compress(compressed_data)

        compression_time = time.time() - start_time

        self.logger.debug(f"Quantization compression completed in {compression_time:.3f}s")

        return compressed_data, metadata

    async def decompress(
        self, compressed_data: bytes, metadata: Dict[str, Any]
    ) -> Dict[str, torch.Tensor]:
        """Decompress quantized gradients"""
        start_time = time.time()

        # Deserialize
        decompressed = lz4.decompress(compressed_data)
        compressed_gradients = pickle.loads(decompressed)

        gradients = {}

        for name, quantized_data in compressed_gradients.items():
            quantized = torch.from_numpy(quantized_data).to(torch.float32)

            scale = metadata["scales"][name]
            zero_point = metadata["zero_points"][name]

            # Dequantize
            dequantized = quantized * scale + zero_point * scale

            # Reshape
            original_shape = metadata["shapes"][name]
            gradients[name] = dequantized.reshape(original_shape)

        decompression_time = time.time() - start_time
        self.logger.debug(f"Quantization decompression completed in {decompression_time:.3f}s")

        return gradients

    def get_compression_ratio(self) -> float:
        """Get theoretical compression ratio"""
        return self.num_bits / 32.0  # Assuming 32-bit floats


class SignSGDCompressor(GradientCompressor):
    """SignSGD compression - transmit only signs"""

    def __init__(self, momentum: float = 0.9):
        self.momentum = momentum
        self.momentum_buffer: Dict[str, torch.Tensor] = {}

        self.logger = logging.getLogger(__name__)

    async def compress(self, gradients: Dict[str, torch.Tensor]) -> Tuple[bytes, Dict[str, Any]]:
        """Compress using sign compression"""
        start_time = time.time()

        compressed_gradients = {}
        metadata = {"algorithm": "signsgd", "shapes": {}, "norms": {}}

        for name, grad in gradients.items():
            # Apply momentum if available
            if name in self.momentum_buffer:
                momentum_grad = (
                    self.momentum * self.momentum_buffer[name] + (1 - self.momentum) * grad
                )
                self.momentum_buffer[name] = momentum_grad
            else:
                momentum_grad = grad
                self.momentum_buffer[name] = grad.clone()

            # Calculate L1 norm for scaling
            norm = torch.norm(momentum_grad, p=1)

            # Extract signs
            signs = torch.sign(momentum_grad)

            # Pack signs into bits (8 signs per byte)
            flat_signs = signs.flatten()

            # Pad to multiple of 8
            remainder = len(flat_signs) % 8
            if remainder != 0:
                padding = torch.zeros(
                    8 - remainder, dtype=flat_signs.dtype, device=flat_signs.device
                )
                flat_signs = torch.cat([flat_signs, padding])

            # Pack into bytes
            sign_bytes = self._pack_signs_to_bytes(flat_signs)

            compressed_gradients[name] = sign_bytes
            metadata["shapes"][name] = list(grad.shape)
            metadata["norms"][name] = norm.item()

        # Serialize
        compressed_data = pickle.dumps(compressed_gradients)
        compressed_data = brotli.compress(compressed_data)

        compression_time = time.time() - start_time
        self.logger.debug(f"SignSGD compression completed in {compression_time:.3f}s")

        return compressed_data, metadata

    async def decompress(
        self, compressed_data: bytes, metadata: Dict[str, Any]
    ) -> Dict[str, torch.Tensor]:
        """Decompress sign-compressed gradients"""
        start_time = time.time()

        # Deserialize
        decompressed = brotli.decompress(compressed_data)
        compressed_gradients = pickle.loads(decompressed)

        gradients = {}

        for name, sign_bytes in compressed_gradients.items():
            original_shape = metadata["shapes"][name]
            norm = metadata["norms"][name]

            # Unpack signs from bytes
            signs = self._unpack_signs_from_bytes(sign_bytes, np.prod(original_shape))

            # Scale by norm
            grad_tensor = torch.from_numpy(signs) * norm / len(signs)

            # Reshape
            gradients[name] = grad_tensor.reshape(original_shape)

        decompression_time = time.time() - start_time
        self.logger.debug(f"SignSGD decompression completed in {decompression_time:.3f}s")

        return gradients

    def _pack_signs_to_bytes(self, signs: torch.Tensor) -> bytes:
        """Pack signs into bytes"""
        signs_np = signs.cpu().numpy().astype(np.int8)

        # Convert -1 to 0 for bit packing
        signs_np[signs_np == -1] = 0

        # Pack 8 signs per byte
        packed_bytes = bytearray()
        for i in range(0, len(signs_np), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(signs_np) and signs_np[i + j] == 1:
                    byte_val |= 1 << j
            packed_bytes.append(byte_val)

        return bytes(packed_bytes)

    def _unpack_signs_from_bytes(self, sign_bytes: bytes, num_elements: int) -> np.ndarray:
        """Unpack signs from bytes"""
        signs = []

        for byte_val in sign_bytes:
            for j in range(8):
                if len(signs) >= num_elements:
                    break

                if byte_val & (1 << j):
                    signs.append(1.0)
                else:
                    signs.append(-1.0)

            if len(signs) >= num_elements:
                break

        return np.array(signs[:num_elements], dtype=np.float32)

    def get_compression_ratio(self) -> float:
        """Get theoretical compression ratio"""
        return 1.0 / 32.0  # 1 bit per parameter vs 32 bits


class AdaptiveCompressor(GradientCompressor):
    """Adaptive compressor that chooses best method based on gradient characteristics"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Initialize different compressors
        self.topk_compressor = TopKSparsification(
            k_ratio=config.get("topk_ratio", 0.1), error_feedback=config.get("error_feedback", True)
        )

        self.quantization_compressor = QuantizationCompressor(
            num_bits=config.get("quantization_bits", 8),
            stochastic=config.get("stochastic_quantization", True),
        )

        self.signsgd_compressor = SignSGDCompressor(momentum=config.get("signsgd_momentum", 0.9))

        # Compression history for adaptation
        self.compression_history: List[CompressionStats] = []

        self.logger = logging.getLogger(__name__)

    async def compress(self, gradients: Dict[str, torch.Tensor]) -> Tuple[bytes, Dict[str, Any]]:
        """Adaptively compress gradients"""

        # Analyze gradient characteristics
        sparsity = self._calculate_sparsity(gradients)
        variance = self._calculate_variance(gradients)
        size = self._calculate_total_size(gradients)

        # Choose compression method
        if sparsity > 0.8:  # Very sparse gradients
            compressor = self.topk_compressor
            method = "topk"
        elif variance < 0.1:  # Low variance gradients
            compressor = self.signsgd_compressor
            method = "signsgd"
        else:  # General case
            compressor = self.quantization_compressor
            method = "quantization"

        start_time = time.time()
        compressed_data, metadata = await compressor.compress(gradients)
        compression_time = time.time() - start_time

        # Add method info to metadata
        metadata["selected_method"] = method
        metadata["gradient_stats"] = {"sparsity": sparsity, "variance": variance, "size": size}

        # Record compression stats
        stats = CompressionStats(
            original_size=size,
            compressed_size=len(compressed_data),
            compression_ratio=len(compressed_data) / size,
            compression_time=compression_time,
            decompression_time=0,  # Will be updated during decompression
            algorithm=method,
        )

        self.compression_history.append(stats)

        # Keep only recent history
        if len(self.compression_history) > 100:
            self.compression_history = self.compression_history[-100:]

        self.logger.info(f"Selected {method} compression (ratio: {stats.compression_ratio:.3f})")

        return compressed_data, metadata

    async def decompress(
        self, compressed_data: bytes, metadata: Dict[str, Any]
    ) -> Dict[str, torch.Tensor]:
        """Decompress using the method specified in metadata"""
        method = metadata["selected_method"]

        start_time = time.time()

        if method == "topk":
            gradients = await self.topk_compressor.decompress(compressed_data, metadata)
        elif method == "quantization":
            gradients = await self.quantization_compressor.decompress(compressed_data, metadata)
        elif method == "signsgd":
            gradients = await self.signsgd_compressor.decompress(compressed_data, metadata)
        else:
            raise ValueError(f"Unknown compression method: {method}")

        decompression_time = time.time() - start_time

        # Update decompression time in latest stats
        if self.compression_history:
            self.compression_history[-1].decompression_time = decompression_time

        return gradients

    def _calculate_sparsity(self, gradients: Dict[str, torch.Tensor]) -> float:
        """Calculate sparsity of gradients"""
        total_zeros = 0
        total_elements = 0

        for grad in gradients.values():
            total_zeros += torch.sum(torch.abs(grad) < 1e-7).item()
            total_elements += grad.numel()

        return total_zeros / max(total_elements, 1)

    def _calculate_variance(self, gradients: Dict[str, torch.Tensor]) -> float:
        """Calculate normalized variance of gradients"""
        all_values = []

        for grad in gradients.values():
            all_values.extend(grad.flatten().tolist())

        if not all_values:
            return 0.0

        values_tensor = torch.tensor(all_values)
        return torch.var(values_tensor).item() / (
            torch.mean(torch.abs(values_tensor)).item() + 1e-7
        )

    def _calculate_total_size(self, gradients: Dict[str, torch.Tensor]) -> int:
        """Calculate total size in bytes"""
        total_elements = sum(grad.numel() for grad in gradients.values())
        return total_elements * 4  # Assuming 32-bit floats

    def get_compression_ratio(self) -> float:
        """Get average compression ratio from recent history"""
        if not self.compression_history:
            return 1.0

        recent_ratios = [stats.compression_ratio for stats in self.compression_history[-10:]]
        return sum(recent_ratios) / len(recent_ratios)

    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        if not self.compression_history:
            return {}

        recent_stats = self.compression_history[-10:]

        return {
            "average_compression_ratio": sum(s.compression_ratio for s in recent_stats)
            / len(recent_stats),
            "average_compression_time": sum(s.compression_time for s in recent_stats)
            / len(recent_stats),
            "average_decompression_time": sum(s.decompression_time for s in recent_stats)
            / len(recent_stats),
            "method_distribution": {
                "topk": sum(1 for s in recent_stats if s.algorithm == "topk"),
                "quantization": sum(1 for s in recent_stats if s.algorithm == "quantization"),
                "signsgd": sum(1 for s in recent_stats if s.algorithm == "signsgd"),
            },
            "total_compressions": len(self.compression_history),
        }


class CommunicationOptimizer:
    """Optimizes communication patterns and bandwidth usage"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        self.compressor = AdaptiveCompressor(config.get("compression", {}))

        # Communication parameters
        self.batch_size = config.get("batch_size", 10)
        self.max_retry_attempts = config.get("max_retry_attempts", 3)
        self.retry_backoff = config.get("retry_backoff", 2.0)

        # Bandwidth monitoring
        self.bandwidth_history: List[Tuple[float, int]] = []  # (timestamp, bytes_sent)
        self.congestion_threshold = config.get("congestion_threshold", 0.8)

        # Message batching
        self.pending_messages: List[Tuple[str, bytes, Dict[str, Any]]] = []
        self.batch_timeout = config.get("batch_timeout", 5.0)

        self.logger = logging.getLogger(__name__)

    async def optimize_gradient_transmission(
        self, gradients: Dict[str, torch.Tensor], recipient_nodes: List[str]
    ) -> Dict[str, Any]:
        """Optimize gradient transmission to multiple nodes"""

        # Compress gradients
        start_time = time.time()
        compressed_data, metadata = await self.compressor.compress(gradients)

        # Check network congestion
        congestion_level = self._get_network_congestion()

        if congestion_level > self.congestion_threshold:
            # Apply additional compression or delay
            await self._handle_network_congestion(compressed_data, metadata)

        # Batch transmission if multiple recipients
        if len(recipient_nodes) > self.batch_size:
            results = await self._batch_transmit(compressed_data, metadata, recipient_nodes)
        else:
            results = await self._direct_transmit(compressed_data, metadata, recipient_nodes)

        total_time = time.time() - start_time

        # Update bandwidth tracking
        total_bytes = len(compressed_data) * len(recipient_nodes)
        self._track_bandwidth(total_bytes)

        return {
            "compression_ratio": (
                metadata.get("gradient_stats", {}).get("size", 0) / len(compressed_data)
                if compressed_data
                else 1.0
            ),
            "transmission_time": total_time,
            "successful_transmissions": sum(1 for r in results if r["success"]),
            "failed_transmissions": sum(1 for r in results if not r["success"]),
            "total_bytes_sent": total_bytes,
            "congestion_level": congestion_level,
            "results": results,
        }

    async def _batch_transmit(
        self, compressed_data: bytes, metadata: Dict[str, Any], recipient_nodes: List[str]
    ) -> List[Dict[str, Any]]:
        """Batch transmission to multiple nodes"""

        # Split recipients into batches
        batches = [
            recipient_nodes[i : i + self.batch_size]
            for i in range(0, len(recipient_nodes), self.batch_size)
        ]

        results = []

        for batch in batches:
            batch_tasks = []
            for node_id in batch:
                task = asyncio.create_task(
                    self._transmit_to_node(compressed_data, metadata, node_id)
                )
                batch_tasks.append((node_id, task))

            # Wait for batch completion
            for node_id, task in batch_tasks:
                try:
                    result = await task
                    results.append(
                        {
                            "node_id": node_id,
                            "success": True,
                            "transmission_time": result.get("time", 0),
                        }
                    )
                except Exception as e:
                    results.append({"node_id": node_id, "success": False, "error": str(e)})

            # Small delay between batches to prevent overwhelming
            await asyncio.sleep(0.1)

        return results

    async def _direct_transmit(
        self, compressed_data: bytes, metadata: Dict[str, Any], recipient_nodes: List[str]
    ) -> List[Dict[str, Any]]:
        """Direct transmission to nodes"""

        tasks = []
        for node_id in recipient_nodes:
            task = asyncio.create_task(self._transmit_to_node(compressed_data, metadata, node_id))
            tasks.append((node_id, task))

        results = []

        for node_id, task in tasks:
            try:
                result = await task
                results.append(
                    {
                        "node_id": node_id,
                        "success": True,
                        "transmission_time": result.get("time", 0),
                    }
                )
            except Exception as e:
                results.append({"node_id": node_id, "success": False, "error": str(e)})

        return results

    async def _transmit_to_node(
        self, compressed_data: bytes, metadata: Dict[str, Any], node_id: str
    ) -> Dict[str, Any]:
        """Transmit data to a specific node with retry logic"""

        last_exception = None

        for attempt in range(self.max_retry_attempts):
            try:
                start_time = time.time()

                # Mock transmission - in practice, use actual network calls
                await asyncio.sleep(0.01)  # Simulate network delay

                transmission_time = time.time() - start_time

                return {
                    "time": transmission_time,
                    "bytes_sent": len(compressed_data),
                    "attempt": attempt + 1,
                }

            except Exception as e:
                last_exception = e

                if attempt < self.max_retry_attempts - 1:
                    # Exponential backoff
                    delay = self.retry_backoff**attempt
                    await asyncio.sleep(delay)

                    self.logger.warning(
                        f"Transmission to {node_id} failed (attempt {attempt + 1}), retrying..."
                    )

        # All attempts failed
        raise last_exception or Exception("Transmission failed")

    def _get_network_congestion(self) -> float:
        """Calculate network congestion level"""
        if len(self.bandwidth_history) < 2:
            return 0.0

        # Calculate recent bandwidth usage
        current_time = time.time()
        recent_bandwidth = [
            (timestamp, bytes_sent)
            for timestamp, bytes_sent in self.bandwidth_history
            if current_time - timestamp < 60  # Last minute
        ]

        if not recent_bandwidth:
            return 0.0

        total_bytes = sum(bytes_sent for _, bytes_sent in recent_bandwidth)
        time_span = max(1, current_time - min(timestamp for timestamp, _ in recent_bandwidth))

        # Calculate bytes per second
        bandwidth_usage = total_bytes / time_span

        # Normalize to congestion level (0-1)
        max_bandwidth = self.config.get("max_bandwidth", 10 * 1024 * 1024)  # 10 MB/s default
        congestion = min(1.0, bandwidth_usage / max_bandwidth)

        return congestion

    def _track_bandwidth(self, bytes_sent: int):
        """Track bandwidth usage"""
        self.bandwidth_history.append((time.time(), bytes_sent))

        # Keep only recent history (last hour)
        cutoff_time = time.time() - 3600
        self.bandwidth_history = [
            (timestamp, bytes_sent)
            for timestamp, bytes_sent in self.bandwidth_history
            if timestamp >= cutoff_time
        ]

    async def _handle_network_congestion(self, compressed_data: bytes, metadata: Dict[str, Any]):
        """Handle network congestion by applying additional optimizations"""

        # Apply additional compression
        if len(compressed_data) > 1024 * 1024:  # > 1MB
            self.logger.info("Applying additional compression due to network congestion")

            # Use higher compression ratio
            additional_compressed = brotli.compress(compressed_data, quality=11)

            if len(additional_compressed) < len(compressed_data) * 0.8:
                metadata["additional_compression"] = "brotli"
                return additional_compressed

        # Or implement traffic shaping, priority queuing, etc.
        return compressed_data

    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics"""
        current_time = time.time()

        # Recent bandwidth (last 5 minutes)
        recent_bandwidth = [
            (timestamp, bytes_sent)
            for timestamp, bytes_sent in self.bandwidth_history
            if current_time - timestamp < 300
        ]

        recent_bytes = sum(bytes_sent for _, bytes_sent in recent_bandwidth)

        return {
            "recent_bandwidth_usage": recent_bytes / 300,  # Bytes per second
            "current_congestion_level": self._get_network_congestion(),
            "total_transmissions": len(self.bandwidth_history),
            "compression_stats": self.compressor.get_compression_stats(),
        }
