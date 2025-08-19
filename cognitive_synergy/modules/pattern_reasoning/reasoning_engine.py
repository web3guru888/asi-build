"""
Reasoning Engine
===============

Advanced reasoning system that performs logical inference, hypothesis formation,
and knowledge synthesis. Integrates with pattern mining through bidirectional
information flow to enable emergent cognitive capabilities.
"""

import numpy as np
import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import time
import logging
import itertools
from abc import ABC, abstractmethod


class ReasoningType(Enum):
    """Types of reasoning"""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"


@dataclass
class Hypothesis:
    """Represents a reasoning hypothesis"""
    id: str
    content: str
    reasoning_type: ReasoningType
    confidence: float
    evidence: List[str] = field(default_factory=list)
    predictions: List[str] = field(default_factory=list)
    support_count: int = 0
    refutation_count: int = 0
    creation_time: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Inference:
    """Represents an inference step"""
    id: str
    premises: List[str]
    conclusion: str
    inference_type: ReasoningType
    confidence: float
    rule_applied: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeItem:
    """Represents a piece of knowledge"""
    id: str
    content: Any
    knowledge_type: str  # 'fact', 'rule', 'concept', 'relationship'
    confidence: float
    source: str
    timestamp: float = field(default_factory=time.time)
    connections: Set[str] = field(default_factory=set)


class ReasoningRule(ABC):
    """Abstract base class for reasoning rules"""
    
    @abstractmethod
    def can_apply(self, premises: List[KnowledgeItem]) -> bool:
        """Check if rule can be applied to given premises"""
        pass
    
    @abstractmethod
    def apply(self, premises: List[KnowledgeItem]) -> List[Inference]:
        """Apply rule to premises and generate inferences"""
        pass


class DeductiveRule(ReasoningRule):
    """Deductive reasoning rule (modus ponens, syllogism, etc.)"""
    
    def __init__(self, name: str, pattern: str):
        self.name = name
        self.pattern = pattern
    
    def can_apply(self, premises: List[KnowledgeItem]) -> bool:
        """Check for modus ponens pattern: A -> B, A, therefore B"""
        if len(premises) < 2:
            return False
        
        # Look for implication and its antecedent
        implications = [p for p in premises if 'implies' in str(p.content)]
        facts = [p for p in premises if p.knowledge_type == 'fact']
        
        return len(implications) > 0 and len(facts) > 0
    
    def apply(self, premises: List[KnowledgeItem]) -> List[Inference]:
        """Apply modus ponens"""
        inferences = []
        
        implications = [p for p in premises if 'implies' in str(p.content)]
        facts = [p for p in premises if p.knowledge_type == 'fact']
        
        for impl in implications:
            for fact in facts:
                # Simple pattern matching for A -> B, A |- B
                if self._matches_antecedent(impl, fact):
                    conclusion = self._extract_consequent(impl)
                    if conclusion:
                        inference = Inference(
                            id=f"deductive_{int(time.time() * 1000)}",
                            premises=[impl.id, fact.id],
                            conclusion=conclusion,
                            inference_type=ReasoningType.DEDUCTIVE,
                            confidence=min(impl.confidence, fact.confidence),
                            rule_applied=self.name
                        )
                        inferences.append(inference)
        
        return inferences
    
    def _matches_antecedent(self, implication: KnowledgeItem, fact: KnowledgeItem) -> bool:
        """Check if fact matches antecedent of implication"""
        # Simplified matching - in practice would use more sophisticated logic
        impl_str = str(implication.content).lower()
        fact_str = str(fact.content).lower()
        
        # Look for key terms from fact in implication antecedent
        fact_terms = fact_str.split()
        return any(term in impl_str for term in fact_terms if len(term) > 2)
    
    def _extract_consequent(self, implication: KnowledgeItem) -> Optional[str]:
        """Extract consequent from implication"""
        impl_str = str(implication.content)
        if 'implies' in impl_str:
            parts = impl_str.split('implies')
            if len(parts) >= 2:
                return parts[1].strip()
        return None


