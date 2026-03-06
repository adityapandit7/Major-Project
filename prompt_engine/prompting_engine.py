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

from core.context_builder import retrieve_context
print("✅ Prompting Engine module loaded") 

class PromptingEngine:
    """
    Prompting Engine with DACOS integration for accurate smell detection.
    Works with RepoState abstraction and Hybrid Retrieval.
    """

    def __init__(
        self,
        model_type: str = "codet5p-770m",
        dacos_folder: Optional[str] = None
    ):

        self.model_type = model_type
        self.dacos_folder = dacos_folder

        self.smell_detector = SmellDetector(dacos_folder)
        self.knowledge = DACOSKnowledgeBase(dacos_folder)

        if dacos_folder and self.knowledge.initialized:
            print(f"✅ Prompting Engine initialized with DACOS from: {dacos_folder}")
        else:
            print("✅ Prompting Engine initialized (using default thresholds)")

    # ----------------------------------------------------------
    # Smell Context Builder
    # ----------------------------------------------------------

    def _build_smell_context(self, smells: List[Dict]) -> str:
        print("✅ smell context Engine module loaded") 
        if not smells:
            return "No major code smells detected."

        context_blocks = ["🔍 DETECTED CODE SMELLS\n"]

        for smell in smells:

            block = f"""
### {smell['name']} ({smell['severity'].upper()})

Issue:
{smell['description']}

Location:
{smell['location']}

Metrics
LOC: {smell['metrics']['loc']}
Parameters: {smell['metrics']['param_count']}
Responsibilities: {smell['metrics']['responsibility_count']}
Nesting Depth: {smell['metrics']['nesting_depth']}

Suggested Fix:
{smell['refactor_guidance']}
"""
            context_blocks.append(block)

        return "\n".join(context_blocks)

    # ----------------------------------------------------------
    # Prompt Generation
    # ----------------------------------------------------------

    def _build_query(self, repo_state, smells):

        tokens = []

        if smells:
            tokens.append(smells[0]["name"])

        if repo_state.functions:
            tokens.append(repo_state.functions[0].name)

        tokens.append("refactor")
        tokens.append("function")

        return " ".join(tokens)

    def generate_prompts(
        self,
        repo_state,
        hybrid_retriever=None,
        query: str = "",
        user_request: str = "both"
    ) -> dict:

        raw_code = repo_state.raw_code
        functions = repo_state.functions
        classes = repo_state.classes
        if hybrid_retriever:

            if not query:
                query = self._build_query(repo_state, smells)

            print("\nDEBUG --- Hybrid Retrieval Query")
            print(query)

            context = retrieve_context(hybrid_retriever, query)

            print("DEBUG --- Context Length:", len(context))

        # ---------------------------
        # Retrieval Context
        # ---------------------------

        retrieved_context = ""
        print(f"✅ Prompting Engine: Starting retrieval context generation (length: {len(retrieved_context)})")
        if hybrid_retriever and query:
            try:
                retrieved_context = retrieve_context(
                    hybrid_retriever,
                    query
                )
                print(f"✅ Prompting Engine: Retrieved context (length: {len(retrieved_context)})")
            except Exception:
                retrieved_context = ""

        prompts = {

            "refactor_prompt": None,
            "documentation_prompt": None,

            "metadata": {

                "dacos_initialized": self.knowledge.initialized,
                "dacos_folder": self.dacos_folder,

                "function_count": len(functions),
                "class_count": len(classes),

                "smells_detected": []
            }
        }
        print(f"=========================================================================\nDEBUG --- Retrieval Query: {query}")
        
        # ---------------------------
        # Detect smells
        # ---------------------------

        smells = self.smell_detector.detect_smells(repo_state)
        if not query:
            query = self._build_query(repo_state, smells)       

        prompts["metadata"]["smells_detected"] = {
            "count": len(smells),
            "summary": [
                {"name": s["name"], "severity": s["severity"]}
                for s in smells
            ],
            "details": smells
        }

        # ------------------------------------------------------
        # Refactor Prompt
        # ------------------------------------------------------

        if user_request in ["refactor", "both"]:

            smell_context = self._build_smell_context(smells)

            dacos_context = self.knowledge.get_dacos_context()

            # single smell template
            if len(smells) == 1:

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

                prompts["refactor_prompt"] = REFACTOR_BASE_TEMPLATE.format(

                    SMELL_CONTEXT=smell_context,

                    RETRIEVED_CONTEXT=retrieved_context,

                    DACOS_CONTEXT=dacos_context,

                    CODE=raw_code.strip()
                )

            if self.model_type == "codet5p-770m":

                prompts["refactor_prompt"] = optimize_template_for_codet5p(
                    prompts["refactor_prompt"]
                )

        # ------------------------------------------------------
        # Documentation Prompt
        # ------------------------------------------------------

        if user_request in ["document", "both"]:

            if functions:

                func_lines = ["Functions detected:\n"]

                for f in functions:
                    func_lines.append(
                        f"- {f.name} ({len(f.params)} parameters)"
                    )

                func_context = "\n".join(func_lines)

            else:
                func_context = "No functions detected."

            prompts["documentation_prompt"] = DOCUMENTATION_BASE_TEMPLATE.format(
                CODE=raw_code.strip(),
                FUNCTIONS=func_context
            )

        return prompts

    # ----------------------------------------------------------
    # Refactoring Plan
    # ----------------------------------------------------------

    def generate_refactoring_plan(self, repo_state) -> str:

        smells = self.smell_detector.get_refactoring_priority(repo_state)

        if not smells:
            return "✅ Code looks clean. No refactoring needed."

        plan = []

        plan.append("REFACTORING PLAN")
        plan.append("=" * 40)

        step = 1

        for smell in smells:

            plan.append(
                f"{step}. {smell['name']} in {smell['location']}"
            )

            plan.append(
                f"   Fix: {smell['refactor_guidance']}"
            )

            step += 1

        plan.append("")
        plan.append("Refactoring Tips")
        plan.append("• Test after each change")
        plan.append("• Commit changes incrementally")

        return "\n".join(plan)

    # ----------------------------------------------------------
    # Save Prompts
    # ----------------------------------------------------------

    def save_prompts(self, prompts: dict, base_filename: str = "prompt"):

        if prompts["refactor_prompt"]:

            with open(
                f"{base_filename}_refactor.txt",
                "w",
                encoding="utf-8"
            ) as f:

                f.write(prompts["refactor_prompt"])

        if prompts["documentation_prompt"]:

            with open(
                f"{base_filename}_documentation.txt",
                "w",
                encoding="utf-8"
            ) as f:

                f.write(prompts["documentation_prompt"])

        with open(
            f"{base_filename}_metadata.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(prompts["metadata"], f, indent=2)
    
    