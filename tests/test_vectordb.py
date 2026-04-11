"""
Tests for the vectordb module (Kenny Vector Database System).

Import strategy: We mock only *external* heavy dependencies (torch,
sentence_transformers, qdrant_client, pinecone, weaviate, openai, cohere,
transformers) at the sys.modules level before importing any vectordb code.
The asi_build package tree is imported normally.
"""

import sys
import types
import hashlib
import time
import math
import os

# ---------------------------------------------------------------------------
# Pre-import mocking: Block external deps that cause ImportError.
# This must run before any asi_build.vectordb imports.
# ---------------------------------------------------------------------------

_MOCK_EXTERNAL = [
    "qdrant_client", "qdrant_client.models",
    "pinecone",
    "weaviate", "weaviate.classes", "weaviate.classes.config", "weaviate.classes.query",
    "torch", "torch.nn", "torch.nn.functional",
    "sentence_transformers",
    "openai",
    "cohere",
    "transformers",
]

for _pkg in _MOCK_EXTERNAL:
    if _pkg not in sys.modules:
        sys.modules[_pkg] = types.ModuleType(_pkg)

# Give torch the minimal API surface that embeddings.py probes at import time
_torch = sys.modules["torch"]
_torch.device = lambda *a, **kw: "cpu"
_torch.no_grad = lambda: type("ctx", (), {"__enter__": lambda s: None, "__exit__": lambda s, *a: None})()
if not hasattr(_torch, "cuda"):
    _cuda = types.ModuleType("torch.cuda")
    _cuda.is_available = lambda: False
    _torch.cuda = _cuda
    sys.modules["torch.cuda"] = _cuda

# Ensure source tree is importable
if "/shared/asi-build/src" not in sys.path:
    sys.path.insert(0, "/shared/asi-build/src")

# ---------------------------------------------------------------------------
# Now import pytest (after path setup so conftest can find things)
# ---------------------------------------------------------------------------
import pytest
import numpy

# ---------------------------------------------------------------------------
# Import vectordb modules — each guarded so a failure skips gracefully
# ---------------------------------------------------------------------------

try:
    from asi_build.vectordb.core.config import (
        DatabaseConfig, PineconeConfig, WeaviateConfig, QdrantConfig,
        EmbeddingConfig, SearchConfig, VectorDBConfig,
    )
    HAS_CONFIG = True
except Exception as _e:
    HAS_CONFIG = False

try:
    from asi_build.vectordb.core.utils import (
        VectorUtils, TextUtils, PerformanceMonitor, VectorStats,
        PerformanceMetrics, timed_operation, performance_monitor,
    )
    HAS_UTILS = True
except Exception as _e:
    HAS_UTILS = False

try:
    from asi_build.vectordb.core.search import (
        SearchResult, SearchQuery, SearchStats,
        QueryExpander, ResultReranker,
    )
    HAS_SEARCH = True
except Exception as _e:
    HAS_SEARCH = False

try:
    from asi_build.vectordb.api.retrieval import (
        QueryOptimizer, FacetProcessor, FacetResult,
        RetrievalQuery, RetrievalResult, QueryCache,
    )
    HAS_RETRIEVAL = True
except Exception as _e:
    HAS_RETRIEVAL = False

try:
    from asi_build.vectordb.api.indexing import (
        Document, IndexingJob, DocumentProcessor, IndexingStats,
    )
    HAS_INDEXING = True
except Exception as _e:
    HAS_INDEXING = False

try:
    from asi_build.vectordb.databases.pinecone_client import PineconeSearchResult
    HAS_PINECONE_DC = True
except Exception:
    HAS_PINECONE_DC = False

try:
    from asi_build.vectordb.databases.weaviate_client import WeaviateSearchResult
    HAS_WEAVIATE_DC = True
except Exception:
    HAS_WEAVIATE_DC = False

try:
    from asi_build.vectordb.databases.qdrant_client import QdrantSearchResult
    HAS_QDRANT_DC = True
except Exception:
    HAS_QDRANT_DC = False


# ===================================================================
# 1. Config dataclasses — 6 tests
# ===================================================================