class InductiveRule(ReasoningRule):
    """Inductive reasoning rule - generalize from specific instances"""
    
    def can_apply(self, premises: List[KnowledgeItem]) -> bool:
        """Check if we have multiple similar instances for generalization"""
        facts = [p for p in premises if p.knowledge_type == 'fact']
        return len(facts) >= 3
    
    def apply(self, premises: List[KnowledgeItem]) -> List[Inference]:
        """Apply inductive generalization"""
        inferences = []
        facts = [p for p in premises if p.knowledge_type == 'fact']
        
        # Group facts by similarity
        fact_groups = self._group_similar_facts(facts)
        
        for group in fact_groups:
            if len(group) >= 3:  # Need multiple instances
                # Generate generalization
                generalization = self._generate_generalization(group)
                if generalization:
                    confidence = len(group) / len(facts)  # Confidence based on support
                    
                    inference = Inference(
                        id=f"inductive_{int(time.time() * 1000)}",
                        premises=[f.id for f in group],
                        conclusion=generalization,
                        inference_type=ReasoningType.INDUCTIVE,
                        confidence=confidence,
                        rule_applied="inductive_generalization"
                    )
                    inferences.append(inference)
        
        return inferences
    
    def _group_similar_facts(self, facts: List[KnowledgeItem]) -> List[List[KnowledgeItem]]:
        """Group similar facts together"""
        groups = []
        used_facts = set()
        
        for fact in facts:
            if fact.id in used_facts:
                continue
            
            group = [fact]
            used_facts.add(fact.id)
            
            for other_fact in facts:
                if (other_fact.id not in used_facts and 
                    self._facts_similar(fact, other_fact)):
                    group.append(other_fact)
                    used_facts.add(other_fact.id)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def _facts_similar(self, fact1: KnowledgeItem, fact2: KnowledgeItem) -> bool:
        """Check if two facts are similar enough for grouping"""
        content1 = str(fact1.content).lower()
        content2 = str(fact2.content).lower()
        
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return False
        
        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union > 0.4
    
    def _generate_generalization(self, facts: List[KnowledgeItem]) -> Optional[str]:
        """Generate generalization from group of facts"""
        # Extract common terms
        all_words = []
        for fact in facts:
            words = str(fact.content).lower().split()
            all_words.extend(words)
        
        # Find most common words
        word_counts = {}
        for word in all_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        common_words = [word for word, count in word_counts.items() 
                       if count >= len(facts) * 0.7]  # Appears in 70% of facts
        
        if common_words:
            return f"Generally, {' '.join(common_words[:5])}"
        
        return None


class AbductiveRule(ReasoningRule):
    """Abductive reasoning rule - inference to best explanation"""
    
    def can_apply(self, premises: List[KnowledgeItem]) -> bool:
        """Check if we have observations that need explanation"""
        observations = [p for p in premises if 'observed' in str(p.content)]
        return len(observations) > 0
    
    def apply(self, premises: List[KnowledgeItem]) -> List[Inference]:
        """Apply abductive reasoning to find best explanations"""
        inferences = []
        
        observations = [p for p in premises if 'observed' in str(p.content)]
        potential_explanations = [p for p in premises if p.knowledge_type == 'rule']
        
        for obs in observations:
            # Find explanations that could account for observation
            explanations = self._find_explanations(obs, potential_explanations)
            
            for explanation in explanations:
                inference = Inference(
                    id=f"abductive_{int(time.time() * 1000)}",
                    premises=[obs.id, explanation.id],
                    conclusion=f"Best explanation: {explanation.content}",
                    inference_type=ReasoningType.ABDUCTIVE,
                    confidence=explanation.confidence * 0.8,  # Lower confidence for abduction
                    rule_applied="abductive_explanation"
                )
                inferences.append(inference)
        
        return inferences
    
    def _find_explanations(self, observation: KnowledgeItem, 
                          explanations: List[KnowledgeItem]) -> List[KnowledgeItem]:
        """Find potential explanations for observation"""
        relevant_explanations = []
        
        obs_content = str(observation.content).lower()
        obs_words = set(obs_content.split())
        
        for exp in explanations:
            exp_content = str(exp.content).lower()
            exp_words = set(exp_content.split())
            
            # Check if explanation could account for observation
            overlap = len(obs_words & exp_words)
            if overlap > 0:
                relevant_explanations.append(exp)
        
        return relevant_explanations


