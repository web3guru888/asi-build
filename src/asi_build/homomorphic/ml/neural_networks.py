"""
Encrypted neural networks using homomorphic encryption.

Implements deep learning models that can operate on encrypted data,
enabling privacy-preserving inference and training.
"""

import numpy as np
import math
from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging

from ..schemes.ckks import CKKSScheme, CKKSCiphertext, CKKSPlaintext
from ..core.base import FHEConfiguration, SchemeType, SecurityLevel

logger = logging.getLogger(__name__)


@dataclass
class LayerConfig:
    """Configuration for a neural network layer."""
    layer_type: str  # "dense", "conv2d", "activation", "pooling"
    input_size: int
    output_size: int
    activation: Optional[str] = None
    use_bias: bool = True
    kernel_size: Optional[Tuple[int, int]] = None
    stride: Optional[Tuple[int, int]] = None
    padding: Optional[str] = None


class ActivationFunction:
    """Collection of activation functions suitable for homomorphic encryption."""
    
    @staticmethod
    def polynomial_approximation(x: CKKSCiphertext, scheme: CKKSScheme, 
                                degree: int = 3) -> CKKSCiphertext:
        """
        Polynomial approximation of activation functions.
        
        Args:
            x: Input ciphertext
            scheme: CKKS scheme instance
            degree: Degree of polynomial approximation
        
        Returns:
            Activated ciphertext
        """
        # Default: approximate sigmoid with degree-3 polynomial
        # sigmoid(x) ≈ 0.5 + 0.197*x - 0.004*x^3 (for x in [-5, 5])
        coeffs = [0.5, 0.197, 0, -0.004]  # [constant, x, x^2, x^3]
        
        return scheme.polynomial_evaluation(x, coeffs[:degree + 1])
    
    @staticmethod
    def relu_approximation(x: CKKSCiphertext, scheme: CKKSScheme) -> CKKSCiphertext:
        """
        Polynomial approximation of ReLU activation.
        
        Args:
            x: Input ciphertext
            scheme: CKKS scheme instance
        
        Returns:
            ReLU-activated ciphertext
        """
        # ReLU approximation: max(0, x) ≈ x/2 + x*sigmoid(x)
        # Using polynomial sigmoid approximation
        sigmoid_x = ActivationFunction.polynomial_approximation(x, scheme, degree=3)
        
        half_x = scheme.multiply_plain(x, 0.5)
        x_sigmoid = scheme.multiply(x, sigmoid_x)
        
        return scheme.add(half_x, x_sigmoid)
    
    @staticmethod
    def tanh_approximation(x: CKKSCiphertext, scheme: CKKSScheme) -> CKKSCiphertext:
        """
        Polynomial approximation of tanh activation.
        
        Args:
            x: Input ciphertext
            scheme: CKKS scheme instance
        
        Returns:
            Tanh-activated ciphertext
        """
        # tanh(x) ≈ x - x^3/3 + 2*x^5/15 (Taylor series)
        coeffs = [0, 1, 0, -1/3, 0, 2/15]  # Up to x^5
        
        return scheme.polynomial_evaluation(x, coeffs)
    
    @staticmethod
    def swish_approximation(x: CKKSCiphertext, scheme: CKKSScheme) -> CKKSCiphertext:
        """
        Polynomial approximation of Swish activation (x * sigmoid(x)).
        
        Args:
            x: Input ciphertext
            scheme: CKKS scheme instance
        
        Returns:
            Swish-activated ciphertext
        """
        sigmoid_x = ActivationFunction.polynomial_approximation(x, scheme, degree=3)
        return scheme.multiply(x, sigmoid_x)


class EncryptedLayer(ABC):
    """Abstract base class for encrypted neural network layers."""
    
    def __init__(self, config: LayerConfig):
        """
        Initialize encrypted layer.
        
        Args:
            config: Layer configuration
        """
        self.config = config
        self.weights = None
        self.bias = None
        self.is_trained = False
    
    @abstractmethod
    def forward(self, x: CKKSCiphertext, scheme: CKKSScheme) -> CKKSCiphertext:
        """
        Forward pass through the layer.
        
        Args:
            x: Input ciphertext
            scheme: CKKS scheme instance
        
        Returns:
            Output ciphertext
        """
        pass
    
    @abstractmethod
    def set_weights(self, weights: np.ndarray, bias: Optional[np.ndarray] = None):
        """
        Set layer weights and bias.
        
        Args:
            weights: Weight matrix
            bias: Bias vector (optional)
        """
        pass


