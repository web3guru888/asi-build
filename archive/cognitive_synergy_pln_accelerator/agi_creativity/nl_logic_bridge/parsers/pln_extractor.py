"""
Automatic PLN (Probabilistic Logic Networks) rule extraction from natural language text.

This module implements sophisticated algorithms to extract PLN rules from natural
language, supporting Ben Goertzel's vision of automated knowledge acquisition.
"""

import re
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import spacy
import nltk
from nltk.corpus import wordnet
from transformers import pipeline, AutoTokenizer, AutoModel
import torch
import numpy as np


class PLNRuleType(Enum):
    """Types of PLN rules that can be extracted."""
    INHERITANCE = "inheritance"  # A is a type of B
    SIMILARITY = "similarity"    # A is similar to B
    IMPLICATION = "implication"  # If A then B
    EVALUATION = "evaluation"    # A has truth value X
    MEMBER = "member"           # A is member of B
    SUBSET = "subset"           # A is subset of B
    EQUIVALENCE = "equivalence" # A is equivalent to B
    NEGATION = "negation"       # A is not B
    TEMPORAL = "temporal"       # A happens before/after B
    CAUSAL = "causal"          # A causes B


@dataclass
class PLNRule:
    """Represents a PLN rule extracted from natural language."""
    rule_type: PLNRuleType
    premise: List[str]
    conclusion: str
    strength: float  # Strength of the rule (0-1)
    confidence: float  # Confidence in the rule (0-1)
    source_text: str
    context: Dict[str, Any]
    variables: List[str] = None
    logical_form: str = None
    
    def to_pln_format(self) -> str:
        """Convert to standard PLN format."""
        if self.rule_type == PLNRuleType.INHERITANCE:
            return f"InheritanceLink <{self.strength}, {self.confidence}>\n  {self.premise[0]}\n  {self.conclusion}"
        elif self.rule_type == PLNRuleType.IMPLICATION:
            premise_str = " AND ".join(self.premise) if len(self.premise) > 1 else self.premise[0]
            return f"ImplicationLink <{self.strength}, {self.confidence}>\n  {premise_str}\n  {self.conclusion}"
        elif self.rule_type == PLNRuleType.SIMILARITY:
            return f"SimilarityLink <{self.strength}, {self.confidence}>\n  {self.premise[0]}\n  {self.conclusion}"
        elif self.rule_type == PLNRuleType.EVALUATION:
            return f"EvaluationLink <{self.strength}, {self.confidence}>\n  {self.premise[0]}\n  {self.conclusion}"
        else:
            return f"{self.rule_type.value.title()}Link <{self.strength}, {self.confidence}>\n  {' '.join(self.premise)}\n  {self.conclusion}"


