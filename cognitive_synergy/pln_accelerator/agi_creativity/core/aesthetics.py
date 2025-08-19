"""
Aesthetic Evaluation Metrics Based on Art Theory

This module implements comprehensive aesthetic evaluation systems grounded in
established art theory, psychology of aesthetics, and computational approaches
to beauty and artistic value assessment.
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum
import cv2
from scipy import stats
from sklearn.cluster import KMeans
import networkx as nx
from PIL import Image


class AestheticDimension(Enum):
    """Dimensions of aesthetic evaluation."""
    BEAUTY = "beauty"
    HARMONY = "harmony"
    BALANCE = "balance"
    PROPORTION = "proportion"
    RHYTHM = "rhythm"
    CONTRAST = "contrast"
    UNITY = "unity"
    COMPLEXITY = "complexity"
    NOVELTY = "novelty"
    EXPRESSIVENESS = "expressiveness"
    EMOTIONAL_IMPACT = "emotional_impact"
    CULTURAL_RESONANCE = "cultural_resonance"


@dataclass
class AestheticEvaluation:
    """Comprehensive aesthetic evaluation result."""
    overall_score: float
    dimension_scores: Dict[AestheticDimension, float]
    theoretical_basis: Dict[str, Any]
    confidence: float
    explanation: str
    cultural_context: Optional[str] = None


@dataclass
class AestheticPrinciple:
    """Represents an aesthetic principle from art theory."""
    name: str
    description: str
    measurement_function: callable
    weight: float
    theory_origin: str  # e.g., "Kant", "Birkhoff", "Gestalt"
    applicable_modalities: List[str]


class GestaltPrinciplesEvaluator:
    """Evaluates aesthetics based on Gestalt psychology principles."""
    
    def __init__(self):
        self.principles = {
            'proximity': self._evaluate_proximity,
            'similarity': self._evaluate_similarity,
            'closure': self._evaluate_closure,
            'continuity': self._evaluate_continuity,
            'symmetry': self._evaluate_symmetry,
            'figure_ground': self._evaluate_figure_ground
        }
        
    def evaluate(self, artwork_data: np.ndarray, modality: str = "visual") -> Dict[str, float]:
        """Evaluate artwork based on Gestalt principles."""
        if modality == "visual":
            return self._evaluate_visual_gestalt(artwork_data)
        elif modality == "audio":
            return self._evaluate_audio_gestalt(artwork_data)
        else:
            return {principle: 0.5 for principle in self.principles.keys()}
            
    def _evaluate_visual_gestalt(self, image_data: np.ndarray) -> Dict[str, float]:
        """Evaluate visual artwork using Gestalt principles."""
        scores = {}
        
        # Convert to grayscale if needed
        if len(image_data.shape) == 3:
            gray = cv2.cvtColor((image_data * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = (image_data * 255).astype(np.uint8)
            
        scores['proximity'] = self._evaluate_proximity(gray)
        scores['similarity'] = self._evaluate_similarity(gray)
        scores['closure'] = self._evaluate_closure(gray)
        scores['continuity'] = self._evaluate_continuity(gray)
        scores['symmetry'] = self._evaluate_symmetry(gray)
        scores['figure_ground'] = self._evaluate_figure_ground(gray)
        
        return scores
        
    def _evaluate_audio_gestalt(self, audio_data: np.ndarray) -> Dict[str, float]:
        """Evaluate audio using Gestalt-inspired principles."""
        scores = {}
        
        # Audio proximity (temporal grouping)
        scores['proximity'] = self._audio_temporal_grouping(audio_data)
        
        # Audio similarity (timbral similarity)
        scores['similarity'] = self._audio_timbral_similarity(audio_data)
        
        # Audio closure (melodic completion)
        scores['closure'] = self._audio_melodic_closure(audio_data)
        
        # Audio continuity (smooth transitions)
        scores['continuity'] = self._audio_continuity(audio_data)
        
        # Audio symmetry (rhythmic patterns)
        scores['symmetry'] = self._audio_rhythmic_symmetry(audio_data)
        
        # Audio figure/ground (melody vs accompaniment)
        scores['figure_ground'] = self._audio_figure_ground(audio_data)
        
        return scores
        
    def _evaluate_proximity(self, data: np.ndarray) -> float:
        """Evaluate proximity principle."""
        if len(data.shape) == 2:  # Image
            # Find connected components
            _, labels = cv2.connectedComponents(cv2.threshold(data, 127, 255, cv2.THRESH_BINARY)[1])
            num_components = np.max(labels)
            
            # Calculate average component size
            component_sizes = []
            for i in range(1, num_components + 1):
                component_size = np.sum(labels == i)
                component_sizes.append(component_size)
                
            if component_sizes:
                size_std = np.std(component_sizes)
                size_mean = np.mean(component_sizes)
                proximity_score = 1.0 - min(1.0, size_std / (size_mean + 1e-6))
            else:
                proximity_score = 0.0
                
            return proximity_score
        else:
            return 0.5  # Default for non-image data
            
    def _evaluate_similarity(self, data: np.ndarray) -> float:
        """Evaluate similarity principle."""
        if len(data.shape) == 2:  # Image
            # Use texture analysis
            glcm = self._compute_glcm(data)
            contrast = self._glcm_contrast(glcm)
            homogeneity = self._glcm_homogeneity(glcm)
            
            similarity_score = homogeneity / (contrast + 1e-6)
            return min(1.0, similarity_score)
        else:
            return 0.5
            
    def _evaluate_closure(self, data: np.ndarray) -> float:
        """Evaluate closure principle."""
        if len(data.shape) == 2:  # Image
            # Detect edges and evaluate completeness
            edges = cv2.Canny(data, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Evaluate contour completeness
                total_perimeter = sum(cv2.arcLength(contour, True) for contour in contours)
                total_area = sum(cv2.contourArea(contour) for contour in contours)
                
                if total_area > 0:
                    circularity = 4 * np.pi * total_area / (total_perimeter ** 2 + 1e-6)
                    closure_score = min(1.0, circularity)
                else:
                    closure_score = 0.0
            else:
                closure_score = 0.0
                
            return closure_score
        else:
            return 0.5
            
    def _evaluate_continuity(self, data: np.ndarray) -> float:
        """Evaluate continuity principle."""
        if len(data.shape) == 2:  # Image
            # Evaluate edge continuity
            edges = cv2.Canny(data, 50, 150)
            
            # Use Hough line transform to find continuous lines
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=50)
            
            if lines is not None:
                num_lines = len(lines)
                # More continuous lines = better continuity
                continuity_score = min(1.0, num_lines / 10.0)
            else:
                continuity_score = 0.0
                
            return continuity_score
        else:
            return 0.5
            
    def _evaluate_symmetry(self, data: np.ndarray) -> float:
        """Evaluate symmetry principle."""
        if len(data.shape) == 2:  # Image
            # Horizontal symmetry
            h, w = data.shape
            left_half = data[:, :w//2]
            right_half = np.fliplr(data[:, w//2:])
            
            if left_half.shape == right_half.shape:
                horizontal_symmetry = 1.0 - np.mean(np.abs(left_half - right_half)) / 255.0
            else:
                horizontal_symmetry = 0.0
                
            # Vertical symmetry
            top_half = data[:h//2, :]
            bottom_half = np.flipud(data[h//2:, :])
            
            if top_half.shape == bottom_half.shape:
                vertical_symmetry = 1.0 - np.mean(np.abs(top_half - bottom_half)) / 255.0
            else:
                vertical_symmetry = 0.0
                
            symmetry_score = max(horizontal_symmetry, vertical_symmetry)
            return symmetry_score
        else:
            return 0.5
            
    def _evaluate_figure_ground(self, data: np.ndarray) -> float:
        """Evaluate figure-ground separation."""
        if len(data.shape) == 2:  # Image
            # Use histogram analysis to evaluate figure-ground separation
            hist = cv2.calcHist([data], [0], None, [256], [0, 256])
            
            # Find peaks in histogram (bimodal is better for figure-ground)
            peaks = []
            for i in range(1, len(hist) - 1):
                if hist[i] > hist[i-1] and hist[i] > hist[i+1]:
                    peaks.append(i)
                    
            if len(peaks) >= 2:
                # Calculate separation between main peaks
                peak_values = [hist[peak][0] for peak in peaks]
                peak_positions = peaks
                
                # Sort by peak height
                sorted_peaks = sorted(zip(peak_values, peak_positions), reverse=True)
                
                if len(sorted_peaks) >= 2:
                    separation = abs(sorted_peaks[0][1] - sorted_peaks[1][1]) / 255.0
                    figure_ground_score = min(1.0, separation)
                else:
                    figure_ground_score = 0.0
            else:
                figure_ground_score = 0.0
                
            return figure_ground_score
        else:
            return 0.5
            
    def _audio_temporal_grouping(self, audio_data: np.ndarray) -> float:
        """Evaluate temporal grouping in audio."""
        # Analyze onset detection and grouping
        onset_strength = np.diff(np.abs(audio_data))
        onset_density = np.sum(onset_strength > np.percentile(onset_strength, 90))
        
        # Normalize by audio length
        temporal_grouping = min(1.0, onset_density / (len(audio_data) / 1000))
        return temporal_grouping
        
    def _audio_timbral_similarity(self, audio_data: np.ndarray) -> float:
        """Evaluate timbral similarity in audio."""
        # Use spectral features for timbral analysis
        if len(audio_data) > 1024:
            # Compute short-time Fourier transform
            window_size = 1024
            overlap = 512
            spectrogram = []
            
            for i in range(0, len(audio_data) - window_size, overlap):
                window = audio_data[i:i + window_size]
                spectrum = np.fft.fft(window)
                spectrogram.append(np.abs(spectrum))
                
            spectrogram = np.array(spectrogram)
            
            # Calculate timbral consistency across time
            if len(spectrogram) > 1:
                spectral_consistency = []
                for i in range(1, len(spectrogram)):
                    correlation = np.corrcoef(spectrogram[i-1], spectrogram[i])[0, 1]
                    if not np.isnan(correlation):
                        spectral_consistency.append(correlation)
                        
                if spectral_consistency:
                    similarity_score = np.mean(spectral_consistency)
                    return max(0.0, similarity_score)
                    
        return 0.5
        
    def _audio_melodic_closure(self, audio_data: np.ndarray) -> float:
        """Evaluate melodic closure in audio."""
        # Analyze pitch contour and resolution
        if len(audio_data) > 512:
            # Simple pitch tracking using autocorrelation
            autocorr = np.correlate(audio_data, audio_data, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Find periodic patterns
            peaks = []
            for i in range(1, min(len(autocorr) - 1, 500)):
                if autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1]:
                    peaks.append((i, autocorr[i]))
                    
            if peaks:
                # Evaluate pattern strength
                peak_strengths = [strength for _, strength in peaks]
                closure_score = max(peak_strengths) / (np.max(autocorr) + 1e-6)
                return min(1.0, closure_score)
                
        return 0.5
        
    def _audio_continuity(self, audio_data: np.ndarray) -> float:
        """Evaluate continuity in audio."""
        # Analyze smooth transitions
        if len(audio_data) > 1:
            # Calculate derivative to measure abrupt changes
            derivatives = np.abs(np.diff(audio_data))
            smoothness = 1.0 - (np.mean(derivatives) / (np.max(np.abs(audio_data)) + 1e-6))
            return max(0.0, smoothness)
        return 0.5
        
    def _audio_rhythmic_symmetry(self, audio_data: np.ndarray) -> float:
        """Evaluate rhythmic symmetry in audio."""
        # Analyze beat patterns and symmetry
        if len(audio_data) > 1024:
            # Simple beat detection using energy
            window_size = 256
            energy_profile = []
            
            for i in range(0, len(audio_data) - window_size, window_size // 2):
                window_energy = np.sum(audio_data[i:i + window_size] ** 2)
                energy_profile.append(window_energy)
                
            energy_profile = np.array(energy_profile)
            
            # Look for periodic patterns in energy
            if len(energy_profile) > 4:
                # Check for symmetrical patterns
                mid_point = len(energy_profile) // 2
                first_half = energy_profile[:mid_point]
                second_half = energy_profile[mid_point:mid_point + len(first_half)]
                
                if len(first_half) == len(second_half):
                    correlation = np.corrcoef(first_half, second_half)[0, 1]
                    if not np.isnan(correlation):
                        return max(0.0, correlation)
                        
        return 0.5
        
    def _audio_figure_ground(self, audio_data: np.ndarray) -> float:
        """Evaluate figure-ground separation in audio."""
        # Analyze frequency content separation
        if len(audio_data) > 1024:
            spectrum = np.fft.fft(audio_data[:1024])
            magnitude = np.abs(spectrum)
            
            # Find dominant frequency regions
            peaks = []
            for i in range(1, len(magnitude) - 1):
                if magnitude[i] > magnitude[i-1] and magnitude[i] > magnitude[i+1]:
                    peaks.append((i, magnitude[i]))
                    
            if len(peaks) >= 2:
                # Sort by magnitude
                peaks.sort(key=lambda x: x[1], reverse=True)
                
                # Calculate frequency separation between main peaks
                freq_separation = abs(peaks[0][0] - peaks[1][0]) / len(magnitude)
                magnitude_ratio = peaks[1][1] / (peaks[0][1] + 1e-6)
                
                figure_ground_score = freq_separation * magnitude_ratio
                return min(1.0, figure_ground_score)
                
        return 0.5
        
    def _compute_glcm(self, image: np.ndarray, distance: int = 1, angle: int = 0) -> np.ndarray:
        """Compute Gray-Level Co-occurrence Matrix."""
        # Simplified GLCM computation
        max_val = int(np.max(image))
        glcm = np.zeros((max_val + 1, max_val + 1))
        
        rows, cols = image.shape
        
        for i in range(rows - distance):
            for j in range(cols - distance):
                pixel1 = int(image[i, j])
                pixel2 = int(image[i + distance, j])
                glcm[pixel1, pixel2] += 1
                
        # Normalize
        glcm = glcm / np.sum(glcm)
        return glcm
        
    def _glcm_contrast(self, glcm: np.ndarray) -> float:
        """Calculate contrast from GLCM."""
        contrast = 0.0
        rows, cols = glcm.shape
        
        for i in range(rows):
            for j in range(cols):
                contrast += glcm[i, j] * (i - j) ** 2
                
        return contrast
        
    def _glcm_homogeneity(self, glcm: np.ndarray) -> float:
        """Calculate homogeneity from GLCM."""
        homogeneity = 0.0
        rows, cols = glcm.shape
        
        for i in range(rows):
            for j in range(cols):
                homogeneity += glcm[i, j] / (1 + abs(i - j))
                
        return homogeneity


class BirkhoffAestheticMeasure:
    """Implementation of Birkhoff's aesthetic measure: M = O/C (Order/Complexity)."""
    
    def __init__(self):
        self.complexity_measures = {
            'visual': self._visual_complexity,
            'audio': self._audio_complexity,
            'text': self._text_complexity
        }
        
        self.order_measures = {
            'visual': self._visual_order,
            'audio': self._audio_order,
            'text': self._text_order
        }
        
    def evaluate(self, artwork_data: Any, modality: str) -> Dict[str, float]:
        """Evaluate using Birkhoff's aesthetic measure."""
        if modality not in self.complexity_measures:
            raise ValueError(f"Modality {modality} not supported")
            
        complexity = self.complexity_measures[modality](artwork_data)
        order = self.order_measures[modality](artwork_data)
        
        # Birkhoff's measure: M = O/C
        aesthetic_measure = order / (complexity + 1e-6)
        
        return {
            'complexity': complexity,
            'order': order,
            'aesthetic_measure': aesthetic_measure,
            'birkhoff_score': min(1.0, aesthetic_measure / 2.0)  # Normalize
        }
        
    def _visual_complexity(self, image_data: np.ndarray) -> float:
        """Calculate visual complexity."""
        if len(image_data.shape) == 3:
            gray = cv2.cvtColor((image_data * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = (image_data * 255).astype(np.uint8)
            
        # Edge density as complexity measure
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Color complexity (if color image)
        if len(image_data.shape) == 3:
            # Number of unique colors
            reshaped = image_data.reshape(-1, image_data.shape[-1])
            unique_colors = len(np.unique(reshaped, axis=0))
            color_complexity = unique_colors / reshaped.shape[0]
        else:
            color_complexity = 0.0
            
        return edge_density + color_complexity
        
    def _visual_order(self, image_data: np.ndarray) -> float:
        """Calculate visual order."""
        if len(image_data.shape) == 3:
            gray = cv2.cvtColor((image_data * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = (image_data * 255).astype(np.uint8)
            
        # Symmetry as order measure
        h, w = gray.shape
        
        # Horizontal symmetry
        left_half = gray[:, :w//2]
        right_half = np.fliplr(gray[:, w//2:])
        
        if left_half.shape == right_half.shape:
            h_symmetry = 1.0 - np.mean(np.abs(left_half.astype(float) - right_half.astype(float))) / 255.0
        else:
            h_symmetry = 0.0
            
        # Vertical symmetry
        top_half = gray[:h//2, :]
        bottom_half = np.flipud(gray[h//2:, :])
        
        if top_half.shape == bottom_half.shape:
            v_symmetry = 1.0 - np.mean(np.abs(top_half.astype(float) - bottom_half.astype(float))) / 255.0
        else:
            v_symmetry = 0.0
            
        # Pattern regularity
        patterns = self._detect_patterns(gray)
        
        return max(h_symmetry, v_symmetry) + patterns
        
    def _audio_complexity(self, audio_data: np.ndarray) -> float:
        """Calculate audio complexity."""
        # Spectral complexity
        if len(audio_data) > 1024:
            spectrum = np.fft.fft(audio_data[:1024])
            magnitude = np.abs(spectrum)
            
            # Spectral entropy as complexity
            normalized_magnitude = magnitude / (np.sum(magnitude) + 1e-6)
            spectral_entropy = -np.sum(normalized_magnitude * np.log(normalized_magnitude + 1e-6))
            
            # Temporal complexity
            temporal_variation = np.std(audio_data)
            
            return spectral_entropy / 10.0 + temporal_variation
        else:
            return np.std(audio_data)
            
    def _audio_order(self, audio_data: np.ndarray) -> float:
        """Calculate audio order."""
        # Periodic patterns as order
        if len(audio_data) > 512:
            autocorr = np.correlate(audio_data, audio_data, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Find strongest periodic component
            max_correlation = np.max(autocorr[1:min(len(autocorr), 500)])
            order_score = max_correlation / (np.max(autocorr) + 1e-6)
            
            return min(1.0, order_score)
        else:
            return 0.5
            
    def _text_complexity(self, text_data: str) -> float:
        """Calculate text complexity."""
        if not isinstance(text_data, str):
            return 0.5
            
        # Lexical diversity
        words = text_data.lower().split()
        unique_words = len(set(words))
        total_words = len(words)
        
        lexical_diversity = unique_words / (total_words + 1e-6)
        
        # Sentence length variation
        sentences = text_data.split('.')
        sentence_lengths = [len(sentence.split()) for sentence in sentences if sentence.strip()]
        
        if sentence_lengths:
            length_variation = np.std(sentence_lengths) / (np.mean(sentence_lengths) + 1e-6)
        else:
            length_variation = 0.0
            
        return lexical_diversity + length_variation / 10.0
        
    def _text_order(self, text_data: str) -> float:
        """Calculate text order."""
        if not isinstance(text_data, str):
            return 0.5
            
        # Structural patterns
        sentences = text_data.split('.')
        
        # Similar sentence lengths indicate order
        sentence_lengths = [len(sentence.split()) for sentence in sentences if sentence.strip()]
        
        if len(sentence_lengths) > 1:
            length_consistency = 1.0 - (np.std(sentence_lengths) / (np.mean(sentence_lengths) + 1e-6))
            return max(0.0, min(1.0, length_consistency))
        else:
            return 0.5
            
    def _detect_patterns(self, image: np.ndarray) -> float:
        """Detect regular patterns in image."""
        # Simple pattern detection using template matching
        h, w = image.shape
        
        # Check for repeating blocks
        pattern_score = 0.0
        block_sizes = [8, 16, 32]
        
        for block_size in block_sizes:
            if h >= block_size * 2 and w >= block_size * 2:
                template = image[:block_size, :block_size]
                result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
                
                # Count strong matches
                matches = np.sum(result > 0.8)
                pattern_score += matches / result.size
                
        return min(1.0, pattern_score)


class KantianAestheticJudgment:
    """Implementation of Kantian aesthetic principles."""
    
    def __init__(self):
        self.principles = {
            'disinterestedness': self._evaluate_disinterestedness,
            'universality': self._evaluate_universality,
            'purposiveness': self._evaluate_purposiveness,
            'necessity': self._evaluate_necessity
        }
        
    def evaluate(self, artwork_data: Any, modality: str, 
                context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Evaluate using Kantian aesthetic principles."""
        scores = {}
        
        for principle, evaluator in self.principles.items():
            scores[principle] = evaluator(artwork_data, modality, context)
            
        # Overall Kantian aesthetic judgment
        scores['kantian_judgment'] = np.mean(list(scores.values()))
        
        return scores
        
    def _evaluate_disinterestedness(self, artwork_data: Any, modality: str, 
                                  context: Optional[Dict[str, Any]]) -> float:
        """Evaluate aesthetic disinterestedness."""
        # Measure formal properties vs content-based properties
        if modality == "visual":
            return self._visual_disinterestedness(artwork_data)
        elif modality == "audio":
            return self._audio_disinterestedness(artwork_data)
        else:
            return 0.5
            
    def _evaluate_universality(self, artwork_data: Any, modality: str,
                             context: Optional[Dict[str, Any]]) -> float:
        """Evaluate aesthetic universality."""
        # Measure cross-cultural appeal and fundamental aesthetic properties
        return 0.7  # Placeholder - would need cultural data
        
    def _evaluate_purposiveness(self, artwork_data: Any, modality: str,
                              context: Optional[Dict[str, Any]]) -> float:
        """Evaluate purposiveness without purpose."""
        # Measure formal coherence and structure
        if modality == "visual":
            return self._visual_purposiveness(artwork_data)
        elif modality == "audio":
            return self._audio_purposiveness(artwork_data)
        else:
            return 0.5
            
    def _evaluate_necessity(self, artwork_data: Any, modality: str,
                          context: Optional[Dict[str, Any]]) -> float:
        """Evaluate aesthetic necessity."""
        # Measure inevitability of aesthetic response
        return 0.6  # Placeholder - complex to implement
        
    def _visual_disinterestedness(self, image_data: np.ndarray) -> float:
        """Evaluate visual disinterestedness."""
        # Focus on formal properties: balance, symmetry, proportion
        if len(image_data.shape) == 3:
            gray = cv2.cvtColor((image_data * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = (image_data * 255).astype(np.uint8)
            
        # Calculate formal balance
        h, w = gray.shape
        center_mass_x = np.sum(np.arange(w) * np.sum(gray, axis=0)) / np.sum(gray)
        center_mass_y = np.sum(np.arange(h) * np.sum(gray, axis=1)) / np.sum(gray)
        
        # Distance from geometric center
        geometric_center_x, geometric_center_y = w / 2, h / 2
        balance_score = 1.0 - min(1.0, np.sqrt(
            (center_mass_x - geometric_center_x) ** 2 +
            (center_mass_y - geometric_center_y) ** 2
        ) / (w + h))
        
        return balance_score
        
    def _audio_disinterestedness(self, audio_data: np.ndarray) -> float:
        """Evaluate audio disinterestedness."""
        # Focus on formal musical properties
        if len(audio_data) > 1024:
            # Spectral balance
            spectrum = np.abs(np.fft.fft(audio_data[:1024]))
            
            # Energy distribution across frequency bands
            low_energy = np.sum(spectrum[:len(spectrum)//4])
            mid_energy = np.sum(spectrum[len(spectrum)//4:3*len(spectrum)//4])
            high_energy = np.sum(spectrum[3*len(spectrum)//4:])
            
            total_energy = low_energy + mid_energy + high_energy
            
            if total_energy > 0:
                balance = 1.0 - np.std([low_energy, mid_energy, high_energy]) / (total_energy / 3)
                return max(0.0, min(1.0, balance))
                
        return 0.5
        
    def _visual_purposiveness(self, image_data: np.ndarray) -> float:
        """Evaluate visual purposiveness."""
        # Measure structural coherence
        if len(image_data.shape) == 3:
            gray = cv2.cvtColor((image_data * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = (image_data * 255).astype(np.uint8)
            
        # Edge coherence
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Measure contour regularity
            regularities = []
            for contour in contours:
                if len(contour) > 10:
                    # Approximate polygon
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    regularity = len(approx) / len(contour)
                    regularities.append(regularity)
                    
            if regularities:
                return np.mean(regularities)
                
        return 0.5
        
    def _audio_purposiveness(self, audio_data: np.ndarray) -> float:
        """Evaluate audio purposiveness."""
        # Measure musical structure and coherence
        if len(audio_data) > 2048:
            # Rhythmic coherence
            window_size = 512
            energy_windows = []
            
            for i in range(0, len(audio_data) - window_size, window_size):
                window_energy = np.sum(audio_data[i:i + window_size] ** 2)
                energy_windows.append(window_energy)
                
            if len(energy_windows) > 4:
                # Look for periodic patterns
                autocorr = np.correlate(energy_windows, energy_windows, mode='full')
                autocorr = autocorr[len(autocorr)//2:]
                
                # Find period
                max_period_corr = np.max(autocorr[1:min(len(autocorr), len(energy_windows)//2)])
                purposiveness = max_period_corr / (np.max(autocorr) + 1e-6)
                
                return min(1.0, purposiveness)
                
        return 0.5


class AestheticEvaluator:
    """Main aesthetic evaluation system combining multiple theoretical approaches."""
    
    def __init__(self):
        self.gestalt_evaluator = GestaltPrinciplesEvaluator()
        self.birkhoff_evaluator = BirkhoffAestheticMeasure()
        self.kantian_evaluator = KantianAestheticJudgment()
        
        self.evaluation_weights = {
            'gestalt': 0.4,
            'birkhoff': 0.3,
            'kantian': 0.3
        }
        
    def evaluate_comprehensive(self, artwork_data: Any, modality: str,
                             context: Optional[Dict[str, Any]] = None) -> AestheticEvaluation:
        """Perform comprehensive aesthetic evaluation."""
        
        # Gestalt evaluation
        gestalt_scores = self.gestalt_evaluator.evaluate(artwork_data, modality)
        
        # Birkhoff evaluation
        birkhoff_scores = self.birkhoff_evaluator.evaluate(artwork_data, modality)
        
        # Kantian evaluation
        kantian_scores = self.kantian_evaluator.evaluate(artwork_data, modality, context)
        
        # Combine evaluations
        dimension_scores = {}
        
        # Map to aesthetic dimensions
        dimension_scores[AestheticDimension.HARMONY] = (
            gestalt_scores.get('similarity', 0.5) * 0.5 +
            kantian_scores.get('disinterestedness', 0.5) * 0.5
        )
        
        dimension_scores[AestheticDimension.BALANCE] = (
            gestalt_scores.get('symmetry', 0.5) * 0.6 +
            kantian_scores.get('disinterestedness', 0.5) * 0.4
        )
        
        dimension_scores[AestheticDimension.PROPORTION] = gestalt_scores.get('proximity', 0.5)
        
        dimension_scores[AestheticDimension.UNITY] = (
            gestalt_scores.get('closure', 0.5) * 0.5 +
            gestalt_scores.get('continuity', 0.5) * 0.5
        )
        
        dimension_scores[AestheticDimension.COMPLEXITY] = birkhoff_scores.get('complexity', 0.5)
        
        dimension_scores[AestheticDimension.BEAUTY] = (
            birkhoff_scores.get('birkhoff_score', 0.5) * 0.5 +
            kantian_scores.get('kantian_judgment', 0.5) * 0.5
        )
        
        # Calculate overall score
        overall_score = (
            self.evaluation_weights['gestalt'] * np.mean(list(gestalt_scores.values())) +
            self.evaluation_weights['birkhoff'] * birkhoff_scores.get('birkhoff_score', 0.5) +
            self.evaluation_weights['kantian'] * kantian_scores.get('kantian_judgment', 0.5)
        )
        
        # Generate explanation
        explanation = self._generate_explanation(gestalt_scores, birkhoff_scores, kantian_scores)
        
        # Calculate confidence based on consistency
        confidence = self._calculate_confidence(gestalt_scores, birkhoff_scores, kantian_scores)
        
        return AestheticEvaluation(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            theoretical_basis={
                'gestalt': gestalt_scores,
                'birkhoff': birkhoff_scores,
                'kantian': kantian_scores
            },
            confidence=confidence,
            explanation=explanation,
            cultural_context=context.get('culture') if context else None
        )
        
    def _generate_explanation(self, gestalt_scores: Dict[str, float],
                            birkhoff_scores: Dict[str, float],
                            kantian_scores: Dict[str, float]) -> str:
        """Generate human-readable explanation of aesthetic evaluation."""
        explanations = []
        
        # Gestalt analysis
        if gestalt_scores.get('symmetry', 0) > 0.7:
            explanations.append("Strong symmetrical structure creates visual harmony")
        if gestalt_scores.get('closure', 0) > 0.7:
            explanations.append("Well-formed, complete visual elements")
        if gestalt_scores.get('continuity', 0) > 0.7:
            explanations.append("Smooth, continuous lines and forms")
            
        # Birkhoff analysis
        order_complexity_ratio = birkhoff_scores.get('order', 0.5) / (birkhoff_scores.get('complexity', 0.5) + 1e-6)
        if order_complexity_ratio > 1.5:
            explanations.append("Excellent balance between order and complexity")
        elif order_complexity_ratio < 0.5:
            explanations.append("High complexity may overwhelm structural order")
            
        # Kantian analysis
        if kantian_scores.get('disinterestedness', 0) > 0.7:
            explanations.append("Strong formal aesthetic properties")
        if kantian_scores.get('purposiveness', 0) > 0.7:
            explanations.append("Coherent structure with purposeful design")
            
        if not explanations:
            explanations.append("Moderate aesthetic qualities across multiple dimensions")
            
        return "; ".join(explanations)
        
    def _calculate_confidence(self, gestalt_scores: Dict[str, float],
                            birkhoff_scores: Dict[str, float],
                            kantian_scores: Dict[str, float]) -> float:
        """Calculate confidence based on consistency across evaluation methods."""
        
        # Extract key scores from each method
        gestalt_avg = np.mean(list(gestalt_scores.values()))
        birkhoff_aesthetic = birkhoff_scores.get('birkhoff_score', 0.5)
        kantian_avg = np.mean(list(kantian_scores.values()))
        
        scores = [gestalt_avg, birkhoff_aesthetic, kantian_avg]
        
        # Calculate consistency (inverse of standard deviation)
        consistency = 1.0 - np.std(scores)
        
        # Confidence is higher when methods agree
        confidence = max(0.0, min(1.0, consistency))
        
        return confidence