from agents.base import Agent
from graph.state import RepoState


class FunctionDocAgent(Agent):
    """
    Documentation agent for standalone (top-level) functions.
    Emits a compact, self-describing artifact.
    """

    def run(self, state: RepoState) -> dict:
        self._validate_state(state)

        return {
            "_agent": "FunctionDocAgent",
            "functions": [
                {
                    "name": fn.name,
                    "params": fn.params,
                }
                for fn in state.functions
            ]
        }
