"""
Multi-Modal Art Generation Engine

This module implements comprehensive multi-modal art generation capabilities,
supporting visual, audio, text, and interactive art forms with cross-modal synthesis.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum
import cv2
from PIL import Image
import librosa
import matplotlib.pyplot as plt
from scipy import signal
import json
import base64
from io import BytesIO


class Modality(Enum):
    """Supported art modalities."""
    VISUAL = "visual"
    AUDIO = "audio"
    TEXT = "text"
    INTERACTIVE = "interactive"
    HAPTIC = "haptic"
    TEMPORAL = "temporal"


class GenerationStyle(Enum):
    """Art generation styles."""
    ABSTRACT = "abstract"
    REALISTIC = "realistic"
    IMPRESSIONISTIC = "impressionistic"
    MINIMALIST = "minimalist"
    EXPRESSIONIST = "expressionist"
    SURREAL = "surreal"
    GEOMETRIC = "geometric"
    ORGANIC = "organic"


@dataclass
class ArtworkSpec:
    """Specification for artwork generation."""
    primary_modality: Modality
    secondary_modalities: List[Modality]
    style: GenerationStyle
    dimensions: Dict[str, int]  # width, height, duration, etc.
    theme: str
    mood: str
    complexity: float  # 0.0 to 1.0
    cultural_context: Optional[str] = None
    constraints: Dict[str, Any] = None


@dataclass
class GeneratedArtwork:
    """Container for generated artwork."""
    artwork_id: str
    modalities: Dict[Modality, Any]
    metadata: Dict[str, Any]
    generation_params: ArtworkSpec
    quality_metrics: Dict[str, float]
    cross_modal_mappings: Dict[str, Any]


class VisualGenerator(nn.Module):
    """Neural network for visual art generation."""
    
    def __init__(self, latent_dim: int = 512, output_size: Tuple[int, int] = (512, 512)):
        super().__init__()
        self.latent_dim = latent_dim
        self.output_size = output_size
        
        # Generator network
        self.generator = nn.Sequential(
            # Input: latent_dim
            nn.Linear(latent_dim, 256 * 8 * 8),
            nn.ReLU(),
            nn.Unflatten(1, (256, 8, 8)),
            
            # Upsample to 16x16
            nn.ConvTranspose2d(256, 128, 4, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            
            # Upsample to 32x32
            nn.ConvTranspose2d(128, 64, 4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            
            # Upsample to 64x64
            nn.ConvTranspose2d(64, 32, 4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            
            # Upsample to 128x128
            nn.ConvTranspose2d(32, 16, 4, stride=2, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            
            # Upsample to 256x256
            nn.ConvTranspose2d(16, 8, 4, stride=2, padding=1),
            nn.BatchNorm2d(8),
            nn.ReLU(),
            
            # Upsample to 512x512
            nn.ConvTranspose2d(8, 3, 4, stride=2, padding=1),
            nn.Tanh()
        )
        
        # Style control network
        self.style_encoder = nn.Sequential(
            nn.Linear(32, 128),  # Style features
            nn.ReLU(),
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, latent_dim // 2)
        )
        
    def forward(self, noise: torch.Tensor, style_features: torch.Tensor) -> torch.Tensor:
        # Combine noise and style
        style_encoded = self.style_encoder(style_features)
        combined_input = torch.cat([noise, style_encoded], dim=1)
        
        return self.generator(combined_input)
        
    def generate_visual_art(self, spec: ArtworkSpec) -> np.ndarray:
        """Generate visual artwork based on specification."""
        batch_size = 1
        noise_dim = self.latent_dim // 2
        
        # Create noise vector
        noise = torch.randn(batch_size, noise_dim)
        
        # Create style features based on spec
        style_features = self._spec_to_style_features(spec)
        
        with torch.no_grad():
            generated = self.forward(noise, style_features)
            
        # Convert to numpy and normalize
        artwork = generated.squeeze(0).permute(1, 2, 0).numpy()
        artwork = (artwork + 1) / 2  # Denormalize from [-1, 1] to [0, 1]
        artwork = np.clip(artwork, 0, 1)
        
        return artwork
        
    def _spec_to_style_features(self, spec: ArtworkSpec) -> torch.Tensor:
        """Convert artwork specification to style feature vector."""
        features = torch.zeros(1, 32)
        
        # Style encoding
        style_map = {
            GenerationStyle.ABSTRACT: 0,
            GenerationStyle.REALISTIC: 1,
            GenerationStyle.IMPRESSIONISTIC: 2,
            GenerationStyle.MINIMALIST: 3,
            GenerationStyle.EXPRESSIONIST: 4,
            GenerationStyle.SURREAL: 5,
            GenerationStyle.GEOMETRIC: 6,
            GenerationStyle.ORGANIC: 7
        }
        
        if spec.style in style_map:
            features[0, style_map[spec.style]] = 1.0
            
        # Mood encoding (simplified)
        mood_features = self._encode_mood(spec.mood)
        features[0, 8:16] = torch.tensor(mood_features)
        
        # Complexity
        features[0, 16] = spec.complexity
        
        # Theme encoding
        theme_features = self._encode_theme(spec.theme)
        features[0, 17:25] = torch.tensor(theme_features)
        
        return features
        
    def _encode_mood(self, mood: str) -> List[float]:
        """Encode mood string to feature vector."""
        mood_encodings = {
            'happy': [1.0, 0.8, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0],
            'sad': [0.0, 0.0, 0.2, 1.0, 0.8, 0.0, 0.0, 0.0],
            'energetic': [0.8, 0.9, 0.0, 0.0, 0.0, 1.0, 0.7, 0.0],
            'calm': [0.2, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 1.0],
            'mysterious': [0.0, 0.0, 0.0, 0.7, 0.9, 0.5, 0.0, 0.3],
            'dramatic': [0.0, 0.0, 0.0, 0.9, 0.0, 0.8, 1.0, 0.0]
        }
        
        return mood_encodings.get(mood.lower(), [0.5] * 8)
        
    def _encode_theme(self, theme: str) -> List[float]:
        """Encode theme string to feature vector."""
        theme_encodings = {
            'nature': [1.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            'urban': [0.0, 0.0, 1.0, 0.8, 0.0, 0.0, 0.0, 0.0],
            'abstract': [0.0, 0.0, 0.0, 0.0, 1.0, 0.9, 0.0, 0.0],
            'portrait': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.8],
            'landscape': [0.8, 1.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0],
            'still_life': [0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8, 1.0]
        }
        
        return theme_encodings.get(theme.lower(), [0.5] * 8)


class AudioGenerator:
    """Generator for audio/musical art."""
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.fundamental_frequencies = {
            'C': 261.63, 'D': 293.66, 'E': 329.63, 'F': 349.23,
            'G': 392.00, 'A': 440.00, 'B': 493.88
        }
        
    def generate_audio_art(self, spec: ArtworkSpec) -> np.ndarray:
        """Generate audio artwork based on specification."""
        duration = spec.dimensions.get('duration', 30)  # seconds
        
        if spec.style == GenerationStyle.ABSTRACT:
            return self._generate_abstract_audio(spec, duration)
        elif spec.style == GenerationStyle.MINIMALIST:
            return self._generate_minimalist_audio(spec, duration)
        elif spec.style == GenerationStyle.ORGANIC:
            return self._generate_organic_audio(spec, duration)
        else:
            return self._generate_harmonic_audio(spec, duration)
            
    def _generate_abstract_audio(self, spec: ArtworkSpec, duration: float) -> np.ndarray:
        """Generate abstract audio composition."""
        samples = int(duration * self.sample_rate)
        audio = np.zeros(samples)
        
        # Create layered abstract sounds
        num_layers = int(3 + spec.complexity * 5)
        
        for layer in range(num_layers):
            # Random frequency modulation
            base_freq = np.random.uniform(80, 2000)
            freq_modulation = np.random.uniform(0.1, 5.0)
            amplitude_modulation = np.random.uniform(0.1, 2.0)
            
            t = np.linspace(0, duration, samples)
            
            # Generate complex waveform
            frequency = base_freq * (1 + 0.1 * np.sin(2 * np.pi * freq_modulation * t))
            amplitude = 0.1 / num_layers * (1 + 0.5 * np.sin(2 * np.pi * amplitude_modulation * t))
            
            # Mix different waveforms
            if layer % 3 == 0:
                wave = np.sin(2 * np.pi * frequency * t)
            elif layer % 3 == 1:
                wave = signal.sawtooth(2 * np.pi * frequency * t)
            else:
                wave = signal.square(2 * np.pi * frequency * t)
                
            # Apply envelope
            envelope = self._create_envelope(samples, layer / num_layers)
            layer_audio = amplitude * wave * envelope
            
            audio += layer_audio
            
        # Apply mood-based filtering
        audio = self._apply_mood_processing(audio, spec.mood)
        
        return np.clip(audio, -1.0, 1.0)
        
    def _generate_minimalist_audio(self, spec: ArtworkSpec, duration: float) -> np.ndarray:
        """Generate minimalist audio composition."""
        samples = int(duration * self.sample_rate)
        audio = np.zeros(samples)
        
        # Simple repetitive patterns
        pattern_length = 2.0  # seconds
        pattern_samples = int(pattern_length * self.sample_rate)
        
        # Create basic pattern
        base_freq = self.fundamental_frequencies['C'] * (2 ** (spec.complexity * 2))
        t_pattern = np.linspace(0, pattern_length, pattern_samples)
        
        # Simple sine wave with gentle modulation
        pattern = np.sin(2 * np.pi * base_freq * t_pattern)
        pattern *= self._create_envelope(pattern_samples, 0.5)
        
        # Repeat pattern with slight variations
        num_repeats = int(duration / pattern_length)
        for i in range(num_repeats):
            start_idx = i * pattern_samples
            end_idx = min(start_idx + pattern_samples, samples)
            
            # Add slight variations
            variation = 1.0 + 0.02 * np.sin(2 * np.pi * i / num_repeats)
            audio[start_idx:end_idx] = pattern[:end_idx-start_idx] * variation
            
        return audio
        
    def _generate_organic_audio(self, spec: ArtworkSpec, duration: float) -> np.ndarray:
        """Generate organic, nature-inspired audio."""
        samples = int(duration * self.sample_rate)
        audio = np.zeros(samples)
        
        t = np.linspace(0, duration, samples)
        
        # Breathing-like rhythm
        breath_freq = 0.2  # 12 breaths per minute
        breath_envelope = 0.5 * (1 + np.sin(2 * np.pi * breath_freq * t))
        
        # Organic frequency modulation (like bird songs)
        base_freq = 440 * (2 ** (spec.complexity - 0.5))
        organic_modulation = np.cumsum(np.random.normal(0, 0.1, samples))
        organic_modulation = signal.savgol_filter(organic_modulation, 1001, 3)  # Smooth
        
        frequency = base_freq * (1 + 0.3 * organic_modulation / np.std(organic_modulation))
        
        # Generate organic waveform
        phase = np.cumsum(2 * np.pi * frequency / self.sample_rate)
        audio = breath_envelope * np.sin(phase)
        
        # Add harmonics
        for harmonic in [2, 3, 5]:
            harmonic_amplitude = 0.3 / harmonic
            audio += harmonic_amplitude * breath_envelope * np.sin(harmonic * phase)
            
        return np.clip(audio, -1.0, 1.0)
        
    def _generate_harmonic_audio(self, spec: ArtworkSpec, duration: float) -> np.ndarray:
        """Generate harmonic audio composition."""
        samples = int(duration * self.sample_rate)
        audio = np.zeros(samples)
        
        # Choose key based on mood
        key_map = {
            'happy': ['C', 'E', 'G'],
            'sad': ['A', 'C', 'E'],
            'energetic': ['G', 'B', 'D'],
            'calm': ['F', 'A', 'C'],
            'mysterious': ['D', 'F', 'A'],
            'dramatic': ['B', 'D', 'F']
        }
        
        chord = key_map.get(spec.mood.lower(), ['C', 'E', 'G'])
        
        # Generate chord progression
        t = np.linspace(0, duration, samples)
        
        for i, note in enumerate(chord):
            freq = self.fundamental_frequencies[note]
            
            # Add some complexity-based variation
            freq *= (1 + spec.complexity * 0.1 * np.sin(2 * np.pi * 0.1 * t))
            
            # Generate note
            note_audio = np.sin(2 * np.pi * freq * t)
            
            # Apply envelope
            envelope = self._create_envelope(samples, i / len(chord))
            note_audio *= envelope
            
            audio += note_audio / len(chord)
            
        return np.clip(audio, -1.0, 1.0)
        
    def _create_envelope(self, samples: int, phase: float) -> np.ndarray:
        """Create amplitude envelope."""
        attack_samples = int(samples * 0.1)
        decay_samples = int(samples * 0.1)
        sustain_samples = samples - attack_samples - decay_samples
        
        envelope = np.ones(samples)
        
        # Attack
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay/Release
        if decay_samples > 0:
            envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)
            
        return envelope
        
    def _apply_mood_processing(self, audio: np.ndarray, mood: str) -> np.ndarray:
        """Apply mood-specific audio processing."""
        if mood.lower() == 'mysterious':
            # Add reverb-like effect
            delay_samples = int(0.1 * self.sample_rate)
            delayed = np.zeros_like(audio)
            delayed[delay_samples:] = audio[:-delay_samples] * 0.3
            audio = audio + delayed
        elif mood.lower() == 'energetic':
            # Add slight distortion
            audio = np.tanh(audio * 2) * 0.7
        elif mood.lower() == 'calm':
            # Low-pass filter
            nyquist = self.sample_rate // 2
            b, a = signal.butter(4, 1000 / nyquist, 'low')
            audio = signal.filtfilt(b, a, audio)
            
        return audio


class TextGenerator:
    """Generator for text-based art and poetry."""
    
    def __init__(self):
        self.poetic_forms = {
            'haiku': {'lines': 3, 'syllables': [5, 7, 5]},
            'sonnet': {'lines': 14, 'syllables': [10] * 14},
            'free_verse': {'lines': None, 'syllables': None},
            'concrete': {'lines': None, 'syllables': None, 'visual': True}
        }
        
        self.word_banks = {
            'nature': ['tree', 'river', 'mountain', 'sky', 'wind', 'earth', 'sun', 'moon'],
            'emotion': ['love', 'joy', 'sorrow', 'hope', 'fear', 'peace', 'passion', 'dream'],
            'abstract': ['time', 'space', 'thought', 'memory', 'spirit', 'soul', 'essence', 'being'],
            'urban': ['city', 'street', 'building', 'light', 'crowd', 'noise', 'movement', 'steel']
        }
        
    def generate_text_art(self, spec: ArtworkSpec) -> str:
        """Generate text-based artwork."""
        if spec.style == GenerationStyle.MINIMALIST:
            return self._generate_minimalist_text(spec)
        elif spec.style == GenerationStyle.ABSTRACT:
            return self._generate_abstract_text(spec)
        elif spec.style == GenerationStyle.ORGANIC:
            return self._generate_organic_text(spec)
        else:
            return self._generate_structured_text(spec)
            
    def _generate_minimalist_text(self, spec: ArtworkSpec) -> str:
        """Generate minimalist text art."""
        theme_words = self.word_banks.get(spec.theme.lower(), self.word_banks['abstract'])
        
        # Very sparse, haiku-like structure
        lines = []
        num_lines = max(1, int(3 * spec.complexity))
        
        for _ in range(num_lines):
            if np.random.random() < 0.7:  # 70% chance of single word
                word = np.random.choice(theme_words)
                lines.append(word)
            else:  # 30% chance of two words
                word1 = np.random.choice(theme_words)
                word2 = np.random.choice(self.word_banks['emotion'])
                lines.append(f"{word1}, {word2}")
                
        return '\n'.join(lines)
        
    def _generate_abstract_text(self, spec: ArtworkSpec) -> str:
        """Generate abstract text art."""
        # Word fragmentation and recombination
        theme_words = self.word_banks.get(spec.theme.lower(), self.word_banks['abstract'])
        
        fragments = []
        for word in theme_words:
            # Fragment words
            if len(word) > 3:
                mid = len(word) // 2
                fragments.extend([word[:mid], word[mid:]])
            else:
                fragments.append(word)
                
        # Recombine in abstract ways
        lines = []
        num_lines = int(5 + spec.complexity * 10)
        
        for _ in range(num_lines):
            if np.random.random() < 0.4:
                # Single fragment
                lines.append(np.random.choice(fragments))
            elif np.random.random() < 0.7:
                # Combined fragments
                frag1 = np.random.choice(fragments)
                frag2 = np.random.choice(fragments)
                lines.append(f"{frag1}{frag2}")
            else:
                # Spaced fragments
                frag1 = np.random.choice(fragments)
                frag2 = np.random.choice(fragments)
                spaces = ' ' * np.random.randint(1, 6)
                lines.append(f"{frag1}{spaces}{frag2}")
                
        return '\n'.join(lines)
        
    def _generate_organic_text(self, spec: ArtworkSpec) -> str:
        """Generate organic, flowing text art."""
        theme_words = self.word_banks.get(spec.theme.lower(), self.word_banks['nature'])
        emotion_words = self.word_banks['emotion']
        
        # Create flowing, nature-inspired text
        lines = []
        num_stanzas = max(1, int(2 + spec.complexity * 3))
        
        for stanza in range(num_stanzas):
            stanza_lines = []
            stanza_length = np.random.randint(2, 5)
            
            for line in range(stanza_length):
                # Build line organically
                line_words = []
                line_length = np.random.randint(2, 6)
                
                for word_pos in range(line_length):
                    if word_pos == 0 or np.random.random() < 0.6:
                        word = np.random.choice(theme_words)
                    else:
                        word = np.random.choice(emotion_words)
                        
                    # Add organic connectors
                    if word_pos > 0 and np.random.random() < 0.3:
                        connectors = ['in', 'through', 'with', 'beneath', 'beyond']
                        line_words.append(np.random.choice(connectors))
                        
                    line_words.append(word)
                    
                stanza_lines.append(' '.join(line_words))
                
            lines.extend(stanza_lines)
            if stanza < num_stanzas - 1:
                lines.append('')  # Empty line between stanzas
                
        return '\n'.join(lines)
        
    def _generate_structured_text(self, spec: ArtworkSpec) -> str:
        """Generate structured text art (sonnets, etc.)."""
        # Simple structured approach
        theme_words = self.word_banks.get(spec.theme.lower(), self.word_banks['abstract'])
        emotion_words = self.word_banks['emotion']
        
        lines = []
        num_lines = int(4 + spec.complexity * 10)
        
        for i in range(num_lines):
            # Create rhyme scheme for every 4 lines
            if i % 4 < 2:
                # A/B rhyme
                ending_sound = 'ing' if i % 2 == 0 else 'ight'
            else:
                # A/B rhyme
                ending_sound = 'tion' if i % 2 == 0 else 'ness'
                
            # Build line with target ending
            line_words = []
            for j in range(np.random.randint(4, 8)):
                if j == 0:
                    word = np.random.choice(theme_words)
                elif j == np.random.randint(4, 8) - 1:  # Last word
                    # Try to create word with target ending
                    base_word = np.random.choice(emotion_words)
                    word = base_word + ending_sound
                else:
                    word = np.random.choice(theme_words + emotion_words)
                    
                line_words.append(word)
                
            lines.append(' '.join(line_words))
            
        return '\n'.join(lines)


class InteractiveGenerator:
    """Generator for interactive art experiences."""
    
    def __init__(self):
        self.interaction_types = [
            'click_to_transform',
            'hover_effects',
            'drag_and_create',
            'sound_reactive',
            'time_based_evolution',
            'collaborative_canvas'
        ]
        
    def generate_interactive_art(self, spec: ArtworkSpec) -> Dict[str, Any]:
        """Generate interactive artwork specification."""
        base_visual = self._create_base_visual(spec)
        interactions = self._design_interactions(spec)
        
        return {
            'type': 'interactive_artwork',
            'base_visual': base_visual,
            'interactions': interactions,
            'metadata': {
                'style': spec.style.value,
                'theme': spec.theme,
                'complexity': spec.complexity
            }
        }
        
    def _create_base_visual(self, spec: ArtworkSpec) -> Dict[str, Any]:
        """Create base visual for interactive artwork."""
        width = spec.dimensions.get('width', 800)
        height = spec.dimensions.get('height', 600)
        
        # Create simple geometric base
        elements = []
        num_elements = int(3 + spec.complexity * 7)
        
        for i in range(num_elements):
            element = {
                'type': np.random.choice(['circle', 'rectangle', 'polygon']),
                'x': np.random.randint(0, width),
                'y': np.random.randint(0, height),
                'size': np.random.randint(20, 100),
                'color': self._generate_color(spec),
                'id': f'element_{i}'
            }
            elements.append(element)
            
        return {
            'width': width,
            'height': height,
            'elements': elements,
            'background_color': self._generate_background_color(spec)
        }
        
    def _design_interactions(self, spec: ArtworkSpec) -> List[Dict[str, Any]]:
        """Design interaction behaviors."""
        interactions = []
        num_interactions = max(1, int(2 + spec.complexity * 3))
        
        for i in range(num_interactions):
            interaction_type = np.random.choice(self.interaction_types)
            
            if interaction_type == 'click_to_transform':
                interactions.append({
                    'type': 'click',
                    'trigger': 'element_click',
                    'effect': 'transform',
                    'parameters': {
                        'scale_change': np.random.uniform(0.5, 2.0),
                        'color_shift': np.random.uniform(0, 360),
                        'animation_duration': np.random.uniform(0.5, 2.0)
                    }
                })
            elif interaction_type == 'hover_effects':
                interactions.append({
                    'type': 'hover',
                    'trigger': 'mouse_over',
                    'effect': 'glow',
                    'parameters': {
                        'glow_intensity': np.random.uniform(0.2, 0.8),
                        'glow_color': self._generate_color(spec)
                    }
                })
            elif interaction_type == 'drag_and_create':
                interactions.append({
                    'type': 'drag',
                    'trigger': 'mouse_drag',
                    'effect': 'create_trail',
                    'parameters': {
                        'trail_width': np.random.randint(2, 10),
                        'trail_color': self._generate_color(spec),
                        'fade_duration': np.random.uniform(2, 5)
                    }
                })
                
        return interactions
        
    def _generate_color(self, spec: ArtworkSpec) -> str:
        """Generate color based on mood and style."""
        mood_colors = {
            'happy': [(255, 255, 0), (255, 165, 0), (255, 192, 203)],
            'sad': [(0, 0, 139), (75, 0, 130), (128, 128, 128)],
            'energetic': [(255, 0, 0), (255, 165, 0), (255, 255, 0)],
            'calm': [(173, 216, 230), (144, 238, 144), (240, 248, 255)],
            'mysterious': [(75, 0, 130), (139, 0, 139), (0, 0, 0)],
            'dramatic': [(220, 20, 60), (139, 0, 0), (0, 0, 0)]
        }
        
        colors = mood_colors.get(spec.mood.lower(), [(128, 128, 128)])
        color = colors[np.random.randint(len(colors))]
        
        # Add some variation
        r, g, b = color
        r = max(0, min(255, r + np.random.randint(-30, 31)))
        g = max(0, min(255, g + np.random.randint(-30, 31)))
        b = max(0, min(255, b + np.random.randint(-30, 31)))
        
        return f"rgb({r}, {g}, {b})"
        
    def _generate_background_color(self, spec: ArtworkSpec) -> str:
        """Generate background color."""
        if spec.style == GenerationStyle.MINIMALIST:
            return "rgb(250, 250, 250)"
        elif spec.mood.lower() == 'mysterious':
            return "rgb(20, 20, 30)"
        elif spec.mood.lower() == 'calm':
            return "rgb(240, 248, 255)"
        else:
            return "rgb(255, 255, 255)"


class MultiModalGenerator:
    """Main multi-modal art generation engine."""
    
    def __init__(self):
        self.visual_generator = VisualGenerator()
        self.audio_generator = AudioGenerator()
        self.text_generator = TextGenerator()
        self.interactive_generator = InteractiveGenerator()
        
        self.cross_modal_mappings = {
            'color_to_pitch': self._map_color_to_pitch,
            'rhythm_to_pattern': self._map_rhythm_to_pattern,
            'text_to_visual': self._map_text_to_visual,
            'visual_to_audio': self._map_visual_to_audio
        }
        
    def generate_artwork(self, spec: ArtworkSpec) -> GeneratedArtwork:
        """Generate multi-modal artwork."""
        artwork_id = f"artwork_{int(np.random.random() * 1000000)}"
        modalities = {}
        cross_modal_mappings = {}
        
        # Generate primary modality
        if spec.primary_modality == Modality.VISUAL:
            modalities[Modality.VISUAL] = self.visual_generator.generate_visual_art(spec)
        elif spec.primary_modality == Modality.AUDIO:
            modalities[Modality.AUDIO] = self.audio_generator.generate_audio_art(spec)
        elif spec.primary_modality == Modality.TEXT:
            modalities[Modality.TEXT] = self.text_generator.generate_text_art(spec)
        elif spec.primary_modality == Modality.INTERACTIVE:
            modalities[Modality.INTERACTIVE] = self.interactive_generator.generate_interactive_art(spec)
            
        # Generate secondary modalities with cross-modal mappings
        for secondary_modality in spec.secondary_modalities:
            if secondary_modality != spec.primary_modality:
                if secondary_modality == Modality.VISUAL and spec.primary_modality == Modality.AUDIO:
                    visual_spec = self._adapt_spec_for_visual(spec, modalities[Modality.AUDIO])
                    modalities[Modality.VISUAL] = self.visual_generator.generate_visual_art(visual_spec)
                    cross_modal_mappings['audio_to_visual'] = self._create_audio_visual_mapping(
                        modalities[Modality.AUDIO], modalities[Modality.VISUAL]
                    )
                elif secondary_modality == Modality.AUDIO and spec.primary_modality == Modality.VISUAL:
                    audio_spec = self._adapt_spec_for_audio(spec, modalities[Modality.VISUAL])
                    modalities[Modality.AUDIO] = self.audio_generator.generate_audio_art(audio_spec)
                    cross_modal_mappings['visual_to_audio'] = self._create_visual_audio_mapping(
                        modalities[Modality.VISUAL], modalities[Modality.AUDIO]
                    )
                elif secondary_modality == Modality.TEXT:
                    text_spec = self._adapt_spec_for_text(spec)
                    modalities[Modality.TEXT] = self.text_generator.generate_text_art(text_spec)
                    
        # Calculate quality metrics
        quality_metrics = self._evaluate_quality(modalities, spec)
        
        return GeneratedArtwork(
            artwork_id=artwork_id,
            modalities=modalities,
            metadata={
                'generation_time': 'now',
                'style': spec.style.value,
                'theme': spec.theme,
                'mood': spec.mood
            },
            generation_params=spec,
            quality_metrics=quality_metrics,
            cross_modal_mappings=cross_modal_mappings
        )
        
    def _adapt_spec_for_visual(self, original_spec: ArtworkSpec, audio_data: np.ndarray) -> ArtworkSpec:
        """Adapt specification for visual generation based on audio."""
        # Analyze audio characteristics
        audio_energy = np.mean(audio_data ** 2)
        audio_dynamics = np.std(audio_data)
        
        # Modify complexity based on audio
        new_complexity = min(1.0, original_spec.complexity + audio_dynamics * 0.5)
        
        return ArtworkSpec(
            primary_modality=Modality.VISUAL,
            secondary_modalities=[],
            style=original_spec.style,
            dimensions=original_spec.dimensions,
            theme=original_spec.theme,
            mood=original_spec.mood,
            complexity=new_complexity,
            cultural_context=original_spec.cultural_context,
            constraints=original_spec.constraints
        )
        
    def _adapt_spec_for_audio(self, original_spec: ArtworkSpec, visual_data: np.ndarray) -> ArtworkSpec:
        """Adapt specification for audio generation based on visual."""
        # Analyze visual characteristics
        visual_complexity = np.std(visual_data)
        visual_brightness = np.mean(visual_data)
        
        # Modify based on visual characteristics
        new_complexity = min(1.0, original_spec.complexity + visual_complexity * 0.3)
        
        return ArtworkSpec(
            primary_modality=Modality.AUDIO,
            secondary_modalities=[],
            style=original_spec.style,
            dimensions={'duration': 30 + visual_brightness * 20},
            theme=original_spec.theme,
            mood=original_spec.mood,
            complexity=new_complexity,
            cultural_context=original_spec.cultural_context,
            constraints=original_spec.constraints
        )
        
    def _adapt_spec_for_text(self, original_spec: ArtworkSpec) -> ArtworkSpec:
        """Adapt specification for text generation."""
        return ArtworkSpec(
            primary_modality=Modality.TEXT,
            secondary_modalities=[],
            style=original_spec.style,
            dimensions=original_spec.dimensions,
            theme=original_spec.theme,
            mood=original_spec.mood,
            complexity=original_spec.complexity,
            cultural_context=original_spec.cultural_context,
            constraints=original_spec.constraints
        )
        
    def _create_audio_visual_mapping(self, audio_data: np.ndarray, 
                                   visual_data: np.ndarray) -> Dict[str, Any]:
        """Create mapping between audio and visual elements."""
        # Analyze audio features
        audio_energy = np.mean(audio_data ** 2)
        audio_spectrum = np.abs(np.fft.fft(audio_data[:1024]))
        dominant_frequency = np.argmax(audio_spectrum)
        
        # Map to visual properties
        brightness = min(1.0, audio_energy * 10)
        hue = (dominant_frequency / len(audio_spectrum)) * 360
        
        return {
            'energy_to_brightness': brightness,
            'frequency_to_hue': hue,
            'dynamics_to_contrast': np.std(audio_data),
            'tempo_to_pattern_density': len(audio_data) / 44100  # Simple tempo estimate
        }
        
    def _create_visual_audio_mapping(self, visual_data: np.ndarray, 
                                   audio_data: np.ndarray) -> Dict[str, Any]:
        """Create mapping between visual and audio elements."""
        # Analyze visual features
        brightness = np.mean(visual_data)
        contrast = np.std(visual_data)
        
        # Analyze audio features
        audio_energy = np.mean(audio_data ** 2)
        audio_pitch = self._estimate_pitch(audio_data)
        
        return {
            'brightness_to_volume': brightness * 0.8,
            'contrast_to_dynamics': contrast,
            'color_to_timbre': np.mean(visual_data, axis=(0, 1)) if len(visual_data.shape) == 3 else [0.5],
            'pattern_to_rhythm': contrast * 2
        }
        
    def _estimate_pitch(self, audio_data: np.ndarray) -> float:
        """Estimate dominant pitch in audio."""
        if len(audio_data) < 1024:
            return 440.0  # Default A4
            
        # Simple autocorrelation-based pitch detection
        autocorr = np.correlate(audio_data[:1024], audio_data[:1024], mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find peak (ignoring zero lag)
        peak_idx = np.argmax(autocorr[1:]) + 1
        
        if peak_idx > 0:
            pitch = 44100 / peak_idx  # Sample rate / period
            return min(2000, max(80, pitch))  # Clamp to reasonable range
        else:
            return 440.0
            
    def _evaluate_quality(self, modalities: Dict[Modality, Any], 
                         spec: ArtworkSpec) -> Dict[str, float]:
        """Evaluate quality of generated artwork."""
        quality_metrics = {}
        
        if Modality.VISUAL in modalities:
            visual_data = modalities[Modality.VISUAL]
            quality_metrics['visual_diversity'] = np.std(visual_data)
            quality_metrics['visual_coherence'] = 1.0 - np.mean(np.abs(np.diff(visual_data, axis=0)))
            
        if Modality.AUDIO in modalities:
            audio_data = modalities[Modality.AUDIO]
            quality_metrics['audio_dynamic_range'] = np.max(audio_data) - np.min(audio_data)
            quality_metrics['audio_spectral_richness'] = len(np.where(np.abs(np.fft.fft(audio_data[:1024])) > 0.1)[0])
            
        if Modality.TEXT in modalities:
            text_data = modalities[Modality.TEXT]
            quality_metrics['text_length'] = len(text_data)
            quality_metrics['text_complexity'] = len(set(text_data.split())) / len(text_data.split()) if text_data.split() else 0
            
        # Overall quality score
        quality_metrics['overall_quality'] = np.mean(list(quality_metrics.values())) if quality_metrics else 0.5
        
        return quality_metrics
        
    def _map_color_to_pitch(self, color: Tuple[float, float, float]) -> float:
        """Map RGB color to musical pitch."""
        r, g, b = color
        # Map to frequency range (80 Hz to 2000 Hz)
        brightness = (r + g + b) / 3
        return 80 + brightness * 1920
        
    def _map_rhythm_to_pattern(self, rhythm_data: np.ndarray) -> Dict[str, Any]:
        """Map rhythmic data to visual pattern."""
        pattern_density = np.mean(np.abs(rhythm_data))
        pattern_regularity = 1.0 - np.std(rhythm_data)
        
        return {
            'density': pattern_density,
            'regularity': pattern_regularity,
            'scale': pattern_density * 10
        }
        
    def _map_text_to_visual(self, text: str) -> Dict[str, Any]:
        """Map text characteristics to visual properties."""
        word_lengths = [len(word) for word in text.split()]
        avg_word_length = np.mean(word_lengths) if word_lengths else 5
        
        return {
            'complexity': avg_word_length / 10,
            'rhythm': np.std(word_lengths) if len(word_lengths) > 1 else 0,
            'texture': len(set(text.lower())) / len(text) if text else 0
        }
        
    def _map_visual_to_audio(self, visual_data: np.ndarray) -> Dict[str, Any]:
        """Map visual characteristics to audio properties."""
        brightness = np.mean(visual_data)
        contrast = np.std(visual_data)
        
        return {
            'volume': brightness,
            'dynamics': contrast,
            'pitch_range': contrast * 1000 + 200,
            'timbre': brightness * 0.5 + 0.25
        }