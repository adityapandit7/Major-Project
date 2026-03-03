"""
core/prompts.py
Prompt Engine for RepoAgent + DocAgent

This module defines:
1. Code Smell Awareness Layer
2. Context Extraction Layer
3. NumPy-Enforced Documentation Layer
4. Final Documentation Template
5. PromptEngine class
6. build_prompt(parsed) helper

Used by:
- RepoAgent (analysis of repository code)
- DocAgent (documentation generation)
"""

# ------------------------------------------------------------
# 1. CODE SMELL AWARENESS LAYER
# ------------------------------------------------------------

CODE_SMELL_LAYER = """
You are an expert static analysis engine.

Analyze the code for:
- Code smells
- Anti-patterns
- Logical risks
- Naming issues
- Missing error handling
- Repeated or unnecessarily complex logic
- Potential bugs
- Violations of Python best practices

Rules:
- Extract only insights that help an LLM understand the code.
- Do not generate documentation.
- Do not propose fixes.
- Do not rewrite the code.
"""


# ------------------------------------------------------------
# 2. CONTEXT EXTRACTION LAYER
# ------------------------------------------------------------

CONTEXT_EXTRACTION_LAYER = """
You are an expert software analyst.

Your task is to extract accurate structural meaning from the code, including:
- Classes and their roles
- Methods and their parameters and returns
- Functions and their parameters and returns
- Relationships between components
- High-level module purpose
- Data flow

Rules:
- Use only information present in the raw code.
- Do not guess functionality or behavior.
- If uncertain, say 'Unknown'.
- Output should be factual, structured, and precise.
- Do not generate documentation at this stage.
"""


# ------------------------------------------------------------
# 3. HIGH-LEVEL DOCUMENTATION LAYER (NUMPY-STYLE)
# ------------------------------------------------------------

DOC_AGENT_LAYER = """
You are an expert technical writer specializing in NumPy-style documentation.

Generate documentation that strictly follows the NumPy docstring standard.

NumPy Docstring Structure:

1. Short summary line.

2. Parameters section:
Parameters
----------
param_name : type
    Description.

3. Returns section (only if applicable):
Returns
-------
return_type
    Description.

4. Notes section:
Notes
-----
Additional details, edge cases, assumptions, or constraints.

5. Examples section (optional):
Examples
--------
Usage examples if meaningful.

Strict rules:
- Do not invent parameters or return types.
- Do not add behaviors not present in the code.
- If type cannot be inferred, use 'Unknown'.
- If behavior is unclear, explicitly state:
  'Behavior cannot be determined from the available code.'
- Apply NumPy format to both functions and class methods.
- Each class should also include a high-level summary and Notes section.

Your output must follow the NumPy format exactly.
"""


# ------------------------------------------------------------
# 4. FINAL DOCUMENTATION TEMPLATE
# ------------------------------------------------------------

DOC_TEMPLATE = """
You are an expert documentation generator.

Use ONLY the metadata extracted from the parser and the raw code.
Do not hallucinate parameters, behavior, or return values.

====================
Code Summary
====================
{summary}

====================
Classes
====================
{classes}

====================
Functions
====================
{functions}

====================
Raw Code
====================
{code}

Instructions:
- Generate final NumPy-style documentation.
- Follow the NumPy docstring standard strictly.
- Use only information present in the code and metadata.
- If types or behaviors are unclear, write 'Unknown'.
- If something cannot be determined, explicitly state it.
"""


# ------------------------------------------------------------
# 5. PROMPT ENGINE
# ------------------------------------------------------------

class PromptEngine:
    """
    Helper for assembling prompts for RepoAgent and DocAgent.

    RepoAgent:
        - Uses code_smell_prompt()
        - Uses context_prompt()

    DocAgent:
        - Uses documentation_prompt()
        - Or full_pipeline_prompt()
    """

    @staticmethod
    def code_smell_prompt(code: str) -> str:
        """Build prompt for code smell analysis."""
        return f"{CODE_SMELL_LAYER}\n\n### Code\n{code}"

    @staticmethod
    def context_prompt(code: str) -> str:
        """Build prompt for context extraction."""
        return f"{CONTEXT_EXTRACTION_LAYER}\n\n### Code\n{code}"

    @staticmethod
    def documentation_prompt(summary: str, classes: str, functions: str, code: str) -> str:
        """Build final NumPy-style documentation prompt."""
        return DOC_TEMPLATE.format(
            summary=summary,
            classes=classes,
            functions=functions,
            code=code
        )

    @staticmethod
    def full_pipeline_prompt(code: str) -> str:
        """
        Full prompt for DocAgent performing all stages:
        - Code Smell Analysis
        - Context Extraction
        - Documentation Generation
        """
        return f"""
{CODE_SMELL_LAYER}

{CONTEXT_EXTRACTION_LAYER}

{DOC_AGENT_LAYER}

### Raw Code
{code}
"""


# ------------------------------------------------------------
# 6. build_prompt(parsed)
# ------------------------------------------------------------

def build_prompt(parsed):
    """
    Build final documentation prompt using parser output.

    Parameters
    ----------
    parsed : dict
        Expected format:
        {
            "summary": str,
            "classes": list | str,
            "functions": list | str,
            "raw": str
        }

    Returns
    -------
    str
        A fully assembled, NumPy-enforced documentation prompt.
    """

    # Extract fields safely
    summary = parsed.get("summary", "No summary available.")

    classes = parsed.get("classes", [])
    if isinstance(classes, list):
        classes = "\n".join(str(c) for c in classes)

    functions = parsed.get("functions", [])
    if isinstance(functions, list):
        functions = "\n".join(str(f) for f in functions)

    raw_code = parsed.get("raw", "")

    # Use PromptEngine to format the final documentation prompt
    return PromptEngine.documentation_prompt(
        summary=summary,
        classes=classes,
        functions=functions,
        code=raw_code
    )


# END OF FILE
