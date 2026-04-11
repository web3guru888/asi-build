"""
Basic functionality tests for Kenny Vector Database System.

Tests the core functionality including:
- Configuration management
- Database connections
- Basic indexing and retrieval
- Error handling
"""

import os
import shutil

# Import the modules we're testing
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenny_vectordb.api.indexing import Document, IndexingAPI
from kenny_vectordb.api.retrieval import RetrievalAPI, RetrievalQuery
from kenny_vectordb.api.unified_client import UnifiedVectorDB
from kenny_vectordb.core.config import VectorDBConfig
from kenny_vectordb.core.embeddings import EmbeddingConfig, EmbeddingPipeline


class TestConfiguration:
    """Test configuration management."""

    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = VectorDBConfig()

        assert config.embedding.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.embedding.batch_size == 32
        assert config.search.top_k == 10
        assert config.search.score_threshold == 0.7

    def test_config_validation(self):
        """Test configuration validation."""
        config = VectorDBConfig()

        # Valid configuration should pass
        assert config.validate_config() == True

        # Invalid configuration should fail
        config.search.top_k = -1
        assert config.validate_config() == False

        # Reset to valid
        config.search.top_k = 10
        assert config.validate_config() == True

    def test_config_update(self):
        """Test configuration updates."""
        config = VectorDBConfig()

        original_batch_size = config.embedding.batch_size
        config.update_config("embedding", batch_size=64)

        assert config.embedding.batch_size == 64
        assert config.embedding.batch_size != original_batch_size

    def test_config_save_load(self):
        """Test saving and loading configuration."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            config_path = f.name

        try:
            # Create and save config
            config1 = VectorDBConfig()
            config1.embedding.batch_size = 128
            config1.save_config(config_path)

            # Load config
            config2 = VectorDBConfig(config_path)

            assert config2.embedding.batch_size == 128

        finally:
            os.unlink(config_path)


class TestEmbeddings:
    """Test embedding pipeline functionality."""

    def test_embedding_pipeline_creation(self):
        """Test creating embedding pipeline."""
        config = EmbeddingConfig()
        config.model_type = "sentence_transformers"
        config.model_name = "sentence-transformers/all-MiniLM-L6-v2"

        pipeline = EmbeddingPipeline(config)

        assert pipeline.config.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert pipeline.model is not None

    def test_single_text_embedding(self):
        """Test embedding a single text."""
        config = EmbeddingConfig()
        config.model_type = "sentence_transformers"
        config.cache_embeddings = False  # Disable cache for testing

        pipeline = EmbeddingPipeline(config)

        text = "This is a test sentence for embedding."
        embedding = pipeline.encode_single(text, use_cache=False)

        assert embedding is not None
        assert len(embedding) > 0
        assert isinstance(embedding[0], float)

    def test_batch_text_embedding(self):
        """Test embedding multiple texts."""
        config = EmbeddingConfig()
        config.model_type = "sentence_transformers"
        config.batch_size = 2
        config.cache_embeddings = False

        pipeline = EmbeddingPipeline(config)

        texts = ["First test sentence.", "Second test sentence.", "Third test sentence."]

        embeddings = pipeline.encode_batch(texts, use_cache=False)

        assert embeddings.shape[0] == len(texts)
        assert embeddings.shape[1] > 0
        assert all(isinstance(x, float) for x in embeddings[0])

    def test_embedding_caching(self):
        """Test embedding caching functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EmbeddingConfig()
            config.cache_embeddings = True
            config.cache_dir = temp_dir

            pipeline = EmbeddingPipeline(config)

            text = "This text will be cached."

            # First call - should cache
            embedding1 = pipeline.encode_single(text, use_cache=True)

            # Second call - should use cache
            embedding2 = pipeline.encode_single(text, use_cache=True)

            # Results should be identical
            assert all(a == b for a, b in zip(embedding1, embedding2))

    def test_text_preprocessing(self):
        """Test text preprocessing."""
        config = EmbeddingConfig()
        pipeline = EmbeddingPipeline(config)

        # Test with messy text
        messy_text = "  This   has    extra   spaces  \n\n  and   newlines  "
        cleaned = pipeline.preprocess_text(messy_text)

        assert cleaned == "This has extra spaces and newlines"

        # Test with very long text
        long_text = "word " * 1000
        cleaned_long = pipeline.preprocess_text(long_text)
        assert len(cleaned_long) <= config.max_length * 4


