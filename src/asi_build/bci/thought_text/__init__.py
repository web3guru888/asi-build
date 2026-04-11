"""
Thought-to-Text Conversion Module

Advanced systems for converting imagined speech and thoughts to text.
Includes speech imagery detection and language model integration.
"""

try:
    from .converter import ThoughtToTextConverter
except (ImportError, ModuleNotFoundError, SyntaxError):
    ThoughtToTextConverter = None
try:
    from .speech_imagery_decoder import SpeechImageryDecoder
except (ImportError, ModuleNotFoundError, SyntaxError):
    SpeechImageryDecoder = None
try:
    from .language_model import NeuralLanguageModel
except (ImportError, ModuleNotFoundError, SyntaxError):
    NeuralLanguageModel = None
try:
    from .text_predictor import TextPredictor
except (ImportError, ModuleNotFoundError, SyntaxError):
    TextPredictor = None

__all__ = ["ThoughtToTextConverter", "SpeechImageryDecoder", "NeuralLanguageModel", "TextPredictor"]
