"""
Prompt Engine module for code analysis and prompt generation.
"""

from .prompting_engine import PromptingEngine
from .smell_detector import SmellDetector, detect_code_smells
from .dacos_knowledge import DACOSKnowledgeBase
from .dacos_evaluator import DACOSEvaluator
from .templates import (
    REFACTOR_BASE_TEMPLATE,
    DOCUMENTATION_BASE_TEMPLATE,
    get_template_for_smell,
    optimize_template_for_codet5p
)

# Try to import dacos_integration if it exists
try:
    from .dacos_integration import init_dacos, get_dacos
except ImportError:
    # Define placeholder functions if dacos_integration doesn't exist yet
    def init_dacos(path):
        print(f"⚠ dacos_integration not fully implemented")
        return None
    
    def get_dacos():
        return None

__all__ = [
    'PromptingEngine',
    'SmellDetector',
    'detect_code_smells',
    'DACOSKnowledgeBase',
    'DACOSEvaluator',
    'init_dacos',
    'get_dacos',
    'REFACTOR_BASE_TEMPLATE',
    'DOCUMENTATION_BASE_TEMPLATE',
    'get_template_for_smell',
    'optimize_template_for_codet5p'
]