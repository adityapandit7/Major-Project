import ast
from typing import Dict, List, Any, Set

class PythonASTParser(ast.NodeVisitor):
    """
    AST-based parser for Python source code.
    Extracts structural and metric information required
    by the Prompting Engine.
    """

    def __init__(self):
        self.functions = []
        self.classes = []
        self.max_nesting_depth = 100  # Safety limit
        self.current_function = None  # Track current function for nesting

    # ---------- Function Parsing ----------
    def visit_FunctionDef(self, node):
        # Save previous context
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
        self.generic_visit(node)
        
        # Restore context
        self.current_function = prev_function

    def visit_AsyncFunctionDef(self, node):
        """Handle async functions."""
        self.visit_FunctionDef(node)

    # ---------- Class Parsing ----------
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
        self.generic_visit(node)

    # ---------- Metrics ----------
    def _calculate_loc(self, node) -> int:
        """
        Calculates Lines of Code (LOC) using AST line numbers.
        """
        if hasattr(node, "end_lineno") and node.end_lineno:
            return node.end_lineno - node.lineno + 1
        return 1  # At least 1 line

    def _count_parameters(self, node) -> int:
        """
        Counts total parameters in a function definition.
        """
        args = node.args
        count = len(args.args)
        count += len(args.kwonlyargs)
        count += len(args.posonlyargs) if hasattr(args, 'posonlyargs') else 0
        count += 1 if args.vararg else 0
        count += 1 if args.kwarg else 0
        return count

    def _calculate_nesting(self, node) -> int:
        """
        Estimates nesting depth using improved algorithm with cycle detection.
        """
        max_depth = 0
        control_nodes = []

        # First pass: collect all control structure nodes
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While, ast.If, ast.With, ast.Try, ast.ExceptHandler)):
                control_nodes.append(child)

        # Second pass: calculate depth safely
        for control_node in control_nodes:
            depth = self._get_safe_depth(control_node)
            max_depth = max(max_depth, depth)

        return max_depth

    def _get_safe_depth(self, node) -> int:
        """
        Safely calculate depth with cycle detection.
        """
        depth = 0
        visited: Set[int] = set()  # Track node IDs to detect cycles
        current = node
        
        while hasattr(current, "parent") and current.parent:
            # Use id() to track unique nodes
            if id(current) in visited:
                break  # Cycle detected
            visited.add(id(current))
            
            current = current.parent
            depth += 1
            
            if depth > self.max_nesting_depth:
                break  # Safety limit
                
        return depth

    def _estimate_responsibilities(self, node) -> int:
        """
        Rough heuristic for responsibility count.
        More branches & loops → more responsibilities.
        """
        count = 1  # Base responsibility
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                count += 1
            elif isinstance(child, ast.With):
                count += 1
            elif isinstance(child, ast.ExceptHandler):
                count += 1
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child != node:
                # Don't count nested functions as responsibilities of parent
                pass
        return count

    # ---------- Utility ----------
    def attach_parents(self, tree):
        """
        Attaches parent references for nesting analysis with cycle prevention.
        """
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                # Check if parent already set to prevent cycles
                if not hasattr(child, 'parent'):
                    child.parent = node
                elif child.parent != node:
                    # Handle case where parent already set differently
                    child.parent = node

    def parse(self, source_code: str) -> Dict[str, Any]:
        """
        Main entry point for parsing Python source code.
        """
        # Reset for each parse
        self.functions = []
        self.classes = []
        
        try:
            tree = ast.parse(source_code)
            self.attach_parents(tree)
            self.visit(tree)
            
            result = {
                "language": "Python",
                "functions": self.functions.copy(),
                "classes": self.classes.copy(),
                "total_lines": len(source_code.splitlines()),
                "parse_success": True
            }
            
        except SyntaxError as e:
            # Handle syntax errors gracefully
            result = {
                "language": "Python",
                "functions": [],
                "classes": [],
                "total_lines": len(source_code.splitlines()),
                "parse_success": False,
                "error": str(e)
            }
        except Exception as e:
            result = {
                "language": "Python",
                "functions": [],
                "classes": [],
                "total_lines": len(source_code.splitlines()),
                "parse_success": False,
                "error": f"Unexpected error: {e}"
            }
        
        return result