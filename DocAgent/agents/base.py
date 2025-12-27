from graph.state import RepoState
from abc import ABC, abstractmethod


class BaseAgent:
    """
    Base class for all agents.

    Enforces RepoState as the ONLY valid input/output abstraction.
    """

    def _validate_state(self, state: RepoState) -> None:
        assert isinstance(state, RepoState), \
            "Agents may only consume RepoState"

        assert state.version >= 0, \
            "RepoState version must be non-negative"

        assert state.state_hash is not None, \
            "RepoState must have a valid hash"

    def run(self, state: RepoState) -> RepoState:
        """
        Subclasses must implement this.
        """
        raise NotImplementedError

Agent = BaseAgent

class Agent(ABC):
    @abstractmethod
    def run(self, state: RepoState) -> dict:
        """
        Consume RepoState and return an artifact.
        Must NOT mutate state.
        """
        pass
