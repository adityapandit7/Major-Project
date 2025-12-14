import ast
from typing import List, Dict, Any, Optional


def _safe_unparse(node: ast.AST) -> str:
    """Return a best-effort name/string for an AST node (uses ast.unparse if available)."""
    try:
        return ast.unparse(node)
    except Exception:
        # Fallbacks for common node types
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            value = _safe_unparse(node.value)
            return f"{value}.{node.attr}"
        return type(node).__name__


def assign_parents(tree: ast.AST) -> None:
    """Assign .parent to every node to help detect contexts (methods vs functions)."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def _extract_param_names(fn: ast.FunctionDef) -> List[str]:
    params = []
    # positional and keyword-only args
    for a in fn.args.args + fn.args.kwonlyargs:
        params.append(a.arg)
    # vararg / kwarg if present (kept minimal, just names)
    if fn.args.vararg:
        params.append(f"*{fn.args.vararg.arg}")
    if fn.args.kwarg:
        params.append(f"**{fn.args.kwarg.arg}")
    return params


def _collect_called_names(node: ast.AST) -> List[str]:
    """Find names of called functions within a node (best-effort)."""
    calls = set()

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, call_node: ast.Call):
            func = call_node.func
            name = _safe_unparse(func)
            # Normalize common wrappers like module.func -> func (still keep full form too)
            calls.add(name)
            self.generic_visit(call_node)

    CallVisitor().visit(node)
    return sorted(calls)


def _is_method(node: ast.FunctionDef) -> bool:
    return isinstance(getattr(node, "parent", None), ast.ClassDef)


def _node_id(kind: str, name: str, parent: Optional[str] = None) -> str:
    """Create a stable id for nodes (used in relationships)."""
    if parent:
        return f"{kind}:{parent}.{name}"
    return f"{kind}:{name}"


def parse_code_compact_ir(source: str) -> Dict[str, Any]:
    """
    Parse Python source into a compact, LLM-friendly IR that focuses on:
      - functions
      - classes
      - parameters
      - documentation
      - relationships (calls, inheritance, containment)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"error": "syntax_error", "raw": source}

    assign_parents(tree)

    units: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []

    # index to look up for relationship creation
    id_index = set()

    # Classes
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                bases.append(_safe_unparse(b))
            class_id = _node_id("class", node.name)
            id_index.add(class_id)
            units.append({
                "type": "class",
                "id": class_id,
                "name": node.name,
                "params": [],  # classes usually have no params here; kept for schema uniformity
                "doc": ast.get_docstring(node) or "",
                "meta": {"bases": bases},
            })
            # inheritance relationships
            for base_name in bases:
                relationships.append({
                    "from": class_id,
                    "to": f"class:{base_name}" if base_name.isidentifier() else base_name,
                    "type": "inherits"
                })

    # Functions & Methods (single pass to preserve containment)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            parent_class = node.parent.name if _is_method(node) else None
            kind = "method" if parent_class else "function"
            unit_id = _node_id(kind, node.name, parent_class)
            id_index.add(unit_id)
            params = _extract_param_names(node)
            doc = ast.get_docstring(node) or ""
            called = _collect_called_names(node)

            units.append({
                "type": kind,
                "id": unit_id,
                "name": node.name,
                "params": params,
                "doc": doc,
                "meta": {"defined_in": parent_class},
            })

            # containment relationship (method -> class)
            if parent_class:
                relationships.append({"from": unit_id, "to": _node_id("class", parent_class), "type": "member_of"})

            # call relationships (function/method -> called symbol)
            for called_name in called:
                # try to resolve called target to a unit id when simple names match
                # prefer exact local style matching: function:name or method:Class.func
                resolved = None
                # direct id candidates
                cand_func = _node_id("function", called_name)
                cand_method = _node_id("method", called_name)
                # also check for dotted calls like Class.method or module.func
                if called_name.count(".") == 1:
                    left, right = called_name.split(".", 1)
                    cand_method_in_class = _node_id("method", right, left)
                    if cand_method_in_class in id_index:
                        resolved = cand_method_in_class
                for cand in (cand_func, cand_method):
                    if cand in id_index:
                        resolved = cand
                        break
                relationships.append({
                    "from": unit_id,
                    "to": resolved or called_name,
                    "type": "calls"
                })

    # Optionally include top-level imports as light-weight units (useful context)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                uid = f"import:{a.name}"
                units.append({
                    "type": "import",
                    "id": uid,
                    "name": a.name,
                    "params": [],
                    "doc": "",
                    "meta": {"alias": a.asname}
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for a in node.names:
                name = f"{module}.{a.name}" if module else a.name
                uid = f"import:{name}"
                units.append({
                    "type": "import",
                    "id": uid,
                    "name": name,
                    "params": [],
                    "doc": "",
                    "meta": {"alias": a.asname}
                })

    return {
        "raw": source,
        "units": units,
        "relationships": relationships
    }


# small inline demo when run as script
if __name__ == "__main__":
    sample = '''
import math

class A:
    def m(self, x):
        return helper(x)

def helper(v):
    return v * 2
'''
    import json
    print(json.dumps(parse_code_compact_ir(sample), indent=2))
