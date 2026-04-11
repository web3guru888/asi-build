"""
Logic Systems for NL-Logic Bridge.

This module provides support for multiple logical formalisms including
FOL, PLN, temporal logic, modal logic, and others.
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class LogicFormalism(Enum):
    """Supported logic formalisms."""

    FOL = "first_order_logic"
    PLN = "probabilistic_logic_networks"
    TEMPORAL = "temporal_logic"
    MODAL = "modal_logic"
    DESCRIPTION = "description_logic"
    FUZZY = "fuzzy_logic"
    PREDICATE = "predicate_logic"
    PROPOSITIONAL = "propositional_logic"


@dataclass
class LogicalExpression:
    """Represents a logical expression."""

    expression: str
    formalism: LogicFormalism
    parsed_form: Dict[str, Any]
    variables: List[str]
    predicates: List[str]
    operators: List[str]
    confidence: float = 1.0
    strength: float = 1.0
    metadata: Dict[str, Any] = None


class LogicConverter(ABC):
    """Abstract base class for logic converters."""

    @abstractmethod
    async def convert_from_semantic_parse(
        self, semantic_parse: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Convert semantic parse to logical expression."""
        pass

    @abstractmethod
    async def parse_expression(self, expression: str) -> Dict[str, Any]:
        """Parse logical expression into components."""
        pass

    @abstractmethod
    def validate_expression(self, expression: str) -> bool:
        """Validate logical expression syntax."""
        pass


class FOLConverter(LogicConverter):
    """First-Order Logic converter."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def convert_from_semantic_parse(
        self, semantic_parse: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Convert semantic parse to FOL expression."""
        try:
            frames = semantic_parse.get("frames", [])

            if not frames:
                return "Unknown(x)"

            fol_expressions = []

            for frame in frames:
                predicate = frame.get("predicate", "unknown")
                arguments = frame.get("arguments", {})

                # Convert arguments to FOL terms
                agent = arguments.get("agent", [])
                patient = arguments.get("patient", [])

                if agent and patient:
                    agent_term = self._normalize_term(agent[0])
                    patient_term = self._normalize_term(patient[0])
                    fol_expr = f"{predicate}({agent_term}, {patient_term})"
                elif agent:
                    agent_term = self._normalize_term(agent[0])
                    fol_expr = f"{predicate}({agent_term})"
                else:
                    fol_expr = f"{predicate}(x)"

                fol_expressions.append(fol_expr)

            # Combine with conjunction
            if len(fol_expressions) == 1:
                return fol_expressions[0]
            else:
                return " ∧ ".join(fol_expressions)

        except Exception as e:
            self.logger.error(f"Error converting to FOL: {str(e)}")
            return "Error(x)"

    async def parse_expression(self, expression: str) -> Dict[str, Any]:
        """Parse FOL expression into components."""
        components = {
            "type": "fol",
            "variables": [],
            "predicates": [],
            "operators": [],
            "quantifiers": [],
        }

        try:
            # Find quantifiers
            quantifier_pattern = r"(∀|∃)(\w+)"
            quantifier_matches = re.findall(quantifier_pattern, expression)

            for quantifier, variable in quantifier_matches:
                components["quantifiers"].append(
                    {
                        "type": "universal" if quantifier == "∀" else "existential",
                        "variable": variable,
                    }
                )
                components["variables"].append(variable)

            # Find predicates
            predicate_pattern = r"(\w+)\s*\([^)]+\)"
            predicate_matches = re.findall(predicate_pattern, expression)
            components["predicates"].extend(predicate_matches)

            # Find logical operators
            if "∧" in expression:
                components["operators"].append("conjunction")
            if "∨" in expression:
                components["operators"].append("disjunction")
            if "→" in expression:
                components["operators"].append("implication")
            if "¬" in expression:
                components["operators"].append("negation")
            if "↔" in expression:
                components["operators"].append("biconditional")

            # Extract variables from predicates
            variable_pattern = r"\b([a-z])\b"
            variables = re.findall(variable_pattern, expression)
            components["variables"].extend(list(set(variables)))

        except Exception as e:
            self.logger.error(f"Error parsing FOL expression: {str(e)}")

        return components

    def validate_expression(self, expression: str) -> bool:
        """Validate FOL expression syntax."""
        try:
            # Basic syntax checks
            if not expression or not expression.strip():
                return False

            # Check balanced parentheses
            if expression.count("(") != expression.count(")"):
                return False

            # Check for valid characters
            valid_pattern = r"^[a-zA-Z0-9\s\(\)\∀∃∧∨→¬↔,\.]+$"
            if not re.match(valid_pattern, expression):
                return False

            return True

        except Exception:
            return False

    def _normalize_term(self, term: str) -> str:
        """Normalize a term for FOL usage."""
        # Convert to lowercase and replace spaces with underscores
        normalized = term.lower().replace(" ", "_")

        # Remove non-alphanumeric characters except underscores
        normalized = re.sub(r"[^a-zA-Z0-9_]", "", normalized)

        return normalized or "unknown"


