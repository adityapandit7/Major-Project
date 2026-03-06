import sys
from pathlib import Path

# add project root to python path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from graph.state import create_repo_state, FunctionUnit, ClassUnit


code = """
def add(a,b):
    return a+b

class Calculator:
    def multiply(self,a,b):
        return a*b
"""

functions = [
    FunctionUnit("add", ["a","b"], None)
]

classes = [
    ClassUnit(
        "Calculator",
        methods=[
            FunctionUnit("multiply",["self","a","b"],None)
        ],
        docstring=None
    )
]

state = create_repo_state(
    raw_code=code,
    classes=classes,
    functions=functions,
    imports=[]
)

print("RepoState hash:", state.state_hash)
print("Functions:", state.functions)
print("Classes:", state.classes)
