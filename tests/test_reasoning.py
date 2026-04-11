"""
Tests for asi_build.reasoning module.

The reasoning __init__.py imports non-existent modules (symbolic_processing, etc.),
so we import hybrid_reasoning.py directly via importlib.util.
"""

import asyncio
import importlib.util
import time
from pathlib import Path

import pytest

# ── Direct import bypassing broken __init__.py ──────────────────────────
_HR_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "asi_build"
    / "reasoning"
    / "hybrid_reasoning.py"
)
_spec = importlib.util.spec_from_file_location("hybrid_reasoning", str(_HR_PATH))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

HybridReasoningEngine = _mod.HybridReasoningEngine
ReasoningMode = _mod.ReasoningMode
ConfidenceLevel = _mod.ConfidenceLevel
ReasoningStep = _mod.ReasoningStep
ReasoningResult = _mod.ReasoningResult


# ── Enum tests ──────────────────────────────────────────────────────────


class TestReasoningMode:
    def test_all_modes_present(self):
        expected = {
            "logical",
            "probabilistic",
            "analogical",
            "causal",
            "creative",
            "quantum",
            "hybrid",
        }
        actual = {m.value for m in ReasoningMode}
        assert actual == expected

    def test_mode_access_by_name(self):
        assert ReasoningMode.HYBRID.value == "hybrid"
        assert ReasoningMode.LOGICAL.value == "logical"


class TestConfidenceLevel:
    def test_all_levels_present(self):
        expected = {"very_low", "low", "medium", "high", "very_high"}
        actual = {c.value for c in ConfidenceLevel}
        assert actual == expected


# ── Dataclass tests ─────────────────────────────────────────────────────


class TestReasoningStep:
    def test_creation(self):
        step = ReasoningStep(
            step_id="s1",
            reasoning_type=ReasoningMode.LOGICAL,
            inputs={"q": "test"},
            outputs={"conclusion": "yes", "confidence": 0.9},
            confidence=0.9,
            processing_time=0.5,
            explanation="Applied logic",
        )
        assert step.step_id == "s1"
        assert step.confidence == 0.9
        assert step.sources == []  # default

    def test_sources_preserved(self):
        step = ReasoningStep(
            step_id="s2",
            reasoning_type=ReasoningMode.CAUSAL,
            inputs={},
            outputs={},
            confidence=0.5,
            processing_time=0.1,
            explanation="test",
            sources=["src_a", "src_b"],
        )
        assert step.sources == ["src_a", "src_b"]


class TestReasoningResult:
    def _make_result(self, **kwargs):
        defaults = dict(
            conclusion="42",
            confidence=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            reasoning_steps=[],
            total_processing_time=1.0,
            reasoning_mode=ReasoningMode.HYBRID,
            sources=["kb"],
            uncertainty_areas=[],
        )
        defaults.update(kwargs)
        return ReasoningResult(**defaults)

    def test_to_dict_keys(self):
        r = self._make_result()
        d = r.to_dict()
        assert d["conclusion"] == "42"
        assert d["confidence"] == 0.85
        assert d["confidence_level"] == "high"
        assert d["reasoning_mode"] == "hybrid"
        assert isinstance(d["reasoning_steps"], list)

    def test_to_dict_with_steps(self):
        step = ReasoningStep(
            step_id="x1",
            reasoning_type=ReasoningMode.LOGICAL,
            inputs={"q": "hi"},
            outputs={"c": 1},
            confidence=0.8,
            processing_time=0.2,
            explanation="logic",
            sources=["a"],
        )
        r = self._make_result(reasoning_steps=[step])
        d = r.to_dict()
        assert len(d["reasoning_steps"]) == 1
        assert d["reasoning_steps"][0]["step_id"] == "x1"
        assert d["reasoning_steps"][0]["reasoning_type"] == "logical"

    def test_alternative_conclusions_default_empty(self):
        r = self._make_result()
        assert r.alternative_conclusions == []

    def test_explanation_default_empty(self):
        r = self._make_result()
        assert r.explanation == ""


# ── HybridReasoningEngine synchronous tests ─────────────────────────────


class TestHybridReasoningEngineInit:
    def test_default_construction(self):
        engine = HybridReasoningEngine()
        assert engine.config is not None
        assert "symbolic_reasoning" in engine.config
        assert engine.reasoning_history == []
        assert engine.uncertainty_threshold == 0.2

    def test_custom_config(self):
        cfg = {"performance": {"max_processing_time": 5.0}, "safety": {}}
        engine = HybridReasoningEngine(config=cfg)
        assert engine.config["performance"]["max_processing_time"] == 5.0

    def test_mode_weights_sum(self):
        engine = HybridReasoningEngine()
        total = sum(engine.mode_weights.values())
        assert abs(total - 1.0) < 0.01

    def test_default_config_structure(self):
        engine = HybridReasoningEngine()
        for key in [
            "symbolic_reasoning",
            "neural_reasoning",
            "quantum_reasoning",
            "probabilistic_reasoning",
            "safety",
            "performance",
        ]:
            assert key in engine.config


