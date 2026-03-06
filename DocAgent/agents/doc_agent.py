from agents.base import BaseAgent
from graph.state import RepoState

from core.prompts import build_prompt
from core.writer import generate_docs
from core.markdown import to_markdown
from core.qa import run_qa


class DocAgent(BaseAgent):
    """
    Main documentation agent.

    - Consumes an immutable RepoState
    - Produces validated documentation artifacts
    - Supports both legacy LLM calls and LangChain-based models (e.g. CodeT5)
    """

    name = "doc"

    def __init__(self, chain=None):
        """
        Args:
            chain (optional):
                A LangChain Runnable (PromptTemplate | LLM | OutputParser).
                If provided, it replaces the legacy LLM call ONLY.
        """
        self.chain = chain

    def run(self, state: RepoState) -> dict:
        # ---- Safety checks (orchestration invariant) ----
        self._validate_state(state)

        # =================================================
        # 1. Generate raw documentation (LLM filler)
        # =================================================
        if self.chain is not None:
            # LangChain / CodeT5 path
            raw_docs = self.chain.invoke({
                "classes": state.classes,
                "functions": state.functions,
                "imports": state.imports,
            })
        else:
            # Legacy path (unchanged behavior)
            prompt = build_prompt(state)
            raw_docs = generate_docs(prompt)

        # =================================================
        # 2. Post-processing (shared, deterministic)
        # =================================================
        markdown = to_markdown(raw_docs)

        # =================================================
        # 3. QA validation
        # =================================================
        qa_report = run_qa(state, markdown)

        # =================================================
        # 4. Artifact return (shape unchanged)
        # =================================================
        return {
            "markdown": markdown,
            "qa": qa_report,
            "meta": {
                "repo_version": state.version,
                "state_hash": state.state_hash,
                "agent": self.name,
                "mode": "langchain" if self.chain else "legacy",
            }
        }