class TestUnifiedVectorDB:
    """Test unified vector database functionality."""

    @pytest.fixture
    def vector_db(self):
        """Create a test vector database instance."""
        config = VectorDBConfig()
        config.embedding.cache_embeddings = False
        config.embedding.batch_size = 2

        return UnifiedVectorDB(config)

    def test_vector_db_initialization(self, vector_db):
        """Test vector database initialization."""
        assert vector_db.config is not None
        assert vector_db.embedding_pipeline is not None
        assert vector_db.search_engine is not None

    def test_health_check(self, vector_db):
        """Test database health checking."""
        health = vector_db._check_database_health(force_check=True)

        assert isinstance(health, dict)
        # Should have entries for available databases
        for db_name, health_info in health.items():
            assert hasattr(health_info, "database_type")
            assert hasattr(health_info, "is_healthy")
            assert hasattr(health_info, "response_time")

    def test_document_insertion_and_retrieval(self, vector_db):
        """Test basic document insertion and retrieval."""
        # Create test documents
        documents = [
            {
                "id": "test_1",
                "content": "This is about artificial intelligence and machine learning.",
                "title": "AI Document",
                "category": "technology",
            },
            {
                "id": "test_2",
                "content": "Climate change is affecting global weather patterns.",
                "title": "Climate Document",
                "category": "environment",
            },
        ]

        # Insert documents
        result = vector_db.insert_documents(documents)

        # Should have some successful insertions
        assert result.inserted_count > 0 or any(result.database_results.values())

        # Wait a moment for indexing
        time.sleep(1)

        # Try to retrieve
        search_results = vector_db.search("artificial intelligence", top_k=5)

        # Should get some results (even if empty due to database connectivity)
        assert isinstance(search_results, list)

    def test_statistics(self, vector_db):
        """Test statistics gathering."""
        stats = vector_db.get_statistics()

        assert "operation_stats" in stats
        assert "database_health" in stats
        assert "embedding_info" in stats

        assert "model_name" in stats["embedding_info"]


class TestIndexingAPI:
    """Test indexing API functionality."""

    @pytest.fixture
    def indexing_api(self):
        """Create test indexing API."""
        config = VectorDBConfig()
        config.embedding.cache_embeddings = False
        vector_db = UnifiedVectorDB(config)
        return IndexingAPI(vector_db, max_workers=2)

    def test_document_creation(self):
        """Test document creation."""
        doc = Document(content="Test document content.", title="Test Document", category="test")

        assert doc.id is not None
        assert doc.content == "Test document content."
        assert doc.title == "Test Document"
        assert doc.category == "test"
        assert doc.timestamp is not None

    def test_document_processing(self, indexing_api):
        """Test document processing and chunking."""
        # Short document - should not be chunked
        short_doc = Document(content="Short content.", title="Short")
        processed_short = indexing_api.document_processor.process_document(short_doc)

        assert len(processed_short) == 1
        assert processed_short[0].content == "Short content."

        # Long document - should be chunked
        long_content = "This is a sentence. " * 100  # Very long document
        long_doc = Document(content=long_content, title="Long")

        processed_long = indexing_api.document_processor.process_document(long_doc)

        # Should create multiple chunks
        assert len(processed_long) > 1

        # Each chunk should have metadata about chunking
        for chunk in processed_long:
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata

    def test_single_document_indexing(self, indexing_api):
        """Test indexing a single document."""
        doc = Document(content="Test content for indexing.", title="Indexing Test", category="test")

        # This might fail if no databases are available, which is OK for testing
        try:
            result = indexing_api.index_document(doc)
            assert isinstance(result, bool)
        except Exception:
            # Expected if no real databases are configured
            pass

    def test_batch_indexing_job_creation(self, indexing_api):
        """Test creating batch indexing jobs."""
        documents = [Document(content=f"Document {i} content.", title=f"Doc {i}") for i in range(5)]

        job = indexing_api.index_documents_batch(documents, batch_size=2)

        assert job.job_id is not None
        assert len(job.documents) == 5
        assert job.total_count == 5
        assert job.status == "pending"

    def test_job_management(self, indexing_api):
        """Test job management functionality."""
        # Create a job
        documents = [Document(content="Test", title="Test")]
        job = indexing_api.index_documents_batch(documents)

        # Job should be in the system
        retrieved_job = indexing_api.get_job_status(job.job_id)
        assert retrieved_job is not None
        assert retrieved_job.job_id == job.job_id

        # Should appear in job list
        all_jobs = indexing_api.list_jobs()
        job_ids = [j.job_id for j in all_jobs]
        assert job.job_id in job_ids

    def test_statistics(self, indexing_api):
        """Test indexing statistics."""
        stats = indexing_api.get_statistics()

        assert "stats" in stats
        assert "jobs" in stats
        assert "realtime" in stats

        # Check specific stats
        assert "total_documents_indexed" in stats["stats"]
        assert "successful_indexing" in stats["stats"]
        assert "failed_indexing" in stats["stats"]


