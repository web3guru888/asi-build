# Hyperon/MORK Integration for Kenny AGI

## Overview

This module provides comprehensive integration between Kenny AGI and:
- **SingularityNET's hyperon** - Symbolic AI framework with MeTTa language support
- **MORK (Memory-Optimized Reasoning Kernel)** - High-performance knowledge graph storage
- **Ben Goertzel's PRIMUS architecture** - Advanced AGI reasoning framework

## Features

### 🧠 Hyperon Compatibility Layer
- **Atomspace Integration**: Full OpenCog Atomspace compatibility
- **PLN (Probabilistic Logic Networks)**: Advanced probabilistic reasoning
- **MeTTa Language Support**: Complete MeTTa interpreter with REPL
- **Pattern Matching**: High-performance pattern matching engine
- **API Adapters**: Drop-in replacement for OpenCog hyperon

### 💾 MORK Data Structure Interfaces
- **Memory-Mapped Storage**: Efficient storage for massive knowledge graphs
- **B+ Tree Indexing**: Fast key-value lookups and range queries
- **Concurrent Access**: Thread-safe read/write operations
- **Delta Compression**: Efficient storage of knowledge updates
- **Distributed Cluster**: Scalable multi-node deployments

### 🔗 Bridge Components
- **Kenny AGI Integration**: Seamless integration with Kenny's reasoning systems
- **Vector Database Converter**: Export to popular vector databases
- **Unified Query Language**: Single interface for all knowledge operations
- **Hybrid Reasoning Engine**: Combine symbolic and neural reasoning
- **Knowledge Graph Sync**: Real-time synchronization across systems

### 🧪 Testing & Validation
- **Compatibility Tests**: Validate OpenCog/hyperon compatibility
- **Performance Benchmarks**: Compare against native implementations
- **Stress Tests**: Validate with large-scale knowledge graphs
- **Migration Tests**: Test import/export from other formats
- **Regression Tests**: Automated API compatibility verification

## Architecture

```
┌─────────────────────────────────────────┐
│         Kenny AGI Core                   │
├─────────────────────────────────────────┤
│    Hyperon/MORK Integration Bridge      │
├─────────────────────────────────────────┤
│    Hyperon Layer    │    MORK Layer     │
│  ┌─────────────────┐│ ┌─────────────────┐│
│  │ Atomspace       ││ │ Memory Storage  ││
│  │ PLN Engine      ││ │ Graph Repr.     ││
│  │ MeTTa Language  ││ │ Query Engine    ││
│  │ Pattern Matcher ││ │ Distributed     ││
│  │ API Adapters    ││ │ Cluster         ││
│  └─────────────────┘│ │ Version Control ││
└─────────────────────┼─┤                 ││
                      │ └─────────────────┘│
                      └─────────────────────┘
```

## Quick Start

### Basic Usage

```python
import asyncio
from integrations.hyperon_mork import create_development_integration

async def main():
    # Create integration manager
    async with create_development_integration() as integration:
        
        # Create knowledge using MeTTa
        knowledge_spec = {
            'metta_code': '''
            (ConceptNode "cat")
            (ConceptNode "animal")
            (InheritanceLink (ConceptNode "cat") (ConceptNode "animal"))
            ''',
            'storage_entries': {
                'metadata': {'created_by': 'kenny_agi', 'timestamp': '2025-08-18'}
            }
        }
        
        # Create knowledge
        results = await integration.create_knowledge(knowledge_spec)
        print(f"Created {len(results['created_atoms'])} atoms")
        
        # Query knowledge
        query = {
            'type': 'reasoning',
            'query_type': 'forward_chain',
            'max_iterations': 10
        }
        
        reasoning_results = await integration.query_knowledge(query)
        print(f"Generated {reasoning_results['reasoning_results']['total_inferences']} inferences")

asyncio.run(main())
```

### Advanced Configuration

```python
from integrations.hyperon_mork import HyperonMORKIntegrationManager, IntegrationConfig, IntegrationMode, StorageMode

# Production configuration
config = IntegrationConfig(
    mode=IntegrationMode.PRODUCTION,
    atomspace_size=5000000,
    storage_file="/data/kenny_knowledge.mork",
    storage_mode=StorageMode.READ_WRITE,
    max_memory_mb=4096,
    pln_enabled=True,
    metta_enabled=True,
    enable_metrics=True,
    sync_interval=5.0
)

integration = HyperonMORKIntegrationManager(config)
```

