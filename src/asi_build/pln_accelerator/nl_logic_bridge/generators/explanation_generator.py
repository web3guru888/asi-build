"""
Logic-to-explanation generator for human comprehension.

This module generates natural language explanations of logical expressions,
making symbolic reasoning accessible to human users and researchers.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from ..core.logic_systems import LogicFormalism
from ..parsers.pln_extractor import PLNRule, PLNRuleType


class ExplanationStyle(Enum):
    """Different styles of explanations."""

    FORMAL = "formal"  # Technical, precise explanations
    CONVERSATIONAL = "conversational"  # Natural, everyday language
    EDUCATIONAL = "educational"  # Teaching-focused explanations
    SIMPLIFIED = "simplified"  # Very basic explanations
    TECHNICAL = "technical"  # For experts and researchers


@dataclass
class ExplanationConfig:
    """Configuration for explanation generation."""

    style: ExplanationStyle = ExplanationStyle.CONVERSATIONAL
    max_length: int = 200
    include_examples: bool = True
    include_counterexamples: bool = False
    detail_level: int = 2  # 1=basic, 2=medium, 3=detailed
    audience: str = "general"  # general, expert, student
    include_visual_aids: bool = False
    multilingual: bool = False


@dataclass
class Explanation:
    """Generated explanation of a logical expression."""

    logical_expression: str
    natural_language: str
    style: ExplanationStyle
    examples: List[str]
    counterexamples: List[str]
    confidence: float
    metadata: Dict[str, Any]
    visual_representation: Optional[str] = None
    step_by_step: List[str] = None


class ExplanationGenerator:
    """
    Logic-to-explanation generator for human comprehension.

    This class converts formal logical expressions into clear, understandable
    natural language explanations suitable for different audiences.
    """

    def __init__(self, config: Optional[ExplanationConfig] = None):
        """Initialize the explanation generator."""
        self.config = config or ExplanationConfig()
        self.logger = logging.getLogger(__name__)

        # Load language generation models
        self._load_models()

        # Initialize explanation templates
        self._init_templates()

        # Statistics tracking
        self.stats = {"explanations_generated": 0, "average_confidence": 0.0, "styles_used": {}}

    def _load_models(self):
        """Load language generation models."""
        try:
            # Load GPT-2 for text generation
            self.text_generator = pipeline(
                "text-generation", model="gpt2-medium", return_full_text=False, pad_token_id=50256
            )

            # Load T5 for text-to-text generation
            self.t5_generator = pipeline("text2text-generation", model="t5-base")

            # Load summarization model for concise explanations
            self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

            self.logger.info("Successfully loaded explanation generation models")

        except Exception as e:
            self.logger.error(f"Error loading models: {str(e)}")
            # Fallback to template-based generation
            self.text_generator = None
            self.t5_generator = None
            self.summarizer = None

    def _init_templates(self):
        """Initialize explanation templates for different logic types."""
        self.templates = {
            PLNRuleType.INHERITANCE: {
                ExplanationStyle.FORMAL: "The logical expression states that all members of {premise} belong to the class {conclusion}.",
                ExplanationStyle.CONVERSATIONAL: "This means that every {premise} is also a {conclusion}.",
                ExplanationStyle.EDUCATIONAL: "When we say {premise} inherits from {conclusion}, we're establishing a 'is-a' relationship.",
                ExplanationStyle.SIMPLIFIED: "{premise} is a type of {conclusion}.",
                ExplanationStyle.TECHNICAL: "∀x: {premise}(x) → {conclusion}(x) with strength {strength} and confidence {confidence}.",
            },
            PLNRuleType.IMPLICATION: {
                ExplanationStyle.FORMAL: "The implication states that whenever {premise} is true, {conclusion} follows with probability {strength}.",
                ExplanationStyle.CONVERSATIONAL: "If {premise} happens, then {conclusion} is likely to happen too.",
                ExplanationStyle.EDUCATIONAL: "This is a conditional relationship where {premise} leads to {conclusion}.",
                ExplanationStyle.SIMPLIFIED: "When {premise}, then {conclusion}.",
                ExplanationStyle.TECHNICAL: "P({conclusion}|{premise}) = {strength} ± {confidence}",
            },
            PLNRuleType.SIMILARITY: {
                ExplanationStyle.FORMAL: "The similarity relation indicates that {premise} and {conclusion} share common properties with degree {strength}.",
                ExplanationStyle.CONVERSATIONAL: "{premise} and {conclusion} are quite similar to each other.",
                ExplanationStyle.EDUCATIONAL: "This shows that {premise} and {conclusion} have many things in common.",
                ExplanationStyle.SIMPLIFIED: "{premise} is like {conclusion}.",
                ExplanationStyle.TECHNICAL: "sim({premise}, {conclusion}) = {strength}",
            },
            PLNRuleType.CAUSAL: {
                ExplanationStyle.FORMAL: "The causal relation establishes that {premise} directly causes {conclusion} with strength {strength}.",
                ExplanationStyle.CONVERSATIONAL: "{premise} causes {conclusion} to happen.",
                ExplanationStyle.EDUCATIONAL: "This is a cause-and-effect relationship where {premise} leads to {conclusion}.",
                ExplanationStyle.SIMPLIFIED: "{premise} makes {conclusion} happen.",
                ExplanationStyle.TECHNICAL: "causal({premise} → {conclusion}) = {strength}",
            },
            PLNRuleType.NEGATION: {
                ExplanationStyle.FORMAL: "The negation indicates that {premise} and {conclusion} are mutually exclusive.",
                ExplanationStyle.CONVERSATIONAL: "{premise} is not {conclusion}.",
                ExplanationStyle.EDUCATIONAL: "This tells us that {premise} and {conclusion} cannot both be true.",
                ExplanationStyle.SIMPLIFIED: "{premise} ≠ {conclusion}.",
                ExplanationStyle.TECHNICAL: "¬({premise} ∧ {conclusion})",
            },
            PLNRuleType.EQUIVALENCE: {
                ExplanationStyle.FORMAL: "The equivalence relation states that {premise} and {conclusion} are logically equivalent.",
                ExplanationStyle.CONVERSATIONAL: "{premise} and {conclusion} mean the same thing.",
                ExplanationStyle.EDUCATIONAL: "These two concepts are interchangeable - they have the same meaning.",
                ExplanationStyle.SIMPLIFIED: "{premise} = {conclusion}.",
                ExplanationStyle.TECHNICAL: "{premise} ↔ {conclusion}",
            },
            PLNRuleType.TEMPORAL: {
                ExplanationStyle.FORMAL: "The temporal relation specifies the chronological order between {premise} and {conclusion}.",
                ExplanationStyle.CONVERSATIONAL: "{premise} happens before {conclusion}.",
                ExplanationStyle.EDUCATIONAL: "This shows us the time sequence of events.",
                ExplanationStyle.SIMPLIFIED: "{premise} comes first, then {conclusion}.",
                ExplanationStyle.TECHNICAL: "temporal_order({premise}, {conclusion})",
            },
        }

        # FOL-specific templates
        self.fol_templates = {
            "universal": {
                ExplanationStyle.CONVERSATIONAL: "For all {variable}, if {variable} is a {premise}, then {variable} is also a {conclusion}.",
                ExplanationStyle.SIMPLIFIED: "All {premise} are {conclusion}.",
                ExplanationStyle.FORMAL: "∀{variable} ({premise}({variable}) → {conclusion}({variable}))",
            },
            "existential": {
                ExplanationStyle.CONVERSATIONAL: "There exists at least one {variable} that is both a {premise} and a {conclusion}.",
                ExplanationStyle.SIMPLIFIED: "Some {premise} are {conclusion}.",
                ExplanationStyle.FORMAL: "∃{variable} ({premise}({variable}) ∧ {conclusion}({variable}))",
            },
            "conjunction": {
                ExplanationStyle.CONVERSATIONAL: "Both {premise1} and {premise2} are true.",
                ExplanationStyle.SIMPLIFIED: "{premise1} and {premise2}.",
                ExplanationStyle.FORMAL: "{premise1} ∧ {premise2}",
            },
            "disjunction": {
                ExplanationStyle.CONVERSATIONAL: "Either {premise1} or {premise2} (or both) is true.",
                ExplanationStyle.SIMPLIFIED: "{premise1} or {premise2}.",
                ExplanationStyle.FORMAL: "{premise1} ∨ {premise2}",
            },
        }

    async def generate_explanations(
        self,
        source_text: str,
        logical_representation: str,
        formalism: LogicFormalism,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Generate explanations for a logical representation.

        Args:
            source_text: Original natural language text
            logical_representation: Logical form to explain
            formalism: Logic formalism used
            context: Additional context information

        Returns:
            List of explanations in natural language
        """
        try:
            explanations = []

            # Generate template-based explanation
            template_explanation = await self._generate_template_explanation(
                logical_representation, formalism, context
            )
            if template_explanation:
                explanations.append(template_explanation.natural_language)

            # Generate neural explanation
            if self.text_generator:
                neural_explanation = await self._generate_neural_explanation(
                    source_text, logical_representation, formalism
                )
                if neural_explanation:
                    explanations.append(neural_explanation.natural_language)

            # Generate step-by-step explanation
            step_explanation = await self._generate_step_by_step_explanation(
                logical_representation, formalism, context
            )
            if step_explanation:
                explanations.extend(step_explanation.step_by_step)

            # Generate examples
            if self.config.include_examples:
                examples = await self._generate_examples(logical_representation, formalism, context)
                explanations.extend(examples)

            self._update_stats(explanations)

            self.logger.info(f"Generated {len(explanations)} explanations")
            return explanations

        except Exception as e:
            self.logger.error(f"Error generating explanations: {str(e)}")
            return [f"Unable to generate explanation for: {logical_representation}"]

    async def explain_logic(
        self,
        logical_expression: str,
        formalism: LogicFormalism,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Explain a logical expression in natural language.

        Args:
            logical_expression: Logical expression to explain
            formalism: Logic formalism
            context: Additional context

        Returns:
            List of explanations
        """
        try:
            if formalism == LogicFormalism.PLN:
                return await self._explain_pln_expression(logical_expression, context)
            elif formalism == LogicFormalism.FOL:
                return await self._explain_fol_expression(logical_expression, context)
            elif formalism == LogicFormalism.TEMPORAL:
                return await self._explain_temporal_logic(logical_expression, context)
            elif formalism == LogicFormalism.MODAL:
                return await self._explain_modal_logic(logical_expression, context)
            else:
                return await self._explain_generic_logic(logical_expression, formalism, context)

        except Exception as e:
            self.logger.error(f"Error explaining logic: {str(e)}")
            return [f"Unable to explain logical expression: {logical_expression}"]

    async def explain_query_results(
        self, query: str, results: Dict[str, Any], formalism: LogicFormalism
    ) -> List[str]:
        """
        Explain query results in natural language.

        Args:
            query: Original query
            results: Query results
            formalism: Logic formalism used

        Returns:
            List of explanations
        """
        explanations = []

        try:
            # Explain the query itself
            query_explanation = f"Your query '{query}' was asking about:"
            explanations.append(query_explanation)

            # Explain the results
            if "matches" in results:
                matches = results["matches"]
                if matches:
                    explanations.append(f"I found {len(matches)} relevant results:")
                    for i, match in enumerate(matches[:5]):  # Show top 5
                        explanations.append(f"{i+1}. {match}")
                else:
                    explanations.append("No matching results were found.")

            # Explain reasoning process
            if "reasoning_steps" in results:
                explanations.append("Here's how I arrived at this answer:")
                explanations.extend(results["reasoning_steps"])

            # Explain confidence
            if "confidence" in results:
                confidence = results["confidence"]
                if confidence > 0.8:
                    explanations.append("I'm quite confident in these results.")
                elif confidence > 0.6:
                    explanations.append("I'm moderately confident in these results.")
                else:
                    explanations.append("These results should be interpreted with caution.")

        except Exception as e:
            self.logger.error(f"Error explaining query results: {str(e)}")
            explanations.append("Unable to explain the query results clearly.")

        return explanations

    async def _generate_template_explanation(
        self,
        logical_representation: str,
        formalism: LogicFormalism,
        context: Optional[Dict[str, Any]],
    ) -> Optional[Explanation]:
        """Generate explanation using templates."""
        try:
            # Parse the logical representation to identify components
            components = self._parse_logical_expression(logical_representation, formalism)

            if not components:
                return None

            rule_type = components.get("type")
            premise = components.get("premise", "")
            conclusion = components.get("conclusion", "")
            strength = components.get("strength", 0.5)
            confidence = components.get("confidence", 0.5)

            # Get appropriate template
            if rule_type in self.templates:
                template = self.templates[rule_type].get(self.config.style, "")

                if template:
                    # Fill in template variables
                    explanation_text = template.format(
                        premise=premise,
                        conclusion=conclusion,
                        strength=strength,
                        confidence=confidence,
                    )

                    return Explanation(
                        logical_expression=logical_representation,
                        natural_language=explanation_text,
                        style=self.config.style,
                        examples=[],
                        counterexamples=[],
                        confidence=0.8,
                        metadata={
                            "method": "template_based",
                            "rule_type": rule_type.value if rule_type else "unknown",
                        },
                    )

        except Exception as e:
            self.logger.warning(f"Error in template explanation: {str(e)}")

        return None

    async def _generate_neural_explanation(
        self, source_text: str, logical_representation: str, formalism: LogicFormalism
    ) -> Optional[Explanation]:
        """Generate explanation using neural language models."""
        if not self.text_generator:
            return None

        try:
            # Create prompt for explanation generation
            prompt = self._create_explanation_prompt(source_text, logical_representation, formalism)

            # Generate explanation
            generated = self.text_generator(
                prompt,
                max_length=self.config.max_length,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
            )

            explanation_text = generated[0]["generated_text"].strip()

            # Clean up the generated text
            explanation_text = self._clean_generated_text(explanation_text)

            return Explanation(
                logical_expression=logical_representation,
                natural_language=explanation_text,
                style=self.config.style,
                examples=[],
                counterexamples=[],
                confidence=0.7,
                metadata={"method": "neural_generation"},
            )

        except Exception as e:
            self.logger.warning(f"Error in neural explanation: {str(e)}")
            return None

    async def _generate_step_by_step_explanation(
        self,
        logical_representation: str,
        formalism: LogicFormalism,
        context: Optional[Dict[str, Any]],
    ) -> Optional[Explanation]:
        """Generate step-by-step breakdown of logical reasoning."""
        try:
            steps = []

            # Step 1: Identify the type of logical expression
            expr_type = self._identify_expression_type(logical_representation, formalism)
            steps.append(f"Step 1: This is a {expr_type} expression.")

            # Step 2: Break down components
            components = self._parse_logical_expression(logical_representation, formalism)
            if components:
                premise = components.get("premise", "")
                conclusion = components.get("conclusion", "")

                if premise:
                    steps.append(f"Step 2: The premise (condition) is: {premise}")
                if conclusion:
                    steps.append(f"Step 3: The conclusion (result) is: {conclusion}")

            # Step 3: Explain the relationship
            relationship_explanation = self._explain_logical_relationship(
                logical_representation, formalism
            )
            if relationship_explanation:
                steps.append(f"Step 4: The relationship means: {relationship_explanation}")

            # Step 4: Provide interpretation
            interpretation = self._generate_interpretation(logical_representation, formalism)
            if interpretation:
                steps.append(f"Step 5: In plain English: {interpretation}")

            return Explanation(
                logical_expression=logical_representation,
                natural_language=" ".join(steps),
                style=self.config.style,
                examples=[],
                counterexamples=[],
                confidence=0.8,
                metadata={"method": "step_by_step"},
                step_by_step=steps,
            )

        except Exception as e:
            self.logger.warning(f"Error in step-by-step explanation: {str(e)}")
            return None

    async def _generate_examples(
        self,
        logical_representation: str,
        formalism: LogicFormalism,
        context: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Generate concrete examples for the logical expression."""
        examples = []

        try:
            components = self._parse_logical_expression(logical_representation, formalism)

            if components and "type" in components:
                rule_type = components["type"]
                premise = components.get("premise", "")
                conclusion = components.get("conclusion", "")

                if rule_type == PLNRuleType.INHERITANCE and premise and conclusion:
                    examples.append(
                        f"Example: If we know that '{premise}' includes dogs, and dogs are animals, then dogs would also be '{conclusion}'."
                    )

                elif rule_type == PLNRuleType.IMPLICATION and premise and conclusion:
                    examples.append(
                        f"Example: If '{premise}' is true (like it's raining), then '{conclusion}' might be true (like the ground gets wet)."
                    )

                elif rule_type == PLNRuleType.CAUSAL and premise and conclusion:
                    examples.append(
                        f"Example: '{premise}' directly causes '{conclusion}' - like how pressing a light switch causes the light to turn on."
                    )

                elif rule_type == PLNRuleType.SIMILARITY and premise and conclusion:
                    examples.append(
                        f"Example: '{premise}' and '{conclusion}' share many characteristics, like how cats and dogs are both pets."
                    )

        except Exception as e:
            self.logger.warning(f"Error generating examples: {str(e)}")

        return examples

    def _create_explanation_prompt(
        self, source_text: str, logical_representation: str, formalism: LogicFormalism
    ) -> str:
        """Create a prompt for neural explanation generation."""
        style_descriptions = {
            ExplanationStyle.FORMAL: "formal and precise",
            ExplanationStyle.CONVERSATIONAL: "conversational and friendly",
            ExplanationStyle.EDUCATIONAL: "educational and clear",
            ExplanationStyle.SIMPLIFIED: "simple and easy to understand",
            ExplanationStyle.TECHNICAL: "technical and detailed",
        }

        style_desc = style_descriptions.get(self.config.style, "clear")

        prompt = f"""
        Explain the following logical expression in a {style_desc} way:
        
        Original text: "{source_text}"
        Logical form: {logical_representation}
        Logic type: {formalism.value}
        
        Explanation:"""

        return prompt

    def _clean_generated_text(self, text: str) -> str:
        """Clean up generated explanation text."""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Remove incomplete sentences at the end
        sentences = text.split(".")
        if len(sentences) > 1 and len(sentences[-1].strip()) < 10:
            text = ".".join(sentences[:-1]) + "."

        # Capitalize first letter
        if text and not text[0].isupper():
            text = text[0].upper() + text[1:]

        return text

    def _parse_logical_expression(
        self, expression: str, formalism: LogicFormalism
    ) -> Optional[Dict[str, Any]]:
        """Parse logical expression to extract components."""
        try:
            if formalism == LogicFormalism.PLN:
                return self._parse_pln_expression(expression)
            elif formalism == LogicFormalism.FOL:
                return self._parse_fol_expression(expression)
            else:
                return self._parse_generic_expression(expression)

        except Exception as e:
            self.logger.warning(f"Error parsing expression: {str(e)}")
            return None

    def _parse_pln_expression(self, expression: str) -> Optional[Dict[str, Any]]:
        """Parse PLN expression format."""
        # Look for PLN link patterns
        inheritance_pattern = r"InheritanceLink\s*<([^>]+)>\s*([^\n]+)\s+([^\n]+)"
        implication_pattern = r"ImplicationLink\s*<([^>]+)>\s*([^\n]+)\s+([^\n]+)"
        similarity_pattern = r"SimilarityLink\s*<([^>]+)>\s*([^\n]+)\s+([^\n]+)"

        patterns = [
            (inheritance_pattern, PLNRuleType.INHERITANCE),
            (implication_pattern, PLNRuleType.IMPLICATION),
            (similarity_pattern, PLNRuleType.SIMILARITY),
        ]

        for pattern, rule_type in patterns:
            match = re.search(pattern, expression, re.IGNORECASE | re.DOTALL)
            if match:
                strength_conf = match.group(1).split(",")
                strength = float(strength_conf[0].strip()) if len(strength_conf) > 0 else 0.5
                confidence = float(strength_conf[1].strip()) if len(strength_conf) > 1 else 0.5

                return {
                    "type": rule_type,
                    "premise": match.group(2).strip(),
                    "conclusion": match.group(3).strip(),
                    "strength": strength,
                    "confidence": confidence,
                }

        return None

    def _parse_fol_expression(self, expression: str) -> Optional[Dict[str, Any]]:
        """Parse First-Order Logic expression."""
        # Universal quantifier
        universal_pattern = r"∀(\w+)\s*\(([^)]+)\s*→\s*([^)]+)\)"
        match = re.search(universal_pattern, expression)
        if match:
            return {
                "type": "universal",
                "variable": match.group(1),
                "premise": match.group(2),
                "conclusion": match.group(3),
            }

        # Existential quantifier
        existential_pattern = r"∃(\w+)\s*\(([^)]+)\s*∧\s*([^)]+)\)"
        match = re.search(existential_pattern, expression)
        if match:
            return {
                "type": "existential",
                "variable": match.group(1),
                "premise": match.group(2),
                "conclusion": match.group(3),
            }

        return None

    def _parse_generic_expression(self, expression: str) -> Optional[Dict[str, Any]]:
        """Parse generic logical expression."""
        # Simple implication pattern
        if "→" in expression or "->" in expression:
            parts = re.split(r"→|->", expression, 1)
            if len(parts) == 2:
                return {
                    "type": "implication",
                    "premise": parts[0].strip(),
                    "conclusion": parts[1].strip(),
                }

        # Conjunction pattern
        if "∧" in expression or "AND" in expression.upper():
            parts = re.split(r"∧|AND", expression, 1)
            if len(parts) == 2:
                return {
                    "type": "conjunction",
                    "premise1": parts[0].strip(),
                    "premise2": parts[1].strip(),
                }

        return None

    def _identify_expression_type(self, expression: str, formalism: LogicFormalism) -> str:
        """Identify the type of logical expression."""
        if "InheritanceLink" in expression:
            return "inheritance relationship"
        elif "ImplicationLink" in expression:
            return "implication relationship"
        elif "SimilarityLink" in expression:
            return "similarity relationship"
        elif "∀" in expression:
            return "universal quantification"
        elif "∃" in expression:
            return "existential quantification"
        elif "→" in expression or "->" in expression:
            return "conditional statement"
        elif "∧" in expression:
            return "conjunction (AND)"
        elif "∨" in expression:
            return "disjunction (OR)"
        else:
            return f"{formalism.value} expression"

    def _explain_logical_relationship(self, expression: str, formalism: LogicFormalism) -> str:
        """Explain the logical relationship in the expression."""
        if "InheritanceLink" in expression:
            return "one concept is a subcategory or instance of another"
        elif "ImplicationLink" in expression:
            return "when the first condition is met, the second condition is likely to follow"
        elif "SimilarityLink" in expression:
            return "the two concepts share common properties or characteristics"
        elif "→" in expression:
            return "if the first part is true, then the second part is also true"
        elif "∧" in expression:
            return "both conditions must be true at the same time"
        elif "∨" in expression:
            return "at least one of the conditions must be true"
        else:
            return "establishes a logical connection between concepts"

    def _generate_interpretation(self, expression: str, formalism: LogicFormalism) -> str:
        """Generate a plain English interpretation."""
        components = self._parse_logical_expression(expression, formalism)

        if not components:
            return "This expresses a logical relationship between concepts."

        premise = components.get("premise", "the condition")
        conclusion = components.get("conclusion", "the result")
        expr_type = components.get("type")

        if expr_type == PLNRuleType.INHERITANCE or expr_type == "inheritance":
            return f"Every {premise} is also a {conclusion}."
        elif expr_type == PLNRuleType.IMPLICATION or expr_type == "implication":
            return f"If {premise} is true, then {conclusion} is likely to be true."
        elif expr_type == PLNRuleType.SIMILARITY or expr_type == "similarity":
            return f"{premise} and {conclusion} are similar in nature."
        elif expr_type == "universal":
            return f"For all things, if they are {premise}, then they are also {conclusion}."
        elif expr_type == "conjunction":
            premise1 = components.get("premise1", "first condition")
            premise2 = components.get("premise2", "second condition")
            return f"Both {premise1} and {premise2} are true."
        else:
            return f"There is a logical relationship between {premise} and {conclusion}."

    async def _explain_pln_expression(
        self, expression: str, context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Explain PLN-specific expressions."""
        explanations = []

        components = self._parse_pln_expression(expression)
        if components:
            rule_type = components["type"]
            premise = components["premise"]
            conclusion = components["conclusion"]
            strength = components.get("strength", 0.5)
            confidence = components.get("confidence", 0.5)

            # Main explanation
            if rule_type in self.templates:
                template = self.templates[rule_type].get(self.config.style, "")
                if template:
                    explanation = template.format(
                        premise=premise,
                        conclusion=conclusion,
                        strength=strength,
                        confidence=confidence,
                    )
                    explanations.append(explanation)

            # Add strength and confidence explanation
            strength_desc = (
                "very strong"
                if strength > 0.8
                else "strong" if strength > 0.6 else "moderate" if strength > 0.4 else "weak"
            )
            confidence_desc = (
                "very confident"
                if confidence > 0.8
                else (
                    "confident"
                    if confidence > 0.6
                    else "somewhat confident" if confidence > 0.4 else "uncertain"
                )
            )

            explanations.append(
                f"The relationship is {strength_desc} (strength: {strength:.2f}) and I am {confidence_desc} about this (confidence: {confidence:.2f})."
            )

        return explanations

    async def _explain_fol_expression(
        self, expression: str, context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Explain First-Order Logic expressions."""
        explanations = []

        components = self._parse_fol_expression(expression)
        if components:
            expr_type = components["type"]

            if expr_type in self.fol_templates:
                template = self.fol_templates[expr_type].get(self.config.style, "")
                if template:
                    explanation = template.format(**components)
                    explanations.append(explanation)

        return explanations

    async def _explain_temporal_logic(
        self, expression: str, context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Explain temporal logic expressions."""
        explanations = []

        # Simple temporal patterns
        if "◊" in expression:  # Eventually
            explanations.append(
                "This means that at some point in the future, the condition will be true."
            )
        elif "□" in expression:  # Always
            explanations.append("This means that the condition will always be true, at all times.")
        elif "U" in expression:  # Until
            explanations.append(
                "This describes a situation that continues until another condition becomes true."
            )

        return explanations

    async def _explain_modal_logic(
        self, expression: str, context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Explain modal logic expressions."""
        explanations = []

        if "◊" in expression:  # Possibly
            explanations.append(
                "This expresses that something is possibly true - it could happen in some scenarios."
            )
        elif "□" in expression:  # Necessarily
            explanations.append(
                "This expresses that something is necessarily true - it must be true in all scenarios."
            )

        return explanations

    async def _explain_generic_logic(
        self, expression: str, formalism: LogicFormalism, context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Explain generic logical expressions."""
        explanations = []

        # Basic logical operators
        if "→" in expression or "->" in expression:
            explanations.append(
                "This is a conditional statement: if the first part is true, then the second part follows."
            )
        elif "∧" in expression:
            explanations.append(
                "This is a conjunction: both conditions must be true simultaneously."
            )
        elif "∨" in expression:
            explanations.append(
                "This is a disjunction: at least one of the conditions must be true."
            )
        elif "¬" in expression:
            explanations.append("This is a negation: the condition is false or does not hold.")
        else:
            explanations.append(
                f"This is a {formalism.value} expression that establishes logical relationships."
            )

        return explanations

    def _update_stats(self, explanations: List[str]):
        """Update explanation generation statistics."""
        self.stats["explanations_generated"] += len(explanations)

        style_key = self.config.style.value
        self.stats["styles_used"][style_key] = self.stats["styles_used"].get(style_key, 0) + 1

    def get_stats(self) -> Dict[str, Any]:
        """Get explanation generation statistics."""
        return self.stats.copy()

    def set_style(self, style: ExplanationStyle):
        """Set the explanation style."""
        self.config.style = style

    def set_detail_level(self, level: int):
        """Set the detail level (1=basic, 2=medium, 3=detailed)."""
        self.config.detail_level = max(1, min(3, level))
