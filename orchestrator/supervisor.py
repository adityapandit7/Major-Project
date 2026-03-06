from graph.state import RepoState


class Supervisor:
    """
    Executes planner tasks sequentially.
    Compatible with immutable RepoState and current PromptingEngine.
    """

    def __init__(self, engine, retriever, symbol_index):
        self.engine = engine
        self.retriever = retriever
        self.symbol_index = symbol_index

    # =========================================================
    # MAIN EXECUTION LOOP
    # =========================================================

    def run(self, repo_state: RepoState) -> RepoState:

        for task in repo_state.tasks:

            if task.id in repo_state.completed_tasks:
                continue

            print(f"\n[Supervisor] Executing task {task.id}")
            print(f"[Supervisor] Type: {task.type}")
            print(f"[Supervisor] Target: {task.target}")

            # Retrieve context (optional but useful for debugging)
            docs = self.retriever.invoke(task.target)

            context = "\n".join(
                doc.page_content for doc in docs
            )

            print(f"[Supervisor] Retrieved {len(docs)} documents")

            # Supervisor does not execute LLM tasks
            # It simply marks tasks as completed

            repo_state = repo_state.evolve(
                completed_tasks=repo_state.completed_tasks + [task.id]
            )

        print("\n[Supervisor] Execution complete")

        return repo_state