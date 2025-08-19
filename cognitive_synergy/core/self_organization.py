"""
Self-Organization Mechanisms
============================

Implements self-organization mechanisms for cognitive synergy systems based on
principles from complex adaptive systems, autopoiesis, and emergent dynamics.
"""

import numpy as np
import networkx as nx
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import time
import logging
from scipy.optimize import minimize
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')


@dataclass
class OrganizationRule:
    """Self-organization rule"""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[Dict[str, Any]], Dict[str, Any]]
    priority: float
    activation_threshold: float
    cooldown_time: float = 10.0  # Seconds between applications
    last_applied: float = 0.0
    application_count: int = 0
    effectiveness_history: List[float] = field(default_factory=list)


@dataclass
class OrganizationState:
    """Current organization state"""
    entropy: float = 0.0
    complexity: float = 0.0
    coherence: float = 0.0
    efficiency: float = 0.0
    adaptability: float = 0.0
    stability: float = 0.0
    timestamp: float = field(default_factory=time.time)


class SelfOrganizationMechanism:
    """
    Self-organization system for cognitive synergy.
    
    Implements multiple self-organization principles:
    1. Homeostatic regulation - Maintain optimal operating ranges
    2. Adaptive restructuring - Modify connections and weights
    3. Resource optimization - Efficient allocation of processing resources
    4. Emergent specialization - Development of specialized subsystems
    5. Dynamic load balancing - Distribute cognitive load optimally
    6. Coherence maintenance - Maintain system-wide coherence
    7. Noise-induced transitions - Use noise for exploration
    """
    
    def __init__(self,
                 target_coherence: float = 0.8,
                 adaptation_rate: float = 0.1,
                 stability_threshold: float = 0.1,
                 reorganization_threshold: float = 0.3):
        """
        Initialize self-organization mechanism.
        
        Args:
            target_coherence: Target global coherence level
            adaptation_rate: Rate of adaptive changes
            stability_threshold: Threshold for stability detection
            reorganization_threshold: Threshold triggering major reorganization
        """
        self.target_coherence = target_coherence
        self.adaptation_rate = adaptation_rate
        self.stability_threshold = stability_threshold
        self.reorganization_threshold = reorganization_threshold
        
        # Organization rules
        self.organization_rules = self._initialize_organization_rules()
        
        # State tracking
        self.organization_history = deque(maxlen=1000)
        self.current_state = OrganizationState()
        
        # Optimization components
        self.homeostatic_controller = HomeostaticController()
        self.adaptive_restructurer = AdaptiveRestructurer()
        self.resource_optimizer = ResourceOptimizer()
        self.coherence_maintainer = CoherenceMaintainer()
        
        # Performance tracking
        self.performance_metrics = defaultdict(list)
        self.reorganization_events = deque(maxlen=100)
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def _initialize_organization_rules(self) -> List[OrganizationRule]:
        """Initialize self-organization rules"""
        rules = []
        
        # Homeostatic regulation rules
        rules.append(OrganizationRule(
            name="coherence_regulation",
            condition=lambda state: abs(state.get('global_coherence', 0) - self.target_coherence) > 0.2,
            action=self._regulate_coherence,
            priority=0.9,
            activation_threshold=0.2
        ))
        
        rules.append(OrganizationRule(
            name="load_balancing",
            condition=lambda state: self._detect_load_imbalance(state),
            action=self._balance_load,
            priority=0.7,
            activation_threshold=0.3
        ))
        
        # Adaptive restructuring rules
        rules.append(OrganizationRule(
            name="weak_connection_pruning",
            condition=lambda state: self._detect_weak_connections(state),
            action=self._prune_weak_connections,
            priority=0.6,
            activation_threshold=0.4
        ))
        
        rules.append(OrganizationRule(
            name="strengthen_synergistic_pairs",
            condition=lambda state: self._detect_strong_synergy(state),
            action=self._strengthen_connections,
            priority=0.8,
            activation_threshold=0.7
        ))
        
        # Resource optimization rules
        rules.append(OrganizationRule(
            name="resource_reallocation",
            condition=lambda state: self._detect_resource_inefficiency(state),
            action=self._reallocate_resources,
            priority=0.5,
            activation_threshold=0.3
        ))
        
        # Specialization rules
        rules.append(OrganizationRule(
            name="promote_specialization",
            condition=lambda state: self._detect_specialization_opportunity(state),
            action=self._promote_specialization,
            priority=0.4,
            activation_threshold=0.6
        ))
        
        return rules
    
    def apply(self, 
              synergy_pairs: Dict[str, Any],
              global_coherence: float,
              integration_matrix: np.ndarray,
              performance_history: Dict[str, List[float]]) -> Dict[str, Any]:
        """Apply self-organization mechanisms"""
        
        # Update current state
        self._update_organization_state(
            synergy_pairs, global_coherence, integration_matrix, performance_history
        )
        
        # Apply organization rules
        applied_rules = []
        organization_actions = {}
        
        system_state = {
            'synergy_pairs': synergy_pairs,
            'global_coherence': global_coherence,
            'integration_matrix': integration_matrix,
            'performance_history': performance_history,
            'current_state': self.current_state
        }
        
        # Sort rules by priority
        sorted_rules = sorted(self.organization_rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if self._should_apply_rule(rule, system_state):
                try:
                    action_result = rule.action(system_state)
                    if action_result:
                        organization_actions[rule.name] = action_result
                        applied_rules.append(rule.name)
                        
                        # Update rule application tracking
                        rule.last_applied = time.time()
                        rule.application_count += 1
                        
                        # Evaluate effectiveness (simplified)
                        effectiveness = self._evaluate_rule_effectiveness(rule, action_result)
                        rule.effectiveness_history.append(effectiveness)
                        
                except Exception as e:
                    self.logger.error(f"Error applying rule {rule.name}: {e}")
        
        # Apply specialized mechanisms
        homeostatic_actions = self.homeostatic_controller.apply(system_state)
        restructuring_actions = self.adaptive_restructurer.apply(system_state)
        resource_actions = self.resource_optimizer.apply(system_state)
        coherence_actions = self.coherence_maintainer.apply(system_state)
        
        # Combine all actions
        all_actions = {
            'organization_rules': organization_actions,
            'homeostatic': homeostatic_actions,
            'restructuring': restructuring_actions,
            'resource': resource_actions,
            'coherence': coherence_actions,
            'applied_rules': applied_rules,
            'organization_state': self.current_state
        }
        
        # Record organization event
        self.organization_history.append({
            'timestamp': time.time(),
            'state': self.current_state,
            'actions_applied': len(applied_rules),
            'rules_applied': applied_rules
        })
        
        return all_actions
    
    def _update_organization_state(self, 
                                 synergy_pairs: Dict[str, Any],
                                 global_coherence: float,
                                 integration_matrix: np.ndarray,
                                 performance_history: Dict[str, List[float]]):
        """Update current organization state metrics"""
        
        # Entropy - measure of disorder/uncertainty
        self.current_state.entropy = self._compute_system_entropy(synergy_pairs, integration_matrix)
        
        # Complexity - measure of system complexity
        self.current_state.complexity = self._compute_system_complexity(synergy_pairs, integration_matrix)
        
        # Coherence - global coherence
        self.current_state.coherence = global_coherence
        
        # Efficiency - performance efficiency
        self.current_state.efficiency = self._compute_system_efficiency(performance_history)
        
        # Adaptability - rate of successful adaptations
        self.current_state.adaptability = self._compute_system_adaptability()
        
        # Stability - consistency of performance
        self.current_state.stability = self._compute_system_stability(performance_history)
        
        self.current_state.timestamp = time.time()
    
    def _compute_system_entropy(self, synergy_pairs: Dict[str, Any], 
                              integration_matrix: np.ndarray) -> float:
        """Compute system entropy"""
        try:
            # Entropy from synergy distribution
            synergy_strengths = [pair.get('synergy_strength', 0) for pair in synergy_pairs.values()]
            
            if not synergy_strengths:
                return 1.0  # Maximum entropy
            
            # Normalize to create probability distribution
            total_synergy = sum(synergy_strengths) + 1e-10
            probs = [s / total_synergy for s in synergy_strengths]
            
            # Shannon entropy
            entropy = -sum(p * np.log2(p + 1e-10) for p in probs if p > 0)
            
            # Normalize by maximum possible entropy
            max_entropy = np.log2(len(probs)) if len(probs) > 0 else 1.0
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 1.0
            
            return max(0.0, min(1.0, normalized_entropy))
            
        except Exception:
            return 0.5  # Default moderate entropy
    
    def _compute_system_complexity(self, synergy_pairs: Dict[str, Any],
                                 integration_matrix: np.ndarray) -> float:
        """Compute system complexity"""
        try:
            # Complexity from network structure
            if integration_matrix.size > 0:
                # Graph complexity measures
                G = nx.from_numpy_array(integration_matrix)
                
                # Node and edge complexity
                node_complexity = G.number_of_nodes() / 20.0  # Normalize by expected max
                edge_complexity = G.number_of_edges() / (G.number_of_nodes() * (G.number_of_nodes() - 1) / 2) if G.number_of_nodes() > 1 else 0
                
                # Clustering coefficient as complexity indicator
                try:
                    clustering = nx.average_clustering(G)
                except:
                    clustering = 0.0
                
                complexity = 0.4 * node_complexity + 0.4 * edge_complexity + 0.2 * clustering
                return max(0.0, min(1.0, complexity))
            
            return 0.0
            
        except Exception:
            return 0.5  # Default moderate complexity
    
    def _compute_system_efficiency(self, performance_history: Dict[str, List[float]]) -> float:
        """Compute system efficiency"""
        try:
            if not performance_history:
                return 0.5
            
            # Average recent performance across metrics
            recent_performances = []
            
            for metric_name, history in performance_history.items():
                if history and len(history) > 0:
                    recent_avg = np.mean(history[-10:])  # Last 10 values
                    recent_performances.append(recent_avg)
            
            if recent_performances:
                efficiency = np.mean(recent_performances)
                return max(0.0, min(1.0, efficiency))
            
            return 0.5
            
        except Exception:
            return 0.5
    
    def _compute_system_adaptability(self) -> float:
        """Compute system adaptability"""
        try:
            if len(self.organization_history) < 5:
                return 0.5  # Insufficient history
            
            # Rate of successful adaptations
            recent_adaptations = list(self.organization_history)[-10:]
            
            adaptation_rate = sum(1 for event in recent_adaptations 
                                if event['actions_applied'] > 0) / len(recent_adaptations)
            
            return max(0.0, min(1.0, adaptation_rate))
            
        except Exception:
            return 0.5
    
    def _compute_system_stability(self, performance_history: Dict[str, List[float]]) -> float:
        """Compute system stability"""
        try:
            if not performance_history:
                return 0.5
            
            # Stability as inverse of variance in performance
            stabilities = []
            
            for metric_name, history in performance_history.items():
                if len(history) >= 5:
                    recent_history = history[-20:]  # Last 20 values
                    variance = np.var(recent_history)
                    stability = 1.0 / (1.0 + variance)
                    stabilities.append(stability)
            
            if stabilities:
                return np.mean(stabilities)
            
            return 0.5
            
        except Exception:
            return 0.5
    
    def _should_apply_rule(self, rule: OrganizationRule, system_state: Dict[str, Any]) -> bool:
        """Determine if a rule should be applied"""
        current_time = time.time()
        
        # Check cooldown
        if current_time - rule.last_applied < rule.cooldown_time:
            return False
        
        # Check condition
        try:
            condition_met = rule.condition(system_state)
            return condition_met
        except Exception:
            return False
    
    def _evaluate_rule_effectiveness(self, rule: OrganizationRule, action_result: Dict[str, Any]) -> float:
        """Evaluate effectiveness of applied rule"""
        # Simplified effectiveness evaluation
        # In practice, this would measure actual improvement in target metrics
        
        if 'improvement' in action_result:
            return action_result['improvement']
        
        # Default moderate effectiveness
        return 0.6
    
    # Rule condition checking methods
    def _detect_load_imbalance(self, state: Dict[str, Any]) -> bool:
        """Detect load imbalance across synergy pairs"""
        synergy_pairs = state.get('synergy_pairs', {})
        
        if len(synergy_pairs) < 2:
            return False
        
        synergy_strengths = [pair.get('synergy_strength', 0) for pair in synergy_pairs.values()]
        
        if not synergy_strengths:
            return False
        
        # Check for high variance in synergy strengths
        variance = np.var(synergy_strengths)
        return variance > 0.1  # Threshold for imbalance
    
    def _detect_weak_connections(self, state: Dict[str, Any]) -> bool:
        """Detect weak connections that should be pruned"""
        synergy_pairs = state.get('synergy_pairs', {})
        
        weak_connections = sum(1 for pair in synergy_pairs.values()
                             if pair.get('synergy_strength', 0) < 0.2)
        
        total_connections = len(synergy_pairs)
        
        return total_connections > 0 and weak_connections / total_connections > 0.3
    
    def _detect_strong_synergy(self, state: Dict[str, Any]) -> bool:
        """Detect strong synergy that should be reinforced"""
        synergy_pairs = state.get('synergy_pairs', {})
        
        strong_synergies = sum(1 for pair in synergy_pairs.values()
                             if pair.get('synergy_strength', 0) > 0.8)
        
        return strong_synergies > 0
    
    def _detect_resource_inefficiency(self, state: Dict[str, Any]) -> bool:
        """Detect resource allocation inefficiencies"""
        current_state = state.get('current_state')
        
        if not current_state:
            return False
        
        # Low efficiency indicates resource problems
        return current_state.efficiency < 0.6
    
    def _detect_specialization_opportunity(self, state: Dict[str, Any]) -> bool:
        """Detect opportunities for process specialization"""
        synergy_pairs = state.get('synergy_pairs', {})
        
        # Look for consistently high-performing pairs
        specialized_candidates = sum(1 for pair in synergy_pairs.values()
                                   if pair.get('synergy_strength', 0) > 0.7 and
                                   pair.get('integration_level', 0) > 0.7)
        
        return specialized_candidates > 0
    
    # Rule action methods
    def _regulate_coherence(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Regulate global coherence toward target"""
        current_coherence = state.get('global_coherence', 0)
        target_coherence = self.target_coherence
        
        coherence_diff = target_coherence - current_coherence
        
        if coherence_diff > 0:
            # Increase coherence by strengthening integration
            return {
                'action': 'increase_integration',
                'magnitude': min(0.2, coherence_diff),
                'improvement': abs(coherence_diff) * 0.5
            }
        else:
            # Decrease coherence by introducing controlled noise
            return {
                'action': 'add_noise',
                'magnitude': min(0.1, abs(coherence_diff)),
                'improvement': abs(coherence_diff) * 0.3
            }
    
    def _balance_load(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Balance load across synergy pairs"""
        synergy_pairs = state.get('synergy_pairs', {})
        
        if not synergy_pairs:
            return {}
        
        synergy_strengths = [pair.get('synergy_strength', 0) for pair in synergy_pairs.values()]
        mean_strength = np.mean(synergy_strengths)
        
        # Identify over/under-loaded pairs
        adjustments = {}
        for pair_name, pair_data in synergy_pairs.items():
            strength = pair_data.get('synergy_strength', 0)
            if strength > mean_strength + 0.2:
                adjustments[pair_name] = -0.1  # Reduce load
            elif strength < mean_strength - 0.2:
                adjustments[pair_name] = 0.1   # Increase load
        
        return {
            'action': 'load_balancing',
            'adjustments': adjustments,
            'improvement': 0.7
        }
    
    def _prune_weak_connections(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Prune weak connections"""
        synergy_pairs = state.get('synergy_pairs', {})
        
        weak_pairs = [name for name, pair in synergy_pairs.items()
                     if pair.get('synergy_strength', 0) < 0.2]
        
        return {
            'action': 'prune_connections',
            'pairs_to_prune': weak_pairs[:3],  # Limit pruning per iteration
            'improvement': 0.6
        }
    
    def _strengthen_connections(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Strengthen high-synergy connections"""
        synergy_pairs = state.get('synergy_pairs', {})
        
        strong_pairs = [name for name, pair in synergy_pairs.items()
                       if pair.get('synergy_strength', 0) > 0.8]
        
        return {
            'action': 'strengthen_connections',
            'pairs_to_strengthen': strong_pairs,
            'improvement': 0.8
        }
    
    def _reallocate_resources(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Reallocate computational resources"""
        current_state = state.get('current_state')
        
        if not current_state:
            return {}
        
        return {
            'action': 'resource_reallocation',
            'efficiency_boost': 0.1,
            'improvement': 0.6
        }
    
    def _promote_specialization(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Promote process specialization"""
        synergy_pairs = state.get('synergy_pairs', {})
        
        specialization_candidates = [name for name, pair in synergy_pairs.items()
                                   if pair.get('synergy_strength', 0) > 0.7]
        
        return {
            'action': 'promote_specialization',
            'candidates': specialization_candidates[:2],  # Limit per iteration
            'improvement': 0.7
        }
    
    def get_organization_metrics(self) -> Dict[str, Any]:
        """Get comprehensive organization metrics"""
        return {
            'current_state': {
                'entropy': self.current_state.entropy,
                'complexity': self.current_state.complexity,
                'coherence': self.current_state.coherence,
                'efficiency': self.current_state.efficiency,
                'adaptability': self.current_state.adaptability,
                'stability': self.current_state.stability
            },
            'rule_statistics': {
                rule.name: {
                    'application_count': rule.application_count,
                    'average_effectiveness': np.mean(rule.effectiveness_history[-10:])
                                          if rule.effectiveness_history else 0.0,
                    'last_applied': rule.last_applied
                }
                for rule in self.organization_rules
            },
            'organization_history_summary': {
                'total_events': len(self.organization_history),
                'recent_activity': len([e for e in self.organization_history
                                      if time.time() - e['timestamp'] < 300]),  # Last 5 min
                'average_actions_per_event': np.mean([e['actions_applied'] 
                                                    for e in self.organization_history]) 
                                           if self.organization_history else 0.0
            }
        }


class HomeostaticController:
    """Maintains homeostatic balance in cognitive systems"""
    
    def apply(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply homeostatic control mechanisms"""
        actions = {}
        
        global_coherence = system_state.get('global_coherence', 0)
        target_coherence = 0.8
        
        # Coherence homeostasis
        if abs(global_coherence - target_coherence) > 0.15:
            actions['coherence_adjustment'] = {
                'current': global_coherence,
                'target': target_coherence,
                'adjustment': (target_coherence - global_coherence) * 0.1
            }
        
        return actions


class AdaptiveRestructurer:
    """Handles adaptive restructuring of cognitive architecture"""
    
    def apply(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply adaptive restructuring"""
        actions = {}
        
        integration_matrix = system_state.get('integration_matrix', np.array([]))
        
        if integration_matrix.size > 0:
            # Identify restructuring opportunities
            mean_integration = np.mean(integration_matrix)
            
            if mean_integration < 0.5:
                actions['increase_connectivity'] = {
                    'current_integration': mean_integration,
                    'target_increase': 0.1
                }
            elif mean_integration > 0.9:
                actions['reduce_connectivity'] = {
                    'current_integration': mean_integration,
                    'target_decrease': 0.1
                }
        
        return actions


class ResourceOptimizer:
    """Optimizes resource allocation across cognitive processes"""
    
    def apply(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply resource optimization"""
        actions = {}
        
        current_state = system_state.get('current_state')
        
        if current_state and current_state.efficiency < 0.7:
            actions['resource_optimization'] = {
                'current_efficiency': current_state.efficiency,
                'optimization_target': 0.8,
                'reallocation_needed': True
            }
        
        return actions


class CoherenceMaintainer:
    """Maintains system-wide coherence"""
    
    def apply(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply coherence maintenance"""
        actions = {}
        
        synergy_pairs = system_state.get('synergy_pairs', {})
        
        if synergy_pairs:
            # Check for coherence breaks
            synergy_variance = np.var([pair.get('synergy_strength', 0) 
                                     for pair in synergy_pairs.values()])
            
            if synergy_variance > 0.15:  # High variance indicates coherence issues
                actions['coherence_restoration'] = {
                    'variance': synergy_variance,
                    'action': 'normalize_synergies'
                }
        
        return actions