class EncryptedDenseLayer(EncryptedLayer):
    """Encrypted dense (fully connected) layer."""
    
    def __init__(self, config: LayerConfig):
        """
        Initialize encrypted dense layer.
        
        Args:
            config: Layer configuration
        """
        super().__init__(config)
        self.activation_fn = self._get_activation_function(config.activation)
    
    def _get_activation_function(self, activation: Optional[str]) -> Optional[Callable]:
        """Get activation function by name."""
        if activation is None:
            return None
        elif activation.lower() == "relu":
            return ActivationFunction.relu_approximation
        elif activation.lower() == "sigmoid":
            return ActivationFunction.polynomial_approximation
        elif activation.lower() == "tanh":
            return ActivationFunction.tanh_approximation
        elif activation.lower() == "swish":
            return ActivationFunction.swish_approximation
        else:
            raise ValueError(f"Unsupported activation function: {activation}")
    
    def set_weights(self, weights: np.ndarray, bias: Optional[np.ndarray] = None):
        """
        Set layer weights and bias.
        
        Args:
            weights: Weight matrix (input_size x output_size)
            bias: Bias vector (output_size,)
        """
        if weights.shape != (self.config.input_size, self.config.output_size):
            raise ValueError(f"Weight shape {weights.shape} doesn't match "
                           f"expected {(self.config.input_size, self.config.output_size)}")
        
        self.weights = weights
        
        if bias is not None:
            if bias.shape != (self.config.output_size,):
                raise ValueError(f"Bias shape {bias.shape} doesn't match "
                               f"expected {(self.config.output_size,)}")
            self.bias = bias
        
        self.is_trained = True
    
    def forward(self, x: CKKSCiphertext, scheme: CKKSScheme) -> CKKSCiphertext:
        """
        Forward pass: y = activation(W^T * x + b)
        
        Args:
            x: Input ciphertext (batch_size, input_size)
            scheme: CKKS scheme instance
        
        Returns:
            Output ciphertext (batch_size, output_size)
        """
        if not self.is_trained:
            raise ValueError("Layer weights not set - call set_weights() first")
        
        # Matrix multiplication: W^T * x
        output = self._encrypted_matrix_multiply(x, self.weights.T, scheme)
        
        # Add bias if present
        if self.bias is not None and self.config.use_bias:
            bias_ciphertext = scheme.encode(self.bias, scale=output.scale)
            bias_encrypted = scheme.encrypt(bias_ciphertext)
            output = scheme.add(output, bias_encrypted)
        
        # Apply activation function
        if self.activation_fn is not None:
            output = self.activation_fn(output, scheme)
        
        return output
    
    def _encrypted_matrix_multiply(self, x: CKKSCiphertext, matrix: np.ndarray, 
                                 scheme: CKKSScheme) -> CKKSCiphertext:
        """
        Encrypted matrix multiplication using rotations and additions.
        
        Args:
            x: Input ciphertext vector
            matrix: Plaintext matrix
            scheme: CKKS scheme instance
        
        Returns:
            Result of matrix multiplication
        """
        rows, cols = matrix.shape
        results = []
        
        for i in range(rows):
            # Compute dot product of x with row i of matrix
            row_plaintext = scheme.encode(matrix[i, :], scale=x.scale)
            row_product = scheme.multiply_plain(x, row_plaintext)
            
            # Sum elements to get scalar result
            row_sum = scheme.sum_elements(row_product)
            results.append(row_sum)
        
        # Combine results into output vector
        # This is a simplified approach - in practice would use more efficient packing
        return results[0] if len(results) == 1 else self._combine_results(results, scheme)
    
    def _combine_results(self, results: List[CKKSCiphertext], 
                        scheme: CKKSScheme) -> CKKSCiphertext:
        """Combine multiple scalar results into a vector."""
        # Simplified implementation - would use proper vector packing
        combined = results[0]
        for result in results[1:]:
            combined = scheme.add(combined, result)
        return combined


