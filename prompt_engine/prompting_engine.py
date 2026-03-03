from .templates import (
    REFACTOR_BASE_TEMPLATE,
    DOCUMENTATION_BASE_TEMPLATE,
    get_template_for_smell,
    optimize_template_for_codet5p
)
from .smell_detector import SmellDetector
from .dacos_knowledge import DACOSKnowledgeBase
from typing import Dict, Optional, List
import json

class PromptingEngine:
    """
    Prompting Engine with DACOS integration for accurate smell detection.
    """
    
    def __init__(self, 
                 model_type: str = "codet5p-770m",
                 dacos_folder: Optional[str] = None):
        """
        Initialize the Prompting Engine.
        
        Args:
            model_type: Type of model to optimize prompts for (default: "codet5p-770m")
            dacos_folder: Path to DACOS dataset folder (optional)
        """
        self.model_type = model_type
        self.dacos_folder = dacos_folder
        self.smell_detector = SmellDetector(dacos_folder)
        self.knowledge = DACOSKnowledgeBase(dacos_folder)
        
        if dacos_folder and self.knowledge.initialized:
            print(f"✅ Prompting Engine initialized with DACOS from: {dacos_folder}")
        else:
            print("✅ Prompting Engine initialized (using default thresholds)")
    
    def _build_smell_context(self, smells: List[Dict]) -> str:
        """Build detailed smell context for prompts."""
        if not smells:
            return "No major code smells detected. Focus on general code quality improvements."
        
        context_blocks = ["🔍 **DETECTED CODE SMELLS**", ""]
        
        for smell in smells:
            block = f"""
### {smell['name']} ({smell['severity'].upper()} Priority)

**Issue:** {smell['description']}

**Location:** {smell['location']}

**Current Metrics:**
- Lines of Code: {smell['metrics']['loc']}
- Parameters: {smell['metrics']['param_count']}
- Responsibilities: {smell['metrics']['responsibility_count']}
- Nesting Depth: {smell['metrics']['nesting_depth']}

**Threshold Information:**
- Detection threshold: {smell.get('threshold', 'N/A')}
- Current value: {smell.get('current_value', 'N/A')}

**Recommended Refactoring:**
{smell['refactor_guidance']}
"""
            context_blocks.append(block)
        
        return "\n".join(context_blocks)
    
    def generate_prompts(
        self,
        raw_code: str,
        parsed_code: dict,
        user_request: str = "both"
    ) -> dict:
        """
        Generates prompts with DACOS context.
        
        Args:
            raw_code: Original source code
            parsed_code: AST-parsed code structure
            user_request: 'refactor', 'document', or 'both'
        
        Returns:
            Dictionary with generated prompts
        """
        prompts = {
            "refactor_prompt": None,
            "documentation_prompt": None,
            "metadata": {
                "dacos_initialized": self.knowledge.initialized,
                "dacos_folder": self.dacos_folder,
                "smells_detected": [],
                "function_count": len(parsed_code.get("functions", [])),
                "class_count": len(parsed_code.get("classes", []))
            }
        }
        
        # Detect smells
        smells = self.smell_detector.detect_smells(parsed_code)
        prompts["metadata"]["smells_detected"] = {
            "count": len(smells),
            "summary": [{"name": s["name"], "severity": s["severity"]} for s in smells],
            "details": smells  # Full details for advanced use
        }
        
        # Generate Refactoring Prompt
        if user_request in ["refactor", "both"]:
            smell_context = self._build_smell_context(smells)
            
            # Add DACOS context if available
            dacos_context = self.knowledge.get_dacos_context()
            
            # Check if we should use smell-specific template
            if len(smells) == 1:
                # Use specific template for single smell
                template = get_template_for_smell(
                    smells[0]["name"], 
                    raw_code.strip(),
                    {
                        "LOC": smells[0]["metrics"]["loc"],
                        "PARAM_COUNT": smells[0]["metrics"]["param_count"]
                    }
                )
                prompts["refactor_prompt"] = template
            else:
                # Use base template with context
                prompts["refactor_prompt"] = REFACTOR_BASE_TEMPLATE.format(
                    SMELL_CONTEXT=smell_context,
                    DACOS_CONTEXT=dacos_context,
                    CODE=raw_code.strip()
                )
            
            # Optimize for CodeT5p if needed
            if self.model_type == "codet5p-770m":
                prompts["refactor_prompt"] = optimize_template_for_codet5p(
                    prompts["refactor_prompt"]
                )
        
        # Generate Documentation Prompt
        if user_request in ["document", "both"]:
            # Add function list to documentation prompt
            functions = parsed_code.get("functions", [])
            if functions:
                func_list = ["**Functions in this code:**"]
                for f in functions:
                    func_list.append(f"- `{f['name']}`: {f['loc']} lines, {f['param_count']} parameters")
                func_context = "\n".join(func_list)
            else:
                func_context = "No functions detected in this code."
            
            prompts["documentation_prompt"] = DOCUMENTATION_BASE_TEMPLATE.format(
                CODE=raw_code.strip(),
                FUNCTIONS=func_context
            )
        
        return prompts
    
    def generate_refactoring_plan(self, parsed_code: dict) -> str:
        """Generate a step-by-step refactoring plan based on detected smells."""
        smells = self.smell_detector.get_refactoring_priority(parsed_code)
        
        if not smells:
            return "✅ Code looks clean! No refactoring needed at this time."
        
        plan = []
        plan.append("📋 **REFACTORING PLAN**")
        plan.append("="*40)
        plan.append("")
        
        # Group by severity
        critical = [s for s in smells if s["severity"] == "critical"]
        high = [s for s in smells if s["severity"] == "high"]
        medium = [s for s in smells if s["severity"] == "medium"]
        
        step = 1
        
        if critical:
            plan.append(f"**CRITICAL PRIORITY (Fix these first):**")
            for smell in critical:
                plan.append(f"{step}. {smell['name']} in {smell['location']}")
                plan.append(f"   → {smell['refactor_guidance']}")
                step += 1
            plan.append("")
        
        if high:
            plan.append(f"**HIGH PRIORITY:**")
            for smell in high:
                plan.append(f"{step}. {smell['name']} in {smell['location']}")
                plan.append(f"   → {smell['refactor_guidance']}")
                step += 1
            plan.append("")
        
        if medium:
            plan.append(f"**MEDIUM PRIORITY:**")
            for smell in medium:
                plan.append(f"{step}. {smell['name']} in {smell['location']}")
                plan.append(f"   → {smell['refactor_guidance']}")
                step += 1
        
        plan.append("")
        plan.append("**Refactoring Tips:**")
        plan.append("• Test after each change")
        plan.append("• Run tests to ensure functionality preserved")
        plan.append("• Commit changes incrementally")
        
        return "\n".join(plan)
    
    def save_prompts(self, prompts: dict, base_filename: str = "prompt"):
        """Save prompts to files."""
        if prompts["refactor_prompt"]:
            with open(f"{base_filename}_refactor.txt", "w", encoding='utf-8') as f:
                f.write(prompts["refactor_prompt"])
        
        if prompts["documentation_prompt"]:
            with open(f"{base_filename}_documentation.txt", "w", encoding='utf-8') as f:
                f.write(prompts["documentation_prompt"])
        
        with open(f"{base_filename}_metadata.json", "w", encoding='utf-8') as f:
            json.dump(prompts["metadata"], f, indent=2)