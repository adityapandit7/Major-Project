from .dacos_knowledge import DACOSKnowledgeBase
from typing import List, Dict, Optional


class SmellDetector:
    """
    Detects code smells using DACOS-informed thresholds.
    """

    def __init__(self, dacos_folder: Optional[str] = None):
        self.knowledge = DACOSKnowledgeBase(dacos_folder)
        self.smells = self.knowledge.get_all_smells()

    def detect_smells(self, parsed_code: dict) -> List[Dict]:
        """
        Detects code smells with severity levels.

        Args:
            parsed_code: Dictionary from AST parser with functions and classes

        Returns:
            List of detected smells with details
        """
        detected = []
        functions = parsed_code.get("functions", [])

        for func in functions:
            for smell_name, smell_data in self.smells.items():

                condition = smell_data.get("condition")
                if not condition:
                    continue

                if condition(func):
                    # Determine severity using the knowledge base
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
                        "thresholds": thresholds  # Include all thresholds for reference
                    })

        # Sort by severity (critical first, then high, then medium)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        detected.sort(key=lambda x: severity_order.get(x["severity"], 4))

        return detected

    def generate_report(self, parsed_code: dict) -> str:
        """Generate a human-readable smell report."""
        smells = self.detect_smells(parsed_code)

        if not smells:
            return "✅ No code smells detected! Your code looks clean."

        report = []
        report.append("="*60)
        report.append("📊 CODE SMELL ANALYSIS REPORT")
        report.append("="*60)
        report.append("")

        # Add summary
        report.append(f"📈 Summary: Found {len(smells)} code smell(s)")

        # Count by severity
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

        # Detailed list
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
            
            # Show severity thresholds if available
            if 'thresholds' in smell and isinstance(smell['thresholds'], dict):
                th = smell['thresholds']
                report.append(f"      • Severity thresholds: Medium >{th.get('threshold', 'N/A')}, "
                             f"High >{th.get('severe', 'N/A')}, Critical >{th.get('critical', 'N/A')}")
            
            report.append(f"   🔧 Suggested Fix: {smell['refactor_guidance']}")
            report.append("")

        report.append("="*60)
        return "\n".join(report)

    def get_refactoring_priority(self, parsed_code: dict) -> List[Dict]:
        """Get smells sorted by refactoring priority."""
        smells = self.detect_smells(parsed_code)

        # Add priority score
        for smell in smells:
            score = 0
            if smell["severity"] == "critical":
                score += 100
            elif smell["severity"] == "high":
                score += 50
            elif smell["severity"] == "medium":
                score += 20

            # Add based on metric value relative to threshold
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


# Simple function for backward compatibility
def detect_code_smells(parsed_code: dict, dacos_folder: Optional[str] = None) -> list:
    """Simple function returning just smell names."""
    detector = SmellDetector(dacos_folder)
    return [s["name"] for s in detector.detect_smells(parsed_code)]