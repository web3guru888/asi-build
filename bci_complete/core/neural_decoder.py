"""
Neural Decoder - Brain signal interpretation and classification

Converts processed neural signals into meaningful commands and intentions.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
import joblib
import os
from datetime import datetime
import json

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

from .config import BCIConfig
from .signal_processor import ProcessedSignal


@dataclass
class DecodingResult:
    """Container for neural decoding results"""
    predicted_class: str
    confidence: float
    probabilities: Dict[str, float]
    features_used: List[str]
    processing_time: float
    metadata: Dict[str, Any]


@dataclass
class ModelPerformance:
    """Container for model performance metrics"""
    accuracy: float
    precision: Dict[str, float]
    recall: Dict[str, float]
    f1_score: Dict[str, float]
    confusion_matrix: np.ndarray
    cross_val_scores: List[float]


class NeuralDecoder:
    """
    Neural signal decoder for BCI applications
    
    Features:
    - Multi-class classification (motor imagery, P300, SSVEP)
    - Ensemble learning with multiple algorithms
    - Online adaptation and learning
    - Performance monitoring and validation
    - Model persistence and loading
    """
    
    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Model storage
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_selectors: Dict[str, Any] = {}
        
        # Performance tracking
        self.performance_history: Dict[str, List[ModelPerformance]] = {}
        self.adaptation_data: Dict[str, List[Dict]] = {}
        
        # Real-time decoding
        self.current_task = None
        self.decoding_enabled = True
        
        # Initialize models
        self._initialize_models()
        
        self.logger.info("Neural Decoder initialized")
    
    def _initialize_models(self):
        """Initialize classification models for different BCI tasks"""
        # Common scalers
        for task in ['motor_imagery', 'p300', 'ssvep', 'neurofeedback']:
            self.scalers[task] = StandardScaler()
            self.adaptation_data[task] = []
            self.performance_history[task] = []
        
        # CSP-LDA for motor imagery
        self.models['motor_imagery'] = self._create_ensemble_classifier([
            ('lda', LinearDiscriminantAnalysis()),
            ('svm', SVC(probability=True, kernel='rbf')),
            ('rf', RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        
        # SVM for P300
        self.models['p300'] = SVC(
            probability=True, 
            kernel='rbf', 
            C=1.0,
            random_state=42
        )
        
        # LDA for SSVEP
        self.models['ssvep'] = LinearDiscriminantAnalysis()
        
        # Neural network for neurofeedback
        self.models['neurofeedback'] = MLPClassifier(
            hidden_layer_sizes=(100, 50),
            max_iter=500,
            random_state=42
        )
        
        self.logger.info("Classification models initialized")
    
    def _create_ensemble_classifier(self, base_classifiers: List[Tuple[str, Any]]) -> VotingClassifier:
        """Create ensemble classifier with voting"""
        return VotingClassifier(
            estimators=base_classifiers,
            voting='soft' if all(hasattr(clf[1], 'predict_proba') for clf in base_classifiers) else 'hard'
        )
    
    def decode(self, processed_signal: ProcessedSignal) -> Optional[DecodingResult]:
        """Decode neural signal into actionable commands"""
        if not self.decoding_enabled or self.current_task is None:
            return None
        
        start_time = datetime.now()
        
        try:
            # Extract features for current task
            features = self._extract_task_features(processed_signal, self.current_task)
            
            if features is None:
                return None
            
            # Get model for current task
            model = self.models.get(self.current_task)
            scaler = self.scalers.get(self.current_task)
            
            if model is None or scaler is None:
                self.logger.warning(f"No trained model found for task: {self.current_task}")
                return None
            
            # Prepare features
            feature_vector = self._prepare_feature_vector(features, self.current_task)
            
            if feature_vector is None:
                return None
            
            # Scale features
            feature_vector_scaled = scaler.transform(feature_vector.reshape(1, -1))
            
            # Make prediction
            predicted_class = model.predict(feature_vector_scaled)[0]
            
            # Get probabilities if available
            probabilities = {}
            confidence = 0.0
            
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(feature_vector_scaled)[0]
                class_names = model.classes_ if hasattr(model, 'classes_') else range(len(proba))
                
                probabilities = {str(cls): float(prob) for cls, prob in zip(class_names, proba)}
                confidence = float(np.max(proba))
            else:
                confidence = 1.0  # For models without probability estimates
                probabilities[str(predicted_class)] = 1.0
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = DecodingResult(
                predicted_class=str(predicted_class),
                confidence=confidence,
                probabilities=probabilities,
                features_used=list(features.keys()),
                processing_time=processing_time,
                metadata={
                    'task': self.current_task,
                    'signal_quality': processed_signal.quality_score,
                    'artifacts_removed': processed_signal.artifacts_removed,
                    'feature_count': len(features)
                }
            )
            
            # Store for adaptation if confidence is high enough
            if confidence >= self.config.classification.confidence_threshold:
                self._store_adaptation_data(processed_signal, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Decoding error: {e}")
            return None
    
    def _extract_task_features(self, processed_signal: ProcessedSignal, task: str) -> Optional[Dict[str, Any]]:
        """Extract features specific to the given task"""
        features = processed_signal.features
        
        if task == 'motor_imagery':
            return self._extract_motor_imagery_features(features)
        elif task == 'p300':
            return self._extract_p300_features(features)
        elif task == 'ssvep':
            return self._extract_ssvep_features(features)
        elif task == 'neurofeedback':
            return self._extract_neurofeedback_features(features)
        else:
            return features
    
    def _extract_motor_imagery_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features for motor imagery classification"""
        mi_features = {}
        
        # Band power features (mu and beta rhythms)
        for channel in self.config.device.channels:
            band_powers = features.get(f'ch_{channel}_band_powers', {})
            
            # Mu rhythm (8-12 Hz) - important for motor imagery
            mi_features[f'{channel}_mu_power'] = band_powers.get('alpha', 0.0)
            
            # Beta rhythm (13-30 Hz) - also important for motor imagery
            mi_features[f'{channel}_beta_power'] = band_powers.get('beta', 0.0)
            
            # Mu/Beta ratio
            mu_power = band_powers.get('alpha', 1e-10)
            beta_power = band_powers.get('beta', 1e-10)
            mi_features[f'{channel}_mu_beta_ratio'] = mu_power / beta_power
        
        # Add spatial features
        spatial_features = features.get('spatial', {})
        mi_features.update(spatial_features)
        
        return mi_features
    
    def _extract_p300_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features for P300 classification"""
        p300_features = {}
        
        # Focus on specific channels (Cz, Pz)
        target_channels = ['Cz', 'Pz', 'C3', 'C4']
        
        for channel in target_channels:
            if channel in self.config.device.channels:
                # Temporal features are most important for P300
                temporal_features = features.get('temporal', {})
                
                for feature_name, value in temporal_features.items():
                    if channel in feature_name:
                        p300_features[feature_name] = value
                
                # Low frequency power (important for P300)
                band_powers = features.get(f'ch_{channel}_band_powers', {})
                p300_features[f'{channel}_delta_power'] = band_powers.get('delta', 0.0)
                p300_features[f'{channel}_theta_power'] = band_powers.get('theta', 0.0)
        
        return p300_features
    
    def _extract_ssvep_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features for SSVEP classification"""
        ssvep_features = {}
        
        # Focus on occipital channels
        target_channels = ['O1', 'O2', 'Oz']
        ssvep_freqs = self.config.ssvep['frequencies']
        
        for channel in target_channels:
            if channel in self.config.device.channels:
                # Spectral features at SSVEP frequencies
                for freq in ssvep_freqs:
                    # This would require more sophisticated spectral analysis
                    # For now, use nearby frequency bands
                    band_powers = features.get(f'ch_{channel}_band_powers', {})
                    
                    if freq <= 12:
                        ssvep_features[f'{channel}_ssvep_{freq}Hz'] = band_powers.get('alpha', 0.0)
                    else:
                        ssvep_features[f'{channel}_ssvep_{freq}Hz'] = band_powers.get('beta', 0.0)
        
        return ssvep_features
    
    def _extract_neurofeedback_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features for neurofeedback training"""
        nf_features = {}
        
        # All frequency bands are relevant for neurofeedback
        for channel in self.config.device.channels:
            band_powers = features.get(f'ch_{channel}_band_powers', {})
            
            for band_name, power in band_powers.items():
                nf_features[f'{channel}_{band_name}_power'] = power
        
        return nf_features
    
    def _prepare_feature_vector(self, features: Dict[str, Any], task: str) -> Optional[np.ndarray]:
        """Prepare feature vector for classification"""
        try:
            # Convert features to numpy array
            feature_values = []
            feature_names = []
            
            for name, value in features.items():
                if isinstance(value, (int, float)) and not np.isnan(value):
                    feature_values.append(value)
                    feature_names.append(name)
            
            if not feature_values:
                return None
            
            return np.array(feature_values)
            
        except Exception as e:
            self.logger.error(f"Feature preparation error: {e}")
            return None
    
    async def train_classifier(self, task: str, training_data: List[Dict]) -> Dict[str, Any]:
        """Train classifier for specific BCI task"""
        try:
            self.logger.info(f"Training classifier for task: {task}")
            
            # Prepare training data
            X, y = self._prepare_training_data(training_data, task)
            
            if X is None or len(X) == 0:
                raise ValueError("No valid training data")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config.classification.validation_split,
                random_state=42, stratify=y
            )
            
            # Scale features
            scaler = self.scalers[task]
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = self.models[task]
            model.fit(X_train_scaled, y_train)
            
            # Evaluate performance
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Cross-validation
            cv_scores = cross_val_score(
                model, X_train_scaled, y_train,
                cv=self.config.classification.cross_validation_folds
            )
            
            # Create performance metrics
            performance = ModelPerformance(
                accuracy=accuracy,
                precision=self._calculate_precision(y_test, y_pred),
                recall=self._calculate_recall(y_test, y_pred),
                f1_score=self._calculate_f1_score(y_test, y_pred),
                confusion_matrix=confusion_matrix(y_test, y_pred),
                cross_val_scores=cv_scores.tolist()
            )
            
            # Store performance
            self.performance_history[task].append(performance)
            
            # Save model
            self._save_model(task)
            
            result = {
                'task': task,
                'accuracy': accuracy,
                'cv_mean': np.mean(cv_scores),
                'cv_std': np.std(cv_scores),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'features': X_train.shape[1]
            }
            
            self.logger.info(f"Training completed for {task}: accuracy={accuracy:.3f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Training failed for {task}: {e}")
            raise
    
    def _prepare_training_data(self, training_data: List[Dict], task: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Prepare training data for classifier"""
        features_list = []
        labels_list = []
        
        for trial in training_data:
            # Extract features from processed data
            processed_data = trial.get('processed_data', [])
            label = trial.get('label') or trial.get('task_type')
            
            if not processed_data or not label:
                continue
            
            # Average features across trial
            trial_features = {}
            feature_count = 0
            
            for sample in processed_data:
                if isinstance(sample, dict) and 'features' in sample:
                    sample_features = sample['features']
                    
                    for key, value in sample_features.items():
                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                full_key = f"{key}_{subkey}"
                                if full_key not in trial_features:
                                    trial_features[full_key] = []
                                trial_features[full_key].append(subvalue)
                        elif isinstance(value, (int, float)):
                            if key not in trial_features:
                                trial_features[key] = []
                            trial_features[key].append(value)
                    
                    feature_count += 1
            
            # Average features
            if feature_count > 0:
                averaged_features = {}
                for key, values in trial_features.items():
                    if values and all(isinstance(v, (int, float)) for v in values):
                        averaged_features[key] = np.mean(values)
                
                # Extract task-specific features
                task_features = self._extract_task_features_from_dict(averaged_features, task)
                
                if task_features:
                    feature_vector = self._prepare_feature_vector(task_features, task)
                    if feature_vector is not None:
                        features_list.append(feature_vector)
                        labels_list.append(label)
        
        if not features_list:
            return None, None
        
        return np.array(features_list), np.array(labels_list)
    
    def _extract_task_features_from_dict(self, features: Dict[str, Any], task: str) -> Dict[str, Any]:
        """Extract task-specific features from feature dictionary"""
        # This is a simplified version - in practice, you'd want more sophisticated feature selection
        if task == 'motor_imagery':
            return {k: v for k, v in features.items() 
                   if any(band in k.lower() for band in ['alpha', 'beta', 'mu'])}
        elif task == 'p300':
            return {k: v for k, v in features.items() 
                   if any(feat in k.lower() for feat in ['delta', 'theta', 'activity', 'complexity'])}
        elif task == 'ssvep':
            return {k: v for k, v in features.items() 
                   if any(ch in k for ch in ['O1', 'O2', 'Oz'])}
        else:
            return features
    
    def _calculate_precision(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate precision for each class"""
        from sklearn.metrics import precision_score
        
        labels = np.unique(y_true)
        precision_dict = {}
        
        for label in labels:
            precision = precision_score(y_true, y_pred, labels=[label], average='macro', zero_division=0)
            precision_dict[str(label)] = float(precision)
        
        return precision_dict
    
    def _calculate_recall(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate recall for each class"""
        from sklearn.metrics import recall_score
        
        labels = np.unique(y_true)
        recall_dict = {}
        
        for label in labels:
            recall = recall_score(y_true, y_pred, labels=[label], average='macro', zero_division=0)
            recall_dict[str(label)] = float(recall)
        
        return recall_dict
    
    def _calculate_f1_score(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate F1 score for each class"""
        from sklearn.metrics import f1_score
        
        labels = np.unique(y_true)
        f1_dict = {}
        
        for label in labels:
            f1 = f1_score(y_true, y_pred, labels=[label], average='macro', zero_division=0)
            f1_dict[str(label)] = float(f1)
        
        return f1_dict
    
    def _store_adaptation_data(self, processed_signal: ProcessedSignal, result: DecodingResult):
        """Store data for online adaptation"""
        adaptation_entry = {
            'timestamp': datetime.now().isoformat(),
            'features': processed_signal.features,
            'predicted_class': result.predicted_class,
            'confidence': result.confidence,
            'signal_quality': processed_signal.quality_score
        }
        
        self.adaptation_data[self.current_task].append(adaptation_entry)
        
        # Keep only recent data (last 100 entries)
        if len(self.adaptation_data[self.current_task]) > 100:
            self.adaptation_data[self.current_task] = self.adaptation_data[self.current_task][-100:]
    
    def set_current_task(self, task: str):
        """Set the current BCI task for decoding"""
        if task in self.models:
            self.current_task = task
            self.logger.info(f"Current task set to: {task}")
        else:
            self.logger.error(f"Unknown task: {task}")
    
    def get_performance_summary(self, task: str) -> Optional[Dict[str, Any]]:
        """Get performance summary for a task"""
        if task not in self.performance_history or not self.performance_history[task]:
            return None
        
        latest_performance = self.performance_history[task][-1]
        
        return {
            'task': task,
            'accuracy': latest_performance.accuracy,
            'precision': latest_performance.precision,
            'recall': latest_performance.recall,
            'f1_score': latest_performance.f1_score,
            'cv_scores': latest_performance.cross_val_scores,
            'training_sessions': len(self.performance_history[task])
        }
    
    def _save_model(self, task: str):
        """Save trained model to disk"""
        try:
            model_dir = self.config.model_directory
            os.makedirs(model_dir, exist_ok=True)
            
            # Save model
            model_path = os.path.join(model_dir, f"{task}_model.pkl")
            joblib.dump(self.models[task], model_path)
            
            # Save scaler
            scaler_path = os.path.join(model_dir, f"{task}_scaler.pkl")
            joblib.dump(self.scalers[task], scaler_path)
            
            # Save metadata
            metadata = {
                'task': task,
                'timestamp': datetime.now().isoformat(),
                'config': self.config._to_dict()
            }
            
            metadata_path = os.path.join(model_dir, f"{task}_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Model saved for task: {task}")
            
        except Exception as e:
            self.logger.error(f"Failed to save model for {task}: {e}")
    
    def load_model(self, task: str) -> bool:
        """Load trained model from disk"""
        try:
            model_dir = self.config.model_directory
            
            # Load model
            model_path = os.path.join(model_dir, f"{task}_model.pkl")
            if os.path.exists(model_path):
                self.models[task] = joblib.load(model_path)
            else:
                return False
            
            # Load scaler
            scaler_path = os.path.join(model_dir, f"{task}_scaler.pkl")
            if os.path.exists(scaler_path):
                self.scalers[task] = joblib.load(scaler_path)
            else:
                return False
            
            self.logger.info(f"Model loaded for task: {task}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load model for {task}: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup neural decoder resources"""
        self.models.clear()
        self.scalers.clear()
        self.adaptation_data.clear()
        self.performance_history.clear()
        self.logger.info("Neural Decoder cleanup complete")