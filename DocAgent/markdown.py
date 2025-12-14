"""
Markdown Formatter
==================

Utility functions and a MarkdownBuilder for converting structured LLM-generated
documentation data into clean, readable Markdown.
"""

import re
from typing import Dict, List, Optional


# ============================================================================
# Basic Formatting Helpers
# ============================================================================

def normalize_blank_lines(text: str) -> str:
    """
    Collapse multiple blank lines and trim surrounding whitespace.

    Parameters
    ----------
    text : str
        Input markdown text.

    Returns
    -------
    str
        Cleaned markdown text.
    """
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip() + "\n"


def indent_bullets(lines: List[str], level: int = 0) -> str:
    """
    Apply indentation to bullet list items.

    Parameters
    ----------
    lines : list of str
        Each bullet line.
    level : int, optional
        Indentation level.

    Returns
    -------
    str
        Markdown formatted bullet list.
    """
    prefix = "  " * level
    return "\n".join(f"{prefix}- {line}" for line in lines)


def code_block(code: str, lang: str = "python") -> str:
    """
    Wrap code inside fenced Markdown code block.

    Parameters
    ----------
    code : str
        Code content.
    lang : str, optional
        Syntax highlighter tag.

    Returns
    -------
    str
        Markdown code block.
    """
    code = code.strip("\n")
    return f"```{lang}\n{code}\n```"


# ============================================================================
# High-Level Block Formatting
# ============================================================================

def format_header(title: str, level: int = 1) -> str:
    """
    Format a Markdown header.

    Parameters
    ----------
    title : str
        Header text.
    level : int, optional
        Markdown header level.

    Returns
    -------
    str
        Markdown header string.
    """
    return f"{'#' * level} {title}\n"


def format_class_block(class_info: Dict) -> str:
    """
    Format a class documentation block.

    Parameters
    ----------
    class_info : dict
        Should contain:
        - name : str
        - bases : list of str
        - docstring : str or None
        - methods : list of method dicts

    Returns
    -------
    str
        Markdown formatted class section.
    """
    name = class_info.get("name", "UnknownClass")
    bases = class_info.get("bases", [])
    doc = class_info.get("docstring", "")
    methods = class_info.get("methods", [])

    header = format_header(f"class {name}", level=2)

    base_line = ""
    if bases:
        base_line = f"**Bases:** {', '.join(bases)}\n\n"

    doc_block = f"{doc.strip()}\n\n" if doc else ""

    method_blocks = []
    for m in methods:
        method_blocks.append(format_function_block(m, level=3))

    return header + base_line + doc_block + "\n".join(method_blocks) + "\n"


def format_function_block(fn_info: Dict, level: int = 2) -> str:
    """
    Format a function or method block.

    Parameters
    ----------
    fn_info : dict
        Should contain:
        - name : str
        - signature : str
        - docstring : str or None

    level : int, optional
        Markdown header level.

    Returns
    -------
    str
        Markdown formatted function block.
    """
    name = fn_info.get("name", "unknown_function")
    signature = fn_info.get("signature", f"{name}()")
    doc = fn_info.get("docstring", "")

    header = format_header(signature, level=level)
    doc_block = f"{doc.strip()}\n\n" if doc else ""

    return header + doc_block


def format_section(name: str, content: str) -> str:
    """
    Format a named documentation section.

    Parameters
    ----------
    name : str
        Section title.
    content : str
        Body content.

    Returns
    -------
    str
        Markdown formatted section.
    """
    return format_header(name, level=2) + content.strip() + "\n\n"


# ============================================================================
# Final Markdown Cleaner
# ============================================================================

def to_markdown(text: str) -> str:
    """
    Clean and normalize markdown produced by LLMs.

    Parameters
    ----------
    text : str
        Raw LLM output.

    Returns
    -------
    str
        Markdown with normalized spacing and no redundant blank lines.
    """
    if not isinstance(text, str):
        return ""

    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = text.replace("\r\n", "\n")
    text = normalize_blank_lines(text)
    return text


# ============================================================================
# MarkdownBuilder Class
# ============================================================================

class MarkdownBuilder:
    """
    Incremental Markdown document builder for RepoAgent and DocAgent.

    Notes
    -----
    This class stores ordered blocks of Markdown and composes them into
    a final cleaned document at the end. All blocks are automatically
    normalized using `to_markdown`.
    """

    def __init__(self):
        self.blocks: List[str] = []

    # --------------------------
    # Header API
    # --------------------------
    def add_header(self, title: str, level: int = 1):
        """
        Add a markdown header.

        Parameters
        ----------
        title : str
            Header text.
        level : int, optional
            Markdown level (1–6).
        """
        self.blocks.append(format_header(title, level))

    # --------------------------
    # Section API
    # --------------------------
    def add_section(self, name: str, content: str):
        """
        Add a named documentation section.

        Parameters
        ----------
        name : str
            Section title.
        content : str
            Section body.
        """
        self.blocks.append(format_section(name, content))

    # --------------------------
    # Class Documentation API
    # --------------------------
    def add_class(self, class_info: Dict):
        """
        Add a formatted class documentation block.

        Parameters
        ----------
        class_info : dict
            Parsed class information.
        """
        self.blocks.append(format_class_block(class_info))

    # --------------------------
    # Function Documentation API
    # --------------------------
    def add_function(self, fn_info: Dict, level: int = 2):
        """
        Add a formatted function documentation block.

        Parameters
        ----------
        fn_info : dict
            Parsed function information.
        level : int, optional
            Markdown header level.
        """
        self.blocks.append(format_function_block(fn_info, level=level))

    # --------------------------
    # Code Block API
    # --------------------------
    def add_code_block(self, code: str, lang: str = "python"):
        """
        Add a fenced code block.

        Parameters
        ----------
        code : str
            Code body.
        lang : str, optional
            Language tag.
        """
        self.blocks.append(code_block(code, lang) + "\n\n")

    # --------------------------
    # Raw Markdown API
    # --------------------------
    def add_raw(self, markdown: str):
        """
        Add arbitrary markdown text.

        Parameters
        ----------
        markdown : str
            Any markdown string.
        """
        self.blocks.append(markdown.strip() + "\n\n")

    # --------------------------
    # Final Assembly
    # --------------------------
    def build(self) -> str:
        """
        Construct the final markdown document.

        Returns
        -------
        str
            Fully assembled and normalized markdown.
        """
        combined = "\n".join(self.blocks)
        return to_markdown(combined)
