from graph.state import create_repo_state
from agents.doc_agent import DocAgent

# 1. Input code
code = """
class A:
    def m(self, x):
        return x * 2

def helper(v):
    return v + 1
"""

# 2. Fake parsed units (temporary)
classes = []
functions = []
imports = []

# 3. Create immutable RepoState
state = create_repo_state(
    raw_code=code,
    classes=classes,
    functions=functions,
    imports=imports,
    version=0
)

# 4. Initialize agents
doc_agent = DocAgent()

# 5. Run orchestration
artifacts = []
artifacts.append(doc_agent.run(state))

# 6. Inspect outputs
print("ARTIFACTS:")
for a in artifacts:
    print(a)
