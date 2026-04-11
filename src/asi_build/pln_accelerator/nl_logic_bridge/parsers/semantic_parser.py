"""
Advanced semantic parser with compositional semantics.

This module implements sophisticated semantic parsing that converts natural language
into structured semantic representations, supporting compositional semantics and
multiple parsing strategies.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import nltk
import numpy as np
import spacy
import torch
from nltk.parse import CoreNLPParser
from nltk.tree import Tree
from transformers import AutoModel, AutoTokenizer, pipeline


class SemanticRole(Enum):
    """Semantic roles for arguments."""

    AGENT = "agent"  # Who/what performs the action
    PATIENT = "patient"  # Who/what receives the action
    THEME = "theme"  # What the action is about
    EXPERIENCER = "experiencer"  # Who experiences something
    INSTRUMENT = "instrument"  # Tool or means
    LOCATION = "location"  # Where something happens
    TIME = "time"  # When something happens
    MANNER = "manner"  # How something is done
    PURPOSE = "purpose"  # Why something is done
    CAUSE = "cause"  # What causes something
    RESULT = "result"  # What results from something


@dataclass
class SemanticFrame:
    """Represents a semantic frame with predicate and arguments."""

    predicate: str
    arguments: Dict[SemanticRole, List[str]]
    frame_type: str
    confidence: float
    source_span: Tuple[int, int]
    modifiers: List[str] = None
    temporal_info: Dict[str, Any] = None
    modal_info: Dict[str, Any] = None


@dataclass
class CompositionRule:
    """Rule for compositional semantics."""

    rule_type: str
    pattern: str
    composition_function: str
    priority: int


@dataclass
class SemanticParse:
    """Complete semantic parse of a sentence."""

    text: str
    frames: List[SemanticFrame]
    entities: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]
    logical_form: str
    compositional_structure: Dict[str, Any]
    confidence: float
    ambiguities: List[str]
    parse_tree: Optional[Any] = None
    dependency_graph: Optional[Any] = None


class SemanticParser:
    """
    Advanced semantic parser with compositional semantics.

    This parser combines multiple approaches including dependency parsing,
    semantic role labeling, and neural semantic parsing to produce rich
    semantic representations.
    """

    def __init__(self):
        """Initialize the semantic parser."""
        self.logger = logging.getLogger(__name__)

        # Load NLP models
        self._load_models()

        # Initialize composition rules
        self._init_composition_rules()

        # Initialize frame knowledge
        self._init_frame_knowledge()

        # Statistics
        self.stats = {"sentences_parsed": 0, "frames_extracted": 0, "average_confidence": 0.0}

    def _load_models(self):
        """Load required NLP models."""
        try:
            # Load spaCy for basic NLP
            self.nlp = spacy.load("en_core_web_sm")

            # Load semantic role labeling model
            self.srl_model = pipeline("question-answering", model="deepset/roberta-base-squad2")

            # Load transformer for semantic similarity
            self.semantic_model = pipeline(
                "feature-extraction", model="sentence-transformers/all-MiniLM-L6-v2"
            )

            # Load coreference resolution (simplified)
            self.coref_model = None  # Would use neuralcoref if available

            self.logger.info("Successfully loaded semantic parsing models")

        except Exception as e:
            self.logger.error(f"Error loading models: {str(e)}")
            # Fallback to basic processing
            self.nlp = None
            self.srl_model = None
            self.semantic_model = None
            self.coref_model = None

    def _init_composition_rules(self):
        """Initialize compositional semantics rules."""
        self.composition_rules = [
            CompositionRule(
                rule_type="function_application",
                pattern="NP VP",
                composition_function="apply",
                priority=1,
            ),
            CompositionRule(
                rule_type="predicate_modification",
                pattern="VP ADVP",
                composition_function="modify",
                priority=2,
            ),
            CompositionRule(
                rule_type="conjunction",
                pattern="X CONJ X",
                composition_function="conjoin",
                priority=3,
            ),
            CompositionRule(
                rule_type="quantification",
                pattern="DET N",
                composition_function="quantify",
                priority=1,
            ),
            CompositionRule(
                rule_type="lambda_abstraction",
                pattern="WH S",
                composition_function="abstract",
                priority=2,
            ),
        ]

    def _init_frame_knowledge(self):
        """Initialize knowledge about semantic frames."""
        # FrameNet-inspired frame definitions
        self.frame_knowledge = {
            "motion": {
                "core_roles": [SemanticRole.THEME, SemanticRole.LOCATION],
                "optional_roles": [SemanticRole.MANNER, SemanticRole.TIME],
                "triggers": ["move", "go", "come", "travel", "walk", "run"],
            },
            "transfer": {
                "core_roles": [SemanticRole.AGENT, SemanticRole.THEME, SemanticRole.PATIENT],
                "optional_roles": [SemanticRole.LOCATION, SemanticRole.TIME],
                "triggers": ["give", "send", "deliver", "hand", "pass"],
            },
            "communication": {
                "core_roles": [SemanticRole.AGENT, SemanticRole.PATIENT],
                "optional_roles": [SemanticRole.THEME, SemanticRole.MANNER],
                "triggers": ["tell", "say", "speak", "communicate", "inform"],
            },
            "causation": {
                "core_roles": [SemanticRole.CAUSE, SemanticRole.RESULT],
                "optional_roles": [SemanticRole.AGENT, SemanticRole.INSTRUMENT],
                "triggers": ["cause", "make", "force", "lead", "result"],
            },
            "creation": {
                "core_roles": [SemanticRole.AGENT, SemanticRole.RESULT],
                "optional_roles": [SemanticRole.INSTRUMENT, SemanticRole.LOCATION],
                "triggers": ["make", "create", "build", "produce", "generate"],
            },
            "perception": {
                "core_roles": [SemanticRole.EXPERIENCER, SemanticRole.THEME],
                "optional_roles": [SemanticRole.LOCATION, SemanticRole.INSTRUMENT],
                "triggers": ["see", "hear", "feel", "smell", "taste", "perceive"],
            },
        }

    async def parse(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parse text into semantic representation.

        Args:
            text: Input text to parse
            context: Additional context information

        Returns:
            Semantic parse dictionary
        """
        try:
            # Preprocess text
            cleaned_text = self._preprocess_text(text)

            # Parse with spaCy
            doc = self.nlp(cleaned_text) if self.nlp else None

            # Extract semantic frames
            frames = await self._extract_semantic_frames(cleaned_text, doc, context)

            # Extract entities
            entities = self._extract_entities(doc) if doc else []

            # Extract relations
            relations = await self._extract_relations(cleaned_text, doc, context)

            # Build compositional structure
            comp_structure = await self._build_compositional_structure(cleaned_text, doc, frames)

            # Generate logical form
            logical_form = self._generate_logical_form(frames, entities, relations)

            # Detect ambiguities
            ambiguities = self._detect_ambiguities(cleaned_text, doc, frames)

            # Calculate confidence
            confidence = self._calculate_confidence(frames, entities, relations)

            # Create semantic parse
            parse_result = {
                "text": text,
                "cleaned_text": cleaned_text,
                "frames": [self._frame_to_dict(f) for f in frames],
                "entities": entities,
                "relations": relations,
                "logical_form": logical_form,
                "compositional_structure": comp_structure,
                "confidence": confidence,
                "ambiguities": ambiguities,
                "complexity_score": self._calculate_complexity(frames, entities),
                "parse_tree": str(doc) if doc else None,
                "dependency_graph": self._extract_dependencies(doc) if doc else None,
            }

            # Update statistics
            self._update_stats(frames, confidence)

            self.logger.info(f"Parsed text with {len(frames)} semantic frames")
            return parse_result

        except Exception as e:
            self.logger.error(f"Error parsing text: {str(e)}")
            return {"text": text, "error": str(e), "confidence": 0.0}

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for parsing."""
        # Basic cleaning
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        # Handle contractions
        contractions = {
            "don't": "do not",
            "won't": "will not",
            "can't": "cannot",
            "isn't": "is not",
            "aren't": "are not",
            "wasn't": "was not",
            "weren't": "were not",
            "haven't": "have not",
            "hasn't": "has not",
            "hadn't": "had not",
            "wouldn't": "would not",
            "shouldn't": "should not",
            "couldn't": "could not",
            "mustn't": "must not",
        }

        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)

        return text

    async def _extract_semantic_frames(
        self, text: str, doc: Optional[Any], context: Optional[Dict[str, Any]]
    ) -> List[SemanticFrame]:
        """Extract semantic frames from text."""
        frames = []

        if not doc:
            return frames

        # Process each sentence
        for sent in doc.sents:
            # Find main predicate (root verb)
            main_verb = None
            for token in sent:
                if token.dep_ == "ROOT" and token.pos_ == "VERB":
                    main_verb = token
                    break

            if main_verb:
                # Identify frame type
                frame_type = self._identify_frame_type(main_verb.lemma_)

                # Extract arguments using SRL
                arguments = await self._extract_frame_arguments(sent, main_verb)

                # Create semantic frame
                frame = SemanticFrame(
                    predicate=main_verb.lemma_,
                    arguments=arguments,
                    frame_type=frame_type,
                    confidence=0.8,
                    source_span=(sent.start_char, sent.end_char),
                    modifiers=self._extract_modifiers(main_verb),
                    temporal_info=self._extract_temporal_info(sent),
                    modal_info=self._extract_modal_info(sent),
                )

                frames.append(frame)

        return frames

    def _identify_frame_type(self, predicate: str) -> str:
        """Identify the semantic frame type for a predicate."""
        for frame_type, frame_info in self.frame_knowledge.items():
            if predicate.lower() in frame_info["triggers"]:
                return frame_type

        # Default frame type based on general patterns
        if predicate in ["be", "seem", "appear", "become"]:
            return "attribution"
        elif predicate in ["have", "own", "possess"]:
            return "possession"
        elif predicate in ["like", "love", "hate", "enjoy"]:
            return "experiencer_object"
        else:
            return "action"

    async def _extract_frame_arguments(
        self, sent: Any, main_verb: Any
    ) -> Dict[SemanticRole, List[str]]:
        """Extract semantic role arguments for a frame."""
        arguments = {}

        # Map dependency relations to semantic roles
        dep_to_role = {
            "nsubj": SemanticRole.AGENT,
            "nsubjpass": SemanticRole.PATIENT,
            "dobj": SemanticRole.PATIENT,
            "iobj": SemanticRole.PATIENT,
            "prep": SemanticRole.LOCATION,  # Default, will be refined
            "agent": SemanticRole.AGENT,
            "attr": SemanticRole.THEME,
            "acomp": SemanticRole.RESULT,
            "xcomp": SemanticRole.RESULT,
        }

        # Extract direct dependencies
        for child in main_verb.children:
            role = dep_to_role.get(child.dep_, None)

            if role:
                # Extract the full phrase
                phrase = self._extract_phrase(child)

                if role not in arguments:
                    arguments[role] = []
                arguments[role].append(phrase)

            # Handle prepositional phrases
            elif child.dep_ == "prep":
                prep_role = self._map_preposition_to_role(child.text)

                # Find the object of preposition
                for prep_child in child.children:
                    if prep_child.dep_ == "pobj":
                        phrase = self._extract_phrase(prep_child)

                        if prep_role not in arguments:
                            arguments[prep_role] = []
                        arguments[prep_role].append(phrase)

        # Use question-answering for additional role extraction
        if self.srl_model:
            qa_arguments = await self._extract_arguments_with_qa(sent.text, main_verb.text)

            # Merge QA results
            for role, values in qa_arguments.items():
                if role not in arguments:
                    arguments[role] = []
                arguments[role].extend(values)

        return arguments

    def _extract_phrase(self, token: Any) -> str:
        """Extract the full phrase headed by a token."""
        # Get all tokens in the subtree
        phrase_tokens = [tok for tok in token.subtree]

        # Sort by position and join
        phrase_tokens.sort(key=lambda x: x.i)
        phrase = " ".join([tok.text for tok in phrase_tokens])

        return phrase.strip()

    def _map_preposition_to_role(self, preposition: str) -> SemanticRole:
        """Map preposition to semantic role."""
        prep_mappings = {
            "in": SemanticRole.LOCATION,
            "at": SemanticRole.LOCATION,
            "on": SemanticRole.LOCATION,
            "to": SemanticRole.LOCATION,
            "from": SemanticRole.LOCATION,
            "with": SemanticRole.INSTRUMENT,
            "by": SemanticRole.AGENT,
            "for": SemanticRole.PURPOSE,
            "because": SemanticRole.CAUSE,
            "during": SemanticRole.TIME,
            "after": SemanticRole.TIME,
            "before": SemanticRole.TIME,
        }

        return prep_mappings.get(preposition.lower(), SemanticRole.LOCATION)

    async def _extract_arguments_with_qa(
        self, sentence: str, predicate: str
    ) -> Dict[SemanticRole, List[str]]:
        """Extract arguments using question-answering model."""
        if not self.srl_model:
            return {}

        arguments = {}

        # Define questions for each semantic role
        role_questions = {
            SemanticRole.AGENT: "Who or what is performing the action?",
            SemanticRole.PATIENT: "Who or what is being affected?",
            SemanticRole.LOCATION: "Where is this happening?",
            SemanticRole.TIME: "When is this happening?",
            SemanticRole.MANNER: "How is this being done?",
            SemanticRole.PURPOSE: "Why is this being done?",
            SemanticRole.INSTRUMENT: "What tool or means is being used?",
        }

        try:
            for role, question in role_questions.items():
                result = self.srl_model(question=question, context=sentence)

                if result["score"] > 0.5:  # Confidence threshold
                    answer = result["answer"].strip()

                    if answer and answer.lower() != "unknown":
                        if role not in arguments:
                            arguments[role] = []
                        arguments[role].append(answer)

        except Exception as e:
            self.logger.warning(f"Error in QA-based SRL: {str(e)}")

        return arguments

    def _extract_entities(self, doc: Any) -> List[Dict[str, Any]]:
        """Extract named entities and their types."""
        if not doc:
            return []

        entities = []

        for ent in doc.ents:
            entity = {
                "text": ent.text,
                "label": ent.label_,
                "description": spacy.explain(ent.label_),
                "start": ent.start_char,
                "end": ent.end_char,
                "confidence": 0.8,  # spaCy doesn't provide confidence scores
            }
            entities.append(entity)

        return entities

    async def _extract_relations(
        self, text: str, doc: Optional[Any], context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract semantic relations between entities."""
        relations = []

        if not doc:
            return relations

        # Extract entity pairs
        entities = [(ent.text, ent.label_, ent.start, ent.end) for ent in doc.ents]

        # Find relations between entity pairs
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i + 1 :]:
                # Use dependency path to infer relation
                relation = self._infer_relation_from_dependency_path(doc, entity1, entity2)

                if relation:
                    relations.append(relation)

        return relations

    def _infer_relation_from_dependency_path(
        self, doc: Any, entity1: Tuple[str, str, int, int], entity2: Tuple[str, str, int, int]
    ) -> Optional[Dict[str, Any]]:
        """Infer relation between entities using dependency path."""
        # Find tokens corresponding to entities
        ent1_tokens = [token for token in doc if token.idx >= entity1[2] and token.idx < entity1[3]]
        ent2_tokens = [token for token in doc if token.idx >= entity2[2] and token.idx < entity2[3]]

        if not ent1_tokens or not ent2_tokens:
            return None

        # Find shortest dependency path
        path = self._find_dependency_path(ent1_tokens[0], ent2_tokens[0])

        if path and len(path) <= 5:  # Reasonable path length
            # Infer relation type from path
            relation_type = self._classify_relation_from_path(path)

            return {
                "subject": entity1[0],
                "subject_type": entity1[1],
                "object": entity2[0],
                "object_type": entity2[1],
                "relation": relation_type,
                "confidence": 0.6,
                "dependency_path": [token.text for token in path],
            }

        return None

    def _find_dependency_path(self, token1: Any, token2: Any) -> Optional[List[Any]]:
        """Find shortest dependency path between two tokens."""
        # Simple BFS to find path
        visited = set()
        queue = [(token1, [token1])]

        while queue:
            current_token, path = queue.pop(0)

            if current_token == token2:
                return path

            if current_token in visited:
                continue

            visited.add(current_token)

            # Add neighbors (head and children)
            neighbors = [current_token.head] + list(current_token.children)

            for neighbor in neighbors:
                if neighbor not in visited and len(path) < 5:
                    queue.append((neighbor, path + [neighbor]))

        return None

    def _classify_relation_from_path(self, path: List[Any]) -> str:
        """Classify relation type from dependency path."""
        path_pos = [token.pos_ for token in path]
        path_deps = [token.dep_ for token in path]

        # Simple heuristics for relation classification
        if "VERB" in path_pos:
            if "nsubj" in path_deps and "dobj" in path_deps:
                return "acts_on"
            elif "prep" in path_deps:
                return "located_at"
            else:
                return "related_to"
        elif "ADP" in path_pos:  # Preposition
            return "spatial_relation"
        else:
            return "associated_with"

    def _extract_modifiers(self, verb: Any) -> List[str]:
        """Extract adverbial and other modifiers of a verb."""
        modifiers = []

        for child in verb.children:
            if child.dep_ in ["advmod", "amod", "prep"]:
                modifier_phrase = self._extract_phrase(child)
                modifiers.append(modifier_phrase)

        return modifiers

    def _extract_temporal_info(self, sent: Any) -> Dict[str, Any]:
        """Extract temporal information from sentence."""
        temporal_info = {}

        # Look for temporal expressions
        temporal_markers = ["when", "while", "before", "after", "during", "since", "until"]

        for token in sent:
            if token.text.lower() in temporal_markers:
                # Extract temporal phrase
                temporal_phrase = self._extract_phrase(token)
                temporal_info["temporal_marker"] = token.text.lower()
                temporal_info["temporal_expression"] = temporal_phrase
                break

        # Look for tense information
        tense_info = self._analyze_tense(sent)
        temporal_info.update(tense_info)

        return temporal_info

    def _analyze_tense(self, sent: Any) -> Dict[str, str]:
        """Analyze tense and aspect information."""
        tense_info = {}

        # Find auxiliary verbs and main verbs
        aux_verbs = []
        main_verbs = []

        for token in sent:
            if token.pos_ == "AUX":
                aux_verbs.append(token.text.lower())
            elif token.pos_ == "VERB" and token.dep_ == "ROOT":
                main_verbs.append(token)

        # Simple tense analysis
        if any(aux in aux_verbs for aux in ["will", "shall"]):
            tense_info["tense"] = "future"
        elif any(aux in aux_verbs for aux in ["have", "has", "had"]):
            tense_info["tense"] = "perfect"
        elif main_verbs and main_verbs[0].text.endswith("ed"):
            tense_info["tense"] = "past"
        else:
            tense_info["tense"] = "present"

        # Aspect analysis
        if "be" in aux_verbs and main_verbs and main_verbs[0].text.endswith("ing"):
            tense_info["aspect"] = "progressive"

        return tense_info

    def _extract_modal_info(self, sent: Any) -> Dict[str, Any]:
        """Extract modal information (possibility, necessity, etc.)."""
        modal_info = {}

        # Modal auxiliaries
        modals = {
            "can": {"type": "ability", "strength": "possible"},
            "could": {"type": "ability", "strength": "possible"},
            "may": {"type": "permission", "strength": "possible"},
            "might": {"type": "possibility", "strength": "possible"},
            "must": {"type": "necessity", "strength": "necessary"},
            "should": {"type": "obligation", "strength": "recommended"},
            "would": {"type": "conditional", "strength": "hypothetical"},
            "will": {"type": "future", "strength": "definite"},
        }

        for token in sent:
            if token.text.lower() in modals:
                modal_info = modals[token.text.lower()].copy()
                modal_info["modal"] = token.text.lower()
                break

        return modal_info

    async def _build_compositional_structure(
        self, text: str, doc: Optional[Any], frames: List[SemanticFrame]
    ) -> Dict[str, Any]:
        """Build compositional semantic structure."""
        if not doc:
            return {}

        structure = {
            "type": "compositional_parse",
            "components": [],
            "composition_rules_applied": [],
        }

        # Process each sentence
        for sent in doc.sents:
            sent_structure = await self._compose_sentence_semantics(sent)
            structure["components"].append(sent_structure)

        return structure

    async def _compose_sentence_semantics(self, sent: Any) -> Dict[str, Any]:
        """Compose semantics for a single sentence using compositional rules."""
        # Simplified compositional analysis
        composition = {
            "sentence": sent.text,
            "root": sent.root.text,
            "constituents": [],
            "semantic_composition": "lambda composition",  # Placeholder
        }

        # Identify major constituents
        noun_phrases = []
        verb_phrases = []

        for chunk in sent.noun_chunks:
            noun_phrases.append(
                {
                    "type": "NP",
                    "text": chunk.text,
                    "head": chunk.root.text,
                    "semantic_type": "entity",
                }
            )

        # Find verb phrases (simplified)
        for token in sent:
            if token.pos_ == "VERB" and token.dep_ == "ROOT":
                vp_text = self._extract_verb_phrase(token)
                verb_phrases.append(
                    {
                        "type": "VP",
                        "text": vp_text,
                        "head": token.text,
                        "semantic_type": "predicate",
                    }
                )

        composition["constituents"] = noun_phrases + verb_phrases

        return composition

    def _extract_verb_phrase(self, verb: Any) -> str:
        """Extract verb phrase headed by a verb."""
        vp_tokens = [verb]

        # Add auxiliary verbs
        for child in verb.children:
            if child.dep_ == "aux" or child.dep_ == "auxpass":
                vp_tokens.append(child)

        # Add particles
        for child in verb.children:
            if child.dep_ == "prt":
                vp_tokens.append(child)

        # Sort by position
        vp_tokens.sort(key=lambda x: x.i)

        return " ".join([token.text for token in vp_tokens])

    def _generate_logical_form(
        self,
        frames: List[SemanticFrame],
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
    ) -> str:
        """Generate logical form representation."""
        logical_forms = []

        # Convert frames to logical form
        for frame in frames:
            frame_lf = self._frame_to_logical_form(frame)
            logical_forms.append(frame_lf)

        # Convert relations to logical form
        for relation in relations:
            rel_lf = f"{relation['relation']}({relation['subject']}, {relation['object']})"
            logical_forms.append(rel_lf)

        # Combine with conjunction
        if logical_forms:
            return " ∧ ".join(logical_forms)
        else:
            return "unknown(x)"

    def _frame_to_logical_form(self, frame: SemanticFrame) -> str:
        """Convert semantic frame to logical form."""
        predicate = frame.predicate

        # Extract arguments
        args = []

        # Add agent
        if SemanticRole.AGENT in frame.arguments:
            args.append(frame.arguments[SemanticRole.AGENT][0])

        # Add patient/theme
        if SemanticRole.PATIENT in frame.arguments:
            args.append(frame.arguments[SemanticRole.PATIENT][0])
        elif SemanticRole.THEME in frame.arguments:
            args.append(frame.arguments[SemanticRole.THEME][0])

        # Create logical form
        if args:
            args_str = ", ".join(args)
            return f"{predicate}({args_str})"
        else:
            return f"{predicate}(x)"

    def _detect_ambiguities(
        self, text: str, doc: Optional[Any], frames: List[SemanticFrame]
    ) -> List[str]:
        """Detect potential ambiguities in the parse."""
        ambiguities = []

        if not doc:
            return ambiguities

        # Syntactic ambiguities
        # PP attachment ambiguity
        for token in doc:
            if token.pos_ == "ADP":  # Preposition
                # Check if preposition could attach to different heads
                potential_heads = [
                    child for child in token.head.children if child.pos_ in ["NOUN", "VERB"]
                ]
                if len(potential_heads) > 1:
                    ambiguities.append(
                        f"PP attachment ambiguity: '{token.text}' could modify different elements"
                    )

        # Coordination ambiguity
        for token in doc:
            if token.dep_ == "conj":
                ambiguities.append(f"Coordination scope ambiguity involving '{token.text}'")

        # Semantic ambiguities
        # Word sense disambiguation
        polysemous_words = ["bank", "bark", "bat", "fair", "light", "match", "rock", "scale"]

        for token in doc:
            if token.text.lower() in polysemous_words:
                ambiguities.append(f"Word sense ambiguity: '{token.text}' has multiple meanings")

        # Quantifier scope ambiguity
        quantifiers = ["every", "all", "some", "many", "few", "most"]
        doc_quantifiers = [token for token in doc if token.text.lower() in quantifiers]

        if len(doc_quantifiers) > 1:
            ambiguities.append("Quantifier scope ambiguity: multiple quantifiers present")

        return ambiguities

    def _calculate_confidence(
        self,
        frames: List[SemanticFrame],
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
    ) -> float:
        """Calculate overall confidence in the parse."""
        if not frames and not entities:
            return 0.1

        # Base confidence
        confidence = 0.7

        # Adjust based on frame confidence
        if frames:
            avg_frame_confidence = sum(f.confidence for f in frames) / len(frames)
            confidence = (confidence + avg_frame_confidence) / 2

        # Boost for entities found
        if entities:
            confidence += min(0.2, len(entities) * 0.05)

        # Boost for relations found
        if relations:
            confidence += min(0.1, len(relations) * 0.02)

        return min(1.0, confidence)

    def _calculate_complexity(
        self, frames: List[SemanticFrame], entities: List[Dict[str, Any]]
    ) -> float:
        """Calculate complexity score of the parse."""
        complexity = 0.0

        # Complexity from number of frames
        complexity += len(frames) * 0.2

        # Complexity from frame arguments
        for frame in frames:
            total_args = sum(len(args) for args in frame.arguments.values())
            complexity += total_args * 0.1

        # Complexity from entities
        complexity += len(entities) * 0.1

        return complexity

    def _extract_dependencies(self, doc: Any) -> List[Dict[str, Any]]:
        """Extract dependency graph information."""
        if not doc:
            return []

        dependencies = []

        for token in doc:
            if token.head != token:  # Not root
                dep_info = {
                    "head": token.head.text,
                    "head_pos": token.head.pos_,
                    "dependent": token.text,
                    "dependent_pos": token.pos_,
                    "relation": token.dep_,
                }
                dependencies.append(dep_info)

        return dependencies

    def _frame_to_dict(self, frame: SemanticFrame) -> Dict[str, Any]:
        """Convert SemanticFrame to dictionary."""
        return {
            "predicate": frame.predicate,
            "arguments": {role.value: args for role, args in frame.arguments.items()},
            "frame_type": frame.frame_type,
            "confidence": frame.confidence,
            "source_span": frame.source_span,
            "modifiers": frame.modifiers or [],
            "temporal_info": frame.temporal_info or {},
            "modal_info": frame.modal_info or {},
        }

    def _update_stats(self, frames: List[SemanticFrame], confidence: float):
        """Update parsing statistics."""
        self.stats["sentences_parsed"] += 1
        self.stats["frames_extracted"] += len(frames)

        # Update average confidence
        current_avg = self.stats["average_confidence"]
        total_sentences = self.stats["sentences_parsed"]

        self.stats["average_confidence"] = (
            current_avg * (total_sentences - 1) + confidence
        ) / total_sentences

    async def generate_alternatives(
        self, text: str, max_alternatives: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate alternative parse interpretations."""
        alternatives = []

        # Get main parse
        main_parse = await self.parse(text)
        alternatives.append(main_parse)

        # Generate alternatives by varying interpretation rules
        # This is simplified - real alternatives would require beam search

        for i in range(min(max_alternatives - 1, 2)):
            # Modify confidence slightly for alternative
            alt_parse = main_parse.copy()
            alt_parse["confidence"] *= 0.9 - i * 0.1
            alt_parse["alternative_id"] = i + 1
            alternatives.append(alt_parse)

        return alternatives

    def get_stats(self) -> Dict[str, Any]:
        """Get parsing statistics."""
        return self.stats.copy()
