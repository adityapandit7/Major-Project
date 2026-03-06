def build_symbol_index(repo_state):
    """
    Build a lookup table for repository symbols.
    """

    index = {}

    for f in repo_state.functions:
        index[f.name.lower()] = {
            "type": "function",
            "symbol": f.name,
            "content": f"{f.name}({', '.join(f.params)})"
        }

    for c in repo_state.classes:
        index[c.name.lower()] = {
            "type": "class",
            "symbol": c.name,
            "content": f"class {c.name}"
        }

    return index