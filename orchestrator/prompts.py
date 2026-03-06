def build_planner_prompt(repo_state, smells, retrieved_symbols):

    return f"""
You are a software architecture planning agent.

Analyze the repository and generate improvement tasks.

Repository functions:
{[f.name for f in repo_state.functions]}

Repository classes:
{[c.name for c in repo_state.classes]}

Detected code smells:
{smells}

Relevant code retrieved from index:
{retrieved_symbols}

Create tasks to improve:

- documentation
- refactoring
- structure

Rules:

1. Refactor tasks must come before documentation tasks
2. Documentation tasks depend on refactoring tasks
3. Use priority values (1 = highest)

Return JSON only:

{{
 "tasks":[
  {{
   "id":1,
   "type":"refactor",
   "target":"function_name",
   "agent":"RefactorAgent",
   "priority":1
  }},
  {{
   "id":2,
   "type":"document",
   "target":"function_name",
   "agent":"DocumentationAgent",
   "priority":2,
   "depends_on":[1]
  }}
 ]
}}
"""