class EncryptedConv2DLayer(EncryptedLayer):
    """Encrypted 2D convolutional layer."""
    
    def __init__(self, config: LayerConfig):
        """
        Initialize encrypted conv2d layer.
        
        Args:
            config: Layer configuration with kernel_size, stride, padding
        """
        super().__init__(config)
        
        if config.kernel_size is None:
            raise ValueError("kernel_size must be specified for Conv2D layer")
        
        self.kernel_size = config.kernel_size
        self.stride = config.stride or (1, 1)
        self.padding = config.padding or "valid"
        self.activation_fn = self._get_activation_function(config.activation)
    
    def _get_activation_function(self, activation: Optional[str]) -> Optional[Callable]:
        """Get activation function by name."""
        if activation is None:
            return None
        elif activation.lower() == "relu":
            return ActivationFunction.relu_approximation
        elif activation.lower() == "sigmoid":
            return ActivationFunction.polynomial_approximation
        else:
            raise ValueError(f"Unsupported activation function: {activation}")
    
    def set_weights(self, weights: np.ndarray, bias: Optional[np.ndarray] = None):
        """
        Set convolutional weights and bias.
        
        Args:
            weights: Kernel weights (kernel_h, kernel_w, input_channels, output_channels)
            bias: Bias vector (output_channels,)
        """
        expected_shape = (*self.kernel_size, self.config.input_size, self.config.output_size)
        if weights.shape != expected_shape:
            raise ValueError(f"Weight shape {weights.shape} doesn't match expected {expected_shape}")
        
        self.weights = weights
        
        if bias is not None:
            if bias.shape != (self.config.output_size,):
                raise ValueError(f"Bias shape {bias.shape} doesn't match expected {(self.config.output_size,)}")
            self.bias = bias
        
        self.is_trained = True
    
    def forward(self, x: CKKSCiphertext, scheme: CKKSScheme) -> CKKSCiphertext:
        """
        Forward pass: convolution operation.
        
        Args:
            x: Input ciphertext (batch, height, width, channels)
            scheme: CKKS scheme instance
        
        Returns:
            Output ciphertext after convolution
        """
        if not self.is_trained:
            raise ValueError("Layer weights not set - call set_weights() first")
        
        # Simplified convolution implementation
        # In practice, would use efficient im2col or FFT-based convolution
        output = self._encrypted_convolution(x, scheme)
        
        # Add bias if present
        if self.bias is not None and self.config.use_bias:
            bias_ciphertext = scheme.encode(self.bias, scale=output.scale)
            bias_encrypted = scheme.encrypt(bias_ciphertext)
            output = scheme.add(output, bias_encrypted)
        
        # Apply activation function
        if self.activation_fn is not None:
            output = self.activation_fn(output, scheme)
        
        return output
    
    def _encrypted_convolution(self, x: CKKSCiphertext, scheme: CKKSScheme) -> CKKSCiphertext:
        """
        Perform encrypted convolution using rotations and multiplications.
        
        Args:
            x: Input ciphertext
            scheme: CKKS scheme instance
        
        Returns:
            Convolution result
        """
        # Simplified implementation
        # Real implementation would handle proper 2D convolution with rotations
        kernel_flat = self.weights.flatten()
        kernel_plaintext = scheme.encode(kernel_flat, scale=x.scale)
        
        # Multiply by flattened kernel (simplified)
        result = scheme.multiply_plain(x, kernel_plaintext)
        
        return result


