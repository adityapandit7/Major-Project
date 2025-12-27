from collections import defaultdict
from typing import List, Dict, Any


def synthesize(artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministically aggregates artifacts produced by independent agents.

    Each artifact MUST:
    - Be a dictionary
    - Declare its provenance via `_agent`

    Artifacts are merged by semantic category without overwriting.
    """

    documentation = defaultdict(list)
    issues = defaultdict(list)
    suggestions = defaultdict(list)

    agents_run = []

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise TypeError("Each artifact must be a dictionary")

        agent_name = artifact.get("_agent")
        if not agent_name:
            raise ValueError("Artifact missing required '_agent' field")

        agents_run.append(agent_name)

        # ---- Documentation artifacts ----
        if "classes" in artifact:
            documentation["classes"].extend(artifact["classes"])

        if "functions" in artifact:
            documentation["functions"].extend(artifact["functions"])

        if "methods" in artifact:
            documentation["methods"].extend(artifact["methods"])

        # ---- Issue artifacts ----
        if "issues" in artifact:
            for key, value in artifact["issues"].items():
                issues[key].extend(value)

        # ---- Suggestion artifacts ----
        if "suggestions" in artifact:
            for key, value in artifact["suggestions"].items():
                suggestions[key].extend(value)

    return {
        "documentation": dict(documentation),
        "issues": dict(issues),
        "suggestions": dict(suggestions),
        "meta": {
            "agents_run": sorted(set(agents_run)),
            "artifact_count": len(artifacts),
        },
    }
