#!/usr/bin/env python3
"""
Hyperon/MORK Integration - Basic Usage Demo
===========================================

Demonstrates basic usage of the hyperon/MORK integration with Kenny AGI,
including knowledge creation, reasoning, and storage operations.

This example shows:
1. Setting up the integration
2. Creating knowledge using MeTTa
3. Performing PLN reasoning
4. Storing and retrieving data with MORK
5. Running integration tests

Run: python basic_usage_demo.py
"""

import asyncio
import time
import json
import sys
import os

# Add the integration path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from integrations.hyperon_mork import (
    create_development_integration,
    create_test_integration,
    HyperonMORKIntegrationManager,
    IntegrationConfig,
    IntegrationMode
)


async def basic_knowledge_creation():
    """Demonstrate basic knowledge creation and querying"""
    print("🧠 Basic Knowledge Creation Demo")
    print("=" * 50)
    
    async with create_development_integration() as integration:
        # Create knowledge using MeTTa language
        print("Creating knowledge using MeTTa...")
        
        metta_knowledge = '''
        ; Create concepts for animals
        (ConceptNode "cat")
        (ConceptNode "dog") 
        (ConceptNode "bird")
        (ConceptNode "mammal")
        (ConceptNode "animal")
        (ConceptNode "pet")
        
        ; Define taxonomic relationships
        (InheritanceLink (ConceptNode "cat") (ConceptNode "mammal"))
        (InheritanceLink (ConceptNode "dog") (ConceptNode "mammal"))
        (InheritanceLink (ConceptNode "mammal") (ConceptNode "animal"))
        
        ; Define functional relationships
        (InheritanceLink (ConceptNode "cat") (ConceptNode "pet"))
        (InheritanceLink (ConceptNode "dog") (ConceptNode "pet"))
        
        ; Add some properties
        (EvaluationLink 
            (PredicateNode "has_property")
            (ListLink 
                (ConceptNode "cat") 
                (ConceptNode "furry")))
                
        (EvaluationLink 
            (PredicateNode "has_property")
            (ListLink 
                (ConceptNode "dog") 
                (ConceptNode "loyal")))
        '''
        
        # Create the knowledge
        knowledge_spec = {
            'metta_code': metta_knowledge,
            'storage_entries': {
                'knowledge_metadata': {
                    'domain': 'animals',
                    'created_by': 'demo_script',
                    'version': '1.0',
                    'timestamp': time.time()
                },
                'taxonomy_info': {
                    'hierarchy_levels': 3,
                    'concept_count': 7,
                    'relationship_count': 6
                }
            }
        }
        
        creation_results = await integration.create_knowledge(knowledge_spec)
        
        print(f"✅ Created {len(creation_results.get('created_atoms', []))} atoms")
        print(f"✅ Stored {len(creation_results.get('stored_entries', []))} storage entries")
        print(f"⏱️  Processing time: {creation_results.get('processing_time', 0):.3f}s")
        
        if creation_results.get('errors'):
            print(f"⚠️  Errors: {creation_results['errors']}")
        
        return creation_results


async def reasoning_demo():
    """Demonstrate PLN reasoning capabilities"""
    print("\n🤖 PLN Reasoning Demo")
    print("=" * 30)
    
    async with create_development_integration() as integration:
        
        # First create some knowledge to reason about
        setup_knowledge = '''
        (ConceptNode "socrates")
        (ConceptNode "human")
        (ConceptNode "mortal")
        
        (InheritanceLink (ConceptNode "socrates") (ConceptNode "human"))
        (InheritanceLink (ConceptNode "human") (ConceptNode "mortal"))
        '''
        
        await integration.create_knowledge({'metta_code': setup_knowledge})
        print("✅ Created base knowledge for reasoning")
        
        # Perform forward chaining reasoning
        reasoning_query = {
            'type': 'reasoning',
            'query_type': 'forward_chain',
            'max_iterations': 10,
            'min_confidence': 0.1
        }
        
        print("🔄 Running forward chaining inference...")
        reasoning_results = await integration.query_knowledge(reasoning_query)
        
        if 'reasoning_results' in reasoning_results:
            results = reasoning_results['reasoning_results']
            print(f"✅ Generated {results.get('total_inferences', 0)} inferences")
            print(f"✅ Analyzed {results.get('communities_analyzed', 0)} reasoning paths")
            print(f"⏱️  Processing time: {results.get('processing_time', 0):.3f}s")
            
            # Show some inference results
            if results.get('results'):
                print("\n📋 Sample Inferences:")
                for i, inference in enumerate(results['results'][:3]):
                    print(f"  {i+1}. {inference.get('explanation', 'No explanation')}")
                    print(f"     Rule: {inference.get('rule_applied', 'Unknown')}")
                    print(f"     Confidence: {inference.get('confidence', 0):.2f}")
        
        return reasoning_results


