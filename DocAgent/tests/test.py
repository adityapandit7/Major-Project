from agents.doc_agent import DocAgent
from core.smoke_chain import build_smoke_chain
from graph.state import RepoState

dummy_state = RepoState(
    raw_code="def add(a, b): return a + b",
    classes=[],
    functions=[{"name": "add"}],
    imports=[],
    metadata={},
    version=0,
    state_hash="smoke"
)

agent = DocAgent(chain=build_smoke_chain())

out = agent.run(dummy_state)

print(out["markdown"])