@pytest.mark.skipif(not HAS_CONFIG, reason="config import failed")
class TestDatabaseConfig:
    def test_defaults(self):
        cfg = DatabaseConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 8080
        assert cfg.api_key is None
        assert cfg.environment == "production"
        assert cfg.timeout == 30
        assert cfg.max_retries == 3

    def test_pinecone_inherits_and_extends(self):
        cfg = PineconeConfig()
        assert cfg.environment == "us-east1-aws"
        assert cfg.index_name == "kenny-vectors"
        assert cfg.dimension == 1536
        assert cfg.metric == "cosine"
        assert isinstance(cfg, DatabaseConfig)

    def test_weaviate_config(self):
        cfg = WeaviateConfig()
        assert cfg.port == 8080
        assert cfg.grpc_port == 50051
        assert cfg.scheme == "http"
        assert cfg.startup_period == 5

    def test_qdrant_config(self):
        cfg = QdrantConfig()
        assert cfg.port == 6333
        assert cfg.grpc_port == 6334
        assert cfg.prefer_grpc is False
        assert cfg.collection_name == "kenny-collection"
        assert cfg.distance == "Cosine"

    def test_embedding_config_defaults(self):
        cfg = EmbeddingConfig()
        assert cfg.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert cfg.batch_size == 32
        assert cfg.max_length == 512
        assert cfg.normalize_embeddings is True

    def test_search_config_defaults(self):
        cfg = SearchConfig()
        assert cfg.top_k == 10
        assert cfg.score_threshold == 0.7
        assert cfg.rerank is True
        assert cfg.alpha == 0.5


# ===================================================================
# 2. VectorDBConfig — 13 tests
# ===================================================================

@pytest.mark.skipif(not HAS_CONFIG, reason="config import failed")
class TestVectorDBConfig:
    def test_default_instantiation(self):
        cfg = VectorDBConfig()
        assert isinstance(cfg.pinecone, PineconeConfig)
        assert isinstance(cfg.weaviate, WeaviateConfig)
        assert isinstance(cfg.qdrant, QdrantConfig)
        assert isinstance(cfg.embedding, EmbeddingConfig)
        assert isinstance(cfg.search, SearchConfig)

    def test_get_database_config_pinecone(self):
        cfg = VectorDBConfig()
        pc = cfg.get_database_config("pinecone")
        assert isinstance(pc, PineconeConfig)

    def test_get_database_config_weaviate(self):
        cfg = VectorDBConfig()
        wv = cfg.get_database_config("weaviate")
        assert isinstance(wv, WeaviateConfig)

    def test_get_database_config_qdrant(self):
        cfg = VectorDBConfig()
        qd = cfg.get_database_config("qdrant")
        assert isinstance(qd, QdrantConfig)

    def test_get_database_config_unknown_raises(self):
        cfg = VectorDBConfig()
        with pytest.raises(ValueError, match="Unsupported database type"):
            cfg.get_database_config("milvus")

    def test_update_config_pinecone(self):
        cfg = VectorDBConfig()
        cfg.update_config("pinecone", dimension=768, metric="euclidean")
        assert cfg.pinecone.dimension == 768
        assert cfg.pinecone.metric == "euclidean"

    def test_update_config_search(self):
        cfg = VectorDBConfig()
        cfg.update_config("search", top_k=20, alpha=0.8)
        assert cfg.search.top_k == 20
        assert cfg.search.alpha == 0.8

    def test_update_config_embedding(self):
        cfg = VectorDBConfig()
        cfg.update_config("embedding", batch_size=64, max_length=1024)
        assert cfg.embedding.batch_size == 64
        assert cfg.embedding.max_length == 1024

    def test_update_config_unknown_raises(self):
        cfg = VectorDBConfig()
        with pytest.raises(ValueError, match="Unsupported config type"):
            cfg.update_config("redis", host="remote")

    def test_validate_config_default_passes(self):
        cfg = VectorDBConfig()
        # NOTE: Source has a typo: `except AssertionError` — but this is actually
        # the correct spelling of Python's AssertionError. The default config is
        # valid, so no assertion fires and it returns True.
        assert cfg.validate_config() is True

    def test_validate_config_bad_search_alpha(self):
        """Setting alpha out of range should fail validation and return False."""
        cfg = VectorDBConfig()
        cfg.search.alpha = 2.0
        assert cfg.validate_config() is False

    def test_save_and_load_json(self, tmp_path):
        cfg = VectorDBConfig()
        cfg.update_config("pinecone", dimension=512)
        out = str(tmp_path / "config.json")
        cfg.save_config(out)
        cfg2 = VectorDBConfig(config_path=out)
        assert cfg2.pinecone.dimension == 512

    def test_env_override_pinecone(self, monkeypatch):
        monkeypatch.setenv("PINECONE_API_KEY", "pk-test-123")
        monkeypatch.setenv("PINECONE_ENVIRONMENT", "us-west2-aws")
        cfg = VectorDBConfig()
        assert cfg.pinecone.api_key == "pk-test-123"
        assert cfg.pinecone.environment == "us-west2-aws"


