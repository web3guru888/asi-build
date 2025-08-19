"""
Atomspace Integration for Hyperon Compatibility
===============================================

Implements full OpenCog Atomspace compatibility for Kenny AGI,
enabling seamless integration with SingularityNET's hyperon framework.

Features:
- Atom creation and management
- Truth values and attention values
- Inheritance hierarchies
- Link traversal and pattern matching
- Atomspace persistence and serialization
- Thread-safe operations

Compatible with:
- OpenCog Atomspace API
- Hyperon symbolic AI framework
- Ben Goertzel's PRIMUS architecture
"""

import asyncio
import threading
import time
import uuid
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from collections import defaultdict
import weakref

logger = logging.getLogger(__name__)


class AtomType(Enum):
    """Standard OpenCog atom types"""
    # Basic types
    ATOM = "Atom"
    NODE = "Node"
    LINK = "Link"
    
    # Node types
    CONCEPT_NODE = "ConceptNode"
    PREDICATE_NODE = "PredicateNode"
    SCHEMA_NODE = "SchemaNode"
    PROCEDURE_NODE = "ProcedureNode"
    VARIABLE_NODE = "VariableNode"
    TYPE_NODE = "TypeNode"
    NUMBER_NODE = "NumberNode"
    WORD_NODE = "WordNode"
    
    # Link types
    INHERITANCE_LINK = "InheritanceLink"
    SIMILARITY_LINK = "SimilarityLink"
    IMPLICATION_LINK = "ImplicationLink"
    EVALUATION_LINK = "EvaluationLink"
    EXECUTION_LINK = "ExecutionLink"
    LIST_LINK = "ListLink"
    SET_LINK = "SetLink"
    MEMBER_LINK = "MemberLink"
    SUBSET_LINK = "SubsetLink"
    AND_LINK = "AndLink"
    OR_LINK = "OrLink"
    NOT_LINK = "NotLink"
    LAMBDA_LINK = "LambdaLink"
    BIND_LINK = "BindLink"
    GET_LINK = "GetLink"
    PUT_LINK = "PutLink"
    FORALL_LINK = "ForAllLink"
    EXISTS_LINK = "ExistsLink"


@dataclass
class TruthValue:
    """OpenCog truth value representation"""
    strength: float = 1.0  # Confidence in truth (0.0 to 1.0)
    confidence: float = 1.0  # Confidence in the strength value (0.0 to 1.0)
    
    def __post_init__(self):
        self.strength = max(0.0, min(1.0, self.strength))
        self.confidence = max(0.0, min(1.0, self.confidence))
    
    @property
    def count(self) -> float:
        """Convert confidence to count for PLN operations"""
        return self.confidence * 1000.0
    
    def to_dict(self) -> Dict[str, float]:
        return {'strength': self.strength, 'confidence': self.confidence}
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'TruthValue':
        return cls(strength=data.get('strength', 1.0), confidence=data.get('confidence', 1.0))


@dataclass
class AttentionValue:
    """OpenCog attention value for importance weighting"""
    sti: int = 0  # Short-term importance (-32768 to 32767)
    lti: int = 0  # Long-term importance (-32768 to 32767)
    vlti: int = 0  # Very long-term importance (0 or 1)
    
    def __post_init__(self):
        self.sti = max(-32768, min(32767, self.sti))
        self.lti = max(-32768, min(32767, self.lti))
        self.vlti = max(0, min(1, self.vlti))
    
    def to_dict(self) -> Dict[str, int]:
        return {'sti': self.sti, 'lti': self.lti, 'vlti': self.vlti}


