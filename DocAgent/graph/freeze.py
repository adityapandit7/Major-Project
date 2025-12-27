import ast
from graph.state import RepoState, ClassUnit, FunctionUnit


def freeze_repository(code: str) -> RepoState:
    tree = ast.parse(code)

    imports = []
    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)

        elif isinstance(node, ast.FunctionDef):
            functions.append(
                FunctionUnit(
                    name=node.name,
                    params=[arg.arg for arg in node.args.args],
                    docstring=ast.get_docstring(node),
                )
            )

        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(
                        FunctionUnit(
                            name=item.name,
                            params=[arg.arg for arg in item.args.args],
                            docstring=ast.get_docstring(item),
                        )
                    )

            classes.append(
                ClassUnit(
                    name=node.name,
                    methods=methods,
                    docstring=ast.get_docstring(node),
                )
            )

    return RepoState(
        raw_code=code,
        classes=classes,
        functions=functions,
        imports=imports,
        metadata={"language": "python"},
    )