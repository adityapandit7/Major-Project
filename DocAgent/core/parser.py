import ast

def parse_code(source: str) -> dict:
    tree = ast.parse(source)

    classes = []
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    return {
        "raw": source,
        "classes": classes,
        "functions": functions,
    }