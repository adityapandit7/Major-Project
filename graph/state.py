from dataclasses import dataclass, field
from typing import List, Dict, Any
import hashlib
import json

from core.task_models import Task


# =========================
# Stable Hash Utility
# =========================

def _stable_hash(data: Dict[str, Any]) -> str:
    payload = json.dumps(
        data,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# =========================
# Core Code Units
# =========================

@dataclass(frozen=True)
class FunctionUnit:
    name: str
    params: List[str]
    docstring: str | None


@dataclass(frozen=True)
class ClassUnit:
    name: str
    methods: List["FunctionUnit"]
    docstring: str | None


# =========================
# Agent Communication Units
# =========================

@dataclass(frozen=True)
class CodeSmell:
    smell_type: str
    location: str
    description: str
    severity: int


@dataclass(frozen=True)
class RefactorResult:
    target_name: str
    success: bool
    changes: str


@dataclass(frozen=True)
class DocumentationResult:
    target_name: str
    docstring: str


# =========================
# Shared Multi-Agent State
# =========================

@dataclass(frozen=True)
class RepoState:

    # ---- Original repo info ----
    raw_code: str
    classes: List[ClassUnit]
    functions: List[FunctionUnit]
    imports: List[str]

    metadata: Dict[str, Any]

    # ---- Multi-agent outputs ----
    smells: List[CodeSmell]
    tasks: List[Task]

    refactor_results: List[RefactorResult]
    documentation_results: List[DocumentationResult]

    evaluation_scores: Dict[str, float]

    # ---- state tracking ----
    version: int = 0
    state_hash: str = field(init=False)

    def __post_init__(self):

        object.__setattr__(
            self,
            "state_hash",
            _stable_hash({
                "raw_code": self.raw_code,
                "classes": sorted(self.classes, key=lambda c: c.name),
                "functions": sorted(self.functions, key=lambda f: f.name),
                "imports": sorted(self.imports),
                "metadata": self.metadata,

                "smells": self.smells,

                # convert pydantic tasks → dict
                "tasks": [t.model_dump() for t in self.tasks],

                "refactor_results": self.refactor_results,
                "documentation_results": self.documentation_results,
                "evaluation_scores": self.evaluation_scores,
            })
        )

    # =========================
    # Immutable State Evolution
    # =========================

    def evolve(self, **changes) -> "RepoState":

        data = {
            "raw_code": self.raw_code,
            "classes": self.classes,
            "functions": self.functions,
            "imports": self.imports,
            "metadata": self.metadata,

            "smells": self.smells,
            "tasks": self.tasks,

            "refactor_results": self.refactor_results,
            "documentation_results": self.documentation_results,
            "evaluation_scores": self.evaluation_scores,
        }

        data.update(changes)

        return RepoState(
            **data,
            version=self.version + 1,
        )


# =========================
# Factory
# =========================

def create_repo_state(
    raw_code: str,
    classes: List[ClassUnit],
    functions: List[FunctionUnit],
    imports: List[str],
    metadata: Dict[str, Any] | None = None,
) -> RepoState:

    if metadata is None:
        metadata = {}
    else:
        metadata = dict(metadata)

    metadata["repo_hash"] = hashlib.sha256(raw_code.encode()).hexdigest()

    return RepoState(
        raw_code=raw_code,
        classes=classes,
        functions=functions,
        imports=imports,
        metadata=metadata,

        smells=[],
        tasks=[],

        refactor_results=[],
        documentation_results=[],
        evaluation_scores={},

        version=0,
    )