async def storage_operations_demo():
    """Demonstrate MORK storage operations"""
    print("\n💾 MORK Storage Demo")
    print("=" * 25)
    
    async with create_development_integration() as integration:
        
        # Store various types of data
        storage_data = {
            'simple_concept': {
                'type': 'concept',
                'name': 'elephant',
                'properties': ['large', 'intelligent', 'mammal'],
                'confidence': 0.95
            },
            'complex_relationship': {
                'type': 'relationship',
                'subject': 'elephant',
                'predicate': 'lives_in',
                'object': 'africa',
                'evidence': [
                    {'source': 'wikipedia', 'confidence': 0.9},
                    {'source': 'nature_doc', 'confidence': 0.85}
                ]
            },
            'numerical_data': {
                'measurements': [1.5, 2.3, 4.1, 6.8],
                'statistics': {
                    'mean': 3.675,
                    'std': 2.234,
                    'count': 4
                }
            },
            'metadata': {
                'created': time.time(),
                'version': '1.0',
                'tags': ['demo', 'storage', 'test']
            }
        }
        
        print("💾 Storing data in MORK...")
        storage_spec = {
            'storage_entries': storage_data
        }
        
        store_results = await integration.create_knowledge(storage_spec)
        print(f"✅ Stored {len(store_results.get('stored_entries', []))} entries")
        
        # Retrieve data
        print("🔍 Retrieving stored data...")
        
        for key in storage_data.keys():
            query = {
                'type': 'storage',
                'key': key
            }
            
            query_results = await integration.query_knowledge(query)
            
            if query_results.get('storage_results'):
                retrieved = query_results['storage_results'][0]
                print(f"✅ Retrieved '{key}': {type(retrieved['value']).__name__}")
            else:
                print(f"❌ Failed to retrieve '{key}'")
        
        # Pattern-based retrieval
        pattern_query = {
            'type': 'storage', 
            'key_pattern': 'concept'
        }
        
        pattern_results = await integration.query_knowledge(pattern_query)
        matching_keys = len(pattern_results.get('storage_results', []))
        print(f"🔍 Pattern search found {matching_keys} matching entries")
        
        return store_results


async def integration_test_demo():
    """Demonstrate running integration tests"""
    print("\n🧪 Integration Test Demo")
    print("=" * 30)
    
    # Use test-specific integration
    async with create_test_integration() as integration:
        
        print("🏃 Running compatibility tests...")
        
        # Run a subset of tests for demo purposes
        test_results = await integration.run_tests()
        
        if test_results:
            summary = test_results.get('summary', {})
            
            print(f"✅ Tests completed:")
            print(f"   Total: {summary.get('total_tests', 0)}")
            print(f"   Passed: {summary.get('passed', 0)}")
            print(f"   Failed: {summary.get('failed', 0)}")
            print(f"   Success Rate: {summary.get('success_rate', 0):.1%}")
            print(f"   Duration: {summary.get('total_time', 0):.1f}s")
            
            # Show benchmark results
            benchmarks = test_results.get('benchmarks', [])
            if benchmarks:
                print("\n📊 Performance Benchmarks:")
                for benchmark in benchmarks[:5]:  # Show first 5
                    ops_per_sec = benchmark.get('operations_per_second', 0)
                    test_name = benchmark.get('test_name', 'Unknown')
                    print(f"   {test_name}: {ops_per_sec:,.0f} ops/sec")
        
        return test_results