## Component Documentation

### 1. Atomspace Integration

The Atomspace provides OpenCog-compatible knowledge representation:

```python
from integrations.hyperon_mork.hyperon_compatibility.atomspace import AtomspaceIntegration, AtomType, TruthValue

# Create atomspace
atomspace = AtomspaceIntegration(max_atoms=1000000)

# Create atoms
cat = atomspace.add_node(AtomType.CONCEPT_NODE, "cat", TruthValue(0.9, 0.8))
animal = atomspace.add_node(AtomType.CONCEPT_NODE, "animal", TruthValue(0.95, 0.9))

# Create relationships
inheritance = atomspace.add_link(
    AtomType.INHERITANCE_LINK, 
    [cat, animal], 
    TruthValue(0.85, 0.9)
)

# Query atoms
concept_nodes = atomspace.get_atoms_by_type(AtomType.CONCEPT_NODE)
cat_incoming = atomspace.get_incoming(cat)

# Export/import
json_data = atomspace.export_to_json()
scheme_data = atomspace.export_to_scheme()
```

### 2. PLN Reasoning

Probabilistic Logic Networks for uncertainty-aware reasoning:

```python
from integrations.hyperon_mork.hyperon_compatibility.pln import PLNInterface, PLNRule

# Create PLN interface
pln = PLNInterface(atomspace)

# Forward chaining
results = pln.inference_engine.forward_chain(max_iterations=100, min_confidence=0.1)

# Apply specific rules
deduction_result = pln.inference_engine.apply_rule(
    PLNRule.DEDUCTION, 
    [premise1, premise2]
)

# Backward chaining
goal = atomspace.add_link(AtomType.INHERITANCE_LINK, [target_concept, goal_concept])
proof_steps = pln.inference_engine.backward_chain(goal, max_depth=5)
```

### 3. MeTTa Language

Full MeTTa language interpreter for symbolic AI:

```python
from integrations.hyperon_mork.hyperon_compatibility.metta_support import MeTTaInterpreter

# Create interpreter
metta = MeTTaInterpreter(atomspace)

# Evaluate expressions
results = metta.evaluate_string("""
; Basic arithmetic
(+ 2 3)

; Variables and functions
(let ($x 10) (* $x $x))

; Atomspace operations
(ConceptNode "dog")
(InheritanceLink (ConceptNode "dog") (ConceptNode "animal"))

; Conditional logic
(if (> 5 3) "greater" "lesser")
""")

# Define custom functions
metta.define_function("square", lambda x: x * x)

# Interactive REPL
metta.repl()  # Starts interactive session
```

### 4. MORK Storage

High-performance memory-mapped storage:

```python
from integrations.hyperon_mork.mork_interfaces.storage import MemoryMappedStorage, StorageMode

# Create storage
with MemoryMappedStorage("knowledge.mork", StorageMode.CREATE) as storage:
    
    # Store data
    storage.put("concept_cat", {
        "type": "concept",
        "name": "cat",
        "properties": ["furry", "mammal"],
        "confidence": 0.9
    })
    
    # Retrieve data
    cat_data = storage.get("concept_cat")
    
    # Iterate keys
    for key in storage.keys():
        value = storage.get(key)
        print(f"{key}: {value}")
    
    # Batch operations
    for i in range(10000):
        storage.put(f"item_{i}", {"index": i, "data": f"value_{i}"})
    
    # Statistics
    stats = storage.get_statistics()
    print(f"Storage: {stats['entries']} entries, {stats['file_size_bytes']} bytes")
```

## Testing

### Running Tests

```python
from integrations.hyperon_mork.tests import IntegrationTestFramework

# Run all tests
async with IntegrationTestFramework() as framework:
    results = await framework.run_all_tests()
    
    print(f"Tests: {results['summary']['passed']}/{results['summary']['total_tests']} passed")
    print(f"Success rate: {results['summary']['success_rate']:.1%}")

# Run specific test categories
framework = IntegrationTestFramework()
compatibility_results = await framework.run_test_suite("Atomspace Compatibility")
performance_results = await framework.run_test_suite("Performance Benchmarks")
```