class PLNConverter(LogicConverter):
    """Probabilistic Logic Networks converter."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def convert_from_semantic_parse(
        self, semantic_parse: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Convert semantic parse to PLN expression."""
        try:
            frames = semantic_parse.get("frames", [])

            if not frames:
                return "UnknownLink <0.5, 0.5>\n  Unknown\n  Unknown"

            pln_expressions = []

            for frame in frames:
                predicate = frame.get("predicate", "unknown")
                arguments = frame.get("arguments", {})
                confidence = frame.get("confidence", 0.7)
                frame_type = frame.get("frame_type", "action")

                # Determine PLN link type
                if frame_type in ["inheritance", "isa"]:
                    link_type = "InheritanceLink"
                elif frame_type in ["similarity", "like"]:
                    link_type = "SimilarityLink"
                elif frame_type in ["causation", "cause"]:
                    link_type = "CausalLink"
                else:
                    link_type = "ImplicationLink"

                # Extract arguments
                agent = arguments.get("agent", ["X"])
                patient = arguments.get("patient", ["Y"])

                agent_term = self._normalize_concept(agent[0])
                patient_term = self._normalize_concept(patient[0])

                # Estimate strength based on predicate certainty
                strength = self._estimate_strength(predicate, frame_type)

                pln_expr = f"{link_type} <{strength:.2f}, {confidence:.2f}>\n  {agent_term}\n  {patient_term}"
                pln_expressions.append(pln_expr)

            return "\n\n".join(pln_expressions)

        except Exception as e:
            self.logger.error(f"Error converting to PLN: {str(e)}")
            return "ErrorLink <0.1, 0.1>\n  Error\n  Unknown"

    async def parse_expression(self, expression: str) -> Dict[str, Any]:
        """Parse PLN expression into components."""
        components = {
            "type": "pln",
            "links": [],
            "concepts": [],
            "strengths": [],
            "confidences": [],
        }

        try:
            # Parse PLN links
            link_pattern = r"(\w+Link)\s*<([^>]+)>\s*([^\n]+)\s*([^\n]+)"
            link_matches = re.findall(link_pattern, expression, re.MULTILINE)

            for link_type, strength_conf, concept1, concept2 in link_matches:
                # Parse strength and confidence
                values = strength_conf.split(",")
                strength = float(values[0].strip()) if len(values) > 0 else 0.5
                confidence = float(values[1].strip()) if len(values) > 1 else 0.5

                link_info = {
                    "type": link_type,
                    "strength": strength,
                    "confidence": confidence,
                    "source": concept1.strip(),
                    "target": concept2.strip(),
                }

                components["links"].append(link_info)
                components["concepts"].extend([concept1.strip(), concept2.strip()])
                components["strengths"].append(strength)
                components["confidences"].append(confidence)

            # Remove duplicates from concepts
            components["concepts"] = list(set(components["concepts"]))

        except Exception as e:
            self.logger.error(f"Error parsing PLN expression: {str(e)}")

        return components

    def validate_expression(self, expression: str) -> bool:
        """Validate PLN expression syntax."""
        try:
            # Check for PLN link pattern
            link_pattern = r"\w+Link\s*<[^>]+>\s*\S+\s*\S+"

            return bool(re.search(link_pattern, expression))

        except Exception:
            return False

    def _normalize_concept(self, concept: str) -> str:
        """Normalize a concept for PLN usage."""
        # Capitalize first letter, replace spaces with underscores
        normalized = concept.strip()
        if normalized:
            normalized = normalized[0].upper() + normalized[1:].lower()
            normalized = normalized.replace(" ", "_")

        return normalized or "UnknownConcept"

    def _estimate_strength(self, predicate: str, frame_type: str) -> float:
        """Estimate strength value based on predicate and frame type."""
        # Strong predicates get higher strength
        strong_predicates = {"cause", "create", "destroy", "kill", "break"}
        medium_predicates = {"help", "influence", "affect", "change"}
        weak_predicates = {"suggest", "imply", "might", "could"}

        if predicate.lower() in strong_predicates:
            return 0.9
        elif predicate.lower() in medium_predicates:
            return 0.7
        elif predicate.lower() in weak_predicates:
            return 0.4
        else:
            return 0.6  # Default strength