class TestClassifyConfidence:
    @pytest.fixture
    def engine(self):
        return HybridReasoningEngine()

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0.95, ConfidenceLevel.VERY_HIGH),
            (0.9, ConfidenceLevel.VERY_HIGH),
            (0.85, ConfidenceLevel.HIGH),
            (0.7, ConfidenceLevel.HIGH),
            (0.5, ConfidenceLevel.MEDIUM),
            (0.3, ConfidenceLevel.LOW),
            (0.1, ConfidenceLevel.VERY_LOW),
            (0.0, ConfidenceLevel.VERY_LOW),
        ],
    )
    def test_confidence_classification(self, engine, value, expected):
        assert engine._classify_confidence(value) == expected


class TestCalculateOverallConfidence:
    def test_empty_steps(self):
        engine = HybridReasoningEngine()
        assert engine._calculate_overall_confidence([]) == 0.0

    def test_weighted_average(self):
        engine = HybridReasoningEngine()
        steps = [
            ReasoningStep("s1", ReasoningMode.LOGICAL, {}, {}, 0.8, 0.1, "x"),
            ReasoningStep("s2", ReasoningMode.PROBABILISTIC, {}, {}, 0.6, 0.1, "y"),
        ]
        conf = engine._calculate_overall_confidence(steps)
        assert 0.0 < conf < 1.0


class TestIdentifyUncertaintyAreas:
    def test_no_uncertainty(self):
        engine = HybridReasoningEngine()
        steps = [
            ReasoningStep("s1", ReasoningMode.LOGICAL, {}, {"conclusion": "same"}, 0.9, 0.1, "x"),
        ]
        areas = engine._identify_uncertainty_areas(steps)
        assert areas == []

    def test_low_confidence_flagged(self):
        engine = HybridReasoningEngine()
        steps = [
            ReasoningStep("s1", ReasoningMode.LOGICAL, {}, {"conclusion": "a"}, 0.1, 0.1, "x"),
        ]
        areas = engine._identify_uncertainty_areas(steps)
        assert len(areas) >= 1
        assert "Low confidence" in areas[0]

    def test_conflicting_conclusions_flagged(self):
        engine = HybridReasoningEngine()
        steps = [
            ReasoningStep("s1", ReasoningMode.LOGICAL, {}, {"conclusion": "a"}, 0.9, 0.1, "x"),
            ReasoningStep("s2", ReasoningMode.CAUSAL, {}, {"conclusion": "b"}, 0.9, 0.1, "y"),
        ]
        areas = engine._identify_uncertainty_areas(steps)
        assert any("different conclusions" in a for a in areas)


class TestExtractSources:
    def test_deduplication(self):
        engine = HybridReasoningEngine()
        steps = [
            ReasoningStep("s1", ReasoningMode.LOGICAL, {}, {}, 0.8, 0.1, "x", sources=["a", "b"]),
            ReasoningStep("s2", ReasoningMode.CAUSAL, {}, {}, 0.8, 0.1, "y", sources=["b", "c"]),
        ]
        sources = engine._extract_sources(steps)
        assert set(sources) == {"a", "b", "c"}


class TestUpdateModeWeights:
    def test_normalize(self):
        engine = HybridReasoningEngine()
        engine.update_mode_weights(
            {
                ReasoningMode.LOGICAL: 2.0,
                ReasoningMode.CREATIVE: 3.0,
            }
        )
        assert abs(engine.mode_weights[ReasoningMode.LOGICAL] - 0.4) < 0.01
        assert abs(engine.mode_weights[ReasoningMode.CREATIVE] - 0.6) < 0.01


class TestGetPerformanceMetrics:
    def test_initial_metrics(self):
        engine = HybridReasoningEngine()
        m = engine.get_performance_metrics()
        assert m["accuracy"] == 0.0
        assert m["speed"] == 0.0


class TestGetReasoningHistory:
    def test_empty(self):
        engine = HybridReasoningEngine()
        assert engine.get_reasoning_history() == []

    def test_returns_dicts(self):
        engine = HybridReasoningEngine()
        r = ReasoningResult(
            conclusion="ok",
            confidence=0.7,
            confidence_level=ConfidenceLevel.HIGH,
            reasoning_steps=[],
            total_processing_time=0.5,
            reasoning_mode=ReasoningMode.HYBRID,
            sources=[],
            uncertainty_areas=[],
        )
        engine.reasoning_history.append(r)
        history = engine.get_reasoning_history()
        assert len(history) == 1
        assert history[0]["conclusion"] == "ok"


