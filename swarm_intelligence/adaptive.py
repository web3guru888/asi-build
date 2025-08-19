"""
Adaptive Swarm Parameters

This module implements adaptive parameter control for swarm
intelligence algorithms, automatically tuning parameters
based on performance feedback.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class AdaptationStrategy(Enum):
    """Parameter adaptation strategies"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    PERFORMANCE_BASED = "performance_based"
    FUZZY_LOGIC = "fuzzy_logic"
    REINFORCEMENT_LEARNING = "reinforcement_learning"


@dataclass
class ParameterRange:
    """Parameter range definition"""
    min_value: float
    max_value: float
    current_value: float
    adaptation_rate: float = 0.1


class AdaptiveSwarmParameters:
    """Adaptive parameter control system for swarm algorithms"""
    
    def __init__(self, initial_params: Dict[str, ParameterRange]):
        self.parameters = initial_params
        self.performance_history = []
        self.parameter_history = {name: [] for name in initial_params.keys()}
        self.adaptation_strategy = AdaptationStrategy.PERFORMANCE_BASED
        
    def update_parameters(self, current_performance: float,
                         improvement: float) -> Dict[str, float]:
        """Update parameters based on performance feedback"""
        
        self.performance_history.append(current_performance)
        
        # Record current parameter values
        for name, param in self.parameters.items():
            self.parameter_history[name].append(param.current_value)
        
        if self.adaptation_strategy == AdaptationStrategy.PERFORMANCE_BASED:
            return self._performance_based_adaptation(improvement)
        elif self.adaptation_strategy == AdaptationStrategy.LINEAR:
            return self._linear_adaptation()
        elif self.adaptation_strategy == AdaptationStrategy.EXPONENTIAL:
            return self._exponential_adaptation()
        else:
            return self._get_current_values()
    
    def _performance_based_adaptation(self, improvement: float) -> Dict[str, float]:
        """Adapt parameters based on performance improvement"""
        
        for name, param in self.parameters.items():
            if improvement > 0:
                # Good performance - small adjustment
                adjustment = param.adaptation_rate * 0.5
            else:
                # Poor performance - larger adjustment
                adjustment = param.adaptation_rate * 1.5
            
            # Random exploration vs exploitation decision
            if np.random.random() < 0.5:
                # Increase parameter
                new_value = min(param.max_value, 
                               param.current_value + adjustment)
            else:
                # Decrease parameter
                new_value = max(param.min_value,
                               param.current_value - adjustment)
            
            param.current_value = new_value
        
        return self._get_current_values()
    
    def _linear_adaptation(self) -> Dict[str, float]:
        """Linear parameter adaptation over time"""
        iteration = len(self.performance_history)
        max_iterations = 1000  # Assumed max iterations
        
        for name, param in self.parameters.items():
            # Linear interpolation from max to min
            progress = min(iteration / max_iterations, 1.0)
            param.current_value = (param.max_value - 
                                 progress * (param.max_value - param.min_value))
        
        return self._get_current_values()
    
    def _exponential_adaptation(self) -> Dict[str, float]:
        """Exponential parameter adaptation"""
        iteration = len(self.performance_history)
        
        for name, param in self.parameters.items():
            # Exponential decay
            decay_rate = 0.95
            param.current_value = max(param.min_value,
                                    param.current_value * decay_rate)
        
        return self._get_current_values()
    
    def _get_current_values(self) -> Dict[str, float]:
        """Get current parameter values"""
        return {name: param.current_value for name, param in self.parameters.items()}
    
    def analyze_parameter_impact(self) -> Dict[str, float]:
        """Analyze the impact of each parameter on performance"""
        if len(self.performance_history) < 10:
            return {}
        
        impacts = {}
        
        for name in self.parameters.keys():
            param_values = self.parameter_history[name][-10:]
            performance_values = self.performance_history[-10:]
            
            # Calculate correlation
            if len(param_values) == len(performance_values):
                correlation = np.corrcoef(param_values, performance_values)[0, 1]
                impacts[name] = abs(correlation) if not np.isnan(correlation) else 0.0
        
        return impacts
    
    def get_adaptation_summary(self) -> Dict[str, Any]:
        """Get summary of parameter adaptation"""
        return {
            'current_parameters': self._get_current_values(),
            'parameter_impacts': self.analyze_parameter_impact(),
            'adaptation_strategy': self.adaptation_strategy.value,
            'total_adaptations': len(self.performance_history),
            'performance_trend': self._calculate_performance_trend()
        }
    
    def _calculate_performance_trend(self) -> float:
        """Calculate recent performance trend"""
        if len(self.performance_history) < 5:
            return 0.0
        
        recent_performance = self.performance_history[-5:]
        x = np.arange(len(recent_performance))
        slope = np.polyfit(x, recent_performance, 1)[0]
        return float(slope)


class FuzzyParameterController:
    """Fuzzy logic controller for parameter adaptation"""
    
    def __init__(self):
        self.rules = self._initialize_fuzzy_rules()
    
    def _initialize_fuzzy_rules(self) -> List[Dict[str, Any]]:
        """Initialize fuzzy logic rules"""
        return [
            {
                'condition': {'performance': 'low', 'diversity': 'low'},
                'action': {'exploration': 'increase', 'exploitation': 'decrease'}
            },
            {
                'condition': {'performance': 'high', 'diversity': 'high'},
                'action': {'exploration': 'maintain', 'exploitation': 'increase'}
            },
            {
                'condition': {'performance': 'medium', 'diversity': 'medium'},
                'action': {'exploration': 'decrease', 'exploitation': 'increase'}
            }
        ]
    
    def fuzzy_adapt(self, performance: float, diversity: float,
                   current_params: Dict[str, float]) -> Dict[str, float]:
        """Apply fuzzy logic adaptation"""
        # Simplified fuzzy logic implementation
        adapted_params = current_params.copy()
        
        # Fuzzification
        perf_low = max(0, min(1, (0.5 - performance) / 0.5))
        perf_high = max(0, min(1, (performance - 0.5) / 0.5))
        
        div_low = max(0, min(1, (0.3 - diversity) / 0.3))
        div_high = max(0, min(1, (diversity - 0.3) / 0.3))
        
        # Apply rules
        if perf_low > 0.5 and div_low > 0.5:
            # Increase exploration
            if 'exploration_rate' in adapted_params:
                adapted_params['exploration_rate'] *= 1.2
        
        if perf_high > 0.5:
            # Increase exploitation
            if 'exploitation_rate' in adapted_params:
                adapted_params['exploitation_rate'] *= 1.1
        
        return adapted_params


# Factory functions
def create_adaptive_pso_parameters() -> AdaptiveSwarmParameters:
    """Create adaptive parameters for PSO"""
    initial_params = {
        'inertia_weight': ParameterRange(0.1, 0.9, 0.7, 0.05),
        'c1': ParameterRange(0.5, 3.0, 2.0, 0.1),
        'c2': ParameterRange(0.5, 3.0, 2.0, 0.1)
    }
    return AdaptiveSwarmParameters(initial_params)


def create_adaptive_aco_parameters() -> AdaptiveSwarmParameters:
    """Create adaptive parameters for ACO"""
    initial_params = {
        'alpha': ParameterRange(0.5, 2.0, 1.0, 0.05),
        'beta': ParameterRange(1.0, 5.0, 2.0, 0.1),
        'rho': ParameterRange(0.01, 0.5, 0.1, 0.02)
    }
    return AdaptiveSwarmParameters(initial_params)