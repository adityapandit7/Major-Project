from core.task_models import Task


class Replanner:
    """
    Generates new tasks when evaluator finds issues.
    No LLM calls — purely orchestration logic.
    """

    def run(self, repo_state):

        evaluation = repo_state.evaluation_scores

        if not evaluation:
            return repo_state

        if evaluation.get("success", False):
            print("\n[Replanner] No replanning required")
            return repo_state

        issues = evaluation.get("issues", [])

        print("\n[Replanner] Issues detected — creating new tasks")

        new_tasks = []

        # next integer ID
        next_id = max([t.id for t in repo_state.tasks], default=0) + 1

        for issue in issues:

            # -----------------------------------
            # Missing Documentation
            # -----------------------------------
            if "undocumented" in issue:

                target = issue.split()[1]

                new_tasks.append(
                    Task(
                        id=next_id,
                        type="documentation",
                        target=target,
                        agent="documentation",
                        priority=1
                    )
                )

                next_id += 1

            # -----------------------------------
            # Refactor Failure
            # -----------------------------------
            elif "Refactor failed" in issue:

                target = issue.split()[-1]

                new_tasks.append(
                    Task(
                        id=next_id,
                        type="refactor",
                        target=target,
                        agent="refactor",
                        priority=1
                    )
                )

                next_id += 1

        if not new_tasks:
            print("[Replanner] No actionable issues")
            return repo_state

        print(f"[Replanner] Created {len(new_tasks)} new tasks")

        updated_tasks = repo_state.tasks + new_tasks

        return repo_state.evolve(tasks=updated_tasks)