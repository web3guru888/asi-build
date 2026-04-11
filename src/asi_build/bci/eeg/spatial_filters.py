"""
EEG Spatial Filtering

Advanced spatial filtering techniques for EEG including
CAR, Laplacian, ICA, and source localization methods.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import linalg
from scipy.spatial.distance import cdist
from sklearn.decomposition import PCA, FastICA

from ..core.config import BCIConfig


class SpatialFilterBank:
    """
    Comprehensive spatial filtering for EEG signals

    Filters available:
    - Common Average Reference (CAR)
    - Surface Laplacian
    - Independent Component Analysis (ICA)
    - Principal Component Analysis (PCA)
    - Spatial whitening
    - Source localization filters
    """

    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        self.channels = config.device.channels
        self.n_channels = len(self.channels)

        # Electrode positions (simplified 10-20 system)
        self.electrode_positions = self._get_electrode_positions()

        # Spatial filter matrices
        self.car_matrix = None
        self.laplacian_matrix = None
        self.ica_model = None
        self.pca_model = None
        self.whitening_matrix = None

        self._initialize_filters()

        self.logger.info("Spatial Filter Bank initialized")

    def _get_electrode_positions(self) -> Dict[str, Tuple[float, float, float]]:
        """Get 3D electrode positions for standard 10-20 system"""
        # Simplified electrode positions (x, y, z) in spherical coordinates
        # These are approximate positions for common electrodes
        positions = {
            "Fp1": (-0.3, 0.9, 0.3),
            "Fp2": (0.3, 0.9, 0.3),
            "F3": (-0.6, 0.6, 0.5),
            "F4": (0.6, 0.6, 0.5),
            "F7": (-0.8, 0.3, 0.5),
            "F8": (0.8, 0.3, 0.5),
            "Fz": (0.0, 0.7, 0.7),
            "C3": (-0.7, 0.0, 0.7),
            "C4": (0.7, 0.0, 0.7),
            "Cz": (0.0, 0.0, 1.0),
            "P3": (-0.6, -0.6, 0.5),
            "P4": (0.6, -0.6, 0.5),
            "P7": (-0.8, -0.3, 0.5),
            "P8": (0.8, -0.3, 0.5),
            "Pz": (0.0, -0.7, 0.7),
            "O1": (-0.3, -0.9, 0.3),
            "O2": (0.3, -0.9, 0.3),
            "Oz": (0.0, -1.0, 0.0),
            "T7": (-1.0, 0.0, 0.0),
            "T8": (1.0, 0.0, 0.0),
            "FC1": (-0.3, 0.3, 0.9),
            "FC2": (0.3, 0.3, 0.9),
            "FC3": (-0.6, 0.3, 0.7),
            "FC4": (0.6, 0.3, 0.7),
            "CP1": (-0.3, -0.3, 0.9),
            "CP2": (0.3, -0.3, 0.9),
            "CP3": (-0.6, -0.3, 0.7),
            "CP4": (0.6, -0.3, 0.7),
            "FCz": (0.0, 0.4, 0.9),
            "CPz": (0.0, -0.4, 0.9),
        }

        # Return only positions for channels in our montage
        available_positions = {}
        for ch in self.channels:
            if ch in positions:
                available_positions[ch] = positions[ch]

        return available_positions

    def _initialize_filters(self):
        """Initialize spatial filter matrices"""
        # Common Average Reference matrix
        self.car_matrix = self._create_car_matrix()

        # Surface Laplacian matrix
        if len(self.electrode_positions) >= 4:
            self.laplacian_matrix = self._create_laplacian_matrix()

    def _create_car_matrix(self) -> np.ndarray:
        """Create Common Average Reference filter matrix"""
        car_matrix = (
            np.eye(self.n_channels) - np.ones((self.n_channels, self.n_channels)) / self.n_channels
        )
        return car_matrix

    def _create_laplacian_matrix(self) -> Optional[np.ndarray]:
        """Create surface Laplacian filter matrix"""
        try:
            if len(self.electrode_positions) < 4:
                return None

            # Get positions for available channels
            positions = []
            channel_indices = []

            for i, ch in enumerate(self.channels):
                if ch in self.electrode_positions:
                    positions.append(self.electrode_positions[ch])
                    channel_indices.append(i)

            if len(positions) < 4:
                return None

            positions = np.array(positions)
            n_electrodes = len(positions)

            # Compute distance matrix
            distance_matrix = cdist(positions, positions)

            # Create Laplacian matrix using inverse distance weighting
            laplacian_matrix = np.zeros((self.n_channels, self.n_channels))

            for i, ch_idx in enumerate(channel_indices):
                # Find neighboring electrodes
                distances = distance_matrix[i, :]

                # Exclude self
                neighbor_mask = distances > 0
                neighbor_distances = distances[neighbor_mask]
                neighbor_indices = np.array(channel_indices)[neighbor_mask]

                if len(neighbor_indices) > 0:
                    # Inverse distance weights
                    weights = 1.0 / (neighbor_distances + 1e-6)
                    weights = weights / np.sum(weights)

                    # Set Laplacian weights
                    laplacian_matrix[ch_idx, ch_idx] = 1.0
                    for j, neighbor_idx in enumerate(neighbor_indices):
                        laplacian_matrix[ch_idx, neighbor_idx] = -weights[j]

            return laplacian_matrix

        except Exception as e:
            self.logger.error(f"Laplacian matrix creation failed: {e}")
            return None

    def apply_car(self, data: np.ndarray) -> np.ndarray:
        """Apply Common Average Reference"""
        if self.car_matrix is None:
            return data

        return self.car_matrix @ data

    def apply_laplacian(self, data: np.ndarray) -> np.ndarray:
        """Apply surface Laplacian filter"""
        if self.laplacian_matrix is None:
            return data

        return self.laplacian_matrix @ data

    def apply_ica(self, data: np.ndarray, n_components: Optional[int] = None) -> np.ndarray:
        """Apply Independent Component Analysis"""
        try:
            if n_components is None:
                n_components = min(self.n_channels, data.shape[1] // 10)

            # Initialize or use existing ICA model
            if self.ica_model is None:
                self.ica_model = FastICA(
                    n_components=n_components, whiten="unit-variance", random_state=42
                )

                # Fit ICA
                self.ica_model.fit(data.T)

            # Transform data
            ica_data = self.ica_model.transform(data.T).T

            # Reconstruct (you might want to remove certain components here)
            reconstructed_data = self.ica_model.inverse_transform(ica_data.T).T

            return reconstructed_data

        except Exception as e:
            self.logger.error(f"ICA application failed: {e}")
            return data

    def apply_pca(
        self, data: np.ndarray, n_components: Optional[int] = None, explained_variance: float = 0.95
    ) -> np.ndarray:
        """Apply Principal Component Analysis"""
        try:
            if self.pca_model is None:
                self.pca_model = PCA()
                self.pca_model.fit(data.T)

            # Determine number of components
            if n_components is None:
                # Use explained variance criterion
                cumsum_var = np.cumsum(self.pca_model.explained_variance_ratio_)
                n_components = np.argmax(cumsum_var >= explained_variance) + 1
                n_components = min(n_components, self.n_channels)

            # Transform to PCA space
            pca_data = self.pca_model.transform(data.T)[:, :n_components]

            # Reconstruct with selected components
            reconstructed_data = self.pca_model.inverse_transform(
                np.column_stack(
                    [
                        pca_data,
                        np.zeros((pca_data.shape[0], self.pca_model.n_components_ - n_components)),
                    ]
                )
            ).T

            return reconstructed_data

        except Exception as e:
            self.logger.error(f"PCA application failed: {e}")
            return data

    def apply_whitening(self, data: np.ndarray) -> np.ndarray:
        """Apply spatial whitening (sphering)"""
        try:
            if self.whitening_matrix is None:
                # Compute covariance matrix
                cov_matrix = np.cov(data)

                # Eigenvalue decomposition
                eigenvals, eigenvecs = linalg.eigh(cov_matrix)

                # Create whitening matrix
                # W = V * D^(-1/2) * V^T
                eigenvals_inv_sqrt = 1.0 / np.sqrt(eigenvals + 1e-10)
                self.whitening_matrix = eigenvecs @ np.diag(eigenvals_inv_sqrt) @ eigenvecs.T

            # Apply whitening
            whitened_data = self.whitening_matrix @ data

            return whitened_data

        except Exception as e:
            self.logger.error(f"Whitening failed: {e}")
            return data

    def apply_bipolar_montage(
        self, data: np.ndarray, pairs: Optional[List[Tuple[str, str]]] = None
    ) -> Tuple[np.ndarray, List[str]]:
        """Apply bipolar montage (difference between electrode pairs)"""
        if pairs is None:
            # Default bipolar pairs
            pairs = [
                ("Fp1", "F3"),
                ("Fp2", "F4"),
                ("F3", "C3"),
                ("F4", "C4"),
                ("C3", "P3"),
                ("C4", "P4"),
                ("P3", "O1"),
                ("P4", "O2"),
                ("F7", "T7"),
                ("F8", "T8"),
                ("T7", "P7"),
                ("T8", "P8"),
            ]

        bipolar_data = []
        bipolar_labels = []

        for ch1, ch2 in pairs:
            if ch1 in self.channels and ch2 in self.channels:
                ch1_idx = self.channels.index(ch1)
                ch2_idx = self.channels.index(ch2)

                # Compute difference
                diff_signal = data[ch1_idx, :] - data[ch2_idx, :]
                bipolar_data.append(diff_signal)
                bipolar_labels.append(f"{ch1}-{ch2}")

        if bipolar_data:
            return np.array(bipolar_data), bipolar_labels
        else:
            return data, self.channels

    def apply_longitudinal_montage(self, data: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """Apply longitudinal bipolar montage"""
        # Longitudinal chains
        chains = [
            ["Fp1", "F3", "C3", "P3", "O1"],
            ["Fp2", "F4", "C4", "P4", "O2"],
            ["F7", "T7", "P7"],
            ["F8", "T8", "P8"],
            ["Fz", "Cz", "Pz", "Oz"],
        ]

        longitudinal_data = []
        longitudinal_labels = []

        for chain in chains:
            # Create pairs within chain
            for i in range(len(chain) - 1):
                ch1, ch2 = chain[i], chain[i + 1]

                if ch1 in self.channels and ch2 in self.channels:
                    ch1_idx = self.channels.index(ch1)
                    ch2_idx = self.channels.index(ch2)

                    # Compute difference
                    diff_signal = data[ch1_idx, :] - data[ch2_idx, :]
                    longitudinal_data.append(diff_signal)
                    longitudinal_labels.append(f"{ch1}-{ch2}")

        if longitudinal_data:
            return np.array(longitudinal_data), longitudinal_labels
        else:
            return data, self.channels

    def apply_transverse_montage(self, data: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """Apply transverse bipolar montage"""
        # Left-right pairs
        lr_pairs = [
            ("Fp1", "Fp2"),
            ("F3", "F4"),
            ("F7", "F8"),
            ("C3", "C4"),
            ("T7", "T8"),
            ("P3", "P4"),
            ("P7", "P8"),
            ("O1", "O2"),
        ]

        transverse_data = []
        transverse_labels = []

        for ch1, ch2 in lr_pairs:
            if ch1 in self.channels and ch2 in self.channels:
                ch1_idx = self.channels.index(ch1)
                ch2_idx = self.channels.index(ch2)

                # Compute difference
                diff_signal = data[ch1_idx, :] - data[ch2_idx, :]
                transverse_data.append(diff_signal)
                transverse_labels.append(f"{ch1}-{ch2}")

        if transverse_data:
            return np.array(transverse_data), transverse_labels
        else:
            return data, self.channels

    def compute_spatial_patterns(
        self, data: np.ndarray, labels: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """Compute spatial patterns for different classes"""
        patterns = {}

        unique_labels = np.unique(labels)

        for label in unique_labels:
            # Get data for this class
            class_mask = labels == label
            class_data = data[:, class_mask] if data.ndim == 2 else data[class_mask, :, :]

            if class_data.ndim == 3:
                # Average across trials
                class_data = np.mean(class_data, axis=0)

            # Compute covariance matrix
            cov_matrix = np.cov(class_data)

            # Eigenvalue decomposition
            eigenvals, eigenvecs = linalg.eigh(cov_matrix)

            # Sort by eigenvalues (descending)
            sort_indices = np.argsort(eigenvals)[::-1]

            patterns[str(label)] = eigenvecs[:, sort_indices]

        return patterns

    def apply_source_localization(
        self, data: np.ndarray, method: str = "minimum_norm"
    ) -> np.ndarray:
        """Apply source localization (simplified)"""
        # This is a very simplified source localization
        # In practice, you would use tools like MNE-Python with proper head models

        if method == "minimum_norm":
            return self._minimum_norm_estimation(data)
        elif method == "beamformer":
            return self._beamformer_localization(data)
        else:
            self.logger.warning(f"Unknown source localization method: {method}")
            return data

    def _minimum_norm_estimation(self, data: np.ndarray) -> np.ndarray:
        """Simplified minimum norm estimation"""
        try:
            # Create simplified leadfield matrix (random for demonstration)
            n_sources = self.n_channels * 2  # Assuming 2 sources per channel
            leadfield = np.random.randn(self.n_channels, n_sources) * 0.1

            # Regularized inverse
            reg_param = 0.1
            inverse_op = (
                linalg.pinv(leadfield.T @ leadfield + reg_param * np.eye(n_sources)) @ leadfield.T
            )

            # Apply inverse
            source_data = inverse_op @ data

            return source_data

        except Exception as e:
            self.logger.error(f"Minimum norm estimation failed: {e}")
            return data

    def _beamformer_localization(self, data: np.ndarray) -> np.ndarray:
        """Simplified beamformer source localization"""
        try:
            # Compute data covariance
            data_cov = np.cov(data)

            # Simplified beamformer weights (identity for demonstration)
            beamformer_weights = np.eye(self.n_channels)

            # Apply beamformer
            source_data = beamformer_weights @ data

            return source_data

        except Exception as e:
            self.logger.error(f"Beamformer localization failed: {e}")
            return data

    def get_available_filters(self) -> List[str]:
        """Get list of available spatial filters"""
        filters = ["car", "bipolar", "longitudinal", "transverse"]

        if self.laplacian_matrix is not None:
            filters.append("laplacian")

        filters.extend(["ica", "pca", "whitening", "source_localization"])

        return filters

    def apply_filter(
        self, data: np.ndarray, filter_name: str, **kwargs
    ) -> Tuple[np.ndarray, Optional[List[str]]]:
        """Apply specified spatial filter"""
        if filter_name == "car":
            return self.apply_car(data), None
        elif filter_name == "laplacian":
            return self.apply_laplacian(data), None
        elif filter_name == "ica":
            return self.apply_ica(data, **kwargs), None
        elif filter_name == "pca":
            return self.apply_pca(data, **kwargs), None
        elif filter_name == "whitening":
            return self.apply_whitening(data), None
        elif filter_name == "bipolar":
            return self.apply_bipolar_montage(data, **kwargs)
        elif filter_name == "longitudinal":
            return self.apply_longitudinal_montage(data)
        elif filter_name == "transverse":
            return self.apply_transverse_montage(data)
        elif filter_name == "source_localization":
            return self.apply_source_localization(data, **kwargs), None
        else:
            self.logger.error(f"Unknown filter: {filter_name}")
            return data, None
