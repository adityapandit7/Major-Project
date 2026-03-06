# tests/smoke_state.py

from graph.state import create_repo_state, FunctionUnit

def test_repo_state_creation():
    state = create_repo_state(
        raw_code="def add(a, b): return a + b",
        classes=[],
        functions=[
            FunctionUnit(name="add", params=["a", "b"], docstring=None)
        ],
        imports=[],
    )

    print("Version:", state.version)
    print("State hash:", state.state_hash)
    print("Functions:", state.functions)


if __name__ == "__main__":
    test_repo_state_creation()
