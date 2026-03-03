# ==========================================================
# BASE TEMPLATES
# ==========================================================

REFACTOR_BASE_TEMPLATE = """
You are a senior software engineer specializing in clean code and refactoring.

TASK:
Refactor the following Python code to improve its quality based on detected code smells.

{DACOS_CONTEXT}

{SMELL_CONTEXT}

CODE TO REFACTOR:
{CODE}

REFACTORING REQUIREMENTS:
- Preserve ALL original functionality
- Do NOT change behavior
- Follow clean code principles and PEP 8
- Use descriptive names
- Keep single responsibility
- Add comments for complex logic

Return ONLY the refactored code.
"""

DOCUMENTATION_BASE_TEMPLATE = """
You are a technical documentation expert.

TASK:
Generate comprehensive documentation for the following Python code.

CODE:
{CODE}

FUNCTIONS:
{FUNCTIONS}

DOCUMENTATION GUIDELINES:
- Overview: What does this module do?
- Functions:
    - Purpose
    - Parameters (name, type, description)
    - Return value
    - Exceptions
- Usage Examples
- Notes

Generate professional documentation in Markdown format.
"""

# ==========================================================
# SMELL-SPECIFIC TEMPLATES
# ==========================================================

LONG_METHOD_TEMPLATE = """
You are refactoring a long method.

ORIGINAL CODE ({LOC} lines):
{CODE}

GOAL:
Break this long method into smaller focused methods.

REFACTORING STEPS:
- Identify logical blocks
- Extract helper functions
- Use descriptive names
- Keep main function clean

Return ONLY the refactored code.
"""

LONG_PARAMETER_LIST_TEMPLATE = """
You are refactoring a method with too many parameters.

ORIGINAL CODE ({PARAM_COUNT} parameters):
{CODE}

GOAL:
Reduce parameter count using:
- Parameter Object Pattern
- Configuration objects
- Group related data

Return ONLY the refactored code.
"""

COMPLEX_CONDITIONAL_TEMPLATE = """
You are refactoring a method with complex conditional logic.

ORIGINAL CODE:
{CODE}

GOAL:
Simplify conditionals using:
- Guard clauses
- Extract condition
- Reduce nesting

Return ONLY the refactored code.
"""

MULTIFACETED_ABSTRACTION_TEMPLATE = """
You are refactoring a function with multiple responsibilities.

ORIGINAL CODE:
{CODE}

GOAL:
Apply Single Responsibility Principle.
Split logic into smaller focused functions.

Return ONLY the refactored code.
"""

# ==========================================================
# TEMPLATE COLLECTION
# ==========================================================

SMELL_SPECIFIC_TEMPLATES = {
    "Long Method": LONG_METHOD_TEMPLATE,
    "Long Parameter List": LONG_PARAMETER_LIST_TEMPLATE,
    "Complex Conditional": COMPLEX_CONDITIONAL_TEMPLATE,
    "Multifaceted Abstraction": MULTIFACETED_ABSTRACTION_TEMPLATE,
}

# ==========================================================
# TEMPLATE SELECTOR
# ==========================================================

def get_template_for_smell(smell_name: str, code: str, metrics: dict = None) -> str:
    """
    Get appropriate template for a detected smell.
    """
    template = SMELL_SPECIFIC_TEMPLATES.get(smell_name, REFACTOR_BASE_TEMPLATE)

    variables = {
        "CODE": code,
        "DACOS_CONTEXT": "",
        "SMELL_CONTEXT": f"Detected smell: {smell_name}"
    }

    if metrics:
        variables.update(metrics)

    try:
        return template.format(**variables)
    except KeyError as e:
        print(f"[Template Warning] Formatting error for {smell_name}: {e}")
        return REFACTOR_BASE_TEMPLATE.format(**variables)

# ==========================================================
# CODET5P OPTIMIZATION
# ==========================================================

def optimize_template_for_codet5p(template: str) -> str:
    """
    Optimize template for CodeT5p-770m.
    Removes markdown formatting but preserves ALL content.
    NO TRUNCATION - full code is kept.
    """
    # Remove markdown-style code block indicators
    optimized = template.replace("```", "").replace("python", "")

    # Remove extra blank lines (optional)
    lines = [line for line in optimized.split("\n") if line.strip() or not line]
    optimized = "\n".join(lines)

    # Return full content, no truncation
    return optimized