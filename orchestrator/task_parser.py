import json

from typing import List, Dict, Any
from orchestrator.prompts import build_planner_prompt
from core.hybrid_retriever import hybrid_retrieve
from core.task_models import Task
def parse_tasks(response: str):

    data = json.loads(response)

    tasks = []

    for t in data.get("tasks", []):

        task = Task(
            id=t["id"],
            type=t["type"],
            target=t["target"],
            agent=t["agent"],
            priority=t.get("priority", 1),
            depends_on=t.get("depends_on", [])
        )

        tasks.append(task)

    return tasks