class EncryptedNeuralNetwork:
    """
    Complete encrypted neural network supporting various layer types.
    
    Enables privacy-preserving inference and training on encrypted data.
    """
    
    def __init__(self, scheme_config: FHEConfiguration, 
                 network_config: List[LayerConfig]):
        """
        Initialize encrypted neural network.
        
        Args:
            scheme_config: FHE scheme configuration
            network_config: List of layer configurations
        """
        self.scheme_config = scheme_config
        self.network_config = network_config
        
        # Initialize CKKS scheme
        self.scheme = CKKSScheme(scheme_config)
        self.keys = None
        
        # Initialize layers
        self.layers = []
        self._build_network()
        
        self.is_trained = False
        self.training_history = []
        
        logger.info(f"Initialized encrypted neural network with {len(self.layers)} layers")
    
    def _build_network(self):
        """Build the neural network layers."""
        for config in self.network_config:
            if config.layer_type.lower() == "dense":
                layer = EncryptedDenseLayer(config)
            elif config.layer_type.lower() == "conv2d":
                layer = EncryptedConv2DLayer(config)
            else:
                raise ValueError(f"Unsupported layer type: {config.layer_type}")
            
            self.layers.append(layer)
    
    def generate_keys(self) -> Dict[str, Any]:
        """
        Generate encryption keys for the network.
        
        Returns:
            Generated keys
        """
        self.keys = self.scheme.generate_keys()
        logger.info("Generated encryption keys for neural network")
        return self.keys
    
    def load_pretrained_weights(self, weights: List[Dict[str, np.ndarray]]):
        """
        Load pretrained weights for all layers.
        
        Args:
            weights: List of weight dictionaries for each layer
        """
        if len(weights) != len(self.layers):
            raise ValueError(f"Number of weight sets ({len(weights)}) doesn't match "
                           f"number of layers ({len(self.layers)})")
        
        for layer, layer_weights in zip(self.layers, weights):
            W = layer_weights.get("weights", layer_weights.get("W"))
            b = layer_weights.get("bias", layer_weights.get("b"))
            
            if W is None:
                raise ValueError("Weights not found in weight dictionary")
            
            layer.set_weights(W, b)
        
        self.is_trained = True
        logger.info("Loaded pretrained weights for all layers")
    
    def encrypt_input(self, data: np.ndarray) -> CKKSCiphertext:
        """
        Encrypt input data.
        
        Args:
            data: Input data to encrypt
        
        Returns:
            Encrypted input
        """
        if self.keys is None:
            raise ValueError("Keys not generated - call generate_keys() first")
        
        # Flatten and encode data
        flat_data = data.flatten() if data.ndim > 1 else data
        plaintext = self.scheme.encode(flat_data.astype(complex))
        
        return self.scheme.encrypt(plaintext)
    
    def predict(self, encrypted_input: CKKSCiphertext) -> CKKSCiphertext:
        """
        Perform inference on encrypted data.
        
        Args:
            encrypted_input: Encrypted input data
        
        Returns:
            Encrypted prediction
        """
        if not self.is_trained:
            raise ValueError("Network not trained - load weights first")
        
        current = encrypted_input
        
        # Forward pass through all layers
        for i, layer in enumerate(self.layers):
            logger.debug(f"Processing layer {i + 1}/{len(self.layers)}")
            current = layer.forward(current, self.scheme)
            
            # Rescale periodically to manage noise growth
            if i % 2 == 1:  # Every other layer
                try:
                    current = self.scheme.rescale(current)
                except Exception as e:
                    logger.warning(f"Rescaling failed at layer {i}: {e}")
        
        return current
    
    def decrypt_output(self, encrypted_output: CKKSCiphertext) -> np.ndarray:
        """
        Decrypt network output.
        
        Args:
            encrypted_output: Encrypted network output
        
        Returns:
            Decrypted output as numpy array
        """
        if self.keys is None:
            raise ValueError("Keys not available for decryption")
        
        decrypted_plaintext = self.scheme.decrypt(encrypted_output)
        values = self.scheme.decode(decrypted_plaintext)
        
        # Convert complex values to real (take real part)
        real_values = np.array([v.real for v in values])
        
        return real_values
    
    def predict_on_plaintext(self, data: np.ndarray) -> np.ndarray:
        """
        End-to-end prediction: encrypt, predict, decrypt.
        
        Args:
            data: Input data
        
        Returns:
            Prediction results
        """
        # Encrypt input
        encrypted_input = self.encrypt_input(data)
        
        # Perform prediction
        encrypted_output = self.predict(encrypted_input)
        
        # Decrypt output
        output = self.decrypt_output(encrypted_output)
        
        return output
    
    def batch_predict(self, batch_data: List[np.ndarray]) -> List[np.ndarray]:
        """
        Predict on a batch of inputs.
        
        Args:
            batch_data: List of input arrays
        
        Returns:
            List of prediction results
        """
        results = []
        
        for i, data in enumerate(batch_data):
            logger.debug(f"Processing batch item {i + 1}/{len(batch_data)}")
            prediction = self.predict_on_plaintext(data)
            results.append(prediction)
        
        return results
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get information about the network architecture."""
        layer_info = []
        
        for i, (layer, config) in enumerate(zip(self.layers, self.network_config)):
            info = {
                "layer_index": i,
                "layer_type": config.layer_type,
                "input_size": config.input_size,
                "output_size": config.output_size,
                "activation": config.activation,
                "use_bias": config.use_bias,
                "is_trained": layer.is_trained
            }
            
            if config.layer_type.lower() == "conv2d":
                info.update({
                    "kernel_size": config.kernel_size,
                    "stride": config.stride,
                    "padding": config.padding
                })
            
            layer_info.append(info)
        
        return {
            "total_layers": len(self.layers),
            "is_trained": self.is_trained,
            "scheme_info": self.scheme.get_scheme_info(),
            "layers": layer_info,
            "keys_generated": self.keys is not None
        }
    
    def estimate_computation_time(self, input_size: int) -> Dict[str, float]:
        """
        Estimate computation time for the network.
        
        Args:
            input_size: Size of input data
        
        Returns:
            Time estimates for different operations
        """
        # Rough estimates based on layer types and sizes
        estimates = {
            "encryption_ms": input_size * 0.1,  # ~0.1ms per element
            "layer_computation_ms": 0,
            "decryption_ms": 100,  # Fixed overhead
            "total_ms": 0
        }
        
        for config in self.network_config:
            if config.layer_type.lower() == "dense":
                # Dense layer: input_size * output_size multiplications
                layer_time = config.input_size * config.output_size * 0.01
            elif config.layer_type.lower() == "conv2d":
                # Conv2D: kernel operations
                kernel_ops = config.kernel_size[0] * config.kernel_size[1] * config.input_size
                layer_time = kernel_ops * 0.02
            else:
                layer_time = 100  # Default estimate
            
            estimates["layer_computation_ms"] += layer_time
        
        estimates["total_ms"] = (estimates["encryption_ms"] + 
                               estimates["layer_computation_ms"] + 
                               estimates["decryption_ms"])
        
        return estimates
    
    def save_model(self, filepath: str):
        """
        Save the encrypted model to file.
        
        Args:
            filepath: Path to save the model
        """
        import pickle
        
        model_data = {
            "scheme_config": self.scheme_config,
            "network_config": self.network_config,
            "keys": self.keys,
            "is_trained": self.is_trained,
            "training_history": self.training_history
        }
        
        # Save layer weights
        layer_weights = []
        for layer in self.layers:
            weights_dict = {}
            if layer.weights is not None:
                weights_dict["weights"] = layer.weights
            if layer.bias is not None:
                weights_dict["bias"] = layer.bias
            layer_weights.append(weights_dict)
        
        model_data["layer_weights"] = layer_weights
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Saved encrypted model to {filepath}")
    
    @classmethod
    def load_model(cls, filepath: str) -> 'EncryptedNeuralNetwork':
        """
        Load an encrypted model from file.
        
        Args:
            filepath: Path to the saved model
        
        Returns:
            Loaded encrypted neural network
        """
        import pickle
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        # Create network
        network = cls(
            model_data["scheme_config"],
            model_data["network_config"]
        )
        
        # Restore keys and weights
        network.keys = model_data["keys"]
        network.is_trained = model_data["is_trained"]
        network.training_history = model_data["training_history"]
        
        # Load layer weights
        if "layer_weights" in model_data:
            network.load_pretrained_weights(model_data["layer_weights"])
        
        logger.info(f"Loaded encrypted model from {filepath}")
        return network