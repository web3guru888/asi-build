"""
Contextual Learner - Adaptive Knowledge Learning System
======================================================

Advanced learning system that adapts and improves knowledge processing
based on interactions, feedback, and performance patterns.
"""

import asyncio
import logging
import time
import json
import pickle
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import os


@dataclass
class LearningPattern:
    """Represents a learned pattern."""
    pattern_id: str
    pattern_type: str  # 'query', 'result', 'performance', 'error'
    pattern_data: Dict[str, Any]
    frequency: int = 1
    confidence: float = 0.5
    last_seen: float = None
    created_at: float = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = time.time()
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class LearningEvent:
    """Represents a learning event."""
    event_id: str
    event_type: str
    query: str
    result_quality: float
    processing_time: float
    user_feedback: Optional[Dict[str, Any]] = None
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class AdaptationRule:
    """Represents an adaptation rule."""
    rule_id: str
    rule_type: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    effectiveness: float = 0.5
    usage_count: int = 0
    enabled: bool = True


class ContextualLearner:
    """
    Contextual learning system for the omniscience network.
    
    Learns from:
    - Query patterns and user preferences
    - Result quality and accuracy
    - System performance metrics
    - User feedback and interactions
    - Error patterns and recovery strategies
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = self._setup_logging()
        
        # Learning components
        self.learning_patterns = {}
        self.adaptation_rules = []
        self.learning_events = deque(maxlen=10000)
        self.performance_history = deque(maxlen=1000)
        
        # Learning models
        self.query_patterns = defaultdict(int)
        self.result_quality_patterns = {}
        self.performance_patterns = {}
        self.error_patterns = defaultdict(list)
        
        # Adaptation state
        self.adaptation_state = {}
        self.learning_metrics = {}
        
        # Initialize learning data
        self._initialize_learning_system()
        
        self.logger.info("Contextual Learner initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'learning_enabled': True,
            'adaptation_enabled': True,
            'pattern_recognition_threshold': 3,
            'pattern_confidence_threshold': 0.6,
            'learning_rate': 0.1,
            'adaptation_frequency': '1h',
            'max_patterns': 10000,
            'pattern_decay_rate': 0.95,
            'persistence_enabled': True,
            'persistence_file': '/tmp/kenny_omniscience_learning.pkl',
            'learning_strategies': [
                'query_pattern_learning',
                'performance_optimization',
                'error_pattern_detection',
                'user_preference_learning',
                'quality_improvement'
            ],
            'adaptation_strategies': [
                'query_preprocessing',
                'source_selection',
                'confidence_calibration',
                'timeout_adjustment',
                'caching_optimization'
            ]
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        logger = logging.getLogger('kenny.omniscience.learner')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_learning_system(self):
        """Initialize the learning system."""
        # Load existing learning data if available
        if self.config.get('persistence_enabled', True):
            self._load_learning_data()
        
        # Initialize default adaptation rules
        self._initialize_adaptation_rules()
        
        # Initialize learning metrics
        self.learning_metrics = {
            'total_learning_events': 0,
            'patterns_learned': 0,
            'adaptations_applied': 0,
            'learning_accuracy': 0.0,
            'adaptation_effectiveness': 0.0
        }
    
    def _initialize_adaptation_rules(self):
        """Initialize default adaptation rules."""
        default_rules = [
            AdaptationRule(
                rule_id="slow_query_timeout",
                rule_type="performance",
                condition={'avg_processing_time': {'gt': 20.0}},
                action={'increase_timeout': 1.5, 'reduce_sources': 0.8},
                effectiveness=0.7
            ),
            AdaptationRule(
                rule_id="low_quality_boost",
                rule_type="quality",
                condition={'avg_result_quality': {'lt': 0.6}},
                action={'increase_validation_threshold': 0.1, 'add_sources': 2},
                effectiveness=0.6
            ),
            AdaptationRule(
                rule_id="frequent_query_cache",
                rule_type="caching",
                condition={'query_frequency': {'gt': 5}},
                action={'extend_cache_ttl': 2.0, 'prioritize_caching': True},
                effectiveness=0.8
            ),
            AdaptationRule(
                rule_id="high_confidence_fast_track",
                rule_type="optimization",
                condition={'result_confidence': {'gt': 0.9}},
                action={'reduce_validation_steps': 0.5, 'fast_track': True},
                effectiveness=0.7
            )
        ]
        
        self.adaptation_rules.extend(default_rules)
    
    async def learn_from_interaction(self, query, result) -> Dict[str, Any]:
        """
        Learn from a knowledge query interaction.
        
        Args:
            query: KnowledgeQuery object
            result: KnowledgeResult object
            
        Returns:
            Dictionary containing learning insights
        """
        if not self.config.get('learning_enabled', True):
            return {'learning_enabled': False}
        
        start_time = time.time()
        
        try:
            # Create learning event
            learning_event = self._create_learning_event(query, result)
            self.learning_events.append(learning_event)
            
            # Extract patterns
            patterns_learned = await self._extract_patterns(learning_event)
            
            # Update learning models
            await self._update_learning_models(learning_event, patterns_learned)
            
            # Check for adaptations
            adaptations = await self._check_for_adaptations(learning_event)
            
            # Update metrics
            self._update_learning_metrics(learning_event, patterns_learned, adaptations)
            
            # Persist learning data
            if self.config.get('persistence_enabled', True):
                await self._persist_learning_data()
            
            learning_time = time.time() - start_time
            
            learning_insights = {
                'patterns_identified': len(patterns_learned),
                'adaptations_triggered': len(adaptations),
                'learning_event_id': learning_event.event_id,
                'learning_time': learning_time,
                'learning_metrics': self.learning_metrics.copy(),
                'recommendations': self._generate_learning_recommendations(patterns_learned, adaptations)
            }
            
            self.logger.debug(f"Learning completed in {learning_time:.3f}s with {len(patterns_learned)} patterns")
            
            return learning_insights
            
        except Exception as e:
            self.logger.error(f"Error in learning from interaction: {str(e)}")
            return {
                'error': str(e),
                'learning_time': time.time() - start_time
            }
    
    def _create_learning_event(self, query, result) -> LearningEvent:
        """Create a learning event from query and result."""
        import hashlib
        
        # Generate unique event ID
        event_data = f"{query.query}_{time.time()}"
        event_id = hashlib.md5(event_data.encode()).hexdigest()
        
        # Extract result quality
        result_quality = getattr(result, 'confidence', 0.5)
        if hasattr(result, 'result') and isinstance(result.result, dict):
            validation = result.result.get('validation', {})
            if isinstance(validation, dict):
                result_quality = validation.get('validation_score', result_quality)
        
        # Extract processing time
        processing_time = getattr(result, 'processing_time', 0.0)
        
        # Extract system metrics
        system_metrics = {
            'source_count': len(getattr(result, 'sources', [])),
            'confidence': getattr(result, 'confidence', 0.5),
            'query_length': len(query.query),
            'query_complexity': self._assess_query_complexity(query.query)
        }
        
        return LearningEvent(
            event_id=event_id,
            event_type='query_interaction',
            query=query.query,
            result_quality=result_quality,
            processing_time=processing_time,
            system_metrics=system_metrics
        )
    
    async def _extract_patterns(self, learning_event: LearningEvent) -> List[LearningPattern]:
        """Extract patterns from a learning event."""
        patterns = []
        
        # Query pattern extraction
        query_patterns = await self._extract_query_patterns(learning_event)
        patterns.extend(query_patterns)
        
        # Performance pattern extraction
        performance_patterns = await self._extract_performance_patterns(learning_event)
        patterns.extend(performance_patterns)
        
        # Quality pattern extraction
        quality_patterns = await self._extract_quality_patterns(learning_event)
        patterns.extend(quality_patterns)
        
        # Store patterns in learning system
        for pattern in patterns:
            pattern_key = f"{pattern.pattern_type}_{pattern.pattern_id}"
            if pattern_key in self.learning_patterns:
                # Update existing pattern
                existing = self.learning_patterns[pattern_key]
                existing.frequency += 1
                existing.last_seen = pattern.last_seen
                existing.confidence = min(0.95, existing.confidence + 0.05)
            else:
                # Add new pattern
                self.learning_patterns[pattern_key] = pattern
        
        return patterns
    
    async def _extract_query_patterns(self, learning_event: LearningEvent) -> List[LearningPattern]:
        """Extract query-related patterns."""
        patterns = []
        query = learning_event.query
        
        # Query length pattern
        query_length = len(query)
        length_category = 'short' if query_length < 20 else 'medium' if query_length < 100 else 'long'
        
        patterns.append(LearningPattern(
            pattern_id=f"length_{length_category}",
            pattern_type="query",
            pattern_data={
                'length_category': length_category,
                'avg_processing_time': learning_event.processing_time,
                'avg_quality': learning_event.result_quality
            }
        ))
        
        # Query type pattern
        query_type = self._classify_query_type(query)
        patterns.append(LearningPattern(
            pattern_id=f"type_{query_type}",
            pattern_type="query",
            pattern_data={
                'query_type': query_type,
                'avg_processing_time': learning_event.processing_time,
                'avg_quality': learning_event.result_quality
            }
        ))
        
        # Domain pattern
        if 'kenny' in query.lower():
            patterns.append(LearningPattern(
                pattern_id="domain_kenny",
                pattern_type="query",
                pattern_data={
                    'domain': 'kenny',
                    'avg_processing_time': learning_event.processing_time,
                    'avg_quality': learning_event.result_quality
                }
            ))
        
        return patterns
    
    async def _extract_performance_patterns(self, learning_event: LearningEvent) -> List[LearningPattern]:
        """Extract performance-related patterns."""
        patterns = []
        
        # Processing time pattern
        time_category = self._categorize_processing_time(learning_event.processing_time)
        patterns.append(LearningPattern(
            pattern_id=f"processing_time_{time_category}",
            pattern_type="performance",
            pattern_data={
                'time_category': time_category,
                'processing_time': learning_event.processing_time,
                'quality': learning_event.result_quality,
                'source_count': learning_event.system_metrics.get('source_count', 0)
            }
        ))
        
        # Quality-time correlation pattern
        quality_time_ratio = learning_event.result_quality / max(learning_event.processing_time, 1.0)
        efficiency_category = 'high' if quality_time_ratio > 0.05 else 'medium' if quality_time_ratio > 0.02 else 'low'
        
        patterns.append(LearningPattern(
            pattern_id=f"efficiency_{efficiency_category}",
            pattern_type="performance",
            pattern_data={
                'efficiency_category': efficiency_category,
                'quality_time_ratio': quality_time_ratio,
                'processing_time': learning_event.processing_time,
                'quality': learning_event.result_quality
            }
        ))
        
        return patterns
    
    async def _extract_quality_patterns(self, learning_event: LearningEvent) -> List[LearningPattern]:
        """Extract quality-related patterns."""
        patterns = []
        
        # Quality category pattern
        quality = learning_event.result_quality
        quality_category = 'high' if quality > 0.8 else 'medium' if quality > 0.6 else 'low'
        
        patterns.append(LearningPattern(
            pattern_id=f"quality_{quality_category}",
            pattern_type="quality",
            pattern_data={
                'quality_category': quality_category,
                'quality_score': quality,
                'source_count': learning_event.system_metrics.get('source_count', 0),
                'query_complexity': learning_event.system_metrics.get('query_complexity', 'medium')
            }
        ))
        
        # Source-quality correlation
        source_count = learning_event.system_metrics.get('source_count', 0)
        if source_count > 0:
            quality_per_source = quality / source_count
            source_efficiency = 'high' if quality_per_source > 0.1 else 'medium' if quality_per_source > 0.05 else 'low'
            
            patterns.append(LearningPattern(
                pattern_id=f"source_efficiency_{source_efficiency}",
                pattern_type="quality",
                pattern_data={
                    'source_efficiency': source_efficiency,
                    'quality_per_source': quality_per_source,
                    'source_count': source_count,
                    'total_quality': quality
                }
            ))
        
        return patterns
    
    async def _update_learning_models(self, learning_event: LearningEvent, patterns: List[LearningPattern]):
        """Update learning models with new information."""
        # Update query patterns
        query_key = self._get_query_key(learning_event.query)
        self.query_patterns[query_key] += 1
        
        # Update performance history
        self.performance_history.append({
            'timestamp': learning_event.timestamp,
            'processing_time': learning_event.processing_time,
            'quality': learning_event.result_quality,
            'query_type': self._classify_query_type(learning_event.query)
        })
        
        # Update pattern-based models
        for pattern in patterns:
            if pattern.pattern_type == 'performance':
                self._update_performance_model(pattern)
            elif pattern.pattern_type == 'quality':
                self._update_quality_model(pattern)
    
    async def _check_for_adaptations(self, learning_event: LearningEvent) -> List[Dict[str, Any]]:
        """Check if any adaptations should be triggered."""
        if not self.config.get('adaptation_enabled', True):
            return []
        
        adaptations = []
        
        for rule in self.adaptation_rules:
            if rule.enabled and self._evaluate_adaptation_condition(rule, learning_event):
                adaptation = {
                    'rule_id': rule.rule_id,
                    'rule_type': rule.rule_type,
                    'action': rule.action,
                    'trigger_event': learning_event.event_id,
                    'effectiveness': rule.effectiveness
                }
                adaptations.append(adaptation)
                
                # Update rule usage
                rule.usage_count += 1
                
                # Apply adaptation
                await self._apply_adaptation(rule, learning_event)
        
        return adaptations
    
    def _evaluate_adaptation_condition(self, rule: AdaptationRule, learning_event: LearningEvent) -> bool:
        """Evaluate if an adaptation rule condition is met."""
        condition = rule.condition
        
        # Get relevant metrics
        if rule.rule_type == 'performance':
            current_metrics = {
                'avg_processing_time': self._get_recent_avg_processing_time(),
                'processing_time': learning_event.processing_time
            }
        elif rule.rule_type == 'quality':
            current_metrics = {
                'avg_result_quality': self._get_recent_avg_quality(),
                'result_quality': learning_event.result_quality
            }
        elif rule.rule_type == 'caching':
            query_key = self._get_query_key(learning_event.query)
            current_metrics = {
                'query_frequency': self.query_patterns.get(query_key, 0)
            }
        else:
            current_metrics = {
                'result_confidence': learning_event.result_quality,
                'processing_time': learning_event.processing_time
            }
        
        # Evaluate conditions
        return self._evaluate_conditions(condition, current_metrics)
    
    def _evaluate_conditions(self, condition: Dict[str, Any], metrics: Dict[str, Any]) -> bool:
        """Evaluate a set of conditions against metrics."""
        for metric_name, condition_spec in condition.items():
            if metric_name not in metrics:
                continue
            
            metric_value = metrics[metric_name]
            
            if isinstance(condition_spec, dict):
                for operator, threshold in condition_spec.items():
                    if operator == 'gt' and metric_value <= threshold:
                        return False
                    elif operator == 'lt' and metric_value >= threshold:
                        return False
                    elif operator == 'eq' and metric_value != threshold:
                        return False
            else:
                # Direct value comparison
                if metric_value != condition_spec:
                    return False
        
        return True
    
    async def _apply_adaptation(self, rule: AdaptationRule, learning_event: LearningEvent):
        """Apply an adaptation rule."""
        action = rule.action
        
        # Store adaptation in state
        if rule.rule_type not in self.adaptation_state:
            self.adaptation_state[rule.rule_type] = {}
        
        self.adaptation_state[rule.rule_type].update(action)
        
        self.logger.info(f"Applied adaptation rule: {rule.rule_id}")
    
    def _update_learning_metrics(self, learning_event: LearningEvent, 
                                patterns: List[LearningPattern], 
                                adaptations: List[Dict[str, Any]]):
        """Update learning performance metrics."""
        self.learning_metrics['total_learning_events'] += 1
        self.learning_metrics['patterns_learned'] += len(patterns)
        self.learning_metrics['adaptations_applied'] += len(adaptations)
        
        # Update learning accuracy (simplified)
        if learning_event.result_quality > 0.7:
            current_accuracy = self.learning_metrics.get('learning_accuracy', 0.0)
            self.learning_metrics['learning_accuracy'] = (current_accuracy * 0.9 + 
                                                        learning_event.result_quality * 0.1)
        
        # Update adaptation effectiveness
        if adaptations:
            avg_effectiveness = sum(a['effectiveness'] for a in adaptations) / len(adaptations)
            current_effectiveness = self.learning_metrics.get('adaptation_effectiveness', 0.0)
            self.learning_metrics['adaptation_effectiveness'] = (current_effectiveness * 0.9 + 
                                                               avg_effectiveness * 0.1)
    
    def _generate_learning_recommendations(self, patterns: List[LearningPattern], 
                                         adaptations: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on learning."""
        recommendations = []
        
        # Pattern-based recommendations
        if patterns:
            high_frequency_patterns = [p for p in patterns if p.frequency >= 3]
            if high_frequency_patterns:
                recommendations.append(f"Found {len(high_frequency_patterns)} recurring patterns - consider optimization")
        
        # Adaptation recommendations
        if adaptations:
            performance_adaptations = [a for a in adaptations if a['rule_type'] == 'performance']
            if performance_adaptations:
                recommendations.append("Performance adaptations applied - monitor effectiveness")
            
            quality_adaptations = [a for a in adaptations if a['rule_type'] == 'quality']
            if quality_adaptations:
                recommendations.append("Quality adaptations applied - verify result improvements")
        
        # Learning effectiveness recommendations
        if self.learning_metrics.get('learning_accuracy', 0.0) < 0.6:
            recommendations.append("Learning accuracy is low - consider adjusting learning parameters")
        
        return recommendations[:3]  # Limit recommendations
    
    # Helper methods
    def _assess_query_complexity(self, query: str) -> str:
        """Assess query complexity."""
        word_count = len(query.split())
        if word_count <= 5:
            return 'simple'
        elif word_count <= 15:
            return 'medium'
        else:
            return 'complex'
    
    def _classify_query_type(self, query: str) -> str:
        """Classify query type."""
        query_lower = query.lower()
        if query_lower.startswith(('how', 'how to')):
            return 'procedural'
        elif query_lower.startswith(('what', 'what is')):
            return 'definitional'
        elif query_lower.startswith(('where', 'when')):
            return 'factual'
        elif query_lower.startswith('why'):
            return 'causal'
        else:
            return 'general'
    
    def _categorize_processing_time(self, processing_time: float) -> str:
        """Categorize processing time."""
        if processing_time < 5.0:
            return 'fast'
        elif processing_time < 15.0:
            return 'medium'
        else:
            return 'slow'
    
    def _get_query_key(self, query: str) -> str:
        """Generate a key for query patterns."""
        # Normalize query for pattern matching
        normalized = query.lower().strip()
        words = normalized.split()[:5]  # Use first 5 words
        return '_'.join(words)
    
    def _get_recent_avg_processing_time(self) -> float:
        """Get recent average processing time."""
        recent_events = list(self.performance_history)[-20:]  # Last 20 events
        if recent_events:
            times = [event['processing_time'] for event in recent_events]
            return statistics.mean(times)
        return 10.0  # Default
    
    def _get_recent_avg_quality(self) -> float:
        """Get recent average quality."""
        recent_events = list(self.performance_history)[-20:]  # Last 20 events
        if recent_events:
            qualities = [event['quality'] for event in recent_events]
            return statistics.mean(qualities)
        return 0.5  # Default
    
    def _update_performance_model(self, pattern: LearningPattern):
        """Update performance model with pattern."""
        pattern_id = pattern.pattern_id
        if pattern_id not in self.performance_patterns:
            self.performance_patterns[pattern_id] = {
                'count': 0,
                'avg_time': 0.0,
                'avg_quality': 0.0
            }
        
        model = self.performance_patterns[pattern_id]
        model['count'] += 1
        
        # Update averages
        data = pattern.pattern_data
        if 'processing_time' in data:
            model['avg_time'] = ((model['avg_time'] * (model['count'] - 1) + 
                                data['processing_time']) / model['count'])
        
        if 'quality' in data:
            model['avg_quality'] = ((model['avg_quality'] * (model['count'] - 1) + 
                                   data['quality']) / model['count'])
    
    def _update_quality_model(self, pattern: LearningPattern):
        """Update quality model with pattern."""
        pattern_id = pattern.pattern_id
        if pattern_id not in self.result_quality_patterns:
            self.result_quality_patterns[pattern_id] = {
                'count': 0,
                'avg_quality': 0.0,
                'factors': {}
            }
        
        model = self.result_quality_patterns[pattern_id]
        model['count'] += 1
        
        # Update quality average
        data = pattern.pattern_data
        if 'quality_score' in data:
            model['avg_quality'] = ((model['avg_quality'] * (model['count'] - 1) + 
                                   data['quality_score']) / model['count'])
        
        # Update factors
        for key, value in data.items():
            if key != 'quality_score':
                if key not in model['factors']:
                    model['factors'][key] = []
                model['factors'][key].append(value)
                
                # Keep only recent factors
                if len(model['factors'][key]) > 100:
                    model['factors'][key] = model['factors'][key][-50:]
    
    def _load_learning_data(self):
        """Load learning data from persistence."""
        persistence_file = self.config.get('persistence_file')
        if persistence_file and os.path.exists(persistence_file):
            try:
                with open(persistence_file, 'rb') as f:
                    data = pickle.load(f)
                    self.learning_patterns = data.get('learning_patterns', {})
                    self.query_patterns = data.get('query_patterns', defaultdict(int))
                    self.performance_patterns = data.get('performance_patterns', {})
                    self.result_quality_patterns = data.get('result_quality_patterns', {})
                    self.learning_metrics = data.get('learning_metrics', {})
                
                self.logger.info(f"Loaded {len(self.learning_patterns)} learning patterns from persistence")
            except Exception as e:
                self.logger.warning(f"Failed to load learning data: {str(e)}")
    
    async def _persist_learning_data(self):
        """Persist learning data."""
        persistence_file = self.config.get('persistence_file')
        if persistence_file:
            try:
                data = {
                    'learning_patterns': self.learning_patterns,
                    'query_patterns': dict(self.query_patterns),
                    'performance_patterns': self.performance_patterns,
                    'result_quality_patterns': self.result_quality_patterns,
                    'learning_metrics': self.learning_metrics,
                    'timestamp': time.time()
                }
                
                with open(persistence_file, 'wb') as f:
                    pickle.dump(data, f)
                
            except Exception as e:
                self.logger.warning(f"Failed to persist learning data: {str(e)}")
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get comprehensive learning insights."""
        insights = {
            'learning_metrics': self.learning_metrics.copy(),
            'total_patterns': len(self.learning_patterns),
            'active_adaptations': len(self.adaptation_state),
            'query_patterns_count': len(self.query_patterns),
            'most_frequent_queries': self._get_top_query_patterns(),
            'performance_insights': self._get_performance_insights(),
            'quality_insights': self._get_quality_insights(),
            'adaptation_effectiveness': self._get_adaptation_effectiveness()
        }
        
        return insights
    
    def _get_top_query_patterns(self) -> List[Dict[str, Any]]:
        """Get top query patterns."""
        sorted_patterns = sorted(self.query_patterns.items(), key=lambda x: x[1], reverse=True)
        return [{'pattern': pattern, 'frequency': freq} for pattern, freq in sorted_patterns[:10]]
    
    def _get_performance_insights(self) -> Dict[str, Any]:
        """Get performance-related insights."""
        if not self.performance_history:
            return {}
        
        recent_times = [event['processing_time'] for event in list(self.performance_history)[-50:]]
        
        return {
            'avg_processing_time': statistics.mean(recent_times) if recent_times else 0.0,
            'processing_time_trend': self._calculate_trend(recent_times),
            'fast_queries_ratio': len([t for t in recent_times if t < 5.0]) / len(recent_times) if recent_times else 0.0
        }
    
    def _get_quality_insights(self) -> Dict[str, Any]:
        """Get quality-related insights."""
        if not self.performance_history:
            return {}
        
        recent_qualities = [event['quality'] for event in list(self.performance_history)[-50:]]
        
        return {
            'avg_quality': statistics.mean(recent_qualities) if recent_qualities else 0.0,
            'quality_trend': self._calculate_trend(recent_qualities),
            'high_quality_ratio': len([q for q in recent_qualities if q > 0.8]) / len(recent_qualities) if recent_qualities else 0.0
        }
    
    def _get_adaptation_effectiveness(self) -> Dict[str, Any]:
        """Get adaptation effectiveness metrics."""
        effectiveness = {}
        
        for rule in self.adaptation_rules:
            if rule.usage_count > 0:
                effectiveness[rule.rule_id] = {
                    'usage_count': rule.usage_count,
                    'effectiveness': rule.effectiveness,
                    'rule_type': rule.rule_type
                }
        
        return effectiveness
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values."""
        if len(values) < 3:
            return 'stable'
        
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        if second_avg > first_avg * 1.1:
            return 'increasing'
        elif second_avg < first_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    async def shutdown(self):
        """Gracefully shutdown the learner."""
        self.logger.info("Shutting down Contextual Learner...")
        
        # Persist final learning state
        if self.config.get('persistence_enabled', True):
            await self._persist_learning_data()
        
        self.logger.info("Contextual Learner shutdown complete")