from dataclasses import dataclass, field
from typing import List, Dict, Any
import hashlib
import json


def _stable_hash(data: Dict[str, Any]) -> str:
    payload = json.dumps(
        data,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FunctionUnit:
    name: str
    params: List[str]
    docstring: str | None


@dataclass(frozen=True)
class ClassUnit:
    name: str
    methods: List[FunctionUnit]
    docstring: str | None


@dataclass(frozen=True)
class RepoState:

    raw_code: str

    classes: List[ClassUnit]
    functions: List[FunctionUnit]
    imports: List[str]

    metadata: Dict[str, Any]

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
            })
        )

    def evolve(self, **changes) -> "RepoState":

        data = {
            "raw_code": self.raw_code,
            "classes": self.classes,
            "functions": self.functions,
            "imports": self.imports,
            "metadata": self.metadata,
        }

        data.update(changes)

        return RepoState(
            **data,
            version=self.version + 1,
        )

print("RepoState initialized with hash:", RepoState.__post_init__.__annotations__)
def create_repo_state(
    raw_code: str,
    classes: List[ClassUnit],
    functions: List[FunctionUnit],
    imports: List[str],
    metadata: Dict[str, Any] | None = None,
    version: int = 0,
) -> RepoState:

    if metadata is None:
        metadata = {}

    return RepoState(
        raw_code=raw_code,
        classes=classes,
        functions=functions,
        imports=imports,
        metadata=metadata,
        version=version,
    )