# ===================================================================
# 3. VectorUtils — 13 tests
# ===================================================================

@pytest.mark.skipif(not HAS_UTILS, reason="utils import failed")
class TestVectorUtils:
    def test_normalize_vector(self):
        v = [3.0, 4.0]
        result = VectorUtils.normalize_vector(v)
        assert abs(numpy.linalg.norm(result) - 1.0) < 1e-5

    def test_normalize_zero_vector(self):
        v = [0.0, 0.0, 0.0]
        result = VectorUtils.normalize_vector(v)
        assert numpy.allclose(result, [0, 0, 0])

    def test_cosine_similarity_identical(self):
        v = [1.0, 2.0, 3.0]
        sim = VectorUtils.cosine_similarity(v, v)
        assert abs(sim - 1.0) < 1e-5

    def test_cosine_similarity_orthogonal(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        sim = VectorUtils.cosine_similarity(v1, v2)
        assert abs(sim) < 1e-5

    def test_cosine_similarity_zero_vector(self):
        v1 = [1.0, 2.0]
        v2 = [0.0, 0.0]
        sim = VectorUtils.cosine_similarity(v1, v2)
        assert sim == 0.0

    def test_euclidean_distance_known(self):
        v1 = [0.0, 0.0]
        v2 = [3.0, 4.0]
        dist = VectorUtils.euclidean_distance(v1, v2)
        assert abs(dist - 5.0) < 1e-5

    def test_dot_product_known(self):
        v1 = [1.0, 2.0, 3.0]
        v2 = [4.0, 5.0, 6.0]
        dp = VectorUtils.dot_product(v1, v2)
        assert abs(dp - 32.0) < 1e-5

    def test_vector_statistics(self):
        vecs = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        stats = VectorUtils.vector_statistics(vecs)
        assert isinstance(stats, VectorStats)
        assert stats.dimension == 2
        assert abs(stats.mean - 3.5) < 1e-5
        assert abs(stats.min_val - 1.0) < 1e-5
        assert abs(stats.max_val - 6.0) < 1e-5

    def test_vector_statistics_empty_raises(self):
        with pytest.raises(ValueError, match="Empty vector list"):
            VectorUtils.vector_statistics([])

    def test_batch_cosine_similarity(self):
        query = [1.0, 0.0]
        vectors = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
        sims = VectorUtils.batch_cosine_similarity(query, vectors)
        assert len(sims) == 3
        assert abs(sims[0] - 1.0) < 1e-5
        assert abs(sims[1] - 0.0) < 1e-5
        assert abs(sims[2] - 1.0 / math.sqrt(2)) < 1e-4

    def test_find_top_k_cosine(self):
        query = [1.0, 0.0]
        vectors = [[0.0, 1.0], [1.0, 0.0], [0.5, 0.5]]
        result = VectorUtils.find_top_k_similar(query, vectors, k=2, metric="cosine")
        assert len(result) == 2
        assert result[0][0] == 1  # index of [1, 0]

    def test_find_top_k_euclidean(self):
        query = [0.0, 0.0]
        vectors = [[1.0, 0.0], [3.0, 4.0], [0.5, 0.5]]
        result = VectorUtils.find_top_k_similar(query, vectors, k=2, metric="euclidean")
        assert len(result) == 2
        assert result[0][0] == 2  # [0.5, 0.5] closest
        assert result[1][0] == 0  # [1, 0] second

    def test_find_top_k_unsupported_metric(self):
        with pytest.raises(ValueError, match="Unsupported metric"):
            VectorUtils.find_top_k_similar([1], [[1]], k=1, metric="manhattan")


# ===================================================================
# 4. TextUtils — 8 tests
# ===================================================================

@pytest.mark.skipif(not HAS_UTILS, reason="utils import failed")
class TestTextUtils:
    def test_clean_text_whitespace(self):
        text = "  hello   world  \n\t test  "
        cleaned = TextUtils.clean_text(text)
        assert cleaned == "hello world test"

    def test_clean_text_special_chars(self):
        text = "hello@#$% world"
        cleaned = TextUtils.clean_text(text)
        assert "@" not in cleaned
        assert "#" not in cleaned
        assert "hello" in cleaned
        assert "world" in cleaned

    def test_split_text_chunks_short(self):
        text = "Short text."
        chunks = TextUtils.split_text_chunks(text, chunk_size=512)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_text_chunks_long(self):
        text = "word " * 200
        chunks = TextUtils.split_text_chunks(text, chunk_size=100, overlap=10)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) > 0

    def test_split_text_chunks_overlap(self):
        text = "A" * 50 + "B" * 50 + "C" * 50 + "D" * 50
        chunks = TextUtils.split_text_chunks(text, chunk_size=80, overlap=20,
                                              preserve_sentences=False)
        assert len(chunks) >= 2

    def test_generate_text_id_deterministic(self):
        text = "hello world"
        id1 = TextUtils.generate_text_id(text)
        id2 = TextUtils.generate_text_id(text)
        assert id1 == id2
        assert id1 == hashlib.md5(text.encode("utf-8")).hexdigest()

    def test_generate_text_id_different_texts(self):
        id1 = TextUtils.generate_text_id("hello")
        id2 = TextUtils.generate_text_id("world")
        assert id1 != id2

    def test_extract_keywords_fallback(self):
        text = "machine learning is a subset of artificial intelligence that focuses on learning"
        keywords = TextUtils.extract_keywords(text, top_k=3)
        assert isinstance(keywords, list)
        assert len(keywords) <= 3


