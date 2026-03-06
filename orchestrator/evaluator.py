import json


class Evaluator:
    """
    Evaluates repository results after supervisor execution.
    Lives inside orchestration layer.
    """

    def __init__(self, engine):
        self.engine = engine

    # ======================================================
    # MAIN
    # ======================================================

    def run(self, repo_state):

        issues = []

        # -----------------------------
        # Documentation Coverage Check
        # -----------------------------
        documented = {d.target_name for d in repo_state.documentation_results}

        for cls in repo_state.classes:
            if cls.name not in documented:
                issues.append(f"Class {cls.name} undocumented")

        for fn in repo_state.functions:
            if fn.name not in documented:
                issues.append(f"Function {fn.name} undocumented")

        # -----------------------------
        # Refactor Success Check
        # -----------------------------
        for r in repo_state.refactor_results:
            if not r.success:
                issues.append(f"Refactor failed for {r.target_name}")

        # -----------------------------
        # Planner Coverage Check
        # -----------------------------
        if len(repo_state.tasks) == 0:
            issues.append("Planner produced no tasks")

        success = len(issues) == 0

        evaluation = {
            "success": success,
            "issues": issues
        }

        print("\n[Evaluator]")
        print(json.dumps(evaluation, indent=2))

        return repo_state.evolve(
            evaluation_scores=evaluation
        )