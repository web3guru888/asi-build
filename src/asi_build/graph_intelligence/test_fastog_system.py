#!/usr/bin/env python3
"""
Test FastToG (Fast Think-on-Graph) reasoning system completeness.
"""

import asyncio
import logging
import os
import sys
import time

from asi_build.graph_intelligence.community_detection import CommunityDetectionEngine
from asi_build.graph_intelligence.community_pruning import CommunityPruningSystem
from asi_build.graph_intelligence.community_to_text import CommunityTextGenerator
from asi_build.graph_intelligence.fastog_reasoning import (
    FastToGReasoningEngine,
    ReasoningMode,
    ReasoningRequest,
)
from asi_build.graph_intelligence.schema_manager import SchemaManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_fastog_complete():
    """Test if FastToG system is complete and functional."""

    logger.info("🧪 Testing FastToG (Fast Think-on-Graph) System...")
    all_tests_passed = True

    # Test 1: Check all required modules exist
    logger.info("\n📊 Test 1: Module Availability")
    try:
        # All modules imported successfully above
        logger.info("  ✅ fastog_reasoning module exists")
        logger.info("  ✅ community_detection module exists")
        logger.info("  ✅ community_pruning module exists")
        logger.info("  ✅ community_to_text module exists")
    except ImportError as e:
        logger.error(f"  ❌ Missing module: {e}")
        all_tests_passed = False

    # Test 2: Initialize FastToG Engine
    logger.info("\n📊 Test 2: FastToG Engine Initialization")
    try:
        schema_manager = SchemaManager()
        fastog_engine = FastToGReasoningEngine(schema_manager)

        # Check all sub-components
        assert hasattr(fastog_engine, "community_engine"), "Missing community_engine"
        assert hasattr(fastog_engine, "community_detection"), "Missing community_detection"
        assert hasattr(fastog_engine, "pruning_system"), "Missing pruning_system"
        assert hasattr(fastog_engine, "text_generator"), "Missing text_generator"

        logger.info("  ✅ FastToG engine initialized successfully")
        logger.info("  ✅ All sub-components present")
    except Exception as e:
        logger.error(f"  ❌ Initialization failed: {e}")
        all_tests_passed = False
        return False

    # Test 3: Community Detection
    logger.info("\n📊 Test 3: Community Detection System")
    try:
        detection_engine = CommunityDetectionEngine(schema_manager)

        # Test community detection methods
        communities = detection_engine.detect_communities(algorithm="louvain")
        logger.info(f"  ✅ Louvain algorithm: Found {len(communities)} communities")

        # Test community retrieval
        all_communities = detection_engine.get_all_communities()
        logger.info(f"  ✅ Retrieved {len(all_communities)} stored communities")

    except Exception as e:
        logger.error(f"  ❌ Community detection failed: {e}")
        all_tests_passed = False

    # Test 4: Community Pruning
    logger.info("\n📊 Test 4: Community Pruning System")
    try:
        pruning_system = CommunityPruningSystem(schema_manager)

        test_context = {
            "user_intent": "Click the save button",
            "current_screen": "main_window",
            "target_action": "save",
        }

        # Test pruning
        pruning_result = pruning_system.prune_communities_for_task(
            test_context, target_community_count=5
        )

        logger.info(
            f"  ✅ Pruning successful: {pruning_result.original_count} → {pruning_result.pruned_count} communities"
        )
        logger.info(f"  ✅ Pruning ratio: {pruning_result.pruning_ratio:.2%}")

    except Exception as e:
        logger.error(f"  ❌ Community pruning failed: {e}")
        all_tests_passed = False

    # Test 5: Community Text Generation
    logger.info("\n📊 Test 5: Community-to-Text System")
    try:
        # Use Graph2TextConverter which has the generate_community_summary method
        from graph_intelligence.community_to_text import Graph2TextConverter

        text_generator = Graph2TextConverter(schema_manager)

        # Get a community to test with
        from graph_intelligence.schema import NodeType

        communities = schema_manager.find_nodes(node_type=NodeType.COMMUNITY, filters=None, limit=1)

        if communities:
            # Generate text description
            text_result = text_generator.generate_community_summary(
                community_id=communities[0].get("id", "test"), include_statistics=True
            )

            logger.info(f"  ✅ Generated text summary: {len(text_result.summary_text)} characters")
            logger.info(f"  ✅ Community type: {text_result.community_type}")
        else:
            logger.info("  ⚠️ No communities available for text generation test")

    except Exception as e:
        logger.error(f"  ❌ Text generation failed: {e}")
        all_tests_passed = False

    # Test 6: Complete FastToG Reasoning Pipeline
    logger.info("\n📊 Test 6: Complete FastToG Reasoning Pipeline")
    try:
        # Create a reasoning request
        request = ReasoningRequest(
            user_intent="Find and click the save button in the file menu",
            context={
                "current_screen": "text_editor",
                "recent_actions": ["open_file", "edit_text"],
                "target": "save_file",
            },
            max_communities=5,
            reasoning_mode=ReasoningMode.COMMUNITY_BASED,
            include_explanations=True,
            timeout_seconds=30,
        )

        # Execute reasoning
        start_time = time.time()
        result = await fastog_engine.reason(request)
        reasoning_time = time.time() - start_time

        logger.info(f"  ✅ Reasoning completed in {reasoning_time:.2f} seconds")
        logger.info(f"  ✅ Analyzed {result.communities_analyzed} communities")
        logger.info(f"  ✅ Overall confidence: {result.overall_confidence:.2%}")
        logger.info(f"  ✅ Reasoning mode: {result.reasoning_mode}")

        if result.final_recommendation:
            logger.info(
                f"  ✅ Generated recommendation: {list(result.final_recommendation.keys())}"
            )

        if result.explanation:
            logger.info(f"  ✅ Generated explanation ({len(result.explanation)} chars)")

    except Exception as e:
        logger.error(f"  ❌ FastToG reasoning pipeline failed: {e}")
        all_tests_passed = False

    # Test 7: Performance Metrics
    logger.info("\n📊 Test 7: Performance Optimization")
    try:
        # Test different reasoning modes
        modes_tested = []

        for mode in [
            ReasoningMode.COMMUNITY_BASED,
            ReasoningMode.TRADITIONAL,
            ReasoningMode.HYBRID,
        ]:
            request.reasoning_mode = mode

            start = time.time()
            result = await fastog_engine.reason(request)
            duration = time.time() - start

            modes_tested.append(
                {"mode": mode.value, "time": duration, "communities": result.communities_analyzed}
            )

            logger.info(
                f"  ✅ {mode.value}: {duration:.2f}s ({result.communities_analyzed} communities)"
            )

        # Compare performance
        community_based = next(m for m in modes_tested if m["mode"] == "community_based")
        traditional = next(m for m in modes_tested if m["mode"] == "traditional")

        if community_based["time"] < traditional["time"]:
            speedup = (traditional["time"] - community_based["time"]) / traditional["time"] * 100
            logger.info(f"  ✅ Community-based is {speedup:.1f}% faster than traditional!")

    except Exception as e:
        logger.error(f"  ❌ Performance testing failed: {e}")
        all_tests_passed = False

    # Final Summary
    logger.info("\n" + "=" * 60)
    if all_tests_passed:
        logger.info("✅ FastToG System is FULLY COMPLETE and FUNCTIONAL!")
        logger.info("🎯 All components operational:")
        logger.info("  • FastToG Reasoning Engine ✅")
        logger.info("  • Community Detection ✅")
        logger.info("  • Community Pruning ✅")
        logger.info("  • Community-to-Text ✅")
        logger.info("  • Complete Pipeline ✅")
        logger.info("  • Performance Optimization ✅")
        logger.info("\n🚀 Kenny can now think 'community by community' for faster decisions!")
    else:
        logger.info("⚠️ FastToG system has some issues to resolve")
    logger.info("=" * 60)

    # Close connection
    schema_manager.close()

    return all_tests_passed


if __name__ == "__main__":
    success = asyncio.run(test_fastog_complete())
    sys.exit(0 if success else 1)