async def performance_monitoring_demo():
    """Demonstrate performance monitoring capabilities"""
    print("\n📊 Performance Monitoring Demo")
    print("=" * 40)
    
    # Use development integration with metrics enabled
    config = IntegrationConfig(
        mode=IntegrationMode.DEVELOPMENT,
        enable_metrics=True,
        atomspace_size=50000,
        sync_interval=1.0
    )
    
    async with HyperonMORKIntegrationManager(config) as integration:
        
        # Perform some operations to generate metrics
        print("🔄 Generating activity for metrics...")
        
        # Create knowledge
        knowledge = {
            'metta_code': '''
            (ConceptNode "test_concept_1")
            (ConceptNode "test_concept_2")
            (InheritanceLink (ConceptNode "test_concept_1") (ConceptNode "test_concept_2"))
            ''',
            'storage_entries': {
                f'perf_test_{i}': {'index': i, 'data': f'test_{i}'}
                for i in range(100)
            }
        }
        
        await integration.create_knowledge(knowledge)
        
        # Perform queries
        for i in range(10):
            await integration.query_knowledge({
                'type': 'atomspace',
                'atom_type': 'ConceptNode'
            })
            
            await integration.query_knowledge({
                'type': 'storage',
                'key': f'perf_test_{i}'
            })
        
        # Wait a moment for metrics to update
        await asyncio.sleep(2)
        
        # Display status
        status = integration.get_status()
        print("📈 System Status:")
        print(f"   Uptime: {status['uptime']:.1f}s")
        print(f"   Mode: {status['mode']}")
        print(f"   Initialized: {status['initialized']}")
        
        print("\n🔧 Component Status:")
        for name, info in status['components'].items():
            print(f"   {name}: {info['status']} ({info['initialization_time']:.3f}s init)")
        
        # Display detailed metrics
        metrics = integration.get_performance_metrics()
        global_metrics = metrics['global']
        
        print("\n📊 Performance Metrics:")
        print(f"   Operations processed: {global_metrics['operations_processed']}")
        print(f"   Average response time: {global_metrics['average_response_time']:.3f}s")
        print(f"   Operations per second: {global_metrics.get('operations_per_second', 0):.1f}")
        print(f"   Errors encountered: {global_metrics['errors_encountered']}")
        print(f"   Memory usage: {global_metrics['memory_usage'] / 1024 / 1024:.1f} MB")
        
        # Component-specific metrics
        print("\n🔍 Component Metrics:")
        for component, comp_metrics in metrics['components'].items():
            if comp_metrics:
                print(f"   {component}:")
                for key, value in comp_metrics.items():
                    if isinstance(value, (int, float)):
                        if 'time' in key.lower():
                            print(f"     {key}: {value:.3f}s")
                        elif 'per_second' in key.lower():
                            print(f"     {key}: {value:.1f}")
                        else:
                            print(f"     {key}: {value}")
        
        return metrics


async def main():
    """Run all demos"""
    print("🎯 Hyperon/MORK Integration - Basic Usage Demo")
    print("=" * 60)
    print("This demo showcases the key features of the hyperon/MORK integration")
    print("with Kenny AGI, including knowledge creation, reasoning, and storage.\n")
    
    try:
        # Run all demos
        await basic_knowledge_creation()
        await reasoning_demo()
        await storage_operations_demo()
        await integration_test_demo()
        await performance_monitoring_demo()
        
        print("\n" + "=" * 60)
        print("✅ All demos completed successfully!")
        print("🎉 The hyperon/MORK integration is working properly.")
        print("\nNext steps:")
        print("  - Explore the advanced examples in the examples/ directory")
        print("  - Read the full documentation in docs/README.md")
        print("  - Try the interactive MeTTa REPL")
        print("  - Run the complete test suite")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)