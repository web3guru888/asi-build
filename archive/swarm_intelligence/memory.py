"""
Swarm Memory and Learning Systems

This module implements memory and learning capabilities for
swarm intelligence algorithms, enabling experience retention
and adaptive behavior improvement.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import pickle
import json


@dataclass
class Experience:
    """Represents a learning experience"""
    state: np.ndarray
    action: str
    reward: float
    next_state: np.ndarray
    timestamp: float
    metadata: Dict[str, Any] = None


class SwarmMemorySystem:
    """Memory system for swarm intelligence algorithms"""
    
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.experiences = deque(maxlen=capacity)
        self.learned_patterns = {}
        self.performance_history = []
    
    def add_experience(self, experience: Experience) -> None:
        """Add new experience to memory"""
        self.experiences.append(experience)
    
    def get_recent_experiences(self, n: int = 10) -> List[Experience]:
        """Get n most recent experiences"""
        return list(self.experiences)[-n:]
    
    def learn_from_experiences(self) -> Dict[str, Any]:
        """Learn patterns from stored experiences"""
        if len(self.experiences) < 10:
            return {}
        
        # Simple pattern learning
        rewards = [exp.reward for exp in self.experiences]
        actions = [exp.action for exp in self.experiences]
        
        # Find best performing actions
        action_rewards = {}
        for action, reward in zip(actions, rewards):
            if action not in action_rewards:
                action_rewards[action] = []
            action_rewards[action].append(reward)
        
        # Calculate average rewards per action
        action_performance = {}
        for action, reward_list in action_rewards.items():
            action_performance[action] = np.mean(reward_list)
        
        self.learned_patterns = action_performance
        return action_performance
    
    def get_best_action(self, state: np.ndarray) -> str:
        """Get best action based on learned patterns"""
        if not self.learned_patterns:
            return "explore"  # Default action
        
        return max(self.learned_patterns, key=self.learned_patterns.get)
    
    def save_memory(self, filepath: str) -> None:
        """Save memory to file"""
        memory_data = {
            'experiences': [
                {
                    'state': exp.state.tolist(),
                    'action': exp.action,
                    'reward': exp.reward,
                    'next_state': exp.next_state.tolist(),
                    'timestamp': exp.timestamp,
                    'metadata': exp.metadata
                }
                for exp in self.experiences
            ],
            'learned_patterns': self.learned_patterns,
            'performance_history': self.performance_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(memory_data, f, indent=2)
    
    def load_memory(self, filepath: str) -> None:
        """Load memory from file"""
        with open(filepath, 'r') as f:
            memory_data = json.load(f)
        
        # Reconstruct experiences
        self.experiences.clear()
        for exp_data in memory_data['experiences']:
            experience = Experience(
                state=np.array(exp_data['state']),
                action=exp_data['action'],
                reward=exp_data['reward'],
                next_state=np.array(exp_data['next_state']),
                timestamp=exp_data['timestamp'],
                metadata=exp_data.get('metadata')
            )
            self.experiences.append(experience)
        
        self.learned_patterns = memory_data.get('learned_patterns', {})
        self.performance_history = memory_data.get('performance_history', [])


class AdaptiveLearningSystem:
    """Adaptive learning system for swarm algorithms"""
    
    def __init__(self):
        self.memory = SwarmMemorySystem()
        self.learning_rate = 0.1
        self.adaptation_threshold = 0.05
    
    def adapt_parameters(self, current_performance: float,
                        algorithm_params: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt algorithm parameters based on performance"""
        self.memory.performance_history.append(current_performance)
        
        if len(self.memory.performance_history) < 10:
            return algorithm_params
        
        # Check if adaptation is needed
        recent_performance = self.memory.performance_history[-10:]
        performance_trend = np.polyfit(range(len(recent_performance)), recent_performance, 1)[0]
        
        adapted_params = algorithm_params.copy()
        
        if performance_trend < -self.adaptation_threshold:
            # Performance declining - increase exploration
            if 'exploration_rate' in adapted_params:
                adapted_params['exploration_rate'] *= 1.1
            if 'mutation_rate' in adapted_params:
                adapted_params['mutation_rate'] *= 1.1
        
        elif performance_trend > self.adaptation_threshold:
            # Performance improving - maintain or increase exploitation
            if 'exploitation_rate' in adapted_params:
                adapted_params['exploitation_rate'] *= 1.05
        
        return adapted_params


# Factory function
def create_swarm_memory_system(capacity: int = 1000) -> SwarmMemorySystem:
    """Create swarm memory system"""
    return SwarmMemorySystem(capacity)