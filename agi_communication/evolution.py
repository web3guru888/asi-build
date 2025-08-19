"""
Emergent Language Evolution Capabilities
=======================================

Advanced system for evolving communication languages and protocols
between AGIs, enabling the emergence of new symbolic systems and
communication conventions through interaction and learning.
"""

import asyncio
import json
import random
import numpy as np
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import uuid
from collections import defaultdict, deque
import heapq

from .core import CommunicationMessage, MessageType

logger = logging.getLogger(__name__)

class LanguageComponent(Enum):
    """Components of emergent languages."""
    SYMBOL = "symbol"
    GRAMMAR_RULE = "grammar_rule"
    SEMANTIC_MAPPING = "semantic_mapping"
    PRAGMATIC_RULE = "pragmatic_rule"
    COMMUNICATION_PROTOCOL = "communication_protocol"

class EvolutionMechanism(Enum):
    """Mechanisms for language evolution."""
    SELECTION = "selection"  # Natural selection of successful patterns
    MUTATION = "mutation"    # Random variation
    CROSSOVER = "crossover"  # Combination of patterns
    DRIFT = "drift"          # Random drift
    INNOVATION = "innovation" # Novel pattern creation
    IMITATION = "imitation"  # Learning from others

class FitnessMetric(Enum):
    """Metrics for evaluating language fitness."""
    COMMUNICATION_SUCCESS = "communication_success"
    EFFICIENCY = "efficiency"
    EXPRESSIVENESS = "expressiveness"
    LEARNABILITY = "learnability"
    COMPOSITIONALITY = "compositionality"
    DISTINCTIVENESS = "distinctiveness"

@dataclass
class LanguageGene:
    """Represents a unit of linguistic information."""
    id: str
    component_type: LanguageComponent
    content: Any
    fitness_score: float = 0.0
    usage_count: int = 0
    success_rate: float = 0.0
    age: int = 0  # Generations since creation
    parent_genes: List[str] = field(default_factory=list)
    mutations: int = 0
    contexts: Set[str] = field(default_factory=set)  # Contexts where used
    
    def update_fitness(self, success: bool):
        """Update fitness based on usage success."""
        self.usage_count += 1
        if success:
            self.success_rate = ((self.success_rate * (self.usage_count - 1)) + 1.0) / self.usage_count
        else:
            self.success_rate = (self.success_rate * (self.usage_count - 1)) / self.usage_count
        
        # Update overall fitness score
        self.fitness_score = self._calculate_fitness()
    
    def _calculate_fitness(self) -> float:
        """Calculate overall fitness score."""
        # Base fitness from success rate
        base_fitness = self.success_rate
        
        # Bonus for usage frequency (but with diminishing returns)
        usage_bonus = min(0.2, self.usage_count / 100.0)
        
        # Age penalty (older genes may become obsolete)
        age_penalty = max(0, (self.age - 50) / 100.0) * 0.1
        
        # Mutation penalty (too many mutations may be detrimental)
        mutation_penalty = min(0.1, self.mutations / 10.0) * 0.05
        
        return max(0, base_fitness + usage_bonus - age_penalty - mutation_penalty)

@dataclass
class LanguagePopulation:
    """Population of language genes."""
    id: str
    name: str
    genes: Dict[str, LanguageGene] = field(default_factory=dict)
    generation: int = 0
    population_size: int = 1000
    selection_pressure: float = 0.1
    mutation_rate: float = 0.01
    crossover_rate: float = 0.3
    innovation_rate: float = 0.05
    
    def add_gene(self, gene: LanguageGene):
        """Add gene to population."""
        self.genes[gene.id] = gene
    
    def remove_gene(self, gene_id: str):
        """Remove gene from population."""
        if gene_id in self.genes:
            del self.genes[gene_id]
    
    def get_fittest_genes(self, n: int) -> List[LanguageGene]:
        """Get top n fittest genes."""
        return sorted(self.genes.values(), key=lambda g: g.fitness_score, reverse=True)[:n]
    
    def get_gene_diversity(self) -> float:
        """Calculate genetic diversity of population."""
        if not self.genes:
            return 0.0
        
        # Simple diversity measure based on component types
        type_counts = defaultdict(int)
        for gene in self.genes.values():
            type_counts[gene.component_type] += 1
        
        # Shannon entropy
        total = len(self.genes)
        entropy = 0.0
        for count in type_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * np.log2(p)
        
        return entropy