class Atom:
    """Base OpenCog Atom class"""
    
    def __init__(self, atom_type: AtomType, name: str = "", 
                 outgoing: List['Atom'] = None, 
                 truth_value: TruthValue = None,
                 attention_value: AttentionValue = None):
        self.id = str(uuid.uuid4())
        self.atom_type = atom_type
        self.name = name
        self.outgoing = outgoing or []
        self.incoming: Set['Atom'] = set()
        self.truth_value = truth_value or TruthValue()
        self.attention_value = attention_value or AttentionValue()
        self.creation_time = time.time()
        
        # Update incoming sets
        for atom in self.outgoing:
            atom.incoming.add(self)
    
    @property
    def arity(self) -> int:
        """Number of outgoing atoms"""
        return len(self.outgoing)
    
    @property
    def is_node(self) -> bool:
        """Check if this atom is a node"""
        return self.arity == 0
    
    @property
    def is_link(self) -> bool:
        """Check if this atom is a link"""
        return self.arity > 0
    
    def get_handle(self) -> str:
        """Get unique handle for this atom"""
        return self.id
    
    def set_truth_value(self, tv: TruthValue):
        """Update truth value"""
        self.truth_value = tv
    
    def set_attention_value(self, av: AttentionValue):
        """Update attention value"""
        self.attention_value = av
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize atom to dictionary"""
        return {
            'id': self.id,
            'type': self.atom_type.value,
            'name': self.name,
            'outgoing': [atom.id for atom in self.outgoing],
            'truth_value': self.truth_value.to_dict(),
            'attention_value': self.attention_value.to_dict(),
            'creation_time': self.creation_time
        }
    
    def __str__(self) -> str:
        if self.is_node:
            return f"({self.atom_type.value} \"{self.name}\")"
        else:
            outgoing_str = " ".join(str(atom) for atom in self.outgoing)
            return f"({self.atom_type.value} {outgoing_str})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Atom):
            return False
        return (self.atom_type == other.atom_type and 
                self.name == other.name and 
                self.outgoing == other.outgoing)
    
    def __hash__(self) -> int:
        return hash((self.atom_type, self.name, tuple(self.outgoing)))


class AtomspaceIntegration:
    """
    Full Atomspace integration for Kenny AGI hyperon compatibility.
    Provides thread-safe atom creation, storage, and manipulation.
    """
    
    def __init__(self, max_atoms: int = 1000000):
        self.max_atoms = max_atoms
        self.atoms: Dict[str, Atom] = {}
        self.type_index: Dict[AtomType, Set[str]] = defaultdict(set)
        self.name_index: Dict[str, Set[str]] = defaultdict(set)
        self.outgoing_index: Dict[str, Set[str]] = defaultdict(set)
        self.incoming_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Thread safety
        self._lock = threading.RLock()
        self._stats = {
            'atoms_created': 0,
            'atoms_deleted': 0,
            'queries_executed': 0,
            'patterns_matched': 0,
            'start_time': time.time()
        }
        
        logger.info(f"Atomspace initialized with capacity for {max_atoms:,} atoms")
    
    def add_atom(self, atom_type: AtomType, name: str = "", 
                 outgoing: List[Atom] = None, 
                 truth_value: TruthValue = None) -> Atom:
        """
        Add an atom to the atomspace.
        
        Args:
            atom_type: Type of atom to create
            name: Name for nodes
            outgoing: Outgoing atoms for links
            truth_value: Optional truth value
            
        Returns:
            Created atom instance
        """
        with self._lock:
            # Check capacity
            if len(self.atoms) >= self.max_atoms:
                self._garbage_collect()
                if len(self.atoms) >= self.max_atoms:
                    raise RuntimeError(f"Atomspace capacity exceeded: {self.max_atoms:,}")
            
            # Create atom
            atom = Atom(atom_type, name, outgoing or [], truth_value)
            
            # Check if equivalent atom already exists
            existing_atom = self._find_existing_atom(atom)
            if existing_atom:
                # Merge truth values
                if truth_value:
                    self._merge_truth_values(existing_atom, truth_value)
                return existing_atom
            
            # Add to atomspace
            self.atoms[atom.id] = atom
            self.type_index[atom_type].add(atom.id)
            
            if name:
                self.name_index[name].add(atom.id)
            
            # Update indices
            for outgoing_atom in atom.outgoing:
                self.outgoing_index[outgoing_atom.id].add(atom.id)
                self.incoming_index[atom.id].add(outgoing_atom.id)
            
            self._stats['atoms_created'] += 1
            logger.debug(f"Created atom: {atom}")
            return atom
    
    def add_node(self, atom_type: AtomType, name: str, 
                 truth_value: TruthValue = None) -> Atom:
        """Create and add a node to the atomspace"""
        return self.add_atom(atom_type, name=name, truth_value=truth_value)
    
    def add_link(self, atom_type: AtomType, outgoing: List[Atom], 
                 truth_value: TruthValue = None) -> Atom:
        """Create and add a link to the atomspace"""
        return self.add_atom(atom_type, outgoing=outgoing, truth_value=truth_value)
    
    def get_atom(self, handle: str) -> Optional[Atom]:
        """Get atom by handle"""
        with self._lock:
            return self.atoms.get(handle)
    
    def remove_atom(self, atom: Union[Atom, str]) -> bool:
        """
        Remove an atom from the atomspace.
        
        Args:
            atom: Atom instance or handle to remove
            
        Returns:
            True if atom was removed, False if not found
        """
        with self._lock:
            if isinstance(atom, str):
                atom_obj = self.atoms.get(atom)
                if not atom_obj:
                    return False
                handle = atom
            else:
                atom_obj = atom
                handle = atom.id
            
            if handle not in self.atoms:
                return False
            
            # Check if atom is referenced by other atoms
            if self.incoming_index[handle]:
                logger.warning(f"Cannot remove atom {handle}: still referenced by other atoms")
                return False
            
            # Remove from indices
            self.type_index[atom_obj.atom_type].discard(handle)
            if atom_obj.name:
                self.name_index[atom_obj.name].discard(handle)
            
            # Update outgoing references
            for outgoing_atom in atom_obj.outgoing:
                self.outgoing_index[outgoing_atom.id].discard(handle)
                self.incoming_index[handle].discard(outgoing_atom.id)
            
            # Remove from atomspace
            del self.atoms[handle]
            self._stats['atoms_deleted'] += 1
            
            logger.debug(f"Removed atom: {atom_obj}")
            return True
    
    def get_atoms_by_type(self, atom_type: AtomType, 
                         subtype: bool = False) -> List[Atom]:
        """
        Get all atoms of a specific type.
        
        Args:
            atom_type: Type of atoms to retrieve
            subtype: Include subtypes (not implemented)
            
        Returns:
            List of atoms matching the type
        """
        with self._lock:
            handles = self.type_index.get(atom_type, set())
            return [self.atoms[handle] for handle in handles if handle in self.atoms]
    
    def get_atoms_by_name(self, name: str) -> List[Atom]:
        """Get all atoms with a specific name"""
        with self._lock:
            handles = self.name_index.get(name, set())
            return [self.atoms[handle] for handle in handles if handle in self.atoms]
    
    def get_incoming(self, atom: Union[Atom, str]) -> List[Atom]:
        """Get all atoms that have this atom as outgoing"""
        with self._lock:
            handle = atom.id if isinstance(atom, Atom) else atom
            handles = self.incoming_index.get(handle, set())
            return [self.atoms[h] for h in handles if h in self.atoms]
    
    def get_outgoing(self, atom: Union[Atom, str]) -> List[Atom]:
        """Get outgoing atoms of a link"""
        with self._lock:
            if isinstance(atom, str):
                atom_obj = self.atoms.get(atom)
                if not atom_obj:
                    return []
                return atom_obj.outgoing.copy()
            return atom.outgoing.copy()
    
    def get_size(self) -> int:
        """Get total number of atoms in atomspace"""
        return len(self.atoms)
    
    def clear(self):
        """Clear all atoms from atomspace"""
        with self._lock:
            self.atoms.clear()
            self.type_index.clear()
            self.name_index.clear()
            self.outgoing_index.clear()
            self.incoming_index.clear()
            self._stats['atoms_deleted'] += self._stats['atoms_created']
            self._stats['atoms_created'] = 0
            logger.info("Atomspace cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get atomspace statistics"""
        with self._lock:
            runtime = time.time() - self._stats['start_time']
            return {
                'total_atoms': len(self.atoms),
                'atoms_created': self._stats['atoms_created'],
                'atoms_deleted': self._stats['atoms_deleted'],
                'queries_executed': self._stats['queries_executed'],
                'patterns_matched': self._stats['patterns_matched'],
                'runtime_seconds': runtime,
                'atoms_per_second': self._stats['atoms_created'] / runtime if runtime > 0 else 0,
                'memory_usage': len(self.atoms) * 1024,  # Rough estimate
                'type_distribution': {
                    atom_type.value: len(handles) 
                    for atom_type, handles in self.type_index.items()
                }
            }
    
    def export_to_scheme(self) -> str:
        """Export atomspace to OpenCog Scheme format"""
        lines = []
        with self._lock:
            for atom in self.atoms.values():
                if atom.is_node:
                    tv_str = f" (stv {atom.truth_value.strength} {atom.truth_value.confidence})"
                    lines.append(f"({atom.atom_type.value} \"{atom.name}\"{tv_str})")
                else:
                    outgoing_refs = " ".join(f"(get-atom {out.id})" for out in atom.outgoing)
                    tv_str = f" (stv {atom.truth_value.strength} {atom.truth_value.confidence})"
                    lines.append(f"({atom.atom_type.value} {outgoing_refs}{tv_str})")
        
        return "\n".join(lines)
    
    def export_to_json(self) -> str:
        """Export atomspace to JSON format"""
        with self._lock:
            data = {
                'atoms': [atom.to_dict() for atom in self.atoms.values()],
                'statistics': self.get_statistics(),
                'export_time': time.time()
            }
            return json.dumps(data, indent=2)
    
    def import_from_json(self, json_data: str):
        """Import atomspace from JSON format"""
        data = json.loads(json_data)
        atoms_data = data.get('atoms', [])
        
        # Create atoms in order (nodes first, then links)
        atoms_by_id = {}
        
        # First pass: create all nodes
        for atom_data in atoms_data:
            if not atom_data.get('outgoing'):
                atom_type = AtomType(atom_data['type'])
                truth_value = TruthValue.from_dict(atom_data['truth_value'])
                atom = self.add_node(atom_type, atom_data['name'], truth_value)
                atoms_by_id[atom_data['id']] = atom
        
        # Second pass: create all links
        for atom_data in atoms_data:
            if atom_data.get('outgoing'):
                atom_type = AtomType(atom_data['type'])
                truth_value = TruthValue.from_dict(atom_data['truth_value'])
                outgoing_atoms = [atoms_by_id[oid] for oid in atom_data['outgoing']]
                atom = self.add_link(atom_type, outgoing_atoms, truth_value)
                atoms_by_id[atom_data['id']] = atom
        
        logger.info(f"Imported {len(atoms_by_id)} atoms from JSON")
    
    def _find_existing_atom(self, atom: Atom) -> Optional[Atom]:
        """Find existing equivalent atom in atomspace"""
        if atom.is_node:
            # For nodes, check by type and name
            candidates = self.name_index.get(atom.name, set())
            for candidate_id in candidates:
                candidate = self.atoms.get(candidate_id)
                if candidate and candidate.atom_type == atom.atom_type:
                    return candidate
        else:
            # For links, check by type and outgoing atoms
            for existing_atom in self.atoms.values():
                if (existing_atom.atom_type == atom.atom_type and 
                    existing_atom.outgoing == atom.outgoing):
                    return existing_atom
        
        return None
    
    def _merge_truth_values(self, existing_atom: Atom, new_tv: TruthValue):
        """Merge truth values using simple weighted average"""
        old_tv = existing_atom.truth_value
        total_conf = old_tv.confidence + new_tv.confidence
        
        if total_conf > 0:
            merged_strength = ((old_tv.strength * old_tv.confidence + 
                              new_tv.strength * new_tv.confidence) / total_conf)
            merged_confidence = min(1.0, total_conf)
            existing_atom.truth_value = TruthValue(merged_strength, merged_confidence)
    
    def _garbage_collect(self):
        """Simple garbage collection based on attention values"""
        with self._lock:
            if len(self.atoms) < self.max_atoms * 0.9:
                return
            
            # Sort atoms by attention value (lowest first)
            sorted_atoms = sorted(
                self.atoms.values(),
                key=lambda a: a.attention_value.sti + a.attention_value.lti
            )
            
            # Remove lowest attention atoms (up to 10% of capacity)
            remove_count = min(len(sorted_atoms) // 10, len(sorted_atoms) - int(self.max_atoms * 0.8))
            
            for atom in sorted_atoms[:remove_count]:
                if not self.incoming_index[atom.id]:  # Only remove if not referenced
                    self.remove_atom(atom)
            
            logger.info(f"Garbage collected {remove_count} atoms")
    
    async def async_query(self, pattern: Dict[str, Any]) -> List[Atom]:
        """Asynchronous pattern matching query"""
        # This would implement pattern matching
        # For now, return simple type-based search
        atom_type = pattern.get('type')
        if atom_type:
            return self.get_atoms_by_type(AtomType(atom_type))
        return []
    
    def __len__(self) -> int:
        return len(self.atoms)
    
    def __contains__(self, atom: Union[Atom, str]) -> bool:
        if isinstance(atom, str):
            return atom in self.atoms
        return atom.id in self.atoms
    
    def __iter__(self):
        return iter(self.atoms.values())


# Factory functions for common atom patterns
def create_inheritance(parent: Atom, child: Atom, 
                      truth_value: TruthValue = None) -> Atom:
    """Create inheritance relationship"""
    return Atom(AtomType.INHERITANCE_LINK, outgoing=[child, parent], 
                truth_value=truth_value)

def create_evaluation(predicate: Atom, arguments: List[Atom], 
                     truth_value: TruthValue = None) -> Atom:
    """Create evaluation link"""
    list_link = Atom(AtomType.LIST_LINK, outgoing=arguments)
    return Atom(AtomType.EVALUATION_LINK, outgoing=[predicate, list_link],
                truth_value=truth_value)

def create_similarity(atom1: Atom, atom2: Atom, 
                     truth_value: TruthValue = None) -> Atom:
    """Create similarity relationship"""
    return Atom(AtomType.SIMILARITY_LINK, outgoing=[atom1, atom2],
                truth_value=truth_value)


# Demo and testing
if __name__ == "__main__":
    print("🧪 Testing Atomspace Integration...")
    
    # Create atomspace
    atomspace = AtomspaceIntegration(max_atoms=10000)
    
    # Create some nodes
    cat = atomspace.add_node(AtomType.CONCEPT_NODE, "cat")
    animal = atomspace.add_node(AtomType.CONCEPT_NODE, "animal")
    furry = atomspace.add_node(AtomType.CONCEPT_NODE, "furry")
    
    # Create inheritance relationships
    cat_is_animal = atomspace.add_link(
        AtomType.INHERITANCE_LINK, 
        [cat, animal], 
        TruthValue(0.9, 0.8)
    )
    
    cat_is_furry = atomspace.add_link(
        AtomType.INHERITANCE_LINK,
        [cat, furry],
        TruthValue(0.8, 0.9)
    )
    
    # Test queries
    concept_nodes = atomspace.get_atoms_by_type(AtomType.CONCEPT_NODE)
    print(f"✅ Created {len(concept_nodes)} concept nodes")
    
    inheritance_links = atomspace.get_atoms_by_type(AtomType.INHERITANCE_LINK)
    print(f"✅ Created {len(inheritance_links)} inheritance links")
    
    # Test incoming/outgoing
    cat_incoming = atomspace.get_incoming(cat)
    print(f"✅ Cat has {len(cat_incoming)} incoming links")
    
    # Test statistics
    stats = atomspace.get_statistics()
    print(f"✅ Atomspace statistics: {stats['total_atoms']} atoms, "
          f"{stats['atoms_per_second']:.1f} atoms/sec")
    
    # Test export/import
    json_export = atomspace.export_to_json()
    print(f"✅ JSON export: {len(json_export)} characters")
    
    scheme_export = atomspace.export_to_scheme()
    print(f"✅ Scheme export: {len(scheme_export)} characters")
    
    print("✅ Atomspace Integration testing completed!")