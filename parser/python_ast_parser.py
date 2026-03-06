import ast
from typing import Dict, List, Any, Set
from graph.state import FunctionUnit, ClassUnit


class PythonASTParser(ast.NodeVisitor):
    """
    AST-based parser for Python source code.

    Extracts:
    1. Structural metrics (for smell detection)
    2. Semantic units (for RepoState abstraction)
    """

    def __init__(self):
        self.functions = []
        self.classes = []

        # NEW: semantic units
        self.function_units: List[FunctionUnit] = []
        self.class_units: List[ClassUnit] = []
        self.imports: List[str] = []

        self.max_nesting_depth = 100
        self.current_function = None

    # =========================================================
    # IMPORT PARSING (NEW)
    # =========================================================

    def visit_Import(self, node):
        for n in node.names:
            self.imports.append(n.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for n in node.names:
            self.imports.append(f"{module}.{n.name}")
        self.generic_visit(node)

    # =========================================================
    # FUNCTION PARSING
    # =========================================================

    def visit_FunctionDef(self, node):

        prev_function = self.current_function
        self.current_function = node

        function_info = {
            "name": node.name,
            "loc": self._calculate_loc(node),
            "param_count": self._count_parameters(node),
            "nesting_depth": self._calculate_nesting(node),
            "responsibility_count": self._estimate_responsibilities(node),
            "lineno": node.lineno,
            "end_lineno": getattr(node, 'end_lineno', node.lineno)
        }

        self.functions.append(function_info)

        # NEW: semantic unit
        self.function_units.append(
            FunctionUnit(
                name=node.name,
                params=[arg.arg for arg in node.args.args],
                docstring=ast.get_docstring(node)
            )
        )

        self.generic_visit(node)

        self.current_function = prev_function

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    # =========================================================
    # CLASS PARSING
    # =========================================================

    def visit_ClassDef(self, node):

        class_info = {
            "name": node.name,
            "method_count": len(
                [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            ),
            "loc": self._calculate_loc(node),
            "lineno": node.lineno,
            "end_lineno": getattr(node, 'end_lineno', node.lineno)
        }

        self.classes.append(class_info)

        # NEW: build method semantic units
        methods = []

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):

                methods.append(
                    FunctionUnit(
                        name=item.name,
                        params=[arg.arg for arg in item.args.args],
                        docstring=ast.get_docstring(item)
                    )
                )

        # NEW: class semantic unit
        self.class_units.append(
            ClassUnit(
                name=node.name,
                methods=methods,
                docstring=ast.get_docstring(node)
            )
        )

        self.generic_visit(node)

    # =========================================================
    # METRICS
    # =========================================================

    def _calculate_loc(self, node) -> int:

        if hasattr(node, "end_lineno") and node.end_lineno:
            return node.end_lineno - node.lineno + 1
        return 1

    def _count_parameters(self, node) -> int:

        args = node.args
        count = len(args.args)
        count += len(args.kwonlyargs)
        count += len(args.posonlyargs) if hasattr(args, 'posonlyargs') else 0
        count += 1 if args.vararg else 0
        count += 1 if args.kwarg else 0
        return count

    def _calculate_nesting(self, node) -> int:

        max_depth = 0
        control_nodes = []

        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While, ast.If, ast.With, ast.Try, ast.ExceptHandler)):
                control_nodes.append(child)

        for control_node in control_nodes:
            depth = self._get_safe_depth(control_node)
            max_depth = max(max_depth, depth)

        return max_depth

    def _get_safe_depth(self, node) -> int:

        depth = 0
        visited: Set[int] = set()
        current = node

        while hasattr(current, "parent") and current.parent:

            if id(current) in visited:
                break

            visited.add(id(current))
            current = current.parent
            depth += 1

            if depth > self.max_nesting_depth:
                break

        return depth

    def _estimate_responsibilities(self, node) -> int:

        count = 1

        for child in ast.walk(node):

            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                count += 1

            elif isinstance(child, ast.With):
                count += 1

            elif isinstance(child, ast.ExceptHandler):
                count += 1

            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child != node:
                pass

        return count

    # =========================================================
    # UTILITY
    # =========================================================

    def attach_parents(self, tree):

        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):

                if not hasattr(child, 'parent'):
                    child.parent = node

                elif child.parent != node:
                    child.parent = node

    # =========================================================
    # MAIN PARSER ENTRY
    # =========================================================

    def parse(self, source_code: str) -> Dict[str, Any]:

        self.functions = []
        self.classes = []

        self.function_units = []
        self.class_units = []
        self.imports = []

        try:

            tree = ast.parse(source_code)
            self.attach_parents(tree)
            self.visit(tree)

            result = {
                "language": "Python",
                "functions": self.functions.copy(),
                "classes": self.classes.copy(),

                # NEW semantic units
                "function_units": self.function_units.copy(),
                "class_units": self.class_units.copy(),
                "imports": self.imports.copy(),

                "total_lines": len(source_code.splitlines()),
                "parse_success": True
            }

        except SyntaxError as e:

            result = {
                "language": "Python",
                "functions": [],
                "classes": [],
                "function_units": [],
                "class_units": [],
                "imports": [],
                "total_lines": len(source_code.splitlines()),
                "parse_success": False,
                "error": str(e)
            }

        except Exception as e:

            result = {
                "language": "Python",
                "functions": [],
                "classes": [],
                "function_units": [],
                "class_units": [],
                "imports": [],
                "total_lines": len(source_code.splitlines()),
                "parse_success": False,
                "error": f"Unexpected error: {e}"
            }

        return result