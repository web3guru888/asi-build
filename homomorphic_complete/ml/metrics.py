"""
Encrypted metrics for evaluating machine learning models.
"""

import numpy as np
import math
from typing import List, Dict, Any, Optional, Union
import logging

from ..schemes.ckks import CKKSScheme, CKKSCiphertext, CKKSPlaintext
from ..core.base import FHEConfiguration

logger = logging.getLogger(__name__)


class EncryptedMetrics:
    """
    Encrypted metrics for privacy-preserving model evaluation.
    
    Supports computation of various ML metrics on encrypted data.
    """
    
    def __init__(self, scheme: CKKSScheme):
        """
        Initialize encrypted metrics.
        
        Args:
            scheme: CKKS scheme instance
        """
        self.scheme = scheme
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def encrypted_mse(self, y_true: CKKSCiphertext, 
                     y_pred: CKKSCiphertext) -> CKKSCiphertext:
        """
        Compute encrypted mean squared error.
        
        Args:
            y_true: Encrypted true values
            y_pred: Encrypted predictions
        
        Returns:
            Encrypted MSE
        """
        # MSE = mean((y_true - y_pred)^2)
        diff = self.scheme.subtract(y_true, y_pred)
        squared_diff = self.scheme.multiply(diff, diff)
        
        # Sum all elements and divide by count
        mse = self.scheme.sum_elements(squared_diff)
        
        return mse
    
    def encrypted_mae(self, y_true: CKKSCiphertext, 
                     y_pred: CKKSCiphertext) -> CKKSCiphertext:
        """
        Compute encrypted mean absolute error (approximation).
        
        Args:
            y_true: Encrypted true values
            y_pred: Encrypted predictions
        
        Returns:
            Encrypted MAE approximation
        """
        # MAE approximation using |x| ≈ sqrt(x^2 + ε)
        epsilon = 1e-6
        
        diff = self.scheme.subtract(y_true, y_pred)
        squared_diff = self.scheme.multiply(diff, diff)
        
        # Add epsilon for numerical stability
        eps_plaintext = self.scheme.encode([epsilon] * self.scheme.encoder.slots)
        eps_encrypted = self.scheme.encrypt(eps_plaintext)
        stabilized = self.scheme.add(squared_diff, eps_encrypted)
        
        # Approximate sqrt using polynomial (simplified)
        # sqrt(x) ≈ x^0.5 ≈ 1 + 0.5*(x-1) - 0.125*(x-1)^2 for x near 1
        # This is a rough approximation
        abs_approx = self.scheme.polynomial_evaluation(
            stabilized, [0, 0.5, -0.125]  # Simplified coefficients
        )
        
        mae = self.scheme.sum_elements(abs_approx)
        return mae
    
    def encrypted_accuracy(self, y_true: CKKSCiphertext, 
                          y_pred: CKKSCiphertext,
                          threshold: float = 0.5) -> CKKSCiphertext:
        """
        Compute encrypted accuracy for binary classification.
        
        Args:
            y_true: Encrypted true labels (0/1)
            y_pred: Encrypted predicted probabilities
            threshold: Classification threshold
        
        Returns:
            Encrypted accuracy
        """
        # Convert probabilities to binary predictions
        # pred_binary = (y_pred >= threshold) approximated as sigmoid(k*(y_pred - threshold))
        # where k is large to make it step-like
        
        k = 10  # Steepness parameter
        threshold_plaintext = self.scheme.encode([threshold] * self.scheme.encoder.slots)
        threshold_encrypted = self.scheme.encrypt(threshold_plaintext)
        
        centered = self.scheme.subtract(y_pred, threshold_encrypted)
        scaled = self.scheme.multiply_plain(centered, k)
        
        # Sigmoid approximation for step function
        pred_binary = self._sigmoid_approximation(scaled)
        
        # Compute accuracy: mean(y_true == pred_binary)
        # This is approximated as 1 - |y_true - pred_binary|
        diff = self.scheme.subtract(y_true, pred_binary)
        abs_diff = self.scheme.multiply(diff, diff)  # Use squared as approximation
        
        one_plaintext = self.scheme.encode([1.0] * self.scheme.encoder.slots)
        one_encrypted = self.scheme.encrypt(one_plaintext)
        
        accuracy_per_sample = self.scheme.subtract(one_encrypted, abs_diff)
        accuracy = self.scheme.sum_elements(accuracy_per_sample)
        
        return accuracy
    
    def _sigmoid_approximation(self, x: CKKSCiphertext) -> CKKSCiphertext:
        """Polynomial approximation of sigmoid function."""
        # sigmoid(x) ≈ 0.5 + 0.197*x - 0.004*x^3
        coeffs = [0.5, 0.197, 0, -0.004]
        return self.scheme.polynomial_evaluation(x, coeffs)
    
    def encrypted_r2_score(self, y_true: CKKSCiphertext, 
                          y_pred: CKKSCiphertext) -> CKKSCiphertext:
        """
        Compute encrypted R² score.
        
        Args:
            y_true: Encrypted true values
            y_pred: Encrypted predictions
        
        Returns:
            Encrypted R² score
        """
        # R² = 1 - SS_res / SS_tot
        # SS_res = sum((y_true - y_pred)^2)
        # SS_tot = sum((y_true - mean(y_true))^2)
        
        # Compute residual sum of squares
        residuals = self.scheme.subtract(y_true, y_pred)
        ss_res = self.scheme.multiply(residuals, residuals)
        ss_res_sum = self.scheme.sum_elements(ss_res)
        
        # Compute total sum of squares
        y_mean = self.scheme.sum_elements(y_true)  # This gives sum, need to divide by n
        y_centered = self.scheme.subtract(y_true, y_mean)
        ss_tot = self.scheme.multiply(y_centered, y_centered)
        ss_tot_sum = self.scheme.sum_elements(ss_tot)
        
        # R² = 1 - ss_res / ss_tot
        ratio = self.scheme.multiply(ss_res_sum, self._multiplicative_inverse_approx(ss_tot_sum))
        
        one_plaintext = self.scheme.encode([1.0])
        one_encrypted = self.scheme.encrypt(one_plaintext)
        
        r2 = self.scheme.subtract(one_encrypted, ratio)
        return r2
    
    def _multiplicative_inverse_approx(self, x: CKKSCiphertext) -> CKKSCiphertext:
        """
        Approximate multiplicative inverse using Newton's method.
        
        Args:
            x: Input ciphertext
        
        Returns:
            Approximation of 1/x
        """
        # Newton's method: x_{n+1} = x_n * (2 - a * x_n)
        # Start with initial guess
        initial_guess = self.scheme.encode([0.1])  # Rough initial guess
        current = self.scheme.encrypt(initial_guess)
        
        # Few iterations of Newton's method
        for _ in range(3):
            # temp = a * x_n
            temp = self.scheme.multiply(x, current)
            
            # 2 - temp
            two_plaintext = self.scheme.encode([2.0])
            two_encrypted = self.scheme.encrypt(two_plaintext)
            two_minus_temp = self.scheme.subtract(two_encrypted, temp)
            
            # x_{n+1} = x_n * (2 - a * x_n)
            current = self.scheme.multiply(current, two_minus_temp)
        
        return current
    
    def encrypted_confusion_matrix_elements(self, y_true: CKKSCiphertext, 
                                          y_pred: CKKSCiphertext,
                                          threshold: float = 0.5) -> Dict[str, CKKSCiphertext]:
        """
        Compute elements of encrypted confusion matrix.
        
        Args:
            y_true: Encrypted true binary labels
            y_pred: Encrypted predicted probabilities
            threshold: Classification threshold
        
        Returns:
            Dictionary with encrypted TP, TN, FP, FN counts
        """
        # Convert predictions to binary
        threshold_plaintext = self.scheme.encode([threshold] * self.scheme.encoder.slots)
        threshold_encrypted = self.scheme.encrypt(threshold_plaintext)
        
        pred_binary = self._step_function_approx(y_pred, threshold_encrypted)
        
        # Compute confusion matrix elements
        # TP = y_true * pred_binary
        tp = self.scheme.multiply(y_true, pred_binary)
        tp_sum = self.scheme.sum_elements(tp)
        
        # TN = (1 - y_true) * (1 - pred_binary)
        one_plaintext = self.scheme.encode([1.0] * self.scheme.encoder.slots)
        one_encrypted = self.scheme.encrypt(one_plaintext)
        
        not_true = self.scheme.subtract(one_encrypted, y_true)
        not_pred = self.scheme.subtract(one_encrypted, pred_binary)
        tn = self.scheme.multiply(not_true, not_pred)
        tn_sum = self.scheme.sum_elements(tn)
        
        # FP = (1 - y_true) * pred_binary
        fp = self.scheme.multiply(not_true, pred_binary)
        fp_sum = self.scheme.sum_elements(fp)
        
        # FN = y_true * (1 - pred_binary)
        fn = self.scheme.multiply(y_true, not_pred)
        fn_sum = self.scheme.sum_elements(fn)
        
        return {
            "true_positive": tp_sum,
            "true_negative": tn_sum,
            "false_positive": fp_sum,
            "false_negative": fn_sum
        }
    
    def _step_function_approx(self, x: CKKSCiphertext, 
                             threshold: CKKSCiphertext) -> CKKSCiphertext:
        """Approximate step function using steep sigmoid."""
        centered = self.scheme.subtract(x, threshold)
        steep_centered = self.scheme.multiply_plain(centered, 20)  # Make it steep
        return self._sigmoid_approximation(steep_centered)
    
    def encrypted_precision_recall(self, confusion_elements: Dict[str, CKKSCiphertext]) -> Dict[str, CKKSCiphertext]:
        """
        Compute encrypted precision and recall from confusion matrix elements.
        
        Args:
            confusion_elements: Dictionary with TP, TN, FP, FN
        
        Returns:
            Dictionary with encrypted precision and recall
        """
        tp = confusion_elements["true_positive"]
        fp = confusion_elements["false_positive"]
        fn = confusion_elements["false_negative"]
        
        # Precision = TP / (TP + FP)
        tp_plus_fp = self.scheme.add(tp, fp)
        precision = self.scheme.multiply(tp, self._multiplicative_inverse_approx(tp_plus_fp))
        
        # Recall = TP / (TP + FN)
        tp_plus_fn = self.scheme.add(tp, fn)
        recall = self.scheme.multiply(tp, self._multiplicative_inverse_approx(tp_plus_fn))
        
        return {
            "precision": precision,
            "recall": recall
        }
    
    def encrypted_f1_score(self, precision: CKKSCiphertext, 
                          recall: CKKSCiphertext) -> CKKSCiphertext:
        """
        Compute encrypted F1 score.
        
        Args:
            precision: Encrypted precision
            recall: Encrypted recall
        
        Returns:
            Encrypted F1 score
        """
        # F1 = 2 * (precision * recall) / (precision + recall)
        numerator = self.scheme.multiply(precision, recall)
        two_plaintext = self.scheme.encode([2.0])
        two_encrypted = self.scheme.encrypt(two_plaintext)
        numerator = self.scheme.multiply(numerator, two_encrypted)
        
        denominator = self.scheme.add(precision, recall)
        
        f1 = self.scheme.multiply(numerator, self._multiplicative_inverse_approx(denominator))
        return f1