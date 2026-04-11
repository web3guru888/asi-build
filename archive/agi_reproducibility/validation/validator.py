"""
Result Validator

Advanced result validation system with statistical analysis, anomaly detection,
and comprehensive verification of AGI experiment outcomes.
"""

import json
import numpy as np
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path
import scipy.stats as stats
from dataclasses import dataclass
import hashlib

from ..core.config import PlatformConfig
from ..core.exceptions import *


@dataclass
class ValidationRule:
    """Validation rule definition."""
    name: str
    rule_type: str  # 'statistical', 'logical', 'structural', 'semantic'
    parameters: Dict[str, Any]
    severity: str  # 'error', 'warning', 'info'
    description: str


@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule_name: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any]
    severity: str
    timestamp: datetime


class ResultValidator:
    """
    Comprehensive result validation system for AGI experiments.
    
    Features:
    - Statistical significance testing
    - Anomaly detection using multiple methods
    - Structural validation of results
    - Semantic consistency checking
    - Performance regression detection
    - Cross-experiment comparison
    - Confidence intervals and uncertainty quantification
    - Domain-specific AGI validation (symbolic reasoning, consciousness metrics, etc.)
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.validation_rules: List[ValidationRule] = []
        self.results_history: Dict[str, List[Dict[str, Any]]] = {}
        
    async def initialize(self) -> None:
        """Initialize the result validator."""
        await self._load_default_validation_rules()
        
    async def _load_default_validation_rules(self) -> None:
        """Load default validation rules for AGI experiments."""
        default_rules = [
            ValidationRule(
                name="statistical_significance",
                rule_type="statistical",
                parameters={
                    "significance_level": self.config.benchmarks.statistical_significance,
                    "min_samples": 5,
                    "test_type": "auto"
                },
                severity="warning",
                description="Check if results are statistically significant"
            ),
            ValidationRule(
                name="result_structure",
                rule_type="structural",
                parameters={
                    "required_fields": ["accuracy", "execution_time"],
                    "numeric_fields": ["accuracy", "precision", "recall", "f1_score"],
                    "range_checks": {
                        "accuracy": [0.0, 1.0],
                        "precision": [0.0, 1.0],
                        "recall": [0.0, 1.0]
                    }
                },
                severity="error",
                description="Validate basic result structure and ranges"
            ),
            ValidationRule(
                name="performance_regression",
                rule_type="statistical",
                parameters={
                    "threshold_percent": 10.0,
                    "lookback_window": 10,
                    "metric_names": ["accuracy", "execution_time"]
                },
                severity="warning",
                description="Detect performance regressions compared to historical results"
            ),
            ValidationRule(
                name="anomaly_detection",
                rule_type="statistical",
                parameters={
                    "method": "isolation_forest",
                    "contamination": 0.1,
                    "features": ["accuracy", "execution_time", "memory_usage"]
                },
                severity="warning",
                description="Detect anomalous results using machine learning"
            ),
            ValidationRule(
                name="consciousness_metrics",
                rule_type="semantic",
                parameters={
                    "required_metrics": ["integration_score", "differentiation_score", "global_workspace_activity"],
                    "phi_threshold": 0.1,
                    "consistency_check": True
                },
                severity="warning",
                description="Validate consciousness-related metrics for AGI experiments"
            ),
            ValidationRule(
                name="symbolic_reasoning_consistency",
                rule_type="logical",
                parameters={
                    "check_logical_consistency": True,
                    "validate_inference_chains": True,
                    "truth_value_ranges": True
                },
                severity="error",
                description="Validate symbolic reasoning results for logical consistency"
            )
        ]
        
        self.validation_rules.extend(default_rules)
    
    async def validate_results(self, experiment_id: str, results: Dict[str, Any],
                             custom_rules: List[ValidationRule] = None) -> Dict[str, Any]:
        """
        Validate experiment results using configured rules.
        
        Args:
            experiment_id: Unique experiment identifier
            results: Experiment results to validate
            custom_rules: Additional custom validation rules
            
        Returns:
            Dict containing validation results and overall score
        """
        validate_experiment_id(experiment_id)
        
        validation_start = datetime.now(timezone.utc)
        
        # Combine default and custom rules
        all_rules = self.validation_rules.copy()
        if custom_rules:
            all_rules.extend(custom_rules)
        
        validation_results = []
        
        # Run each validation rule
        for rule in all_rules:
            try:
                result = await self._apply_validation_rule(rule, experiment_id, results)
                validation_results.append(result)
            except Exception as e:
                error_result = ValidationResult(
                    rule_name=rule.name,
                    passed=False,
                    score=0.0,
                    message=f"Validation rule failed: {str(e)}",
                    details={"error": str(e)},
                    severity="error",
                    timestamp=datetime.now(timezone.utc)
                )
                validation_results.append(error_result)
        
        # Calculate overall validation score
        overall_score = self._calculate_overall_score(validation_results)
        
        # Generate validation summary
        summary = self._generate_validation_summary(validation_results, overall_score)
        
        # Store results for future comparisons
        await self._store_validation_results(experiment_id, results, validation_results)
        
        validation_end = datetime.now(timezone.utc)
        
        return {
            'experiment_id': experiment_id,
            'validation_timestamp': validation_start.isoformat(),
            'validation_duration': (validation_end - validation_start).total_seconds(),
            'overall_score': overall_score,
            'passed': overall_score >= 0.7,  # Configurable threshold
            'summary': summary,
            'individual_results': [
                {
                    'rule_name': r.rule_name,
                    'passed': r.passed,
                    'score': r.score,
                    'message': r.message,
                    'severity': r.severity,
                    'details': r.details
                } for r in validation_results
            ]
        }
    
    async def _apply_validation_rule(self, rule: ValidationRule, experiment_id: str,
                                   results: Dict[str, Any]) -> ValidationResult:
        """Apply a single validation rule."""
        if rule.rule_type == "statistical":
            return await self._apply_statistical_rule(rule, experiment_id, results)
        elif rule.rule_type == "structural":
            return await self._apply_structural_rule(rule, experiment_id, results)
        elif rule.rule_type == "logical":
            return await self._apply_logical_rule(rule, experiment_id, results)
        elif rule.rule_type == "semantic":
            return await self._apply_semantic_rule(rule, experiment_id, results)
        else:
            raise ValidationError(f"Unknown rule type: {rule.rule_type}")
    
    async def _apply_statistical_rule(self, rule: ValidationRule, experiment_id: str,
                                    results: Dict[str, Any]) -> ValidationResult:
        """Apply statistical validation rules."""
        if rule.name == "statistical_significance":
            return await self._check_statistical_significance(rule, experiment_id, results)
        elif rule.name == "performance_regression":
            return await self._check_performance_regression(rule, experiment_id, results)
        elif rule.name == "anomaly_detection":
            return await self._check_anomalies(rule, experiment_id, results)
        else:
            raise ValidationError(f"Unknown statistical rule: {rule.name}")
    
    async def _check_statistical_significance(self, rule: ValidationRule, experiment_id: str,
                                            results: Dict[str, Any]) -> ValidationResult:
        """Check if results are statistically significant."""
        params = rule.parameters
        significance_level = params.get('significance_level', 0.05)
        min_samples = params.get('min_samples', 5)
        
        # Extract numerical metrics from results
        metrics = self._extract_numerical_metrics(results)
        
        if not metrics:
            return ValidationResult(
                rule_name=rule.name,
                passed=False,
                score=0.0,
                message="No numerical metrics found for statistical analysis",
                details={},
                severity=rule.severity,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Get historical data for comparison
        historical_data = await self._get_historical_metrics(experiment_id, list(metrics.keys()))
        
        significance_results = {}
        overall_significant = True
        
        for metric_name, current_value in metrics.items():
            if metric_name in historical_data and len(historical_data[metric_name]) >= min_samples:
                historical_values = historical_data[metric_name]
                
                # Perform t-test
                t_stat, p_value = stats.ttest_1samp(historical_values, current_value)
                
                significant = p_value < significance_level
                significance_results[metric_name] = {
                    'current_value': current_value,
                    'historical_mean': np.mean(historical_values),
                    'historical_std': np.std(historical_values),
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'significant': significant,
                    'sample_size': len(historical_values)
                }
                
                if not significant:
                    overall_significant = False
        
        score = 1.0 if overall_significant else 0.5
        message = f"Statistical significance check {'passed' if overall_significant else 'failed'}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=overall_significant,
            score=score,
            message=message,
            details=significance_results,
            severity=rule.severity,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _check_performance_regression(self, rule: ValidationRule, experiment_id: str,
                                          results: Dict[str, Any]) -> ValidationResult:
        """Check for performance regressions."""
        params = rule.parameters
        threshold_percent = params.get('threshold_percent', 10.0)
        lookback_window = params.get('lookback_window', 10)
        metric_names = params.get('metric_names', ['accuracy'])
        
        # Get current metrics
        current_metrics = self._extract_numerical_metrics(results)
        
        # Get historical data
        historical_data = await self._get_historical_metrics(experiment_id, metric_names, lookback_window)
        
        regression_results = {}
        overall_passed = True
        
        for metric_name in metric_names:
            if metric_name in current_metrics and metric_name in historical_data:
                current_value = current_metrics[metric_name]
                historical_values = historical_data[metric_name]
                
                if len(historical_values) > 0:
                    historical_mean = np.mean(historical_values)
                    
                    # Calculate percentage change
                    if historical_mean != 0:
                        change_percent = ((current_value - historical_mean) / historical_mean) * 100
                    else:
                        change_percent = 0
                    
                    # For metrics like accuracy, negative change is bad
                    # For metrics like execution_time, positive change is bad
                    is_regression = False
                    if metric_name in ['accuracy', 'precision', 'recall', 'f1_score']:
                        is_regression = change_percent < -threshold_percent
                    elif metric_name in ['execution_time', 'memory_usage', 'error_rate']:
                        is_regression = change_percent > threshold_percent
                    
                    regression_results[metric_name] = {
                        'current_value': current_value,
                        'historical_mean': historical_mean,
                        'change_percent': change_percent,
                        'is_regression': is_regression,
                        'threshold': threshold_percent
                    }
                    
                    if is_regression:
                        overall_passed = False
        
        score = 1.0 if overall_passed else 0.3
        message = f"Performance regression check {'passed' if overall_passed else 'failed'}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=overall_passed,
            score=score,
            message=message,
            details=regression_results,
            severity=rule.severity,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _check_anomalies(self, rule: ValidationRule, experiment_id: str,
                             results: Dict[str, Any]) -> ValidationResult:
        """Check for anomalous results."""
        params = rule.parameters
        method = params.get('method', 'isolation_forest')
        contamination = params.get('contamination', 0.1)
        features = params.get('features', ['accuracy', 'execution_time'])
        
        # Extract current feature values
        current_features = []
        feature_names = []
        
        for feature in features:
            value = self._extract_metric_value(results, feature)
            if value is not None:
                current_features.append(value)
                feature_names.append(feature)
        
        if len(current_features) == 0:
            return ValidationResult(
                rule_name=rule.name,
                passed=True,
                score=0.5,
                message="No features available for anomaly detection",
                details={},
                severity=rule.severity,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Get historical data for anomaly detection
        historical_data = await self._get_historical_metrics(experiment_id, feature_names, 50)
        
        # Prepare data for anomaly detection
        historical_matrix = []
        for i in range(len(feature_names)):
            feature_name = feature_names[i]
            if feature_name in historical_data:
                historical_matrix.append(historical_data[feature_name])
        
        if not historical_matrix or len(historical_matrix[0]) < 10:
            return ValidationResult(
                rule_name=rule.name,
                passed=True,
                score=0.5,
                message="Insufficient historical data for anomaly detection",
                details={},
                severity=rule.severity,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Transpose to get samples x features format
        historical_matrix = np.array(historical_matrix).T
        current_sample = np.array(current_features).reshape(1, -1)
        
        # Apply anomaly detection
        is_anomaly = False
        anomaly_score = 0.0
        
        if method == 'isolation_forest':
            try:
                from sklearn.ensemble import IsolationForest
                
                detector = IsolationForest(contamination=contamination, random_state=42)
                detector.fit(historical_matrix)
                
                prediction = detector.predict(current_sample)[0]
                anomaly_score = detector.decision_function(current_sample)[0]
                
                is_anomaly = prediction == -1
                
            except ImportError:
                # Fallback to statistical method
                is_anomaly, anomaly_score = self._statistical_anomaly_detection(
                    current_features, historical_matrix
                )
        
        score = 0.2 if is_anomaly else 1.0
        message = f"Anomaly detection: {'anomaly detected' if is_anomaly else 'normal'}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=not is_anomaly,
            score=score,
            message=message,
            details={
                'is_anomaly': is_anomaly,
                'anomaly_score': anomaly_score,
                'features': dict(zip(feature_names, current_features)),
                'method': method
            },
            severity=rule.severity,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _statistical_anomaly_detection(self, current_features: List[float],
                                     historical_matrix: np.ndarray) -> Tuple[bool, float]:
        """Fallback statistical anomaly detection."""
        # Use multivariate Z-score
        historical_mean = np.mean(historical_matrix, axis=0)
        historical_std = np.std(historical_matrix, axis=0)
        
        z_scores = []
        for i, value in enumerate(current_features):
            if historical_std[i] > 0:
                z_score = abs((value - historical_mean[i]) / historical_std[i])
                z_scores.append(z_score)
        
        if z_scores:
            max_z_score = max(z_scores)
            is_anomaly = max_z_score > 3.0  # 3-sigma rule
            return is_anomaly, max_z_score
        
        return False, 0.0
    
    async def _apply_structural_rule(self, rule: ValidationRule, experiment_id: str,
                                   results: Dict[str, Any]) -> ValidationResult:
        """Apply structural validation rules."""
        params = rule.parameters
        required_fields = params.get('required_fields', [])
        numeric_fields = params.get('numeric_fields', [])
        range_checks = params.get('range_checks', {})
        
        issues = []
        
        # Check required fields
        for field in required_fields:
            if field not in results:
                issues.append(f"Missing required field: {field}")
        
        # Check numeric fields are actually numeric
        for field in numeric_fields:
            if field in results:
                try:
                    float(results[field])
                except (ValueError, TypeError):
                    issues.append(f"Field {field} is not numeric: {results[field]}")
        
        # Check value ranges
        for field, (min_val, max_val) in range_checks.items():
            if field in results:
                try:
                    value = float(results[field])
                    if value < min_val or value > max_val:
                        issues.append(f"Field {field} value {value} outside range [{min_val}, {max_val}]")
                except (ValueError, TypeError):
                    pass  # Already caught in numeric check
        
        passed = len(issues) == 0
        score = 1.0 if passed else max(0.0, 1.0 - (len(issues) * 0.2))
        message = f"Structural validation {'passed' if passed else 'failed'}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'issues': issues},
            severity=rule.severity,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _apply_logical_rule(self, rule: ValidationRule, experiment_id: str,
                                results: Dict[str, Any]) -> ValidationResult:
        """Apply logical consistency validation rules."""
        if rule.name == "symbolic_reasoning_consistency":
            return await self._check_symbolic_reasoning_consistency(rule, experiment_id, results)
        
        # Default logical rule implementation
        return ValidationResult(
            rule_name=rule.name,
            passed=True,
            score=1.0,
            message="Logical rule not implemented",
            details={},
            severity=rule.severity,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _check_symbolic_reasoning_consistency(self, rule: ValidationRule, experiment_id: str,
                                                  results: Dict[str, Any]) -> ValidationResult:
        """Check symbolic reasoning results for logical consistency."""
        params = rule.parameters
        
        consistency_issues = []
        
        # Check for PLN-style truth values
        if 'truth_values' in results:
            truth_values = results['truth_values']
            for atom, tv in truth_values.items():
                if isinstance(tv, dict) and 'strength' in tv and 'confidence' in tv:
                    strength = tv['strength']
                    confidence = tv['confidence']
                    
                    # Basic truth value consistency checks
                    if not (0 <= strength <= 1):
                        consistency_issues.append(f"Invalid strength for {atom}: {strength}")
                    if not (0 <= confidence <= 1):
                        consistency_issues.append(f"Invalid confidence for {atom}: {confidence}")
        
        # Check inference chain consistency
        if 'inference_chains' in results:
            chains = results['inference_chains']
            for chain in chains:
                if isinstance(chain, list) and len(chain) > 1:
                    # Check that each step follows logically from the previous
                    for i in range(1, len(chain)):
                        prev_step = chain[i-1]
                        curr_step = chain[i]
                        # This would require domain-specific logic validation
                        # For now, just check basic structure
                        if not isinstance(curr_step, dict) or 'rule' not in curr_step:
                            consistency_issues.append(f"Invalid inference step in chain: {curr_step}")
        
        passed = len(consistency_issues) == 0
        score = 1.0 if passed else max(0.0, 1.0 - (len(consistency_issues) * 0.3))
        message = f"Symbolic reasoning consistency {'passed' if passed else 'failed'}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'consistency_issues': consistency_issues},
            severity=rule.severity,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _apply_semantic_rule(self, rule: ValidationRule, experiment_id: str,
                                 results: Dict[str, Any]) -> ValidationResult:
        """Apply semantic validation rules."""
        if rule.name == "consciousness_metrics":
            return await self._check_consciousness_metrics(rule, experiment_id, results)
        
        # Default semantic rule implementation
        return ValidationResult(
            rule_name=rule.name,
            passed=True,
            score=1.0,
            message="Semantic rule not implemented",
            details={},
            severity=rule.severity,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _check_consciousness_metrics(self, rule: ValidationRule, experiment_id: str,
                                         results: Dict[str, Any]) -> ValidationResult:
        """Check consciousness-related metrics for validity."""
        params = rule.parameters
        required_metrics = params.get('required_metrics', [])
        phi_threshold = params.get('phi_threshold', 0.1)
        
        issues = []
        
        # Check for required consciousness metrics
        for metric in required_metrics:
            if metric not in results:
                issues.append(f"Missing consciousness metric: {metric}")
        
        # Validate Phi (integrated information) if present
        if 'phi' in results:
            phi = results['phi']
            try:
                phi_value = float(phi)
                if phi_value < 0:
                    issues.append(f"Negative Phi value: {phi_value}")
                elif phi_value < phi_threshold:
                    issues.append(f"Phi value below threshold: {phi_value} < {phi_threshold}")
            except (ValueError, TypeError):
                issues.append(f"Invalid Phi value: {phi}")
        
        # Check integration vs differentiation consistency
        if 'integration_score' in results and 'differentiation_score' in results:
            try:
                integration = float(results['integration_score'])
                differentiation = float(results['differentiation_score'])
                
                # These should be related but not identical
                if abs(integration - differentiation) < 0.01:
                    issues.append("Integration and differentiation scores are too similar")
            except (ValueError, TypeError):
                issues.append("Invalid integration or differentiation scores")
        
        passed = len(issues) == 0
        score = 1.0 if passed else max(0.0, 1.0 - (len(issues) * 0.25))
        message = f"Consciousness metrics validation {'passed' if passed else 'failed'}"
        
        return ValidationResult(
            rule_name=rule.name,
            passed=passed,
            score=score,
            message=message,
            details={'issues': issues},
            severity=rule.severity,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _extract_numerical_metrics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Extract numerical metrics from results."""
        metrics = {}
        
        def extract_recursive(data: Any, prefix: str = ""):
            if isinstance(data, dict):
                for key, value in data.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, (int, float)):
                        metrics[full_key] = float(value)
                    elif isinstance(value, dict):
                        extract_recursive(value, full_key)
            elif isinstance(data, (int, float)):
                if prefix:
                    metrics[prefix] = float(data)
        
        extract_recursive(results)
        return metrics
    
    def _extract_metric_value(self, results: Dict[str, Any], metric_name: str) -> Optional[float]:
        """Extract a specific metric value from results."""
        # Handle nested metric names with dots
        keys = metric_name.split('.')
        current = results
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        try:
            return float(current)
        except (ValueError, TypeError):
            return None
    
    async def _get_historical_metrics(self, experiment_id: str, metric_names: List[str],
                                    limit: int = 50) -> Dict[str, List[float]]:
        """Get historical metric values for an experiment."""
        # This would typically query a database or file system
        # For now, return empty dict - would be implemented with actual storage
        return {}
    
    def _calculate_overall_score(self, validation_results: List[ValidationResult]) -> float:
        """Calculate overall validation score."""
        if not validation_results:
            return 0.0
        
        # Weight by severity
        weights = {'error': 1.0, 'warning': 0.7, 'info': 0.3}
        
        total_weight = 0.0
        weighted_score = 0.0
        
        for result in validation_results:
            weight = weights.get(result.severity, 0.5)
            total_weight += weight
            weighted_score += result.score * weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _generate_validation_summary(self, validation_results: List[ValidationResult],
                                   overall_score: float) -> Dict[str, Any]:
        """Generate validation summary."""
        errors = [r for r in validation_results if r.severity == 'error' and not r.passed]
        warnings = [r for r in validation_results if r.severity == 'warning' and not r.passed]
        passed_checks = [r for r in validation_results if r.passed]
        
        return {
            'total_checks': len(validation_results),
            'passed_checks': len(passed_checks),
            'error_count': len(errors),
            'warning_count': len(warnings),
            'overall_score': overall_score,
            'grade': self._score_to_grade(overall_score),
            'error_messages': [e.message for e in errors],
            'warning_messages': [w.message for w in warnings]
        }
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numerical score to letter grade."""
        if score >= 0.9:
            return 'A'
        elif score >= 0.8:
            return 'B'
        elif score >= 0.7:
            return 'C'
        elif score >= 0.6:
            return 'D'
        else:
            return 'F'
    
    async def _store_validation_results(self, experiment_id: str, results: Dict[str, Any],
                                      validation_results: List[ValidationResult]) -> None:
        """Store validation results for future comparison."""
        # Extract metrics for historical tracking
        metrics = self._extract_numerical_metrics(results)
        
        # Store in memory (would typically use persistent storage)
        if experiment_id not in self.results_history:
            self.results_history[experiment_id] = []
        
        history_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics': metrics,
            'validation_score': self._calculate_overall_score(validation_results)
        }
        
        self.results_history[experiment_id].append(history_entry)
        
        # Keep only recent history
        if len(self.results_history[experiment_id]) > 100:
            self.results_history[experiment_id] = self.results_history[experiment_id][-100:]
    
    async def add_custom_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self.validation_rules.append(rule)
    
    async def remove_rule(self, rule_name: str) -> bool:
        """Remove a validation rule by name."""
        original_count = len(self.validation_rules)
        self.validation_rules = [r for r in self.validation_rules if r.name != rule_name]
        return len(self.validation_rules) < original_count
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on result validator."""
        try:
            return {
                'status': 'healthy',
                'rule_count': len(self.validation_rules),
                'experiments_tracked': len(self.results_history),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }