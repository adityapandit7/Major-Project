from dataclasses import dataclass, field
from typing import List, Dict, Any
import hashlib
import json


def _stable_hash(data: Dict[str, Any]) -> str:
    """
    Compute a deterministic semantic hash from structured repository data.

    Rules:
    - Hash must depend ONLY on semantic content.
    - Identical semantic content must yield identical hashes.
    - Order must be deterministic.
    """
    payload = json.dumps(
        data,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# =========================
# === Semantic Units ======
# =========================

@dataclass(frozen=True)
class FunctionUnit:
    """
    Immutable representation of a single function or method.
    """
    name: str
    params: List[str]
    docstring: str | None


@dataclass(frozen=True)
class ClassUnit:
    """
    Immutable representation of a class definition.
    """
    name: str
    methods: List[FunctionUnit]
    docstring: str | None


# =========================
# === RepoState ===========
# =========================

@dataclass(frozen=True)
class RepoState:
    """
    Immutable intermediate representation of the repository.

    SINGLE SOURCE OF TRUTH.
    All agents MUST reason exclusively over this structure.

    Invariants:
    - RepoState is immutable.
    - Agents must NOT re-parse raw code or filesystem.
    - Any semantic change MUST create a new RepoState.
    """

    # Raw input
    raw_code: str

    # Structured semantic units
    classes: List[ClassUnit]
    functions: List[FunctionUnit]
    imports: List[str]

    # Agent- or system-level annotations
    metadata: Dict[str, Any]

    # Lineage
    version: int = 0
    state_hash: str = field(init=False)

    def __post_init__(self):
        """
        Compute deterministic semantic hash from structured content.
        """
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
        """
        Create a new RepoState with updated fields.

        This is the ONLY allowed way to evolve state.
        Automatically increments version and recomputes hash.
        """
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


# =========================
# === Factory =============
# =========================

def create_repo_state(
    raw_code: str,
    classes: List[ClassUnit],
    functions: List[FunctionUnit],
    imports: List[str],
    metadata: Dict[str, Any] | None = None,
    version: int = 0,
) -> RepoState:
    """
    Factory for creating the initial RepoState.

    Agents MUST NOT call this.
    Only the orchestrator / entrypoint may.
    """
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