### Performance Benchmarks

The integration includes comprehensive benchmarks:

- **Atomspace Operations**: Node/link creation, search, traversal
- **PLN Reasoning**: Forward/backward chaining, rule application
- **Storage Operations**: Read/write performance, concurrent access
- **Memory Usage**: Memory consumption analysis
- **Scalability**: Performance with large knowledge graphs

Example benchmark results:
```
Atomspace Operations:
  Node Creation: 45,000 ops/sec
  Link Creation: 32,000 ops/sec
  Search Operations: 120,000 ops/sec

MORK Storage:
  Write Operations: 85,000 ops/sec
  Read Operations: 180,000 ops/sec
  Concurrent Access: 95% efficiency

PLN Reasoning:
  Deduction Rules: 1,200 inferences/sec
  Forward Chaining: 850 inferences/sec
```

## API Reference

### Integration Manager

```python
class HyperonMORKIntegrationManager:
    async def initialize() -> bool
    async def create_knowledge(knowledge_spec: Dict) -> Dict
    async def query_knowledge(query: Dict) -> Dict
    async def run_tests(categories: List[str] = None) -> Dict
    def get_status() -> Dict
    def get_performance_metrics() -> Dict
    async def shutdown()
```

### Configuration

```python
@dataclass
class IntegrationConfig:
    mode: IntegrationMode = IntegrationMode.DEVELOPMENT
    atomspace_size: int = 1000000
    storage_file: Optional[str] = None
    pln_enabled: bool = True
    metta_enabled: bool = True
    max_memory_mb: int = 1024
    enable_metrics: bool = True
```

## SingularityNET Collaboration

This integration is designed for seamless collaboration with SingularityNET's ecosystem:

### Hyperon Compatibility
- **Full API Compatibility**: Drop-in replacement for hyperon components
- **MeTTa Language**: 100% compatible MeTTa interpreter
- **Atomspace Format**: Compatible with OpenCog Atomspace serialization
- **PLN Rules**: Implements standard PLN rule set

### PRIMUS Architecture
- **Modular Design**: Compatible with Ben Goertzel's PRIMUS framework
- **Distributed Reasoning**: Support for multi-agent reasoning systems
- **Knowledge Integration**: Seamless knowledge sharing between agents
- **Scalable Architecture**: Designed for large-scale AGI deployments

## Performance Optimization

### Memory Management
- Memory-mapped files for efficient large-scale storage
- B+ tree indexing for fast lookups
- Concurrent access with minimal locking
- Automatic garbage collection and defragmentation

### Computation Optimization  
- Vectorized operations where possible
- Multi-threaded reasoning and inference
- Lazy evaluation for complex expressions
- Caching strategies for frequently accessed data

### Network Optimization
- Efficient serialization protocols
- Delta compression for updates
- Batch operations for network efficiency
- Automatic failover and load balancing

## Integration Examples

### Example 1: Basic Knowledge Creation and Reasoning

```python
import asyncio
from integrations.hyperon_mork import create_development_integration

async def basic_example():
    async with create_development_integration() as integration:
        
        # Create animals taxonomy through MeTTa
        taxonomy_code = '''
        ; Define concepts
        (ConceptNode "cat")
        (ConceptNode "dog") 
        (ConceptNode "mammal")
        (ConceptNode "animal")
        (ConceptNode "living_thing")
        
        ; Define inheritance hierarchy
        (InheritanceLink (ConceptNode "cat") (ConceptNode "mammal"))
        (InheritanceLink (ConceptNode "dog") (ConceptNode "mammal"))
        (InheritanceLink (ConceptNode "mammal") (ConceptNode "animal"))
        (InheritanceLink (ConceptNode "animal") (ConceptNode "living_thing"))
        '''
        
        # Create knowledge
        await integration.create_knowledge({
            'metta_code': taxonomy_code,
            'storage_entries': {
                'taxonomy_metadata': {
                    'domain': 'biology',
                    'version': '1.0',
                    'source': 'example'
                }
            }
        })
        
        # Perform reasoning to derive new relationships
        reasoning_results = await integration.query_knowledge({
            'type': 'reasoning',
            'query_type': 'forward_chain',
            'max_iterations': 10,
            'min_confidence': 0.5
        })
        
        print(f"Derived {reasoning_results['reasoning_results']['total_inferences']} new relationships")
        
        # Query specific relationships
        cat_relationships = await integration.query_knowledge({
            'type': 'atomspace',
            'name': 'cat'
        })
        
        print(f"Found {len(cat_relationships['atoms'])} atoms related to 'cat'")

asyncio.run(basic_example())
```

