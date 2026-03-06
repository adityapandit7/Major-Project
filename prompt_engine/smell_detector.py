from .dacos_knowledge import DACOSKnowledgeBase
from typing import List, Dict, Optional, Any


class SmellDetector:
    """
    Detects code smells using DACOS-informed thresholds.

    Supports two input formats:
    1. parsed_code dictionary (existing pipeline)
    2. RepoState object (semantic abstraction)
    """

    def __init__(self, dacos_folder: Optional[str] = None):
        self.knowledge = DACOSKnowledgeBase(dacos_folder)
        self.smells = self.knowledge.get_all_smells()

    # =========================================================
    # Internal helper
    # =========================================================

    def _extract_functions(self, data: Any) -> List[Dict]:
        """
        Convert RepoState or parsed_code into a list of
        metric dictionaries usable by smell conditions.
        """

        # Case 1: parsed_code dictionary
        if isinstance(data, dict):
            return data.get("functions", [])

        # Case 2: RepoState object
        if hasattr(data, "functions"):
            functions = []

            for f in data.functions:
                functions.append({
                    "name": f.name,
                    "loc": 0,  # RepoState doesn't store LOC
                    "param_count": len(f.params),
                    "responsibility_count": 1,
                    "nesting_depth": 0,
                    "lineno": "unknown"
                })

            return functions

        return []

    # =========================================================
    # Main smell detection
    # =========================================================

    def detect_smells(self, data: Any) -> List[Dict]:
        """
        Detects code smells with severity levels.

        Args:
            data: parsed_code dict OR RepoState object

        Returns:
            List of detected smells with details
        """

        detected = []
        functions = self._extract_functions(data)

        for func in functions:
            for smell_name, smell_data in self.smells.items():

                condition = smell_data.get("condition")
                if not condition:
                    continue

                if condition(func):

                    severity = self.knowledge.get_severity(smell_name, func)

                    metric_name = smell_data.get("metric", "loc")
                    metric_value = func.get(metric_name, 0)

                    thresholds = smell_data.get("thresholds", {})
                    threshold_value = thresholds.get("threshold", "N/A")

                    detected.append({
                        "name": smell_name,
                        "severity": severity,
                        "description": smell_data["description"],
                        "refactor_guidance": smell_data["refactor_guidance"],
                        "location": f"Function: {func['name']} (line {func.get('lineno', 'unknown')})",
                        "metrics": {
                            "loc": func.get("loc", 0),
                            "param_count": func.get("param_count", 0),
                            "responsibility_count": func.get("responsibility_count", 1),
                            "nesting_depth": func.get("nesting_depth", 0)
                        },
                        "threshold": threshold_value,
                        "current_value": metric_value,
                        "thresholds": thresholds
                    })

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        detected.sort(key=lambda x: severity_order.get(x["severity"], 4))

        return detected

    # =========================================================
    # Report generation
    # =========================================================

    def generate_report(self, data: Any) -> str:
        """Generate a human-readable smell report."""

        smells = self.detect_smells(data)

        if not smells:
            return "✅ No code smells detected! Your code looks clean."

        report = []
        report.append("="*60)
        report.append("📊 CODE SMELL ANALYSIS REPORT")
        report.append("="*60)
        report.append("")

        report.append(f"📈 Summary: Found {len(smells)} code smell(s)")

        severity_counts = {}
        for smell in smells:
            sev = smell["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if severity_counts:
            report.append("📊 By severity:")
            for sev in ["critical", "high", "medium", "low"]:
                if sev in severity_counts:
                    report.append(f"   • {sev.title()}: {severity_counts[sev]}")

        report.append("")
        report.append("-"*60)

        for i, smell in enumerate(smells, 1):

            report.append(f"\n{i}. {smell['name']} ({smell['severity'].upper()})")
            report.append(f"   📍 Location: {smell['location']}")
            report.append(f"   📝 Issue: {smell['description']}")

            report.append(f"   📊 Metrics:")
            report.append(f"      • Lines of Code: {smell['metrics']['loc']}")
            report.append(f"      • Parameters: {smell['metrics']['param_count']}")
            report.append(f"      • Responsibilities: {smell['metrics']['responsibility_count']}")

            if smell['threshold'] != 'N/A':
                report.append(f"      • Threshold: {smell['threshold']} (current: {smell['current_value']})")

            if 'thresholds' in smell and isinstance(smell['thresholds'], dict):

                th = smell['thresholds']

                report.append(
                    f"      • Severity thresholds: "
                    f"Medium >{th.get('threshold', 'N/A')}, "
                    f"High >{th.get('severe', 'N/A')}, "
                    f"Critical >{th.get('critical', 'N/A')}"
                )

            report.append(f"   🔧 Suggested Fix: {smell['refactor_guidance']}")
            report.append("")

        report.append("="*60)

        return "\n".join(report)

    # =========================================================
    # Refactoring priority
    # =========================================================

    def get_refactoring_priority(self, data: Any) -> List[Dict]:
        """Get smells sorted by refactoring priority."""

        smells = self.detect_smells(data)

        for smell in smells:

            score = 0

            if smell["severity"] == "critical":
                score += 100
            elif smell["severity"] == "high":
                score += 50
            elif smell["severity"] == "medium":
                score += 20

            threshold = smell.get("threshold")

            if threshold and threshold != "N/A" and isinstance(threshold, (int, float)) and threshold > 0:
                try:
                    ratio = smell["current_value"] / threshold
                    score += int(ratio * 10)
                except (TypeError, ZeroDivisionError):
                    pass

            smell["priority_score"] = score

        smells.sort(key=lambda x: x["priority_score"], reverse=True)

        return smells


# =========================================================
# Backward compatibility
# =========================================================

def detect_code_smells(data: Any, dacos_folder: Optional[str] = None) -> list:
    """Simple function returning just smell names."""

    detector = SmellDetector(dacos_folder)
    return [s["name"] for s in detector.detect_smells(data)]
from typing import List, Dict, Optional, Any


class SmellDetector:
    """
    Detects code smells using DACOS-informed thresholds.

    Supports two input formats:
    1. parsed_code dictionary (existing pipeline)
    2. RepoState object (semantic abstraction)
    """

    def __init__(self, dacos_folder: Optional[str] = None):
        self.knowledge = DACOSKnowledgeBase(dacos_folder)
        self.smells = self.knowledge.get_all_smells()

    # =========================================================
    # Internal helper
    # =========================================================

    def _extract_functions(self, data: Any) -> List[Dict]:
        """
        Convert RepoState or parsed_code into a list of
        metric dictionaries usable by smell conditions.
        """

        # Case 1: parsed_code dictionary
        if isinstance(data, dict):
            return data.get("functions", [])

        # Case 2: RepoState object
        if hasattr(data, "functions"):
            functions = []

            for f in data.functions:
                functions.append({
                    "name": f.name,
                    "loc": 0,  # RepoState doesn't store LOC
                    "param_count": len(f.params),
                    "responsibility_count": 1,
                    "nesting_depth": 0,
                    "lineno": "unknown"
                })

            return functions

        return []

    # =========================================================
    # Main smell detection
    # =========================================================

    def detect_smells(self, data: Any) -> List[Dict]:
        """
        Detects code smells with severity levels.

        Args:
            data: parsed_code dict OR RepoState object

        Returns:
            List of detected smells with details
        """

        detected = []
        functions = self._extract_functions(data)

        for func in functions:
            for smell_name, smell_data in self.smells.items():

                condition = smell_data.get("condition")
                if not condition:
                    continue

                if condition(func):

                    severity = self.knowledge.get_severity(smell_name, func)

                    metric_name = smell_data.get("metric", "loc")
                    metric_value = func.get(metric_name, 0)

                    thresholds = smell_data.get("thresholds", {})
                    threshold_value = thresholds.get("threshold", "N/A")

                    detected.append({
                        "name": smell_name,
                        "severity": severity,
                        "description": smell_data["description"],
                        "refactor_guidance": smell_data["refactor_guidance"],
                        "location": f"Function: {func['name']} (line {func.get('lineno', 'unknown')})",
                        "metrics": {
                            "loc": func.get("loc", 0),
                            "param_count": func.get("param_count", 0),
                            "responsibility_count": func.get("responsibility_count", 1),
                            "nesting_depth": func.get("nesting_depth", 0)
                        },
                        "threshold": threshold_value,
                        "current_value": metric_value,
                        "thresholds": thresholds
                    })

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        detected.sort(key=lambda x: severity_order.get(x["severity"], 4))

        return detected

    # =========================================================
    # Report generation
    # =========================================================

    def generate_report(self, data: Any) -> str:
        """Generate a human-readable smell report."""

        smells = self.detect_smells(data)

        if not smells:
            return "✅ No code smells detected! Your code looks clean."

        report = []
        report.append("="*60)
        report.append("📊 CODE SMELL ANALYSIS REPORT")
        report.append("="*60)
        report.append("")

        report.append(f"📈 Summary: Found {len(smells)} code smell(s)")

        severity_counts = {}
        for smell in smells:
            sev = smell["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if severity_counts:
            report.append("📊 By severity:")
            for sev in ["critical", "high", "medium", "low"]:
                if sev in severity_counts:
                    report.append(f"   • {sev.title()}: {severity_counts[sev]}")

        report.append("")
        report.append("-"*60)

        for i, smell in enumerate(smells, 1):

            report.append(f"\n{i}. {smell['name']} ({smell['severity'].upper()})")
            report.append(f"   📍 Location: {smell['location']}")
            report.append(f"   📝 Issue: {smell['description']}")

            report.append(f"   📊 Metrics:")
            report.append(f"      • Lines of Code: {smell['metrics']['loc']}")
            report.append(f"      • Parameters: {smell['metrics']['param_count']}")
            report.append(f"      • Responsibilities: {smell['metrics']['responsibility_count']}")

            if smell['threshold'] != 'N/A':
                report.append(f"      • Threshold: {smell['threshold']} (current: {smell['current_value']})")

            if 'thresholds' in smell and isinstance(smell['thresholds'], dict):

                th = smell['thresholds']

                report.append(
                    f"      • Severity thresholds: "
                    f"Medium >{th.get('threshold', 'N/A')}, "
                    f"High >{th.get('severe', 'N/A')}, "
                    f"Critical >{th.get('critical', 'N/A')}"
                )

            report.append(f"   🔧 Suggested Fix: {smell['refactor_guidance']}")
            report.append("")

        report.append("="*60)

        return "\n".join(report)

    # =========================================================
    # Refactoring priority
    # =========================================================

    def get_refactoring_priority(self, data: Any) -> List[Dict]:
        """Get smells sorted by refactoring priority."""

        smells = self.detect_smells(data)

        for smell in smells:

            score = 0

            if smell["severity"] == "critical":
                score += 100
            elif smell["severity"] == "high":
                score += 50
            elif smell["severity"] == "medium":
                score += 20

            threshold = smell.get("threshold")

            if threshold and threshold != "N/A" and isinstance(threshold, (int, float)) and threshold > 0:
                try:
                    ratio = smell["current_value"] / threshold
                    score += int(ratio * 10)
                except (TypeError, ZeroDivisionError):
                    pass

            smell["priority_score"] = score

        smells.sort(key=lambda x: x["priority_score"], reverse=True)

        return smells


# =========================================================
# Backward compatibility
# =========================================================

def detect_code_smells(data: Any, dacos_folder: Optional[str] = None) -> list:
    """Simple function returning just smell names."""

    detector = SmellDetector(dacos_folder)
    return [s["name"] for s in detector.detect_smells(data)]