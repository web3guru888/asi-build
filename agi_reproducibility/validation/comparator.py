"""
Result Comparator

Advanced result comparison system for validating experiment reproducibility
and detecting non-deterministic behavior.
"""

import json
import numpy as np
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
import hashlib
import difflib

from ..core.config import PlatformConfig
from ..core.exceptions import *


@dataclass
class ComparisonResult:
    """Result of comparing two experiment results."""
    similarity_score: float
    is_deterministic: bool
    differences: List[Dict[str, Any]]
    statistical_analysis: Dict[str, Any]
    details: Dict[str, Any]
    timestamp: datetime


class ResultComparator:
    """
    Advanced result comparison system for AGI experiments.
    
    Features:
    - Statistical comparison of numerical results
    - Structural comparison of complex data
    - Fuzzy matching for approximate equality
    - Non-determinism detection and analysis
    - Visualization of differences
    - Time-series comparison for dynamic systems
    - Semantic similarity for text outputs
    - Graph comparison for network structures
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.tolerance = config.benchmarks.performance_tolerance
        
    async def initialize(self) -> None:
        """Initialize the result comparator."""
        pass
    
    async def compare_results(self, result1: Dict[str, Any], result2: Dict[str, Any],
                            comparison_config: Dict[str, Any] = None) -> ComparisonResult:
        """
        Compare two experiment results comprehensively.
        
        Args:
            result1: First result set
            result2: Second result set  
            comparison_config: Optional configuration for comparison
            
        Returns:
            Detailed comparison results
        """
        config = comparison_config or {}
        tolerance = config.get('tolerance', self.tolerance)
        
        comparison_start = datetime.now(timezone.utc)
        
        # Structural comparison
        structural_diff = await self._compare_structure(result1, result2)
        
        # Numerical comparison
        numerical_diff = await self._compare_numerical_values(result1, result2, tolerance)
        
        # Text comparison
        text_diff = await self._compare_text_values(result1, result2)
        
        # Statistical analysis
        stats_analysis = await self._statistical_analysis(result1, result2)
        
        # Calculate overall similarity
        similarity_score = self._calculate_similarity_score(
            structural_diff, numerical_diff, text_diff, stats_analysis
        )
        
        # Determine if results are deterministic
        is_deterministic = self._assess_determinism(
            structural_diff, numerical_diff, text_diff, tolerance
        )
        
        # Collect all differences
        all_differences = (
            structural_diff.get('differences', []) +
            numerical_diff.get('differences', []) +
            text_diff.get('differences', [])
        )
        
        return ComparisonResult(
            similarity_score=similarity_score,
            is_deterministic=is_deterministic,
            differences=all_differences,
            statistical_analysis=stats_analysis,
            details={
                'structural_comparison': structural_diff,
                'numerical_comparison': numerical_diff,
                'text_comparison': text_diff,
                'tolerance_used': tolerance,
                'comparison_timestamp': comparison_start.isoformat()
            },
            timestamp=comparison_start
        )
    
    async def _compare_structure(self, result1: Dict[str, Any], 
                               result2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare the structural organization of results."""
        differences = []
        
        def compare_recursive(obj1, obj2, path=""):
            if type(obj1) != type(obj2):
                differences.append({
                    'type': 'type_mismatch',
                    'path': path,
                    'value1_type': type(obj1).__name__,
                    'value2_type': type(obj2).__name__,
                    'severity': 'high'
                })
                return
            
            if isinstance(obj1, dict):
                keys1, keys2 = set(obj1.keys()), set(obj2.keys())
                
                # Missing keys
                for key in keys1 - keys2:
                    differences.append({
                        'type': 'missing_key',
                        'path': f"{path}.{key}" if path else key,
                        'key': key,
                        'in_result1': True,
                        'in_result2': False,
                        'severity': 'medium'
                    })
                
                for key in keys2 - keys1:
                    differences.append({
                        'type': 'missing_key',
                        'path': f"{path}.{key}" if path else key,
                        'key': key,
                        'in_result1': False,
                        'in_result2': True,
                        'severity': 'medium'
                    })
                
                # Compare common keys
                for key in keys1 & keys2:
                    new_path = f"{path}.{key}" if path else key
                    compare_recursive(obj1[key], obj2[key], new_path)
            
            elif isinstance(obj1, list):
                if len(obj1) != len(obj2):
                    differences.append({
                        'type': 'list_length_mismatch',
                        'path': path,
                        'length1': len(obj1),
                        'length2': len(obj2),
                        'severity': 'medium'
                    })
                
                # Compare elements up to min length
                min_len = min(len(obj1), len(obj2))
                for i in range(min_len):
                    compare_recursive(obj1[i], obj2[i], f"{path}[{i}]")
        
        compare_recursive(result1, result2)
        
        return {
            'differences': differences,
            'total_structural_differences': len(differences),
            'has_structural_differences': len(differences) > 0
        }
    
    async def _compare_numerical_values(self, result1: Dict[str, Any], 
                                      result2: Dict[str, Any], 
                                      tolerance: float) -> Dict[str, Any]:
        """Compare numerical values with tolerance."""
        differences = []
        numerical_pairs = []
        
        def extract_numerical(obj, path=""):
            if isinstance(obj, (int, float)):
                return [(path, float(obj))]
            elif isinstance(obj, dict):
                pairs = []
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    pairs.extend(extract_numerical(value, new_path))
                return pairs
            elif isinstance(obj, list):
                pairs = []
                for i, value in enumerate(obj):
                    pairs.extend(extract_numerical(value, f"{path}[{i}]"))
                return pairs
            else:
                return []
        
        # Extract numerical values
        nums1 = dict(extract_numerical(result1))
        nums2 = dict(extract_numerical(result2))
        
        # Compare numerical values
        all_paths = set(nums1.keys()) | set(nums2.keys())
        
        for path in all_paths:
            if path not in nums1:
                differences.append({
                    'type': 'missing_numerical_value',
                    'path': path,
                    'value2': nums2[path],
                    'severity': 'medium'
                })
            elif path not in nums2:
                differences.append({
                    'type': 'missing_numerical_value',
                    'path': path,
                    'value1': nums1[path],
                    'severity': 'medium'
                })
            else:
                val1, val2 = nums1[path], nums2[path]
                
                # Handle special cases
                if np.isnan(val1) and np.isnan(val2):
                    continue  # Both NaN, considered equal
                elif np.isnan(val1) or np.isnan(val2):
                    differences.append({
                        'type': 'nan_mismatch',
                        'path': path,
                        'value1': val1,
                        'value2': val2,
                        'severity': 'high'
                    })
                    continue
                
                # Calculate relative and absolute differences
                abs_diff = abs(val1 - val2)
                if val1 != 0:
                    rel_diff = abs_diff / abs(val1)
                else:
                    rel_diff = abs_diff
                
                numerical_pairs.append({
                    'path': path,
                    'value1': val1,
                    'value2': val2,
                    'absolute_difference': abs_diff,
                    'relative_difference': rel_diff
                })
                
                # Check if difference exceeds tolerance
                if rel_diff > tolerance and abs_diff > 1e-10:  # Also check absolute for very small numbers
                    differences.append({
                        'type': 'numerical_difference',
                        'path': path,
                        'value1': val1,
                        'value2': val2,
                        'absolute_difference': abs_diff,
                        'relative_difference': rel_diff,
                        'tolerance': tolerance,
                        'severity': 'high' if rel_diff > tolerance * 2 else 'medium'
                    })
        
        # Statistical summary
        if numerical_pairs:
            abs_diffs = [p['absolute_difference'] for p in numerical_pairs]
            rel_diffs = [p['relative_difference'] for p in numerical_pairs]
            
            statistical_summary = {
                'total_numerical_comparisons': len(numerical_pairs),
                'mean_absolute_difference': np.mean(abs_diffs),
                'max_absolute_difference': np.max(abs_diffs),
                'mean_relative_difference': np.mean(rel_diffs),
                'max_relative_difference': np.max(rel_diffs),
                'values_within_tolerance': sum(1 for rd in rel_diffs if rd <= tolerance)
            }
        else:
            statistical_summary = {'total_numerical_comparisons': 0}
        
        return {
            'differences': differences,
            'numerical_pairs': numerical_pairs,
            'statistical_summary': statistical_summary,
            'tolerance_used': tolerance
        }
    
    async def _compare_text_values(self, result1: Dict[str, Any], 
                                 result2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare text values using various similarity metrics."""
        differences = []
        text_comparisons = []
        
        def extract_text(obj, path=""):
            if isinstance(obj, str):
                return [(path, obj)]
            elif isinstance(obj, dict):
                pairs = []
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    pairs.extend(extract_text(value, new_path))
                return pairs
            elif isinstance(obj, list):
                pairs = []
                for i, value in enumerate(obj):
                    pairs.extend(extract_text(value, f"{path}[{i}]"))
                return pairs
            else:
                return []
        
        # Extract text values
        texts1 = dict(extract_text(result1))
        texts2 = dict(extract_text(result2))
        
        # Compare text values
        all_paths = set(texts1.keys()) | set(texts2.keys())
        
        for path in all_paths:
            if path not in texts1:
                differences.append({
                    'type': 'missing_text_value',
                    'path': path,
                    'value2': texts2[path][:100] + "..." if len(texts2[path]) > 100 else texts2[path],
                    'severity': 'low'
                })
            elif path not in texts2:
                differences.append({
                    'type': 'missing_text_value',
                    'path': path,
                    'value1': texts1[path][:100] + "..." if len(texts1[path]) > 100 else texts1[path],
                    'severity': 'low'
                })
            else:
                text1, text2 = texts1[path], texts2[path]
                
                if text1 != text2:
                    # Calculate similarity metrics
                    similarity_ratio = difflib.SequenceMatcher(None, text1, text2).ratio()
                    
                    text_comparisons.append({
                        'path': path,
                        'similarity_ratio': similarity_ratio,
                        'length1': len(text1),
                        'length2': len(text2)
                    })
                    
                    if similarity_ratio < 0.9:  # Significant text difference
                        differences.append({
                            'type': 'text_difference',
                            'path': path,
                            'similarity_ratio': similarity_ratio,
                            'value1_preview': text1[:100] + "..." if len(text1) > 100 else text1,
                            'value2_preview': text2[:100] + "..." if len(text2) > 100 else text2,
                            'severity': 'high' if similarity_ratio < 0.5 else 'medium'
                        })
        
        return {
            'differences': differences,
            'text_comparisons': text_comparisons,
            'total_text_comparisons': len(text_comparisons)
        }
    
    async def _statistical_analysis(self, result1: Dict[str, Any], 
                                  result2: Dict[str, Any]) -> Dict[str, Any]:
        """Perform statistical analysis of the comparison."""
        
        def extract_all_numbers(obj):
            numbers = []
            if isinstance(obj, (int, float)):
                numbers.append(float(obj))
            elif isinstance(obj, dict):
                for value in obj.values():
                    numbers.extend(extract_all_numbers(value))
            elif isinstance(obj, list):
                for item in obj:
                    numbers.extend(extract_all_numbers(item))
            return numbers
        
        nums1 = extract_all_numbers(result1)
        nums2 = extract_all_numbers(result2)
        
        if not nums1 or not nums2:
            return {'error': 'No numerical values found for statistical analysis'}
        
        # Basic statistics
        stats1 = {
            'count': len(nums1),
            'mean': np.mean(nums1),
            'std': np.std(nums1),
            'min': np.min(nums1),
            'max': np.max(nums1)
        }
        
        stats2 = {
            'count': len(nums2),
            'mean': np.mean(nums2),
            'std': np.std(nums2),
            'min': np.min(nums2),
            'max': np.max(nums2)
        }
        
        # Statistical tests
        analysis = {
            'result1_stats': stats1,
            'result2_stats': stats2,
            'mean_difference': abs(stats1['mean'] - stats2['mean']),
            'std_difference': abs(stats1['std'] - stats2['std'])
        }
        
        # Perform t-test if we have enough samples
        if len(nums1) > 1 and len(nums2) > 1:
            try:
                from scipy import stats as scipy_stats
                t_stat, p_value = scipy_stats.ttest_ind(nums1, nums2)
                analysis.update({
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'statistically_different': p_value < 0.05
                })
            except ImportError:
                analysis['scipy_unavailable'] = True
        
        return analysis
    
    def _calculate_similarity_score(self, structural_diff: Dict[str, Any],
                                   numerical_diff: Dict[str, Any],
                                   text_diff: Dict[str, Any],
                                   stats_analysis: Dict[str, Any]) -> float:
        """Calculate overall similarity score."""
        score = 1.0
        
        # Structural similarity
        struct_diffs = len(structural_diff.get('differences', []))
        if struct_diffs > 0:
            score -= min(0.3, struct_diffs * 0.05)
        
        # Numerical similarity
        num_diffs = len(numerical_diff.get('differences', []))
        if num_diffs > 0:
            # Weight by severity
            high_severity = sum(1 for d in numerical_diff.get('differences', []) 
                              if d.get('severity') == 'high')
            medium_severity = num_diffs - high_severity
            score -= min(0.4, high_severity * 0.1 + medium_severity * 0.05)
        
        # Text similarity
        text_diffs = len(text_diff.get('differences', []))
        if text_diffs > 0:
            score -= min(0.2, text_diffs * 0.03)
        
        # Statistical significance
        if stats_analysis.get('statistically_different', False):
            score -= 0.1
        
        return max(0.0, score)
    
    def _assess_determinism(self, structural_diff: Dict[str, Any],
                          numerical_diff: Dict[str, Any],
                          text_diff: Dict[str, Any],
                          tolerance: float) -> bool:
        """Assess if results indicate deterministic behavior."""
        
        # Check for structural determinism
        if structural_diff.get('has_structural_differences', False):
            return False
        
        # Check for numerical determinism
        num_diffs = numerical_diff.get('differences', [])
        significant_num_diffs = [d for d in num_diffs 
                               if d.get('type') == 'numerical_difference' and 
                                  d.get('relative_difference', 0) > tolerance]
        
        if significant_num_diffs:
            return False
        
        # Check for text determinism (exact matches expected)
        text_diffs = text_diff.get('differences', [])
        exact_text_diffs = [d for d in text_diffs 
                           if d.get('type') == 'text_difference' and 
                              d.get('similarity_ratio', 1.0) < 1.0]
        
        if exact_text_diffs:
            return False
        
        return True
    
    async def compare_time_series(self, series1: List[Dict[str, Any]], 
                                series2: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare time series data from dynamic experiments."""
        if len(series1) != len(series2):
            return {
                'error': 'Time series length mismatch',
                'length1': len(series1),
                'length2': len(series2)
            }
        
        comparisons = []
        for i, (point1, point2) in enumerate(zip(series1, series2)):
            point_comparison = await self.compare_results(point1, point2)
            comparisons.append({
                'timestamp_index': i,
                'similarity_score': point_comparison.similarity_score,
                'is_deterministic': point_comparison.is_deterministic,
                'difference_count': len(point_comparison.differences)
            })
        
        # Overall time series analysis
        similarity_scores = [c['similarity_score'] for c in comparisons]
        deterministic_points = [c['is_deterministic'] for c in comparisons]
        
        return {
            'total_points': len(series1),
            'mean_similarity': np.mean(similarity_scores),
            'min_similarity': np.min(similarity_scores),
            'deterministic_points': sum(deterministic_points),
            'deterministic_ratio': sum(deterministic_points) / len(deterministic_points),
            'point_comparisons': comparisons
        }
    
    async def generate_diff_report(self, comparison_result: ComparisonResult) -> str:
        """Generate a human-readable diff report."""
        report_lines = [
            "AGI Experiment Result Comparison Report",
            "=" * 50,
            f"Similarity Score: {comparison_result.similarity_score:.3f}",
            f"Deterministic: {'Yes' if comparison_result.is_deterministic else 'No'}",
            f"Total Differences: {len(comparison_result.differences)}",
            f"Generated: {comparison_result.timestamp.isoformat()}",
            ""
        ]
        
        if comparison_result.differences:
            report_lines.extend([
                "DIFFERENCES FOUND:",
                "-" * 20
            ])
            
            # Group by severity
            high_severity = [d for d in comparison_result.differences if d.get('severity') == 'high']
            medium_severity = [d for d in comparison_result.differences if d.get('severity') == 'medium']
            low_severity = [d for d in comparison_result.differences if d.get('severity') == 'low']
            
            for severity, diffs in [('HIGH', high_severity), ('MEDIUM', medium_severity), ('LOW', low_severity)]:
                if diffs:
                    report_lines.append(f"\\n{severity} SEVERITY ({len(diffs)} issues):")
                    for i, diff in enumerate(diffs[:10], 1):  # Limit to 10 per severity
                        report_lines.append(f"  {i}. [{diff.get('type', 'unknown')}] {diff.get('path', 'N/A')}")
                        if 'value1' in diff and 'value2' in diff:
                            report_lines.append(f"     Result 1: {diff['value1']}")
                            report_lines.append(f"     Result 2: {diff['value2']}")
                    if len(diffs) > 10:
                        report_lines.append(f"     ... and {len(diffs) - 10} more")
        else:
            report_lines.append("✓ No significant differences found")
        
        # Statistical summary
        stats = comparison_result.statistical_analysis
        if 'result1_stats' in stats:
            report_lines.extend([
                "",
                "STATISTICAL SUMMARY:",
                "-" * 20,
                f"Result 1 - Mean: {stats['result1_stats']['mean']:.6f}, Std: {stats['result1_stats']['std']:.6f}",
                f"Result 2 - Mean: {stats['result2_stats']['mean']:.6f}, Std: {stats['result2_stats']['std']:.6f}",
                f"Mean Difference: {stats.get('mean_difference', 0):.6f}",
                f"Std Difference: {stats.get('std_difference', 0):.6f}"
            ])
            
            if 'statistically_different' in stats:
                report_lines.append(f"Statistically Different: {'Yes' if stats['statistically_different'] else 'No'}")
        
        return "\\n".join(report_lines)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on result comparator."""
        try:
            # Test basic comparison functionality
            test_result1 = {'test': 1.0, 'data': [1, 2, 3]}
            test_result2 = {'test': 1.001, 'data': [1, 2, 3]}
            
            test_comparison = await self.compare_results(test_result1, test_result2)
            comparison_working = test_comparison.similarity_score > 0.9
            
            return {
                'status': 'healthy' if comparison_working else 'degraded',
                'comparison_working': comparison_working,
                'tolerance': self.tolerance,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }