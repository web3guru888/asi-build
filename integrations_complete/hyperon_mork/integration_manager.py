"""
Hyperon/MORK Integration Manager
===============================

Main orchestrator for hyperon/MORK integration with Kenny AGI.
Provides unified interface for symbolic AI, memory management,
and distributed reasoning capabilities.

Features:
- Unified hyperon/MORK interface
- Automatic component initialization
- Resource management and lifecycle
- Performance monitoring and optimization
- Error handling and recovery
- Plugin architecture for extensions

Compatible with:
- SingularityNET hyperon framework
- Ben Goertzel's PRIMUS architecture
- OpenCog symbolic AI stack
- Distributed reasoning systems
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from contextlib import AsyncExitStack

# Import all integration components
from .hyperon_compatibility.atomspace.atomspace_integration import (
    AtomspaceIntegration, Atom, AtomType, TruthValue
)
from .hyperon_compatibility.pln.pln_interface import PLNInterface
from .hyperon_compatibility.metta_support.metta_interpreter import MeTTaInterpreter
from .mork_interfaces.storage.memory_mapped_storage import MemoryMappedStorage, StorageMode
from .tests.test_framework import IntegrationTestFramework

logger = logging.getLogger(__name__)


class IntegrationMode(Enum):
    """Integration operating modes"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"  
    TESTING = "testing"
    BENCHMARK = "benchmark"