@dataclass
class CommunicationEvent:
    """Record of a communication event for language evolution."""
    id: str
    sender_id: str
    receiver_id: str
    message_content: Any
    genes_used: List[str]
    success: bool
    understanding_score: float
    efficiency_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    context: str = ""

class LanguageInnovator:
    """Creates novel language patterns through various mechanisms."""
    
    def __init__(self):
        self.innovation_strategies = {
            'symbol_creation': self._create_symbol,
            'grammar_induction': self._induce_grammar,
            'semantic_shift': self._shift_semantics,
            'protocol_adaptation': self._adapt_protocol
        }
    
    def innovate(self, strategy: str, context: Dict[str, Any]) -> LanguageGene:
        """Create novel language gene using specified strategy."""
        if strategy in self.innovation_strategies:
            return self.innovation_strategies[strategy](context)
        else:
            return self._random_innovation(context)
    
    def _create_symbol(self, context: Dict[str, Any]) -> LanguageGene:
        """Create a new symbol."""
        # Generate novel symbol based on phonetic/visual patterns
        symbol_type = random.choice(['phonetic', 'visual', 'conceptual'])
        
        if symbol_type == 'phonetic':
            # Create phonetically plausible symbol
            consonants = 'bcdfghjklmnpqrstvwxyz'
            vowels = 'aeiou'
            syllables = random.randint(1, 3)
            symbol = ''
            
            for _ in range(syllables):
                if random.random() < 0.7:  # Start with consonant
                    symbol += random.choice(consonants)
                symbol += random.choice(vowels)
                if random.random() < 0.5:  # End with consonant
                    symbol += random.choice(consonants)
        
        elif symbol_type == 'visual':
            # Create visual symbol representation
            symbol = f"visual_symbol_{random.randint(1000, 9999)}"
        
        else:
            # Conceptual symbol
            symbol = f"concept_{uuid.uuid4().hex[:8]}"
        
        return LanguageGene(
            id=str(uuid.uuid4()),
            component_type=LanguageComponent.SYMBOL,
            content={'symbol': symbol, 'type': symbol_type, 'meaning': None},
            fitness_score=0.5  # Neutral initial fitness
        )
    
    def _induce_grammar(self, context: Dict[str, Any]) -> LanguageGene:
        """Induce new grammatical rule."""
        rule_types = ['word_order', 'morphology', 'syntax', 'composition']
        rule_type = random.choice(rule_types)
        
        if rule_type == 'word_order':
            # Create word order rule
            patterns = ['SVO', 'SOV', 'VSO', 'VOS', 'OSV', 'OVS']
            rule = {'type': 'word_order', 'pattern': random.choice(patterns)}
        
        elif rule_type == 'morphology':
            # Create morphological rule
            rule = {
                'type': 'morphology',
                'operation': random.choice(['prefix', 'suffix', 'infix']),
                'marker': f"morph_{random.randint(100, 999)}",
                'function': random.choice(['past', 'future', 'plural', 'negation', 'question'])
            }
        
        elif rule_type == 'syntax':
            # Create syntactic rule
            rule = {
                'type': 'syntax',
                'structure': random.choice(['NP+VP', 'VP+NP', 'recursive', 'embedded']),
                'constraint': random.choice(['agreement', 'case', 'binding'])
            }
        
        else:
            # Compositional rule
            rule = {
                'type': 'composition',
                'combination': random.choice(['concatenation', 'nesting', 'blending']),
                'semantics': random.choice(['additive', 'multiplicative', 'selective'])
            }
        
        return LanguageGene(
            id=str(uuid.uuid4()),
            component_type=LanguageComponent.GRAMMAR_RULE,
            content=rule,
            fitness_score=0.5
        )
    
    def _shift_semantics(self, context: Dict[str, Any]) -> LanguageGene:
        """Create semantic shift in existing symbol."""
        shift_types = ['metaphor', 'metonymy', 'generalization', 'specialization', 'analogy']
        shift_type = random.choice(shift_types)
        
        semantic_mapping = {
            'shift_type': shift_type,
            'source_concept': f"concept_{random.randint(100, 999)}",
            'target_concept': f"concept_{random.randint(100, 999)}",
            'similarity_basis': random.choice(['functional', 'structural', 'causal', 'temporal'])
        }
        
        return LanguageGene(
            id=str(uuid.uuid4()),
            component_type=LanguageComponent.SEMANTIC_MAPPING,
            content=semantic_mapping,
            fitness_score=0.5
        )
    
    def _adapt_protocol(self, context: Dict[str, Any]) -> LanguageGene:
        """Adapt communication protocol."""
        protocol_types = ['turn_taking', 'error_correction', 'confirmation', 'elaboration']
        protocol_type = random.choice(protocol_types)
        
        if protocol_type == 'turn_taking':
            protocol = {
                'type': 'turn_taking',
                'signal': f"turn_signal_{random.randint(100, 999)}",
                'duration': random.uniform(0.5, 5.0)
            }
        elif protocol_type == 'error_correction':
            protocol = {
                'type': 'error_correction',
                'strategy': random.choice(['repeat', 'rephrase', 'clarify', 'simplify']),
                'threshold': random.uniform(0.3, 0.8)
            }
        elif protocol_type == 'confirmation':
            protocol = {
                'type': 'confirmation',
                'method': random.choice(['echo', 'paraphrase', 'acknowledgment']),
                'frequency': random.uniform(0.1, 1.0)
            }
        else:
            protocol = {
                'type': 'elaboration',
                'trigger': random.choice(['confusion', 'interest', 'request']),
                'detail_level': random.uniform(0.1, 1.0)
            }
        
        return LanguageGene(
            id=str(uuid.uuid4()),
            component_type=LanguageComponent.COMMUNICATION_PROTOCOL,
            content=protocol,
            fitness_score=0.5
        )
    
    def _random_innovation(self, context: Dict[str, Any]) -> LanguageGene:
        """Create random innovation."""
        component_types = list(LanguageComponent)
        component_type = random.choice(component_types)
        
        return LanguageGene(
            id=str(uuid.uuid4()),
            component_type=component_type,
            content={'type': 'random', 'data': f"random_{uuid.uuid4().hex[:8]}"},
            fitness_score=random.uniform(0.3, 0.7)
        )