class TemporalLogicConverter(LogicConverter):
    """Temporal Logic converter."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def convert_from_semantic_parse(
        self, semantic_parse: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Convert semantic parse to temporal logic expression."""
        try:
            frames = semantic_parse.get("frames", [])

            temporal_expressions = []

            for frame in frames:
                predicate = frame.get("predicate", "unknown")
                temporal_info = frame.get("temporal_info", {})

                if temporal_info:
                    tense = temporal_info.get("tense", "present")
                    temporal_marker = temporal_info.get("temporal_marker", "")

                    if tense == "future":
                        expr = f"◊F {predicate}(x)"  # Eventually in the future
                    elif tense == "past":
                        expr = f"◊P {predicate}(x)"  # Sometimes in the past
                    elif temporal_marker == "always":
                        expr = f"□ {predicate}(x)"  # Always
                    elif temporal_marker == "eventually":
                        expr = f"◊ {predicate}(x)"  # Eventually
                    else:
                        expr = f"{predicate}(x)"  # Present/atemporal
                else:
                    expr = f"{predicate}(x)"

                temporal_expressions.append(expr)

            return " ∧ ".join(temporal_expressions) if temporal_expressions else "◊ Unknown(x)"

        except Exception as e:
            self.logger.error(f"Error converting to temporal logic: {str(e)}")
            return "Error(x)"

    async def parse_expression(self, expression: str) -> Dict[str, Any]:
        """Parse temporal logic expression into components."""
        components = {
            "type": "temporal",
            "operators": [],
            "predicates": [],
            "temporal_modalities": [],
        }

        try:
            # Find temporal operators
            if "◊" in expression:
                components["operators"].append("diamond")
                components["temporal_modalities"].append("eventually")
            if "□" in expression:
                components["operators"].append("box")
                components["temporal_modalities"].append("always")
            if "◊F" in expression:
                components["operators"].append("future_diamond")
                components["temporal_modalities"].append("eventually_future")
            if "◊P" in expression:
                components["operators"].append("past_diamond")
                components["temporal_modalities"].append("eventually_past")

            # Find predicates
            predicate_pattern = r"(\w+)\s*\([^)]*\)"
            predicates = re.findall(predicate_pattern, expression)
            components["predicates"].extend(predicates)

        except Exception as e:
            self.logger.error(f"Error parsing temporal logic: {str(e)}")

        return components

    def validate_expression(self, expression: str) -> bool:
        """Validate temporal logic expression syntax."""
        try:
            # Check for valid temporal logic symbols
            valid_pattern = r"^[a-zA-Z0-9\s\(\)◊□∧∨→¬FPGHXxUyRSWC,\.]+$"
            return bool(re.match(valid_pattern, expression))
        except Exception:
            return False


class ModalLogicConverter(LogicConverter):
    """Modal Logic converter."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def convert_from_semantic_parse(
        self, semantic_parse: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Convert semantic parse to modal logic expression."""
        try:
            frames = semantic_parse.get("frames", [])

            modal_expressions = []

            for frame in frames:
                predicate = frame.get("predicate", "unknown")
                modal_info = frame.get("modal_info", {})

                if modal_info:
                    modal_type = modal_info.get("type", "")
                    modal_strength = modal_info.get("strength", "")

                    if modal_strength == "necessary":
                        expr = f"□ {predicate}(x)"  # Necessarily
                    elif modal_strength == "possible":
                        expr = f"◊ {predicate}(x)"  # Possibly
                    elif modal_type == "conditional":
                        expr = f"◊ {predicate}(x)"  # Conditionally possible
                    else:
                        expr = f"{predicate}(x)"
                else:
                    expr = f"{predicate}(x)"

                modal_expressions.append(expr)

            return " ∧ ".join(modal_expressions) if modal_expressions else "◊ Unknown(x)"

        except Exception as e:
            self.logger.error(f"Error converting to modal logic: {str(e)}")
            return "Error(x)"

    async def parse_expression(self, expression: str) -> Dict[str, Any]:
        """Parse modal logic expression into components."""
        components = {"type": "modal", "operators": [], "predicates": [], "modalities": []}

        try:
            # Find modal operators
            if "◊" in expression:
                components["operators"].append("diamond")
                components["modalities"].append("possibly")
            if "□" in expression:
                components["operators"].append("box")
                components["modalities"].append("necessarily")

            # Find predicates
            predicate_pattern = r"(\w+)\s*\([^)]*\)"
            predicates = re.findall(predicate_pattern, expression)
            components["predicates"].extend(predicates)

        except Exception as e:
            self.logger.error(f"Error parsing modal logic: {str(e)}")

        return components

    def validate_expression(self, expression: str) -> bool:
        """Validate modal logic expression syntax."""
        try:
            valid_pattern = r"^[a-zA-Z0-9\s\(\)◊□∧∨→¬,\.]+$"
            return bool(re.match(valid_pattern, expression))
        except Exception:
            return False


