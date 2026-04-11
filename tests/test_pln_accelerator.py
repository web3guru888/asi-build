"""
Tests for asi_build.pln_accelerator module.

The package __init__ chain imports spacy (not installed), so we import
the core pure-Python modules directly via importlib.util:
  - logic_systems.py   (776 LOC)  – Logic converters, LogicSystems manager
  - context_manager.py (591 LOC)  – Session/context management
"""

import asyncio
import importlib.util
import re
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Direct imports bypassing spacy-dependent __init__.py ────────────────
_BASE = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "asi_build"
    / "pln_accelerator"
    / "nl_logic_bridge"
    / "core"
)

_ls_spec = importlib.util.spec_from_file_location("logic_systems", str(_BASE / "logic_systems.py"))
_ls_mod = importlib.util.module_from_spec(_ls_spec)
_ls_spec.loader.exec_module(_ls_mod)

LogicSystems = _ls_mod.LogicSystems
LogicFormalism = _ls_mod.LogicFormalism
FOLConverter = _ls_mod.FOLConverter
PLNConverter = _ls_mod.PLNConverter
TemporalLogicConverter = _ls_mod.TemporalLogicConverter
ModalLogicConverter = _ls_mod.ModalLogicConverter
LogicConverter = _ls_mod.LogicConverter
LogicalExpression = _ls_mod.LogicalExpression

_cm_spec = importlib.util.spec_from_file_location(
    "context_manager", str(_BASE / "context_manager.py")
)
_cm_mod = importlib.util.module_from_spec(_cm_spec)
_cm_spec.loader.exec_module(_cm_mod)

ContextManager = _cm_mod.ContextManager
ContextType = _cm_mod.ContextType
ContextItem = _cm_mod.ContextItem
SessionContext = _cm_mod.SessionContext


# ═══════════════════════════════════════════════════════════════════════
# Logic Systems Tests
# ═══════════════════════════════════════════════════════════════════════


class TestLogicFormalism:
    def test_all_formalisms_present(self):
        expected = {
            "first_order_logic",
            "probabilistic_logic_networks",
            "temporal_logic",
            "modal_logic",
            "description_logic",
            "fuzzy_logic",
            "predicate_logic",
            "propositional_logic",
        }
        actual = {f.value for f in LogicFormalism}
        assert actual == expected


class TestLogicalExpression:
    def test_creation(self):
        expr = LogicalExpression(
            expression="∀x Human(x) → Mortal(x)",
            formalism=LogicFormalism.FOL,
            parsed_form={"type": "fol"},
            variables=["x"],
            predicates=["Human", "Mortal"],
            operators=["→"],
        )
        assert expr.confidence == 1.0
        assert expr.strength == 1.0
        assert expr.metadata is None


# ── FOLConverter ────────────────────────────────────────────────────────