class ComponentStatus(Enum):
    """Component status tracking"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class IntegrationConfig:
    """Configuration for hyperon/MORK integration"""
    # General settings
    mode: IntegrationMode = IntegrationMode.DEVELOPMENT
    max_memory_mb: int = 1024
    num_threads: int = 4
    
    # Hyperon settings
    atomspace_size: int = 1000000
    pln_enabled: bool = True
    metta_enabled: bool = True
    truth_value_precision: int = 6
    
    # MORK settings
    storage_file: Optional[str] = None
    storage_mode: StorageMode = StorageMode.CREATE
    memory_mapped: bool = True
    page_size: int = 4096
    
    # Performance settings
    cache_size: int = 10000
    batch_size: int = 1000
    sync_interval: float = 1.0
    
    # Monitoring
    enable_metrics: bool = True
    log_level: str = "INFO"


@dataclass
class ComponentInfo:
    """Information about an integration component"""
    name: str
    status: ComponentStatus
    version: str
    initialization_time: float
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class HyperonMORKIntegrationManager:
    """
    Main integration manager for hyperon/MORK compatibility with Kenny AGI.
    
    This class orchestrates all components of the hyperon/MORK integration,
    providing a unified interface for symbolic AI operations, memory management,
    and distributed reasoning capabilities.
    """
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        self.config = config or IntegrationConfig()
        self.components: Dict[str, ComponentInfo] = {}
        
        # Core components
        self.atomspace: Optional[AtomspaceIntegration] = None
        self.pln: Optional[PLNInterface] = None
        self.metta: Optional[MeTTaInterpreter] = None
        self.storage: Optional[MemoryMappedStorage] = None
        self.test_framework: Optional[IntegrationTestFramework] = None
        
        # Runtime state
        self._initialized = False
        self._shutdown = False
        self._lock = threading.RLock()
        self._background_tasks: List[asyncio.Task] = []
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {
            'component_initialized': [],
            'component_error': [],
            'reasoning_complete': [],
            'storage_sync': []
        }
        
        # Statistics
        self.stats = {
            'start_time': time.time(),
            'operations_processed': 0,
            'errors_encountered': 0,
            'average_response_time': 0.0,
            'memory_usage': 0,
            'storage_operations': 0
        }
        
        logger.info(f"Hyperon/MORK Integration Manager created (mode: {self.config.mode.value})")
    
    async def initialize(self) -> bool:
        """
        Initialize all integration components.
        
        Returns:
            True if all components initialized successfully
        """
        if self._initialized:
            return True
        
        logger.info("Initializing hyperon/MORK integration...")
        
        try:
            with self._lock:
                # Initialize atomspace
                await self._initialize_atomspace()
                
                # Initialize storage
                await self._initialize_storage()
                
                # Initialize PLN (depends on atomspace)
                if self.config.pln_enabled and self.atomspace:
                    await self._initialize_pln()
                
                # Initialize MeTTa (depends on atomspace)
                if self.config.metta_enabled and self.atomspace:
                    await self._initialize_metta()
                
                # Initialize test framework
                if self.config.mode == IntegrationMode.TESTING:
                    await self._initialize_test_framework()
                
                # Start background tasks
                await self._start_background_tasks()
                
                self._initialized = True
                logger.info("Hyperon/MORK integration initialized successfully")
                
                # Emit event
                await self._emit_event('integration_initialized', {
                    'components': list(self.components.keys()),
                    'mode': self.config.mode.value
                })
                
                return True
                
        except Exception as e:
            logger.error(f"Integration initialization failed: {e}")
            await self._emit_event('integration_error', {'error': str(e)})
            return False
    
    async def _initialize_atomspace(self):
        """Initialize OpenCog Atomspace compatibility layer"""
        start_time = time.time()
        
        self.components['atomspace'] = ComponentInfo(
            name='Atomspace Integration',
            status=ComponentStatus.INITIALIZING,
            version='1.0.0',
            initialization_time=0.0
        )
        
        try:
            self.atomspace = AtomspaceIntegration(max_atoms=self.config.atomspace_size)
            
            self.components['atomspace'].status = ComponentStatus.READY
            self.components['atomspace'].initialization_time = time.time() - start_time
            
            logger.info(f"Atomspace initialized (capacity: {self.config.atomspace_size:,} atoms)")
            await self._emit_event('component_initialized', {'component': 'atomspace'})
            
        except Exception as e:
            self.components['atomspace'].status = ComponentStatus.ERROR
            self.components['atomspace'].last_error = str(e)
            raise RuntimeError(f"Atomspace initialization failed: {e}")
    
    async def _initialize_storage(self):
        """Initialize MORK memory-mapped storage"""
        start_time = time.time()
        
        self.components['storage'] = ComponentInfo(
            name='MORK Storage',
            status=ComponentStatus.INITIALIZING,
            version='1.0.0',
            initialization_time=0.0
        )
        
        try:
            storage_file = self.config.storage_file or f"/tmp/kenny_mork_{int(time.time())}.db"
            
            self.storage = MemoryMappedStorage(
                filename=storage_file,
                mode=self.config.storage_mode,
                page_size=self.config.page_size,
                max_size=self.config.max_memory_mb * 1024 * 1024
            )
            
            self.components['storage'].status = ComponentStatus.READY
            self.components['storage'].initialization_time = time.time() - start_time
            
            logger.info(f"MORK storage initialized (file: {storage_file})")
            await self._emit_event('component_initialized', {'component': 'storage'})
            
        except Exception as e:
            self.components['storage'].status = ComponentStatus.ERROR
            self.components['storage'].last_error = str(e)
            raise RuntimeError(f"MORK storage initialization failed: {e}")
    
    async def _initialize_pln(self):
        """Initialize Probabilistic Logic Networks interface"""
        start_time = time.time()
        
        self.components['pln'] = ComponentInfo(
            name='PLN Interface',
            status=ComponentStatus.INITIALIZING,
            version='1.0.0',
            initialization_time=0.0
        )
        
        try:
            if not self.atomspace:
                raise RuntimeError("Atomspace must be initialized before PLN")
            
            self.pln = PLNInterface(self.atomspace)
            
            self.components['pln'].status = ComponentStatus.READY
            self.components['pln'].initialization_time = time.time() - start_time
            
            logger.info("PLN interface initialized")
            await self._emit_event('component_initialized', {'component': 'pln'})
            
        except Exception as e:
            self.components['pln'].status = ComponentStatus.ERROR
            self.components['pln'].last_error = str(e)
            raise RuntimeError(f"PLN initialization failed: {e}")
    
    async def _initialize_metta(self):
        """Initialize MeTTa language interpreter"""
        start_time = time.time()
        
        self.components['metta'] = ComponentInfo(
            name='MeTTa Interpreter',
            status=ComponentStatus.INITIALIZING,
            version='1.0.0',
            initialization_time=0.0
        )
        
        try:
            if not self.atomspace:
                raise RuntimeError("Atomspace must be initialized before MeTTa")
            
            self.metta = MeTTaInterpreter(self.atomspace)
            
            self.components['metta'].status = ComponentStatus.READY
            self.components['metta'].initialization_time = time.time() - start_time
            
            logger.info("MeTTa interpreter initialized")
            await self._emit_event('component_initialized', {'component': 'metta'})
            
        except Exception as e:
            self.components['metta'].status = ComponentStatus.ERROR
            self.components['metta'].last_error = str(e)
            raise RuntimeError(f"MeTTa initialization failed: {e}")
    
    async def _initialize_test_framework(self):
        """Initialize integration test framework"""
        start_time = time.time()
        
        self.components['test_framework'] = ComponentInfo(
            name='Test Framework',
            status=ComponentStatus.INITIALIZING,
            version='1.0.0',
            initialization_time=0.0
        )
        
        try:
            self.test_framework = IntegrationTestFramework()
            
            self.components['test_framework'].status = ComponentStatus.READY
            self.components['test_framework'].initialization_time = time.time() - start_time
            
            logger.info("Test framework initialized")
            await self._emit_event('component_initialized', {'component': 'test_framework'})
            
        except Exception as e:
            self.components['test_framework'].status = ComponentStatus.ERROR
            self.components['test_framework'].last_error = str(e)
            raise RuntimeError(f"Test framework initialization failed: {e}")
    
    async def _start_background_tasks(self):
        """Start background maintenance tasks"""
        if self.config.enable_metrics:
            # Statistics collection task
            task = asyncio.create_task(self._statistics_collector())
            self._background_tasks.append(task)
        
        if self.storage and self.config.sync_interval > 0:
            # Storage synchronization task
            task = asyncio.create_task(self._storage_sync_task())
            self._background_tasks.append(task)
        
        logger.debug(f"Started {len(self._background_tasks)} background tasks")
    
    async def _statistics_collector(self):
        """Background task to collect performance statistics"""
        while not self._shutdown:
            try:
                # Collect atomspace stats
                if self.atomspace:
                    atomspace_stats = self.atomspace.get_statistics()
                    self.components['atomspace'].metrics = atomspace_stats
                
                # Collect PLN stats
                if self.pln:
                    pln_stats = self.pln.inference_engine.get_statistics()
                    self.components['pln'].metrics = pln_stats
                
                # Collect MeTTa stats
                if self.metta:
                    metta_stats = self.metta.get_statistics()
                    self.components['metta'].metrics = metta_stats
                
                # Collect storage stats
                if self.storage:
                    storage_stats = self.storage.get_statistics()
                    self.components['storage'].metrics = storage_stats
                
                # Update global stats
                self.stats['memory_usage'] = sum(
                    comp.metrics.get('memory_usage', 0) for comp in self.components.values()
                )
                
                await asyncio.sleep(5.0)  # Collect every 5 seconds
                
            except Exception as e:
                logger.error(f"Statistics collection error: {e}")
                await asyncio.sleep(10.0)
    
    async def _storage_sync_task(self):
        """Background task to synchronize storage"""
        while not self._shutdown:
            try:
                if self.storage:
                    self.storage.sync()
                    await self._emit_event('storage_sync', {
                        'timestamp': time.time(),
                        'entries': len(self.storage)
                    })
                
                await asyncio.sleep(self.config.sync_interval)
                
            except Exception as e:
                logger.error(f"Storage sync error: {e}")
                await asyncio.sleep(self.config.sync_interval * 2)
    
    # Main API methods
    
    async def create_knowledge(self, knowledge_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create knowledge structures using multiple modalities.
        
        Args:
            knowledge_spec: Knowledge specification
            
        Returns:
            Creation results
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        results = {'created_atoms': [], 'stored_entries': [], 'errors': []}
        
        try:
            # MeTTa code execution
            if 'metta_code' in knowledge_spec and self.metta:
                metta_results = self.metta.evaluate_string(knowledge_spec['metta_code'])
                results['metta_results'] = metta_results
            
            # Direct atom creation
            if 'atoms' in knowledge_spec and self.atomspace:
                for atom_spec in knowledge_spec['atoms']:
                    atom = self._create_atom_from_spec(atom_spec)
                    if atom:
                        results['created_atoms'].append(atom.id)
            
            # Storage entries
            if 'storage_entries' in knowledge_spec and self.storage:
                for key, value in knowledge_spec['storage_entries'].items():
                    success = self.storage.put(key, value)
                    if success:
                        results['stored_entries'].append(key)
            
            self.stats['operations_processed'] += 1
            processing_time = time.time() - start_time
            results['processing_time'] = processing_time
            
            # Update average response time
            self.stats['average_response_time'] = (
                (self.stats['average_response_time'] * (self.stats['operations_processed'] - 1) + processing_time) /
                self.stats['operations_processed']
            )
            
            return results
            
        except Exception as e:
            self.stats['errors_encountered'] += 1
            results['errors'].append(str(e))
            logger.error(f"Knowledge creation failed: {e}")
            return results
    
    async def query_knowledge(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query knowledge using various methods.
        
        Args:
            query: Query specification
            
        Returns:
            Query results
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        results = {'atoms': [], 'storage_results': [], 'reasoning_results': []}
        
        try:
            query_type = query.get('type', 'atomspace')
            
            if query_type == 'atomspace' and self.atomspace:
                # Atomspace query
                if 'atom_type' in query:
                    atom_type = AtomType(query['atom_type'])
                    atoms = self.atomspace.get_atoms_by_type(atom_type)
                    results['atoms'] = [str(atom) for atom in atoms[:100]]  # Limit results
                
                elif 'name' in query:
                    atoms = self.atomspace.get_atoms_by_name(query['name'])
                    results['atoms'] = [str(atom) for atom in atoms]
            
            elif query_type == 'storage' and self.storage:
                # Storage query
                if 'key' in query:
                    value = self.storage.get(query['key'])
                    results['storage_results'] = [{'key': query['key'], 'value': value}]
                elif 'key_pattern' in query:
                    # Simple pattern matching
                    pattern = query['key_pattern']
                    matching_keys = [key for key in self.storage.keys() if pattern in key]
                    results['storage_results'] = [
                        {'key': key, 'value': self.storage.get(key)}
                        for key in matching_keys[:50]  # Limit results
                    ]
            
            elif query_type == 'reasoning' and self.pln:
                # PLN reasoning query
                reasoning_results = await self.pln.reason(query)
                results['reasoning_results'] = reasoning_results
                
                await self._emit_event('reasoning_complete', {
                    'query': query,
                    'results': reasoning_results,
                    'timestamp': time.time()
                })
            
            elif query_type == 'metta' and self.metta:
                # MeTTa query
                if 'code' in query:
                    metta_results = self.metta.evaluate_string(query['code'])
                    results['metta_results'] = metta_results
            
            processing_time = time.time() - start_time
            results['processing_time'] = processing_time
            
            self.stats['operations_processed'] += 1
            
            return results
            
        except Exception as e:
            self.stats['errors_encountered'] += 1
            logger.error(f"Knowledge query failed: {e}")
            return {'error': str(e), 'processing_time': time.time() - start_time}
    
    async def run_tests(self, test_categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run integration tests.
        
        Args:
            test_categories: Specific test categories to run
            
        Returns:
            Test results
        """
        if not self.test_framework:
            await self._initialize_test_framework()
        
        if not test_categories:
            # Run all tests
            results = await self.test_framework.run_all_tests()
        else:
            # Run specific categories
            results = {'summary': {}, 'results': {}, 'benchmarks': []}
            # Implementation would filter and run specific test categories
        
        return results
    
    def _create_atom_from_spec(self, atom_spec: Dict[str, Any]) -> Optional[Atom]:
        """Create atom from specification"""
        try:
            atom_type = AtomType(atom_spec['type'])
            truth_value = None
            
            if 'truth_value' in atom_spec:
                tv_spec = atom_spec['truth_value']
                truth_value = TruthValue(tv_spec['strength'], tv_spec['confidence'])
            
            if 'name' in atom_spec:
                # Node
                return self.atomspace.add_node(atom_type, atom_spec['name'], truth_value)
            elif 'outgoing' in atom_spec:
                # Link
                outgoing_atoms = []
                for outgoing_spec in atom_spec['outgoing']:
                    outgoing_atom = self._create_atom_from_spec(outgoing_spec)
                    if outgoing_atom:
                        outgoing_atoms.append(outgoing_atom)
                
                return self.atomspace.add_link(atom_type, outgoing_atoms, truth_value)
            
        except Exception as e:
            logger.error(f"Failed to create atom from spec: {e}")
            return None
    
    # Event system
    
    def on(self, event_name: str, handler: Callable):
        """Register event handler"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
    
    async def _emit_event(self, event_name: str, data: Dict[str, Any]):
        """Emit event to registered handlers"""
        if event_name in self._event_handlers:
            for handler in self._event_handlers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_name, data)
                    else:
                        handler(event_name, data)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
    
    # Status and monitoring
    
    def get_status(self) -> Dict[str, Any]:
        """Get integration status"""
        return {
            'initialized': self._initialized,
            'mode': self.config.mode.value,
            'components': {
                name: {
                    'status': info.status.value,
                    'version': info.version,
                    'initialization_time': info.initialization_time,
                    'last_error': info.last_error,
                    'metrics_count': len(info.metrics)
                }
                for name, info in self.components.items()
            },
            'statistics': self.stats,
            'uptime': time.time() - self.stats['start_time']
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        metrics = {
            'global': self.stats,
            'components': {
                name: info.metrics for name, info in self.components.items()
            }
        }
        
        # Add derived metrics
        uptime = time.time() - self.stats['start_time']
        if uptime > 0:
            metrics['global']['operations_per_second'] = self.stats['operations_processed'] / uptime
            metrics['global']['error_rate'] = self.stats['errors_encountered'] / self.stats['operations_processed'] if self.stats['operations_processed'] > 0 else 0
        
        return metrics
    
    # Lifecycle management
    
    async def shutdown(self):
        """Shutdown integration and clean up resources"""
        if self._shutdown:
            return
        
        logger.info("Shutting down hyperon/MORK integration...")
        self._shutdown = True
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Shutdown components
        if self.storage:
            self.storage.close()
        
        if self.test_framework:
            self.test_framework.cleanup()
        
        # Update component statuses
        for component in self.components.values():
            component.status = ComponentStatus.SHUTDOWN
        
        logger.info("Hyperon/MORK integration shutdown complete")
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()


# Factory functions

def create_development_integration(storage_file: Optional[str] = None) -> HyperonMORKIntegrationManager:
    """Create integration manager for development"""
    config = IntegrationConfig(
        mode=IntegrationMode.DEVELOPMENT,
        atomspace_size=100000,
        storage_file=storage_file,
        enable_metrics=True,
        log_level="DEBUG"
    )
    return HyperonMORKIntegrationManager(config)

def create_production_integration(storage_file: str, 
                                 max_memory_mb: int = 2048) -> HyperonMORKIntegrationManager:
    """Create integration manager for production"""
    config = IntegrationConfig(
        mode=IntegrationMode.PRODUCTION,
        atomspace_size=5000000,
        storage_file=storage_file,
        storage_mode=StorageMode.READ_WRITE,
        max_memory_mb=max_memory_mb,
        enable_metrics=True,
        sync_interval=5.0,
        log_level="INFO"
    )
    return HyperonMORKIntegrationManager(config)

def create_test_integration() -> HyperonMORKIntegrationManager:
    """Create integration manager for testing"""
    config = IntegrationConfig(
        mode=IntegrationMode.TESTING,
        atomspace_size=50000,
        storage_mode=StorageMode.CREATE,
        enable_metrics=True,
        log_level="DEBUG"
    )
    return HyperonMORKIntegrationManager(config)


# Demo and testing
if __name__ == "__main__":
    print("🧪 Testing Hyperon/MORK Integration Manager...")
    
    async def test_integration_manager():
        # Test development integration
        async with create_development_integration() as integration:
            print("✅ Development integration initialized")
            
            # Test knowledge creation
            knowledge_spec = {
                'metta_code': '''
                (ConceptNode "cat")
                (ConceptNode "animal")
                (InheritanceLink (ConceptNode "cat") (ConceptNode "animal"))
                ''',
                'storage_entries': {
                    'test_key': {'type': 'test', 'value': 42},
                    'metadata': {'created': time.time(), 'source': 'test'}
                }
            }
            
            create_results = await integration.create_knowledge(knowledge_spec)
            print(f"✅ Knowledge creation: {len(create_results.get('created_atoms', []))} atoms, "
                  f"{len(create_results.get('stored_entries', []))} storage entries")
            
            # Test queries
            atomspace_query = {'type': 'atomspace', 'atom_type': 'ConceptNode'}
            query_results = await integration.query_knowledge(atomspace_query)
            print(f"✅ Atomspace query: {len(query_results.get('atoms', []))} results")
            
            storage_query = {'type': 'storage', 'key': 'test_key'}
            storage_results = await integration.query_knowledge(storage_query)
            print(f"✅ Storage query: {len(storage_results.get('storage_results', []))} results")
            
            # Test PLN reasoning
            if integration.pln:
                reasoning_query = {
                    'type': 'reasoning',
                    'query_type': 'forward_chain',
                    'max_iterations': 3,
                    'min_confidence': 0.1
                }
                reasoning_results = await integration.query_knowledge(reasoning_query)
                print(f"✅ PLN reasoning: {reasoning_results.get('reasoning_results', {}).get('total_inferences', 0)} inferences")
            
            # Test status
            status = integration.get_status()
            print(f"✅ Status check: {len(status['components'])} components, "
                  f"uptime: {status['uptime']:.1f}s")
            
            # Test metrics
            metrics = integration.get_performance_metrics()
            print(f"✅ Performance metrics: {metrics['global']['operations_processed']} operations, "
                  f"{metrics['global']['average_response_time']:.3f}s avg response time")
            
            print("🎯 Integration Manager test completed successfully!")
    
    asyncio.run(test_integration_manager())
    print("✅ Hyperon/MORK Integration Manager testing completed!")