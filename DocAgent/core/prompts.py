from graph.state import RepoState


def build_prompt(state: RepoState) -> str:
    """
    Build a documentation prompt from RepoState.

    IMPORTANT:
    - RepoState is NOT a dict.
    - All access must be via explicit attributes.
    """

    assert isinstance(state, RepoState), "build_prompt expects RepoState"

    class_names = [cls.name for cls in state.classes]
    function_names = [fn.name for fn in state.functions]

    return (
        "DOCUMENT THE FOLLOWING CODE\n\n"
        f"Classes ({len(class_names)}): {class_names}\n"
        f"Functions ({len(function_names)}): {function_names}\n\n"
        "Raw Code:\n"
        f"{state.raw_code}\n"
    )


def generate_docs(prompt: str) -> str:
    """
    Placeholder documentation generator.
    This will later be replaced by an LLM call.
    """

    return (
        "## Auto-Generated Documentation\n\n"
        f"{prompt}\n"
        "This documentation was generated using filler logic."
    )