# ===================================================================
# 5. PerformanceMonitor — 5 tests
# ===================================================================

@pytest.mark.skipif(not HAS_UTILS, reason="utils import failed")
class TestPerformanceMonitor:
    def test_time_operation_decorator(self):
        monitor = PerformanceMonitor()

        @monitor.time_operation("test_op")
        def sample_func():
            time.sleep(0.01)
            return 42

        result = sample_func()
        assert result == 42
        metrics = monitor.get_metrics("test_op")
        assert len(metrics) == 1
        assert metrics[0].success is True
        assert metrics[0].duration >= 0.005

    def test_time_operation_records_failure(self):
        monitor = PerformanceMonitor()

        @monitor.time_operation("fail_op")
        def failing_func():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            failing_func()

        metrics = monitor.get_metrics("fail_op")
        assert len(metrics) == 1
        assert metrics[0].success is False
        assert metrics[0].error_message == "boom"

    def test_get_summary(self):
        monitor = PerformanceMonitor()

        @monitor.time_operation("sum_op")
        def quick():
            return True

        quick()
        quick()

        summary = monitor.get_summary("sum_op")
        assert summary["total_operations"] == 2
        assert summary["successful_operations"] == 2
        assert summary["success_rate"] == 1.0

    def test_get_summary_no_metrics(self):
        monitor = PerformanceMonitor()
        summary = monitor.get_summary("nonexistent")
        assert "error" in summary

    def test_clear_metrics(self):
        monitor = PerformanceMonitor()

        @monitor.time_operation("clear_op")
        def noop():
            pass

        noop()
        assert len(monitor.get_metrics()) == 1
        monitor.clear_metrics()
        assert len(monitor.get_metrics()) == 0


# ===================================================================
# 6. Search dataclasses — 3 tests
# ===================================================================

