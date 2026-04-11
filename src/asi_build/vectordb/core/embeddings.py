"""
Embedding generation pipeline for Kenny Vector Database System

This module provides comprehensive embedding generation capabilities with support for:
- Multiple embedding models (Sentence Transformers, OpenAI, Cohere, HuggingFace)
- Batch processing and caching
- Text preprocessing and normalization
- Multi-modal embeddings (text, images, code)
"""

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch

# Import embedding libraries
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import cohere

    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False

try:
    from transformers import AutoModel, AutoTokenizer

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from .config import EmbeddingConfig

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Container for embedding results."""

    embeddings: np.ndarray
    texts: List[str]
    model_name: str
    dimension: int
    processing_time: float
    cached: List[bool]


class BaseEmbeddingModel(ABC):
    """Abstract base class for embedding models."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.model_name = config.model_name

    @abstractmethod
    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        """Encode texts to embeddings."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if model is available."""
        pass


class SentenceTransformerModel(BaseEmbeddingModel):
    """Sentence Transformers embedding model."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not available. Install with: pip install sentence-transformers"
            )

        self.model = SentenceTransformer(self.model_name)

    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        """Encode texts using Sentence Transformers."""
        embeddings = self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize_embeddings,
            convert_to_numpy=True,
            **kwargs,
        )
        return embeddings

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def is_available(self) -> bool:
        """Check if model is available."""
        return SENTENCE_TRANSFORMERS_AVAILABLE


class OpenAIEmbeddingModel(BaseEmbeddingModel):
    """OpenAI embedding model."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        if not OPENAI_AVAILABLE:
            raise ImportError("openai not available. Install with: pip install openai")

        if not config.api_key:
            raise ValueError("OpenAI API key required")

        openai.api_key = config.api_key

        # Map model names to dimensions
        self.model_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }

    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        """Encode texts using OpenAI embeddings."""
        embeddings = []

        # Process in batches
        batch_size = min(self.config.batch_size, 2048)  # OpenAI batch limit

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            response = openai.Embedding.create(model=self.model_name, input=batch, **kwargs)

            batch_embeddings = [item["embedding"] for item in response["data"]]
            embeddings.extend(batch_embeddings)

        return np.array(embeddings)

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model_dimensions.get(self.model_name, 1536)

    def is_available(self) -> bool:
        """Check if model is available."""
        return OPENAI_AVAILABLE and bool(self.config.api_key)


class CohereEmbeddingModel(BaseEmbeddingModel):
    """Cohere embedding model."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        if not COHERE_AVAILABLE:
            raise ImportError("cohere not available. Install with: pip install cohere")

        if not config.api_key:
            raise ValueError("Cohere API key required")

        self.client = cohere.Client(config.api_key)

    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        """Encode texts using Cohere embeddings."""
        response = self.client.embed(texts=texts, model=self.model_name, **kwargs)

        embeddings = np.array(response.embeddings)

        if self.config.normalize_embeddings:
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        return embeddings

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        # Most Cohere models use 4096 dimensions
        return 4096

    def is_available(self) -> bool:
        """Check if model is available."""
        return COHERE_AVAILABLE and bool(self.config.api_key)


class HuggingFaceEmbeddingModel(BaseEmbeddingModel):
    """HuggingFace Transformers embedding model."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers not available. Install with: pip install transformers")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)

        # Use GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        """Encode texts using HuggingFace Transformers."""
        embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]

            # Tokenize
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.config.max_length,
                return_tensors="pt",
            ).to(self.device)

            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)

                # Mean pooling
                attention_mask = inputs["attention_mask"]
                token_embeddings = outputs.last_hidden_state

                input_mask_expanded = (
                    attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                )
                batch_embeddings = torch.sum(
                    token_embeddings * input_mask_expanded, 1
                ) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

                if self.config.normalize_embeddings:
                    batch_embeddings = torch.nn.functional.normalize(batch_embeddings, p=2, dim=1)

                embeddings.append(batch_embeddings.cpu().numpy())

        return np.vstack(embeddings)

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.config.hidden_size

    def is_available(self) -> bool:
        """Check if model is available."""
        return TRANSFORMERS_AVAILABLE


