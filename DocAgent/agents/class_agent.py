# agents/class_agent.py

from agents.base import Agent
from graph.state import RepoState


class ClassDocAgent(Agent):
    """
    Documentation agent for class-level metadata.
    Emits a compact, self-describing artifact.
    """

    def run(self, state: RepoState) -> dict:
        self._validate_state(state)

        return {
            "_agent": "ClassDocAgent",
            "classes": [
                {
                    "name": cls.name,
                    "method_count": len(cls.methods),
                }
                for cls in state.classes
            ]
        }