class LogicSystems:
    """
    Main logic systems manager.

    This class coordinates different logical formalisms and provides
    conversion between semantic parses and logical expressions.
    """

    def __init__(self):
        """Initialize the logic systems manager."""
        self.logger = logging.getLogger(__name__)

        # Initialize converters
        self.converters = {
            LogicFormalism.FOL: FOLConverter(),
            LogicFormalism.PLN: PLNConverter(),
            LogicFormalism.TEMPORAL: TemporalLogicConverter(),
            LogicFormalism.MODAL: ModalLogicConverter(),
        }

        # Statistics
        self.stats = {"conversions_performed": 0, "formalism_usage": {}, "parsing_errors": 0}

    async def convert_to_formalism(
        self,
        semantic_parse: Dict[str, Any],
        formalism: LogicFormalism,
        pln_rules: List[Any] = None,
        context: Dict[str, Any] = None,
    ) -> str:
        """
        Convert semantic parse to specified logical formalism.

        Args:
            semantic_parse: Parsed semantic structure
            formalism: Target logical formalism
            pln_rules: Optional PLN rules for PLN formalism
            context: Additional context information

        Returns:
            Logical expression string
        """
        try:
            converter = self.converters.get(formalism)
            if not converter:
                raise ValueError(f"Unsupported formalism: {formalism}")

            # Use PLN rules if available and formalism is PLN
            if formalism == LogicFormalism.PLN and pln_rules:
                logical_expr = await self._convert_pln_rules_to_expression(pln_rules)
            else:
                logical_expr = await converter.convert_from_semantic_parse(
                    semantic_parse, context or {}
                )

            # Update statistics
            self.stats["conversions_performed"] += 1
            formalism_key = formalism.value
            self.stats["formalism_usage"][formalism_key] = (
                self.stats["formalism_usage"].get(formalism_key, 0) + 1
            )

            self.logger.info(f"Converted to {formalism.value}: {logical_expr[:50]}...")
            return logical_expr

        except Exception as e:
            self.stats["parsing_errors"] += 1
            self.logger.error(f"Error converting to {formalism.value}: {str(e)}")
            return f"Error: Unable to convert to {formalism.value}"

    async def parse_expression(self, expression: str, formalism: LogicFormalism) -> Dict[str, Any]:
        """
        Parse logical expression into components.

        Args:
            expression: Logical expression string
            formalism: Logic formalism type

        Returns:
            Parsed components dictionary
        """
        try:
            converter = self.converters.get(formalism)
            if not converter:
                return {"error": f"Unsupported formalism: {formalism}"}

            parsed = await converter.parse_expression(expression)
            parsed["original_expression"] = expression
            parsed["formalism"] = formalism.value

            return parsed

        except Exception as e:
            self.stats["parsing_errors"] += 1
            self.logger.error(f"Error parsing {formalism.value} expression: {str(e)}")
            return {"error": str(e), "original_expression": expression}

    def validate_expression(self, expression: str, formalism: LogicFormalism) -> bool:
        """
        Validate logical expression syntax.

        Args:
            expression: Expression to validate
            formalism: Logic formalism

        Returns:
            True if valid, False otherwise
        """
        try:
            converter = self.converters.get(formalism)
            if not converter:
                return False

            return converter.validate_expression(expression)

        except Exception as e:
            self.logger.error(f"Error validating expression: {str(e)}")
            return False

    async def _convert_pln_rules_to_expression(self, pln_rules: List[Any]) -> str:
        """Convert PLN rules to PLN expression format."""
        if not pln_rules:
            return "UnknownLink <0.5, 0.5>\n  Unknown\n  Unknown"

        expressions = []

        for rule in pln_rules:
            if hasattr(rule, "to_pln_format"):
                expressions.append(rule.to_pln_format())
            elif isinstance(rule, dict):
                # Convert dictionary format to PLN
                rule_type = rule.get("rule_type", "ImplicationLink")
                premise = rule.get("premise", ["Unknown"])
                conclusion = rule.get("conclusion", "Unknown")
                strength = rule.get("strength", 0.5)
                confidence = rule.get("confidence", 0.5)

                premise_str = premise[0] if isinstance(premise, list) else str(premise)

                pln_expr = f"{rule_type} <{strength:.2f}, {confidence:.2f}>\n  {premise_str}\n  {conclusion}"
                expressions.append(pln_expr)

        return "\n\n".join(expressions)

    async def convert_between_formalisms(
        self, expression: str, source_formalism: LogicFormalism, target_formalism: LogicFormalism
    ) -> str:
        """
        Convert expression from one formalism to another.

        Args:
            expression: Source expression
            source_formalism: Source logic formalism
            target_formalism: Target logic formalism

        Returns:
            Converted expression
        """
        try:
            # Parse source expression
            parsed = await self.parse_expression(expression, source_formalism)

            if "error" in parsed:
                return f"Error: {parsed['error']}"

            # Convert parsed form to target formalism
            # This is simplified - a full implementation would have
            # more sophisticated conversion logic

            if target_formalism == LogicFormalism.FOL:
                return await self._convert_to_fol_from_parsed(parsed)
            elif target_formalism == LogicFormalism.PLN:
                return await self._convert_to_pln_from_parsed(parsed)
            elif target_formalism == LogicFormalism.TEMPORAL:
                return await self._convert_to_temporal_from_parsed(parsed)
            elif target_formalism == LogicFormalism.MODAL:
                return await self._convert_to_modal_from_parsed(parsed)
            else:
                return f"Conversion to {target_formalism.value} not implemented"

        except Exception as e:
            self.logger.error(f"Error converting between formalisms: {str(e)}")
            return f"Error: {str(e)}"

    async def _convert_to_fol_from_parsed(self, parsed: Dict[str, Any]) -> str:
        """Convert parsed expression to FOL."""
        if parsed.get("type") == "pln":
            links = parsed.get("links", [])
            if links:
                link = links[0]  # Take first link
                source = link.get("source", "X")
                target = link.get("target", "Y")
                return f"Relation({source}, {target})"

        return "Unknown(x)"

    async def _convert_to_pln_from_parsed(self, parsed: Dict[str, Any]) -> str:
        """Convert parsed expression to PLN."""
        if parsed.get("type") == "fol":
            predicates = parsed.get("predicates", [])
            if predicates:
                pred = predicates[0]
                return f"ImplicationLink <0.7, 0.8>\n  {pred}\n  True"

        return "UnknownLink <0.5, 0.5>\n  Unknown\n  Unknown"

    async def _convert_to_temporal_from_parsed(self, parsed: Dict[str, Any]) -> str:
        """Convert parsed expression to temporal logic."""
        predicates = parsed.get("predicates", [])
        if predicates:
            return f"◊ {predicates[0]}(x)"

        return "◊ Unknown(x)"

    async def _convert_to_modal_from_parsed(self, parsed: Dict[str, Any]) -> str:
        """Convert parsed expression to modal logic."""
        predicates = parsed.get("predicates", [])
        if predicates:
            return f"◊ {predicates[0]}(x)"

        return "◊ Unknown(x)"

    def get_supported_formalisms(self) -> List[LogicFormalism]:
        """Get list of supported logical formalisms."""
        return list(self.converters.keys())

    def get_formalism_info(self, formalism: LogicFormalism) -> Dict[str, Any]:
        """Get information about a specific formalism."""
        info = {
            LogicFormalism.FOL: {
                "name": "First-Order Logic",
                "description": "Classical predicate logic with quantifiers",
                "operators": ["∀", "∃", "∧", "∨", "→", "¬", "↔"],
                "use_cases": [
                    "Mathematical reasoning",
                    "Knowledge representation",
                    "Automated theorem proving",
                ],
            },
            LogicFormalism.PLN: {
                "name": "Probabilistic Logic Networks",
                "description": "Logic with uncertainty and strength values",
                "operators": ["InheritanceLink", "SimilarityLink", "ImplicationLink"],
                "use_cases": ["Uncertain reasoning", "Knowledge fusion", "AGI applications"],
            },
            LogicFormalism.TEMPORAL: {
                "name": "Temporal Logic",
                "description": "Logic for reasoning about time",
                "operators": ["◊", "□", "◊F", "◊P", "U", "S"],
                "use_cases": ["System verification", "Planning", "Event reasoning"],
            },
            LogicFormalism.MODAL: {
                "name": "Modal Logic",
                "description": "Logic for necessity and possibility",
                "operators": ["◊", "□"],
                "use_cases": ["Epistemic reasoning", "Deontic logic", "Belief systems"],
            },
        }

        return info.get(formalism, {"name": "Unknown", "description": "Unknown formalism"})

    def get_stats(self) -> Dict[str, Any]:
        """Get logic systems statistics."""
        return self.stats.copy()