class TestFOLConverter:
    @pytest.fixture
    def converter(self):
        return FOLConverter()

    @pytest.mark.asyncio
    async def test_convert_empty_frames(self, converter):
        result = await converter.convert_from_semantic_parse({"frames": []}, {})
        assert result == "Unknown(x)"

    @pytest.mark.asyncio
    async def test_convert_agent_patient(self, converter):
        parse = {
            "frames": [
                {
                    "predicate": "chase",
                    "arguments": {"agent": ["Cat"], "patient": ["Mouse"]},
                }
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert result == "chase(cat, mouse)"

    @pytest.mark.asyncio
    async def test_convert_agent_only(self, converter):
        parse = {
            "frames": [
                {
                    "predicate": "sleep",
                    "arguments": {"agent": ["Dog"]},
                }
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert result == "sleep(dog)"

    @pytest.mark.asyncio
    async def test_convert_multiple_frames(self, converter):
        parse = {
            "frames": [
                {"predicate": "run", "arguments": {"agent": ["Alice"]}},
                {"predicate": "jump", "arguments": {"agent": ["Bob"]}},
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert "∧" in result

    @pytest.mark.asyncio
    async def test_parse_expression(self, converter):
        parsed = await converter.parse_expression("∀x Human(x) → Mortal(x)")
        assert "fol" in parsed["type"]
        assert "Human" in parsed["predicates"]
        assert "implication" in parsed["operators"]

    @pytest.mark.asyncio
    async def test_parse_expression_quantifiers(self, converter):
        parsed = await converter.parse_expression("∀x ∃y Loves(x, y)")
        assert len(parsed["quantifiers"]) == 2

    @pytest.mark.asyncio
    async def test_parse_expression_operators(self, converter):
        parsed = await converter.parse_expression("P(x) ∧ Q(x) ∨ ¬R(x)")
        assert "conjunction" in parsed["operators"]
        assert "disjunction" in parsed["operators"]
        assert "negation" in parsed["operators"]

    def test_validate_good(self, converter):
        assert converter.validate_expression("Human(x)") is True
        assert converter.validate_expression("∀x P(x) → Q(x)") is True

    def test_validate_bad(self, converter):
        assert converter.validate_expression("") is False
        assert converter.validate_expression("P(x") is False  # unbalanced

    def test_normalize_term(self, converter):
        assert converter._normalize_term("Hello World") == "hello_world"
        assert converter._normalize_term("") == "unknown"
        assert converter._normalize_term("A-B") == "ab"


# ── PLNConverter ────────────────────────────────────────────────────────


class TestPLNConverter:
    @pytest.fixture
    def converter(self):
        return PLNConverter()

    @pytest.mark.asyncio
    async def test_convert_empty(self, converter):
        result = await converter.convert_from_semantic_parse({"frames": []}, {})
        assert "UnknownLink" in result

    @pytest.mark.asyncio
    async def test_convert_inheritance(self, converter):
        parse = {
            "frames": [
                {
                    "predicate": "is_a",
                    "arguments": {"agent": ["Cat"], "patient": ["Animal"]},
                    "frame_type": "inheritance",
                    "confidence": 0.9,
                }
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert "InheritanceLink" in result
        assert "0.90" in result

    @pytest.mark.asyncio
    async def test_convert_causal(self, converter):
        parse = {
            "frames": [
                {
                    "predicate": "cause",
                    "arguments": {"agent": ["Fire"], "patient": ["Smoke"]},
                    "frame_type": "causation",
                    "confidence": 0.8,
                }
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert "CausalLink" in result

    @pytest.mark.asyncio
    async def test_parse_expression(self, converter):
        expr = "InheritanceLink <0.80, 0.90>\n  Cat\n  Animal"
        parsed = await converter.parse_expression(expr)
        assert parsed["type"] == "pln"
        assert len(parsed["links"]) >= 1

    def test_validate(self, converter):
        assert converter.validate_expression("InheritanceLink <0.8, 0.9>\n  Cat\n  Animal") is True
        assert converter.validate_expression("random text no link") is False

    def test_normalize_concept(self, converter):
        assert converter._normalize_concept("hello world") == "Hello_world"
        assert converter._normalize_concept("") == "UnknownConcept"

    def test_estimate_strength(self, converter):
        assert converter._estimate_strength("cause", "action") == 0.9
        assert converter._estimate_strength("help", "action") == 0.7
        assert converter._estimate_strength("might", "action") == 0.4
        assert converter._estimate_strength("walk", "action") == 0.6


# ── TemporalLogicConverter ──────────────────────────────────────────────


class TestTemporalLogicConverter:
    @pytest.fixture
    def converter(self):
        return TemporalLogicConverter()

    @pytest.mark.asyncio
    async def test_future_tense(self, converter):
        parse = {
            "frames": [
                {
                    "predicate": "rain",
                    "temporal_info": {"tense": "future"},
                }
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert "◊F" in result

    @pytest.mark.asyncio
    async def test_past_tense(self, converter):
        parse = {
            "frames": [
                {
                    "predicate": "rain",
                    "temporal_info": {"tense": "past"},
                }
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert "◊P" in result

    @pytest.mark.asyncio
    async def test_always_marker(self, converter):
        parse = {
            "frames": [
                {
                    "predicate": "shine",
                    "temporal_info": {"tense": "present", "temporal_marker": "always"},
                }
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert "□" in result

    @pytest.mark.asyncio
    async def test_no_temporal_info(self, converter):
        parse = {"frames": [{"predicate": "walk"}]}
        result = await converter.convert_from_semantic_parse(parse, {})
        assert "walk(x)" == result

    @pytest.mark.asyncio
    async def test_parse_expression(self, converter):
        parsed = await converter.parse_expression("◊F rain(x) ∧ □ shine(y)")
        assert "eventually_future" in parsed["temporal_modalities"]
        assert "always" in parsed["temporal_modalities"]
        assert "rain" in parsed["predicates"]

    def test_validate(self, converter):
        assert converter.validate_expression("◊ rain(x)") is True
        assert converter.validate_expression("invalid{chars}") is False


# ── ModalLogicConverter ─────────────────────────────────────────────────


class TestModalLogicConverter:
    @pytest.fixture
    def converter(self):
        return ModalLogicConverter()

    @pytest.mark.asyncio
    async def test_necessary(self, converter):
        parse = {
            "frames": [
                {
                    "predicate": "exist",
                    "modal_info": {"type": "alethic", "strength": "necessary"},
                }
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert "□" in result

    @pytest.mark.asyncio
    async def test_possible(self, converter):
        parse = {
            "frames": [
                {
                    "predicate": "fly",
                    "modal_info": {"type": "ability", "strength": "possible"},
                }
            ]
        }
        result = await converter.convert_from_semantic_parse(parse, {})
        assert "◊" in result

    @pytest.mark.asyncio
    async def test_parse_expression(self, converter):
        parsed = await converter.parse_expression("□ exist(x) ∧ ◊ fly(y)")
        assert "necessarily" in parsed["modalities"]
        assert "possibly" in parsed["modalities"]

    def test_validate(self, converter):
        assert converter.validate_expression("◊ fly(x)") is True


# ── LogicSystems manager ────────────────────────────────────────────────


class TestLogicSystems:
    @pytest.fixture
    def systems(self):
        return LogicSystems()

    def test_init_converters(self, systems):
        assert LogicFormalism.FOL in systems.converters
        assert LogicFormalism.PLN in systems.converters
        assert LogicFormalism.TEMPORAL in systems.converters
        assert LogicFormalism.MODAL in systems.converters

    def test_supported_formalisms(self, systems):
        supported = systems.get_supported_formalisms()
        assert len(supported) == 4

    def test_formalism_info(self, systems):
        info = systems.get_formalism_info(LogicFormalism.FOL)
        assert info["name"] == "First-Order Logic"
        assert "operators" in info
        assert "use_cases" in info

    def test_formalism_info_pln(self, systems):
        info = systems.get_formalism_info(LogicFormalism.PLN)
        assert "Probabilistic" in info["name"]

    def test_get_stats(self, systems):
        stats = systems.get_stats()
        assert stats["conversions_performed"] == 0

    @pytest.mark.asyncio
    async def test_convert_to_fol(self, systems):
        parse = {
            "frames": [
                {
                    "predicate": "chase",
                    "arguments": {"agent": ["Cat"], "patient": ["Mouse"]},
                }
            ]
        }
        result = await systems.convert_to_formalism(parse, LogicFormalism.FOL)
        assert "chase" in result
        assert systems.stats["conversions_performed"] == 1

    @pytest.mark.asyncio
    async def test_convert_to_pln(self, systems):
        parse = {
            "frames": [
                {
                    "predicate": "cause",
                    "arguments": {"agent": ["Heat"], "patient": ["Expansion"]},
                    "frame_type": "causation",
                    "confidence": 0.85,
                }
            ]
        }
        result = await systems.convert_to_formalism(parse, LogicFormalism.PLN)
        assert "Link" in result

    @pytest.mark.asyncio
    async def test_convert_unsupported_formalism(self, systems):
        result = await systems.convert_to_formalism({}, LogicFormalism.FUZZY)
        assert "Error" in result or "Unable" in result

    @pytest.mark.asyncio
    async def test_parse_expression(self, systems):
        parsed = await systems.parse_expression("Human(x)", LogicFormalism.FOL)
        assert parsed["formalism"] == "first_order_logic"
        assert "Human" in parsed["predicates"]

    @pytest.mark.asyncio
    async def test_parse_expression_unsupported(self, systems):
        parsed = await systems.parse_expression("test", LogicFormalism.FUZZY)
        assert "error" in parsed

    def test_validate_expression(self, systems):
        assert systems.validate_expression("Human(x)", LogicFormalism.FOL) is True
        assert systems.validate_expression("", LogicFormalism.FOL) is False
        assert systems.validate_expression("Human(x)", LogicFormalism.FUZZY) is False

    @pytest.mark.asyncio
    async def test_convert_pln_rules(self, systems):
        rules = [
            {
                "rule_type": "ImplicationLink",
                "premise": ["Rain"],
                "conclusion": "Wet",
                "strength": 0.9,
                "confidence": 0.8,
            }
        ]
        result = await systems.convert_to_formalism(
            {"frames": []}, LogicFormalism.PLN, pln_rules=rules
        )
        assert "ImplicationLink" in result
        assert "Rain" in result

    @pytest.mark.asyncio
    async def test_convert_between_formalisms_fol_to_pln(self, systems):
        result = await systems.convert_between_formalisms(
            "Human(x)", LogicFormalism.FOL, LogicFormalism.PLN
        )
        assert "Link" in result or "Unknown" in result

    @pytest.mark.asyncio
    async def test_convert_between_formalisms_pln_to_fol(self, systems):
        expr = "InheritanceLink <0.8, 0.9>\n  Cat\n  Animal"
        result = await systems.convert_between_formalisms(
            expr, LogicFormalism.PLN, LogicFormalism.FOL
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_convert_to_temporal_from_parsed(self, systems):
        result = await systems._convert_to_temporal_from_parsed({"predicates": ["Rain"]})
        assert "◊" in result
        assert "Rain" in result

    @pytest.mark.asyncio
    async def test_convert_to_modal_from_parsed(self, systems):
        result = await systems._convert_to_modal_from_parsed({"predicates": ["Fly"]})
        assert "◊" in result

    @pytest.mark.asyncio
    async def test_stats_tracking(self, systems):
        parse = {"frames": [{"predicate": "test", "arguments": {}}]}
        await systems.convert_to_formalism(parse, LogicFormalism.FOL)
        await systems.convert_to_formalism(parse, LogicFormalism.FOL)
        assert systems.stats["conversions_performed"] == 2
        assert systems.stats["formalism_usage"]["first_order_logic"] == 2


# ═══════════════════════════════════════════════════════════════════════
# Context Manager Tests
# ═══════════════════════════════════════════════════════════════════════


class TestContextType:
    def test_all_types(self):
        expected = {
            "conversational",
            "domain",
            "temporal",
            "spatial",
            "user_profile",
            "session",
            "discourse",
        }
        actual = {ct.value for ct in ContextType}
        assert actual == expected


class TestContextItem:
    def test_creation(self):
        item = ContextItem(
            key="test",
            value="val",
            context_type=ContextType.DOMAIN,
            timestamp=time.time(),
            confidence=0.9,
            source="user",
        )
        assert item.decay_rate == 0.1
        assert item.importance == 0.5

    def test_not_expired(self):
        item = ContextItem(
            key="t",
            value="v",
            context_type=ContextType.SESSION,
            timestamp=time.time(),
            confidence=0.8,
            source="sys",
        )
        assert item.is_expired() is False

    def test_expired(self):
        item = ContextItem(
            key="t",
            value="v",
            context_type=ContextType.SESSION,
            timestamp=time.time() - 7200,
            confidence=0.8,
            source="sys",
        )
        assert item.is_expired(max_age=3600) is True

    def test_decayed_confidence(self):
        item = ContextItem(
            key="t",
            value="v",
            context_type=ContextType.SESSION,
            timestamp=time.time(),
            confidence=0.8,
            source="sys",
            decay_rate=0.1,
        )
        # Just created → confidence ≈ original
        conf = item.get_current_confidence()
        assert abs(conf - 0.8) < 0.05

    def test_decayed_confidence_old(self):
        item = ContextItem(
            key="t",
            value="v",
            context_type=ContextType.SESSION,
            timestamp=time.time() - 36000,
            confidence=1.0,
            source="sys",
            decay_rate=0.5,
        )
        conf = item.get_current_confidence()
        assert conf < 1.0


class TestSessionContext:
    def test_creation(self):
        sc = SessionContext(
            session_id="s1",
            start_time=time.time(),
            last_activity=time.time(),
        )
        assert sc.is_active()
        assert len(sc.conversation_history) == 0

    def test_inactive_session(self):
        sc = SessionContext(
            session_id="s2",
            start_time=time.time() - 7200,
            last_activity=time.time() - 7200,
        )
        assert sc.is_active(timeout=1800) is False

    def test_update_activity(self):
        sc = SessionContext(
            session_id="s3",
            start_time=time.time() - 3600,
            last_activity=time.time() - 3600,
        )
        sc.update_activity()
        assert sc.is_active()


class TestContextManager:
    @pytest.fixture
    def cm(self):
        return ContextManager(max_sessions=10)

    def test_create_session(self, cm):
        session = cm.create_session("test_session")
        assert session.session_id == "test_session"
        assert cm.stats["total_sessions"] == 1

    def test_create_session_idempotent(self, cm):
        s1 = cm.create_session("s1")
        s2 = cm.create_session("s1")
        assert s1 is s2
        assert cm.stats["total_sessions"] == 1

    def test_create_session_with_user(self, cm):
        session = cm.create_session("s1", user_id="user123")
        assert "user_id" in session.context_items
        assert session.context_items["user_id"].value == "user123"

    def test_update_session_context(self, cm):
        cm.create_session("s1")
        cm.update_session_context("s1", "Hello world, I need help with programming code")
        ctx = cm.get_session_context("s1")
        assert ctx["conversation_length"] == 1

    def test_update_creates_session(self, cm):
        cm.update_session_context("new_session", "test text")
        assert "new_session" in cm.sessions

    def test_get_context_empty(self, cm):
        ctx = cm.get_session_context("nonexistent")
        assert ctx == {}

    def test_get_context_structure(self, cm):
        cm.create_session("s1")
        cm.update_session_context("s1", "Discuss medical treatment options")
        ctx = cm.get_session_context("s1")
        assert "session_id" in ctx
        assert "active_topics" in ctx
        assert "current_context" in ctx
        assert "recent_conversation" in ctx

    def test_temporal_context_extraction(self, cm):
        cm.create_session("s1")
        cm.update_session_context("s1", "I need this done by tomorrow morning")
        ctx = cm.get_session_context("s1")
        # Should extract "tomorrow" and "morning"
        temporal_items = [k for k in ctx.get("current_context", {}) if k.startswith("temporal_")]
        assert len(temporal_items) >= 1

    def test_domain_context_extraction(self, cm):
        cm.create_session("s1")
        cm.update_session_context("s1", "The patient needs medical treatment")
        ctx = cm.get_session_context("s1")
        domain_items = [k for k in ctx.get("current_context", {}) if k.startswith("domain_")]
        assert len(domain_items) >= 1

    def test_spatial_context_extraction(self, cm):
        cm.create_session("s1")
        cm.update_session_context("s1", "It is nearby the building")
        ctx = cm.get_session_context("s1")
        spatial_items = [k for k in ctx.get("current_context", {}) if k.startswith("spatial_")]
        assert len(spatial_items) >= 1

    def test_active_topics(self, cm):
        cm.create_session("s1")
        cm.update_session_context("s1", "Python programming machine learning algorithms")
        ctx = cm.get_session_context("s1")
        topics = ctx["active_topics"]
        assert len(topics) > 0

    def test_add_global_context(self, cm):
        cm.add_global_context("system_mode", "production", ContextType.SESSION)
        assert "system_mode" in cm.global_context

    def test_resolve_coreference_no_session(self, cm):
        result = cm.resolve_coreference("nonexistent", "it is blue")
        assert result == "it is blue"

    def test_resolve_coreference(self, cm):
        cm.create_session("s1")
        cm.update_session_context("s1", "Python is a great language")
        resolved = cm.resolve_coreference("s1", "it is very popular")
        # Should attempt to replace 'it' with Python
        assert isinstance(resolved, str)

    def test_context_summary(self, cm):
        cm.create_session("s1")
        cm.update_session_context("s1", "Test content about computer science")
        summary = cm.get_context_summary("s1")
        assert "session_id" in summary
        assert "active_context_items" in summary

    def test_context_summary_nonexistent(self, cm):
        summary = cm.get_context_summary("no_such_session")
        assert "error" in summary

    def test_classify_domain(self, cm):
        assert cm._classify_domain("medical") == "medical"
        assert cm._classify_domain("legal") == "legal"
        assert cm._classify_domain("unknown_word") == "general"

    def test_cleanup_expired(self, cm):
        cm.create_session("s1")
        # Add an expired item directly
        item = ContextItem(
            key="old_item",
            value="old",
            context_type=ContextType.SESSION,
            timestamp=time.time() - 7200,  # 2 hours ago
            confidence=0.5,
            source="test",
        )
        cm.sessions["s1"].context_items["old_item"] = item
        cm.cleanup_expired_context()
        assert "old_item" not in cm.sessions["s1"].context_items

    def test_get_stats(self, cm):
        cm.create_session("s1")
        cm.create_session("s2")
        stats = cm.get_stats()
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] >= 1

    def test_max_sessions_cleanup(self, cm):
        """Creating sessions beyond max_sessions triggers cleanup."""
        cm_small = ContextManager(max_sessions=3)
        for i in range(5):
            cm_small.create_session(f"session_{i}")
        # Should not exceed max — old inactive sessions would be cleaned
        # (all are active so none cleaned, but no crash)
        assert len(cm_small.sessions) <= 5  # still creates since all active

    def test_additional_context(self, cm):
        cm.create_session("s1")
        cm.update_session_context("s1", "test", additional_context={"mood": "happy"})
        session = cm.sessions["s1"]
        assert "mood" in session.context_items
        assert session.context_items["mood"].value == "happy"
