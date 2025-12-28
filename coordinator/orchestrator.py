from agents.doc_agent import DocAgent
from agents.refactor_agent import RefactorAgent


class Coordinator:
    def __init__(self):
        self.doc_agent = DocAgent()
        self.refactor_agent = RefactorAgent()

    def run(self, code: str):
        print("🔹 Coordinator started orchestration...\n")

        documentation = self.doc_agent.generate_docs(code)
        print("📄 Documentation Generated:\n")
        print(documentation)

        refactored_code = self.refactor_agent.refactor(code)
        print("\n🛠 Refactored Code:\n")
        print(refactored_code)

        print("\n✅ Orchestration completed.")
