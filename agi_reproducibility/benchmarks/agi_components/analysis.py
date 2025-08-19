"""
Analysis Tools for AGI Component Benchmark Suite

Implements comprehensive analysis capabilities including:
- Statistical analysis of benchmark results
- Performance comparison between systems
- Trend analysis over time
- Capability profiling and visualization
- Gap analysis and recommendations
- Report generation
"""

import json
import statistics
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from .core import BenchmarkSuiteResult, BenchmarkResult
from .tracking import ProgressTracker, ProgressMetrics, CapabilityGap


@dataclass
class ComparisonResult:
    """Result of comparing two systems"""
    system_a: str
    system_b: str
    overall_difference: float
    category_differences: Dict[str, float]
    significant_improvements: List[str]
    significant_regressions: List[str]
    statistical_significance: Dict[str, float]


@dataclass
class TrendAnalysis:
    """Trend analysis result"""
    system_id: str
    metric: str
    trend_direction: str  # improving, declining, stable
    trend_strength: float  # 0-1
    slope: float
    r_squared: float
    prediction_next_month: float


@dataclass
class CapabilityProfile:
    """Capability profile of a system"""
    system_id: str
    capabilities: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    overall_maturity: float
    coverage_completeness: float


class BenchmarkAnalyzer:
    """Comprehensive analysis tool for benchmark results"""
    
    def __init__(self, tracker: ProgressTracker = None):
        self.tracker = tracker
        self.visualization_enabled = True
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError:
            self.visualization_enabled = False
            print("Visualization libraries not available. Install matplotlib and seaborn for full functionality.")
    
    def compare_systems(self, system_a_results: Dict[str, Any], 
                       system_b_results: Dict[str, Any],
                       statistical_test: bool = True) -> ComparisonResult:
        """Compare performance between two systems"""
        
        # Extract system names
        system_a = system_a_results.get("system_name", "System A")
        system_b = system_b_results.get("system_name", "System B")
        
        # Calculate overall scores
        score_a = system_a_results.get("summary", {}).get("average_score", 0)
        score_b = system_b_results.get("summary", {}).get("average_score", 0)
        overall_difference = score_b - score_a
        
        # Calculate category differences
        category_differences = {}
        results_a = system_a_results.get("results", [])
        results_b = system_b_results.get("results", [])
        
        # Group results by category
        categories_a = self._group_by_category(results_a)
        categories_b = self._group_by_category(results_b)
        
        all_categories = set(categories_a.keys()).union(set(categories_b.keys()))
        
        for category in all_categories:
            scores_a = [r["normalized_score"] for r in categories_a.get(category, [])]
            scores_b = [r["normalized_score"] for r in categories_b.get(category, [])]
            
            avg_a = statistics.mean(scores_a) if scores_a else 0
            avg_b = statistics.mean(scores_b) if scores_b else 0
            category_differences[category] = avg_b - avg_a
        
        # Identify significant changes
        significant_improvements = []
        significant_regressions = []
        
        for category, diff in category_differences.items():
            if abs(diff) > 5:  # 5% threshold for significance
                if diff > 0:
                    significant_improvements.append(category)
                else:
                    significant_regressions.append(category)
        
        # Statistical significance testing
        statistical_significance = {}
        if statistical_test:
            statistical_significance = self._calculate_statistical_significance(
                categories_a, categories_b
            )
        
        return ComparisonResult(
            system_a=system_a,
            system_b=system_b,
            overall_difference=overall_difference,
            category_differences=category_differences,
            significant_improvements=significant_improvements,
            significant_regressions=significant_regressions,
            statistical_significance=statistical_significance
        )
    
    def analyze_trends(self, system_id: str, metric: str = "overall_score", 
                      days: int = 90) -> TrendAnalysis:
        """Analyze performance trends over time"""
        if not self.tracker:
            raise ValueError("ProgressTracker required for trend analysis")
        
        progress_data = self.tracker.get_system_progress(system_id, days)
        
        if len(progress_data) < 3:
            return TrendAnalysis(
                system_id=system_id,
                metric=metric,
                trend_direction="insufficient_data",
                trend_strength=0.0,
                slope=0.0,
                r_squared=0.0,
                prediction_next_month=0.0
            )
        
        # Extract time series data
        timestamps = [p.timestamp for p in progress_data]
        if metric == "overall_score":
            values = [p.overall_score for p in progress_data]
        elif metric == "capability_coverage":
            values = [p.capability_coverage for p in progress_data]
        elif metric == "consistency_score":
            values = [p.consistency_score for p in progress_data]
        else:
            # Category-specific metric
            values = [p.category_scores.get(metric, 0) for p in progress_data]
        
        # Convert timestamps to numeric values (days since first measurement)
        start_time = timestamps[0]
        x_values = [(t - start_time).days for t in timestamps]
        
        # Perform linear regression
        slope, r_squared = self._linear_regression(x_values, values)
        
        # Determine trend direction and strength
        if abs(slope) < 0.1:
            trend_direction = "stable"
        elif slope > 0:
            trend_direction = "improving"
        else:
            trend_direction = "declining"
        
        trend_strength = min(1.0, abs(slope) / 2.0)  # Normalize to 0-1
        
        # Predict next month (30 days)
        next_month_x = x_values[-1] + 30
        prediction_next_month = values[-1] + (slope * 30)
        
        return TrendAnalysis(
            system_id=system_id,
            metric=metric,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            slope=slope,
            r_squared=r_squared,
            prediction_next_month=prediction_next_month
        )
    
    def create_capability_profile(self, system_results: Dict[str, Any]) -> CapabilityProfile:
        """Create a comprehensive capability profile"""
        system_id = system_results.get("system_name", "Unknown")
        results = system_results.get("results", [])
        
        # Group by categories and calculate scores
        categories = self._group_by_category(results)
        capabilities = {}
        
        for category, category_results in categories.items():
            scores = [r["normalized_score"] for r in category_results if r["success"]]
            capabilities[category] = statistics.mean(scores) if scores else 0.0
        
        # Identify strengths and weaknesses
        sorted_caps = sorted(capabilities.items(), key=lambda x: x[1], reverse=True)
        
        # Top 3 capabilities are strengths, bottom 3 are weaknesses
        strengths = [cap[0] for cap in sorted_caps[:3] if cap[1] > 60]
        weaknesses = [cap[0] for cap in sorted_caps[-3:] if cap[1] < 50]
        
        # Calculate overall maturity (weighted average)
        weights = {
            "reasoning": 0.15,
            "learning": 0.15,
            "memory": 0.12,
            "creativity": 0.10,
            "consciousness": 0.08,
            "symbolic": 0.15,
            "neural_symbolic": 0.12,
            "real_world": 0.13
        }
        
        overall_maturity = 0
        total_weight = 0
        for capability, score in capabilities.items():
            weight = weights.get(capability, 0.1)
            overall_maturity += score * weight
            total_weight += weight
        
        if total_weight > 0:
            overall_maturity /= total_weight
        
        # Calculate coverage completeness
        expected_capabilities = set(weights.keys())
        covered_capabilities = set(capabilities.keys())
        coverage_completeness = len(covered_capabilities.intersection(expected_capabilities)) / len(expected_capabilities) * 100
        
        return CapabilityProfile(
            system_id=system_id,
            capabilities=capabilities,
            strengths=strengths,
            weaknesses=weaknesses,
            overall_maturity=overall_maturity,
            coverage_completeness=coverage_completeness
        )
    
    def generate_performance_report(self, system_results: List[Dict[str, Any]], 
                                   output_path: str = None) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "generation_date": datetime.now().isoformat(),
            "systems_analyzed": len(system_results),
            "executive_summary": {},
            "detailed_analysis": {},
            "recommendations": [],
            "visualizations": []
        }
        
        if not system_results:
            report["executive_summary"]["message"] = "No systems to analyze"
            return report
        
        # Executive Summary
        all_scores = []
        system_summaries = []
        
        for result in system_results:
            system_name = result.get("system_name", "Unknown")
            avg_score = result.get("summary", {}).get("average_score", 0)
            success_rate = result.get("summary", {}).get("success_rate", 0)
            
            all_scores.append(avg_score)
            system_summaries.append({
                "name": system_name,
                "score": avg_score,
                "success_rate": success_rate
            })
        
        # Sort systems by performance
        system_summaries.sort(key=lambda x: x["score"], reverse=True)
        
        report["executive_summary"] = {
            "best_performing_system": system_summaries[0]["name"] if system_summaries else "None",
            "highest_score": max(all_scores) if all_scores else 0,
            "average_score_across_systems": statistics.mean(all_scores) if all_scores else 0,
            "score_variance": statistics.variance(all_scores) if len(all_scores) > 1 else 0,
            "system_rankings": system_summaries
        }
        
        # Detailed Analysis
        detailed_analysis = {}
        
        for result in system_results:
            system_name = result.get("system_name", "Unknown")
            
            # Create capability profile
            profile = self.create_capability_profile(result)
            
            # Analyze category performance
            category_analysis = self._analyze_category_performance(result.get("results", []))
            
            detailed_analysis[system_name] = {
                "capability_profile": {
                    "capabilities": profile.capabilities,
                    "strengths": profile.strengths,
                    "weaknesses": profile.weaknesses,
                    "overall_maturity": profile.overall_maturity,
                    "coverage_completeness": profile.coverage_completeness
                },
                "category_analysis": category_analysis,
                "performance_consistency": self._calculate_performance_consistency(result.get("results", []))
            }
        
        report["detailed_analysis"] = detailed_analysis
        
        # Generate recommendations
        report["recommendations"] = self._generate_improvement_recommendations(system_results)
        
        # Create visualizations if enabled
        if self.visualization_enabled and output_path:
            viz_paths = self._create_visualizations(system_results, output_path)
            report["visualizations"] = viz_paths
        
        # Save report if output path provided
        if output_path:
            report_path = Path(output_path) / "performance_report.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            report["report_path"] = str(report_path)
        
        return report
    
    def analyze_benchmark_coverage(self, system_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze coverage of benchmark tests across systems"""
        all_tests = set()
        all_categories = set()
        system_coverage = {}
        
        for result in system_results:
            system_name = result.get("system_name", "Unknown")
            results = result.get("results", [])
            
            system_tests = set()
            system_categories = set()
            
            for test_result in results:
                test_name = test_result.get("test_name", "")
                benchmark_name = test_result.get("benchmark_name", "")
                category = benchmark_name.split('_')[0] if benchmark_name else ""
                
                all_tests.add(test_name)
                all_categories.add(category)
                system_tests.add(test_name)
                system_categories.add(category)
            
            system_coverage[system_name] = {
                "tests_covered": len(system_tests),
                "categories_covered": len(system_categories),
                "test_coverage_percentage": len(system_tests) / len(all_tests) * 100 if all_tests else 0,
                "category_coverage_percentage": len(system_categories) / len(all_categories) * 100 if all_categories else 0
            }
        
        return {
            "total_unique_tests": len(all_tests),
            "total_categories": len(all_categories),
            "system_coverage": system_coverage,
            "average_test_coverage": statistics.mean([c["test_coverage_percentage"] for c in system_coverage.values()]) if system_coverage else 0,
            "average_category_coverage": statistics.mean([c["category_coverage_percentage"] for c in system_coverage.values()]) if system_coverage else 0
        }
    
    def identify_performance_patterns(self, system_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify patterns in performance across systems"""
        patterns = {
            "architectural_patterns": {},
            "capability_correlations": {},
            "common_failure_modes": {},
            "performance_clusters": {}
        }
        
        # Architectural patterns (if architecture info available)
        arch_performance = {}
        for result in system_results:
            arch_type = result.get("system_info", {}).get("architecture_type", "unknown")
            avg_score = result.get("summary", {}).get("average_score", 0)
            
            if arch_type not in arch_performance:
                arch_performance[arch_type] = []
            arch_performance[arch_type].append(avg_score)
        
        for arch, scores in arch_performance.items():
            patterns["architectural_patterns"][arch] = {
                "average_score": statistics.mean(scores),
                "score_variance": statistics.variance(scores) if len(scores) > 1 else 0,
                "system_count": len(scores)
            }
        
        # Capability correlations
        all_capabilities = {}
        for result in system_results:
            profile = self.create_capability_profile(result)
            for cap, score in profile.capabilities.items():
                if cap not in all_capabilities:
                    all_capabilities[cap] = []
                all_capabilities[cap].append(score)
        
        # Calculate correlation matrix
        cap_names = list(all_capabilities.keys())
        if len(cap_names) > 1:
            correlations = {}
            for i, cap1 in enumerate(cap_names):
                for j, cap2 in enumerate(cap_names[i+1:], i+1):
                    if len(all_capabilities[cap1]) == len(all_capabilities[cap2]):
                        corr = self._calculate_correlation(all_capabilities[cap1], all_capabilities[cap2])
                        correlations[f"{cap1}_{cap2}"] = corr
            
            patterns["capability_correlations"] = correlations
        
        # Common failure modes
        failure_modes = {}
        for result in system_results:
            for test_result in result.get("results", []):
                if not test_result.get("success", True):
                    error = test_result.get("error_message", "unknown_error")
                    test_name = test_result.get("test_name", "unknown_test")
                    
                    if error not in failure_modes:
                        failure_modes[error] = []
                    failure_modes[error].append(test_name)
        
        # Sort by frequency
        sorted_failures = sorted(failure_modes.items(), key=lambda x: len(x[1]), reverse=True)
        patterns["common_failure_modes"] = dict(sorted_failures[:10])  # Top 10
        
        return patterns
    
    def _group_by_category(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group benchmark results by category"""
        categories = {}
        
        for result in results:
            benchmark_name = result.get("benchmark_name", "")
            category = benchmark_name.split('_')[0] if benchmark_name else "unknown"
            
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        return categories
    
    def _calculate_statistical_significance(self, categories_a: Dict[str, List], 
                                          categories_b: Dict[str, List]) -> Dict[str, float]:
        """Calculate statistical significance of differences between systems"""
        significance = {}
        
        try:
            from scipy import stats
            
            for category in set(categories_a.keys()).intersection(set(categories_b.keys())):
                scores_a = [r["normalized_score"] for r in categories_a[category]]
                scores_b = [r["normalized_score"] for r in categories_b[category]]
                
                if len(scores_a) > 1 and len(scores_b) > 1:
                    # Perform t-test
                    t_stat, p_value = stats.ttest_ind(scores_a, scores_b)
                    significance[category] = p_value
        except ImportError:
            # scipy not available, skip statistical testing
            pass
        
        return significance
    
    def _linear_regression(self, x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
        """Perform simple linear regression"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0, 0.0
        
        n = len(x_values)
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        # Calculate slope
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0, 0.0
        
        slope = numerator / denominator
        
        # Calculate R-squared
        y_pred = [slope * (x - x_mean) + y_mean for x in x_values]
        ss_res = sum((y_values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y_values[i] - y_mean) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        
        return slope, r_squared
    
    def _calculate_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0
        
        try:
            n = len(x_values)
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(y_values)
            
            numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
            x_var = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            y_var = sum((y_values[i] - y_mean) ** 2 for i in range(n))
            
            denominator = (x_var * y_var) ** 0.5
            
            return numerator / denominator if denominator != 0 else 0.0
        except:
            return 0.0
    
    def _analyze_category_performance(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance within each category"""
        categories = self._group_by_category(results)
        analysis = {}
        
        for category, category_results in categories.items():
            scores = [r["normalized_score"] for r in category_results if r["success"]]
            execution_times = [r["execution_time"] for r in category_results]
            
            if scores:
                analysis[category] = {
                    "average_score": statistics.mean(scores),
                    "median_score": statistics.median(scores),
                    "score_std": statistics.stdev(scores) if len(scores) > 1 else 0,
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "average_execution_time": statistics.mean(execution_times),
                    "success_rate": len(scores) / len(category_results) * 100,
                    "test_count": len(category_results)
                }
            else:
                analysis[category] = {
                    "average_score": 0,
                    "success_rate": 0,
                    "test_count": len(category_results),
                    "note": "No successful tests"
                }
        
        return analysis
    
    def _calculate_performance_consistency(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate consistency metrics for performance"""
        if not results:
            return {"coefficient_of_variation": 0, "score_range": 0}
        
        scores = [r["normalized_score"] for r in results if r["success"]]
        
        if not scores:
            return {"coefficient_of_variation": 0, "score_range": 0}
        
        mean_score = statistics.mean(scores)
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0
        
        cv = std_score / mean_score if mean_score > 0 else 0
        score_range = max(scores) - min(scores)
        
        return {
            "coefficient_of_variation": cv,
            "score_range": score_range,
            "consistency_rating": "high" if cv < 0.2 else "medium" if cv < 0.5 else "low"
        }
    
    def _generate_improvement_recommendations(self, system_results: List[Dict[str, Any]]) -> List[str]:
        """Generate improvement recommendations based on analysis"""
        recommendations = []
        
        # Analyze common weaknesses
        all_weaknesses = []
        for result in system_results:
            profile = self.create_capability_profile(result)
            all_weaknesses.extend(profile.weaknesses)
        
        # Count frequency of weaknesses
        weakness_counts = {}
        for weakness in all_weaknesses:
            weakness_counts[weakness] = weakness_counts.get(weakness, 0) + 1
        
        # Generate recommendations for most common weaknesses
        common_weaknesses = sorted(weakness_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        weakness_recommendations = {
            "reasoning": "Focus on logical inference training and formal reasoning modules",
            "learning": "Implement meta-learning algorithms and continual learning mechanisms",
            "memory": "Enhance episodic memory systems and working memory capacity",
            "creativity": "Add divergent thinking modules and novelty detection capabilities",
            "consciousness": "Implement self-monitoring systems and metacognitive components",
            "symbolic": "Strengthen logical reasoning and probabilistic logic capabilities",
            "neural_symbolic": "Improve symbol grounding and neural-symbolic integration",
            "real_world": "Add robotic control modules and enhance natural language understanding"
        }
        
        for weakness, count in common_weaknesses:
            if weakness in weakness_recommendations:
                recommendations.append(f"Common weakness ({count} systems): {weakness_recommendations[weakness]}")
        
        # Performance consistency recommendations
        low_consistency_systems = []
        for result in system_results:
            consistency = self._calculate_performance_consistency(result.get("results", []))
            if consistency["consistency_rating"] == "low":
                low_consistency_systems.append(result.get("system_name", "Unknown"))
        
        if low_consistency_systems:
            recommendations.append(f"Improve performance consistency for: {', '.join(low_consistency_systems)}")
        
        # Coverage recommendations
        coverage_analysis = self.analyze_benchmark_coverage(system_results)
        avg_coverage = coverage_analysis["average_category_coverage"]
        
        if avg_coverage < 80:
            recommendations.append(f"Increase benchmark coverage (current average: {avg_coverage:.1f}%)")
        
        return recommendations
    
    def _create_visualizations(self, system_results: List[Dict[str, Any]], output_path: str) -> List[str]:
        """Create visualization plots for the analysis"""
        if not self.visualization_enabled:
            return []
        
        viz_paths = []
        output_dir = Path(output_path)
        output_dir.mkdir(exist_ok=True)
        
        try:
            # 1. Overall performance comparison
            system_names = []
            overall_scores = []
            
            for result in system_results:
                system_names.append(result.get("system_name", "Unknown"))
                overall_scores.append(result.get("summary", {}).get("average_score", 0))
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(system_names, overall_scores, color='skyblue', edgecolor='navy', alpha=0.7)
            plt.title('Overall Performance Comparison', fontsize=16, fontweight='bold')
            plt.xlabel('AGI Systems', fontsize=12)
            plt.ylabel('Average Score', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            plt.ylim(0, 100)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{height:.1f}', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            overall_path = output_dir / "overall_performance.png"
            plt.savefig(overall_path, dpi=300, bbox_inches='tight')
            plt.close()
            viz_paths.append(str(overall_path))
            
            # 2. Capability radar chart
            if len(system_results) <= 5:  # Only create radar chart for reasonable number of systems
                fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
                
                capabilities = ["reasoning", "learning", "memory", "creativity", 
                              "consciousness", "symbolic", "neural_symbolic", "real_world"]
                
                for result in system_results:
                    profile = self.create_capability_profile(result)
                    values = [profile.capabilities.get(cap, 0) for cap in capabilities]
                    values += values[:1]  # Complete the circle
                    
                    angles = np.linspace(0, 2 * np.pi, len(capabilities), endpoint=False).tolist()
                    angles += angles[:1]
                    
                    ax.plot(angles, values, 'o-', linewidth=2, label=result.get("system_name", "Unknown"))
                    ax.fill(angles, values, alpha=0.25)
                
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(capabilities)
                ax.set_ylim(0, 100)
                ax.set_title('Capability Profiles', fontsize=16, fontweight='bold', pad=20)
                ax.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
                
                radar_path = output_dir / "capability_radar.png"
                plt.savefig(radar_path, dpi=300, bbox_inches='tight')
                plt.close()
                viz_paths.append(str(radar_path))
            
            # 3. Category performance heatmap
            category_data = []
            system_labels = []
            
            for result in system_results:
                system_labels.append(result.get("system_name", "Unknown"))
                categories = self._group_by_category(result.get("results", []))
                row = []
                
                for cap in ["reasoning", "learning", "memory", "creativity", 
                           "consciousness", "symbolic", "neural_symbolic", "real_world"]:
                    if cap in categories:
                        scores = [r["normalized_score"] for r in categories[cap] if r["success"]]
                        avg_score = statistics.mean(scores) if scores else 0
                    else:
                        avg_score = 0
                    row.append(avg_score)
                
                category_data.append(row)
            
            if category_data:
                plt.figure(figsize=(12, 8))
                sns.heatmap(category_data, 
                           xticklabels=["Reasoning", "Learning", "Memory", "Creativity", 
                                       "Consciousness", "Symbolic", "Neural-Symbolic", "Real-World"],
                           yticklabels=system_labels,
                           annot=True, 
                           fmt='.1f',
                           cmap='RdYlBu_r',
                           vmin=0, 
                           vmax=100,
                           cbar_kws={'label': 'Score'})
                
                plt.title('Category Performance Heatmap', fontsize=16, fontweight='bold')
                plt.xlabel('AGI Capabilities', fontsize=12)
                plt.ylabel('Systems', fontsize=12)
                plt.tight_layout()
                
                heatmap_path = output_dir / "category_heatmap.png"
                plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
                plt.close()
                viz_paths.append(str(heatmap_path))
            
        except Exception as e:
            print(f"Error creating visualizations: {e}")
        
        return viz_paths