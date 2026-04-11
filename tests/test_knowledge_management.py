"""
Tests for asi_build.knowledge_management module.

Covers: KnowledgeGraphManager, InformationAggregator, IntelligentSearch,
        QualityController, PredictiveSynthesizer, ContextualLearner,
        KnowledgeEngine dataclasses.
"""

import pytest

pytest.importorskip("aiohttp")
import asyncio
import os
import sys
import time
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from asi_build.knowledge_management.core.information_aggregator import (
    AggregatedInformation,
    InformationAggregator,
    InformationSource,
)
from asi_build.knowledge_management.core.knowledge_engine import (
    KnowledgeQuery,
    KnowledgeResult,
)
from asi_build.knowledge_management.core.knowledge_graph_manager import (
    GraphAnalysisResult,
    KnowledgeGraphManager,
    KnowledgeNode,
    KnowledgeRelationship,
)
from asi_build.knowledge_management.learning.contextual_learner import (
    AdaptationRule,
    ContextualLearner,
    LearningEvent,
    LearningPattern,
)
from asi_build.knowledge_management.search.intelligent_search import (
    IntelligentSearch,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from asi_build.knowledge_management.synthesis.predictive_synthesizer import (
    KnowledgeSynthesis,
    Prediction,
    PredictiveSynthesizer,
    SynthesisQuery,
)
from asi_build.knowledge_management.validation.quality_controller import (
    QualityController,
    ValidationResult,
    ValidationRule,
)

# ── Dataclass tests ─────────────────────────────────────────────────────


class TestDataclasses:
    def test_knowledge_query_defaults(self):
        q = KnowledgeQuery(query="test", context={})
        assert q.priority == 1
        assert q.timestamp is not None

    def test_knowledge_node_timestamp(self):
        n = KnowledgeNode(id="n1", label="test", node_type="concept", properties={})
        assert n.timestamp is not None
        assert n.confidence == 1.0

    def test_knowledge_relationship_defaults(self):
        r = KnowledgeRelationship(
            source_id="a",
            target_id="b",
            relationship_type="relates_to",
            properties={},
        )
        assert r.strength == 1.0
        assert r.confidence == 1.0

    def test_search_query_defaults(self):
        q = SearchQuery(query="test")
        assert q.search_type == "comprehensive"
        assert q.max_results == 50

    def test_synthesis_query_defaults(self):
        q = SynthesisQuery(query="test")
        assert q.synthesis_type == "comprehensive"
        assert q.include_predictions is True

    def test_prediction_fields(self):
        p = Prediction(
            description="Rising trend",
            probability=0.7,
            confidence=0.6,
            time_frame="24h",
            supporting_evidence=["trend detected"],
            risk_factors=["reversal"],
        )
        assert p.metadata == {}

    def test_learning_pattern_defaults(self):
        lp = LearningPattern(
            pattern_id="p1",
            pattern_type="query",
            pattern_data={"a": 1},
        )
        assert lp.frequency == 1
        assert lp.confidence == 0.5
        assert lp.last_seen is not None

    def test_learning_event_defaults(self):
        le = LearningEvent(
            event_id="e1",
            event_type="interaction",
            query="test",
            result_quality=0.8,
            processing_time=1.0,
        )
        assert le.timestamp is not None
        assert le.user_feedback is None

    def test_adaptation_rule_defaults(self):
        ar = AdaptationRule(
            rule_id="r1",
            rule_type="perf",
            condition={"x": {"gt": 5}},
            action={"y": 1},
        )
        assert ar.effectiveness == 0.5
        assert ar.enabled is True

    def test_validation_rule_defaults(self):
        vr = ValidationRule(
            name="test",
            rule_type="accuracy",
            check_function="check_test",
        )
        assert vr.weight == 1.0
        assert vr.threshold == 0.7


# ── KnowledgeGraphManager ───────────────────────────────────────────────


class TestKnowledgeGraphManager:
    def test_init_defaults(self):
        mgr = KnowledgeGraphManager()
        assert mgr.nodes == {}
        assert mgr.relationships == []
        assert len(mgr.graph.nodes()) == 0

    def test_default_config(self):
        mgr = KnowledgeGraphManager()
        assert "relationship_types" in mgr.config
        assert "node_types" in mgr.config

    def test_graph_statistics_empty(self):
        mgr = KnowledgeGraphManager()
        stats = mgr._get_graph_statistics()
        assert stats["total_nodes"] == 0
        assert stats["total_relationships"] == 0

    def test_graph_complexity_empty(self):
        mgr = KnowledgeGraphManager()
        assert mgr._calculate_graph_complexity() == 0.0

    def test_get_knowledge_subgraph_empty(self):
        mgr = KnowledgeGraphManager()
        sub = mgr.get_knowledge_subgraph(["nonexistent"])
        assert sub["subgraph_size"] == 0

    @pytest.mark.asyncio
    async def test_analyze_relationships(self):
        mgr = KnowledgeGraphManager()
        query = KnowledgeQuery(query="test automation workflow", context={})
        agg_info = {
            "aggregated_content": {
                "source1": {"content": "automation testing workflow", "type": "technical"}
            }
        }
        result = await mgr.analyze_relationships(query, agg_info)
        assert "analysis_result" in result or "error" in result

    @pytest.mark.asyncio
    async def test_build_graph_adds_nodes(self):
        mgr = KnowledgeGraphManager()
        concepts = ["automation", "testing"]
        await mgr._build_graph_from_concepts(concepts, {})
        assert len(mgr.nodes) == 2
        assert "concept_automation" in mgr.nodes

    @pytest.mark.asyncio
    async def test_relationships_created(self):
        mgr = KnowledgeGraphManager()
        concepts = ["automation", "workflow"]
        agg_info = {"aggregated_content": {}}
        await mgr._build_graph_from_concepts(concepts, agg_info)
        await mgr._create_relationships_from_context(concepts, agg_info)
        assert len(mgr.relationships) > 0

    def test_get_knowledge_subgraph_with_data(self):
        mgr = KnowledgeGraphManager()
        # Add nodes manually
        for concept in ["alpha", "beta", "gamma"]:
            nid = f"concept_{concept}"
            mgr.nodes[nid] = KnowledgeNode(
                id=nid, label=concept, node_type="concept", properties={}
            )
            mgr.graph.add_node(nid)
        mgr.graph.add_edge(
            "concept_alpha", "concept_beta", relationship_type="relates_to", strength=0.8
        )
        mgr.graph.add_edge(
            "concept_beta", "concept_gamma", relationship_type="enables", strength=0.9
        )

        sub = mgr.get_knowledge_subgraph(["alpha"], max_depth=1)
        assert "alpha" in sub["nodes"]
        assert "beta" in sub["nodes"]

    def test_generate_analysis_insights(self):
        mgr = KnowledgeGraphManager()
        insights = mgr._generate_analysis_insights(
            ["concept_a", "concept_b"], {"co_occurs_with": 12}
        )
        assert len(insights) > 0
        assert any("Rich" in i for i in insights)


# ── InformationAggregator ───────────────────────────────────────────────


class TestInformationAggregator:
    def test_init_sources(self):
        agg = InformationAggregator()
        assert len(agg.sources) > 0
        names = [s.name for s in agg.sources]
        assert "kenny_memory_analytics" in names

    def test_cache_initialized(self):
        agg = InformationAggregator()
        assert "memory_cache" in agg.cache

    def test_cache_key_generation(self):
        agg = InformationAggregator()
        k1 = agg._generate_cache_key("hello")
        k2 = agg._generate_cache_key("hello")
        assert k1 == k2
        assert k1 != agg._generate_cache_key("world")

    def test_cache_put_get(self):
        agg = InformationAggregator()
        agg._cache_result("key1", {"data": "test"})
        result = agg._get_from_cache("key1")
        assert result["data"] == "test"

    def test_cache_miss(self):
        agg = InformationAggregator()
        assert agg._get_from_cache("nonexistent") is None

    def test_select_sources_priority(self):
        agg = InformationAggregator()
        query = KnowledgeQuery(query="kenny automation test", context={})
        selected = agg._select_sources(query)
        assert len(selected) > 0
        # Kenny sources should be boosted
        kenny_sources = [s for s in selected if "kenny" in s.name]
        assert len(kenny_sources) > 0

    def test_aggregation_stats(self):
        agg = InformationAggregator()
        stats = agg.get_aggregation_stats()
        assert stats["total_queries"] == 0
        assert stats["active_sources"] > 0

    def test_process_aggregation_results_empty(self):
        agg = InformationAggregator()
        query = KnowledgeQuery(query="test", context={})
        result = agg._process_aggregation_results([], [], query)
        assert result["sources_successful"] == 0
        assert result["overall_confidence"] == 0.0

    def test_process_aggregation_results_with_data(self):
        agg = InformationAggregator()
        query = KnowledgeQuery(query="test", context={})
        sources = [
            InformationSource(name="s1", source_type="kenny_system", endpoint="test"),
        ]
        results = [{"source": "s1", "data": {"content": "hello", "confidence": 0.8}}]
        processed = agg._process_aggregation_results(results, sources, query)
        assert processed["sources_successful"] == 1
        assert processed["overall_confidence"] == 0.8


# ── IntelligentSearch ───────────────────────────────────────────────────


class TestIntelligentSearch:
    def test_init(self):
        search = IntelligentSearch()
        assert search.total_searches == 0
        assert len(search.strategies) > 0

    def test_extract_keywords(self):
        search = IntelligentSearch()
        kw = search._extract_keywords("what is the best python framework for web")
        assert "python" in kw
        assert "framework" in kw
        # Stop words filtered
        assert "the" not in kw
        assert "is" not in kw

    def test_extract_semantic_concepts(self):
        search = IntelligentSearch()
        concepts = search._extract_semantic_concepts("kenny automation workflow system")
        assert "automation" in concepts

    def test_semantic_similarity(self):
        search = IntelligentSearch()
        sim = search._calculate_semantic_similarity(["a", "b", "c"], ["a", "b", "d"])
        assert 0.0 < sim < 1.0

    def test_semantic_similarity_no_overlap(self):
        search = IntelligentSearch()
        sim = search._calculate_semantic_similarity(["x"], ["y"])
        assert sim == 0.0

    def test_semantic_similarity_empty(self):
        search = IntelligentSearch()
        assert search._calculate_semantic_similarity([], ["x"]) == 0.0

    def test_classify_query_type(self):
        search = IntelligentSearch()
        assert search._classify_query_type("how to build a website") == "procedural"
        assert search._classify_query_type("what is AI") == "definitional"
        assert search._classify_query_type("why is the sky blue") == "causal"
        assert search._classify_query_type("hello world") == "descriptive"

    def test_assess_query_complexity(self):
        search = IntelligentSearch()
        assert search._assess_query_complexity("hi there") == "simple"
        assert (
            search._assess_query_complexity("this is a moderate length query for search")
            == "moderate"
        )
        assert search._assess_query_complexity(" ".join(["word"] * 15)) == "complex"

    def test_highlight_text(self):
        search = IntelligentSearch()
        highlighted = search._highlight_text("hello world test", [(6, 11)])
        assert "**world**" in highlighted

    def test_source_authority_boost(self):
        search = IntelligentSearch()
        assert search._get_source_authority_boost("kenny_memory_analytics") == 1.2
        assert search._get_source_authority_boost("unknown_xyz") == 0.7

    def test_search_statistics(self):
        search = IntelligentSearch()
        stats = search.get_search_statistics()
        assert stats["total_searches"] == 0

    @pytest.mark.asyncio
    async def test_keyword_search(self):
        search = IntelligentSearch()
        query = SearchQuery(query="automation workflow")
        corpus = [
            {
                "text": "automation workflow testing system",
                "source": "s1",
                "confidence": 0.8,
                "metadata": {},
            },
            {
                "text": "unrelated content about cooking",
                "source": "s2",
                "confidence": 0.5,
                "metadata": {},
            },
        ]
        results = await search._keyword_search(query, corpus)
        assert len(results) >= 1
        assert results[0].source == "s1"

    @pytest.mark.asyncio
    async def test_fuzzy_search(self):
        search = IntelligentSearch()
        query = SearchQuery(query="automaton workflow")
        corpus = [
            {"text": "automation workflow", "source": "s1", "confidence": 0.8, "metadata": {}},
        ]
        results = await search._fuzzy_search(query, corpus)
        # fuzzy match should find it (high similarity)
        assert len(results) >= 1

    def test_prepare_search_corpus(self):
        search = IntelligentSearch()
        agg = {
            "aggregated_content": {
                "src1": {"content": "hello world", "type": "web", "metadata": {"ts": 1}},
            }
        }
        corpus = search._prepare_search_corpus(agg)
        assert len(corpus) == 1
        assert "hello world" in corpus[0]["text"]


# ── QualityController ───────────────────────────────────────────────────


class TestQualityController:
    def test_init_rules(self):
        qc = QualityController()
        assert len(qc.validation_rules) > 0
        rule_names = [r.name for r in qc.validation_rules]
        assert "source_consistency" in rule_names

    @pytest.mark.asyncio
    async def test_validate_empty_synthesis(self):
        qc = QualityController()
        result = await qc.validate_knowledge({})
        assert "validation" in result

    @pytest.mark.asyncio
    async def test_check_source_consistency_few_sources(self):
        qc = QualityController()
        components = {"sources": ["s1"], "synthesis_data": {}}
        result = await qc._check_source_consistency(components)
        assert result["score"] == 0.7
        assert any("Insufficient" in i for i in result["issues"])

    @pytest.mark.asyncio
    async def test_check_source_consistency_diverse(self):
        qc = QualityController()
        components = {
            "sources": ["kenny_system_a", "external_api_b"],
            "synthesis_data": {"key_findings": ["finding1"]},
        }
        result = await qc._check_source_consistency(components)
        assert result["score"] == 0.9  # mixed sources

    @pytest.mark.asyncio
    async def test_check_completeness(self):
        qc = QualityController()
        components = {
            "synthesis_data": {
                "summary": "A " * 30,
                "key_findings": ["f1", "f2"],
                "insights": ["i1"],
            }
        }
        result = await qc._check_information_completeness(components)
        assert result["passed"] is True
        assert result["score"] >= 0.6

    @pytest.mark.asyncio
    async def test_check_completeness_missing(self):
        qc = QualityController()
        components = {"synthesis_data": {}}
        result = await qc._check_information_completeness(components)
        assert result["score"] == 0.0

    @pytest.mark.asyncio
    async def test_check_source_reliability(self):
        qc = QualityController()
        components = {"sources": ["kenny_system_1", "kenny_docs"]}
        result = await qc._check_source_reliability(components)
        assert result["score"] > 0

    @pytest.mark.asyncio
    async def test_check_confidence_calibration(self):
        qc = QualityController()
        components = {
            "synthesis_data": {"key_findings": ["a", "b"], "insights": ["c"]},
            "confidence_scores": {"overall": 0.99},
        }
        result = await qc._check_confidence_calibration(components)
        # Extremely high → flagged
        assert any("overconfidence" in i for i in result["issues"])

    def test_aggregate_validation_results(self):
        qc = QualityController()
        results = {
            "source_consistency": {"passed": True, "score": 0.9, "issues": []},
            "source_reliability": {"passed": True, "score": 0.8, "issues": []},
        }
        agg = qc._aggregate_validation_results(results)
        assert agg["overall_score"] > 0
        assert agg["passed_checks"] >= 1

    def test_calculate_quality_metrics(self):
        qc = QualityController()
        results = {
            "source_consistency": {"score": 0.9},
            "source_reliability": {"score": 0.7},
        }
        metrics = qc._calculate_quality_metrics(results)
        assert "average_score" in metrics

    def test_confidence_adjustments(self):
        qc = QualityController()
        results = {
            "rule1": {"score": 0.95, "passed": True},
        }
        adj = qc._calculate_confidence_adjustments(results)
        assert "confidence_multiplier" in adj

    def test_validation_statistics(self):
        qc = QualityController()
        stats = qc.get_validation_statistics()
        assert stats["total_validations"] == 0


# ── PredictiveSynthesizer ──────────────────────────────────────────────


class TestPredictiveSynthesizer:
    def test_init(self):
        ps = PredictiveSynthesizer()
        assert ps.total_syntheses == 0

    def test_assess_data_quality_good(self):
        ps = PredictiveSynthesizer()
        agg = {
            "aggregated_content": {
                "s1": {"confidence": 0.8, "type": "web"},
                "s2": {"confidence": 0.7, "type": "api"},
                "s3": {"confidence": 0.9, "type": "kenny"},
            }
        }
        graph = {"insights": ["one"]}
        search = {"search_results": [{"content": "x"}]}
        quality = ps._assess_data_quality(agg, graph, search)
        assert quality["data_completeness"] == 1.0
        assert quality["information_diversity"] > 0

    def test_assess_data_quality_poor(self):
        ps = PredictiveSynthesizer()
        quality = ps._assess_data_quality({}, {}, {})
        assert quality["overall_quality"] == "poor"

    def test_extract_key_themes(self):
        ps = PredictiveSynthesizer()
        themes = ps._extract_key_themes("automation workflow testing system automation")
        assert "automation" in themes

    def test_generate_content_summary(self):
        ps = PredictiveSynthesizer()
        content = "First sentence here. Second sentence is longer and more detailed. Third sentence wraps up."
        summary = ps._generate_content_summary(content)
        assert len(summary) > 0

    def test_detect_content_patterns(self):
        ps = PredictiveSynthesizer()
        agg = {
            "aggregated_content": {
                "s1": {"type": "web_content"},
                "s2": {"type": "web_content"},
                "s3": {"type": "api_data"},
            }
        }
        patterns = ps._detect_content_patterns(agg)
        assert len(patterns) >= 1
        assert patterns[0]["pattern"] == "web_content"

    def test_detect_trends_insufficient_data(self):
        ps = PredictiveSynthesizer()
        trends = ps._detect_trends([{"confidence": 0.5, "timestamp": 1}])
        assert trends == []

    def test_detect_trends_increasing(self):
        ps = PredictiveSynthesizer()
        data = [
            {"confidence": 0.3, "timestamp": 1},
            {"confidence": 0.4, "timestamp": 2},
            {"confidence": 0.5, "timestamp": 3},
            {"confidence": 0.8, "timestamp": 4},
            {"confidence": 0.9, "timestamp": 5},
        ]
        trends = ps._detect_trends(data)
        assert len(trends) == 1
        assert trends[0]["direction"] == "increasing"

    def test_calculate_content_correlation(self):
        ps = PredictiveSynthesizer()
        c1 = {"content": "automation workflow system"}
        c2 = {"content": "automation testing workflow"}
        corr = ps._calculate_content_correlation(c1, c2)
        assert 0.0 < corr < 1.0

    def test_generate_trend_predictions(self):
        ps = PredictiveSynthesizer()
        trend_analysis = {
            "identified_trends": [
                {"metric": "confidence", "direction": "increasing", "strength": 0.7}
            ]
        }
        preds = ps._generate_trend_predictions(trend_analysis, "24h")
        assert len(preds) == 1
        assert preds[0].time_frame == "24h"

    def test_synthesis_statistics(self):
        ps = PredictiveSynthesizer()
        stats = ps.get_synthesis_statistics()
        assert stats["total_syntheses"] == 0


# ── ContextualLearner ───────────────────────────────────────────────────


class TestContextualLearner:
    def test_init(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        assert learner.learning_metrics["total_learning_events"] == 0

    def test_query_complexity(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        assert learner._assess_query_complexity("hi") == "simple"
        assert learner._assess_query_complexity("this is a longer query indeed") == "medium"
        assert learner._assess_query_complexity(" ".join(["word"] * 20)) == "complex"

    def test_classify_query_type(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        assert learner._classify_query_type("how to cook") == "procedural"
        assert learner._classify_query_type("what is AI") == "definitional"
        assert learner._classify_query_type("why is the sky blue") == "causal"

    def test_categorize_processing_time(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        assert learner._categorize_processing_time(2.0) == "fast"
        assert learner._categorize_processing_time(10.0) == "medium"
        assert learner._categorize_processing_time(30.0) == "slow"

    def test_get_query_key(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        key = learner._get_query_key("Hello World How Are You Today")
        assert key == "hello_world_how_are_you"

    def test_evaluate_conditions_gt(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        assert learner._evaluate_conditions({"x": {"gt": 5}}, {"x": 10}) is True
        assert learner._evaluate_conditions({"x": {"gt": 5}}, {"x": 3}) is False

    def test_evaluate_conditions_lt(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        assert learner._evaluate_conditions({"x": {"lt": 10}}, {"x": 5}) is True

    def test_calculate_trend(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        assert learner._calculate_trend([1, 2]) == "stable"  # too few
        assert learner._calculate_trend([1, 1, 1, 5, 5, 5]) == "increasing"
        assert learner._calculate_trend([5, 5, 5, 1, 1, 1]) == "decreasing"

    def test_adaptation_rules_initialized(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        assert len(learner.adaptation_rules) > 0
        rule_ids = [r.rule_id for r in learner.adaptation_rules]
        assert "slow_query_timeout" in rule_ids

    def test_learning_insights_empty(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        insights = learner.get_learning_insights()
        assert insights["total_patterns"] == 0

    @pytest.mark.asyncio
    async def test_extract_query_patterns(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        event = LearningEvent(
            event_id="e1",
            event_type="query_interaction",
            query="how to build a website",
            result_quality=0.8,
            processing_time=3.0,
        )
        patterns = await learner._extract_query_patterns(event)
        assert len(patterns) >= 2  # length + type patterns
        types = [p.pattern_id for p in patterns]
        assert any("type_procedural" in t for t in types)

    @pytest.mark.asyncio
    async def test_extract_performance_patterns(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        event = LearningEvent(
            event_id="e1",
            event_type="interaction",
            query="test",
            result_quality=0.5,
            processing_time=2.0,
            system_metrics={"source_count": 3},
        )
        patterns = await learner._extract_performance_patterns(event)
        assert len(patterns) >= 1

    def test_update_performance_model(self):
        learner = ContextualLearner(config={"persistence_enabled": False})
        pattern = LearningPattern(
            pattern_id="time_fast",
            pattern_type="performance",
            pattern_data={"processing_time": 1.0, "quality": 0.9},
        )
        learner._update_performance_model(pattern)
        assert "time_fast" in learner.performance_patterns
        assert learner.performance_patterns["time_fast"]["count"] == 1