class EvolutionaryOperators:
    """Operators for evolving language populations."""
    
    @staticmethod
    def mutate_gene(gene: LanguageGene, mutation_rate: float) -> LanguageGene:
        """Mutate a language gene."""
        if random.random() > mutation_rate:
            return gene  # No mutation
        
        # Create mutated version
        mutated_gene = LanguageGene(
            id=str(uuid.uuid4()),
            component_type=gene.component_type,
            content=EvolutionaryOperators._mutate_content(gene.content, gene.component_type),
            fitness_score=gene.fitness_score * random.uniform(0.8, 1.2),  # Slight fitness change
            parent_genes=[gene.id],
            mutations=gene.mutations + 1
        )
        
        return mutated_gene
    
    @staticmethod
    def _mutate_content(content: Any, component_type: LanguageComponent) -> Any:
        """Mutate gene content based on component type."""
        if component_type == LanguageComponent.SYMBOL:
            if isinstance(content, dict) and 'symbol' in content:
                # Mutate symbol
                symbol = content['symbol']
                if len(symbol) > 0:
                    # Random character substitution, insertion, or deletion
                    mutation_type = random.choice(['substitute', 'insert', 'delete'])
                    
                    if mutation_type == 'substitute' and len(symbol) > 0:
                        pos = random.randint(0, len(symbol) - 1)
                        chars = 'abcdefghijklmnopqrstuvwxyz'
                        new_char = random.choice(chars)
                        symbol = symbol[:pos] + new_char + symbol[pos+1:]
                    
                    elif mutation_type == 'insert':
                        pos = random.randint(0, len(symbol))
                        chars = 'abcdefghijklmnopqrstuvwxyz'
                        new_char = random.choice(chars)
                        symbol = symbol[:pos] + new_char + symbol[pos:]
                    
                    elif mutation_type == 'delete' and len(symbol) > 1:
                        pos = random.randint(0, len(symbol) - 1)
                        symbol = symbol[:pos] + symbol[pos+1:]
                
                mutated_content = content.copy()
                mutated_content['symbol'] = symbol
                return mutated_content
        
        elif component_type == LanguageComponent.GRAMMAR_RULE:
            if isinstance(content, dict):
                mutated_content = content.copy()
                # Randomly modify one aspect of the rule
                if 'pattern' in content:
                    patterns = ['SVO', 'SOV', 'VSO', 'VOS', 'OSV', 'OVS']
                    mutated_content['pattern'] = random.choice(patterns)
                return mutated_content
        
        # Default: return slightly modified content
        if isinstance(content, dict):
            mutated_content = content.copy()
            mutated_content['mutation_id'] = uuid.uuid4().hex[:8]
            return mutated_content
        
        return content
    
    @staticmethod
    def crossover_genes(parent1: LanguageGene, parent2: LanguageGene) -> LanguageGene:
        """Create offspring through crossover of two parent genes."""
        if parent1.component_type != parent2.component_type:
            # Cannot crossover different component types, return random parent
            return random.choice([parent1, parent2])
        
        # Create offspring by combining parent features
        offspring_content = EvolutionaryOperators._combine_content(
            parent1.content, parent2.content, parent1.component_type
        )
        
        offspring = LanguageGene(
            id=str(uuid.uuid4()),
            component_type=parent1.component_type,
            content=offspring_content,
            fitness_score=(parent1.fitness_score + parent2.fitness_score) / 2,
            parent_genes=[parent1.id, parent2.id]
        )
        
        return offspring
    
    @staticmethod
    def _combine_content(content1: Any, content2: Any, component_type: LanguageComponent) -> Any:
        """Combine content from two parents."""
        if isinstance(content1, dict) and isinstance(content2, dict):
            combined = {}
            all_keys = set(content1.keys()) | set(content2.keys())
            
            for key in all_keys:
                if key in content1 and key in content2:
                    # Randomly choose from parents
                    combined[key] = random.choice([content1[key], content2[key]])
                elif key in content1:
                    combined[key] = content1[key]
                else:
                    combined[key] = content2[key]
            
            return combined
        
        # Default: random selection
        return random.choice([content1, content2])
    
    @staticmethod
    def select_survivors(population: LanguagePopulation, selection_pressure: float) -> List[LanguageGene]:
        """Select surviving genes based on fitness."""
        genes = list(population.genes.values())
        
        # Sort by fitness
        genes.sort(key=lambda g: g.fitness_score, reverse=True)
        
        # Select top performers
        num_survivors = max(1, int(len(genes) * (1 - selection_pressure)))
        survivors = genes[:num_survivors]
        
        # Add some random survivors for diversity
        num_random = max(0, int(len(genes) * 0.05))  # 5% random survivors
        remaining = genes[num_survivors:]
        if remaining:
            random_survivors = random.sample(remaining, min(num_random, len(remaining)))
            survivors.extend(random_survivors)
        
        return survivors