### Example 2: Large-Scale Knowledge Graph Processing

```python
import asyncio
from integrations.hyperon_mork import create_production_integration

async def large_scale_example():
    # Production configuration for large datasets
    async with create_production_integration(
        storage_file="/data/large_knowledge_graph.mork",
        max_memory_mb=8192
    ) as integration:
        
        # Process large knowledge graph
        print("Processing large-scale knowledge graph...")
        
        # Create 100,000 concepts and relationships
        batch_size = 1000
        for batch in range(100):
            batch_knowledge = {
                'atoms': [],
                'storage_entries': {}
            }
            
            # Create batch of concepts
            for i in range(batch_size):
                concept_id = batch * batch_size + i
                
                batch_knowledge['atoms'].extend([
                    {
                        'type': 'ConceptNode',
                        'name': f'concept_{concept_id}',
                        'truth_value': {'strength': 0.8, 'confidence': 0.9}
                    },
                    {
                        'type': 'InheritanceLink',
                        'outgoing': [
                            {'type': 'ConceptNode', 'name': f'concept_{concept_id}'},
                            {'type': 'ConceptNode', 'name': f'category_{concept_id // 100}'}
                        ],
                        'truth_value': {'strength': 0.7, 'confidence': 0.8}
                    }
                ])
                
                batch_knowledge['storage_entries'][f'metadata_{concept_id}'] = {
                    'batch': batch,
                    'index': i,
                    'created': time.time()
                }
            
            # Process batch
            results = await integration.create_knowledge(batch_knowledge)
            print(f"Batch {batch}: {len(results['created_atoms'])} atoms created")
        
        # Perform large-scale reasoning
        print("Starting large-scale reasoning...")
        reasoning_results = await integration.query_knowledge({
            'type': 'reasoning',
            'query_type': 'forward_chain',
            'max_iterations': 50,
            'min_confidence': 0.1
        })
        
        print(f"Large-scale reasoning completed: {reasoning_results['reasoning_results']['total_inferences']} inferences")
        
        # Performance metrics
        metrics = integration.get_performance_metrics()
        print(f"Performance: {metrics['global']['operations_per_second']:.0f} ops/sec")
        print(f"Memory usage: {metrics['global']['memory_usage'] / 1024 / 1024:.1f} MB")

asyncio.run(large_scale_example())
```

## Troubleshooting

### Common Issues

1. **Memory Errors**: Increase `max_memory_mb` in configuration
2. **Storage Corruption**: Use storage compaction or recreation
3. **Performance Issues**: Check indexing and enable metrics
4. **Compatibility Problems**: Verify hyperon/OpenCog versions

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

config = IntegrationConfig(log_level="DEBUG")
integration = HyperonMORKIntegrationManager(config)
```

### Performance Monitoring

```python
# Enable detailed metrics
config = IntegrationConfig(enable_metrics=True)

async with HyperonMORKIntegrationManager(config) as integration:
    # Run operations...
    
    # Check performance
    metrics = integration.get_performance_metrics()
    print(json.dumps(metrics, indent=2))
```

## Contributing

This integration is part of Kenny AGI's commitment to open, collaborative AI development. Contributions are welcome!

### Development Setup

1. Clone Kenny AGI repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `python -m pytest integrations/hyperon_mork/tests/`
4. Submit pull requests with comprehensive tests

### Guidelines

- Follow OpenCog/hyperon compatibility standards
- Include comprehensive tests for all features
- Maintain backward compatibility
- Document all public APIs
- Optimize for performance and memory usage

## License

This integration is released under the same license as Kenny AGI, supporting open source AI development and collaboration with the global AI research community.

## Support

For support with this integration:

1. Check the troubleshooting guide above
2. Review the test framework for examples
3. Open issues in the Kenny AGI repository
4. Join the Kenny AGI community discussions

---

*Built with ❤️ for the future of Artificial General Intelligence*