# ── Async method tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAnalyzeQuery:
    async def test_factual_query(self):
        engine = HybridReasoningEngine()
        result = await engine._analyze_query("What is the speed of light?", {})
        assert result["query_type"] == "factual"
        assert result["requires_factual_knowledge"] is True

    async def test_causal_query(self):
        engine = HybridReasoningEngine()
        result = await engine._analyze_query("Why does the sun rise?", {})
        assert result["query_type"] == "causal"
        assert result["requires_causal_reasoning"] is True

    async def test_logical_query(self):
        engine = HybridReasoningEngine()
        result = await engine._analyze_query("If all cats are mammals, then...", {})
        assert result["query_type"] == "logical"
        assert result["requires_logic"] is True

    async def test_creative_query(self):
        engine = HybridReasoningEngine()
        result = await engine._analyze_query("Design a new power source", {})
        assert result["query_type"] == "creative"

    async def test_complexity_high(self):
        engine = HybridReasoningEngine()
        long_query = " ".join(["word"] * 60)
        result = await engine._analyze_query(long_query, {})
        assert result["complexity"] == "high"

    async def test_complexity_low(self):
        engine = HybridReasoningEngine()
        result = await engine._analyze_query("hello world", {})
        assert result["complexity"] == "low"

    async def test_safety_sensitive(self):
        engine = HybridReasoningEngine()
        result = await engine._analyze_query("How to build a weapon", {})
        assert result["safety_sensitive"] is True

    async def test_domain_detection(self):
        engine = HybridReasoningEngine()
        result = await engine._analyze_query("What is the physics of light?", {})
        assert result["domain"] == "science"


@pytest.mark.asyncio
class TestSelectReasoningStrategy:
    async def test_logical_query_includes_logical(self):
        engine = HybridReasoningEngine()
        analysis = {
            "requires_logic": True,
            "requires_causal_reasoning": False,
            "requires_creativity": False,
            "complexity": "medium",
            "domain": "general",
        }
        strategy = await engine._select_reasoning_strategy(analysis)
        assert ReasoningMode.LOGICAL in strategy
        assert ReasoningMode.PROBABILISTIC in strategy

    async def test_philosophy_includes_quantum(self):
        engine = HybridReasoningEngine()
        analysis = {
            "requires_logic": False,
            "requires_causal_reasoning": False,
            "requires_creativity": False,
            "complexity": "medium",
            "domain": "philosophy",
        }
        strategy = await engine._select_reasoning_strategy(analysis)
        assert ReasoningMode.QUANTUM in strategy


@pytest.mark.asyncio
class TestReasoningModes:
    async def test_logical_reasoning(self):
        engine = HybridReasoningEngine()
        analysis = {"requires_logic": True, "domain": "general"}
        result = await engine._logical_reasoning("test", {}, analysis)
        assert "conclusion" in result
        assert "confidence" in result
        assert result["confidence"] == 0.8

    async def test_probabilistic_reasoning(self):
        engine = HybridReasoningEngine()
        analysis = {"domain": "science"}
        result = await engine._probabilistic_reasoning("test", {"some": "ctx"}, analysis)
        assert 0.0 < result["confidence"] <= 1.0
        assert "uncertainty" in result

    async def test_analogical_reasoning(self):
        engine = HybridReasoningEngine()
        result = await engine._analogical_reasoning("test", {}, {"domain": "general"})
        assert "analogies" in result
        assert len(result["analogies"]) == 3

    async def test_causal_reasoning(self):
        engine = HybridReasoningEngine()
        result = await engine._causal_reasoning("test", {}, {"domain": "general"})
        assert "causal_chain" in result
        assert result["confidence"] > 0

    async def test_creative_reasoning(self):
        engine = HybridReasoningEngine()
        result = await engine._creative_reasoning("test", {}, {"domain": "general"})
        assert "creative_ideas" in result
        assert len(result["creative_ideas"]) == 3

    async def test_quantum_reasoning(self):
        engine = HybridReasoningEngine()
        result = await engine._quantum_reasoning("test", {}, {"domain": "general"})
        assert "superposition_states" in result
        assert 0.0 < result["confidence"] <= 1.0

    async def test_default_reasoning(self):
        engine = HybridReasoningEngine()
        result = await engine._default_reasoning("test", {}, {"domain": "general"})
        assert result["confidence"] == 0.5