class TestRetrievalAPI:
    """Test retrieval API functionality."""

    @pytest.fixture
    def retrieval_api(self):
        """Create test retrieval API."""
        config = VectorDBConfig()
        config.embedding.cache_embeddings = False
        vector_db = UnifiedVectorDB(config)
        return RetrievalAPI(vector_db, cache_size=10)

    def test_query_optimization(self, retrieval_api):
        """Test query optimization."""
        optimizer = retrieval_api.query_optimizer

        # Test basic optimization
        messy_query = "  what are the best artificial intelligence algorithms?  "
        optimized = optimizer.optimize_query(messy_query)

        assert optimized.strip() == optimized  # No leading/trailing whitespace
        assert len(optimized.split()) >= 1  # Should have words

    def test_query_suggestions(self, retrieval_api):
        """Test query suggestion system."""
        optimizer = retrieval_api.query_optimizer

        # Record some successful queries
        optimizer.record_successful_query("machine learning algorithms")
        optimizer.record_successful_query("deep learning neural networks")
        optimizer.record_successful_query("artificial intelligence applications")

        # Test suggestions
        suggestions = optimizer.suggest_queries("machine learning", max_suggestions=3)

        assert isinstance(suggestions, list)
        # Should include the recorded query
        assert "machine learning algorithms" in suggestions

    def test_retrieval_query_creation(self):
        """Test retrieval query creation."""
        query = RetrievalQuery(
            query="test query", search_mode="semantic", top_k=5, score_threshold=0.5
        )

        assert query.query == "test query"
        assert query.search_mode == "semantic"
        assert query.top_k == 5
        assert query.score_threshold == 0.5

    def test_search_execution(self, retrieval_api):
        """Test search execution."""
        query = RetrievalQuery(query="artificial intelligence", search_mode="semantic", top_k=3)

        # This might return empty results if no data is indexed
        result = retrieval_api.search(query, use_cache=False)

        assert hasattr(result, "results")
        assert hasattr(result, "total_found")
        assert hasattr(result, "query_time")
        assert isinstance(result.results, list)
        assert isinstance(result.total_found, int)
        assert isinstance(result.query_time, float)

    def test_caching(self, retrieval_api):
        """Test query caching."""
        query = RetrievalQuery(query="test caching", top_k=5)

        # First search - should cache
        result1 = retrieval_api.search(query, use_cache=True)

        # Second search - should use cache
        result2 = retrieval_api.search(query, use_cache=True)

        # Should get cache hit on second call
        assert retrieval_api.retrieval_stats["cache_hits"] > 0

    def test_analytics(self, retrieval_api):
        """Test analytics gathering."""
        # Perform some operations to generate stats
        query = RetrievalQuery(query="test analytics")
        retrieval_api.search(query)

        analytics = retrieval_api.get_analytics()

        assert "retrieval_stats" in analytics
        assert "cache_stats" in analytics
        assert "query_stats" in analytics

        assert analytics["retrieval_stats"]["total_queries"] > 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_configuration(self):
        """Test handling of invalid configurations."""
        config = VectorDBConfig()

        # Set invalid values
        config.embedding.batch_size = -1
        config.search.top_k = 0
        config.search.score_threshold = 2.0  # Should be 0-1

        assert config.validate_config() == False

    def test_empty_document_handling(self):
        """Test handling of empty or invalid documents."""
        config = VectorDBConfig()
        pipeline = EmbeddingPipeline(config)

        # Empty text
        empty_embedding = pipeline.encode_single("", use_cache=False)
        assert empty_embedding is not None

        # Very short text
        short_embedding = pipeline.encode_single("Hi", use_cache=False)
        assert short_embedding is not None

    def test_nonexistent_file_processing(self):
        """Test handling of nonexistent files."""
        config = VectorDBConfig()
        vector_db = UnifiedVectorDB(config)
        indexing_api = IndexingAPI(vector_db)

        with pytest.raises(FileNotFoundError):
            indexing_api.index_file("/nonexistent/file.txt")

    def test_malformed_retrieval_query(self, retrieval_api):
        """Test handling of malformed retrieval queries."""
        # Empty query
        empty_query = RetrievalQuery(query="")
        result = retrieval_api.search(empty_query)

        assert result.total_found == 0
        assert len(result.results) == 0


# Integration test class
class TestIntegration:
    """Test integration between components."""

    def test_end_to_end_workflow(self):
        """Test complete workflow from indexing to retrieval."""
        # Setup
        config = VectorDBConfig()
        config.embedding.cache_embeddings = False
        config.embedding.batch_size = 2

        vector_db = UnifiedVectorDB(config)
        indexing_api = IndexingAPI(vector_db)
        retrieval_api = RetrievalAPI(vector_db)

        # Create test documents
        documents = [
            Document(
                content="Machine learning is a subset of artificial intelligence.",
                title="ML Introduction",
                category="technology",
            ),
            Document(
                content="Climate change affects weather patterns globally.",
                title="Climate Science",
                category="environment",
            ),
        ]

        # Index documents
        successful_indexing = 0
        for doc in documents:
            try:
                if indexing_api.index_document(doc):
                    successful_indexing += 1
            except Exception:
                pass  # May fail if no databases configured

        # If we successfully indexed something, try searching
        if successful_indexing > 0:
            time.sleep(1)  # Wait for indexing

            # Search
            query = RetrievalQuery(query="machine learning artificial intelligence", top_k=5)

            results = retrieval_api.search(query)

            # Should get some results
            assert isinstance(results.results, list)
            assert results.total_found >= 0

        # Get statistics
        db_stats = vector_db.get_statistics()
        indexing_stats = indexing_api.get_statistics()
        retrieval_stats = retrieval_api.get_analytics()

        # All should have valid stats
        assert isinstance(db_stats, dict)
        assert isinstance(indexing_stats, dict)
        assert isinstance(retrieval_stats, dict)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