class EmergentLanguageEvolver:
    """
    Emergent Language Evolution System
    
    Enables the evolution of communication languages and protocols
    between AGIs through natural selection, mutation, and innovation.
    """
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.populations: Dict[str, LanguagePopulation] = {}
        self.innovator = LanguageInnovator()
        self.operators = EvolutionaryOperators()
        self.communication_events: List[CommunicationEvent] = []
        self.evolution_history: List[Dict[str, Any]] = []
        
        # Evolution parameters
        self.generation_size = 1000
        self.evolution_interval = timedelta(hours=1)
        self.fitness_decay_rate = 0.95
        
        # Create default population
        self._create_default_population()
        
        # Start evolution process
        asyncio.create_task(self._evolution_loop())
    
    def _create_default_population(self):
        """Create default language population."""
        default_pop = LanguagePopulation(
            id="default",
            name="Default Language Population",
            population_size=self.generation_size
        )
        
        # Seed with basic language genes
        for _ in range(100):
            # Create basic symbols
            symbol_gene = self.innovator.innovate('symbol_creation', {})
            default_pop.add_gene(symbol_gene)
            
            # Create basic grammar rules
            grammar_gene = self.innovator.innovate('grammar_induction', {})
            default_pop.add_gene(grammar_gene)
        
        self.populations["default"] = default_pop
    
    async def evolve_language(self, population_id: str = "default") -> Dict[str, Any]:
        """Run one generation of language evolution."""
        if population_id not in self.populations:
            raise ValueError(f"Population {population_id} not found")
        
        population = self.populations[population_id]
        
        # Update gene fitness based on recent communications
        self._update_gene_fitness(population)
        
        # Selection
        survivors = self.operators.select_survivors(population, population.selection_pressure)
        
        # Create new generation
        new_genes = {}
        
        # Keep survivors
        for gene in survivors:
            gene.age += 1
            new_genes[gene.id] = gene
        
        # Generate offspring through crossover
        while len(new_genes) < population.population_size * 0.8:
            parent1, parent2 = random.sample(survivors, 2)
            if random.random() < population.crossover_rate:
                offspring = self.operators.crossover_genes(parent1, parent2)
                new_genes[offspring.id] = offspring
        
        # Generate mutated variants
        for gene in list(new_genes.values()):
            if random.random() < population.mutation_rate:
                mutated = self.operators.mutate_gene(gene, 1.0)  # Force mutation
                new_genes[mutated.id] = mutated
        
        # Add innovations
        while len(new_genes) < population.population_size:
            strategy = random.choice(list(self.innovator.innovation_strategies.keys()))
            innovation = self.innovator.innovate(strategy, {})
            new_genes[innovation.id] = innovation
        
        # Update population
        population.genes = new_genes
        population.generation += 1
        
        # Record evolution
        evolution_record = {
            'timestamp': datetime.now().isoformat(),
            'population_id': population_id,
            'generation': population.generation,
            'population_size': len(new_genes),
            'avg_fitness': sum(gene.fitness_score for gene in new_genes.values()) / len(new_genes),
            'diversity': population.get_gene_diversity(),
            'survivors_count': len(survivors)
        }
        
        self.evolution_history.append(evolution_record)
        
        return evolution_record
    
    def _update_gene_fitness(self, population: LanguagePopulation):
        """Update gene fitness based on recent communication events."""
        # Decay existing fitness
        for gene in population.genes.values():
            gene.fitness_score *= self.fitness_decay_rate
        
        # Update based on recent events
        recent_events = [
            event for event in self.communication_events
            if (datetime.now() - event.timestamp) < timedelta(hours=24)
        ]
        
        for event in recent_events:
            for gene_id in event.genes_used:
                if gene_id in population.genes:
                    gene = population.genes[gene_id]
                    
                    # Update fitness based on communication success
                    success_weight = 0.4
                    understanding_weight = 0.3
                    efficiency_weight = 0.3
                    
                    fitness_change = (
                        (1.0 if event.success else 0.0) * success_weight +
                        event.understanding_score * understanding_weight +
                        event.efficiency_score * efficiency_weight
                    )
                    
                    gene.update_fitness(fitness_change > 0.5)
                    
                    # Add context
                    if event.context:
                        gene.contexts.add(event.context)
    
    async def record_communication_event(self, sender_id: str, receiver_id: str,
                                       message_content: Any, genes_used: List[str],
                                       success: bool, understanding_score: float = 0.5,
                                       efficiency_score: float = 0.5, context: str = ""):
        """Record a communication event for evolution feedback."""
        event = CommunicationEvent(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_content=message_content,
            genes_used=genes_used,
            success=success,
            understanding_score=understanding_score,
            efficiency_score=efficiency_score,
            context=context
        )
        
        self.communication_events.append(event)
        
        # Keep events limited
        if len(self.communication_events) > 10000:
            self.communication_events = self.communication_events[-8000:]
    
    async def generate_novel_expression(self, concept: str, population_id: str = "default") -> Dict[str, Any]:
        """Generate novel expression for a concept using evolved language."""
        if population_id not in self.populations:
            return {"expression": concept, "confidence": 0.5}
        
        population = self.populations[population_id]
        
        # Get relevant genes
        symbol_genes = [gene for gene in population.genes.values() 
                       if gene.component_type == LanguageComponent.SYMBOL]
        grammar_genes = [gene for gene in population.genes.values() 
                        if gene.component_type == LanguageComponent.GRAMMAR_RULE]
        
        if not symbol_genes:
            return {"expression": concept, "confidence": 0.3}
        
        # Select genes based on fitness
        selected_symbols = sorted(symbol_genes, key=lambda g: g.fitness_score, reverse=True)[:5]
        selected_grammars = sorted(grammar_genes, key=lambda g: g.fitness_score, reverse=True)[:3]
        
        # Generate expression
        expression_parts = []
        genes_used = []
        
        # Use symbols
        for symbol_gene in selected_symbols[:2]:  # Use top 2 symbols
            symbol_content = symbol_gene.content
            if isinstance(symbol_content, dict) and 'symbol' in symbol_content:
                expression_parts.append(symbol_content['symbol'])
                genes_used.append(symbol_gene.id)
        
        # Apply grammar rules
        if selected_grammars and expression_parts:
            grammar_gene = selected_grammars[0]
            grammar_rule = grammar_gene.content
            
            if isinstance(grammar_rule, dict) and 'type' in grammar_rule:
                if grammar_rule['type'] == 'word_order' and len(expression_parts) >= 2:
                    pattern = grammar_rule.get('pattern', 'SVO')
                    if pattern == 'SOV':
                        expression_parts = [expression_parts[1], expression_parts[0]]  # Reverse order
                
                genes_used.append(grammar_gene.id)
        
        # Combine into expression
        expression = " ".join(expression_parts) if expression_parts else concept
        
        # Calculate confidence based on gene fitness
        avg_fitness = sum(population.genes[gene_id].fitness_score for gene_id in genes_used) / max(1, len(genes_used))
        confidence = min(0.95, avg_fitness * 1.2)
        
        return {
            "expression": expression,
            "confidence": confidence,
            "genes_used": genes_used,
            "population_id": population_id
        }
    
    async def interpret_novel_expression(self, expression: str, population_id: str = "default") -> Dict[str, Any]:
        """Interpret novel expression using evolved language knowledge."""
        if population_id not in self.populations:
            return {"interpretation": expression, "confidence": 0.3}
        
        population = self.populations[population_id]
        
        # Find matching genes
        matching_genes = []
        
        for gene in population.genes.values():
            if gene.component_type == LanguageComponent.SYMBOL:
                symbol_content = gene.content
                if isinstance(symbol_content, dict) and 'symbol' in symbol_content:
                    symbol = symbol_content['symbol']
                    if symbol in expression:
                        matching_genes.append((gene, 'symbol_match'))
            
            elif gene.component_type == LanguageComponent.SEMANTIC_MAPPING:
                # Check for semantic patterns
                mapping = gene.content
                if isinstance(mapping, dict) and 'source_concept' in mapping:
                    if any(concept in expression for concept in mapping.values() if isinstance(concept, str)):
                        matching_genes.append((gene, 'semantic_match'))
        
        if not matching_genes:
            return {"interpretation": expression, "confidence": 0.2}
        
        # Generate interpretation based on matching genes
        interpretation_parts = []
        confidence_scores = []
        
        for gene, match_type in matching_genes:
            if match_type == 'symbol_match':
                symbol_content = gene.content
                if isinstance(symbol_content, dict):
                    meaning = symbol_content.get('meaning', 'unknown_concept')
                    if meaning:
                        interpretation_parts.append(str(meaning))
                        confidence_scores.append(gene.fitness_score)
            
            elif match_type == 'semantic_match':
                mapping = gene.content
                if isinstance(mapping, dict):
                    target_concept = mapping.get('target_concept', 'mapped_concept')
                    interpretation_parts.append(str(target_concept))
                    confidence_scores.append(gene.fitness_score)
        
        # Combine interpretation
        interpretation = " ".join(interpretation_parts) if interpretation_parts else expression
        avg_confidence = sum(confidence_scores) / max(1, len(confidence_scores))
        
        return {
            "interpretation": interpretation,
            "confidence": avg_confidence,
            "matching_genes": len(matching_genes)
        }
    
    async def _evolution_loop(self):
        """Background evolution loop."""
        while True:
            try:
                for population_id in self.populations:
                    await self.evolve_language(population_id)
                
                await asyncio.sleep(self.evolution_interval.total_seconds())
            
            except Exception as e:
                logger.error(f"Error in evolution loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retrying
    
    async def handle_language_evolution(self, message: CommunicationMessage):
        """Handle language evolution message from another AGI."""
        payload = message.payload
        action = payload.get('action')
        
        try:
            if action == 'expression_generation':
                await self._handle_expression_generation(message)
            elif action == 'expression_interpretation':
                await self._handle_expression_interpretation(message)
            elif action == 'language_sharing':
                await self._handle_language_sharing(message)
            else:
                logger.warning(f"Unknown language evolution action: {action}")
        
        except Exception as e:
            logger.error(f"Error handling language evolution: {e}")
    
    async def _handle_expression_generation(self, message: CommunicationMessage):
        """Handle expression generation request."""
        payload = message.payload
        concept = payload.get('concept', '')
        population_id = payload.get('population_id', 'default')
        
        result = await self.generate_novel_expression(concept, population_id)
        
        response_message = CommunicationMessage(
            id=str(uuid.uuid4()),
            sender_id=self.protocol.identity.id,
            receiver_id=message.sender_id,
            message_type=MessageType.LANGUAGE_EVOLUTION,
            timestamp=datetime.now(),
            payload={
                'action': 'expression_response',
                'original_message_id': message.id,
                'concept': concept,
                'result': result
            }
        )
        
        await self.protocol.send_message(response_message)
    
    async def _handle_expression_interpretation(self, message: CommunicationMessage):
        """Handle expression interpretation request."""
        payload = message.payload
        expression = payload.get('expression', '')
        population_id = payload.get('population_id', 'default')
        
        result = await self.interpret_novel_expression(expression, population_id)
        
        response_message = CommunicationMessage(
            id=str(uuid.uuid4()),
            sender_id=self.protocol.identity.id,
            receiver_id=message.sender_id,
            message_type=MessageType.LANGUAGE_EVOLUTION,
            timestamp=datetime.now(),
            payload={
                'action': 'interpretation_response',
                'original_message_id': message.id,
                'expression': expression,
                'result': result
            }
        )
        
        await self.protocol.send_message(response_message)
    
    async def _handle_language_sharing(self, message: CommunicationMessage):
        """Handle language gene sharing."""
        payload = message.payload
        shared_genes_data = payload.get('genes', [])
        
        # Import shared genes into local population
        population = self.populations.get('default')
        if population:
            for gene_data in shared_genes_data[:10]:  # Limit imports
                try:
                    gene = LanguageGene(
                        id=gene_data['id'],
                        component_type=LanguageComponent(gene_data['component_type']),
                        content=gene_data['content'],
                        fitness_score=gene_data.get('fitness_score', 0.5),
                        usage_count=gene_data.get('usage_count', 0),
                        success_rate=gene_data.get('success_rate', 0.5)
                    )
                    
                    # Add with reduced fitness (foreign gene penalty)
                    gene.fitness_score *= 0.7
                    population.add_gene(gene)
                    
                except Exception as e:
                    logger.warning(f"Error importing gene: {e}")
    
    def get_evolution_statistics(self) -> Dict[str, Any]:
        """Get language evolution statistics."""
        if not self.populations:
            return {'total_populations': 0}
        
        stats = {
            'total_populations': len(self.populations),
            'communication_events': len(self.communication_events),
            'evolution_generations': len(self.evolution_history)
        }
        
        # Population statistics
        for pop_id, population in self.populations.items():
            pop_stats = {
                'generation': population.generation,
                'population_size': len(population.genes),
                'diversity': population.get_gene_diversity(),
                'avg_fitness': sum(g.fitness_score for g in population.genes.values()) / max(1, len(population.genes)),
                'component_distribution': {}
            }
            
            # Component type distribution
            for gene in population.genes.values():
                comp_type = gene.component_type.value
                pop_stats['component_distribution'][comp_type] = pop_stats['component_distribution'].get(comp_type, 0) + 1
            
            stats[f'population_{pop_id}'] = pop_stats
        
        return stats