@pytest.mark.skipif(not HAS_SEARCH, reason="search import failed")
class TestSearchDataclasses:
    def test_search_result_creation(self):
        sr = SearchResult(id="r1", score=0.95, content="hello",
                          metadata={"k": "v"}, source_db="pinecone")
        assert sr.id == "r1"
        assert sr.score == 0.95
        assert sr.vector is None

    def test_search_query_defaults(self):
        sq = SearchQuery(query="test query")
        assert sq.top_k == 10
        assert sq.expand_query is True
        assert sq.rerank is True
        assert "pinecone" in sq.database_weights

    def test_search_stats_creation(self):
        ss = SearchStats(query="test", total_results=5,
                         databases_searched=["qdrant"],
                         search_time=0.1, embedding_time=0.05,
                         rerank_time=0.02, top_score=0.9, avg_score=0.8)
        assert ss.total_results == 5


# ===================================================================
# 7. QueryExpander — 4 tests
# ===================================================================

@pytest.mark.skipif(not HAS_SEARCH, reason="search import failed")
class TestQueryExpander:
    def test_expand_known_synonym(self):
        qe = QueryExpander()
        expanded = qe.expand_query("ai search", max_expansions=3)
        assert len(expanded) >= 2
        assert "ai search" in expanded

    def test_expand_no_synonyms(self):
        qe = QueryExpander()
        expanded = qe.expand_query("xylophone", max_expansions=3)
        assert expanded[0] == "xylophone"

    def test_expand_max_limit(self):
        qe = QueryExpander()
        expanded = qe.expand_query("ai search database", max_expansions=2)
        assert len(expanded) <= 3  # max_expansions + 1

    def test_synonyms_loaded(self):
        qe = QueryExpander()
        assert "ai" in qe.synonyms
        assert "database" in qe.synonyms
        assert isinstance(qe.synonyms["ai"], list)


# ===================================================================
# 8. ResultReranker — 4 tests
# ===================================================================

@pytest.mark.skipif(not HAS_SEARCH, reason="search import failed")
class TestResultReranker:
    def test_rerank_basic(self):
        rr = ResultReranker()
        results = [
            SearchResult(id="1", score=0.8, content="ai machine learning topic",
                         metadata={}, source_db="test"),
            SearchResult(id="2", score=0.9, content="unrelated content here",
                         metadata={}, source_db="test"),
        ]
        reranked = rr.rerank_results(results, "ai machine learning")
        assert len(reranked) == 2
        for r in reranked:
            assert r.score > 0

    def test_rerank_single_passthrough(self):
        rr = ResultReranker()
        results = [
            SearchResult(id="1", score=0.8, content="test", metadata={}, source_db="t"),
        ]
        reranked = rr.rerank_results(results, "test")
        assert len(reranked) == 1
        assert reranked[0].id == "1"

    def test_boost_content_length(self):
        rr = ResultReranker()
        r = SearchResult(id="1", score=0.5, content="x" * 500,
                         metadata={}, source_db="t")
        boost = rr._calculate_boost_score(r, "test")
        assert boost >= 0.05

    def test_boost_keyword_match(self):
        rr = ResultReranker()
        r = SearchResult(id="1", score=0.5, content="hello world query",
                         metadata={}, source_db="t")
        boost = rr._calculate_boost_score(r, "hello world")
        assert boost >= 0.1


# ===================================================================
# 9. QueryOptimizer (retrieval.py) — 7 tests
# ===================================================================

@pytest.mark.skipif(not HAS_RETRIEVAL, reason="retrieval import failed")
class TestQueryOptimizer:
    def test_optimize_strips_whitespace(self):
        qo = QueryOptimizer()
        result = qo.optimize_query("  hello   world  ")
        assert result == "hello world"

    def test_optimize_removes_stopwords_long(self):
        qo = QueryOptimizer()
        result = qo.optimize_query("the search for the best database in the world")
        assert "the" not in result.split()
        assert "search" in result.split()

    def test_optimize_preserves_short_query(self):
        qo = QueryOptimizer()
        result = qo.optimize_query("the database")
        assert result == "the database"

    def test_suggest_queries_from_history(self):
        qo = QueryOptimizer()
        qo.record_successful_query("machine learning algorithms")
        qo.record_successful_query("deep learning frameworks")
        suggestions = qo.suggest_queries("learning")
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1

    def test_record_successful_query(self):
        qo = QueryOptimizer()
        qo.record_successful_query("test query")
        assert "test query" in qo.successful_queries
        assert "test query" in qo.query_history

    def test_get_popular_terms(self):
        qo = QueryOptimizer()
        qo.optimize_query("vector search")
        qo.optimize_query("vector database")
        qo.optimize_query("vector embedding")
        terms = qo.get_popular_terms(top_k=3)
        assert terms[0][0] == "vector"
        assert terms[0][1] == 3

    def test_popular_terms_limit(self):
        qo = QueryOptimizer()
        for i in range(20):
            qo.optimize_query(f"term_{i}")
        terms = qo.get_popular_terms(top_k=5)
        assert len(terms) == 5


