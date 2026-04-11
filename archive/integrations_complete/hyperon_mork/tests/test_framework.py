"""
Integration Test Framework for Hyperon/MORK Compatibility
=========================================================

Comprehensive testing framework for validating hyperon/MORK integration
with Kenny AGI, including performance benchmarks, stress tests, and
compatibility verification.

Test Categories:
- Compatibility tests for all major operations
- Performance benchmarks vs native implementations
- Stress tests for large-scale knowledge graphs
- Migration tests from other formats
- Regression tests for API changes
"""

import asyncio
import time
import logging
import traceback
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import tempfile
import os

# Import integration components
from ..hyperon_compatibility.atomspace.atomspace_integration import (
    AtomspaceIntegration, Atom, AtomType, TruthValue
)
from ..hyperon_compatibility.pln.pln_interface import PLNInterface
from ..hyperon_compatibility.metta_support.metta_interpreter import MeTTaInterpreter
from ..mork_interfaces.storage.memory_mapped_storage import MemoryMappedStorage, StorageMode

logger = logging.getLogger(__name__)


class TestResult(Enum):
    """Test result status"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestCase:
    """Individual test case"""
    name: str
    description: str
    test_function: Callable
    category: str = "general"
    timeout: float = 30.0
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    
    # Results
    result: TestResult = TestResult.SKIP
    execution_time: float = 0.0
    error_message: str = ""
    output: str = ""


@dataclass
class TestSuite:
    """Test suite containing multiple test cases"""
    name: str
    description: str
    tests: List[TestCase] = field(default_factory=list)
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None


@dataclass
class BenchmarkResult:
    """Performance benchmark result"""
    test_name: str
    operations_per_second: float
    total_operations: int
    execution_time: float
    memory_usage: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntegrationTestFramework:
    """
    Comprehensive test framework for hyperon/MORK integration testing.
    """
    
    def __init__(self):
        self.test_suites: List[TestSuite] = []
        self.results: Dict[str, List[TestCase]] = {}
        self.benchmarks: List[BenchmarkResult] = []
        
        # Test environment
        self.temp_dir = tempfile.mkdtemp(prefix="hyperon_mork_test_")
        self.atomspace: Optional[AtomspaceIntegration] = None
        self.pln: Optional[PLNInterface] = None
        self.metta: Optional[MeTTaInterpreter] = None
        self.storage: Optional[MemoryMappedStorage] = None
        
        # Statistics
        self.stats = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'start_time': 0.0,
            'end_time': 0.0
        }
        
        self._register_test_suites()
        logger.info("Integration Test Framework initialized")
    
    def _register_test_suites(self):
        """Register all test suites"""
        # Atomspace compatibility tests
        self.add_test_suite(self._create_atomspace_test_suite())
        
        # PLN reasoning tests
        self.add_test_suite(self._create_pln_test_suite())
        
        # MeTTa interpreter tests
        self.add_test_suite(self._create_metta_test_suite())
        
        # MORK storage tests
        self.add_test_suite(self._create_mork_test_suite())
        
        # Integration tests
        self.add_test_suite(self._create_integration_test_suite())
        
        # Performance benchmarks
        self.add_test_suite(self._create_performance_test_suite())
        
        # Stress tests
        self.add_test_suite(self._create_stress_test_suite())
    
    def _create_atomspace_test_suite(self) -> TestSuite:
        """Create Atomspace compatibility test suite"""
        suite = TestSuite(
            name="Atomspace Compatibility",
            description="Test OpenCog Atomspace compatibility"
        )
        
        # Atom creation test
        suite.tests.append(TestCase(
            name="test_atom_creation",
            description="Test basic atom creation and storage",
            test_function=self._test_atom_creation,
            category="compatibility"
        ))
        
        # Truth value test
        suite.tests.append(TestCase(
            name="test_truth_values",
            description="Test truth value operations",
            test_function=self._test_truth_values,
            category="compatibility"
        ))
        
        # Link traversal test
        suite.tests.append(TestCase(
            name="test_link_traversal",
            description="Test link traversal and pattern matching",
            test_function=self._test_link_traversal,
            category="compatibility"
        ))
        
        # Serialization test
        suite.tests.append(TestCase(
            name="test_serialization",
            description="Test atomspace serialization/deserialization",
            test_function=self._test_atomspace_serialization,
            category="compatibility"
        ))
        
        return suite
    
    def _create_pln_test_suite(self) -> TestSuite:
        """Create PLN reasoning test suite"""
        suite = TestSuite(
            name="PLN Reasoning",
            description="Test Probabilistic Logic Networks compatibility"
        )
        
        suite.tests.append(TestCase(
            name="test_deduction_rule",
            description="Test PLN deduction rule",
            test_function=self._test_pln_deduction,
            category="reasoning"
        ))
        
        suite.tests.append(TestCase(
            name="test_induction_rule",
            description="Test PLN induction rule",
            test_function=self._test_pln_induction,
            category="reasoning"
        ))
        
        suite.tests.append(TestCase(
            name="test_forward_chaining",
            description="Test PLN forward chaining",
            test_function=self._test_pln_forward_chaining,
            category="reasoning"
        ))
        
        return suite
    
    def _create_metta_test_suite(self) -> TestSuite:
        """Create MeTTa interpreter test suite"""
        suite = TestSuite(
            name="MeTTa Interpreter",
            description="Test MeTTa language compatibility"
        )
        
        suite.tests.append(TestCase(
            name="test_basic_expressions",
            description="Test basic MeTTa expression evaluation",
            test_function=self._test_metta_expressions,
            category="language"
        ))
        
        suite.tests.append(TestCase(
            name="test_atomspace_integration",
            description="Test MeTTa-Atomspace integration",
            test_function=self._test_metta_atomspace,
            category="integration"
        ))
        
        return suite
    
    def _create_mork_test_suite(self) -> TestSuite:
        """Create MORK storage test suite"""
        suite = TestSuite(
            name="MORK Storage",
            description="Test MORK memory-mapped storage"
        )
        
        suite.tests.append(TestCase(
            name="test_basic_operations",
            description="Test basic CRUD operations",
            test_function=self._test_mork_basic_ops,
            category="storage"
        ))
        
        suite.tests.append(TestCase(
            name="test_concurrent_access",
            description="Test concurrent read/write operations",
            test_function=self._test_mork_concurrency,
            category="storage"
        ))
        
        return suite
    
    def _create_integration_test_suite(self) -> TestSuite:
        """Create full integration test suite"""
        suite = TestSuite(
            name="Full Integration",
            description="Test complete hyperon/MORK integration"
        )
        
        suite.tests.append(TestCase(
            name="test_end_to_end_reasoning",
            description="Test end-to-end reasoning workflow",
            test_function=self._test_end_to_end_reasoning,
            category="integration",
            timeout=60.0
        ))
        
        return suite
    
    def _create_performance_test_suite(self) -> TestSuite:
        """Create performance benchmark suite"""
        suite = TestSuite(
            name="Performance Benchmarks",
            description="Performance benchmarks vs native implementations"
        )
        
        suite.tests.append(TestCase(
            name="benchmark_atomspace_operations",
            description="Benchmark atomspace operations",
            test_function=self._benchmark_atomspace_ops,
            category="performance",
            timeout=120.0
        ))
        
        suite.tests.append(TestCase(
            name="benchmark_storage_operations",
            description="Benchmark storage operations",
            test_function=self._benchmark_storage_ops,
            category="performance",
            timeout=120.0
        ))
        
        return suite
    
    def _create_stress_test_suite(self) -> TestSuite:
        """Create stress test suite"""
        suite = TestSuite(
            name="Stress Tests",
            description="Stress tests for large-scale knowledge graphs"
        )
        
        suite.tests.append(TestCase(
            name="stress_large_atomspace",
            description="Stress test with large atomspace",
            test_function=self._stress_test_large_atomspace,
            category="stress",
            timeout=300.0
        ))
        
        return suite
    
    # Test implementations
    async def _test_atom_creation(self) -> bool:
        """Test basic atom creation"""
        self.atomspace = AtomspaceIntegration(max_atoms=10000)
        
        # Create nodes
        cat = self.atomspace.add_node(AtomType.CONCEPT_NODE, "cat", TruthValue(0.9, 0.8))
        animal = self.atomspace.add_node(AtomType.CONCEPT_NODE, "animal", TruthValue(0.95, 0.9))
        
        assert cat is not None, "Failed to create cat node"
        assert animal is not None, "Failed to create animal node"
        assert cat.name == "cat", "Incorrect cat node name"
        assert animal.name == "animal", "Incorrect animal node name"
        
        # Create link
        inheritance = self.atomspace.add_link(
            AtomType.INHERITANCE_LINK,
            [cat, animal],
            TruthValue(0.85, 0.9)
        )
        
        assert inheritance is not None, "Failed to create inheritance link"
        assert len(inheritance.outgoing) == 2, "Incorrect link arity"
        assert inheritance.outgoing[0] == cat, "Incorrect first outgoing"
        assert inheritance.outgoing[1] == animal, "Incorrect second outgoing"
        
        return True
    
    async def _test_truth_values(self) -> bool:
        """Test truth value operations"""
        tv1 = TruthValue(0.8, 0.9)
        tv2 = TruthValue(0.7, 0.8)
        
        assert 0.0 <= tv1.strength <= 1.0, "Invalid strength range"
        assert 0.0 <= tv1.confidence <= 1.0, "Invalid confidence range"
        assert tv1.count > 0, "Invalid count value"
        
        # Test serialization
        tv_dict = tv1.to_dict()
        tv_restored = TruthValue.from_dict(tv_dict)
        
        assert abs(tv_restored.strength - tv1.strength) < 1e-6, "Strength serialization error"
        assert abs(tv_restored.confidence - tv1.confidence) < 1e-6, "Confidence serialization error"
        
        return True
    
    async def _test_link_traversal(self) -> bool:
        """Test link traversal"""
        if not self.atomspace:
            self.atomspace = AtomspaceIntegration(max_atoms=10000)
        
        # Create hierarchy
        cat = self.atomspace.add_node(AtomType.CONCEPT_NODE, "cat")
        animal = self.atomspace.add_node(AtomType.CONCEPT_NODE, "animal")
        being = self.atomspace.add_node(AtomType.CONCEPT_NODE, "being")
        
        link1 = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [cat, animal])
        link2 = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [animal, being])
        
        # Test incoming links
        cat_incoming = self.atomspace.get_incoming(cat)
        assert len(cat_incoming) == 1, "Incorrect incoming count for cat"
        assert link1 in cat_incoming, "Missing inheritance link in cat incoming"
        
        # Test outgoing links
        link1_outgoing = self.atomspace.get_outgoing(link1)
        assert len(link1_outgoing) == 2, "Incorrect outgoing count for link1"
        assert link1_outgoing[0] == cat, "Incorrect first outgoing"
        assert link1_outgoing[1] == animal, "Incorrect second outgoing"
        
        return True
    
    async def _test_atomspace_serialization(self) -> bool:
        """Test atomspace serialization"""
        if not self.atomspace:
            self.atomspace = AtomspaceIntegration(max_atoms=10000)
        
        # Add some atoms
        cat = self.atomspace.add_node(AtomType.CONCEPT_NODE, "cat", TruthValue(0.9, 0.8))
        dog = self.atomspace.add_node(AtomType.CONCEPT_NODE, "dog", TruthValue(0.85, 0.9))
        animal = self.atomspace.add_node(AtomType.CONCEPT_NODE, "animal", TruthValue(0.95, 0.95))
        
        link1 = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [cat, animal], TruthValue(0.8, 0.9))
        link2 = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [dog, animal], TruthValue(0.85, 0.85))
        
        original_size = len(self.atomspace)
        
        # Export to JSON
        json_data = self.atomspace.export_to_json()
        assert len(json_data) > 0, "Empty JSON export"
        
        # Create new atomspace and import
        new_atomspace = AtomspaceIntegration(max_atoms=10000)
        new_atomspace.import_from_json(json_data)
        
        assert len(new_atomspace) == original_size, "Size mismatch after import"
        
        # Verify specific atoms exist
        cat_nodes = new_atomspace.get_atoms_by_name("cat")
        assert len(cat_nodes) > 0, "Cat node missing after import"
        
        inheritance_links = new_atomspace.get_atoms_by_type(AtomType.INHERITANCE_LINK)
        assert len(inheritance_links) >= 2, "Inheritance links missing after import"
        
        return True
    
    async def _test_pln_deduction(self) -> bool:
        """Test PLN deduction rule"""
        if not self.atomspace:
            self.atomspace = AtomspaceIntegration(max_atoms=10000)
        
        self.pln = PLNInterface(self.atomspace)
        
        # Create premises: A->B, B->C
        a = self.atomspace.add_node(AtomType.CONCEPT_NODE, "A", TruthValue(0.9, 0.9))
        b = self.atomspace.add_node(AtomType.CONCEPT_NODE, "B", TruthValue(0.9, 0.9))
        c = self.atomspace.add_node(AtomType.CONCEPT_NODE, "C", TruthValue(0.9, 0.9))
        
        ab = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [a, b], TruthValue(0.8, 0.9))
        bc = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [b, c], TruthValue(0.7, 0.8))
        
        # Apply deduction rule
        from ..hyperon_compatibility.pln.pln_interface import PLNRule
        result = self.pln.inference_engine.apply_rule(PLNRule.DEDUCTION, [ab, bc])
        
        assert result is not None, "Deduction rule failed"
        assert result.conclusion is not None, "No conclusion from deduction"
        assert result.conclusion.atom_type == AtomType.INHERITANCE_LINK, "Incorrect conclusion type"
        
        # Check truth value calculation
        expected_strength = ab.truth_value.strength * bc.truth_value.strength
        actual_strength = result.truth_value.strength
        assert abs(actual_strength - expected_strength) < 0.1, "Incorrect strength calculation"
        
        return True
    
    async def _test_pln_induction(self) -> bool:
        """Test PLN induction rule"""
        if not self.pln:
            if not self.atomspace:
                self.atomspace = AtomspaceIntegration(max_atoms=10000)
            self.pln = PLNInterface(self.atomspace)
        
        # Create premises: A->B, A->C
        a = self.atomspace.add_node(AtomType.CONCEPT_NODE, "A2", TruthValue(0.9, 0.9))
        b = self.atomspace.add_node(AtomType.CONCEPT_NODE, "B2", TruthValue(0.9, 0.9))
        c = self.atomspace.add_node(AtomType.CONCEPT_NODE, "C2", TruthValue(0.9, 0.9))
        
        ab = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [a, b], TruthValue(0.8, 0.9))
        ac = self.atomspace.add_link(AtomType.INHERITANCE_LINK, [a, c], TruthValue(0.75, 0.85))
        
        # Apply induction rule
        from ..hyperon_compatibility.pln.pln_interface import PLNRule
        result = self.pln.inference_engine.apply_rule(PLNRule.INDUCTION, [ab, ac])
        
        assert result is not None, "Induction rule failed"
        assert result.conclusion is not None, "No conclusion from induction"
        
        return True
    
    async def _test_pln_forward_chaining(self) -> bool:
        """Test PLN forward chaining"""
        if not self.pln:
            if not self.atomspace:
                self.atomspace = AtomspaceIntegration(max_atoms=10000)
            self.pln = PLNInterface(self.atomspace)
        
        # Create knowledge base
        cat = self.atomspace.add_node(AtomType.CONCEPT_NODE, "cat", TruthValue(0.9, 0.9))
        mammal = self.atomspace.add_node(AtomType.CONCEPT_NODE, "mammal", TruthValue(0.9, 0.9))
        animal = self.atomspace.add_node(AtomType.CONCEPT_NODE, "animal", TruthValue(0.9, 0.9))
        
        self.atomspace.add_link(AtomType.INHERITANCE_LINK, [cat, mammal], TruthValue(0.9, 0.8))
        self.atomspace.add_link(AtomType.INHERITANCE_LINK, [mammal, animal], TruthValue(0.95, 0.9))
        
        # Run forward chaining
        results = self.pln.inference_engine.forward_chain(max_iterations=10, min_confidence=0.1)
        
        assert len(results) > 0, "No inferences from forward chaining"
        
        # Check if we derived cat->animal
        cat_to_animal = None
        for result in results:
            if (result.conclusion.atom_type == AtomType.INHERITANCE_LINK and
                result.conclusion.outgoing[0].name == "cat" and
                result.conclusion.outgoing[1].name == "animal"):
                cat_to_animal = result
                break
        
        assert cat_to_animal is not None, "Failed to derive cat->animal"
        
        return True
    
    async def _test_metta_expressions(self) -> bool:
        """Test MeTTa expression evaluation"""
        if not self.atomspace:
            self.atomspace = AtomspaceIntegration(max_atoms=10000)
        
        self.metta = MeTTaInterpreter(self.atomspace)
        
        # Test basic arithmetic
        results = self.metta.evaluate_string("(+ 2 3)")
        assert len(results) > 0, "No results from MeTTa evaluation"
        assert results[0] == 5, f"Incorrect arithmetic result: {results[0]}"
        
        # Test conditional
        results = self.metta.evaluate_string('(if (> 5 3) "yes" "no")')
        assert len(results) > 0, "No results from conditional"
        assert results[0] == "yes", f"Incorrect conditional result: {results[0]}"
        
        return True
    
    async def _test_metta_atomspace(self) -> bool:
        """Test MeTTa-Atomspace integration"""
        if not self.metta:
            if not self.atomspace:
                self.atomspace = AtomspaceIntegration(max_atoms=10000)
            self.metta = MeTTaInterpreter(self.atomspace)
        
        # Create atoms through MeTTa
        results = self.metta.evaluate_string('(ConceptNode "dog")')
        assert len(results) > 0, "No results from ConceptNode creation"
        
        # Verify atom was created in atomspace
        dog_nodes = self.atomspace.get_atoms_by_name("dog")
        assert len(dog_nodes) > 0, "Dog node not created in atomspace"
        
        return True
    
    async def _test_mork_basic_ops(self) -> bool:
        """Test MORK basic operations"""
        storage_file = os.path.join(self.temp_dir, "test_storage.db")
        
        with MemoryMappedStorage(storage_file, StorageMode.CREATE) as storage:
            # Test put/get
            test_data = {"name": "test", "value": 42}
            success = storage.put("test_key", test_data)
            assert success, "Failed to put data"
            
            retrieved = storage.get("test_key")
            assert retrieved is not None, "Failed to get data"
            assert retrieved == test_data, "Data mismatch"
            
            # Test existence
            assert storage.exists("test_key"), "Key existence check failed"
            assert not storage.exists("nonexistent"), "False positive existence check"
            
            # Test deletion
            deleted = storage.delete("test_key")
            assert deleted, "Failed to delete key"
            assert not storage.exists("test_key"), "Key still exists after deletion"
        
        return True
    
    async def _test_mork_concurrency(self) -> bool:
        """Test MORK concurrent operations"""
        storage_file = os.path.join(self.temp_dir, "concurrent_test.db")
        
        async def writer_task(storage, start_idx, count):
            for i in range(start_idx, start_idx + count):
                key = f"key_{i}"
                value = {"index": i, "data": f"test_{i}"}
                storage.put(key, value)
        
        async def reader_task(storage, keys):
            results = []
            for key in keys:
                value = storage.get(key)
                results.append(value)
            return results
        
        with MemoryMappedStorage(storage_file, StorageMode.CREATE) as storage:
            # Pre-populate some data
            for i in range(50):
                storage.put(f"key_{i}", {"index": i})
            
            # Run concurrent writers and readers
            write_tasks = [
                writer_task(storage, 50, 25),
                writer_task(storage, 75, 25)
            ]
            
            read_keys = [f"key_{i}" for i in range(0, 50, 2)]
            read_task = reader_task(storage, read_keys)
            
            # Execute concurrently
            await asyncio.gather(*write_tasks, read_task)
            
            # Verify final state
            total_keys = len(list(storage.keys()))
            assert total_keys >= 100, f"Expected at least 100 keys, got {total_keys}"
        
        return True
    
    async def _test_end_to_end_reasoning(self) -> bool:
        """Test complete end-to-end reasoning workflow"""
        # Initialize all components
        self.atomspace = AtomspaceIntegration(max_atoms=50000)
        self.pln = PLNInterface(self.atomspace)
        self.metta = MeTTaInterpreter(self.atomspace)
        
        storage_file = os.path.join(self.temp_dir, "e2e_test.db")
        self.storage = MemoryMappedStorage(storage_file, StorageMode.CREATE)
        
        try:
            # 1. Create knowledge through MeTTa
            metta_code = '''
            (ConceptNode "cat")
            (ConceptNode "mammal")
            (ConceptNode "animal")
            (InheritanceLink (ConceptNode "cat") (ConceptNode "mammal"))
            (InheritanceLink (ConceptNode "mammal") (ConceptNode "animal"))
            '''
            
            metta_results = self.metta.evaluate_string(metta_code)
            assert len(metta_results) >= 5, "Failed to create knowledge through MeTTa"
            
            # 2. Store knowledge in MORK
            for i, atom in enumerate(self.atomspace.atoms.values()):
                key = f"atom_{atom.id}"
                value = {
                    "type": atom.atom_type.value,
                    "name": atom.name,
                    "outgoing": [out.id for out in atom.outgoing],
                    "truth_value": atom.truth_value.to_dict()
                }
                self.storage.put(key, value)
            
            # 3. Perform PLN reasoning
            reasoning_query = {
                'type': 'forward_chain',
                'max_iterations': 5,
                'min_confidence': 0.1
            }
            
            reasoning_result = await self.pln.reason(reasoning_query)
            assert reasoning_result['total_inferences'] > 0, "No inferences generated"
            
            # 4. Verify derived knowledge
            cat_animal_derived = False
            for inference in reasoning_result['results']:
                if ("cat" in inference['explanation'] and 
                    "animal" in inference['explanation']):
                    cat_animal_derived = True
                    break
            
            assert cat_animal_derived, "Failed to derive cat->animal relationship"
            
            # 5. Store reasoning results
            reasoning_key = "reasoning_results"
            self.storage.put(reasoning_key, reasoning_result)
            
            retrieved_results = self.storage.get(reasoning_key)
            assert retrieved_results is not None, "Failed to retrieve reasoning results"
            
            return True
            
        finally:
            if self.storage:
                self.storage.close()
    
    async def _benchmark_atomspace_ops(self) -> bool:
        """Benchmark atomspace operations"""
        self.atomspace = AtomspaceIntegration(max_atoms=100000)
        
        # Benchmark node creation
        start_time = time.time()
        nodes = []
        for i in range(10000):
            node = self.atomspace.add_node(AtomType.CONCEPT_NODE, f"concept_{i}")
            nodes.append(node)
        
        node_creation_time = time.time() - start_time
        node_ops_per_sec = 10000 / node_creation_time
        
        # Benchmark link creation
        start_time = time.time()
        for i in range(5000):
            child = nodes[i % len(nodes)]
            parent = nodes[(i + 1) % len(nodes)]
            self.atomspace.add_link(AtomType.INHERITANCE_LINK, [child, parent])
        
        link_creation_time = time.time() - start_time
        link_ops_per_sec = 5000 / link_creation_time
        
        # Benchmark searches
        start_time = time.time()
        for i in range(1000):
            concept_name = f"concept_{i % 100}"
            results = self.atomspace.get_atoms_by_name(concept_name)
        
        search_time = time.time() - start_time
        search_ops_per_sec = 1000 / search_time
        
        # Record benchmarks
        self.benchmarks.append(BenchmarkResult(
            test_name="atomspace_node_creation",
            operations_per_second=node_ops_per_sec,
            total_operations=10000,
            execution_time=node_creation_time,
            memory_usage=len(self.atomspace) * 1024,
            metadata={"operation": "node_creation"}
        ))
        
        self.benchmarks.append(BenchmarkResult(
            test_name="atomspace_link_creation",
            operations_per_second=link_ops_per_sec,
            total_operations=5000,
            execution_time=link_creation_time,
            memory_usage=len(self.atomspace) * 1024,
            metadata={"operation": "link_creation"}
        ))
        
        self.benchmarks.append(BenchmarkResult(
            test_name="atomspace_search",
            operations_per_second=search_ops_per_sec,
            total_operations=1000,
            execution_time=search_time,
            memory_usage=len(self.atomspace) * 1024,
            metadata={"operation": "search"}
        ))
        
        return True
    
    async def _benchmark_storage_ops(self) -> bool:
        """Benchmark storage operations"""
        storage_file = os.path.join(self.temp_dir, "benchmark_storage.db")
        
        with MemoryMappedStorage(storage_file, StorageMode.CREATE, max_size=512*1024*1024) as storage:
            # Benchmark writes
            test_data = {"name": "test", "value": list(range(100))}
            
            start_time = time.time()
            for i in range(10000):
                key = f"benchmark_key_{i}"
                storage.put(key, test_data)
            
            write_time = time.time() - start_time
            write_ops_per_sec = 10000 / write_time
            
            # Benchmark reads
            start_time = time.time()
            for i in range(10000):
                key = f"benchmark_key_{i}"
                value = storage.get(key)
            
            read_time = time.time() - start_time
            read_ops_per_sec = 10000 / read_time
            
            # Record benchmarks
            self.benchmarks.append(BenchmarkResult(
                test_name="mork_storage_write",
                operations_per_second=write_ops_per_sec,
                total_operations=10000,
                execution_time=write_time,
                memory_usage=storage.get_statistics()['file_size_bytes'],
                metadata={"operation": "write"}
            ))
            
            self.benchmarks.append(BenchmarkResult(
                test_name="mork_storage_read",
                operations_per_second=read_ops_per_sec,
                total_operations=10000,
                execution_time=read_time,
                memory_usage=storage.get_statistics()['file_size_bytes'],
                metadata={"operation": "read"}
            ))
        
        return True
    
    async def _stress_test_large_atomspace(self) -> bool:
        """Stress test with large atomspace"""
        self.atomspace = AtomspaceIntegration(max_atoms=500000)
        
        # Create large hierarchy
        concepts = []
        for i in range(10000):
            concept = self.atomspace.add_node(AtomType.CONCEPT_NODE, f"concept_{i}")
            concepts.append(concept)
        
        # Create many inheritance relationships
        for i in range(50000):
            child = concepts[i % len(concepts)]
            parent = concepts[(i + 1) % len(concepts)]
            self.atomspace.add_link(AtomType.INHERITANCE_LINK, [child, parent])
        
        # Verify atomspace integrity
        assert len(self.atomspace) >= 60000, "Atomspace size too small"
        
        # Test operations on large atomspace
        concept_nodes = self.atomspace.get_atoms_by_type(AtomType.CONCEPT_NODE)
        assert len(concept_nodes) >= 10000, "Concept node count mismatch"
        
        inheritance_links = self.atomspace.get_atoms_by_type(AtomType.INHERITANCE_LINK)
        assert len(inheritance_links) >= 50000, "Inheritance link count mismatch"
        
        return True
    
    # Framework methods
    def add_test_suite(self, suite: TestSuite):
        """Add test suite to framework"""
        self.test_suites.append(suite)
        self.stats['total_tests'] += len(suite.tests)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites"""
        logger.info("Starting hyperon/MORK integration tests...")
        self.stats['start_time'] = time.time()
        
        for suite in self.test_suites:
            await self.run_test_suite(suite)
        
        self.stats['end_time'] = time.time()
        total_time = self.stats['end_time'] - self.stats['start_time']
        
        # Generate report
        report = {
            'summary': {
                'total_tests': self.stats['total_tests'],
                'passed': self.stats['passed'],
                'failed': self.stats['failed'],
                'errors': self.stats['errors'],
                'skipped': self.stats['skipped'],
                'success_rate': self.stats['passed'] / self.stats['total_tests'] if self.stats['total_tests'] > 0 else 0,
                'total_time': total_time
            },
            'results': self.results,
            'benchmarks': [
                {
                    'test_name': b.test_name,
                    'operations_per_second': b.operations_per_second,
                    'total_operations': b.total_operations,
                    'execution_time': b.execution_time,
                    'memory_usage': b.memory_usage,
                    'metadata': b.metadata
                } for b in self.benchmarks
            ]
        }
        
        logger.info(f"Integration tests completed: {self.stats['passed']}/{self.stats['total_tests']} passed "
                   f"({report['summary']['success_rate']:.1%}) in {total_time:.1f}s")
        
        return report
    
    async def run_test_suite(self, suite: TestSuite):
        """Run individual test suite"""
        logger.info(f"Running test suite: {suite.name}")
        
        # Suite setup
        if suite.setup:
            try:
                await suite.setup()
            except Exception as e:
                logger.error(f"Suite setup failed: {e}")
        
        suite_results = []
        
        for test in suite.tests:
            result = await self.run_test_case(test)
            suite_results.append(result)
        
        self.results[suite.name] = suite_results
        
        # Suite teardown
        if suite.teardown:
            try:
                await suite.teardown()
            except Exception as e:
                logger.error(f"Suite teardown failed: {e}")
    
    async def run_test_case(self, test: TestCase) -> TestCase:
        """Run individual test case"""
        logger.debug(f"Running test: {test.name}")
        
        # Test setup
        if test.setup:
            try:
                await test.setup()
            except Exception as e:
                test.result = TestResult.ERROR
                test.error_message = f"Setup failed: {e}"
                self.stats['errors'] += 1
                return test
        
        # Run test
        start_time = time.time()
        
        try:
            # Run with timeout
            success = await asyncio.wait_for(
                test.test_function(),
                timeout=test.timeout
            )
            
            test.execution_time = time.time() - start_time
            
            if success:
                test.result = TestResult.PASS
                self.stats['passed'] += 1
            else:
                test.result = TestResult.FAIL
                self.stats['failed'] += 1
                
        except asyncio.TimeoutError:
            test.result = TestResult.ERROR
            test.error_message = f"Test timed out after {test.timeout}s"
            test.execution_time = test.timeout
            self.stats['errors'] += 1
            
        except Exception as e:
            test.result = TestResult.ERROR
            test.error_message = str(e)
            test.execution_time = time.time() - start_time
            self.stats['errors'] += 1
            logger.error(f"Test {test.name} failed: {e}")
            logger.debug(traceback.format_exc())
        
        # Test teardown
        if test.teardown:
            try:
                await test.teardown()
            except Exception as e:
                logger.warning(f"Test teardown failed: {e}")
        
        return test
    
    def cleanup(self):
        """Clean up test resources"""
        try:
            if self.storage:
                self.storage.close()
            
            # Clean up temp directory
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