class EmbeddingCache:
    """Cache for embeddings to avoid recomputation."""

    def __init__(self, cache_dir: str, max_size: int = 10000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size = max_size
        self.cache_file = self.cache_dir / "embeddings_cache.json"

        # Load existing cache
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk."""
        if self.cache_file.exists():
            with open(self.cache_file, "r") as f:
                self.cache = json.load(f)
        else:
            self.cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        # Limit cache size
        if len(self.cache) > self.max_size:
            # Remove oldest entries (simple FIFO)
            items = list(self.cache.items())
            self.cache = dict(items[-self.max_size :])

        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def _get_cache_key(self, text: str, model_name: str) -> str:
        """Generate cache key for text and model."""
        content = f"{model_name}:{text}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """Get embedding from cache."""
        cache_key = self._get_cache_key(text, model_name)

        if cache_key in self.cache:
            embedding_path = self.cache_dir / f"{cache_key}.npy"
            if embedding_path.exists():
                return np.load(embedding_path)

        return None

    def set(self, text: str, model_name: str, embedding: np.ndarray):
        """Set embedding in cache."""
        cache_key = self._get_cache_key(text, model_name)
        embedding_path = self.cache_dir / f"{cache_key}.npy"

        # Save embedding
        np.save(embedding_path, embedding)

        # Update cache index
        self.cache[cache_key] = {
            "text": text,
            "model_name": model_name,
            "embedding_path": str(embedding_path),
        }

        self._save_cache()

    def clear(self):
        """Clear all cache."""
        for cache_key in self.cache:
            embedding_path = self.cache_dir / f"{cache_key}.npy"
            if embedding_path.exists():
                embedding_path.unlink()

        self.cache = {}
        self._save_cache()


class EmbeddingPipeline:
    """Main embedding generation pipeline."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config

        # Initialize model
        self.model = self._create_model()

        # Initialize cache if enabled
        if config.cache_embeddings:
            self.cache = EmbeddingCache(config.cache_dir)
        else:
            self.cache = None

    def _create_model(self) -> BaseEmbeddingModel:
        """Create embedding model based on configuration."""
        model_type = self.config.model_type.lower()

        if model_type == "sentence_transformers":
            return SentenceTransformerModel(self.config)
        elif model_type == "openai":
            return OpenAIEmbeddingModel(self.config)
        elif model_type == "cohere":
            return CohereEmbeddingModel(self.config)
        elif model_type == "huggingface":
            return HuggingFaceEmbeddingModel(self.config)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

    def preprocess_text(self, text: str) -> str:
        """Preprocess text before embedding."""
        # Basic text cleaning
        text = text.strip()

        # Remove excessive whitespace
        import re

        text = re.sub(r"\s+", " ", text)

        # Truncate if too long
        if len(text) > self.config.max_length * 4:  # Rough character limit
            text = text[: self.config.max_length * 4]

        return text

    def generate_embeddings(
        self, texts: Union[str, List[str]], use_cache: bool = True
    ) -> EmbeddingResult:
        """
        Generate embeddings for texts.

        Args:
            texts: Single text or list of texts
            use_cache: Whether to use cache

        Returns:
            EmbeddingResult containing embeddings and metadata
        """
        import time

        start_time = time.time()

        # Ensure texts is a list
        if isinstance(texts, str):
            texts = [texts]

        # Preprocess texts
        processed_texts = [self.preprocess_text(text) for text in texts]

        embeddings = []
        cached = []
        uncached_texts = []
        uncached_indices = []

        # Check cache first
        if use_cache and self.cache:
            for i, text in enumerate(processed_texts):
                cached_embedding = self.cache.get(text, self.model.model_name)
                if cached_embedding is not None:
                    embeddings.append(cached_embedding)
                    cached.append(True)
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
                    embeddings.append(None)  # Placeholder
                    cached.append(False)
        else:
            uncached_texts = processed_texts
            uncached_indices = list(range(len(processed_texts)))
            embeddings = [None] * len(processed_texts)
            cached = [False] * len(processed_texts)

        # Generate embeddings for uncached texts
        if uncached_texts:
            logger.info(
                f"Generating embeddings for {len(uncached_texts)} texts using {self.model.model_name}"
            )

            uncached_embeddings = self.model.encode(uncached_texts)

            # Cache new embeddings
            if self.cache:
                for text, embedding in zip(uncached_texts, uncached_embeddings):
                    self.cache.set(text, self.model.model_name, embedding)

            # Fill in embeddings
            for i, idx in enumerate(uncached_indices):
                embeddings[idx] = uncached_embeddings[i]

        # Convert to numpy array
        final_embeddings = np.array(embeddings)

        processing_time = time.time() - start_time

        return EmbeddingResult(
            embeddings=final_embeddings,
            texts=processed_texts,
            model_name=self.model.model_name,
            dimension=self.model.get_dimension(),
            processing_time=processing_time,
            cached=cached,
        )

    def encode_single(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Input text
            use_cache: Whether to use cache

        Returns:
            Embedding vector
        """
        result = self.generate_embeddings(text, use_cache=use_cache)
        return result.embeddings[0]

    def encode_batch(self, texts: List[str], use_cache: bool = True) -> np.ndarray:
        """
        Generate embeddings for batch of texts.

        Args:
            texts: List of input texts
            use_cache: Whether to use cache

        Returns:
            Array of embedding vectors
        """
        result = self.generate_embeddings(texts, use_cache=use_cache)
        return result.embeddings

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        return {
            "model_name": self.model.model_name,
            "model_type": self.config.model_type,
            "dimension": self.model.get_dimension(),
            "batch_size": self.config.batch_size,
            "max_length": self.config.max_length,
            "normalize_embeddings": self.config.normalize_embeddings,
            "cache_enabled": self.config.cache_embeddings,
            "available": self.model.is_available(),
        }

    def clear_cache(self):
        """Clear embedding cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Embedding cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.cache:
            return {"cache_enabled": False}

        cache_size = len(self.cache.cache)
        cache_dir_size = sum(f.stat().st_size for f in self.cache.cache_dir.glob("*.npy"))

        return {
            "cache_enabled": True,
            "cache_size": cache_size,
            "cache_dir_size_mb": cache_dir_size / (1024 * 1024),
            "cache_dir": str(self.cache.cache_dir),
        }
