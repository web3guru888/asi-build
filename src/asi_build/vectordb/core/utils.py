"""
Utility functions for Kenny Vector Database System

This module provides common utilities for vector operations, text processing,
performance monitoring, and system management.
"""

import hashlib
import json
import logging
import statistics
import time
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VectorStats:
    """Statistics for vector operations."""

    mean: float
    std: float
    min_val: float
    max_val: float
    median: float
    dimension: int
    norm: float


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""

    operation_name: str
    duration: float
    start_time: float
    end_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VectorUtils:
    """Utility class for vector operations and computations."""

    @staticmethod
    def normalize_vector(vector: Union[List[float], np.ndarray]) -> np.ndarray:
        """
        Normalize a vector to unit length.

        Args:
            vector: Input vector

        Returns:
            Normalized vector
        """
        vector = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(vector)

        if norm == 0:
            logger.warning("Cannot normalize zero vector")
            return vector

        return vector / norm

    @staticmethod
    def cosine_similarity(
        vector1: Union[List[float], np.ndarray], vector2: Union[List[float], np.ndarray]
    ) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vector1: First vector
            vector2: Second vector

        Returns:
            Cosine similarity score
        """
        v1 = np.array(vector1, dtype=np.float32)
        v2 = np.array(vector2, dtype=np.float32)

        # Normalize vectors
        v1_norm = np.linalg.norm(v1)
        v2_norm = np.linalg.norm(v2)

        if v1_norm == 0 or v2_norm == 0:
            return 0.0

        return np.dot(v1, v2) / (v1_norm * v2_norm)

    @staticmethod
    def euclidean_distance(
        vector1: Union[List[float], np.ndarray], vector2: Union[List[float], np.ndarray]
    ) -> float:
        """
        Calculate Euclidean distance between two vectors.

        Args:
            vector1: First vector
            vector2: Second vector

        Returns:
            Euclidean distance
        """
        v1 = np.array(vector1, dtype=np.float32)
        v2 = np.array(vector2, dtype=np.float32)

        return np.linalg.norm(v1 - v2)

    @staticmethod
    def dot_product(
        vector1: Union[List[float], np.ndarray], vector2: Union[List[float], np.ndarray]
    ) -> float:
        """
        Calculate dot product between two vectors.

        Args:
            vector1: First vector
            vector2: Second vector

        Returns:
            Dot product
        """
        v1 = np.array(vector1, dtype=np.float32)
        v2 = np.array(vector2, dtype=np.float32)

        return np.dot(v1, v2)

    @staticmethod
    def vector_statistics(vectors: List[Union[List[float], np.ndarray]]) -> VectorStats:
        """
        Calculate statistics for a collection of vectors.

        Args:
            vectors: List of vectors

        Returns:
            Vector statistics
        """
        if not vectors:
            raise ValueError("Empty vector list provided")

        # Convert to numpy array
        vector_array = np.array(vectors, dtype=np.float32)

        # Calculate statistics
        flat_values = vector_array.flatten()

        return VectorStats(
            mean=float(np.mean(flat_values)),
            std=float(np.std(flat_values)),
            min_val=float(np.min(flat_values)),
            max_val=float(np.max(flat_values)),
            median=float(np.median(flat_values)),
            dimension=vector_array.shape[1] if len(vector_array.shape) > 1 else len(vector_array),
            norm=float(np.mean([np.linalg.norm(v) for v in vector_array])),
        )

    @staticmethod
    def batch_cosine_similarity(
        query_vector: Union[List[float], np.ndarray], vectors: List[Union[List[float], np.ndarray]]
    ) -> List[float]:
        """
        Calculate cosine similarity between query vector and batch of vectors.

        Args:
            query_vector: Query vector
            vectors: List of vectors to compare against

        Returns:
            List of similarity scores
        """
        query = np.array(query_vector, dtype=np.float32)
        vector_array = np.array(vectors, dtype=np.float32)

        # Normalize query vector
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return [0.0] * len(vectors)

        query_normalized = query / query_norm

        # Normalize all vectors
        vector_norms = np.linalg.norm(vector_array, axis=1)
        vector_norms[vector_norms == 0] = 1  # Avoid division by zero
        vectors_normalized = vector_array / vector_norms[:, np.newaxis]

        # Calculate similarities
        similarities = np.dot(vectors_normalized, query_normalized)

        return similarities.tolist()

    @staticmethod
    def find_top_k_similar(
        query_vector: Union[List[float], np.ndarray],
        vectors: List[Union[List[float], np.ndarray]],
        k: int = 10,
        metric: str = "cosine",
    ) -> List[Tuple[int, float]]:
        """
        Find top-k most similar vectors.

        Args:
            query_vector: Query vector
            vectors: List of vectors to search
            k: Number of top results
            metric: Similarity metric (cosine, euclidean, dot)

        Returns:
            List of (index, score) tuples
        """
        if metric == "cosine":
            scores = VectorUtils.batch_cosine_similarity(query_vector, vectors)
            # Higher is better for cosine similarity
            indexed_scores = [(i, score) for i, score in enumerate(scores)]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
        elif metric == "euclidean":
            query = np.array(query_vector, dtype=np.float32)
            scores = [VectorUtils.euclidean_distance(query, v) for v in vectors]
            # Lower is better for Euclidean distance
            indexed_scores = [(i, score) for i, score in enumerate(scores)]
            indexed_scores.sort(key=lambda x: x[1])
        elif metric == "dot":
            query = np.array(query_vector, dtype=np.float32)
            scores = [VectorUtils.dot_product(query, v) for v in vectors]
            # Higher is better for dot product
            indexed_scores = [(i, score) for i, score in enumerate(scores)]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
        else:
            raise ValueError(f"Unsupported metric: {metric}")

        return indexed_scores[:k]

    @staticmethod
    def cluster_vectors(
        vectors: List[Union[List[float], np.ndarray]], n_clusters: int = 10, method: str = "kmeans"
    ) -> List[int]:
        """
        Cluster vectors using specified method.

        Args:
            vectors: List of vectors to cluster
            n_clusters: Number of clusters
            method: Clustering method

        Returns:
            List of cluster assignments
        """
        try:
            from sklearn.cluster import AgglomerativeClustering, KMeans

            vector_array = np.array(vectors, dtype=np.float32)

            if method == "kmeans":
                clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            elif method == "hierarchical":
                clusterer = AgglomerativeClustering(n_clusters=n_clusters)
            else:
                raise ValueError(f"Unsupported clustering method: {method}")

            labels = clusterer.fit_predict(vector_array)
            return labels.tolist()

        except ImportError:
            logger.error("scikit-learn not available for clustering")
            return [0] * len(vectors)
        except Exception as e:
            logger.error(f"Clustering failed: {str(e)}")
            return [0] * len(vectors)


class TextUtils:
    """Utility class for text processing operations."""

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        import re

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:\'"()-]', "", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    @staticmethod
    def split_text_chunks(
        text: str, chunk_size: int = 512, overlap: int = 50, preserve_sentences: bool = True
    ) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks
            preserve_sentences: Try to preserve sentence boundaries

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end >= len(text):
                chunks.append(text[start:])
                break

            # Try to find sentence boundary if requested
            if preserve_sentences and end < len(text):
                # Look for sentence endings near the chunk boundary
                search_start = max(start + chunk_size // 2, end - 100)
                search_end = min(end + 100, len(text))

                sentence_ends = []
                for i in range(search_start, search_end):
                    if text[i] in ".!?":
                        sentence_ends.append(i + 1)

                if sentence_ends:
                    # Choose the sentence end closest to the target chunk size
                    best_end = min(sentence_ends, key=lambda x: abs(x - end))
                    end = best_end

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    @staticmethod
    def extract_keywords(text: str, top_k: int = 10) -> List[str]:
        """
        Extract keywords from text.

        Args:
            text: Input text
            top_k: Number of keywords to extract

        Returns:
            List of keywords
        """
        try:
            from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

            # Simple keyword extraction using TF-IDF
            vectorizer = TfidfVectorizer(
                max_features=top_k * 2,
                stop_words=list(ENGLISH_STOP_WORDS),
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.8,
            )

            # Split text into sentences for TF-IDF
            sentences = text.split(".")
            if len(sentences) < 2:
                sentences = [text]

            try:
                tfidf_matrix = vectorizer.fit_transform(sentences)
                feature_names = vectorizer.get_feature_names_out()

                # Get average TF-IDF scores
                mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)

                # Sort by score and return top keywords
                keyword_scores = list(zip(feature_names, mean_scores))
                keyword_scores.sort(key=lambda x: x[1], reverse=True)

                return [keyword for keyword, score in keyword_scores[:top_k]]

            except ValueError:
                # Fallback to simple word frequency
                words = text.lower().split()
                word_freq = {}
                for word in words:
                    if len(word) > 3 and word.isalpha():
                        word_freq[word] = word_freq.get(word, 0) + 1

                sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
                return [word for word, freq in sorted_words[:top_k]]

        except ImportError:
            logger.warning("scikit-learn not available for keyword extraction")
            # Simple fallback
            words = text.lower().split()
            unique_words = list(set(word for word in words if len(word) > 3 and word.isalpha()))
            return unique_words[:top_k]

    @staticmethod
    def generate_text_id(text: str) -> str:
        """
        Generate a unique ID for text content.

        Args:
            text: Input text

        Returns:
            Unique text ID
        """
        content = text.encode("utf-8")
        hash_obj = hashlib.md5(content)
        return hash_obj.hexdigest()


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []

    def time_operation(self, operation_name: str):
        """Decorator to time operations."""

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_message = None
                result = None

                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    success = False
                    error_message = str(e)
                    raise
                finally:
                    end_time = time.time()
                    duration = end_time - start_time

                    metric = PerformanceMetrics(
                        operation_name=operation_name,
                        duration=duration,
                        start_time=start_time,
                        end_time=end_time,
                        success=success,
                        error_message=error_message,
                    )

                    self.metrics.append(metric)
                    logger.debug(f"Operation '{operation_name}' took {duration:.3f}s")

                return result

            return wrapper

        return decorator

    def get_metrics(self, operation_name: Optional[str] = None) -> List[PerformanceMetrics]:
        """Get performance metrics."""
        if operation_name:
            return [m for m in self.metrics if m.operation_name == operation_name]
        return self.metrics

    def get_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary."""
        metrics = self.get_metrics(operation_name)

        if not metrics:
            return {"error": "No metrics found"}

        durations = [m.duration for m in metrics if m.success]
        success_count = sum(1 for m in metrics if m.success)
        total_count = len(metrics)

        if not durations:
            return {"error": "No successful operations"}

        return {
            "operation_name": operation_name or "all",
            "total_operations": total_count,
            "successful_operations": success_count,
            "success_rate": success_count / total_count,
            "avg_duration": statistics.mean(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "std_duration": statistics.stdev(durations) if len(durations) > 1 else 0.0,
            "total_duration": sum(durations),
        }

    def clear_metrics(self):
        """Clear all metrics."""
        self.metrics = []

    def export_metrics(self, filepath: str):
        """Export metrics to JSON file."""
        metrics_data = []
        for metric in self.metrics:
            metrics_data.append(
                {
                    "operation_name": metric.operation_name,
                    "duration": metric.duration,
                    "start_time": metric.start_time,
                    "end_time": metric.end_time,
                    "success": metric.success,
                    "error_message": metric.error_message,
                    "metadata": metric.metadata,
                }
            )

        with open(filepath, "w") as f:
            json.dump(metrics_data, f, indent=2)

        logger.info(f"Exported {len(metrics_data)} metrics to {filepath}")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def timed_operation(operation_name: str):
    """Decorator for timing operations using global monitor."""
    return performance_monitor.time_operation(operation_name)
