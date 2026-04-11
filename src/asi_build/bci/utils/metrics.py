"""
BCI Performance Metrics

Comprehensive metrics for evaluating BCI system performance.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


class BCIMetrics:
    """Performance metrics for BCI systems"""

    @staticmethod
    def information_transfer_rate(accuracy: float, n_classes: int, selection_time: float) -> float:
        """
        Calculate Information Transfer Rate (ITR) in bits/minute

        Parameters:
        accuracy: Classification accuracy (0-1)
        n_classes: Number of classes
        selection_time: Time per selection in seconds
        """
        if accuracy <= 1 / n_classes:
            return 0.0

        # ITR formula from Wolpaw et al.
        p = max(accuracy, 1e-10)  # Avoid log(0)

        if p >= 1.0:
            p = 0.999  # Avoid log(0)

        bits_per_selection = (
            np.log2(n_classes) + p * np.log2(p) + (1 - p) * np.log2((1 - p) / (n_classes - 1))
        )
        selections_per_minute = 60.0 / selection_time

        itr = bits_per_selection * selections_per_minute

        return max(0.0, itr)

    @staticmethod
    def classification_metrics(
        y_true: np.ndarray, y_pred: np.ndarray, y_proba: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """Compute comprehensive classification metrics"""
        metrics = {}

        # Basic metrics
        metrics["accuracy"] = float(accuracy_score(y_true, y_pred))

        # Multi-class metrics
        metrics["precision_macro"] = float(
            precision_score(y_true, y_pred, average="macro", zero_division=0)
        )
        metrics["precision_micro"] = float(
            precision_score(y_true, y_pred, average="micro", zero_division=0)
        )
        metrics["recall_macro"] = float(
            recall_score(y_true, y_pred, average="macro", zero_division=0)
        )
        metrics["recall_micro"] = float(
            recall_score(y_true, y_pred, average="micro", zero_division=0)
        )
        metrics["f1_macro"] = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
        metrics["f1_micro"] = float(f1_score(y_true, y_pred, average="micro", zero_division=0))

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics["confusion_matrix"] = cm.tolist()

        # Per-class metrics
        class_report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        metrics["per_class_metrics"] = class_report

        # ROC-AUC for binary/multi-class
        if y_proba is not None:
            try:
                unique_classes = np.unique(y_true)
                if len(unique_classes) == 2:
                    # Binary classification
                    if y_proba.ndim == 2:
                        proba_positive = y_proba[:, 1]
                    else:
                        proba_positive = y_proba

                    metrics["roc_auc"] = float(roc_auc_score(y_true, proba_positive))

                    # ROC curve
                    fpr, tpr, thresholds = roc_curve(y_true, proba_positive)
                    metrics["roc_curve"] = {
                        "fpr": fpr.tolist(),
                        "tpr": tpr.tolist(),
                        "thresholds": thresholds.tolist(),
                    }
                else:
                    # Multi-class
                    metrics["roc_auc_ovr"] = float(
                        roc_auc_score(y_true, y_proba, multi_class="ovr", average="macro")
                    )
                    metrics["roc_auc_ovo"] = float(
                        roc_auc_score(y_true, y_proba, multi_class="ovo", average="macro")
                    )
            except Exception as e:
                logging.warning(f"ROC-AUC calculation failed: {e}")

        return metrics

    @staticmethod
    def temporal_metrics(
        timestamps: np.ndarray, predictions: np.ndarray, true_labels: np.ndarray
    ) -> Dict[str, float]:
        """Compute temporal performance metrics"""
        metrics = {}

        # Response time statistics
        if len(timestamps) > 1:
            response_times = np.diff(timestamps)
            metrics["mean_response_time"] = float(np.mean(response_times))
            metrics["std_response_time"] = float(np.std(response_times))
            metrics["min_response_time"] = float(np.min(response_times))
            metrics["max_response_time"] = float(np.max(response_times))

        # Accuracy over time (sliding window)
        window_size = min(10, len(predictions) // 4)
        if window_size > 0:
            sliding_accuracies = []
            for i in range(len(predictions) - window_size + 1):
                window_acc = accuracy_score(
                    true_labels[i : i + window_size], predictions[i : i + window_size]
                )
                sliding_accuracies.append(window_acc)

            if sliding_accuracies:
                metrics["sliding_accuracy_mean"] = float(np.mean(sliding_accuracies))
                metrics["sliding_accuracy_std"] = float(np.std(sliding_accuracies))
                metrics["accuracy_trend"] = (
                    float(np.corrcoef(range(len(sliding_accuracies)), sliding_accuracies)[0, 1])
                    if len(sliding_accuracies) > 1
                    else 0.0
                )

        return metrics

    @staticmethod
    def signal_quality_metrics(data: np.ndarray, sampling_rate: float) -> Dict[str, float]:
        """Compute signal quality metrics"""
        metrics = {}

        if data.ndim == 1:
            data = data.reshape(1, -1)

        n_channels, n_samples = data.shape

        # Per-channel metrics
        channel_metrics = []

        for ch in range(n_channels):
            ch_data = data[ch, :]
            ch_metrics = {}

            # Signal-to-noise ratio estimation
            from scipy.signal import welch

            f, psd = welch(ch_data, fs=sampling_rate, nperseg=256)

            # Signal power in EEG bands (1-40 Hz)
            signal_mask = (f >= 1) & (f <= 40)
            signal_power = np.trapezoid(psd[signal_mask], f[signal_mask])

            # Noise power in high frequencies (40-100 Hz)
            noise_mask = (f >= 40) & (f <= min(100, sampling_rate / 2 - 1))
            if np.any(noise_mask):
                noise_power = np.trapezoid(psd[noise_mask], f[noise_mask])
                ch_metrics["snr"] = float(signal_power / (noise_power + 1e-10))
            else:
                ch_metrics["snr"] = float(signal_power)

            # Dynamic range
            ch_metrics["dynamic_range"] = float(np.ptp(ch_data))

            # Variance
            ch_metrics["variance"] = float(np.var(ch_data))

            # Kurtosis (spikiness)
            from scipy.stats import kurtosis

            ch_metrics["kurtosis"] = float(kurtosis(ch_data))

            # Zero crossings
            zero_crossings = len(np.where(np.diff(np.sign(ch_data)))[0])
            ch_metrics["zero_crossings"] = zero_crossings

            channel_metrics.append(ch_metrics)

        # Aggregate metrics
        metrics["mean_snr"] = float(np.mean([cm["snr"] for cm in channel_metrics]))
        metrics["mean_dynamic_range"] = float(
            np.mean([cm["dynamic_range"] for cm in channel_metrics])
        )
        metrics["mean_variance"] = float(np.mean([cm["variance"] for cm in channel_metrics]))
        metrics["channel_metrics"] = channel_metrics

        return metrics

    @staticmethod
    def stability_metrics(accuracies: List[float], session_times: List[float]) -> Dict[str, float]:
        """Compute system stability metrics"""
        metrics = {}

        if len(accuracies) < 2:
            return metrics

        accuracies = np.array(accuracies)
        session_times = np.array(session_times)

        # Accuracy stability
        metrics["accuracy_mean"] = float(np.mean(accuracies))
        metrics["accuracy_std"] = float(np.std(accuracies))
        metrics["accuracy_cv"] = float(np.std(accuracies) / (np.mean(accuracies) + 1e-10))

        # Performance trend over time
        if len(session_times) == len(accuracies) and len(session_times) > 1:
            correlation = np.corrcoef(session_times, accuracies)[0, 1]
            metrics["performance_trend"] = float(correlation) if not np.isnan(correlation) else 0.0

        # Session length analysis
        metrics["mean_session_time"] = float(np.mean(session_times))
        metrics["session_time_std"] = float(np.std(session_times))

        return metrics

    @staticmethod
    def user_experience_metrics(
        response_times: List[float],
        error_rates: List[float],
        user_ratings: Optional[List[int]] = None,
    ) -> Dict[str, float]:
        """Compute user experience metrics"""
        metrics = {}

        if response_times:
            response_times = np.array(response_times)
            metrics["mean_response_time"] = float(np.mean(response_times))
            metrics["response_time_p95"] = float(np.percentile(response_times, 95))

            # Responsiveness score (lower is better)
            metrics["responsiveness_score"] = float(
                np.mean(response_times) + 2 * np.std(response_times)
            )

        if error_rates:
            error_rates = np.array(error_rates)
            metrics["mean_error_rate"] = float(np.mean(error_rates))
            metrics["error_rate_std"] = float(np.std(error_rates))

            # Reliability score
            metrics["reliability_score"] = float(1.0 - np.mean(error_rates))

        if user_ratings:
            user_ratings = np.array(user_ratings)
            metrics["mean_user_rating"] = float(np.mean(user_ratings))
            metrics["user_satisfaction_score"] = float(
                np.mean(user_ratings) / 5.0
            )  # Assuming 1-5 scale

        return metrics

    @staticmethod
    def comprehensive_report(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None,
        timestamps: Optional[np.ndarray] = None,
        signal_data: Optional[np.ndarray] = None,
        sampling_rate: Optional[float] = None,
        n_classes: Optional[int] = None,
        selection_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive BCI performance report"""
        report = {}

        # Classification metrics
        classification_metrics = BCIMetrics.classification_metrics(y_true, y_pred, y_proba)
        report["classification"] = classification_metrics

        # Information Transfer Rate
        if n_classes and selection_time:
            accuracy = classification_metrics["accuracy"]
            itr = BCIMetrics.information_transfer_rate(accuracy, n_classes, selection_time)
            report["information_transfer_rate"] = float(itr)

        # Temporal metrics
        if timestamps is not None:
            temporal_metrics = BCIMetrics.temporal_metrics(timestamps, y_pred, y_true)
            report["temporal"] = temporal_metrics

        # Signal quality metrics
        if signal_data is not None and sampling_rate is not None:
            signal_metrics = BCIMetrics.signal_quality_metrics(signal_data, sampling_rate)
            report["signal_quality"] = signal_metrics

        return report
