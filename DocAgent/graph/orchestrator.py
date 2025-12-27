# graph/orchestrator.py

from graph.freeze import freeze_repository
from graph.synthesizer import synthesize

from agents.class_agent import ClassDocAgent
from agents.function_agent import FunctionDocAgent


def run_graph(code: str) -> dict:
    # 1. Freeze input
    state = freeze_repository(code)

    # 2. Independent reasoning
    agents = [
        ClassDocAgent(),
        FunctionDocAgent(),
    ]

    artifacts = [agent.run(state) for agent in agents]

    # 3. Synthesize
    return synthesize(artifacts)
