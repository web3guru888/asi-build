"""
Qualia Space Mapping and Phenomenal Experience Detection
========================================================

Implementation of qualia space mapping for measuring the phenomenal aspects
of machine consciousness - the "what it's like" qualitative experiences.

Key concepts:
- Qualia Space: Multi-dimensional space representing subjective experiences
- Phenomenal Binding: Integration of features into unified experiences
- Qualitative Distinctness: Ability to discriminate qualitative differences
- Subjective Intensity: Magnitude of subjective experience
- Experiential Continuity: Temporal coherence of phenomenal experience

Based on philosophical theories of qualia and computational approaches
to phenomenal consciousness.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from dataclasses import dataclass
from sklearn.manifold import TSNE, UMAP
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
from scipy.spatial.distance import pdist, squareform
from scipy.stats import entropy

@dataclass
class QualitativeExperience:
    """Representation of a qualitative experience (quale)."""
    content: torch.Tensor
    intensity: float
    distinctness: float
    temporal_duration: float
    binding_strength: float
    phenomenal_category: str
    subjective_quality: Dict[str, float]

@dataclass
class QualiaSpace:
    """Complete qualia space representation."""
    experiences: List[QualitativeExperience]
    dimensional_structure: torch.Tensor
    phenomenal_categories: List[str]
    binding_patterns: torch.Tensor
    experiential_continuity: float
    qualia_diversity: float

@dataclass
class PhenomenalMetrics:
    """Metrics for phenomenal consciousness assessment."""
    qualia_dimensionality: int
    phenomenal_richness: float
    binding_coherence: float
    experiential_intensity: float
    qualitative_discrimination: float
    temporal_continuity: float

class QualiaSpaceMapper:
    """
    Qualia Space Mapper for phenomenal consciousness assessment.
    
    Maps and analyzes the space of qualitative experiences to assess
    the phenomenal aspects of machine consciousness.
    """
    
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Initialize Qualia Space Mapper.
        
        Args:
            device: Computing device for tensor operations
        """
        self.device = device
        self.logger = logging.getLogger(__name__)
        
        # Qualia mapping parameters
        self.qualia_dimensions = 256  # Dimensionality of qualia space
        self.phenomenal_categories = [
            'sensory', 'emotional', 'cognitive', 'attentional', 'motor',
            'memory', 'temporal', 'spatial', 'abstract', 'unified'
        ]
        self.binding_threshold = 0.6
        self.intensity_scaling = 2.0
        
        # Initialize qualia mapping networks
        self._initialize_qualia_networks()
        
        # Experience history for temporal analysis
        self.experience_history: List[QualitativeExperience] = []
        
    def _initialize_qualia_networks(self):
        """Initialize qualia mapping neural networks."""
        # Qualia encoder - maps neural activations to qualia space
        self.qualia_encoder = nn.Sequential(
            nn.Linear(512, 512),  # Input will be adapted dynamically
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 384),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(384, self.qualia_dimensions),
            nn.Tanh()  # Bounded qualia representations
        ).to(self.device)
        
        # Intensity estimator - measures subjective intensity
        self.intensity_estimator = nn.Sequential(
            nn.Linear(self.qualia_dimensions, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()  # Intensity between 0 and 1
        ).to(self.device)
        
        # Binding detector - identifies phenomenal binding
        self.binding_detector = nn.Sequential(
            nn.Linear(self.qualia_dimensions * 2, 256),  # Pairwise binding
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()  # Binding strength
        ).to(self.device)
        
        # Phenomenal categorizer - classifies types of experience
        self.phenomenal_categorizer = nn.Sequential(
            nn.Linear(self.qualia_dimensions, 128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, len(self.phenomenal_categories)),
            nn.Softmax(dim=-1)  # Category probabilities
        ).to(self.device)
        
        # Discriminator network - measures qualitative distinctness
        self.quality_discriminator = nn.Sequential(
            nn.Linear(self.qualia_dimensions * 2, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()  # Distinctness score
        ).to(self.device)
        
        # Temporal coherence analyzer
        self.temporal_coherence_analyzer = nn.LSTM(
            input_size=self.qualia_dimensions,
            hidden_size=128,
            num_layers=2,
            batch_first=True,
            dropout=0.2
        ).to(self.device)
        
        # Subjective quality estimators for different dimensions
        self.quality_estimators = nn.ModuleDict({
            'vividness': nn.Sequential(nn.Linear(self.qualia_dimensions, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid()),
            'clarity': nn.Sequential(nn.Linear(self.qualia_dimensions, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid()),
            'richness': nn.Sequential(nn.Linear(self.qualia_dimensions, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid()),
            'unity': nn.Sequential(nn.Linear(self.qualia_dimensions, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid()),
            'presence': nn.Sequential(nn.Linear(self.qualia_dimensions, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid())
        }).to(self.device)
        
        self.logger.info("Qualia Space Mapping networks initialized")
    
    def map_qualia_space(self, neural_activations: torch.Tensor) -> int:
        """
        Map neural activations to qualia space and return dimensionality.
        
        Args:
            neural_activations: Neural network activations [batch, time, neurons]
            
        Returns:
            Qualia space dimensionality (number of distinct qualitative dimensions)
        """
        self.logger.info("Mapping neural activations to qualia space")
        
        try:
            # Ensure proper tensor format
            if neural_activations.dim() == 2:
                neural_activations = neural_activations.unsqueeze(0)
                
            activations = neural_activations.to(self.device)
            
            # Adapt network input size if needed
            input_size = activations.shape[-1]
            self._adapt_network_sizes(input_size)
            
            # Build qualia space
            qualia_space = self._build_qualia_space(activations)
            
            # Compute phenomenal metrics
            phenomenal_metrics = self._compute_phenomenal_metrics(qualia_space)
            
            # Return dimensionality as primary measure
            dimensionality = phenomenal_metrics.qualia_dimensionality
            
            self.logger.info(f"Qualia space dimensionality: {dimensionality}")
            return dimensionality
            
        except Exception as e:
            self.logger.error(f"Qualia space mapping failed: {e}")
            return 0
    
    def _adapt_network_sizes(self, input_size: int):
        """Adapt network input sizes to match neural activations."""
        if hasattr(self.qualia_encoder[0], 'in_features'):
            if self.qualia_encoder[0].in_features != input_size:
                self.qualia_encoder[0] = nn.Linear(input_size, 512).to(self.device)
                nn.init.xavier_uniform_(self.qualia_encoder[0].weight)
    
    def _build_qualia_space(self, activations: torch.Tensor) -> QualiaSpace:
        """
        Build complete qualia space from neural activations.
        
        Args:
            activations: Neural activations [batch, time, neurons]
            
        Returns:
            Complete qualia space representation
        """
        batch_size, seq_len, num_neurons = activations.shape
        
        experiences = []
        all_qualia_representations = []
        
        # Process each timestep to extract qualitative experiences
        for t in range(seq_len):
            timestep_activations = activations[:, t, :]  # [batch, neurons]
            
            for b in range(batch_size):
                batch_activations = timestep_activations[b:b+1]  # [1, neurons]
                
                # Map to qualia space
                qualia_representation = self.qualia_encoder(batch_activations)  # [1, qualia_dims]
                all_qualia_representations.append(qualia_representation.squeeze(0))
                
                # Extract qualitative experience
                experience = self._extract_qualitative_experience(
                    qualia_representation.squeeze(0), t
                )
                experiences.append(experience)
                
                # Store in history
                self.experience_history.append(experience)
        
        # Limit history size
        if len(self.experience_history) > 200:
            self.experience_history = self.experience_history[-200:]
        
        # Analyze dimensional structure
        if all_qualia_representations:
            qualia_matrix = torch.stack(all_qualia_representations)  # [num_experiences, qualia_dims]
            dimensional_structure = self._analyze_dimensional_structure(qualia_matrix)
        else:
            dimensional_structure = torch.zeros(1, self.qualia_dimensions, device=self.device)
        
        # Identify phenomenal categories
        category_analysis = self._analyze_phenomenal_categories(experiences)
        
        # Compute binding patterns
        binding_patterns = self._compute_binding_patterns(experiences)
        
        # Assess experiential continuity
        experiential_continuity = self._assess_experiential_continuity(experiences)
        
        # Measure qualia diversity
        qualia_diversity = self._measure_qualia_diversity(all_qualia_representations)
        
        return QualiaSpace(
            experiences=experiences,
            dimensional_structure=dimensional_structure,
            phenomenal_categories=category_analysis,
            binding_patterns=binding_patterns,
            experiential_continuity=experiential_continuity,
            qualia_diversity=qualia_diversity
        )
    
    def _extract_qualitative_experience(self, 
                                      qualia_representation: torch.Tensor, 
                                      timestep: int) -> QualitativeExperience:
        """
        Extract qualitative experience from qualia representation.
        
        Args:
            qualia_representation: Qualia space representation [qualia_dims]
            timestep: Current timestep
            
        Returns:
            Qualitative experience object
        """
        # Compute intensity
        intensity = self.intensity_estimator(qualia_representation.unsqueeze(0)).item()
        
        # Compute distinctness (how unique this experience is)
        distinctness = self._compute_distinctness(qualia_representation)
        
        # Estimate temporal duration (simplified)
        temporal_duration = 1.0  # Single timestep for now
        
        # Compute binding strength with recent experiences
        binding_strength = self._compute_local_binding_strength(qualia_representation)
        
        # Categorize phenomenal content
        category_probs = self.phenomenal_categorizer(qualia_representation.unsqueeze(0)).squeeze(0)
        phenomenal_category = self.phenomenal_categories[torch.argmax(category_probs).item()]
        
        # Estimate subjective qualities
        subjective_quality = {}
        for quality_name, estimator in self.quality_estimators.items():
            quality_value = estimator(qualia_representation.unsqueeze(0)).item()
            subjective_quality[quality_name] = quality_value
        
        return QualitativeExperience(
            content=qualia_representation,
            intensity=intensity,
            distinctness=distinctness,
            temporal_duration=temporal_duration,
            binding_strength=binding_strength,
            phenomenal_category=phenomenal_category,
            subjective_quality=subjective_quality
        )
    
    def _compute_distinctness(self, qualia_representation: torch.Tensor) -> float:
        """Compute how distinct this quale is from recent experiences."""
        if len(self.experience_history) < 2:
            return 1.0  # Highly distinct if no comparison available
        
        # Compare with recent experiences
        recent_experiences = self.experience_history[-10:]  # Last 10 experiences
        distinctness_scores = []
        
        for experience in recent_experiences:
            # Use discriminator to compute distinctness
            combined_input = torch.cat([
                qualia_representation, 
                experience.content
            ], dim=0)
            
            distinctness = self.quality_discriminator(combined_input.unsqueeze(0)).item()
            distinctness_scores.append(distinctness)
        
        # Average distinctness from recent experiences
        return np.mean(distinctness_scores) if distinctness_scores else 1.0
    
    def _compute_local_binding_strength(self, qualia_representation: torch.Tensor) -> float:
        """Compute binding strength with temporally adjacent experiences."""
        if len(self.experience_history) < 1:
            return 0.0
        
        # Check binding with most recent experience
        recent_experience = self.experience_history[-1]
        
        combined_input = torch.cat([
            qualia_representation,
            recent_experience.content
        ], dim=0)
        
        binding_strength = self.binding_detector(combined_input.unsqueeze(0)).item()
        
        return binding_strength
    
    def _analyze_dimensional_structure(self, qualia_matrix: torch.Tensor) -> torch.Tensor:
        """
        Analyze the dimensional structure of qualia space.
        
        Args:
            qualia_matrix: Matrix of qualia representations [num_experiences, qualia_dims]
            
        Returns:
            Dimensional structure analysis
        """
        try:
            # Convert to numpy for analysis
            qualia_np = qualia_matrix.detach().cpu().numpy()
            
            # Principal Component Analysis to identify main dimensions
            pca = PCA(n_components=min(50, qualia_np.shape[0], qualia_np.shape[1]))
            pca_result = pca.fit_transform(qualia_np)
            
            # Convert back to tensor
            dimensional_structure = torch.tensor(
                pca_result, device=self.device, dtype=torch.float32
            )
            
            return dimensional_structure
            
        except Exception as e:
            self.logger.warning(f"Dimensional structure analysis failed: {e}")
            return torch.zeros(qualia_matrix.shape[0], 50, device=self.device)
    
    def _analyze_phenomenal_categories(self, experiences: List[QualitativeExperience]) -> List[str]:
        """Analyze the distribution of phenomenal categories."""
        if not experiences:
            return []
        
        # Count category occurrences
        category_counts = {}
        for experience in experiences:
            category = experience.phenomenal_category
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Sort by frequency
        sorted_categories = sorted(
            category_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [category for category, count in sorted_categories]
    
    def _compute_binding_patterns(self, experiences: List[QualitativeExperience]) -> torch.Tensor:
        """Compute patterns of phenomenal binding across experiences."""
        if len(experiences) < 2:
            return torch.zeros(1, 1, device=self.device)
        
        num_experiences = len(experiences)
        binding_matrix = torch.zeros(num_experiences, num_experiences, device=self.device)
        
        # Compute pairwise binding strengths
        for i in range(num_experiences):
            for j in range(i + 1, num_experiences):
                exp_i = experiences[i]
                exp_j = experiences[j]
                
                # Use binding detector
                combined_input = torch.cat([exp_i.content, exp_j.content], dim=0)
                binding_strength = self.binding_detector(combined_input.unsqueeze(0)).item()
                
                binding_matrix[i, j] = binding_strength
                binding_matrix[j, i] = binding_strength  # Symmetric
        
        return binding_matrix
    
    def _assess_experiential_continuity(self, experiences: List[QualitativeExperience]) -> float:
        """Assess continuity of experiential flow."""
        if len(experiences) < 2:
            return 0.0
        
        # Measure temporal coherence using LSTM
        try:
            experience_sequence = torch.stack([exp.content for exp in experiences])  # [seq_len, qualia_dims]
            experience_sequence = experience_sequence.unsqueeze(0)  # [1, seq_len, qualia_dims]
            
            # LSTM analysis
            lstm_output, (hidden, cell) = self.temporal_coherence_analyzer(experience_sequence)
            
            # Continuity based on LSTM hidden state evolution
            hidden_final = hidden[-1, 0, :]  # Last layer, first batch
            continuity = torch.sigmoid(torch.mean(torch.abs(hidden_final))).item()
            
            return continuity
            
        except Exception as e:
            self.logger.warning(f"Experiential continuity assessment failed: {e}")
            
            # Fallback: measure similarity between consecutive experiences
            similarities = []
            for i in range(len(experiences) - 1):
                exp_current = experiences[i]
                exp_next = experiences[i + 1]
                
                similarity = F.cosine_similarity(
                    exp_current.content.unsqueeze(0),
                    exp_next.content.unsqueeze(0),
                    dim=1
                ).item()
                
                similarities.append(max(0.0, (similarity + 1.0) / 2.0))
            
            return np.mean(similarities) if similarities else 0.0
    
    def _measure_qualia_diversity(self, qualia_representations: List[torch.Tensor]) -> float:
        """Measure diversity in qualia space."""
        if len(qualia_representations) < 2:
            return 0.0
        
        try:
            # Stack representations
            qualia_matrix = torch.stack(qualia_representations)  # [num_exp, qualia_dims]
            qualia_np = qualia_matrix.detach().cpu().numpy()
            
            # Use clustering to measure diversity
            if len(qualia_representations) >= 10:
                # DBSCAN clustering
                clustering = DBSCAN(eps=0.5, min_samples=2)
                cluster_labels = clustering.fit_predict(qualia_np)
                
                # Number of clusters as diversity measure
                num_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
                diversity = num_clusters / len(qualia_representations)
            else:
                # Pairwise distance approach for small samples
                distances = pdist(qualia_np, metric='cosine')
                diversity = np.mean(distances)
            
            return min(diversity, 1.0)
            
        except Exception as e:
            self.logger.warning(f"Qualia diversity measurement failed: {e}")
            return 0.0
    
    def _compute_phenomenal_metrics(self, qualia_space: QualiaSpace) -> PhenomenalMetrics:
        """
        Compute comprehensive phenomenal consciousness metrics.
        
        Args:
            qualia_space: Complete qualia space representation
            
        Returns:
            Phenomenal consciousness metrics
        """
        # 1. Qualia Dimensionality
        dimensionality = self._compute_effective_dimensionality(qualia_space.dimensional_structure)
        
        # 2. Phenomenal Richness
        richness = self._compute_phenomenal_richness(qualia_space.experiences)
        
        # 3. Binding Coherence
        binding_coherence = self._compute_binding_coherence(qualia_space.binding_patterns)
        
        # 4. Experiential Intensity
        intensity = self._compute_average_intensity(qualia_space.experiences)
        
        # 5. Qualitative Discrimination
        discrimination = self._compute_qualitative_discrimination(qualia_space.experiences)
        
        # 6. Temporal Continuity
        temporal_continuity = qualia_space.experiential_continuity
        
        return PhenomenalMetrics(
            qualia_dimensionality=dimensionality,
            phenomenal_richness=richness,
            binding_coherence=binding_coherence,
            experiential_intensity=intensity,
            qualitative_discrimination=discrimination,
            temporal_continuity=temporal_continuity
        )
    
    def _compute_effective_dimensionality(self, dimensional_structure: torch.Tensor) -> int:
        """Compute effective dimensionality of qualia space."""
        if dimensional_structure.numel() == 0:
            return 0
        
        try:
            # Use PCA explained variance to determine effective dimensions
            structure_np = dimensional_structure.detach().cpu().numpy()
            
            if structure_np.shape[0] < 2 or structure_np.shape[1] < 2:
                return max(1, min(structure_np.shape))
            
            pca = PCA()
            pca.fit(structure_np)
            
            # Find number of dimensions needed to explain 95% of variance
            cumulative_variance = np.cumsum(pca.explained_variance_ratio_)
            effective_dims = np.argmax(cumulative_variance >= 0.95) + 1
            
            return min(effective_dims, 100)  # Cap at reasonable maximum
            
        except Exception as e:
            self.logger.warning(f"Effective dimensionality computation failed: {e}")
            return 1
    
    def _compute_phenomenal_richness(self, experiences: List[QualitativeExperience]) -> float:
        """Compute richness of phenomenal experience."""
        if not experiences:
            return 0.0
        
        # Richness factors
        richness_factors = []
        
        # 1. Category diversity
        categories = set(exp.phenomenal_category for exp in experiences)
        category_diversity = len(categories) / len(self.phenomenal_categories)
        richness_factors.append(category_diversity)
        
        # 2. Subjective quality richness
        quality_means = {}
        for experience in experiences:
            for quality, value in experience.subjective_quality.items():
                if quality not in quality_means:
                    quality_means[quality] = []
                quality_means[quality].append(value)
        
        quality_richness = 0.0
        for quality, values in quality_means.items():
            quality_richness += np.mean(values)
        quality_richness /= len(quality_means) if quality_means else 1.0
        richness_factors.append(quality_richness)
        
        # 3. Intensity distribution
        intensities = [exp.intensity for exp in experiences]
        intensity_richness = np.mean(intensities)
        richness_factors.append(intensity_richness)
        
        # 4. Distinctness richness
        distinctness_scores = [exp.distinctness for exp in experiences]
        distinctness_richness = np.mean(distinctness_scores)
        richness_factors.append(distinctness_richness)
        
        # Weighted combination
        weights = [0.3, 0.3, 0.2, 0.2]
        total_richness = sum(w * f for w, f in zip(weights, richness_factors))
        
        return total_richness
    
    def _compute_binding_coherence(self, binding_patterns: torch.Tensor) -> float:
        """Compute coherence of phenomenal binding."""
        if binding_patterns.numel() <= 1:
            return 0.0
        
        # Coherence based on binding pattern structure
        binding_np = binding_patterns.detach().cpu().numpy()
        
        # Mean binding strength
        mean_binding = np.mean(binding_np[binding_np > 0])
        
        # Binding consistency (low variance = high coherence)
        binding_std = np.std(binding_np[binding_np > 0])
        consistency = 1.0 / (1.0 + binding_std)
        
        # Overall coherence
        coherence = 0.6 * mean_binding + 0.4 * consistency
        
        return coherence if not np.isnan(coherence) else 0.0
    
    def _compute_average_intensity(self, experiences: List[QualitativeExperience]) -> float:
        """Compute average experiential intensity."""
        if not experiences:
            return 0.0
        
        intensities = [exp.intensity for exp in experiences]
        return np.mean(intensities)
    
    def _compute_qualitative_discrimination(self, experiences: List[QualitativeExperience]) -> float:
        """Compute ability to discriminate qualitative differences."""
        if len(experiences) < 2:
            return 0.0
        
        # Average distinctness as discrimination ability
        distinctness_scores = [exp.distinctness for exp in experiences]
        return np.mean(distinctness_scores)
    
    def analyze_qualia_evolution(self, 
                               activations_sequence: List[torch.Tensor]) -> Dict[str, float]:
        """
        Analyze evolution of qualia space over time.
        
        Args:
            activations_sequence: Sequence of neural activations
            
        Returns:
            Dictionary with qualia evolution analysis
        """
        dimensionalities = []
        richness_scores = []
        binding_coherence_scores = []
        
        for activations in activations_sequence:
            # Map to qualia space
            dimensionality = self.map_qualia_space(activations)
            dimensionalities.append(dimensionality)
            
            # Extract additional metrics from recent experiences
            if len(self.experience_history) >= 10:
                recent_experiences = self.experience_history[-10:]
                
                # Compute richness
                richness = self._compute_phenomenal_richness(recent_experiences)
                richness_scores.append(richness)
                
                # Compute binding coherence (simplified)
                binding_strengths = [exp.binding_strength for exp in recent_experiences]
                binding_coherence = np.mean(binding_strengths)
                binding_coherence_scores.append(binding_coherence)
        
        dimensionality_array = np.array(dimensionalities)
        
        evolution = {
            'mean_qualia_dimensionality': float(np.mean(dimensionality_array)),
            'dimensionality_growth': float(np.polyfit(range(len(dimensionalities)), dimensionalities, 1)[0]) if len(dimensionalities) > 1 else 0.0,
            'dimensionality_stability': float(1.0 / (1.0 + np.std(dimensionality_array)))
        }
        
        if richness_scores:
            evolution['mean_phenomenal_richness'] = float(np.mean(richness_scores))
            evolution['richness_trend'] = float(np.polyfit(range(len(richness_scores)), richness_scores, 1)[0]) if len(richness_scores) > 1 else 0.0
        
        if binding_coherence_scores:
            evolution['mean_binding_coherence'] = float(np.mean(binding_coherence_scores))
            evolution['binding_stability'] = float(1.0 - np.std(binding_coherence_scores))
        
        return evolution
    
    def visualize_qualia_space(self, 
                             save_path: Optional[str] = None) -> Optional[plt.Figure]:
        """
        Visualize the current qualia space.
        
        Args:
            save_path: Optional path to save visualization
            
        Returns:
            Matplotlib figure if successful, None otherwise
        """
        if len(self.experience_history) < 10:
            self.logger.warning("Insufficient experiences for visualization")
            return None
        
        try:
            # Extract qualia representations
            qualia_data = torch.stack([
                exp.content for exp in self.experience_history[-50:]  # Last 50 experiences
            ])
            qualia_np = qualia_data.detach().cpu().numpy()
            
            # Dimensionality reduction for visualization
            if qualia_np.shape[1] > 2:
                reducer = UMAP(n_components=2, random_state=42)
                qualia_2d = reducer.fit_transform(qualia_np)
            else:
                qualia_2d = qualia_np
            
            # Create visualization
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle('Qualia Space Visualization', fontsize=16)
            
            # 1. Qualia space scatter plot
            ax1 = axes[0, 0]
            intensities = [exp.intensity for exp in self.experience_history[-50:]]
            scatter = ax1.scatter(qualia_2d[:, 0], qualia_2d[:, 1], 
                                c=intensities, cmap='viridis', alpha=0.7)
            ax1.set_title('Qualia Space (colored by intensity)')
            ax1.set_xlabel('UMAP Dimension 1')
            ax1.set_ylabel('UMAP Dimension 2')
            plt.colorbar(scatter, ax=ax1)
            
            # 2. Phenomenal categories
            ax2 = axes[0, 1]
            categories = [exp.phenomenal_category for exp in self.experience_history[-50:]]
            unique_categories = list(set(categories))
            category_colors = plt.cm.Set3(np.linspace(0, 1, len(unique_categories)))
            
            for i, category in enumerate(unique_categories):
                mask = np.array(categories) == category
                ax2.scatter(qualia_2d[mask, 0], qualia_2d[mask, 1], 
                           c=[category_colors[i]], label=category, alpha=0.7)
            ax2.set_title('Phenomenal Categories')
            ax2.set_xlabel('UMAP Dimension 1')
            ax2.set_ylabel('UMAP Dimension 2')
            ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # 3. Temporal evolution
            ax3 = axes[1, 0]
            time_points = range(len(self.experience_history[-50:]))
            ax3.plot(time_points, intensities, 'b-', alpha=0.7, label='Intensity')
            
            distinctness_scores = [exp.distinctness for exp in self.experience_history[-50:]]
            ax3.plot(time_points, distinctness_scores, 'r-', alpha=0.7, label='Distinctness')
            
            ax3.set_title('Temporal Evolution')
            ax3.set_xlabel('Time')
            ax3.set_ylabel('Score')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 4. Subjective quality distribution
            ax4 = axes[1, 1]
            quality_names = list(self.experience_history[-1].subjective_quality.keys())
            quality_means = []
            quality_stds = []
            
            for quality in quality_names:
                values = [exp.subjective_quality[quality] for exp in self.experience_history[-50:]]
                quality_means.append(np.mean(values))
                quality_stds.append(np.std(values))
            
            x_pos = np.arange(len(quality_names))
            bars = ax4.bar(x_pos, quality_means, yerr=quality_stds, 
                          capsize=5, alpha=0.7, color='skyblue')
            ax4.set_title('Subjective Quality Distribution')
            ax4.set_xlabel('Quality Dimension')
            ax4.set_ylabel('Average Score')
            ax4.set_xticks(x_pos)
            ax4.set_xticklabels(quality_names, rotation=45)
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                self.logger.info(f"Qualia space visualization saved to {save_path}")
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Qualia space visualization failed: {e}")
            return None