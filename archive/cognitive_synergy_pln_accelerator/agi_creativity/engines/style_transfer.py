"""
Style Transfer and Artistic Interpretation Engines

This module implements advanced style transfer and artistic interpretation capabilities,
enabling AGI to understand, analyze, and apply artistic styles across different media.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import cv2
from PIL import Image
import librosa
from scipy import signal
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE


@dataclass
class ArtisticStyle:
    """Represents an artistic style with its characteristics."""
    style_id: str
    name: str
    artist: Optional[str]
    period: Optional[str]
    characteristics: Dict[str, Any]
    style_embedding: np.ndarray
    modality: str  # visual, audio, text, etc.
    examples: List[Any] = None


@dataclass
class StyleTransferResult:
    """Result of style transfer operation."""
    transferred_artwork: Any
    style_applied: ArtisticStyle
    original_content: Any
    transfer_quality: float
    style_preservation: float
    content_preservation: float
    metadata: Dict[str, Any]


class StyleEncoder(nn.Module):
    """Neural network for encoding artistic styles."""
    
    def __init__(self, input_channels: int = 3, style_dim: int = 256):
        super().__init__()
        self.style_dim = style_dim
        
        # Convolutional layers for feature extraction
        self.features = nn.Sequential(
            # Layer 1
            nn.Conv2d(input_channels, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Layer 2
            nn.Conv2d(64, 128, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Layer 3
            nn.Conv2d(128, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Layer 4
            nn.Conv2d(256, 512, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, 3, padding=1),
            nn.ReLU(inplace=True),
        )
        
        # Style encoding layers
        self.style_encoder = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(512, 512),
            nn.ReLU(inplace=True),
            nn.Linear(512, style_dim)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.features(x)
        style_embedding = self.style_encoder(features)
        return style_embedding
        
    def extract_style_features(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        """Extract detailed style features from an image."""
        if len(image.shape) == 2:
            image = np.stack([image] * 3, axis=-1)
            
        # Convert to tensor
        image_tensor = torch.tensor(image.transpose(2, 0, 1), dtype=torch.float32).unsqueeze(0) / 255.0
        
        with torch.no_grad():
            # Get intermediate features
            features = {}
            x = image_tensor
            
            for i, layer in enumerate(self.features):
                x = layer(x)
                if isinstance(layer, nn.MaxPool2d):
                    features[f'layer_{i//3 + 1}'] = x.squeeze(0).numpy()
                    
            # Get final style embedding
            style_embedding = self.style_encoder(self.features(image_tensor))
            features['style_embedding'] = style_embedding.squeeze(0).numpy()
            
        return features


class VisualStyleTransfer:
    """Implements visual style transfer using neural style transfer techniques."""
    
    def __init__(self):
        self.style_encoder = StyleEncoder()
        self.style_database = {}
        
    def analyze_style(self, artwork: np.ndarray, style_name: str) -> ArtisticStyle:
        """Analyze and extract style characteristics from artwork."""
        
        # Extract visual features
        style_features = self.style_encoder.extract_style_features(artwork)
        
        # Analyze color palette
        color_analysis = self._analyze_color_palette(artwork)
        
        # Analyze texture and patterns
        texture_analysis = self._analyze_texture(artwork)
        
        # Analyze composition
        composition_analysis = self._analyze_composition(artwork)
        
        # Analyze brushstrokes/mark-making
        brushstroke_analysis = self._analyze_brushstrokes(artwork)
        
        characteristics = {
            'color_palette': color_analysis,
            'texture': texture_analysis,
            'composition': composition_analysis,
            'brushstrokes': brushstroke_analysis,
            'visual_features': style_features
        }
        
        style = ArtisticStyle(
            style_id=f"style_{len(self.style_database)}",
            name=style_name,
            artist=None,
            period=None,
            characteristics=characteristics,
            style_embedding=style_features['style_embedding'],
            modality='visual'
        )
        
        self.style_database[style.style_id] = style
        return style
        
    def transfer_style(self, content_image: np.ndarray, 
                      style: ArtisticStyle,
                      strength: float = 1.0) -> StyleTransferResult:
        """Transfer style to content image."""
        
        # Neural style transfer implementation
        transferred_image = self._neural_style_transfer(content_image, style, strength)
        
        # Evaluate transfer quality
        quality_metrics = self._evaluate_transfer_quality(content_image, transferred_image, style)
        
        return StyleTransferResult(
            transferred_artwork=transferred_image,
            style_applied=style,
            original_content=content_image,
            transfer_quality=quality_metrics['overall_quality'],
            style_preservation=quality_metrics['style_preservation'],
            content_preservation=quality_metrics['content_preservation'],
            metadata={'transfer_strength': strength, 'method': 'neural_style_transfer'}
        )
        
    def _analyze_color_palette(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze color palette of artwork."""
        if len(image.shape) == 2:
            return {'type': 'grayscale', 'dominant_colors': [128]}
            
        # Reshape image for clustering
        pixels = image.reshape(-1, 3)
        
        # Find dominant colors using K-means
        n_colors = min(8, len(np.unique(pixels, axis=0)))
        if n_colors > 1:
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            dominant_colors = kmeans.cluster_centers_.astype(int).tolist()
        else:
            dominant_colors = [np.mean(pixels, axis=0).astype(int).tolist()]
            
        # Analyze color temperature
        avg_color = np.mean(pixels, axis=0)
        color_temperature = 'warm' if avg_color[0] > avg_color[2] else 'cool'
        
        # Analyze saturation
        hsv = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2HSV)
        avg_saturation = np.mean(hsv[:, :, 1]) / 255.0
        
        return {
            'dominant_colors': dominant_colors,
            'color_temperature': color_temperature,
            'saturation_level': avg_saturation,
            'num_distinct_colors': n_colors
        }
        
    def _analyze_texture(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze texture characteristics."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = image.astype(np.uint8)
            
        # Calculate texture metrics using Gray Level Co-occurrence Matrix
        glcm = self._compute_glcm(gray)
        
        contrast = self._glcm_contrast(glcm)
        homogeneity = self._glcm_homogeneity(glcm)
        energy = self._glcm_energy(glcm)
        
        # Edge density for roughness
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        return {
            'contrast': contrast,
            'homogeneity': homogeneity,
            'energy': energy,
            'roughness': edge_density,
            'texture_type': self._classify_texture(contrast, homogeneity, edge_density)
        }
        
    def _analyze_composition(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze compositional elements."""
        h, w = image.shape[:2]
        
        # Rule of thirds analysis
        thirds_h = h // 3
        thirds_w = w // 3
        
        # Calculate visual weight in different regions
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = image.astype(np.uint8)
            
        # Divide into 9 regions
        regions = []
        for i in range(3):
            for j in range(3):
                region = gray[i*thirds_h:(i+1)*thirds_h, j*thirds_w:(j+1)*thirds_w]
                weight = np.std(region)  # Visual activity
                regions.append(weight)
                
        # Find focal points
        focal_regions = np.argsort(regions)[-3:]  # Top 3 active regions
        
        # Symmetry analysis
        left_half = gray[:, :w//2]
        right_half = np.fliplr(gray[:, w//2:])
        if left_half.shape == right_half.shape:
            horizontal_symmetry = 1.0 - np.mean(np.abs(left_half.astype(float) - right_half.astype(float))) / 255.0
        else:
            horizontal_symmetry = 0.0
            
        return {
            'focal_regions': focal_regions.tolist(),
            'visual_weights': regions,
            'horizontal_symmetry': horizontal_symmetry,
            'composition_type': self._classify_composition(regions, horizontal_symmetry)
        }
        
    def _analyze_brushstrokes(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze brushstroke patterns and mark-making."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = image.astype(np.uint8)
            
        # Edge analysis for stroke direction
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        
        # Calculate dominant stroke direction
        angles = np.arctan2(sobely, sobelx)
        hist, bins = np.histogram(angles, bins=8, range=(-np.pi, np.pi))
        dominant_direction = bins[np.argmax(hist)]
        
        # Stroke length estimation
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            stroke_lengths = [cv2.arcLength(contour, False) for contour in contours]
            avg_stroke_length = np.mean(stroke_lengths)
            stroke_variation = np.std(stroke_lengths)
        else:
            avg_stroke_length = 0
            stroke_variation = 0
            
        return {
            'dominant_direction': dominant_direction,
            'average_stroke_length': avg_stroke_length,
            'stroke_variation': stroke_variation,
            'stroke_density': len(contours) / (gray.shape[0] * gray.shape[1]),
            'mark_making_style': self._classify_mark_making(avg_stroke_length, stroke_variation)
        }
        
    def _neural_style_transfer(self, content: np.ndarray, 
                              style: ArtisticStyle, 
                              strength: float) -> np.ndarray:
        """Perform neural style transfer."""
        # Simplified style transfer implementation
        # In a full implementation, this would use pre-trained VGG networks
        
        style_characteristics = style.characteristics
        
        # Apply color palette transfer
        transferred = self._transfer_color_palette(content, style_characteristics['color_palette'])
        
        # Apply texture transfer
        transferred = self._transfer_texture(transferred, style_characteristics['texture'], strength)
        
        # Apply composition adjustments
        transferred = self._adjust_composition(transferred, style_characteristics['composition'], strength)
        
        return transferred
        
    def _transfer_color_palette(self, image: np.ndarray, 
                               palette_info: Dict[str, Any]) -> np.ndarray:
        """Transfer color palette to image."""
        if len(image.shape) == 2:
            return image
            
        dominant_colors = np.array(palette_info['dominant_colors'])
        
        # Reshape image
        original_shape = image.shape
        pixels = image.reshape(-1, 3)
        
        # Map each pixel to nearest palette color
        transferred_pixels = np.zeros_like(pixels)
        
        for i, pixel in enumerate(pixels):
            distances = np.sum((dominant_colors - pixel) ** 2, axis=1)
            closest_color_idx = np.argmin(distances)
            # Blend original and palette color
            transferred_pixels[i] = 0.7 * dominant_colors[closest_color_idx] + 0.3 * pixel
            
        return transferred_pixels.reshape(original_shape)
        
    def _transfer_texture(self, image: np.ndarray, 
                         texture_info: Dict[str, Any], 
                         strength: float) -> np.ndarray:
        """Transfer texture characteristics."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = image.astype(np.uint8)
            
        target_contrast = texture_info['contrast']
        target_roughness = texture_info['roughness']
        
        # Adjust contrast
        current_contrast = np.std(gray)
        if current_contrast > 0:
            contrast_factor = target_contrast / current_contrast
            gray_adjusted = gray.astype(float)
            gray_adjusted = (gray_adjusted - np.mean(gray_adjusted)) * contrast_factor + np.mean(gray_adjusted)
            gray_adjusted = np.clip(gray_adjusted, 0, 255).astype(np.uint8)
        else:
            gray_adjusted = gray
            
        # Add texture noise based on roughness
        if target_roughness > 0.1:
            noise = np.random.normal(0, target_roughness * 10, gray_adjusted.shape)
            gray_adjusted = gray_adjusted.astype(float) + noise * strength
            gray_adjusted = np.clip(gray_adjusted, 0, 255).astype(np.uint8)
            
        # Convert back to color if needed
        if len(image.shape) == 3:
            # Maintain color ratios
            result = image.copy().astype(float)
            for c in range(3):
                if np.std(image[:, :, c]) > 0:
                    result[:, :, c] = (result[:, :, c] / np.mean(image[:, :, c])) * np.mean(gray_adjusted)
            return np.clip(result, 0, 255).astype(np.uint8)
        else:
            return gray_adjusted
            
    def _adjust_composition(self, image: np.ndarray, 
                           composition_info: Dict[str, Any], 
                           strength: float) -> np.ndarray:
        """Adjust composition based on style."""
        # Simple composition adjustment - enhance focal regions
        focal_regions = composition_info['focal_regions']
        
        if len(focal_regions) > 0 and strength > 0.1:
            h, w = image.shape[:2]
            thirds_h, thirds_w = h // 3, w // 3
            
            enhanced = image.copy().astype(float)
            
            for region_idx in focal_regions:
                i, j = region_idx // 3, region_idx % 3
                region_slice = (slice(i*thirds_h, (i+1)*thirds_h), 
                               slice(j*thirds_w, (j+1)*thirds_w))
                
                # Enhance contrast in focal regions
                region = enhanced[region_slice]
                region_mean = np.mean(region)
                enhanced[region_slice] = (region - region_mean) * (1 + strength * 0.3) + region_mean
                
            return np.clip(enhanced, 0, 255).astype(np.uint8)
        
        return image
        
    def _evaluate_transfer_quality(self, original: np.ndarray, 
                                  transferred: np.ndarray, 
                                  style: ArtisticStyle) -> Dict[str, float]:
        """Evaluate quality of style transfer."""
        # Content preservation - structural similarity
        if len(original.shape) == 3:
            orig_gray = cv2.cvtColor(original.astype(np.uint8), cv2.COLOR_RGB2GRAY)
            trans_gray = cv2.cvtColor(transferred.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            orig_gray = original.astype(np.uint8)
            trans_gray = transferred.astype(np.uint8)
            
        # Simple structural similarity
        content_preservation = 1.0 - np.mean(np.abs(orig_gray.astype(float) - trans_gray.astype(float))) / 255.0
        
        # Style preservation - compare with style characteristics
        transferred_style = self.analyze_style(transferred, "transferred_temp")
        style_preservation = self._compare_styles(style, transferred_style)
        
        overall_quality = (content_preservation + style_preservation) / 2
        
        return {
            'content_preservation': content_preservation,
            'style_preservation': style_preservation,
            'overall_quality': overall_quality
        }
        
    def _compare_styles(self, style1: ArtisticStyle, style2: ArtisticStyle) -> float:
        """Compare similarity between two styles."""
        # Compare embeddings
        embedding_similarity = np.dot(style1.style_embedding, style2.style_embedding) / (
            np.linalg.norm(style1.style_embedding) * np.linalg.norm(style2.style_embedding)
        )
        
        # Compare color palettes
        colors1 = style1.characteristics['color_palette']['dominant_colors']
        colors2 = style2.characteristics['color_palette']['dominant_colors']
        
        color_similarity = 0.0
        if colors1 and colors2:
            # Simple color comparison
            colors1_arr = np.array(colors1)
            colors2_arr = np.array(colors2)
            
            min_len = min(len(colors1_arr), len(colors2_arr))
            if min_len > 0:
                color_distances = np.linalg.norm(colors1_arr[:min_len] - colors2_arr[:min_len], axis=1)
                color_similarity = 1.0 - np.mean(color_distances) / 441.67  # Max RGB distance
                
        return (embedding_similarity + color_similarity) / 2
        
    def _compute_glcm(self, image: np.ndarray, distance: int = 1) -> np.ndarray:
        """Compute Gray-Level Co-occurrence Matrix."""
        max_val = 256
        glcm = np.zeros((max_val, max_val))
        
        rows, cols = image.shape
        
        for i in range(rows - distance):
            for j in range(cols - distance):
                pixel1 = int(image[i, j])
                pixel2 = int(image[i + distance, j])
                glcm[pixel1, pixel2] += 1
                
        # Normalize
        if np.sum(glcm) > 0:
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
        
    def _glcm_energy(self, glcm: np.ndarray) -> float:
        """Calculate energy from GLCM."""
        return np.sum(glcm ** 2)
        
    def _classify_texture(self, contrast: float, homogeneity: float, edge_density: float) -> str:
        """Classify texture type."""
        if contrast > 0.5 and edge_density > 0.1:
            return "rough"
        elif homogeneity > 0.8:
            return "smooth"
        elif contrast > 0.3:
            return "textured"
        else:
            return "uniform"
            
    def _classify_composition(self, visual_weights: List[float], symmetry: float) -> str:
        """Classify composition type."""
        max_weight_idx = np.argmax(visual_weights)
        
        if symmetry > 0.8:
            return "symmetrical"
        elif max_weight_idx == 4:  # Center region
            return "central"
        elif max_weight_idx in [2, 5, 8]:  # Right side
            return "right_weighted"
        elif max_weight_idx in [0, 3, 6]:  # Left side
            return "left_weighted"
        else:
            return "balanced"
            
    def _classify_mark_making(self, avg_length: float, variation: float) -> str:
        """Classify mark-making style."""
        if avg_length > 50 and variation < 20:
            return "smooth_flowing"
        elif avg_length < 20:
            return "short_choppy"
        elif variation > 30:
            return "varied_expressive"
        else:
            return "controlled_consistent"


class AudioStyleTransfer:
    """Implements audio style transfer for musical and sonic art."""
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.style_database = {}
        
    def analyze_audio_style(self, audio: np.ndarray, style_name: str) -> ArtisticStyle:
        """Analyze and extract style characteristics from audio."""
        
        # Spectral analysis
        spectral_features = self._analyze_spectral_features(audio)
        
        # Rhythmic analysis
        rhythmic_features = self._analyze_rhythm(audio)
        
        # Harmonic analysis
        harmonic_features = self._analyze_harmony(audio)
        
        # Temporal dynamics
        dynamic_features = self._analyze_dynamics(audio)
        
        characteristics = {
            'spectral': spectral_features,
            'rhythmic': rhythmic_features,
            'harmonic': harmonic_features,
            'dynamic': dynamic_features
        }
        
        # Create style embedding
        style_embedding = self._create_audio_style_embedding(characteristics)
        
        style = ArtisticStyle(
            style_id=f"audio_style_{len(self.style_database)}",
            name=style_name,
            artist=None,
            period=None,
            characteristics=characteristics,
            style_embedding=style_embedding,
            modality='audio'
        )
        
        self.style_database[style.style_id] = style
        return style
        
    def transfer_audio_style(self, content_audio: np.ndarray, 
                           style: ArtisticStyle,
                           strength: float = 1.0) -> StyleTransferResult:
        """Transfer audio style to content."""
        
        # Apply spectral style transfer
        transferred = self._transfer_spectral_characteristics(content_audio, style, strength)
        
        # Apply rhythmic style transfer
        transferred = self._transfer_rhythmic_characteristics(transferred, style, strength)
        
        # Apply dynamic style transfer
        transferred = self._transfer_dynamic_characteristics(transferred, style, strength)
        
        # Evaluate transfer quality
        quality_metrics = self._evaluate_audio_transfer_quality(content_audio, transferred, style)
        
        return StyleTransferResult(
            transferred_artwork=transferred,
            style_applied=style,
            original_content=content_audio,
            transfer_quality=quality_metrics['overall_quality'],
            style_preservation=quality_metrics['style_preservation'],
            content_preservation=quality_metrics['content_preservation'],
            metadata={'transfer_strength': strength, 'method': 'spectral_style_transfer'}
        )
        
    def _analyze_spectral_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Analyze spectral characteristics of audio."""
        # Compute spectrogram
        f, t, Sxx = signal.spectrogram(audio, fs=self.sample_rate, nperseg=1024)
        
        # Spectral centroid
        spectral_centroid = np.sum(f[:, np.newaxis] * Sxx, axis=0) / (np.sum(Sxx, axis=0) + 1e-10)
        
        # Spectral rolloff
        spectral_rolloff = []
        for i in range(Sxx.shape[1]):
            cumulative_energy = np.cumsum(Sxx[:, i])
            total_energy = cumulative_energy[-1]
            rolloff_idx = np.where(cumulative_energy >= 0.85 * total_energy)[0]
            if len(rolloff_idx) > 0:
                spectral_rolloff.append(f[rolloff_idx[0]])
            else:
                spectral_rolloff.append(f[-1])
                
        # Spectral bandwidth
        spectral_bandwidth = np.sqrt(np.sum(((f[:, np.newaxis] - spectral_centroid) ** 2) * Sxx, axis=0) / 
                                   (np.sum(Sxx, axis=0) + 1e-10))
        
        return {
            'centroid_mean': np.mean(spectral_centroid),
            'centroid_std': np.std(spectral_centroid),
            'rolloff_mean': np.mean(spectral_rolloff),
            'bandwidth_mean': np.mean(spectral_bandwidth),
            'spectral_energy_distribution': np.mean(Sxx, axis=1)
        }
        
    def _analyze_rhythm(self, audio: np.ndarray) -> Dict[str, Any]:
        """Analyze rhythmic characteristics."""
        # Simple beat tracking using onset detection
        onset_frames = self._detect_onsets(audio)
        
        if len(onset_frames) > 1:
            # Calculate inter-onset intervals
            intervals = np.diff(onset_frames) / self.sample_rate
            
            # Estimate tempo
            if len(intervals) > 0:
                mean_interval = np.mean(intervals)
                tempo = 60.0 / mean_interval if mean_interval > 0 else 120.0
            else:
                tempo = 120.0
                
            # Rhythmic regularity
            regularity = 1.0 - (np.std(intervals) / (np.mean(intervals) + 1e-10)) if len(intervals) > 0 else 0.0
        else:
            tempo = 120.0
            regularity = 0.0
            intervals = []
            
        return {
            'tempo': tempo,
            'regularity': regularity,
            'onset_density': len(onset_frames) / (len(audio) / self.sample_rate),
            'rhythmic_complexity': np.std(intervals) if len(intervals) > 0 else 0.0
        }
        
    def _analyze_harmony(self, audio: np.ndarray) -> Dict[str, Any]:
        """Analyze harmonic content."""
        # Chromagram for harmonic analysis
        if len(audio) >= 2048:
            # Simple harmonic analysis using FFT
            fft = np.fft.fft(audio[:2048])
            magnitude = np.abs(fft[:1024])
            
            # Find peaks (harmonics)
            peaks = []
            for i in range(1, len(magnitude) - 1):
                if magnitude[i] > magnitude[i-1] and magnitude[i] > magnitude[i+1]:
                    peaks.append(i)
                    
            # Harmonic to noise ratio
            if peaks:
                harmonic_energy = np.sum([magnitude[p] for p in peaks])
                total_energy = np.sum(magnitude)
                harmonicity = harmonic_energy / (total_energy + 1e-10)
            else:
                harmonicity = 0.0
                
            # Spectral flatness (measure of noisiness)
            geometric_mean = np.exp(np.mean(np.log(magnitude + 1e-10)))
            arithmetic_mean = np.mean(magnitude)
            spectral_flatness = geometric_mean / (arithmetic_mean + 1e-10)
            
        else:
            harmonicity = 0.0
            spectral_flatness = 0.0
            peaks = []
            
        return {
            'harmonicity': harmonicity,
            'spectral_flatness': spectral_flatness,
            'num_harmonics': len(peaks),
            'harmonic_richness': len(peaks) / 10.0  # Normalized
        }
        
    def _analyze_dynamics(self, audio: np.ndarray) -> Dict[str, Any]:
        """Analyze dynamic characteristics."""
        # RMS energy over time
        window_size = self.sample_rate // 10  # 100ms windows
        rms_values = []
        
        for i in range(0, len(audio) - window_size, window_size // 2):
            window = audio[i:i + window_size]
            rms = np.sqrt(np.mean(window ** 2))
            rms_values.append(rms)
            
        rms_values = np.array(rms_values)
        
        # Dynamic range
        dynamic_range = np.max(rms_values) - np.min(rms_values) if len(rms_values) > 0 else 0.0
        
        # Dynamic variability
        dynamic_variability = np.std(rms_values) if len(rms_values) > 0 else 0.0
        
        # Attack characteristics
        attack_times = self._analyze_attack_times(audio)
        
        return {
            'dynamic_range': dynamic_range,
            'dynamic_variability': dynamic_variability,
            'average_level': np.mean(rms_values) if len(rms_values) > 0 else 0.0,
            'attack_sharpness': np.mean(attack_times) if attack_times else 0.0
        }
        
    def _create_audio_style_embedding(self, characteristics: Dict[str, Any]) -> np.ndarray:
        """Create style embedding from audio characteristics."""
        embedding = []
        
        # Spectral features
        spectral = characteristics['spectral']
        embedding.extend([
            spectral['centroid_mean'] / 1000.0,  # Normalize
            spectral['centroid_std'] / 1000.0,
            spectral['rolloff_mean'] / 1000.0,
            spectral['bandwidth_mean'] / 1000.0
        ])
        
        # Rhythmic features
        rhythmic = characteristics['rhythmic']
        embedding.extend([
            rhythmic['tempo'] / 200.0,  # Normalize
            rhythmic['regularity'],
            rhythmic['onset_density'],
            rhythmic['rhythmic_complexity']
        ])
        
        # Harmonic features
        harmonic = characteristics['harmonic']
        embedding.extend([
            harmonic['harmonicity'],
            harmonic['spectral_flatness'],
            harmonic['harmonic_richness']
        ])
        
        # Dynamic features
        dynamic = characteristics['dynamic']
        embedding.extend([
            dynamic['dynamic_range'],
            dynamic['dynamic_variability'],
            dynamic['average_level'],
            dynamic['attack_sharpness']
        ])
        
        # Pad to consistent size
        while len(embedding) < 64:
            embedding.append(0.0)
            
        return np.array(embedding[:64])
        
    def _detect_onsets(self, audio: np.ndarray) -> np.ndarray:
        """Simple onset detection."""
        # Energy-based onset detection
        window_size = 1024
        hop_size = 512
        
        onset_frames = []
        energy_prev = 0
        
        for i in range(0, len(audio) - window_size, hop_size):
            window = audio[i:i + window_size]
            energy = np.sum(window ** 2)
            
            # Simple threshold-based detection
            if energy > energy_prev * 1.5 and energy > 0.01:
                onset_frames.append(i)
                
            energy_prev = energy
            
        return np.array(onset_frames)
        
    def _analyze_attack_times(self, audio: np.ndarray) -> List[float]:
        """Analyze attack characteristics of sounds."""
        onset_frames = self._detect_onsets(audio)
        attack_times = []
        
        for onset in onset_frames:
            # Analyze the attack portion (first 50ms after onset)
            attack_window_size = min(self.sample_rate // 20, len(audio) - onset)
            if attack_window_size > 0:
                attack_portion = audio[onset:onset + attack_window_size]
                
                # Find peak
                peak_idx = np.argmax(np.abs(attack_portion))
                attack_time = peak_idx / self.sample_rate  # Convert to seconds
                attack_times.append(attack_time)
                
        return attack_times
        
    def _transfer_spectral_characteristics(self, audio: np.ndarray, 
                                         style: ArtisticStyle, 
                                         strength: float) -> np.ndarray:
        """Transfer spectral characteristics."""
        target_spectral = style.characteristics['spectral']
        
        # Apply spectral filtering to match target characteristics
        # Simple implementation using filtering
        
        # Compute current spectral centroid
        f, t, Sxx = signal.spectrogram(audio, fs=self.sample_rate, nperseg=1024)
        current_centroid = np.sum(f[:, np.newaxis] * Sxx, axis=0) / (np.sum(Sxx, axis=0) + 1e-10)
        
        target_centroid = target_spectral['centroid_mean']
        current_centroid_mean = np.mean(current_centroid)
        
        # Apply filtering to shift spectral centroid
        if current_centroid_mean > 0:
            shift_factor = target_centroid / current_centroid_mean
            
            # Simple spectral shifting using resampling
            if 0.5 < shift_factor < 2.0:  # Reasonable range
                from scipy.signal import resample
                shifted_length = int(len(audio) / shift_factor)
                shifted_audio = resample(audio, shifted_length)
                
                # Pad or truncate to original length
                if len(shifted_audio) > len(audio):
                    shifted_audio = shifted_audio[:len(audio)]
                else:
                    padded = np.zeros(len(audio))
                    padded[:len(shifted_audio)] = shifted_audio
                    shifted_audio = padded
                    
                # Blend with original based on strength
                return (1 - strength) * audio + strength * shifted_audio
                
        return audio
        
    def _transfer_rhythmic_characteristics(self, audio: np.ndarray, 
                                         style: ArtisticStyle, 
                                         strength: float) -> np.ndarray:
        """Transfer rhythmic characteristics."""
        # This is a simplified implementation
        # In practice, this would involve complex rhythm modification
        
        target_rhythmic = style.characteristics['rhythmic']
        target_regularity = target_rhythmic['regularity']
        
        # Simple rhythm regularization
        if target_regularity > 0.7 and strength > 0.5:
            # Apply some temporal smoothing for regularity
            window_size = self.sample_rate // 10  # 100ms
            smoothed = np.convolve(audio, np.ones(window_size)/window_size, mode='same')
            return (1 - strength) * audio + strength * smoothed
            
        return audio
        
    def _transfer_dynamic_characteristics(self, audio: np.ndarray, 
                                        style: ArtisticStyle, 
                                        strength: float) -> np.ndarray:
        """Transfer dynamic characteristics."""
        target_dynamic = style.characteristics['dynamic']
        target_range = target_dynamic['dynamic_range']
        
        # Adjust dynamic range
        current_max = np.max(np.abs(audio))
        if current_max > 0:
            current_range = current_max - np.min(np.abs(audio))
            
            if current_range > 0:
                range_factor = target_range / current_range
                
                # Apply dynamic range adjustment
                adjusted = audio * range_factor * strength + audio * (1 - strength)
                return np.clip(adjusted, -1.0, 1.0)
                
        return audio
        
    def _evaluate_audio_transfer_quality(self, original: np.ndarray, 
                                       transferred: np.ndarray, 
                                       style: ArtisticStyle) -> Dict[str, float]:
        """Evaluate quality of audio style transfer."""
        # Content preservation - spectral similarity
        orig_spec = np.abs(np.fft.fft(original[:min(2048, len(original))]))
        trans_spec = np.abs(np.fft.fft(transferred[:min(2048, len(transferred))]))
        
        min_len = min(len(orig_spec), len(trans_spec))
        if min_len > 0:
            spectral_similarity = np.corrcoef(orig_spec[:min_len], trans_spec[:min_len])[0, 1]
            if np.isnan(spectral_similarity):
                spectral_similarity = 0.0
        else:
            spectral_similarity = 0.0
            
        # Style preservation - compare characteristics
        transferred_style = self.analyze_audio_style(transferred, "temp")
        style_similarity = self._compare_audio_styles(style, transferred_style)
        
        return {
            'content_preservation': max(0.0, spectral_similarity),
            'style_preservation': style_similarity,
            'overall_quality': (max(0.0, spectral_similarity) + style_similarity) / 2
        }
        
    def _compare_audio_styles(self, style1: ArtisticStyle, style2: ArtisticStyle) -> float:
        """Compare similarity between audio styles."""
        # Compare style embeddings
        embedding_similarity = np.dot(style1.style_embedding, style2.style_embedding) / (
            np.linalg.norm(style1.style_embedding) * np.linalg.norm(style2.style_embedding) + 1e-10
        )
        
        return max(0.0, min(1.0, embedding_similarity))


class StyleTransferEngine:
    """Main style transfer engine supporting multiple modalities."""
    
    def __init__(self):
        self.visual_transfer = VisualStyleTransfer()
        self.audio_transfer = AudioStyleTransfer()
        self.supported_modalities = ['visual', 'audio']
        
    def analyze_style(self, artwork: Any, style_name: str, modality: str) -> ArtisticStyle:
        """Analyze style from artwork in specified modality."""
        if modality == 'visual':
            return self.visual_transfer.analyze_style(artwork, style_name)
        elif modality == 'audio':
            return self.audio_transfer.analyze_audio_style(artwork, style_name)
        else:
            raise ValueError(f"Modality {modality} not supported")
            
    def transfer_style(self, content: Any, style: ArtisticStyle, 
                      strength: float = 1.0) -> StyleTransferResult:
        """Transfer style to content."""
        if style.modality == 'visual':
            return self.visual_transfer.transfer_style(content, style, strength)
        elif style.modality == 'audio':
            return self.audio_transfer.transfer_audio_style(content, style, strength)
        else:
            raise ValueError(f"Modality {style.modality} not supported")
            
    def get_style_database(self) -> Dict[str, List[ArtisticStyle]]:
        """Get all analyzed styles by modality."""
        return {
            'visual': list(self.visual_transfer.style_database.values()),
            'audio': list(self.audio_transfer.style_database.values())
        }
        
    def recommend_styles(self, content: Any, modality: str, 
                        n_recommendations: int = 5) -> List[ArtisticStyle]:
        """Recommend styles that would work well with given content."""
        if modality == 'visual':
            styles = list(self.visual_transfer.style_database.values())
        elif modality == 'audio':
            styles = list(self.audio_transfer.style_database.values())
        else:
            return []
            
        if not styles:
            return []
            
        # Simple recommendation based on style diversity
        # In a full implementation, this would use content analysis
        recommendations = styles[:n_recommendations]
        
        return recommendations