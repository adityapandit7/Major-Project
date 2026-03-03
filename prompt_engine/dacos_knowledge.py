from .dacos_integration import get_dacos, init_dacos, DACOSDataset
from typing import Dict, Optional, Any, List, Callable
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default thresholds as fallback
DEFAULT_THRESHOLDS = {
    "Long Method": {"threshold": 20, "severe": 40, "critical": 60},
    "Long Parameter List": {"threshold": 4, "severe": 7, "critical": 10},
    "Complex Conditional": {"threshold": 5, "severe": 10, "critical": 15},
    "Multifaceted Abstraction": {"threshold": 1, "severe": 3, "critical": 5}
}

class DACOSKnowledgeBase:
    """
    DACOS-powered knowledge base for code smells with real thresholds.
    """
    
    def __init__(self, dacos_folder: Optional[str] = None):
        """Initialize with optional path to DACOS folder."""
        self.dacos: Optional[DACOSDataset] = None
        self.dacos_folder = dacos_folder
        self.thresholds = DEFAULT_THRESHOLDS.copy()
        self.initialized = False
        
        # Try to initialize DACOS
        if dacos_folder and dacos_folder != "SKIP":
            self._initialize_dacos()
        
        # Build smell definitions (always have fallbacks)
        self.smells = self._build_smells()
        
        if self.initialized:
            logger.info(f"DACOS Knowledge Base initialized with real thresholds")
        else:
            logger.info("DACOS Knowledge Base initialized with default thresholds")
    
    def _initialize_dacos(self) -> bool:
        """Initialize DACOS with error handling."""
        try:
            self.dacos = init_dacos(self.dacos_folder)
            if self.dacos:
                dacos_thresholds = self.dacos.get_smell_thresholds()
                # Merge with defaults, preferring DACOS values
                for smell, values in dacos_thresholds.items():
                    if smell in self.thresholds:
                        self.thresholds[smell].update(values)
                    else:
                        self.thresholds[smell] = values
                self.initialized = True
                return True
        except Exception as e:
            logger.warning(f"Failed to initialize DACOS: {e}")
        
        return False
    
    def _get_fallback_threshold(self, smell_name: str, level: str = "threshold") -> Any:
        """Get fallback threshold value."""
        return self.thresholds.get(smell_name, {}).get(level, 0)
    
    def _build_smells(self) -> Dict:
        """Build smell definitions using DACOS thresholds."""
        
        # Get thresholds with fallbacks
        long_method = self.thresholds.get("Long Method", {})
        long_method_th = long_method.get("threshold", 20)
        long_method_severe = long_method.get("severe", 40)
        long_method_critical = long_method.get("critical", 60)
        
        long_param = self.thresholds.get("Long Parameter List", {})
        param_th = long_param.get("threshold", 4)
        param_severe = long_param.get("severe", 7)
        param_critical = long_param.get("critical", 10)
        
        complex_cond = self.thresholds.get("Complex Conditional", {})
        complex_th = complex_cond.get("threshold", 5)
        complex_severe = complex_cond.get("severe", 10)
        complex_critical = complex_cond.get("critical", 15)
        
        multifaceted = self.thresholds.get("Multifaceted Abstraction", {})
        multifaceted_th = multifaceted.get("threshold", 1)
        multifaceted_severe = multifaceted.get("severe", 3)
        multifaceted_critical = multifaceted.get("critical", 5)
        
        return {
            "Long Method": {
                "name": "Long Method",
                "description": f"Method is too long (> {long_method_th} lines) and may do too many things.",
                "refactor_guidance": (
                    f"Split the method into smaller helper methods using Extract Method. "
                    f"Each helper method should have a single responsibility. "
                    f"Aim for methods under {long_method_th} lines."
                ),
                "condition": lambda f: f.get("loc", 0) > long_method_th,
                "severity_levels": {
                    "critical": lambda f: f.get("loc", 0) > long_method_critical,
                    "high": lambda f: f.get("loc", 0) > long_method_severe,
                    "medium": lambda f: f.get("loc", 0) > long_method_th
                },
                "thresholds": {
                    "threshold": long_method_th,
                    "severe": long_method_severe,
                    "critical": long_method_critical
                },
                "metric": "loc"
            },
            "Long Parameter List": {
                "name": "Long Parameter List",
                "description": f"Method has too many parameters (> {param_th}), reducing readability.",
                "refactor_guidance": (
                    f"Reduce parameters by introducing parameter objects or grouping related parameters. "
                    f"Consider using a configuration object or builder pattern. "
                    f"Aim for less than {param_th} parameters."
                ),
                "condition": lambda f: f.get("param_count", 0) > param_th,
                "severity_levels": {
                    "critical": lambda f: f.get("param_count", 0) > param_critical,
                    "high": lambda f: f.get("param_count", 0) > param_severe,
                    "medium": lambda f: f.get("param_count", 0) > param_th
                },
                "thresholds": {
                    "threshold": param_th,
                    "severe": param_severe,
                    "critical": param_critical
                },
                "metric": "param_count"
            },
            "Complex Conditional": {
                "name": "Complex Conditional",
                "description": f"Method contains complex conditional logic (responsibility count > {complex_th}).",
                "refactor_guidance": (
                    f"Simplify complex conditionals by extracting them into well-named methods. "
                    f"Use guard clauses to reduce nesting. Consider polymorphism instead of multiple conditions."
                ),
                "condition": lambda f: f.get("responsibility_count", 1) > complex_th,
                "severity_levels": {
                    "critical": lambda f: f.get("responsibility_count", 1) > complex_critical,
                    "high": lambda f: f.get("responsibility_count", 1) > complex_severe,
                    "medium": lambda f: f.get("responsibility_count", 1) > complex_th
                },
                "thresholds": {
                    "threshold": complex_th,
                    "severe": complex_severe,
                    "critical": complex_critical
                },
                "metric": "responsibility_count"
            },
            "Multifaceted Abstraction": {
                "name": "Multifaceted Abstraction",
                "description": f"Function handles multiple unrelated responsibilities (> {multifaceted_th}).",
                "refactor_guidance": (
                    "Separate responsibilities into distinct functions "
                    "following the Single Responsibility Principle. Each function should do one thing well."
                ),
                "condition": lambda f: f.get("responsibility_count", 1) > multifaceted_th,
                "severity_levels": {
                    "critical": lambda f: f.get("responsibility_count", 1) > multifaceted_critical,
                    "high": lambda f: f.get("responsibility_count", 1) > multifaceted_severe,
                    "medium": lambda f: f.get("responsibility_count", 1) > multifaceted_th
                },
                "thresholds": {
                    "threshold": multifaceted_th,
                    "severe": multifaceted_severe,
                    "critical": multifaceted_critical
                },
                "metric": "responsibility_count"
            }
        }
    
    def get_smell_info(self, smell_name: str) -> Optional[Dict]:
        """Get information about a specific smell."""
        return self.smells.get(smell_name)
    
    def get_all_smells(self) -> Dict:
        """Get all smell definitions."""
        return self.smells
    
    def get_dacos_context(self) -> str:
        """Get DACOS context for prompts."""
        if self.dacos and self.initialized:
            return self.dacos.generate_dacos_context()
        return "DACOS dataset not loaded. Using standard thresholds."
    
    def get_severity(self, smell_name: str, func: dict) -> str:
        """
        Determine severity level based on function metrics.
        
        Args:
            smell_name: Name of the smell
            func: Function dictionary with metrics
        
        Returns:
            Severity level: critical, high, medium, or low
        """
        smell = self.smells.get(smell_name)
        if not smell:
            return "unknown"
        
        severity_levels = smell.get("severity_levels", {})
        
        if severity_levels.get("critical", lambda x: False)(func):
            return "critical"
        elif severity_levels.get("high", lambda x: False)(func):
            return "high"
        elif severity_levels.get("medium", lambda x: False)(func):
            return "medium"
        else:
            return "low"
    
    def reload(self) -> bool:
        """Reload DACOS data."""
        if self.dacos_folder and self.dacos_folder != "SKIP":
            return self._initialize_dacos()
        return False


# For backward compatibility
DACOS_KNOWLEDGE = DACOSKnowledgeBase().get_all_smells()