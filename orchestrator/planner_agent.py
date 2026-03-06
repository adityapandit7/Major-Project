from core.task_models import Task
from core.hybrid_retriever import hybrid_retrieve


class PlannerAgent:

    def __init__(self, engine, retriever, symbol_index):
        """
        PlannerAgent converts repository state + detected smells
        into Task DAG nodes.
        """
        self.engine = engine
        self.retriever = retriever
        self.symbol_index = symbol_index

    def run(self, repo_state, smells):

        # =====================================================
        # 1. Build retrieval query
        # =====================================================

        query_tokens = []

        for f in repo_state.functions[:3]:
            query_tokens.append(f.name)

        for c in repo_state.classes[:2]:
            query_tokens.append(c.name)

        for s in smells[:2]:
            if isinstance(s, dict):
                query_tokens.append(s.get("name", ""))
            else:
                query_tokens.append(str(s))

        query_tokens.append("refactor code")

        query = " ".join(query_tokens)

        # =====================================================
        # 2. Retrieve context from vector DB
        # =====================================================

        try:
            results = hybrid_retrieve(
                query,
                self.retriever,
                self.symbol_index
            )

            retrieved_symbols = [r.get("symbol", "") for r in results]

        except Exception as e:

            print("Planner retrieval warning:", e)
            retrieved_symbols = []

        # =====================================================
        # 3. Generate tasks from smells
        # =====================================================

        tasks = []
        task_id = 1

        # -----------------------------------------
        # Case 1: smells exist → refactor + docs
        # -----------------------------------------

        if smells:

            for smell in smells:

                if isinstance(smell, dict):

                    target = smell.get("name", "unknown")
                    severity = smell.get("severity", "medium")

                else:

                    target = str(smell)
                    severity = "medium"

                priority_map = {
                    "critical": 1,
                    "high": 2,
                    "medium": 3,
                    "low": 4
                }

                priority = priority_map.get(severity, 3)

                # -------------------------------
                # Refactor task
                # -------------------------------

                refactor_task = Task(
                    id=task_id,
                    type="refactor",
                    target=target,
                    agent="RefactorAgent",
                    priority=priority
                )

                tasks.append(refactor_task)

                refactor_id = task_id
                task_id += 1

                # -------------------------------
                # Documentation task
                # -------------------------------

                doc_task = Task(
                    id=task_id,
                    type="document",
                    target=target,
                    agent="DocumentationAgent",
                    priority=priority + 1,
                    depends_on=[refactor_id]
                )

                tasks.append(doc_task)

                task_id += 1

        # -----------------------------------------
        # Case 2: no smells → documentation tasks
        # -----------------------------------------

        else:

            print("DEBUG --- No smells detected. Generating documentation tasks.")

            for func in repo_state.functions:

                tasks.append(
                    Task(
                        id=task_id,
                        type="document",
                        target=func.name,
                        agent="DocumentationAgent",
                        priority=3
                    )
                )

                task_id += 1

        # =====================================================
        # 4. Debug output
        # =====================================================

        print("\nDEBUG --- Planner Generated Tasks")

        for t in tasks:
            print(
                f"Task {t.id}: {t.type} → {t.target} "
                f"(priority {t.priority}, depends {t.depends_on})"
            )

        # =====================================================
        # 5. Update RepoState
        # =====================================================

        new_state = repo_state.evolve(tasks=tasks)

        return new_state