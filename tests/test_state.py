import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph.state import create_repo_state
from core.task_models import Task

state = create_repo_state(
    raw_code="print('hello')",
    classes=[],
    functions=[],
    imports=[]
)

task = Task(
    id=1,
    type="refactor",
    target="example_function",
    agent="RefactorAgent",
    priority=1
)

state2 = state.evolve(tasks=[task])

print(state2.tasks)

