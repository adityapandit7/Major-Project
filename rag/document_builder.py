from typing import List, Dict

def build_documents(repo_state) -> List[Dict]:

    documents = []

    # Functions
    for f in repo_state.functions:

        content = f"""
Function: {f.name}
Parameters: {", ".join(f.params)}

Docstring:
{f.docstring or "None"}
"""

        documents.append({
            "id": f.name,
            "type": "function",
            "symbol": f.name,
            "content": content.strip(),
            "metadata": {
                "kind": "function",
                "params": f.params,
                "param_count": len(f.params)
            }
        })

    # Classes
    for c in repo_state.classes:

        methods = [m.name for m in c.methods]

        content = f"""
Class: {c.name}

Methods:
{", ".join(methods)}

Docstring:
{c.docstring or "None"}
"""

        documents.append({
            "id": c.name,
            "type": "class",
            "symbol": c.name,
            "content": content.strip(),
            "metadata": {
                "kind": "class",
                "method_count": len(methods),
                "methods": methods
            }
        })

    return documents