class PLNExtractor:
    """
    Automatic PLN rule extraction from natural language text.
    
    This class uses advanced NLP techniques including transformers, dependency parsing,
    and semantic role labeling to extract PLN rules from natural language.
    """
    
    def __init__(self):
        """Initialize the PLN extractor."""
        self.logger = logging.getLogger(__name__)
        
        # Load language models
        self._load_models()
        
        # Initialize pattern matchers
        self._init_patterns()
        
        # Rule extraction statistics
        self.extraction_stats = {
            "total_rules_extracted": 0,
            "rules_by_type": {},
            "average_confidence": 0.0
        }
    
    def _load_models(self):
        """Load required NLP models."""
        try:
            # Load spaCy model for dependency parsing
            self.nlp = spacy.load("en_core_web_sm")
            
            # Load transformer for semantic understanding
            self.semantic_model = pipeline(
                "feature-extraction",
                model="sentence-transformers/all-MiniLM-L6-v2",
                return_tensors="pt"
            )
            
            # Load question-answering model for relation extraction
            self.qa_model = pipeline(
                "question-answering",
                model="distilbert-base-cased-distilled-squad"
            )
            
            # Load text classification model for rule type detection
            self.classifier = pipeline(
                "text-classification",
                model="microsoft/DialoGPT-medium"
            )
            
            self.logger.info("Successfully loaded NLP models for PLN extraction")
            
        except Exception as e:
            self.logger.error(f"Error loading models: {str(e)}")
            # Fallback to basic processing
            self.nlp = None
            self.semantic_model = None
            self.qa_model = None
            self.classifier = None
    
    def _init_patterns(self):
        """Initialize regex patterns for rule extraction."""
        self.patterns = {
            PLNRuleType.INHERITANCE: [
                r"(.+?)\s+(?:is|are)\s+(?:a|an)\s+(?:type of|kind of)?\s*(.+)",
                r"(.+?)\s+(?:is|are)\s+(.+)",
                r"(.+?)\s+(?:belongs to|part of)\s+(.+)",
                r"All\s+(.+?)\s+(?:is|are)\s+(.+)",
            ],
            PLNRuleType.IMPLICATION: [
                r"(?:If|When)\s+(.+?),?\s+then\s+(.+)",
                r"(.+?)\s+(?:implies|means|leads to|results in|causes)\s+(.+)",
                r"(.+?)\s+→\s+(.+)",
                r"Given\s+(.+?),\s+(.+)",
            ],
            PLNRuleType.SIMILARITY: [
                r"(.+?)\s+(?:is similar to|resembles|is like)\s+(.+)",
                r"(.+?)\s+and\s+(.+?)\s+(?:are similar|share similarities)",
                r"(.+?)\s+≈\s+(.+)",
            ],
            PLNRuleType.CAUSAL: [
                r"(.+?)\s+(?:causes|leads to|results in|triggers)\s+(.+)",
                r"(.+?)\s+(?:is caused by|results from)\s+(.+)",
                r"Due to\s+(.+?),\s+(.+)",
                r"Because of\s+(.+?),\s+(.+)",
            ],
            PLNRuleType.TEMPORAL: [
                r"(.+?)\s+(?:happens|occurs|takes place)\s+(?:before|after|during)\s+(.+)",
                r"(?:Before|After)\s+(.+?),\s+(.+)",
                r"(.+?)\s+(?:precedes|follows)\s+(.+)",
            ],
            PLNRuleType.NEGATION: [
                r"(.+?)\s+(?:is not|are not|isn't|aren't)\s+(.+)",
                r"(.+?)\s+(?:does not|doesn't|cannot|can't)\s+(.+)",
                r"It is not the case that\s+(.+)",
            ],
            PLNRuleType.EQUIVALENCE: [
                r"(.+?)\s+(?:is equivalent to|equals|is the same as)\s+(.+)",
                r"(.+?)\s+(?:≡|=)\s+(.+)",
                r"(.+?)\s+and\s+(.+?)\s+are equivalent",
            ]
        }
    
    async def extract_rules(
        self,
        text: str,
        semantic_parse: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[PLNRule]:
        """
        Extract PLN rules from natural language text.
        
        Args:
            text: Input natural language text
            semantic_parse: Pre-computed semantic parse
            context: Additional context information
            
        Returns:
            List of extracted PLN rules
        """
        try:
            rules = []
            
            # Preprocess text
            preprocessed_text = self._preprocess_text(text)
            
            # Extract rules using multiple methods
            pattern_rules = await self._extract_pattern_based_rules(preprocessed_text)
            dependency_rules = await self._extract_dependency_based_rules(preprocessed_text)
            semantic_rules = await self._extract_semantic_rules(preprocessed_text, semantic_parse)
            transformer_rules = await self._extract_transformer_rules(preprocessed_text)
            
            # Combine all extracted rules
            all_rules = pattern_rules + dependency_rules + semantic_rules + transformer_rules
            
            # Post-process and filter rules
            filtered_rules = await self._post_process_rules(all_rules, context)
            
            # Update statistics
            self._update_stats(filtered_rules)
            
            self.logger.info(f"Extracted {len(filtered_rules)} PLN rules from text")
            return filtered_rules
            
        except Exception as e:
            self.logger.error(f"Error extracting PLN rules: {str(e)}")
            return []
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for rule extraction."""
        # Basic cleaning
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Sentence segmentation
        sentences = nltk.sent_tokenize(text) if nltk else [text]
        
        return " ".join(sentences)
    
    async def _extract_pattern_based_rules(self, text: str) -> List[PLNRule]:
        """Extract rules using regex patterns."""
        rules = []
        
        for rule_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        premise = [groups[0].strip()]
                        conclusion = groups[1].strip()
                        
                        # Calculate confidence based on pattern specificity
                        confidence = self._calculate_pattern_confidence(pattern, match)
                        strength = self._estimate_rule_strength(premise, conclusion, text)
                        
                        rule = PLNRule(
                            rule_type=rule_type,
                            premise=premise,
                            conclusion=conclusion,
                            strength=strength,
                            confidence=confidence,
                            source_text=match.group(0),
                            context={"extraction_method": "pattern_based"}
                        )
                        
                        rules.append(rule)
        
        return rules
    
    async def _extract_dependency_based_rules(self, text: str) -> List[PLNRule]:
        """Extract rules using dependency parsing."""
        if not self.nlp:
            return []
        
        rules = []
        doc = self.nlp(text)
        
        for sent in doc.sents:
            # Find subject-predicate-object relationships
            subjects = []
            predicates = []
            objects = []
            
            for token in sent:
                if token.dep_ in ["nsubj", "nsubjpass"]:
                    subjects.append(token)
                elif token.dep_ == "ROOT" and token.pos_ == "VERB":
                    predicates.append(token)
                elif token.dep_ in ["dobj", "pobj", "attr"]:
                    objects.append(token)
            
            # Create rules from SVO patterns
            for subj in subjects:
                for pred in predicates:
                    for obj in objects:
                        if self._is_valid_svo_relation(subj, pred, obj):
                            rule = self._create_dependency_rule(subj, pred, obj, sent)
                            if rule:
                                rules.append(rule)
            
            # Extract copula relationships (X is Y)
            copula_rules = self._extract_copula_rules(sent)
            rules.extend(copula_rules)
            
            # Extract causal relationships
            causal_rules = self._extract_causal_relations(sent)
            rules.extend(causal_rules)
        
        return rules
    
    async def _extract_semantic_rules(
        self,
        text: str,
        semantic_parse: Optional[Dict[str, Any]]
    ) -> List[PLNRule]:
        """Extract rules using semantic role labeling."""
        rules = []
        
        if semantic_parse and "semantic_roles" in semantic_parse:
            roles = semantic_parse["semantic_roles"]
            
            for role_frame in roles:
                # Extract agent-action-patient relationships
                if all(key in role_frame for key in ["agent", "action", "patient"]):
                    rule = PLNRule(
                        rule_type=PLNRuleType.IMPLICATION,
                        premise=[f"{role_frame['agent']} {role_frame['action']}"],
                        conclusion=role_frame["patient"],
                        strength=0.7,
                        confidence=0.8,
                        source_text=role_frame.get("text", ""),
                        context={"extraction_method": "semantic_roles"}
                    )
                    rules.append(rule)
        
        return rules
    
    async def _extract_transformer_rules(self, text: str) -> List[PLNRule]:
        """Extract rules using transformer models."""
        if not self.qa_model:
            return []
        
        rules = []
        
        # Define questions to extract different types of relationships
        questions = [
            ("What is a type of what?", PLNRuleType.INHERITANCE),
            ("What causes what?", PLNRuleType.CAUSAL),
            ("What is similar to what?", PLNRuleType.SIMILARITY),
            ("What implies what?", PLNRuleType.IMPLICATION),
            ("What happens before what?", PLNRuleType.TEMPORAL),
        ]
        
        for question, rule_type in questions:
            try:
                result = self.qa_model(question=question, context=text)
                
                if result["score"] > 0.5:  # Confidence threshold
                    answer = result["answer"]
                    
                    # Parse the answer to extract premise and conclusion
                    premise, conclusion = self._parse_qa_answer(answer, rule_type)
                    
                    if premise and conclusion:
                        rule = PLNRule(
                            rule_type=rule_type,
                            premise=[premise],
                            conclusion=conclusion,
                            strength=result["score"],
                            confidence=result["score"],
                            source_text=answer,
                            context={"extraction_method": "transformer_qa"}
                        )
                        rules.append(rule)
                        
            except Exception as e:
                self.logger.warning(f"Error in transformer extraction: {str(e)}")
                continue
        
        return rules
    
    def _is_valid_svo_relation(self, subj, pred, obj) -> bool:
        """Check if subject-verb-object relation is valid for rule extraction."""
        # Filter out auxiliary verbs, pronouns, etc.
        if pred.lemma_ in ["be", "have", "do"]:
            return False
        
        if subj.text.lower() in ["it", "this", "that", "they"]:
            return False
        
        return True
    
    def _create_dependency_rule(self, subj, pred, obj, sent) -> Optional[PLNRule]:
        """Create a PLN rule from dependency parse elements."""
        try:
            # Determine rule type based on predicate
            if pred.lemma_ in ["cause", "lead", "result", "trigger"]:
                rule_type = PLNRuleType.CAUSAL
            elif pred.lemma_ in ["resemble", "like"]:
                rule_type = PLNRuleType.SIMILARITY
            elif pred.lemma_ == "be" and obj.dep_ == "attr":
                rule_type = PLNRuleType.INHERITANCE
            else:
                rule_type = PLNRuleType.IMPLICATION
            
            premise = [f"{subj.text} {pred.text}"]
            conclusion = obj.text
            
            # Calculate strength and confidence
            strength = 0.7  # Default strength
            confidence = 0.6  # Conservative confidence for dependency-based rules
            
            return PLNRule(
                rule_type=rule_type,
                premise=premise,
                conclusion=conclusion,
                strength=strength,
                confidence=confidence,
                source_text=sent.text,
                context={"extraction_method": "dependency_parsing"}
            )
            
        except Exception as e:
            self.logger.warning(f"Error creating dependency rule: {str(e)}")
            return None
    
    def _extract_copula_rules(self, sent) -> List[PLNRule]:
        """Extract inheritance rules from copula constructions (X is Y)."""
        rules = []
        
        for token in sent:
            if token.lemma_ == "be" and token.dep_ == "ROOT":
                # Find subject and predicate nominative
                subj = None
                pred_nom = None
                
                for child in token.children:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        subj = child
                    elif child.dep_ in ["attr", "acomp"]:
                        pred_nom = child
                
                if subj and pred_nom:
                    rule = PLNRule(
                        rule_type=PLNRuleType.INHERITANCE,
                        premise=[subj.text],
                        conclusion=pred_nom.text,
                        strength=0.8,
                        confidence=0.7,
                        source_text=sent.text,
                        context={"extraction_method": "copula_extraction"}
                    )
                    rules.append(rule)
        
        return rules
    
    def _extract_causal_relations(self, sent) -> List[PLNRule]:
        """Extract causal relationships from dependency parse."""
        rules = []
        
        # Look for causal markers
        causal_markers = ["because", "since", "due", "cause", "result", "lead"]
        
        for token in sent:
            if token.text.lower() in causal_markers:
                # Extract cause and effect
                cause_tokens = []
                effect_tokens = []
                
                # Simple heuristic: tokens before marker are effect, after are cause
                marker_idx = token.i
                
                for t in sent:
                    if t.i < marker_idx and t.dep_ not in ["det", "prep"]:
                        effect_tokens.append(t.text)
                    elif t.i > marker_idx and t.dep_ not in ["det", "prep"]:
                        cause_tokens.append(t.text)
                
                if cause_tokens and effect_tokens:
                    rule = PLNRule(
                        rule_type=PLNRuleType.CAUSAL,
                        premise=[" ".join(cause_tokens)],
                        conclusion=" ".join(effect_tokens),
                        strength=0.6,
                        confidence=0.5,
                        source_text=sent.text,
                        context={"extraction_method": "causal_marker"}
                    )
                    rules.append(rule)
        
        return rules
    
    def _parse_qa_answer(self, answer: str, rule_type: PLNRuleType) -> Tuple[str, str]:
        """Parse QA model answer to extract premise and conclusion."""
        # Simple parsing - could be enhanced
        if " and " in answer:
            parts = answer.split(" and ", 1)
            return parts[0].strip(), parts[1].strip()
        elif " to " in answer and rule_type == PLNRuleType.CAUSAL:
            parts = answer.split(" to ", 1)
            return parts[0].strip(), parts[1].strip()
        else:
            # Single entity - create simple rule
            return answer.strip(), "true"
    
    def _calculate_pattern_confidence(self, pattern: str, match) -> float:
        """Calculate confidence based on pattern specificity."""
        # More specific patterns get higher confidence
        if "if" in pattern.lower() or "when" in pattern.lower():
            return 0.8
        elif "is a" in pattern.lower() or "type of" in pattern.lower():
            return 0.9
        elif "causes" in pattern.lower() or "leads to" in pattern.lower():
            return 0.7
        else:
            return 0.6
    
    def _estimate_rule_strength(self, premise: List[str], conclusion: str, context: str) -> float:
        """Estimate the strength of a rule based on linguistic cues."""
        strength = 0.5  # Default strength
        
        # Look for strength indicators
        strength_indicators = {
            "always": 0.9,
            "usually": 0.8,
            "often": 0.7,
            "sometimes": 0.5,
            "rarely": 0.3,
            "never": 0.1,
            "definitely": 0.9,
            "probably": 0.7,
            "possibly": 0.5,
            "likely": 0.7,
            "unlikely": 0.3
        }
        
        text = " ".join(premise + [conclusion]).lower()
        
        for indicator, value in strength_indicators.items():
            if indicator in text:
                strength = value
                break
        
        return strength
    
    async def _post_process_rules(
        self,
        rules: List[PLNRule],
        context: Optional[Dict[str, Any]]
    ) -> List[PLNRule]:
        """Post-process and filter extracted rules."""
        filtered_rules = []
        
        for rule in rules:
            # Filter out low-confidence rules
            if rule.confidence < 0.3:
                continue
            
            # Filter out trivial rules
            if self._is_trivial_rule(rule):
                continue
            
            # Normalize rule text
            rule = self._normalize_rule(rule)
            
            # Add logical form
            rule.logical_form = self._generate_logical_form(rule)
            
            filtered_rules.append(rule)
        
        # Remove duplicates
        filtered_rules = self._remove_duplicate_rules(filtered_rules)
        
        # Sort by confidence
        filtered_rules.sort(key=lambda x: x.confidence, reverse=True)
        
        return filtered_rules
    
    def _is_trivial_rule(self, rule: PLNRule) -> bool:
        """Check if a rule is trivial and should be filtered out."""
        premise_text = " ".join(rule.premise).lower()
        conclusion_text = rule.conclusion.lower()
        
        # Filter out tautologies
        if premise_text == conclusion_text:
            return True
        
        # Filter out very short rules
        if len(premise_text) < 3 or len(conclusion_text) < 3:
            return True
        
        # Filter out rules with stop words only
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being"}
        premise_words = set(premise_text.split())
        conclusion_words = set(conclusion_text.split())
        
        if premise_words.issubset(stop_words) or conclusion_words.issubset(stop_words):
            return True
        
        return False
    
    def _normalize_rule(self, rule: PLNRule) -> PLNRule:
        """Normalize rule text for consistency."""
        # Lowercase and strip
        rule.premise = [p.strip().lower() for p in rule.premise]
        rule.conclusion = rule.conclusion.strip().lower()
        
        # Remove articles and common words
        def clean_text(text):
            words = text.split()
            cleaned_words = []
            for word in words:
                if word not in ["the", "a", "an"]:
                    cleaned_words.append(word)
            return " ".join(cleaned_words)
        
        rule.premise = [clean_text(p) for p in rule.premise]
        rule.conclusion = clean_text(rule.conclusion)
        
        return rule
    
    def _generate_logical_form(self, rule: PLNRule) -> str:
        """Generate logical form representation of the rule."""
        if rule.rule_type == PLNRuleType.INHERITANCE:
            return f"∀x (P(x) → Q(x))"  # All P are Q
        elif rule.rule_type == PLNRuleType.IMPLICATION:
            return f"P → Q"
        elif rule.rule_type == PLNRuleType.SIMILARITY:
            return f"P ≈ Q"
        elif rule.rule_type == PLNRuleType.CAUSAL:
            return f"P ⟹ Q"  # P causes Q
        elif rule.rule_type == PLNRuleType.EQUIVALENCE:
            return f"P ↔ Q"
        elif rule.rule_type == PLNRuleType.NEGATION:
            return f"¬P"
        else:
            return f"R(P, Q)"  # Generic relation
    
    def _remove_duplicate_rules(self, rules: List[PLNRule]) -> List[PLNRule]:
        """Remove duplicate rules based on premise and conclusion similarity."""
        unique_rules = []
        seen_rules = set()
        
        for rule in rules:
            # Create a signature for the rule
            signature = (
                rule.rule_type,
                tuple(rule.premise),
                rule.conclusion
            )
            
            if signature not in seen_rules:
                seen_rules.add(signature)
                unique_rules.append(rule)
        
        return unique_rules
    
    def _update_stats(self, rules: List[PLNRule]):
        """Update extraction statistics."""
        self.extraction_stats["total_rules_extracted"] += len(rules)
        
        for rule in rules:
            rule_type = rule.rule_type.value
            self.extraction_stats["rules_by_type"][rule_type] = \
                self.extraction_stats["rules_by_type"].get(rule_type, 0) + 1
        
        if rules:
            avg_confidence = sum(rule.confidence for rule in rules) / len(rules)
            total_rules = self.extraction_stats["total_rules_extracted"]
            current_avg = self.extraction_stats["average_confidence"]
            
            # Update running average
            self.extraction_stats["average_confidence"] = \
                (current_avg * (total_rules - len(rules)) + avg_confidence * len(rules)) / total_rules
    
    async def extract_rules_from_corpus(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[PLNRule]:
        """Extract PLN rules from a corpus of texts."""
        all_rules = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [self.extract_rules(text) for text in batch]
            batch_results = await asyncio.gather(*tasks)
            
            # Flatten results
            for rules in batch_results:
                all_rules.extend(rules)
        
        # Post-process entire corpus
        final_rules = await self._post_process_rules(all_rules, None)
        
        self.logger.info(f"Extracted {len(final_rules)} rules from corpus of {len(texts)} texts")
        return final_rules
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get current extraction statistics."""
        return self.extraction_stats.copy()
    
    def export_rules_to_atomspace(self, rules: List[PLNRule]) -> str:
        """Export rules to OpenCog AtomSpace format."""
        atomspace_format = []
        
        for rule in rules:
            pln_format = rule.to_pln_format()
            atomspace_format.append(pln_format)
        
        return "\n\n".join(atomspace_format)
    
    def export_rules_to_json(self, rules: List[PLNRule]) -> str:
        """Export rules to JSON format."""
        json_rules = []
        
        for rule in rules:
            json_rule = {
                "rule_type": rule.rule_type.value,
                "premise": rule.premise,
                "conclusion": rule.conclusion,
                "strength": rule.strength,
                "confidence": rule.confidence,
                "source_text": rule.source_text,
                "logical_form": rule.logical_form,
                "context": rule.context
            }
            json_rules.append(json_rule)
        
        return json.dumps(json_rules, indent=2)