"""
core/qa.py — Quality Checking Layer

Validates:
- Completeness of documentation
- Consistency with parsed code
- Potential fixes and improvements
"""

import re
from typing import Dict, List


# ---------------------------------------------------------------------------
# 1. COMPLETENESS CHECK
# ---------------------------------------------------------------------------

def check_completeness(parsed: dict, generated_docs: str) -> Dict[str, List[str]]:
    """
    Check if every function/class is documented and parameters are referenced.

    Parameters
    ----------
    parsed : dict
        Output from parser.py

    generated_docs : str
        Final markdown documentation string

    Returns
    -------
    dict
        {
            "missing_function_docs": [...],
            "missing_param_mentions": [...],
            "empty_sections": [...]
        }
    """
    issues = {
        "missing_function_docs": [],
        "missing_param_mentions": [],
        "empty_sections": []
    }

    # --------------------------------------------
    # Detect missing function documentation
    # --------------------------------------------
    for fn in parsed.get("functions", []):
        fn_name = fn["name"]
        if fn_name not in generated_docs:
            issues["missing_function_docs"].append(fn_name)

    # --------------------------------------------
    # Detect if parameters appear in documentation
    # --------------------------------------------
    for fn in parsed.get("functions", []):
        fn_name = fn["name"]
        for arg in fn.get("args", []):
            if arg not in generated_docs:
                issues["missing_param_mentions"].append(f"{fn_name}.{arg}")

    # --------------------------------------------
    # Detect empty sections like:
    # ## Classes\n\n(No content)
    # --------------------------------------------
    empty_section_pattern = r"##\s+[A-Za-z ]+\n+?(?=##|$)"
    sections = re.findall(empty_section_pattern, generated_docs)

    for s in sections:
        # If section only contains the header but no body text/code
        header, *body = s.split("\n", 1)
        if len(body) == 0 or body[0].strip() == "":
            issues["empty_sections"].append(header.replace("#", "").strip())

    return issues


# ---------------------------------------------------------------------------
# 2. CONSISTENCY CHECK
# ---------------------------------------------------------------------------

def check_consistency(parsed: dict, generated_docs: str) -> Dict[str, List[str]]:
    """
    Ensure documentation does not hallucinate functions/classes
    or omit actual parsed definitions.

    Parameters
    ----------
    parsed : dict
    generated_docs : str

    Returns
    -------
    dict
        {
            "hallucinated_functions": [...],
            "hallucinated_classes": [...],
            "missing_methods": [...]
        }
    """
    issues = {
        "hallucinated_functions": [],
        "hallucinated_classes": [],
        "missing_methods": [],
    }

    # Helper: find identifiers referenced in docs
    documented_funcs = re.findall(r"###\s+([A-Za-z_][A-Za-z0-9_]*)", generated_docs)
    documented_classes = re.findall(r"###\s+([A-Za-z_][A-Za-z0-9_]*)", generated_docs)

    # --------------------------------------------
    # Hallucinated functions (appear in docs but not parsed)
    # --------------------------------------------
    parsed_funcs = {fn["name"] for fn in parsed.get("functions", [])}
    for fn in documented_funcs:
        if fn not in parsed_funcs:
            issues["hallucinated_functions"].append(fn)

    # --------------------------------------------
    # Hallucinated classes
    # --------------------------------------------
    parsed_classes = {cls["name"] for cls in parsed.get("classes", [])}
    for cls in documented_classes:
        if cls not in parsed_classes:
            issues["hallucinated_classes"].append(cls)

    # --------------------------------------------
    # Missing methods inside classes
    # --------------------------------------------
    for cls in parsed.get("classes", []):
        class_name = cls["name"]
        if class_name not in generated_docs:
            continue  # class itself missing, captured above

        for m in cls.get("methods", []):
            if m["name"] not in generated_docs:
                issues["missing_methods"].append(f"{class_name}.{m['name']}")

    return issues


# ---------------------------------------------------------------------------
# 3. FIX SUGGESTION ENGINE
# ---------------------------------------------------------------------------

def suggest_fixes(parsed: dict = None, qa_results: dict = None, generated_docs: str = "") -> List[str]:
    """
    Suggest improvements based on detected QA issues.

    Parameters
    ----------
    parsed : dict
        Parsed code structure

    qa_results : dict
        Combined results of check_completeness + check_consistency

    generated_docs : str
        The documentation text

    Returns
    -------
    list of str
        Suggestions for improving documentation
    """

    suggestions = []

    # Missing documentation
    if qa_results.get("missing_function_docs"):
        for fn in qa_results["missing_function_docs"]:
            suggestions.append(f"Add documentation for function `{fn}`.")

    # Missing parameters
    if qa_results.get("missing_param_mentions"):
        for pair in qa_results["missing_param_mentions"]:
            fn, param = pair.split(".")
            suggestions.append(f"Document parameter `{param}` in function `{fn}`.")

    # Hallucinations
    if qa_results.get("hallucinated_functions"):
        for fn in qa_results["hallucinated_functions"]:
            suggestions.append(f"Remove hallucinated function `{fn}` from documentation.")

    if qa_results.get("hallucinated_classes"):
        for cls in qa_results["hallucinated_classes"]:
            suggestions.append(f"Documentation references non-existent class `{cls}`.")

    # Missing methods
    if qa_results.get("missing_methods"):
        for m in qa_results["missing_methods"]:
            suggestions.append(f"Add missing method `{m}` to class documentation.")

    # General improvements
    # --------------------------------------------
    # Suggest missing return types (simple heuristic)
    # --------------------------------------------
    return_candidates = re.findall(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\(", generated_docs)
    for fn in return_candidates:
        if "return" not in generated_docs:
            suggestions.append(f"Consider specifying the return value for `{fn}`.")

    # Suggest clearer writing
    unclear_patterns = ["TODO", "not sure", "???", "fix later"]
    for p in unclear_patterns:
        if p.lower() in generated_docs.lower():
            suggestions.append("Some wording appears unclear; revise for clarity.")

    # Detect duplicate sections
    headers = re.findall(r"(##\s+[A-Za-z ]+)", generated_docs)
    seen = set()
    for h in headers:
        if h in seen:
            suggestions.append(f"Duplicate section detected: `{h.strip()}`.")
        seen.add(h)

    return suggestions