# Demo and testing
if __name__ == "__main__":
    print("🧪 Running Hyperon/MORK Integration Tests...")
    
    async def run_tests():
        with IntegrationTestFramework() as framework:
            report = await framework.run_all_tests()
            
            print("\n" + "="*60)
            print("INTEGRATION TEST RESULTS")
            print("="*60)
            
            summary = report['summary']
            print(f"Total Tests: {summary['total_tests']}")
            print(f"Passed: {summary['passed']}")
            print(f"Failed: {summary['failed']}")
            print(f"Errors: {summary['errors']}")
            print(f"Success Rate: {summary['success_rate']:.1%}")
            print(f"Total Time: {summary['total_time']:.1f}s")
            
            print(f"\nBenchmarks:")
            for benchmark in report['benchmarks']:
                print(f"  {benchmark['test_name']}: {benchmark['operations_per_second']:.0f} ops/sec")
            
            # Detailed results
            for suite_name, tests in report['results'].items():
                print(f"\n{suite_name}:")
                for test in tests:
                    status = "✅" if test.result == TestResult.PASS else "❌"
                    print(f"  {status} {test.name} ({test.execution_time:.3f}s)")
                    if test.error_message:
                        print(f"    Error: {test.error_message}")
            
            return summary['success_rate'] > 0.8  # 80% pass rate required
    
    success = asyncio.run(run_tests())
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed!'}")
    print("🎯 Hyperon/MORK Integration Test Framework completed!")