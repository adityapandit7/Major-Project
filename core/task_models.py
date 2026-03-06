from pydantic import BaseModel, Field
from typing import List


class Task(BaseModel):
    """
    Represents a node in the task DAG used by the planner.
    """

    id: int
    type: str
    target: str
    agent: str
    priority: int

    depends_on: List[int] = Field(default_factory=list)
    