class ReasoningEngine:
    """
    Advanced reasoning engine for cognitive synergy.
    
    Performs multiple types of reasoning:
    - Deductive (logical inference from premises)
    - Inductive (generalization from instances)
    - Abductive (inference to best explanation)
    - Analogical (reasoning by similarity)
    - Causal (cause-effect reasoning)
    """
    
    def __init__(self,
                 max_knowledge_items: int = 50000,
                 max_hypotheses: int = 1000,
                 confidence_threshold: float = 0.5,
                 reasoning_depth: int = 5):
        """
        Initialize reasoning engine.
        
        Args:
            max_knowledge_items: Maximum knowledge items to maintain
            max_hypotheses: Maximum hypotheses to maintain
            confidence_threshold: Minimum confidence for valid inferences
            reasoning_depth: Maximum depth for recursive reasoning
        """
        self.max_knowledge_items = max_knowledge_items
        self.max_hypotheses = max_hypotheses
        self.confidence_threshold = confidence_threshold
        self.reasoning_depth = reasoning_depth
        
        # Knowledge base
        self.knowledge_base: Dict[str, KnowledgeItem] = {}
        self.knowledge_graph = nx.DiGraph()
        
        # Hypotheses and inferences
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.inferences: Dict[str, Inference] = {}
        
        # Reasoning rules
        self.reasoning_rules: Dict[ReasoningType, List[ReasoningRule]] = {
            ReasoningType.DEDUCTIVE: [DeductiveRule("modus_ponens", "A->B, A |- B")],
            ReasoningType.INDUCTIVE: [InductiveRule()],
            ReasoningType.ABDUCTIVE: [AbductiveRule()]
        }
        
        # Working memory for active reasoning
        self.working_memory: deque = deque(maxlen=100)
        self.reasoning_agenda: deque = deque(maxlen=1000)
        
        # Pattern mining integration
        self.pattern_feedback = {}
        self.pattern_requests = deque(maxlen=100)
        
        # Statistics
        self.reasoning_stats = {
            'inferences_made': 0,
            'hypotheses_generated': 0,
            'hypotheses_confirmed': 0,
            'hypotheses_refuted': 0,
            'total_reasoning_time': 0.0
        }
        
        # State
        self.activation_level = 0.0
        self._last_reasoning_time = 0.0
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def add_knowledge(self, content: Any, knowledge_type: str = 'fact', 
                     confidence: float = 1.0, source: str = 'input'):
        """Add knowledge item to the knowledge base"""
        knowledge_id = f"{knowledge_type}_{int(time.time() * 1000)}"
        
        knowledge_item = KnowledgeItem(
            id=knowledge_id,
            content=content,
            knowledge_type=knowledge_type,
            confidence=confidence,
            source=source
        )
        
        self.knowledge_base[knowledge_id] = knowledge_item
        self.knowledge_graph.add_node(knowledge_id)
        
        # Add to working memory if important enough
        if confidence > 0.7:
            self.working_memory.append(knowledge_item)
        
        # Trigger reasoning on new knowledge
        self.reasoning_agenda.append({
            'type': 'new_knowledge',
            'item_id': knowledge_id,
            'priority': confidence
        })
        
        self.logger.debug(f"Added knowledge: {knowledge_id}")
    
    def reason(self) -> List[Inference]:
        """Perform reasoning cycle"""
        start_time = time.time()
        new_inferences = []
        
        # Process reasoning agenda
        agenda_items = list(self.reasoning_agenda)
        self.reasoning_agenda.clear()
        
        # Sort by priority
        agenda_items.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        for item in agenda_items[:20]:  # Limit processing per cycle
            item_inferences = self._process_agenda_item(item)
            new_inferences.extend(item_inferences)
        
        # Apply different reasoning types
        deductive_inferences = self._apply_deductive_reasoning()
        inductive_inferences = self._apply_inductive_reasoning()
        abductive_inferences = self._apply_abductive_reasoning()
        analogical_inferences = self._apply_analogical_reasoning()
        
        new_inferences.extend(deductive_inferences)
        new_inferences.extend(inductive_inferences)
        new_inferences.extend(abductive_inferences)
        new_inferences.extend(analogical_inferences)
        
        # Filter and validate inferences
        valid_inferences = self._validate_inferences(new_inferences)
        
        # Add valid inferences to knowledge base
        for inference in valid_inferences:
            self.inferences[inference.id] = inference
            
            # Convert conclusion to knowledge if confidence is high enough
            if inference.confidence > self.confidence_threshold:
                self.add_knowledge(
                    content=inference.conclusion,
                    knowledge_type='derived_fact',
                    confidence=inference.confidence,
                    source='reasoning'
                )
        
        # Update statistics
        reasoning_time = time.time() - start_time
        self.reasoning_stats['total_reasoning_time'] += reasoning_time
        self.reasoning_stats['inferences_made'] += len(valid_inferences)
        self._last_reasoning_time = reasoning_time
        
        # Update activation
        self.activation_level = min(1.0, len(valid_inferences) / 10.0)
        
        return valid_inferences
    
    def _process_agenda_item(self, item: Dict[str, Any]) -> List[Inference]:
        """Process individual agenda item"""
        item_type = item.get('type')
        inferences = []
        
        if item_type == 'new_knowledge':
            item_id = item.get('item_id')
            if item_id in self.knowledge_base:
                # Trigger reasoning on this specific knowledge
                inferences.extend(self._reason_about_knowledge(self.knowledge_base[item_id]))
        elif item_type == 'hypothesis_test':
            hypothesis_id = item.get('hypothesis_id')
            if hypothesis_id in self.hypotheses:
                inferences.extend(self._test_hypothesis(self.hypotheses[hypothesis_id]))
        
        return inferences
    
    def _reason_about_knowledge(self, knowledge_item: KnowledgeItem) -> List[Inference]:
        """Reason about specific knowledge item"""
        inferences = []
        
        # Find related knowledge
        related_knowledge = self._find_related_knowledge(knowledge_item)
        
        # Apply reasoning rules to this knowledge and related knowledge
        premises = [knowledge_item] + related_knowledge[:10]  # Limit premises
        
        for reasoning_type, rules in self.reasoning_rules.items():
            for rule in rules:
                if rule.can_apply(premises):
                    rule_inferences = rule.apply(premises)
                    inferences.extend(rule_inferences)
        
        return inferences
    
    def _find_related_knowledge(self, knowledge_item: KnowledgeItem) -> List[KnowledgeItem]:
        """Find knowledge items related to given item"""
        related = []
        
        # Simple content-based similarity
        item_content = str(knowledge_item.content).lower()
        item_words = set(item_content.split())
        
        for other_id, other_item in self.knowledge_base.items():
            if other_id == knowledge_item.id:
                continue
            
            other_content = str(other_item.content).lower()
            other_words = set(other_content.split())
            
            # Jaccard similarity
            if item_words and other_words:
                intersection = len(item_words & other_words)
                union = len(item_words | other_words)
                similarity = intersection / union
                
                if similarity > 0.2:  # Threshold for relatedness
                    related.append(other_item)
        
        # Sort by confidence and return top matches
        related.sort(key=lambda x: x.confidence, reverse=True)
        return related[:20]
    
    def _apply_deductive_reasoning(self) -> List[Inference]:
        """Apply deductive reasoning rules"""
        inferences = []
        
        # Get recent working memory items
        recent_items = list(self.working_memory)[-20:]
        
        for rule in self.reasoning_rules[ReasoningType.DEDUCTIVE]:
            if rule.can_apply(recent_items):
                rule_inferences = rule.apply(recent_items)
                inferences.extend(rule_inferences)
        
        return inferences
    
    def _apply_inductive_reasoning(self) -> List[Inference]:
        """Apply inductive reasoning rules"""
        inferences = []
        
        # Get facts for generalization
        facts = [item for item in self.knowledge_base.values() 
                if item.knowledge_type == 'fact']
        
        if len(facts) >= 5:  # Need sufficient data for induction
            for rule in self.reasoning_rules[ReasoningType.INDUCTIVE]:
                if rule.can_apply(facts):
                    rule_inferences = rule.apply(facts)
                    inferences.extend(rule_inferences)
        
        return inferences
    
    def _apply_abductive_reasoning(self) -> List[Inference]:
        """Apply abductive reasoning rules"""
        inferences = []
        
        # Get observations and potential explanations
        all_items = list(self.knowledge_base.values())
        
        for rule in self.reasoning_rules[ReasoningType.ABDUCTIVE]:
            if rule.can_apply(all_items):
                rule_inferences = rule.apply(all_items)
                inferences.extend(rule_inferences)
        
        return inferences
    
    def _apply_analogical_reasoning(self) -> List[Inference]:
        """Apply analogical reasoning"""
        inferences = []
        
        # Find analogous situations/patterns
        knowledge_items = list(self.knowledge_base.values())
        
        for i, item1 in enumerate(knowledge_items):
            for item2 in knowledge_items[i+1:]:
                analogy_strength = self._compute_analogy_strength(item1, item2)
                
                if analogy_strength > 0.6:  # Strong analogy
                    # Generate analogical inference
                    inference = self._create_analogical_inference(item1, item2, analogy_strength)
                    if inference:
                        inferences.append(inference)
        
        return inferences
    
    def _compute_analogy_strength(self, item1: KnowledgeItem, item2: KnowledgeItem) -> float:
        """Compute strength of analogy between two knowledge items"""
        content1 = str(item1.content).lower()
        content2 = str(item2.content).lower()
        
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Structural similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        structural_sim = intersection / union
        
        # Type similarity
        type_sim = 1.0 if item1.knowledge_type == item2.knowledge_type else 0.5
        
        # Confidence similarity
        conf_diff = abs(item1.confidence - item2.confidence)
        conf_sim = 1.0 - conf_diff
        
        return 0.6 * structural_sim + 0.2 * type_sim + 0.2 * conf_sim
    
    def _create_analogical_inference(self, item1: KnowledgeItem, item2: KnowledgeItem, 
                                   strength: float) -> Optional[Inference]:
        """Create analogical inference from two similar items"""
        # Simple analogical transfer
        conclusion = f"By analogy between '{item1.content}' and '{item2.content}', " \
                    f"similar properties may apply"
        
        inference = Inference(
            id=f"analogical_{int(time.time() * 1000)}",
            premises=[item1.id, item2.id],
            conclusion=conclusion,
            inference_type=ReasoningType.ANALOGICAL,
            confidence=strength * min(item1.confidence, item2.confidence),
            rule_applied="analogical_transfer"
        )
        
        return inference
    
    def _validate_inferences(self, inferences: List[Inference]) -> List[Inference]:
        """Validate and filter inferences"""
        valid_inferences = []
        
        for inference in inferences:
            # Check confidence threshold
            if inference.confidence < self.confidence_threshold:
                continue
            
            # Check for duplicates
            is_duplicate = False
            for existing_inference in self.inferences.values():
                if self._inferences_similar(inference, existing_inference):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                valid_inferences.append(inference)
        
        return valid_inferences
    
    def _inferences_similar(self, inf1: Inference, inf2: Inference) -> bool:
        """Check if two inferences are similar"""
        # Compare conclusions
        conclusion1 = inf1.conclusion.lower()
        conclusion2 = inf2.conclusion.lower()
        
        words1 = set(conclusion1.split())
        words2 = set(conclusion2.split())
        
        if words1 and words2:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            similarity = intersection / union
            return similarity > 0.8
        
        return False
    
    def generate_hypothesis(self, observations: List[str], reasoning_type: ReasoningType = ReasoningType.ABDUCTIVE) -> Hypothesis:
        """Generate hypothesis from observations"""
        hypothesis_id = f"hypothesis_{int(time.time() * 1000)}"
        
        # Simple hypothesis generation based on observations
        if reasoning_type == ReasoningType.ABDUCTIVE:
            content = f"Hypothesis to explain: {'; '.join(observations)}"
        elif reasoning_type == ReasoningType.INDUCTIVE:
            content = f"Generalization from: {'; '.join(observations)}"
        else:
            content = f"Hypothesis based on: {'; '.join(observations)}"
        
        hypothesis = Hypothesis(
            id=hypothesis_id,
            content=content,
            reasoning_type=reasoning_type,
            confidence=0.6,  # Initial confidence
            evidence=observations
        )
        
        self.hypotheses[hypothesis_id] = hypothesis
        self.reasoning_stats['hypotheses_generated'] += 1
        
        # Add to agenda for testing
        self.reasoning_agenda.append({
            'type': 'hypothesis_test',
            'hypothesis_id': hypothesis_id,
            'priority': 0.8
        })
        
        return hypothesis
    
    def _test_hypothesis(self, hypothesis: Hypothesis) -> List[Inference]:
        """Test hypothesis against available evidence"""
        inferences = []
        
        # Find relevant evidence
        relevant_evidence = self._find_relevant_evidence(hypothesis)
        
        supporting_evidence = 0
        conflicting_evidence = 0
        
        for evidence in relevant_evidence:
            # Simple evidence evaluation
            evidence_content = str(evidence.content).lower()
            hypothesis_content = hypothesis.content.lower()
            
            # Count overlapping terms
            evidence_words = set(evidence_content.split())
            hypothesis_words = set(hypothesis_content.split())
            overlap = len(evidence_words & hypothesis_words)
            
            if overlap > 2:  # Significant overlap
                if evidence.confidence > 0.7:
                    supporting_evidence += 1
                else:
                    conflicting_evidence += 1
        
        # Update hypothesis confidence
        total_evidence = supporting_evidence + conflicting_evidence
        if total_evidence > 0:
            new_confidence = supporting_evidence / total_evidence
            hypothesis.confidence = 0.7 * hypothesis.confidence + 0.3 * new_confidence
            hypothesis.support_count = supporting_evidence
            hypothesis.refutation_count = conflicting_evidence
            hypothesis.last_updated = time.time()
            
            # Generate inference about hypothesis status
            if hypothesis.confidence > 0.8:
                conclusion = f"Hypothesis '{hypothesis.content}' is well-supported"
                self.reasoning_stats['hypotheses_confirmed'] += 1
            elif hypothesis.confidence < 0.3:
                conclusion = f"Hypothesis '{hypothesis.content}' is poorly supported"
                self.reasoning_stats['hypotheses_refuted'] += 1
            else:
                conclusion = f"Hypothesis '{hypothesis.content}' has moderate support"
            
            inference = Inference(
                id=f"hypothesis_test_{int(time.time() * 1000)}",
                premises=[hypothesis.id],
                conclusion=conclusion,
                inference_type=hypothesis.reasoning_type,
                confidence=hypothesis.confidence,
                rule_applied="hypothesis_testing"
            )
            inferences.append(inference)
        
        return inferences
    
    def _find_relevant_evidence(self, hypothesis: Hypothesis) -> List[KnowledgeItem]:
        """Find evidence relevant to hypothesis"""
        relevant = []
        
        hypothesis_content = hypothesis.content.lower()
        hypothesis_words = set(hypothesis_content.split())
        
        for knowledge_item in self.knowledge_base.values():
            item_content = str(knowledge_item.content).lower()
            item_words = set(item_content.split())
            
            # Check relevance
            if hypothesis_words and item_words:
                intersection = len(hypothesis_words & item_words)
                union = len(hypothesis_words | item_words)
                relevance = intersection / union
                
                if relevance > 0.1:  # Some relevance
                    relevant.append(knowledge_item)
        
        return relevant
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state of reasoning engine"""
        return {
            'activation_level': self.activation_level,
            'knowledge_base_size': len(self.knowledge_base),
            'num_hypotheses': len(self.hypotheses),
            'num_inferences': len(self.inferences),
            'working_memory_size': len(self.working_memory),
            'reasoning_agenda_size': len(self.reasoning_agenda),
            'reasoning_stats': self.reasoning_stats.copy(),
            'last_reasoning_time': self._last_reasoning_time,
            'confidence_distribution': self._get_confidence_distribution()
        }
    
    def _get_confidence_distribution(self) -> Dict[str, int]:
        """Get distribution of confidence levels in knowledge base"""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for item in self.knowledge_base.values():
            if item.confidence > 0.7:
                distribution['high'] += 1
            elif item.confidence > 0.4:
                distribution['medium'] += 1
            else:
                distribution['low'] += 1
        
        return distribution
    
    def receive_pattern_feedback(self, patterns: List[Any]):
        """Receive patterns from pattern mining engine"""
        for pattern in patterns:
            # Convert patterns to knowledge
            self.add_knowledge(
                content=f"Pattern: {pattern}",
                knowledge_type='pattern',
                confidence=getattr(pattern, 'confidence', 0.7),
                source='pattern_mining'
            )
        
        # Update activation based on pattern input
        self.activation_level = min(1.0, self.activation_level + 0.2)
    
    def send_reasoning_to_patterns(self, pattern_engine) -> Dict[str, Any]:
        """Send reasoning results to pattern mining engine"""
        # Send high-confidence inferences and hypotheses
        high_confidence_inferences = [
            inf for inf in self.inferences.values()
            if inf.confidence > 0.8
        ]
        
        confirmed_hypotheses = [
            hyp for hyp in self.hypotheses.values()
            if hyp.confidence > 0.8
        ]
        
        return {
            'inferences': high_confidence_inferences[-20:],  # Recent high-confidence inferences
            'hypotheses': confirmed_hypotheses[-10:],  # Recent confirmed hypotheses
            'reasoning_confidence': self.activation_level,
            'boost_types': ['causal', 'temporal'],  # Request specific pattern types
            'timestamp': time.time()
        }
    
    def query_knowledge(self, query: str) -> List[KnowledgeItem]:
        """Query knowledge base"""
        query_words = set(query.lower().split())
        relevant_items = []
        
        for item in self.knowledge_base.values():
            item_content = str(item.content).lower()
            item_words = set(item_content.split())
            
            if query_words and item_words:
                intersection = len(query_words & item_words)
                if intersection > 0:
                    relevance = intersection / len(query_words)
                    relevant_items.append((item, relevance))
        
        # Sort by relevance and confidence
        relevant_items.sort(key=lambda x: (x[1], x[0].confidence), reverse=True)
        return [item[0] for item in relevant_items[:10]]