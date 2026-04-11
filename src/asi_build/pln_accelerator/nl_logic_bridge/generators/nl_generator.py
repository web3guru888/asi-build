"""
Natural Language Generation from Logical Expressions.

This module converts formal logical expressions back to natural language,
making symbolic reasoning results accessible to humans.
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


class GenerationStyle(Enum):
    """Different styles of natural language generation."""

    FORMAL = "formal"
    CONVERSATIONAL = "conversational"
    SIMPLIFIED = "simplified"
    TECHNICAL = "technical"
    NARRATIVE = "narrative"


@dataclass
class GenerationConfig:
    """Configuration for natural language generation."""

    style: GenerationStyle = GenerationStyle.CONVERSATIONAL
    max_length: int = 150
    temperature: float = 0.7
    include_confidence: bool = True
    include_reasoning: bool = True
    target_language: str = "en"
    formality_level: int = 2  # 1=informal, 3=very formal
    use_pronouns: bool = True
    include_examples: bool = False


@dataclass
class GeneratedText:
    """Result of natural language generation."""

    logical_input: str
    natural_language: str
    style: GenerationStyle
    confidence: float
    formalism: LogicFormalism
    metadata: Dict[str, Any]
    alternatives: List[str] = None


class NLGenerator:
    """
    Natural Language Generator for logical expressions.

    This class converts formal logical expressions into natural, readable text
    using various generation strategies including templates and neural models.
    """

    def __init__(self, config: Optional[GenerationConfig] = None):
        """Initialize the NL generator."""
        self.config = config or GenerationConfig()
        self.logger = logging.getLogger(__name__)

        # Load generation models
        self._load_models()

        # Initialize generation templates
        self._init_templates()

        # Statistics
        self.stats = {"texts_generated": 0, "average_confidence": 0.0, "styles_used": {}}

    def _load_models(self):
        """Load language generation models."""
        try:
            # Load GPT-2 for general text generation
            self.text_generator = pipeline(
                "text-generation", model="gpt2-medium", return_full_text=False, pad_token_id=50256
            )

            # Load T5 for text-to-text generation
            self.t5_generator = pipeline("text2text-generation", model="t5-base")

            # Load paraphrase model for generating alternatives
            self.paraphrase_model = pipeline(
                "text2text-generation", model="Vamsi/T5_Paraphrase_Paws"
            )

            self.logger.info("Successfully loaded NL generation models")

        except Exception as e:
            self.logger.error(f"Error loading models: {str(e)}")
            # Fallback to template-based generation only
            self.text_generator = None
            self.t5_generator = None
            self.paraphrase_model = None

    def _init_templates(self):
        """Initialize generation templates for different logic types."""

        # PLN rule type templates
        self.pln_templates = {
            PLNRuleType.INHERITANCE: {
                GenerationStyle.FORMAL: "It can be formally stated that {subject} is a type of {object} with strength {strength}.",
                GenerationStyle.CONVERSATIONAL: "Generally speaking, {subject} is a kind of {object}.",
                GenerationStyle.SIMPLIFIED: "{subject} is a {object}.",
                GenerationStyle.TECHNICAL: "InheritanceLink({subject}, {object}) = {strength}",
                GenerationStyle.NARRATIVE: "In our understanding, {subject} belongs to the category of {object}.",
            },
            PLNRuleType.IMPLICATION: {
                GenerationStyle.FORMAL: "The logical implication states that {premise} implies {conclusion} with strength {strength}.",
                GenerationStyle.CONVERSATIONAL: "If {premise}, then {conclusion} is likely to happen.",
                GenerationStyle.SIMPLIFIED: "When {premise}, then {conclusion}.",
                GenerationStyle.TECHNICAL: "P({conclusion}|{premise}) = {strength}",
                GenerationStyle.NARRATIVE: "Our analysis shows that {premise} typically leads to {conclusion}.",
            },
            PLNRuleType.SIMILARITY: {
                GenerationStyle.FORMAL: "The similarity relationship indicates that {subject} and {object} share common properties with degree {strength}.",
                GenerationStyle.CONVERSATIONAL: "{subject} and {object} are quite similar to each other.",
                GenerationStyle.SIMPLIFIED: "{subject} is like {object}.",
                GenerationStyle.TECHNICAL: "SimilarityLink({subject}, {object}) = {strength}",
                GenerationStyle.NARRATIVE: "We observe that {subject} resembles {object} in many ways.",
            },
            PLNRuleType.CAUSAL: {
                GenerationStyle.FORMAL: "The causal relationship establishes that {cause} directly causes {effect} with strength {strength}.",
                GenerationStyle.CONVERSATIONAL: "{cause} causes {effect} to happen.",
                GenerationStyle.SIMPLIFIED: "{cause} makes {effect} happen.",
                GenerationStyle.TECHNICAL: "CausalLink({cause}, {effect}) = {strength}",
                GenerationStyle.NARRATIVE: "Research indicates that {cause} is a primary factor leading to {effect}.",
            },
            PLNRuleType.TEMPORAL: {
                GenerationStyle.FORMAL: "The temporal relationship specifies that {before} occurs before {after}.",
                GenerationStyle.CONVERSATIONAL: "{before} happens before {after}.",
                GenerationStyle.SIMPLIFIED: "First {before}, then {after}.",
                GenerationStyle.TECHNICAL: "TemporalLink({before}, {after})",
                GenerationStyle.NARRATIVE: "In the sequence of events, {before} precedes {after}.",
            },
            PLNRuleType.NEGATION: {
                GenerationStyle.FORMAL: "The negation indicates that {subject} does not possess the property {property}.",
                GenerationStyle.CONVERSATIONAL: "{subject} is not {property}.",
                GenerationStyle.SIMPLIFIED: "{subject} ≠ {property}.",
                GenerationStyle.TECHNICAL: "¬P({subject}, {property})",
                GenerationStyle.NARRATIVE: "Contrary to some beliefs, {subject} does not exhibit {property}.",
            },
        }

        # FOL templates
        self.fol_templates = {
            "universal": {
                GenerationStyle.FORMAL: "For all {variable}, if {variable} is {premise}, then {variable} is {conclusion}.",
                GenerationStyle.CONVERSATIONAL: "All {premise} are {conclusion}.",
                GenerationStyle.SIMPLIFIED: "Every {premise} is a {conclusion}.",
                GenerationStyle.TECHNICAL: "∀{variable}({premise}({variable}) → {conclusion}({variable}))",
                GenerationStyle.NARRATIVE: "Without exception, anything that is {premise} will also be {conclusion}.",
            },
            "existential": {
                GenerationStyle.FORMAL: "There exists at least one {variable} such that {variable} is both {premise} and {conclusion}.",
                GenerationStyle.CONVERSATIONAL: "Some {premise} are also {conclusion}.",
                GenerationStyle.SIMPLIFIED: "There are {premise} that are {conclusion}.",
                GenerationStyle.TECHNICAL: "∃{variable}({premise}({variable}) ∧ {conclusion}({variable}))",
                GenerationStyle.NARRATIVE: "We can find examples where {premise} and {conclusion} occur together.",
            },
            "conjunction": {
                GenerationStyle.FORMAL: "Both {premise1} and {premise2} are simultaneously true.",
                GenerationStyle.CONVERSATIONAL: "{premise1} and {premise2} both happen.",
                GenerationStyle.SIMPLIFIED: "{premise1} and {premise2}.",
                GenerationStyle.TECHNICAL: "{premise1} ∧ {premise2}",
                GenerationStyle.NARRATIVE: "The situation involves both {premise1} and {premise2} occurring together.",
            },
            "disjunction": {
                GenerationStyle.FORMAL: "Either {premise1} or {premise2} (or possibly both) is true.",
                GenerationStyle.CONVERSATIONAL: "Either {premise1} or {premise2} happens.",
                GenerationStyle.SIMPLIFIED: "{premise1} or {premise2}.",
                GenerationStyle.TECHNICAL: "{premise1} ∨ {premise2}",
                GenerationStyle.NARRATIVE: "The outcome depends on whether {premise1} or {premise2} occurs.",
            },
        }

        # Generic logical operator templates
        self.operator_templates = {
            "→": {
                GenerationStyle.CONVERSATIONAL: "if {left}, then {right}",
                GenerationStyle.SIMPLIFIED: "{left} leads to {right}",
                GenerationStyle.FORMAL: "{left} implies {right}",
            },
            "∧": {
                GenerationStyle.CONVERSATIONAL: "{left} and {right}",
                GenerationStyle.SIMPLIFIED: "both {left} and {right}",
                GenerationStyle.FORMAL: "{left} in conjunction with {right}",
            },
            "∨": {
                GenerationStyle.CONVERSATIONAL: "{left} or {right}",
                GenerationStyle.SIMPLIFIED: "either {left} or {right}",
                GenerationStyle.FORMAL: "{left} or alternatively {right}",
            },
            "¬": {
                GenerationStyle.CONVERSATIONAL: "not {operand}",
                GenerationStyle.SIMPLIFIED: "not {operand}",
                GenerationStyle.FORMAL: "the negation of {operand}",
            },
            "↔": {
                GenerationStyle.CONVERSATIONAL: "{left} means the same as {right}",
                GenerationStyle.SIMPLIFIED: "{left} equals {right}",
                GenerationStyle.FORMAL: "{left} is equivalent to {right}",
            },
        }

    async def generate(
        self,
        logical_expression: str,
        formalism: LogicFormalism,
        target_language: str = "en",
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedText:
        """
        Generate natural language from logical expression.

        Args:
            logical_expression: Input logical expression
            formalism: Logic formalism type
            target_language: Target language code
            context: Additional context information

        Returns:
            Generated natural language text
        """
        try:
            # Parse the logical expression
            parsed_logic = await self._parse_logical_expression(logical_expression, formalism)

            # Generate using multiple strategies
            template_result = await self._generate_with_templates(parsed_logic, formalism, context)

            neural_result = None
            if self.text_generator:
                neural_result = await self._generate_with_neural_model(
                    logical_expression, formalism, context
                )

            # Choose best result
            if template_result and (
                not neural_result or template_result.confidence > neural_result.confidence
            ):
                final_result = template_result
            elif neural_result:
                final_result = neural_result
            else:
                # Fallback to basic conversion
                final_result = await self._generate_fallback(logical_expression, formalism)

            # Generate alternatives if requested
            if self.paraphrase_model and self.config.include_examples:
                alternatives = await self._generate_alternatives(final_result.natural_language)
                final_result.alternatives = alternatives

            # Apply post-processing
            final_result = await self._post_process_generated_text(final_result)

            # Update statistics
            self._update_stats(final_result)

            self.logger.info(f"Generated NL text with confidence {final_result.confidence}")
            return final_result

        except Exception as e:
            self.logger.error(f"Error generating natural language: {str(e)}")
            return GeneratedText(
                logical_input=logical_expression,
                natural_language=f"Unable to convert: {logical_expression}",
                style=self.config.style,
                confidence=0.1,
                formalism=formalism,
                metadata={"error": str(e)},
            )

    async def _parse_logical_expression(
        self, expression: str, formalism: LogicFormalism
    ) -> Dict[str, Any]:
        """Parse logical expression into components."""
        try:
            if formalism == LogicFormalism.PLN:
                return await self._parse_pln_expression(expression)
            elif formalism == LogicFormalism.FOL:
                return await self._parse_fol_expression(expression)
            else:
                return await self._parse_generic_expression(expression)
        except Exception as e:
            self.logger.warning(f"Error parsing expression: {str(e)}")
            return {"type": "unknown", "expression": expression}

    async def _parse_pln_expression(self, expression: str) -> Dict[str, Any]:
        """Parse PLN expression format."""
        # Match different PLN link patterns
        patterns = {
            "inheritance": r"InheritanceLink\s*<([^>]+)>\s*([^\n]+)\s*([^\n]+)",
            "implication": r"ImplicationLink\s*<([^>]+)>\s*([^\n]+)\s*([^\n]+)",
            "similarity": r"SimilarityLink\s*<([^>]+)>\s*([^\n]+)\s*([^\n]+)",
            "evaluation": r"EvaluationLink\s*<([^>]+)>\s*([^\n]+)\s*([^\n]+)",
        }

        for pattern_type, pattern in patterns.items():
            match = re.search(pattern, expression, re.IGNORECASE | re.DOTALL)
            if match:
                strength_conf = match.group(1).split(",")
                strength = float(strength_conf[0].strip()) if len(strength_conf) > 0 else 0.5
                confidence = float(strength_conf[1].strip()) if len(strength_conf) > 1 else 0.5

                return {
                    "type": pattern_type,
                    "subject": match.group(2).strip(),
                    "object": match.group(3).strip(),
                    "strength": strength,
                    "confidence": confidence,
                    "rule_type": getattr(
                        PLNRuleType, pattern_type.upper(), PLNRuleType.INHERITANCE
                    ),
                }

        # Fallback parsing
        return {"type": "unknown_pln", "expression": expression}

    async def _parse_fol_expression(self, expression: str) -> Dict[str, Any]:
        """Parse First-Order Logic expression."""
        # Universal quantifier
        universal_match = re.search(r"∀(\w+)\s*\(([^)]+)\s*→\s*([^)]+)\)", expression)
        if universal_match:
            return {
                "type": "universal",
                "variable": universal_match.group(1),
                "premise": universal_match.group(2),
                "conclusion": universal_match.group(3),
            }

        # Existential quantifier
        existential_match = re.search(r"∃(\w+)\s*\(([^)]+)\s*∧\s*([^)]+)\)", expression)
        if existential_match:
            return {
                "type": "existential",
                "variable": existential_match.group(1),
                "premise": existential_match.group(2),
                "conclusion": existential_match.group(3),
            }

        # Simple operators
        if "→" in expression:
            parts = expression.split("→", 1)
            return {
                "type": "implication",
                "premise": parts[0].strip(),
                "conclusion": parts[1].strip(),
            }
        elif "∧" in expression:
            parts = expression.split("∧", 1)
            return {
                "type": "conjunction",
                "premise1": parts[0].strip(),
                "premise2": parts[1].strip(),
            }
        elif "∨" in expression:
            parts = expression.split("∨", 1)
            return {
                "type": "disjunction",
                "premise1": parts[0].strip(),
                "premise2": parts[1].strip(),
            }

        return {"type": "unknown_fol", "expression": expression}

    async def _parse_generic_expression(self, expression: str) -> Dict[str, Any]:
        """Parse generic logical expression."""
        # Look for common patterns
        if "->" in expression or "→" in expression:
            parts = re.split(r"->|→", expression, 1)
            return {
                "type": "implication",
                "premise": parts[0].strip(),
                "conclusion": parts[1].strip(),
            }
        elif "AND" in expression.upper() or "∧" in expression:
            parts = re.split(r"AND|∧", expression, 1, re.IGNORECASE)
            return {
                "type": "conjunction",
                "premise1": parts[0].strip(),
                "premise2": parts[1].strip(),
            }
        elif "OR" in expression.upper() or "∨" in expression:
            parts = re.split(r"OR|∨", expression, 1, re.IGNORECASE)
            return {
                "type": "disjunction",
                "premise1": parts[0].strip(),
                "premise2": parts[1].strip(),
            }

        return {"type": "atomic", "expression": expression}

    async def _generate_with_templates(
        self,
        parsed_logic: Dict[str, Any],
        formalism: LogicFormalism,
        context: Optional[Dict[str, Any]],
    ) -> Optional[GeneratedText]:
        """Generate text using templates."""
        try:
            logic_type = parsed_logic.get("type", "unknown")

            if formalism == LogicFormalism.PLN:
                return await self._generate_pln_with_templates(parsed_logic)
            elif formalism == LogicFormalism.FOL:
                return await self._generate_fol_with_templates(parsed_logic)
            else:
                return await self._generate_generic_with_templates(parsed_logic)

        except Exception as e:
            self.logger.warning(f"Error in template generation: {str(e)}")
            return None

    async def _generate_pln_with_templates(
        self, parsed_logic: Dict[str, Any]
    ) -> Optional[GeneratedText]:
        """Generate text for PLN expressions using templates."""
        rule_type = parsed_logic.get("rule_type")

        if rule_type and rule_type in self.pln_templates:
            template_dict = self.pln_templates[rule_type]
            template = template_dict.get(self.config.style, "")

            if template:
                # Fill template with values
                filled_text = template.format(**parsed_logic)

                # Add confidence information if requested
                if self.config.include_confidence:
                    strength = parsed_logic.get("strength", 0.5)
                    conf = parsed_logic.get("confidence", 0.5)

                    if strength > 0.8:
                        conf_text = " (high certainty)"
                    elif strength > 0.6:
                        conf_text = " (moderate certainty)"
                    else:
                        conf_text = " (low certainty)"

                    filled_text += conf_text

                return GeneratedText(
                    logical_input=parsed_logic.get("expression", ""),
                    natural_language=filled_text,
                    style=self.config.style,
                    confidence=0.85,
                    formalism=LogicFormalism.PLN,
                    metadata={
                        "method": "template",
                        "rule_type": rule_type.value if rule_type else "unknown",
                    },
                )

        return None

    async def _generate_fol_with_templates(
        self, parsed_logic: Dict[str, Any]
    ) -> Optional[GeneratedText]:
        """Generate text for FOL expressions using templates."""
        logic_type = parsed_logic.get("type", "unknown")

        if logic_type in self.fol_templates:
            template_dict = self.fol_templates[logic_type]
            template = template_dict.get(self.config.style, "")

            if template:
                filled_text = template.format(**parsed_logic)

                return GeneratedText(
                    logical_input=parsed_logic.get("expression", ""),
                    natural_language=filled_text,
                    style=self.config.style,
                    confidence=0.8,
                    formalism=LogicFormalism.FOL,
                    metadata={"method": "template", "logic_type": logic_type},
                )

        return None

    async def _generate_generic_with_templates(
        self, parsed_logic: Dict[str, Any]
    ) -> Optional[GeneratedText]:
        """Generate text for generic expressions using templates."""
        logic_type = parsed_logic.get("type", "unknown")

        # Handle basic logical operators
        if logic_type == "implication":
            template = self.operator_templates["→"][self.config.style]
            text = template.format(
                left=parsed_logic.get("premise", ""), right=parsed_logic.get("conclusion", "")
            )
        elif logic_type == "conjunction":
            template = self.operator_templates["∧"][self.config.style]
            text = template.format(
                left=parsed_logic.get("premise1", ""), right=parsed_logic.get("premise2", "")
            )
        elif logic_type == "disjunction":
            template = self.operator_templates["∨"][self.config.style]
            text = template.format(
                left=parsed_logic.get("premise1", ""), right=parsed_logic.get("premise2", "")
            )
        elif logic_type == "atomic":
            text = f"The statement '{parsed_logic.get('expression', '')}' holds."
        else:
            return None

        return GeneratedText(
            logical_input=parsed_logic.get("expression", ""),
            natural_language=text,
            style=self.config.style,
            confidence=0.7,
            formalism=LogicFormalism.FOL,
            metadata={"method": "template", "logic_type": logic_type},
        )

    async def _generate_with_neural_model(
        self, logical_expression: str, formalism: LogicFormalism, context: Optional[Dict[str, Any]]
    ) -> Optional[GeneratedText]:
        """Generate text using neural language models."""
        if not self.text_generator:
            return None

        try:
            # Create prompt for generation
            prompt = self._create_generation_prompt(logical_expression, formalism)

            # Generate text
            generated = self.text_generator(
                prompt,
                max_length=self.config.max_length,
                temperature=self.config.temperature,
                num_return_sequences=1,
                do_sample=True,
            )

            generated_text = generated[0]["generated_text"].strip()

            # Clean up generated text
            cleaned_text = self._clean_generated_text(generated_text)

            return GeneratedText(
                logical_input=logical_expression,
                natural_language=cleaned_text,
                style=self.config.style,
                confidence=0.75,
                formalism=formalism,
                metadata={"method": "neural", "model": "gpt2-medium"},
            )

        except Exception as e:
            self.logger.warning(f"Error in neural generation: {str(e)}")
            return None

    def _create_generation_prompt(self, logical_expression: str, formalism: LogicFormalism) -> str:
        """Create prompt for neural text generation."""
        style_descriptions = {
            GenerationStyle.FORMAL: "formal and precise",
            GenerationStyle.CONVERSATIONAL: "conversational and friendly",
            GenerationStyle.SIMPLIFIED: "simple and easy to understand",
            GenerationStyle.TECHNICAL: "technical and detailed",
            GenerationStyle.NARRATIVE: "narrative and engaging",
        }

        style_desc = style_descriptions.get(self.config.style, "clear")

        prompt = f"""
        Convert the following logical expression to natural language in a {style_desc} way:
        
        Logic type: {formalism.value}
        Expression: {logical_expression}
        
        Natural language:"""

        return prompt

    def _clean_generated_text(self, text: str) -> str:
        """Clean up generated text."""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Remove incomplete sentences at the end
        sentences = text.split(".")
        if len(sentences) > 1 and len(sentences[-1].strip()) < 10:
            text = ".".join(sentences[:-1]) + "."

        # Ensure proper capitalization
        if text and not text[0].isupper():
            text = text[0].upper() + text[1:]

        # Remove redundant phrases
        redundant_phrases = [
            "natural language:",
            "in other words:",
            "this means:",
            "to put it simply:",
        ]

        for phrase in redundant_phrases:
            text = re.sub(rf"^{re.escape(phrase)}\s*", "", text, flags=re.IGNORECASE)

        return text

    async def _generate_fallback(
        self, logical_expression: str, formalism: LogicFormalism
    ) -> GeneratedText:
        """Generate fallback text when other methods fail."""
        # Very basic conversion
        basic_text = f"This {formalism.value} expression states: {logical_expression}"

        # Try to make it more readable
        readable_text = self._make_expression_readable(logical_expression)

        return GeneratedText(
            logical_input=logical_expression,
            natural_language=readable_text,
            style=self.config.style,
            confidence=0.4,
            formalism=formalism,
            metadata={"method": "fallback"},
        )

    def _make_expression_readable(self, expression: str) -> str:
        """Make logical expression more readable."""
        # Replace logical symbols with words
        replacements = {
            "→": " implies ",
            "∧": " and ",
            "∨": " or ",
            "¬": " not ",
            "∀": " for all ",
            "∃": " there exists ",
            "↔": " is equivalent to ",
            "(": " (",
            ")": ") ",
            "=": " equals ",
        }

        readable = expression
        for symbol, word in replacements.items():
            readable = readable.replace(symbol, word)

        # Clean up extra spaces
        readable = re.sub(r"\s+", " ", readable).strip()

        # Add proper sentence structure
        if not readable.endswith("."):
            readable += "."

        # Capitalize first letter
        if readable:
            readable = readable[0].upper() + readable[1:]

        return readable

    async def _generate_alternatives(self, text: str) -> List[str]:
        """Generate alternative phrasings of the same text."""
        if not self.paraphrase_model:
            return []

        alternatives = []

        try:
            # Generate paraphrases
            paraphrase_input = f"paraphrase: {text}"
            results = self.paraphrase_model(
                paraphrase_input, max_length=150, num_return_sequences=3, temperature=0.8
            )

            for result in results:
                paraphrase = result["generated_text"]
                if paraphrase != text and len(paraphrase) > 10:
                    alternatives.append(paraphrase)

        except Exception as e:
            self.logger.warning(f"Error generating alternatives: {str(e)}")

        return alternatives[:3]  # Return top 3 alternatives

    async def _post_process_generated_text(self, generated_text: GeneratedText) -> GeneratedText:
        """Post-process generated text for quality and consistency."""
        text = generated_text.natural_language

        # Apply style-specific post-processing
        if self.config.style == GenerationStyle.FORMAL:
            text = self._formalize_text(text)
        elif self.config.style == GenerationStyle.SIMPLIFIED:
            text = self._simplify_text(text)
        elif self.config.style == GenerationStyle.CONVERSATIONAL:
            text = self._conversationalize_text(text)

        # Apply language-specific adjustments
        if self.config.target_language != "en":
            text = await self._adjust_for_target_language(text)

        # Update the generated text
        generated_text.natural_language = text

        return generated_text

    def _formalize_text(self, text: str) -> str:
        """Make text more formal."""
        # Replace contractions
        contractions = {
            "can't": "cannot",
            "won't": "will not",
            "don't": "do not",
            "isn't": "is not",
            "aren't": "are not",
        }

        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)

        # Add formal connectors
        if not any(
            word in text.lower()
            for word in ["therefore", "consequently", "moreover", "furthermore"]
        ):
            if "." in text:
                sentences = text.split(".")
                if len(sentences) > 1:
                    text = sentences[0] + ". Furthermore, " + ".".join(sentences[1:])

        return text

    def _simplify_text(self, text: str) -> str:
        """Simplify text for easier understanding."""
        # Replace complex words with simpler alternatives
        simplifications = {
            "consequently": "so",
            "furthermore": "also",
            "nevertheless": "but",
            "subsequently": "then",
            "accordingly": "so",
            "demonstrates": "shows",
            "indicates": "shows",
            "establishes": "shows",
        }

        for complex_word, simple_word in simplifications.items():
            text = re.sub(rf"\b{complex_word}\b", simple_word, text, flags=re.IGNORECASE)

        return text

    def _conversationalize_text(self, text: str) -> str:
        """Make text more conversational."""
        # Add conversational markers
        if not text.startswith(("Well,", "So,", "Now,", "You know,")):
            text = "So, " + text.lower()
            # Re-capitalize first letter after "So, "
            if len(text) > 4:
                text = text[:4] + text[4].upper() + text[5:]

        return text

    async def _adjust_for_target_language(self, text: str) -> str:
        """Adjust text for target language characteristics."""
        # This would integrate with translation services
        # For now, just return the original text
        # In a full implementation, this would:
        # 1. Translate to target language
        # 2. Adjust for cultural context
        # 3. Modify sentence structure as needed

        return text

    def _update_stats(self, generated_text: GeneratedText):
        """Update generation statistics."""
        self.stats["texts_generated"] += 1

        # Update average confidence
        current_avg = self.stats["average_confidence"]
        total_texts = self.stats["texts_generated"]
        new_confidence = generated_text.confidence

        self.stats["average_confidence"] = (
            current_avg * (total_texts - 1) + new_confidence
        ) / total_texts

        # Update style usage
        style_key = generated_text.style.value
        self.stats["styles_used"][style_key] = self.stats["styles_used"].get(style_key, 0) + 1

    async def batch_generate(
        self, expressions: List[str], formalism: LogicFormalism, batch_size: int = 5
    ) -> List[GeneratedText]:
        """Generate natural language for multiple expressions in batches."""
        results = []

        for i in range(0, len(expressions), batch_size):
            batch = expressions[i : i + batch_size]

            # Process batch concurrently
            tasks = [self.generate(expr, formalism) for expr in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
            for result in batch_results:
                if isinstance(result, GeneratedText):
                    results.append(result)
                else:
                    self.logger.error(f"Error in batch generation: {result}")

        return results

    def set_style(self, style: GenerationStyle):
        """Change the generation style."""
        self.config.style = style

    def set_formality_level(self, level: int):
        """Set formality level (1=informal, 3=very formal)."""
        self.config.formality_level = max(1, min(3, level))

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return self.stats.copy()
