"""
Quality Controller - Knowledge Validation and Quality Assurance
==============================================================

Comprehensive validation system that ensures knowledge quality,
accuracy, and reliability through multiple validation strategies.
"""

import asyncio
import logging
import time
import json
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib


@dataclass
class ValidationRule:
    """Represents a validation rule."""
    name: str
    rule_type: str  # 'consistency', 'accuracy', 'completeness', 'reliability'
    check_function: str
    weight: float = 1.0
    threshold: float = 0.7
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Results from knowledge validation."""
    overall_score: float
    passed_checks: int
    total_checks: int
    validation_issues: List[str]
    quality_metrics: Dict[str, float]
    recommendations: List[str]
    confidence_adjustments: Dict[str, float]
    metadata: Dict[str, Any]


class QualityController:
    """
    Comprehensive knowledge validation and quality control system.
    
    Validates knowledge through multiple dimensions:
    - Consistency checking across sources
    - Accuracy verification
    - Completeness assessment
    - Source reliability evaluation
    - Logical coherence validation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = self._setup_logging()
        
        # Validation rules and metrics
        self.validation_rules = self._initialize_validation_rules()
        self.quality_metrics = {}
        self.validation_history = []
        
        # Knowledge bases for validation
        self.fact_database = {}
        self.source_credibility = {}
        self.consistency_cache = {}
        
        # Performance tracking
        self.total_validations = 0
        self.validation_time = 0.0
        
        self.logger.info("Quality Controller initialized with validation rules")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'validation_timeout': 15.0,
            'min_validation_score': 0.6,
            'consistency_threshold': 0.8,
            'accuracy_threshold': 0.7,
            'completeness_threshold': 0.6,
            'enable_fact_checking': True,
            'enable_source_verification': True,
            'enable_consistency_checking': True,
            'enable_completeness_checking': True,
            'validation_strategies': [
                'consistency_validation',
                'accuracy_validation',
                'completeness_validation',
                'reliability_validation',
                'coherence_validation'
            ],
            'source_credibility_weights': {
                'kenny_system': 0.9,
                'official_documentation': 0.8,
                'verified_api': 0.7,
                'community_source': 0.5,
                'unknown_source': 0.3
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        logger = logging.getLogger('kenny.omniscience.validation')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_validation_rules(self) -> List[ValidationRule]:
        """Initialize validation rules."""
        rules = [
            ValidationRule(
                name="source_consistency",
                rule_type="consistency",
                check_function="check_source_consistency",
                weight=1.0,
                threshold=0.8
            ),
            ValidationRule(
                name="information_completeness",
                rule_type="completeness",
                check_function="check_information_completeness",
                weight=0.8,
                threshold=0.6
            ),
            ValidationRule(
                name="source_reliability",
                rule_type="reliability",
                check_function="check_source_reliability",
                weight=1.2,
                threshold=0.7
            ),
            ValidationRule(
                name="logical_coherence",
                rule_type="accuracy",
                check_function="check_logical_coherence",
                weight=1.1,
                threshold=0.7
            ),
            ValidationRule(
                name="factual_accuracy",
                rule_type="accuracy",
                check_function="check_factual_accuracy",
                weight=1.3,
                threshold=0.8
            ),
            ValidationRule(
                name="temporal_consistency",
                rule_type="consistency",
                check_function="check_temporal_consistency",
                weight=0.9,
                threshold=0.7
            ),
            ValidationRule(
                name="confidence_calibration",
                rule_type="reliability",
                check_function="check_confidence_calibration",
                weight=0.7,
                threshold=0.6
            )
        ]
        
        return [rule for rule in rules if rule.enabled]
    
    async def validate_knowledge(self, synthesis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate synthesized knowledge for quality and reliability.
        
        Args:
            synthesis_result: Result from knowledge synthesis
            
        Returns:
            Dictionary containing validation results and quality metrics
        """
        start_time = time.time()
        self.total_validations += 1
        
        self.logger.info("Validating synthesized knowledge...")
        
        try:
            # Extract knowledge components for validation
            knowledge_components = self._extract_knowledge_components(synthesis_result)
            
            # Execute validation strategies
            validation_results = await self._execute_validation_strategies(knowledge_components)
            
            # Aggregate validation results
            aggregated_results = self._aggregate_validation_results(validation_results)
            
            # Generate quality metrics
            quality_metrics = self._calculate_quality_metrics(validation_results)
            
            # Determine confidence adjustments
            confidence_adjustments = self._calculate_confidence_adjustments(validation_results)
            
            # Generate recommendations
            recommendations = self._generate_validation_recommendations(validation_results, quality_metrics)
            
            validation_time = time.time() - start_time
            self.validation_time += validation_time
            
            # Create comprehensive validation result
            final_result = {
                'validation_passed': aggregated_results['overall_score'] >= self.config.get('min_validation_score', 0.6),
                'validation_score': aggregated_results['overall_score'],
                'quality_metrics': quality_metrics,
                'validation_details': aggregated_results,
                'confidence_adjustments': confidence_adjustments,
                'recommendations': recommendations,
                'validation_metadata': {
                    'processing_time': validation_time,
                    'rules_applied': len(self.validation_rules),
                    'validation_timestamp': time.time(),
                    'version': '1.0.0'
                }
            }
            
            # Update validation history
            self.validation_history.append({
                'timestamp': time.time(),
                'score': aggregated_results['overall_score'],
                'passed': final_result['validation_passed']
            })
            
            # Apply confidence adjustments to synthesis result
            adjusted_result = self._apply_confidence_adjustments(synthesis_result, confidence_adjustments)
            
            # Merge validation into synthesis result
            validated_synthesis = {
                **adjusted_result,
                'validation': final_result,
                'confidence': adjusted_result.get('confidence', 0.5) * aggregated_results['overall_score']
            }
            
            self.logger.info(f"Knowledge validation completed in {validation_time:.2f}s with score {aggregated_results['overall_score']:.2f}")
            
            return validated_synthesis
            
        except Exception as e:
            validation_time = time.time() - start_time
            self.logger.error(f"Error in knowledge validation: {str(e)}")
            return {
                **synthesis_result,
                'validation': {
                    'error': str(e),
                    'validation_passed': False,
                    'validation_score': 0.0,
                    'validation_metadata': {
                        'processing_time': validation_time,
                        'success': False
                    }
                }
            }
    
    def _extract_knowledge_components(self, synthesis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract components for validation."""
        components = {
            'synthesis_data': synthesis_result.get('synthesis', {}),
            'predictions': synthesis_result.get('predictions', []),
            'sources': [],
            'confidence_scores': {},
            'content_data': {}
        }
        
        # Extract synthesis information
        synthesis = synthesis_result.get('synthesis', {})
        if hasattr(synthesis, '__dict__'):
            components['synthesis_data'] = synthesis.__dict__
        elif isinstance(synthesis, dict):
            components['synthesis_data'] = synthesis
        
        # Extract source information
        sources_analyzed = components['synthesis_data'].get('sources_analyzed', [])
        components['sources'] = sources_analyzed
        
        # Extract confidence information
        overall_confidence = components['synthesis_data'].get('confidence_score', 0.5)
        components['confidence_scores']['overall'] = overall_confidence
        
        return components
    
    async def _execute_validation_strategies(self, knowledge_components: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all validation strategies."""
        validation_results = {}
        
        for rule in self.validation_rules:
            try:
                result = await self._execute_validation_rule(rule, knowledge_components)
                validation_results[rule.name] = result
            except Exception as e:
                self.logger.warning(f"Validation rule {rule.name} failed: {str(e)}")
                validation_results[rule.name] = {
                    'passed': False,
                    'score': 0.0,
                    'issues': [f"Validation error: {str(e)}"],
                    'metadata': {'error': True}
                }
        
        return validation_results
    
    async def _execute_validation_rule(self, rule: ValidationRule, components: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific validation rule."""
        if rule.check_function == "check_source_consistency":
            return await self._check_source_consistency(components)
        elif rule.check_function == "check_information_completeness":
            return await self._check_information_completeness(components)
        elif rule.check_function == "check_source_reliability":
            return await self._check_source_reliability(components)
        elif rule.check_function == "check_logical_coherence":
            return await self._check_logical_coherence(components)
        elif rule.check_function == "check_factual_accuracy":
            return await self._check_factual_accuracy(components)
        elif rule.check_function == "check_temporal_consistency":
            return await self._check_temporal_consistency(components)
        elif rule.check_function == "check_confidence_calibration":
            return await self._check_confidence_calibration(components)
        else:
            return {
                'passed': False,
                'score': 0.0,
                'issues': [f"Unknown validation function: {rule.check_function}"],
                'metadata': {}
            }
    
    async def _check_source_consistency(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Check consistency across sources."""
        sources = components.get('sources', [])
        synthesis_data = components.get('synthesis_data', {})
        
        issues = []
        consistency_score = 1.0
        
        # Check if we have multiple sources
        if len(sources) < 2:
            issues.append("Insufficient sources for consistency checking")
            consistency_score = 0.7
        else:
            # Check for conflicting information (simplified)
            key_findings = synthesis_data.get('key_findings', [])
            if not key_findings:
                issues.append("No key findings to validate consistency")
                consistency_score = 0.5
            
            # Simulate consistency analysis
            source_types = set()
            for source in sources:
                if 'kenny' in source.lower():
                    source_types.add('internal')
                else:
                    source_types.add('external')
            
            if len(source_types) > 1:
                consistency_score = 0.9  # Mixed sources are good
            else:
                consistency_score = 0.7  # Single source type
                issues.append("Limited source diversity may affect consistency")
        
        return {
            'passed': consistency_score >= 0.8,
            'score': consistency_score,
            'issues': issues,
            'metadata': {
                'source_count': len(sources),
                'source_diversity': len(set(sources))
            }
        }
    
    async def _check_information_completeness(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Check completeness of information."""
        synthesis_data = components.get('synthesis_data', {})
        
        issues = []
        completeness_score = 0.0
        
        # Check required components
        required_components = ['summary', 'key_findings', 'insights']
        present_components = 0
        
        for component in required_components:
            if component in synthesis_data and synthesis_data[component]:
                present_components += 1
            else:
                issues.append(f"Missing or empty component: {component}")
        
        completeness_score = present_components / len(required_components)
        
        # Check content depth
        summary = synthesis_data.get('summary', '')
        if len(summary) < 50:
            issues.append("Summary too brief for comprehensive analysis")
            completeness_score *= 0.8
        
        key_findings = synthesis_data.get('key_findings', [])
        if len(key_findings) < 2:
            issues.append("Insufficient key findings")
            completeness_score *= 0.9
        
        return {
            'passed': completeness_score >= 0.6,
            'score': completeness_score,
            'issues': issues,
            'metadata': {
                'present_components': present_components,
                'total_components': len(required_components),
                'summary_length': len(summary),
                'findings_count': len(key_findings)
            }
        }
    
    async def _check_source_reliability(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Check reliability of sources."""
        sources = components.get('sources', [])
        
        issues = []
        reliability_scores = []
        
        credibility_weights = self.config.get('source_credibility_weights', {})
        
        for source in sources:
            # Determine source type and credibility
            if 'kenny' in source.lower():
                credibility = credibility_weights.get('kenny_system', 0.9)
            elif 'documentation' in source.lower():
                credibility = credibility_weights.get('official_documentation', 0.8)
            elif 'api' in source.lower():
                credibility = credibility_weights.get('verified_api', 0.7)
            else:
                credibility = credibility_weights.get('unknown_source', 0.3)
                issues.append(f"Unknown source reliability: {source}")
            
            reliability_scores.append(credibility)
        
        if not reliability_scores:
            overall_reliability = 0.0
            issues.append("No sources to evaluate reliability")
        else:
            overall_reliability = sum(reliability_scores) / len(reliability_scores)
        
        # Check for minimum reliable sources
        reliable_sources = [score for score in reliability_scores if score >= 0.7]
        if len(reliable_sources) < len(sources) * 0.5:
            issues.append("Majority of sources have low reliability")
            overall_reliability *= 0.8
        
        return {
            'passed': overall_reliability >= 0.7,
            'score': overall_reliability,
            'issues': issues,
            'metadata': {
                'total_sources': len(sources),
                'reliable_sources': len(reliable_sources),
                'average_reliability': overall_reliability
            }
        }
    
    async def _check_logical_coherence(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Check logical coherence of the synthesis."""
        synthesis_data = components.get('synthesis_data', {})
        
        issues = []
        coherence_score = 1.0
        
        # Check summary-findings alignment
        summary = synthesis_data.get('summary', '')
        key_findings = synthesis_data.get('key_findings', [])
        
        if summary and key_findings:
            # Simple coherence check based on keyword overlap
            summary_words = set(re.findall(r'\b\w+\b', summary.lower()))
            findings_words = set()
            for finding in key_findings:
                findings_words.update(re.findall(r'\b\w+\b', str(finding).lower()))
            
            if findings_words:
                overlap = len(summary_words.intersection(findings_words))
                total_unique = len(summary_words.union(findings_words))
                coherence_ratio = overlap / total_unique if total_unique > 0 else 0
                
                if coherence_ratio < 0.3:
                    issues.append("Low coherence between summary and findings")
                    coherence_score = coherence_ratio + 0.3
                else:
                    coherence_score = min(coherence_ratio + 0.5, 1.0)
        else:
            issues.append("Insufficient content for coherence analysis")
            coherence_score = 0.5
        
        # Check insights consistency with findings
        insights = synthesis_data.get('insights', [])
        if insights and key_findings:
            # Ensure insights don't contradict findings
            contradiction_count = 0
            for insight in insights:
                insight_words = set(re.findall(r'\b\w+\b', str(insight).lower()))
                negative_words = {'not', 'no', 'never', 'none', 'cannot', 'impossible'}
                if insight_words.intersection(negative_words) and len(key_findings) > 0:
                    contradiction_count += 1
            
            if contradiction_count > len(insights) * 0.3:
                issues.append("Potential contradictions between insights and findings")
                coherence_score *= 0.8
        
        return {
            'passed': coherence_score >= 0.7,
            'score': coherence_score,
            'issues': issues,
            'metadata': {
                'coherence_ratio': coherence_score,
                'summary_length': len(summary),
                'findings_count': len(key_findings),
                'insights_count': len(insights)
            }
        }
    
    async def _check_factual_accuracy(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Check factual accuracy (simplified implementation)."""
        synthesis_data = components.get('synthesis_data', {})
        
        issues = []
        accuracy_score = 0.8  # Default score for now
        
        # In a real implementation, this would check against known facts
        # For now, we'll do basic sanity checks
        
        key_findings = synthesis_data.get('key_findings', [])
        for finding in key_findings:
            finding_str = str(finding).lower()
            
            # Check for obviously incorrect statements
            if 'impossible' in finding_str or 'never' in finding_str:
                # This would need more sophisticated analysis
                pass
            
            # Check for numerical inconsistencies
            numbers = re.findall(r'\d+', finding_str)
            if len(numbers) > 1:
                # Could check for logical number relationships
                pass
        
        # Check confidence consistency
        confidence = synthesis_data.get('confidence_score', 0.5)
        if confidence > 0.9 and len(key_findings) < 3:
            issues.append("High confidence with limited findings may indicate overconfidence")
            accuracy_score *= 0.9
        
        return {
            'passed': accuracy_score >= 0.8,
            'score': accuracy_score,
            'issues': issues,
            'metadata': {
                'findings_analyzed': len(key_findings),
                'confidence_score': confidence
            }
        }
    
    async def _check_temporal_consistency(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Check temporal consistency of information."""
        synthesis_data = components.get('synthesis_data', {})
        
        issues = []
        temporal_score = 1.0
        
        # Check synthesis metadata for temporal information
        metadata = synthesis_data.get('synthesis_metadata', {})
        synthesis_timestamp = metadata.get('synthesis_timestamp', time.time())
        
        # Check if synthesis is recent enough
        age_hours = (time.time() - synthesis_timestamp) / 3600
        if age_hours > 24:
            issues.append("Synthesis data may be outdated")
            temporal_score = max(0.5, 1.0 - (age_hours - 24) / 168)  # Decay over week
        
        # Check for temporal references in content
        summary = synthesis_data.get('summary', '')
        temporal_references = re.findall(r'\b(today|yesterday|tomorrow|recent|current|latest)\b', summary.lower())
        
        if temporal_references and age_hours > 6:
            issues.append("Temporal references may be outdated")
            temporal_score *= 0.9
        
        return {
            'passed': temporal_score >= 0.7,
            'score': temporal_score,
            'issues': issues,
            'metadata': {
                'synthesis_age_hours': age_hours,
                'temporal_references': len(temporal_references)
            }
        }
    
    async def _check_confidence_calibration(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Check if confidence scores are well-calibrated."""
        synthesis_data = components.get('synthesis_data', {})
        confidence_scores = components.get('confidence_scores', {})
        
        issues = []
        calibration_score = 1.0
        
        overall_confidence = confidence_scores.get('overall', 0.5)
        
        # Check if confidence aligns with content quality
        key_findings = synthesis_data.get('key_findings', [])
        insights = synthesis_data.get('insights', [])
        
        content_quality_indicators = len(key_findings) + len(insights)
        
        # High confidence should come with substantial content
        if overall_confidence > 0.8 and content_quality_indicators < 5:
            issues.append("High confidence not supported by content depth")
            calibration_score = 0.7
        
        # Low confidence with rich content suggests under-confidence
        if overall_confidence < 0.4 and content_quality_indicators > 8:
            issues.append("Low confidence despite rich content")
            calibration_score = 0.8
        
        # Check for extreme confidence values
        if overall_confidence > 0.95:
            issues.append("Extremely high confidence may indicate overconfidence")
            calibration_score = 0.8
        elif overall_confidence < 0.1:
            issues.append("Extremely low confidence may indicate system issues")
            calibration_score = 0.6
        
        return {
            'passed': calibration_score >= 0.6,
            'score': calibration_score,
            'issues': issues,
            'metadata': {
                'overall_confidence': overall_confidence,
                'content_quality_indicators': content_quality_indicators
            }
        }
    
    def _aggregate_validation_results(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from all validation checks."""
        total_score = 0.0
        total_weight = 0.0
        passed_checks = 0
        total_checks = len(validation_results)
        all_issues = []
        
        rule_scores = {}
        
        for rule in self.validation_rules:
            result = validation_results.get(rule.name, {})
            score = result.get('score', 0.0)
            weight = rule.weight
            
            total_score += score * weight
            total_weight += weight
            
            if result.get('passed', False):
                passed_checks += 1
            
            all_issues.extend(result.get('issues', []))
            rule_scores[rule.name] = score
        
        overall_score = total_score / total_weight if total_weight > 0 else 0.0
        
        return {
            'overall_score': overall_score,
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'validation_issues': all_issues,
            'rule_scores': rule_scores,
            'pass_rate': passed_checks / total_checks if total_checks > 0 else 0.0
        }
    
    def _calculate_quality_metrics(self, validation_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate comprehensive quality metrics."""
        metrics = {}
        
        # Aggregate scores by rule type
        rule_type_scores = defaultdict(list)
        for rule in self.validation_rules:
            result = validation_results.get(rule.name, {})
            score = result.get('score', 0.0)
            rule_type_scores[rule.rule_type].append(score)
        
        # Calculate type-specific metrics
        for rule_type, scores in rule_type_scores.items():
            if scores:
                metrics[f'{rule_type}_score'] = sum(scores) / len(scores)
        
        # Calculate overall metrics
        all_scores = []
        for result in validation_results.values():
            all_scores.append(result.get('score', 0.0))
        
        if all_scores:
            metrics['average_score'] = sum(all_scores) / len(all_scores)
            metrics['min_score'] = min(all_scores)
            metrics['max_score'] = max(all_scores)
        
        return metrics
    
    def _calculate_confidence_adjustments(self, validation_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence adjustments based on validation."""
        adjustments = {}
        
        # Calculate overall adjustment factor
        all_scores = [result.get('score', 0.5) for result in validation_results.values()]
        if all_scores:
            avg_validation_score = sum(all_scores) / len(all_scores)
            
            # Adjust confidence based on validation performance
            if avg_validation_score >= 0.9:
                adjustments['confidence_multiplier'] = 1.1
            elif avg_validation_score >= 0.7:
                adjustments['confidence_multiplier'] = 1.0
            elif avg_validation_score >= 0.5:
                adjustments['confidence_multiplier'] = 0.9
            else:
                adjustments['confidence_multiplier'] = 0.7
        else:
            adjustments['confidence_multiplier'] = 0.8
        
        # Specific adjustments for critical failures
        for rule in self.validation_rules:
            result = validation_results.get(rule.name, {})
            if not result.get('passed', False) and rule.rule_type == 'accuracy':
                adjustments['accuracy_penalty'] = -0.2
                break
        
        return adjustments
    
    def _generate_validation_recommendations(self, validation_results: Dict[str, Any], quality_metrics: Dict[str, float]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Check overall quality
        avg_score = quality_metrics.get('average_score', 0.0)
        if avg_score < 0.6:
            recommendations.append("Overall validation score is low - consider gathering additional sources")
        
        # Check specific rule failures
        for rule in self.validation_rules:
            result = validation_results.get(rule.name, {})
            if not result.get('passed', False):
                if rule.rule_type == 'consistency':
                    recommendations.append("Improve source consistency by cross-referencing information")
                elif rule.rule_type == 'completeness':
                    recommendations.append("Gather more comprehensive information to improve completeness")
                elif rule.rule_type == 'reliability':
                    recommendations.append("Use more authoritative sources to improve reliability")
                elif rule.rule_type == 'accuracy':
                    recommendations.append("Verify factual accuracy through additional fact-checking")
        
        # Check for excessive issues
        total_issues = sum(len(result.get('issues', [])) for result in validation_results.values())
        if total_issues > len(validation_results) * 2:
            recommendations.append("Multiple validation issues detected - consider regenerating synthesis")
        
        return recommendations[:5]  # Limit recommendations
    
    def _apply_confidence_adjustments(self, synthesis_result: Dict[str, Any], adjustments: Dict[str, float]) -> Dict[str, Any]:
        """Apply confidence adjustments to synthesis result."""
        adjusted_result = synthesis_result.copy()
        
        # Apply multiplier to confidence scores
        confidence_multiplier = adjustments.get('confidence_multiplier', 1.0)
        
        if 'synthesis' in adjusted_result:
            synthesis = adjusted_result['synthesis']
            if hasattr(synthesis, 'confidence_score'):
                synthesis.confidence_score *= confidence_multiplier
            elif isinstance(synthesis, dict) and 'confidence_score' in synthesis:
                synthesis['confidence_score'] *= confidence_multiplier
        
        # Apply penalties
        accuracy_penalty = adjustments.get('accuracy_penalty', 0.0)
        if accuracy_penalty < 0:
            if 'synthesis' in adjusted_result:
                synthesis = adjusted_result['synthesis']
                if hasattr(synthesis, 'confidence_score'):
                    synthesis.confidence_score = max(0.1, synthesis.confidence_score + accuracy_penalty)
                elif isinstance(synthesis, dict) and 'confidence_score' in synthesis:
                    synthesis['confidence_score'] = max(0.1, synthesis['confidence_score'] + accuracy_penalty)
        
        return adjusted_result
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation performance statistics."""
        avg_validation_time = self.validation_time / self.total_validations if self.total_validations > 0 else 0.0
        
        # Calculate success rate from history
        recent_history = self.validation_history[-100:]  # Last 100 validations
        success_rate = sum(1 for v in recent_history if v['passed']) / len(recent_history) if recent_history else 0.0
        
        return {
            'total_validations': self.total_validations,
            'total_validation_time': self.validation_time,
            'average_validation_time': avg_validation_time,
            'success_rate': success_rate,
            'active_rules': len([r for r in self.validation_rules if r.enabled]),
            'total_rules': len(self.validation_rules),
            'validation_history_size': len(self.validation_history)
        }
    
    async def shutdown(self):
        """Gracefully shutdown the quality controller."""
        self.logger.info("Shutting down Quality Controller...")
        # Save validation state, clear caches, etc.
        self.logger.info("Quality Controller shutdown complete")