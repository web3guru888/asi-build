"""
Aesthetic Reinforcement Learning

This module implements reinforcement learning for aesthetic evaluation and improvement,
allowing AGI to learn and refine aesthetic judgment through experience.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import deque
import random


@dataclass
class AestheticState:
    """Represents aesthetic state for RL."""
    artwork_features: np.ndarray
    context_features: np.ndarray
    aesthetic_scores: Dict[str, float]


@dataclass
class AestheticAction:
    """Represents aesthetic action for RL."""
    action_type: str
    parameters: Dict[str, float]
    strength: float


class AestheticRL:
    """Reinforcement learning system for aesthetic evaluation and improvement."""
    
    def __init__(self, state_dim: int = 128, action_dim: int = 32):
        """Initialize aesthetic RL system."""
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # RL components
        self.q_network = AestheticQNetwork(state_dim, action_dim)
        self.target_network = AestheticQNetwork(state_dim, action_dim)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=0.001)
        
        # Experience replay
        self.memory = deque(maxlen=10000)
        self.batch_size = 64
        
        # Exploration
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        
        # Update target network
        self.update_target_every = 100
        self.step_count = 0
        
        print("🤖 Aesthetic RL system initialized")
        
    def get_aesthetic_state(self, artwork: Any, context: Dict[str, Any] = None) -> AestheticState:
        """Convert artwork and context to RL state."""
        # Extract features from artwork
        if isinstance(artwork, np.ndarray):
            if len(artwork.shape) == 3:  # Image
                artwork_features = self._extract_visual_features(artwork)
            elif len(artwork.shape) == 1:  # Audio
                artwork_features = self._extract_audio_features(artwork)
            else:
                artwork_features = np.mean(artwork, axis=tuple(range(len(artwork.shape)-1)))
        else:
            artwork_features = np.random.randn(64)  # Placeholder
            
        # Extract context features
        context_features = self._extract_context_features(context or {})
        
        # Initial aesthetic scores (to be learned)
        aesthetic_scores = {
            'beauty': 0.5,
            'harmony': 0.5,
            'complexity': 0.5,
            'novelty': 0.5
        }
        
        return AestheticState(
            artwork_features=artwork_features,
            context_features=context_features,
            aesthetic_scores=aesthetic_scores
        )
        
    def select_aesthetic_action(self, state: AestheticState, 
                              available_actions: List[str] = None) -> AestheticAction:
        """Select aesthetic improvement action using epsilon-greedy policy."""
        if available_actions is None:
            available_actions = ['enhance_color', 'adjust_composition', 'modify_texture', 
                               'change_contrast', 'alter_rhythm', 'shift_harmony']
            
        # Combine state features
        state_tensor = torch.FloatTensor(
            np.concatenate([state.artwork_features, state.context_features])
        ).unsqueeze(0)
        
        if random.random() < self.epsilon:
            # Explore: random action
            action_type = random.choice(available_actions)
            parameters = {key: random.uniform(-1, 1) for key in ['intensity', 'direction', 'scope']}
            strength = random.uniform(0.1, 1.0)
        else:
            # Exploit: use Q-network
            with torch.no_grad():
                q_values = self.q_network(state_tensor)
                action_idx = torch.argmax(q_values).item()
                
            # Map action index to action type
            action_type = available_actions[action_idx % len(available_actions)]
            
            # Generate parameters based on Q-values
            parameters = {
                'intensity': float(q_values[0, action_idx % self.action_dim]),
                'direction': float(q_values[0, (action_idx + 1) % self.action_dim]),
                'scope': float(q_values[0, (action_idx + 2) % self.action_dim])
            }
            strength = min(1.0, max(0.1, float(q_values[0, action_idx])))
            
        return AestheticAction(
            action_type=action_type,
            parameters=parameters,
            strength=strength
        )
        
    def apply_aesthetic_action(self, artwork: Any, action: AestheticAction) -> Any:
        """Apply aesthetic action to artwork."""
        if action.action_type == 'enhance_color':
            return self._enhance_color(artwork, action)
        elif action.action_type == 'adjust_composition':
            return self._adjust_composition(artwork, action)
        elif action.action_type == 'modify_texture':
            return self._modify_texture(artwork, action)
        elif action.action_type == 'change_contrast':
            return self._change_contrast(artwork, action)
        elif action.action_type == 'alter_rhythm':
            return self._alter_rhythm(artwork, action)
        elif action.action_type == 'shift_harmony':
            return self._shift_harmony(artwork, action)
        else:
            return artwork  # No change for unknown actions
            
    def calculate_aesthetic_reward(self, original_state: AestheticState, 
                                 new_state: AestheticState,
                                 action: AestheticAction,
                                 human_feedback: Optional[float] = None) -> float:
        """Calculate reward for aesthetic improvement."""
        # Base reward from aesthetic score improvement
        beauty_improvement = new_state.aesthetic_scores['beauty'] - original_state.aesthetic_scores['beauty']
        harmony_improvement = new_state.aesthetic_scores['harmony'] - original_state.aesthetic_scores['harmony']
        
        base_reward = (beauty_improvement + harmony_improvement) / 2
        
        # Bonus for complexity-novelty balance
        complexity = new_state.aesthetic_scores['complexity']
        novelty = new_state.aesthetic_scores['novelty']
        balance_bonus = 1.0 - abs(complexity - novelty)  # Reward balance
        
        # Penalty for excessive changes
        action_penalty = -0.1 * action.strength if action.strength > 0.8 else 0.0
        
        # Human feedback integration
        human_bonus = 0.0
        if human_feedback is not None:
            human_bonus = human_feedback * 0.5  # Weight human feedback
            
        total_reward = base_reward + 0.2 * balance_bonus + action_penalty + human_bonus
        
        return total_reward
        
    def train_step(self, state: AestheticState, action: AestheticAction,
                  reward: float, next_state: AestheticState, done: bool):
        """Perform one training step."""
        # Store experience
        experience = (state, action, reward, next_state, done)
        self.memory.append(experience)
        
        # Train if enough experiences
        if len(self.memory) >= self.batch_size:
            self._replay_training()
            
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        # Update target network
        self.step_count += 1
        if self.step_count % self.update_target_every == 0:
            self._update_target_network()
            
    def _replay_training(self):
        """Train on batch of experiences."""
        # Sample batch
        batch = random.sample(self.memory, self.batch_size)
        
        states = []
        actions = []
        rewards = []
        next_states = []
        dones = []
        
        for state, action, reward, next_state, done in batch:
            state_features = np.concatenate([state.artwork_features, state.context_features])
            next_state_features = np.concatenate([next_state.artwork_features, next_state.context_features])
            
            states.append(state_features)
            actions.append(self._action_to_index(action))
            rewards.append(reward)
            next_states.append(next_state_features)
            dones.append(done)
            
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)
        dones = torch.BoolTensor(dones)
        
        # Current Q-values
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        
        # Next Q-values from target network
        next_q_values = self.target_network(next_states).max(1)[0].detach()
        target_q_values = rewards + (0.99 * next_q_values * ~dones)
        
        # Loss and optimization
        loss = F.mse_loss(current_q_values.squeeze(), target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
    def _update_target_network(self):
        """Update target network with current network weights."""
        self.target_network.load_state_dict(self.q_network.state_dict())
        
    def _action_to_index(self, action: AestheticAction) -> int:
        """Convert action to index for Q-learning."""
        action_types = ['enhance_color', 'adjust_composition', 'modify_texture', 
                       'change_contrast', 'alter_rhythm', 'shift_harmony']
        if action.action_type in action_types:
            return action_types.index(action.action_type)
        return 0
        
    def _extract_visual_features(self, image: np.ndarray) -> np.ndarray:
        """Extract features from visual artwork."""
        if len(image.shape) == 3:
            # Color statistics
            mean_color = np.mean(image, axis=(0, 1))
            std_color = np.std(image, axis=(0, 1))
            
            # Convert to grayscale for other features
            gray = np.mean(image, axis=2)
        else:
            gray = image
            mean_color = [np.mean(gray)]
            std_color = [np.std(gray)]
            
        # Texture features
        gradients = np.gradient(gray)
        gradient_magnitude = np.sqrt(gradients[0]**2 + gradients[1]**2)
        
        features = np.concatenate([
            mean_color,
            std_color,
            [np.mean(gradient_magnitude)],
            [np.std(gradient_magnitude)],
            [np.mean(gray)],
            [np.std(gray)]
        ])
        
        # Pad or truncate to 64 features
        if len(features) < 64:
            features = np.pad(features, (0, 64 - len(features)))
        else:
            features = features[:64]
            
        return features
        
    def _extract_audio_features(self, audio: np.ndarray) -> np.ndarray:
        """Extract features from audio artwork."""
        # Basic audio features
        features = [
            np.mean(audio),
            np.std(audio),
            np.max(audio),
            np.min(audio)
        ]
        
        # Spectral features (simplified)
        if len(audio) >= 1024:
            fft = np.fft.fft(audio[:1024])
            magnitude = np.abs(fft)
            features.extend([
                np.mean(magnitude),
                np.std(magnitude),
                np.argmax(magnitude)  # Dominant frequency
            ])
        else:
            features.extend([0, 0, 0])
            
        # Pad to 64 features
        while len(features) < 64:
            features.append(0.0)
            
        return np.array(features[:64])
        
    def _extract_context_features(self, context: Dict[str, Any]) -> np.ndarray:
        """Extract features from context."""
        features = []
        
        # Time-based features
        import time
        current_time = time.time()
        features.extend([
            current_time % (24 * 3600) / (24 * 3600),  # Time of day
            (current_time % (7 * 24 * 3600)) / (7 * 24 * 3600)  # Day of week
        ])
        
        # Context-specific features
        if 'user_preference' in context:
            features.append(context['user_preference'])
        else:
            features.append(0.5)
            
        if 'style_preference' in context:
            features.append(context['style_preference'])
        else:
            features.append(0.5)
            
        # Pad to 64 features
        while len(features) < 64:
            features.append(0.0)
            
        return np.array(features[:64])
        
    def _enhance_color(self, artwork: Any, action: AestheticAction) -> Any:
        """Enhance color in artwork."""
        if not isinstance(artwork, np.ndarray) or len(artwork.shape) != 3:
            return artwork
            
        intensity = action.parameters.get('intensity', 0.0)
        enhanced = artwork.copy()
        
        # Simple color enhancement
        enhanced = enhanced * (1 + intensity * action.strength * 0.2)
        enhanced = np.clip(enhanced, 0, 1)
        
        return enhanced
        
    def _adjust_composition(self, artwork: Any, action: AestheticAction) -> Any:
        """Adjust composition of artwork."""
        # Placeholder implementation
        return artwork
        
    def _modify_texture(self, artwork: Any, action: AestheticAction) -> Any:
        """Modify texture in artwork."""
        # Placeholder implementation
        return artwork
        
    def _change_contrast(self, artwork: Any, action: AestheticAction) -> Any:
        """Change contrast in artwork."""
        if not isinstance(artwork, np.ndarray):
            return artwork
            
        intensity = action.parameters.get('intensity', 0.0)
        contrast_factor = 1 + intensity * action.strength * 0.5
        
        if len(artwork.shape) == 3:
            # Image
            mean_val = np.mean(artwork)
            adjusted = (artwork - mean_val) * contrast_factor + mean_val
        else:
            # Audio or 1D
            mean_val = np.mean(artwork)
            adjusted = (artwork - mean_val) * contrast_factor + mean_val
            
        return np.clip(adjusted, 0, 1)
        
    def _alter_rhythm(self, artwork: Any, action: AestheticAction) -> Any:
        """Alter rhythm in artwork (mainly for audio)."""
        # Placeholder implementation
        return artwork
        
    def _shift_harmony(self, artwork: Any, action: AestheticAction) -> Any:
        """Shift harmony in artwork."""
        # Placeholder implementation
        return artwork
        
    def evaluate_aesthetic_improvement(self, original_artwork: Any, 
                                     improved_artwork: Any) -> Dict[str, float]:
        """Evaluate aesthetic improvement between artworks."""
        original_state = self.get_aesthetic_state(original_artwork)
        improved_state = self.get_aesthetic_state(improved_artwork)
        
        # Calculate improvements
        beauty_improvement = improved_state.aesthetic_scores['beauty'] - original_state.aesthetic_scores['beauty']
        harmony_improvement = improved_state.aesthetic_scores['harmony'] - original_state.aesthetic_scores['harmony']
        complexity_change = improved_state.aesthetic_scores['complexity'] - original_state.aesthetic_scores['complexity']
        novelty_change = improved_state.aesthetic_scores['novelty'] - original_state.aesthetic_scores['novelty']
        
        return {
            'beauty_improvement': beauty_improvement,
            'harmony_improvement': harmony_improvement,
            'complexity_change': complexity_change,
            'novelty_change': novelty_change,
            'overall_improvement': (beauty_improvement + harmony_improvement) / 2
        }


class AestheticQNetwork(nn.Module):
    """Q-Network for aesthetic reinforcement learning."""
    
    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        
        self.network = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)
        )
        
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.network(state)