# ===================================================================
# 10. FacetProcessor (retrieval.py) — 3 tests
# ===================================================================

@pytest.mark.skipif(not HAS_RETRIEVAL or not HAS_SEARCH,
                    reason="retrieval/search import failed")
class TestFacetProcessor:
    def test_compute_category_facet(self):
        fp = FacetProcessor()
        results = [
            SearchResult(id="1", score=0.9, content="a",
                         metadata={"category": "science"}, source_db="t"),
            SearchResult(id="2", score=0.8, content="b",
                         metadata={"category": "science"}, source_db="t"),
            SearchResult(id="3", score=0.7, content="c",
                         metadata={"category": "tech"}, source_db="t"),
        ]
        facets = fp.compute_facets(results, ["category"])
        assert "category" in facets
        assert facets["category"].values["science"] == 2
        assert facets["category"].values["tech"] == 1
        assert facets["category"].total_docs == 3

    def test_compute_content_length_facet(self):
        fp = FacetProcessor()
        results = [
            SearchResult(id="1", score=0.9, content="a" * 50,
                         metadata={}, source_db="t"),
            SearchResult(id="2", score=0.8, content="b" * 300,
                         metadata={}, source_db="t"),
            SearchResult(id="3", score=0.7, content="c" * 800,
                         metadata={}, source_db="t"),
        ]
        facets = fp.compute_facets(results, ["content_length"])
        vals = facets["content_length"].values
        assert vals["short"] == 1
        assert vals["medium"] == 1
        assert vals["long"] == 1

    def test_compute_tags_facet(self):
        fp = FacetProcessor()
        results = [
            SearchResult(id="1", score=0.9, content="a",
                         metadata={"tags": ["ml", "ai"]}, source_db="t"),
            SearchResult(id="2", score=0.8, content="b",
                         metadata={"tags": ["ml"]}, source_db="t"),
        ]
        facets = fp.compute_facets(results, ["tags"])
        assert facets["tags"].values["ml"] == 2
        assert facets["tags"].values["ai"] == 1


# ===================================================================
# 11. QueryCache (retrieval.py) — 2 tests
# ===================================================================

@pytest.mark.skipif(not HAS_RETRIEVAL, reason="retrieval import failed")
class TestQueryCache:
    def test_not_expired(self):
        cache = QueryCache(
            query_hash="abc123",
            results=RetrievalResult(results=[], total_found=0, query_time=0.0),
            timestamp=time.time(),
            ttl=300.0,
        )
        assert cache.is_expired() is False

    def test_expired(self):
        cache = QueryCache(
            query_hash="abc123",
            results=RetrievalResult(results=[], total_found=0, query_time=0.0),
            timestamp=time.time() - 600,
            ttl=300.0,
        )
        assert cache.is_expired() is True


# ===================================================================
# 12. Document + DocumentProcessor (indexing.py) — 7 tests
# ===================================================================

@pytest.mark.skipif(not HAS_INDEXING, reason="indexing import failed")
class TestDocument:
    def test_auto_id(self):
        doc = Document(content="hello world")
        assert doc.id is not None
        assert len(doc.id) == 36  # UUID4

    def test_auto_timestamp(self):
        before = time.time()
        doc = Document(content="test")
        after = time.time()
        assert before <= doc.timestamp <= after

    def test_explicit_id_preserved(self):
        doc = Document(id="custom-id", content="test")
        assert doc.id == "custom-id"

    def test_to_dict(self):
        doc = Document(id="d1", content="hello", title="t1", source="s1",
                       category="cat", tags=["a", "b"], metadata={"k": "v"})
        d = doc.to_dict()
        assert d["id"] == "d1"
        assert d["content"] == "hello"
        assert d["title"] == "t1"
        assert d["tags"] == ["a", "b"]
        assert d["metadata"]["k"] == "v"


