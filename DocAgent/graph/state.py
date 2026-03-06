from dataclasses import dataclass, field
from typing import List, Dict, Any
import hashlib
import json


# ============================================================
# === Internal Utilities =====================================
# ============================================================

def _stable_hash(data: Dict[str, Any]) -> str:
    """
    Compute a deterministic semantic hash from structured repository data.

    Design goals:
    - Hash depends ONLY on semantic content (not memory location).
    - Identical semantic content MUST yield identical hashes.
    - Ordering MUST be deterministic to avoid spurious hash changes.

    This hash is used for:
    - State lineage tracking
    - Agent invariants
    - Debugging and reproducibility
    """
    payload = json.dumps(
        data,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ============================================================
# === Semantic Units =========================================
# ============================================================

@dataclass(frozen=True)
class FunctionUnit:
    """
    Immutable representation of a single function or method.

    This is a *semantic* unit, not a syntactic one.
    Agents must reason over this abstraction rather than raw AST nodes.
    """
    name: str
    params: List[str]
    docstring: str | None


@dataclass(frozen=True)
class ClassUnit:
    """
    Immutable representation of a class definition.

    Classes are represented only by:
    - name
    - methods (as FunctionUnit objects)
    - optional docstring
    """
    name: str
    methods: List[FunctionUnit]
    docstring: str | None


# ============================================================
# === RepoState ==============================================
# ============================================================

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
    - state_hash is DERIVED, never user-supplied.
    """

    # --------------------------------------------------------
    # Raw input (for traceability / debugging only)
    # --------------------------------------------------------
    raw_code: str

    # --------------------------------------------------------
    # Structured semantic units
    # --------------------------------------------------------
    classes: List[ClassUnit]
    functions: List[FunctionUnit]
    imports: List[str]

    # --------------------------------------------------------
    # Agent- or system-level annotations
    # (e.g., metrics, warnings, provenance)
    # --------------------------------------------------------
    metadata: Dict[str, Any]

    # --------------------------------------------------------
    # Lineage
    # --------------------------------------------------------
    version: int = 0
    state_hash: str = field(init=False)

    def __post_init__(self):
        """
        Compute a deterministic semantic hash from structured content.

        NOTE:
        - We explicitly sort lists to ensure order-independent hashing.
        - state_hash is derived and therefore cannot be passed to __init__.
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

        Rules:
        - Original RepoState remains unchanged.
        - Version is automatically incremented.
        - state_hash is recomputed from new semantic content.

        Example:
            new_state = state.evolve(
                metadata={**state.metadata, "qa_passed": True}
            )
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


# ============================================================
# === Factory (Option 1) =====================================
# ============================================================

def create_repo_state(
    raw_code: str,
    classes: List[ClassUnit],
    functions: List[FunctionUnit],
    imports: List[str],
    metadata: Dict[str, Any] | None = None,
    version: int = 0,
) -> RepoState:
    """
    Factory for creating the INITIAL RepoState.

    This is the ONLY place where RepoState should be constructed directly.

    Usage rules:
    - Agents MUST NOT call this function.
    - Only the orchestrator / service entrypoint may call this.
    - All subsequent changes MUST go through RepoState.evolve().

    This factory enforces:
    - Proper initialization
    - Derived state_hash computation
    - Consistent versioning
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