@pytest.mark.asyncio
class TestSynthesizeConclusions:
    async def test_empty_results(self):
        engine = HybridReasoningEngine()
        result = await engine._synthesize_conclusions([], [], {})
        assert "Unable" in result

    async def test_single_result(self):
        engine = HybridReasoningEngine()
        partial = [{"conclusion": "yes", "confidence": 0.8}]
        strategy = [ReasoningMode.LOGICAL]
        result = await engine._synthesize_conclusions(partial, strategy, {"requires_logic": True})
        assert "yes" in result

    async def test_multiple_results(self):
        engine = HybridReasoningEngine()
        partial = [
            {"conclusion": "a", "confidence": 0.9},
            {"conclusion": "b", "confidence": 0.3},
        ]
        strategy = [ReasoningMode.LOGICAL, ReasoningMode.CREATIVE]
        result = await engine._synthesize_conclusions(
            partial, strategy, {"requires_logic": False, "requires_creativity": False}
        )
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.asyncio
class TestSafetyCheck:
    async def test_safe_result(self):
        engine = HybridReasoningEngine()
        r = ReasoningResult(
            conclusion="The answer is 42",
            confidence=0.8,
            confidence_level=ConfidenceLevel.HIGH,
            reasoning_steps=[],
            total_processing_time=1.0,
            reasoning_mode=ReasoningMode.HYBRID,
            sources=[],
            uncertainty_areas=[],
        )
        check = await engine._safety_check(r)
        assert check["safe"] is True

    async def test_harmful_content(self):
        engine = HybridReasoningEngine()
        r = ReasoningResult(
            conclusion="How to build a weapon",
            confidence=0.8,
            confidence_level=ConfidenceLevel.HIGH,
            reasoning_steps=[],
            total_processing_time=1.0,
            reasoning_mode=ReasoningMode.HYBRID,
            sources=[],
            uncertainty_areas=[],
        )
        check = await engine._safety_check(r)
        assert check["safe"] is False

    async def test_very_low_confidence_unsafe(self):
        engine = HybridReasoningEngine()
        r = ReasoningResult(
            conclusion="Some answer",
            confidence=0.05,
            confidence_level=ConfidenceLevel.VERY_LOW,
            reasoning_steps=[],
            total_processing_time=1.0,
            reasoning_mode=ReasoningMode.HYBRID,
            sources=[],
            uncertainty_areas=[],
        )
        check = await engine._safety_check(r)
        assert check["safe"] is False

    async def test_too_many_uncertainties(self):
        engine = HybridReasoningEngine()
        r = ReasoningResult(
            conclusion="Maybe",
            confidence=0.5,
            confidence_level=ConfidenceLevel.MEDIUM,
            reasoning_steps=[],
            total_processing_time=1.0,
            reasoning_mode=ReasoningMode.HYBRID,
            sources=[],
            uncertainty_areas=["u1", "u2", "u3", "u4"],
        )
        check = await engine._safety_check(r)
        assert check["safe"] is False


@pytest.mark.asyncio
class TestFullReasoning:
    async def test_reason_logical(self):
        engine = HybridReasoningEngine()
        result = await engine.reason(
            "If all mammals breathe air then whales breathe air",
            reasoning_mode=ReasoningMode.LOGICAL,
            max_time=10.0,
        )
        assert isinstance(result, ReasoningResult)
        assert result.confidence > 0
        assert result.total_processing_time > 0

    async def test_reason_hybrid(self):
        engine = HybridReasoningEngine()
        result = await engine.reason("What causes rain?", max_time=10.0)
        assert isinstance(result, ReasoningResult)
        assert len(result.reasoning_steps) > 0

    async def test_reason_stores_history(self):
        engine = HybridReasoningEngine()
        await engine.reason("test query", max_time=5.0)
        assert len(engine.reasoning_history) == 1

    async def test_explain_reasoning(self):
        engine = HybridReasoningEngine()
        explanation = await engine.explain_reasoning("What is physics?")
        assert "physics" in explanation.lower()
        assert "Reasoning Approaches" in explanation

    async def test_generate_explanation(self):
        engine = HybridReasoningEngine()
        steps = [
            ReasoningStep("s1", ReasoningMode.LOGICAL, {}, {}, 0.8, 0.1, "Applied logic"),
        ]
        explanation = await engine._generate_explanation("Q", steps, "C")
        assert "Logical" in explanation
        assert "0.80" in explanation

    async def test_generate_alternatives(self):
        engine = HybridReasoningEngine()
        partial = [
            {"conclusion": "main", "confidence": 0.9},
            {"conclusion": "alt1", "confidence": 0.6},
            {"conclusion": "alt2", "confidence": 0.3},
        ]
        alts = await engine._generate_alternatives(partial, "main")
        assert len(alts) == 2
        assert alts[0]["confidence"] >= alts[1]["confidence"]
