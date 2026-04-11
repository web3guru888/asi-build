"""
Encrypted linear models for regression and classification.

Implements privacy-preserving linear regression, logistic regression,
and other linear models using homomorphic encryption.
"""

import numpy as np
import math
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
import logging

from ..schemes.ckks import CKKSScheme, CKKSCiphertext, CKKSPlaintext
from ..core.base import FHEConfiguration, SchemeType, SecurityLevel

logger = logging.getLogger(__name__)


@dataclass
class LinearModelConfig:
    """Configuration for linear models."""
    regularization: str = "none"  # "none", "l1", "l2", "elastic_net"
    alpha: float = 0.01  # Regularization strength
    l1_ratio: float = 0.5  # For elastic net
    fit_intercept: bool = True
    normalize: bool = False
    max_iterations: int = 1000
    tolerance: float = 1e-6


class EncryptedLinearRegression:
    """
    Encrypted linear regression using homomorphic encryption.
    
    Supports various regularization methods and can perform both
    training and inference on encrypted data.
    """
    
    def __init__(self, config: LinearModelConfig, scheme_config: FHEConfiguration):
        """
        Initialize encrypted linear regression.
        
        Args:
            config: Linear model configuration
            scheme_config: FHE scheme configuration
        """
        self.config = config
        self.scheme_config = scheme_config
        
        # Initialize CKKS scheme
        self.scheme = CKKSScheme(scheme_config)
        self.keys = None
        
        # Model parameters
        self.weights = None
        self.intercept = None
        self.is_trained = False
        
        # Training statistics
        self.training_loss_history = []
        self.n_features = None
        self.feature_means = None
        self.feature_stds = None
        
        logger.info("Initialized encrypted linear regression")
    
    def generate_keys(self) -> Dict[str, Any]:
        """Generate encryption keys."""
        self.keys = self.scheme.generate_keys()
        logger.info("Generated encryption keys for linear regression")
        return self.keys
    
    def _normalize_features(self, X: np.ndarray) -> np.ndarray:
        """Normalize features if requested."""
        if not self.config.normalize:
            return X
        
        if self.feature_means is None:
            # First time - compute statistics
            self.feature_means = np.mean(X, axis=0)
            self.feature_stds = np.std(X, axis=0)
            # Avoid division by zero
            self.feature_stds[self.feature_stds == 0] = 1.0
        
        return (X - self.feature_means) / self.feature_stds
    
    def _add_intercept_column(self, X: np.ndarray) -> np.ndarray:
        """Add intercept column if requested."""
        if not self.config.fit_intercept:
            return X
        
        intercept_column = np.ones((X.shape[0], 1))
        return np.hstack([intercept_column, X])
    
    def fit_plaintext(self, X: np.ndarray, y: np.ndarray) -> 'EncryptedLinearRegression':
        """
        Fit the model using plaintext data (for comparison/initialization).
        
        Args:
            X: Training features (n_samples, n_features)
            y: Training targets (n_samples,)
        
        Returns:
            Self for method chaining
        """
        # Normalize features
        X_normalized = self._normalize_features(X)
        
        # Add intercept column
        X_with_intercept = self._add_intercept_column(X_normalized)
        
        self.n_features = X.shape[1]
        
        # Solve normal equations: w = (X^T X + λI)^(-1) X^T y
        XtX = X_with_intercept.T @ X_with_intercept
        Xty = X_with_intercept.T @ y
        
        # Add regularization
        if self.config.regularization == "l2":
            ridge_matrix = np.eye(XtX.shape[0]) * self.config.alpha
            if self.config.fit_intercept:
                ridge_matrix[0, 0] = 0  # Don't regularize intercept
            XtX += ridge_matrix
        
        # Solve for weights
        try:
            weights = np.linalg.solve(XtX, Xty)
        except np.linalg.LinAlgError:
            # Use pseudo-inverse if singular
            weights = np.linalg.pinv(XtX) @ Xty
        
        # Split weights and intercept
        if self.config.fit_intercept:
            self.intercept = weights[0]
            self.weights = weights[1:]
        else:
            self.intercept = 0.0
            self.weights = weights
        
        self.is_trained = True
        
        # Compute training loss
        predictions = self.predict_plaintext(X)
        mse = np.mean((y - predictions) ** 2)
        self.training_loss_history.append(mse)
        
        logger.info(f"Trained linear regression - MSE: {mse:.6f}")
        return self
    
    def fit_encrypted(self, X_encrypted: List[CKKSCiphertext], 
                     y_encrypted: CKKSCiphertext,
                     learning_rate: float = 0.01) -> 'EncryptedLinearRegression':
        """
        Fit the model using encrypted data with gradient descent.
        
        Args:
            X_encrypted: Encrypted training features
            y_encrypted: Encrypted training targets
            learning_rate: Learning rate for gradient descent
        
        Returns:
            Self for method chaining
        """
        if self.keys is None:
            raise ValueError("Keys not generated - call generate_keys() first")
        
        n_samples = len(X_encrypted)
        n_features = self.scheme.encoder.slots  # Assuming packed encoding
        
        # Initialize weights (encrypted zeros)
        zero_weights = self.scheme.encrypt(self.scheme.encode([0.0] * n_features))
        current_weights = zero_weights
        
        zero_intercept = self.scheme.encrypt(self.scheme.encode([0.0]))
        current_intercept = zero_intercept
        
        for iteration in range(self.config.max_iterations):
            logger.debug(f"Encrypted training iteration {iteration + 1}")
            
            # Compute predictions: y_pred = X @ w + b
            predictions = []
            for x_sample in X_encrypted:
                pred = self.scheme.dot_product(x_sample, current_weights)
                pred = self.scheme.add(pred, current_intercept)
                predictions.append(pred)
            
            # Compute gradients (simplified)
            # gradient_w = (1/n) * X^T @ (y_pred - y)
            # gradient_b = (1/n) * sum(y_pred - y)
            
            weight_gradient = zero_weights
            intercept_gradient = zero_intercept
            
            for i, (x_sample, y_sample, pred) in enumerate(zip(X_encrypted, 
                                                              [y_encrypted] * n_samples, 
                                                              predictions)):
                # error = pred - y_sample
                error = self.scheme.subtract(pred, y_sample)
                
                # Accumulate gradients
                x_error = self.scheme.multiply(x_sample, error)
                weight_gradient = self.scheme.add(weight_gradient, x_error)
                intercept_gradient = self.scheme.add(intercept_gradient, error)
            
            # Average gradients
            avg_factor = 1.0 / n_samples
            weight_gradient = self.scheme.multiply_plain(weight_gradient, avg_factor)
            intercept_gradient = self.scheme.multiply_plain(intercept_gradient, avg_factor)
            
            # Update weights: w = w - lr * gradient
            lr_weight_grad = self.scheme.multiply_plain(weight_gradient, learning_rate)
            lr_intercept_grad = self.scheme.multiply_plain(intercept_gradient, learning_rate)
            
            current_weights = self.scheme.subtract(current_weights, lr_weight_grad)
            current_intercept = self.scheme.subtract(current_intercept, lr_intercept_grad)
            
            # Rescale to manage noise
            if iteration % 5 == 0:
                try:
                    current_weights = self.scheme.rescale(current_weights)
                    current_intercept = self.scheme.rescale(current_intercept)
                except Exception as e:
                    logger.warning(f"Rescaling failed at iteration {iteration}: {e}")
        
        # Store encrypted weights (would need to decrypt for practical use)
        self.encrypted_weights = current_weights
        self.encrypted_intercept = current_intercept
        self.is_trained = True
        
        logger.info(f"Completed encrypted training with {self.config.max_iterations} iterations")
        return self
    
    def encrypt_features(self, X: np.ndarray) -> List[CKKSCiphertext]:
        """
        Encrypt feature matrix.
        
        Args:
            X: Feature matrix (n_samples, n_features)
        
        Returns:
            List of encrypted feature vectors
        """
        if self.keys is None:
            raise ValueError("Keys not generated - call generate_keys() first")
        
        # Normalize features
        X_normalized = self._normalize_features(X)
        
        encrypted_samples = []
        for i in range(X_normalized.shape[0]):
            sample = X_normalized[i, :].astype(complex)
            plaintext = self.scheme.encode(sample)
            encrypted = self.scheme.encrypt(plaintext)
            encrypted_samples.append(encrypted)
        
        return encrypted_samples
    
    def encrypt_targets(self, y: np.ndarray) -> CKKSCiphertext:
        """
        Encrypt target vector.
        
        Args:
            y: Target vector (n_samples,)
        
        Returns:
            Encrypted targets
        """
        if self.keys is None:
            raise ValueError("Keys not generated - call generate_keys() first")
        
        y_complex = y.astype(complex)
        plaintext = self.scheme.encode(y_complex)
        return self.scheme.encrypt(plaintext)
    
    def predict_plaintext(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions on plaintext data.
        
        Args:
            X: Input features (n_samples, n_features)
        
        Returns:
            Predictions (n_samples,)
        """
        if not self.is_trained:
            raise ValueError("Model not trained - call fit() first")
        
        # Normalize features
        X_normalized = self._normalize_features(X)
        
        # Compute predictions
        predictions = X_normalized @ self.weights
        
        if self.config.fit_intercept:
            predictions += self.intercept
        
        return predictions
    
    def predict_encrypted(self, X_encrypted: List[CKKSCiphertext]) -> List[CKKSCiphertext]:
        """
        Make predictions on encrypted data.
        
        Args:
            X_encrypted: Encrypted input features
        
        Returns:
            Encrypted predictions
        """
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        if not hasattr(self, 'encrypted_weights'):
            # Encrypt plaintext weights for prediction
            weights_plaintext = self.scheme.encode(self.weights.astype(complex))
            self.encrypted_weights = self.scheme.encrypt(weights_plaintext)
            
            intercept_plaintext = self.scheme.encode([self.intercept])
            self.encrypted_intercept = self.scheme.encrypt(intercept_plaintext)
        
        predictions = []
        for x_sample in X_encrypted:
            # y = x @ w + b
            pred = self.scheme.dot_product(x_sample, self.encrypted_weights)
            if self.config.fit_intercept:
                pred = self.scheme.add(pred, self.encrypted_intercept)
            predictions.append(pred)
        
        return predictions
    
    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        """
        Compute R² score.
        
        Args:
            X: Test features
            y: True targets
        
        Returns:
            R² score
        """
        predictions = self.predict_plaintext(X)
        
        ss_res = np.sum((y - predictions) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        
        r2 = 1 - (ss_res / ss_tot)
        return r2
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        info = {
            "model_type": "Linear Regression",
            "is_trained": self.is_trained,
            "n_features": self.n_features,
            "config": {
                "regularization": self.config.regularization,
                "alpha": self.config.alpha,
                "fit_intercept": self.config.fit_intercept,
                "normalize": self.config.normalize
            },
            "training_history": {
                "n_iterations": len(self.training_loss_history),
                "final_loss": self.training_loss_history[-1] if self.training_loss_history else None
            }
        }
        
        if self.weights is not None:
            info["weights_shape"] = self.weights.shape
            info["intercept"] = float(self.intercept) if self.intercept is not None else None
        
        return info


class EncryptedLogisticRegression:
    """
    Encrypted logistic regression for binary classification.
    
    Uses polynomial approximations for the sigmoid function to enable
    homomorphic evaluation.
    """
    
    def __init__(self, config: LinearModelConfig, scheme_config: FHEConfiguration):
        """
        Initialize encrypted logistic regression.
        
        Args:
            config: Linear model configuration
            scheme_config: FHE scheme configuration
        """
        self.config = config
        self.scheme_config = scheme_config
        
        # Initialize CKKS scheme
        self.scheme = CKKSScheme(scheme_config)
        self.keys = None
        
        # Model parameters
        self.weights = None
        self.intercept = None
        self.is_trained = False
        
        # Training statistics
        self.training_loss_history = []
        self.n_features = None
        
        logger.info("Initialized encrypted logistic regression")
    
    def generate_keys(self) -> Dict[str, Any]:
        """Generate encryption keys."""
        self.keys = self.scheme.generate_keys()
        logger.info("Generated encryption keys for logistic regression")
        return self.keys
    
    def _sigmoid_approximation(self, x: CKKSCiphertext) -> CKKSCiphertext:
        """
        Polynomial approximation of sigmoid function.
        
        Args:
            x: Input ciphertext
        
        Returns:
            Sigmoid-activated ciphertext
        """
        # sigmoid(x) ≈ 0.5 + 0.197*x - 0.004*x^3 (for x in [-5, 5])
        coeffs = [0.5, 0.197, 0, -0.004]
        return self.scheme.polynomial_evaluation(x, coeffs)
    
    def fit_plaintext(self, X: np.ndarray, y: np.ndarray, 
                     learning_rate: float = 0.01) -> 'EncryptedLogisticRegression':
        """
        Fit the model using plaintext data with gradient descent.
        
        Args:
            X: Training features (n_samples, n_features)
            y: Training targets (n_samples,) - should be 0 or 1
            learning_rate: Learning rate for gradient descent
        
        Returns:
            Self for method chaining
        """
        n_samples, n_features = X.shape
        self.n_features = n_features
        
        # Initialize weights
        self.weights = np.random.normal(0, 0.01, n_features)
        self.intercept = 0.0 if self.config.fit_intercept else None
        
        # Gradient descent
        for iteration in range(self.config.max_iterations):
            # Forward pass
            z = X @ self.weights
            if self.config.fit_intercept:
                z += self.intercept
            
            # Sigmoid activation
            predictions = 1 / (1 + np.exp(-np.clip(z, -250, 250)))  # Clip for stability
            
            # Compute loss (cross-entropy)
            loss = -np.mean(y * np.log(predictions + 1e-15) + 
                           (1 - y) * np.log(1 - predictions + 1e-15))
            
            # Add regularization
            if self.config.regularization == "l2":
                loss += 0.5 * self.config.alpha * np.sum(self.weights ** 2)
            
            self.training_loss_history.append(loss)
            
            # Compute gradients
            error = predictions - y
            weight_grad = (X.T @ error) / n_samples
            
            # Add regularization gradient
            if self.config.regularization == "l2":
                weight_grad += self.config.alpha * self.weights
            
            # Update weights
            self.weights -= learning_rate * weight_grad
            
            if self.config.fit_intercept:
                intercept_grad = np.mean(error)
                self.intercept -= learning_rate * intercept_grad
            
            # Check convergence
            if iteration > 0 and abs(self.training_loss_history[-2] - loss) < self.config.tolerance:
                logger.info(f"Converged after {iteration + 1} iterations")
                break
        
        self.is_trained = True
        logger.info(f"Trained logistic regression - Final loss: {loss:.6f}")
        return self
    
    def predict_plaintext(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions on plaintext data.
        
        Args:
            X: Input features (n_samples, n_features)
        
        Returns:
            Predicted probabilities (n_samples,)
        """
        if not self.is_trained:
            raise ValueError("Model not trained - call fit() first")
        
        z = X @ self.weights
        if self.config.fit_intercept:
            z += self.intercept
        
        # Sigmoid activation
        probabilities = 1 / (1 + np.exp(-np.clip(z, -250, 250)))
        
        return probabilities
    
    def predict_encrypted(self, X_encrypted: List[CKKSCiphertext]) -> List[CKKSCiphertext]:
        """
        Make predictions on encrypted data.
        
        Args:
            X_encrypted: Encrypted input features
        
        Returns:
            Encrypted predicted probabilities
        """
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        # Encrypt weights if not already done
        if not hasattr(self, 'encrypted_weights'):
            weights_plaintext = self.scheme.encode(self.weights.astype(complex))
            self.encrypted_weights = self.scheme.encrypt(weights_plaintext)
            
            if self.config.fit_intercept:
                intercept_plaintext = self.scheme.encode([self.intercept])
                self.encrypted_intercept = self.scheme.encrypt(intercept_plaintext)
        
        predictions = []
        for x_sample in X_encrypted:
            # z = x @ w + b
            z = self.scheme.dot_product(x_sample, self.encrypted_weights)
            if self.config.fit_intercept:
                z = self.scheme.add(z, self.encrypted_intercept)
            
            # Apply sigmoid approximation
            prob = self._sigmoid_approximation(z)
            predictions.append(prob)
        
        return predictions
    
    def predict_classes_plaintext(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """
        Predict binary classes.
        
        Args:
            X: Input features
            threshold: Classification threshold
        
        Returns:
            Predicted classes (0 or 1)
        """
        probabilities = self.predict_plaintext(X)
        return (probabilities >= threshold).astype(int)
    
    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        """
        Compute classification accuracy.
        
        Args:
            X: Test features
            y: True labels
        
        Returns:
            Accuracy score
        """
        predictions = self.predict_classes_plaintext(X)
        return np.mean(predictions == y)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        info = {
            "model_type": "Logistic Regression",
            "is_trained": self.is_trained,
            "n_features": self.n_features,
            "config": {
                "regularization": self.config.regularization,
                "alpha": self.config.alpha,
                "fit_intercept": self.config.fit_intercept,
                "max_iterations": self.config.max_iterations
            },
            "training_history": {
                "n_iterations": len(self.training_loss_history),
                "final_loss": self.training_loss_history[-1] if self.training_loss_history else None
            }
        }
        
        if self.weights is not None:
            info["weights_shape"] = self.weights.shape
            info["intercept"] = float(self.intercept) if self.intercept is not None else None
        
        return info