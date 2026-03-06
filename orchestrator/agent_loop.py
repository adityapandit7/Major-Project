class AgentLoop:
    """
    Controls the orchestration cycle:
    Planner → Supervisor → Prompt Engine → Evaluator → Replanner
    """

    def __init__(
        self,
        planner,
        supervisor,
        evaluator,
        replanner,
        engine,
        max_iterations=3
    ):
        self.planner = planner
        self.supervisor = supervisor
        self.evaluator = evaluator
        self.replanner = replanner
        self.engine = engine
        self.max_iterations = max_iterations

    # =========================================================
    # MAIN LOOP
    # =========================================================

    def run(self, repo_state, smells):

        print("\n[AgentLoop] Starting execution loop")

        # -----------------------------
        # Initial planning
        # -----------------------------

        repo_state = self.planner.run(repo_state, smells)

        for iteration in range(self.max_iterations):

            print(f"\n[AgentLoop] Iteration {iteration + 1}")

            # -----------------------------
            # Execute tasks
            # -----------------------------

            repo_state = self.supervisor.run(repo_state)

            # -----------------------------
            # Generate prompts / results
            # -----------------------------

            prompts = self.engine.generate_prompts(
                repo_state=repo_state,
                user_request="both"
            )

            # -----------------------------
            # Evaluate results
            # -----------------------------

            repo_state = self.evaluator.run(repo_state)

            evaluation = repo_state.evaluation_scores

            if evaluation.get("success", False):
                print("\n[AgentLoop] Evaluation successful")
                return repo_state, prompts

            print("\n[AgentLoop] Issues detected")
            print(evaluation["issues"])

            # -----------------------------
            # Replanning
            # -----------------------------

            repo_state = self.replanner.run(repo_state)

        print("\n[AgentLoop] Max iterations reached")

        return repo_state, prompts