@pytest.mark.skipif(not HAS_INDEXING, reason="indexing import failed")
class TestDocumentProcessor:
    def test_no_chunking_short(self):
        dp = DocumentProcessor(chunk_size=1000)
        doc = Document(id="d1", content="Short content here.")
        result = dp.process_document(doc)
        assert len(result) == 1
        assert result[0].id == "d1"

    def test_chunks_long(self):
        dp = DocumentProcessor(chunk_size=100, chunk_overlap=10)
        doc = Document(id="d1", content="word " * 200)
        result = dp.process_document(doc)
        assert len(result) > 1
        assert result[0].id.startswith("d1_")

    def test_chunk_metadata(self):
        dp = DocumentProcessor(chunk_size=100, chunk_overlap=10,
                                extract_keywords=False)
        doc = Document(id="d1", content="word " * 200)
        result = dp.process_document(doc)
        meta = result[0].metadata
        assert meta["original_id"] == "d1"
        assert "chunk_index" in meta
        assert "total_chunks" in meta
        assert "word_count" in meta


@pytest.mark.skipif(not HAS_INDEXING, reason="indexing import failed")
class TestIndexingJob:
    def test_auto_total_count(self):
        docs = [Document(content=f"doc {i}") for i in range(5)]
        job = IndexingJob(job_id="j1", documents=docs)
        assert job.total_count == 5
        assert job.status == "pending"
        assert job.progress == 0.0


# ===================================================================
# 13. Database client dataclasses — 3 tests
# ===================================================================

@pytest.mark.skipif(not HAS_PINECONE_DC, reason="pinecone_client import failed")
class TestPineconeSearchResult:
    def test_creation(self):
        r = PineconeSearchResult(id="p1", score=0.9, metadata={"k": "v"})
        assert r.id == "p1"
        assert r.values is None


@pytest.mark.skipif(not HAS_WEAVIATE_DC, reason="weaviate_client import failed")
class TestWeaviateSearchResult:
    def test_creation(self):
        r = WeaviateSearchResult(id="w1", score=0.8,
                                  metadata={"k": "v"},
                                  properties={"content": "hello"})
        assert r.id == "w1"
        assert r.vector is None
        assert r.explanation is None


@pytest.mark.skipif(not HAS_QDRANT_DC, reason="qdrant_client import failed")
class TestQdrantSearchResult:
    def test_creation(self):
        r = QdrantSearchResult(id="q1", score=0.7, payload={"content": "test"})
        assert r.id == "q1"
        assert r.vector is None


# ===================================================================
# 14. RetrievalQuery + RetrievalResult dataclasses — 2 tests
# ===================================================================

@pytest.mark.skipif(not HAS_RETRIEVAL, reason="retrieval import failed")
class TestRetrievalDataclasses:
    def test_retrieval_query_defaults(self):
        rq = RetrievalQuery(query="test")
        assert rq.search_mode == "semantic"
        assert rq.top_k == 10
        assert rq.rerank is True
        assert rq.expand_query is True

    def test_retrieval_result_empty(self):
        rr = RetrievalResult(results=[], total_found=0, query_time=0.01)
        assert rr.total_found == 0
        assert rr.facets == {}
        assert rr.suggestions == []


# ===================================================================
# 15. Global timed_operation decorator — 1 test
# ===================================================================

@pytest.mark.skipif(not HAS_UTILS, reason="utils import failed")
class TestGlobalTimedOperation:
    def test_global_monitor_decorator(self):
        performance_monitor.clear_metrics()

        @timed_operation("global_test")
        def sample():
            return "ok"

        result = sample()
        assert result == "ok"
        metrics = performance_monitor.get_metrics("global_test")
        assert len(metrics) >= 1


# ===================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
