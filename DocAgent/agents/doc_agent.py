from agents.base import BaseAgent
from graph.state import RepoState

from core.prompts import build_prompt
from core.writer import generate_docs
from core.markdown import to_markdown
from core.qa import run_qa


class DocAgent(BaseAgent):
    """
    Main documentation agent.
    Consumes an immutable RepoState and produces validated documentation.
    """

    def run(self, state: RepoState) -> dict:
        self._validate_state(state)

        # 1. Build LLM prompt from structured RepoState
        prompt = build_prompt(state)

        # 2. Generate raw documentation from LLM
        raw_docs = generate_docs(prompt)

        # 3. Convert to clean Markdown
        markdown = to_markdown(raw_docs)

        # 4. Run QA checks
        qa_report = run_qa(state, markdown)

        return {
            "markdown": markdown,
            "qa": qa_report,
            "meta": {
                "repo_version": state.version,
                "state_hash": state.state_hash,
            }
        }
