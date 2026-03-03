# evaluate_refactor.py

import ast
import difflib
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import json
from datetime import datetime
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Constants
MAX_LINE_LENGTH_PEP8 = 79
MAX_LINE_LENGTH_RELAXED = 99
MIN_IDEAL_LINE_LENGTH = 20
MAX_IDEAL_LINE_LENGTH = 60
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 30
MIN_MEANINGFUL_CHANGES = 3

# Try to import codebleu, but provide fallback if not available
try:
    from codebleu import calc_codebleu
    CODEBLEU_AVAILABLE = True
except ImportError:
    CODEBLEU_AVAILABLE = False
    logger.warning("codebleu not installed. Install with: pip install codebleu")
    logger.warning("CodeBLEU score will be estimated based on other metrics.")


# -------------------- UTILS --------------------

def read_file(path: str) -> str:
    """Read file content with proper error handling."""
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        sys.exit(1)


# -------------------- AST VALIDITY --------------------

def ast_valid(code: str) -> Tuple[bool, str]:
    """Check if code is valid Python syntax."""
    try:
        ast.parse(code)
        return True, "Valid Python syntax"
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"AST parsing error: {e}"


# -------------------- CHANGE RATIO --------------------

def change_ratio(original: str, refactored: str) -> Dict[str, Any]:
    """Calculate similarity and difference metrics between codes."""
    original_lines = original.splitlines()
    refactored_lines = refactored.splitlines()
    
    matcher = difflib.SequenceMatcher(None, original, refactored)
    
    # Get detailed differences
    diff = list(difflib.unified_diff(
        original_lines,
        refactored_lines,
        lineterm=''
    ))
    
    # Count changed lines (excluding diff headers)
    changed_lines = len([line for line in diff if line.startswith(('+', '-')) 
                        and not line.startswith('+++') and not line.startswith('---')])
    
    # Count total lines
    total_lines = max(len(original_lines), len(refactored_lines))
    
    # Calculate meaningful changes (not just whitespace)
    meaningful_changes = 0
    min_length = min(len(original_lines), len(refactored_lines))
    
    for i in range(min_length):
        if original_lines[i].strip() != refactored_lines[i].strip():
            meaningful_changes += 1
    
    # Check for added/removed lines
    meaningful_changes += abs(len(original_lines) - len(refactored_lines))
    
    # Calculate similarity ratio safely
    similarity_ratio = matcher.ratio() if total_lines > 0 else 1.0
    
    return {
        "similarity_ratio": round(similarity_ratio, 3),
        "changed_lines": changed_lines,
        "total_lines": total_lines,
        "change_percentage": round((changed_lines / total_lines) * 100, 1) if total_lines > 0 else 0,
        "meaningful_changes": meaningful_changes,
        "lines_added": len(refactored_lines) - len(original_lines) if len(refactored_lines) > len(original_lines) else 0,
        "lines_removed": len(original_lines) - len(refactored_lines) if len(original_lines) > len(refactored_lines) else 0
    }


# -------------------- STYLE HEURISTIC --------------------

def analyze_code_style(code: str) -> Dict[str, Any]:
    """Analyze code style metrics."""
    lines = [line.rstrip() for line in code.splitlines() if line.strip()]
    if not lines:
        return {
            "avg_length": 0, 
            "max_length": 0, 
            "function_count": 0, 
            "descriptive_names": 0,
            "total_names": 0,
            "name_quality_score": 0,
            "avg_name_length": 0,
            "total_lines": 0,
            "comment_lines": 0,
            "docstring_count": 0
        }
    
    # Calculate line lengths
    line_lengths = [len(line) for line in lines]
    
    # Count function definitions
    function_count = sum(1 for line in lines if line.strip().startswith('def '))
    
    # Count comment lines
    comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
    
    # Analyze naming quality
    descriptive_names = 0
    total_names = 0
    name_lengths = []
    docstring_count = 0
    
    try:
        tree = ast.parse(code)
        
        # Extract variable and parameter names from AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Function name
                total_names += 1
                if (len(node.name) > MIN_NAME_LENGTH and 
                    '_' in node.name and 
                    len(node.name) <= MAX_NAME_LENGTH):
                    descriptive_names += 1
                
                # Parameter names
                for arg in node.args.args:
                    total_names += 1
                    name_lengths.append(len(arg.arg))
                    if (len(arg.arg) > MIN_NAME_LENGTH and 
                        '_' in arg.arg and 
                        len(arg.arg) <= MAX_NAME_LENGTH):
                        descriptive_names += 1
                
                # Check for docstring
                if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and
                    isinstance(node.body[0].value.value, str)):
                    docstring_count += 1
            
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                # Variable assignments
                total_names += 1
                name_lengths.append(len(node.id))
                if (len(node.id) > MIN_NAME_LENGTH and 
                    '_' in node.id and 
                    len(node.id) <= MAX_NAME_LENGTH):
                    descriptive_names += 1
    except Exception as e:
        logger.debug(f"AST analysis failed, using fallback: {e}")
        # Fallback to simple line-based analysis
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                left_side = line.split('=', 1)[0].strip()
                if left_side.isidentifier():
                    total_names += 1
                    name_lengths.append(len(left_side))
                    if (len(left_side) > MIN_NAME_LENGTH and 
                        '_' in left_side and 
                        len(left_side) <= MAX_NAME_LENGTH):
                        descriptive_names += 1
    
    # Calculate name quality score (0-1)
    name_quality_score = descriptive_names / total_names if total_names > 0 else 0
    avg_name_length = sum(name_lengths) / len(name_lengths) if name_lengths else 0
    
    return {
        "avg_length": round(sum(line_lengths) / len(line_lengths), 1),
        "max_length": max(line_lengths) if line_lengths else 0,
        "function_count": function_count,
        "descriptive_names": descriptive_names,
        "total_names": total_names,
        "name_quality_score": round(name_quality_score, 3),
        "avg_name_length": round(avg_name_length, 1),
        "total_lines": len(lines),
        "comment_lines": comment_lines,
        "docstring_count": docstring_count
    }


def style_improvement(original: str, refactored: str) -> Dict[str, Any]:
    """Evaluate style improvements between original and refactored code."""
    
    before = analyze_code_style(original)
    after = analyze_code_style(refactored)
    
    # Calculate improvement score (0-1)
    improvements = 0
    improvement_details = []
    total_checks = 6  # Increased from 5
    
    # 1. Descriptive naming improvement
    if after["name_quality_score"] > before["name_quality_score"]:
        improvements += 1
        improvement_details.append("Better naming conventions")
    elif after["name_quality_score"] >= 0.7 and before["name_quality_score"] < 0.7:
        improvements += 1
        improvement_details.append("Achieved good naming quality")
    
    # 2. Function count preserved (not decreased)
    if after["function_count"] >= before["function_count"]:
        improvements += 1
        improvement_details.append("Function count preserved or increased")
    
    # 3. Average name length (longer names are often more descriptive)
    if (after["avg_name_length"] > before["avg_name_length"] and 
        after["avg_name_length"] <= MAX_NAME_LENGTH):
        improvements += 1
        improvement_details.append("More descriptive names")
    
    # 4. Max line length (PEP 8 recommends max 79)
    before_max_ok = before["max_length"] <= MAX_LINE_LENGTH_PEP8
    after_max_ok = after["max_length"] <= MAX_LINE_LENGTH_PEP8
    
    if after_max_ok and not before_max_ok:
        improvements += 1
        improvement_details.append("Fixed overly long lines")
    elif after_max_ok and before_max_ok:
        improvements += 1
        improvement_details.append("Line length within PEP 8 limits")
    elif after["max_length"] <= MAX_LINE_LENGTH_RELAXED:
        improvements += 0.5
        improvement_details.append("Line length within relaxed limits")
    
    # 5. Average line length (optimal range 20-60)
    before_ideal = (MIN_IDEAL_LINE_LENGTH <= before["avg_length"] <= MAX_IDEAL_LINE_LENGTH)
    after_ideal = (MIN_IDEAL_LINE_LENGTH <= after["avg_length"] <= MAX_IDEAL_LINE_LENGTH)
    
    if after_ideal and not before_ideal:
        improvements += 1
        improvement_details.append("Improved line length balance")
    elif after_ideal and before_ideal:
        improvements += 1
        improvement_details.append("Maintained good line length")
    elif after["avg_length"] < MAX_IDEAL_LINE_LENGTH * 1.5:
        improvements += 0.5
        improvement_details.append("Line length acceptable")
    
    # 6. Documentation improvement
    if after["docstring_count"] > before["docstring_count"]:
        improvements += 1
        improvement_details.append("Added/improved documentation")
    elif after["comment_lines"] > before["comment_lines"]:
        improvements += 0.5
        improvement_details.append("Added more comments")
    
    style_score = improvements / total_checks if total_checks > 0 else 0.5
    
    return {
        "score": round(style_score, 3),
        "before": before,
        "after": after,
        "improvements": improvements,
        "total_checks": total_checks,
        "improvement_details": improvement_details
    }


# -------------------- CODEBLEU --------------------

def compute_codebleu(reference: str, prediction: str) -> float:
    """Compute CodeBLEU score if available, otherwise estimate."""
    if not CODEBLEU_AVAILABLE:
        return estimate_codebleu(reference, prediction)
    
    try:
        # CodeBLEU expects list of references and predictions
        result = calc_codebleu(
            references=[reference.splitlines()],
            predictions=[prediction.splitlines()],
            lang="python"
        )
        
        # Extract the codebleu score from the result dictionary
        if isinstance(result, dict):
            # Try different possible keys
            for key in ["codebleu", "CodeBLEU", "score"]:
                if key in result:
                    return round(result[key], 3)
        
        # Fallback to ngram match score
        return estimate_codebleu(reference, prediction)
            
    except Exception as e:
        logger.debug(f"CodeBLEU calculation failed: {e}")
        return estimate_codebleu(reference, prediction)


def estimate_codebleu(reference: str, prediction: str) -> float:
    """Estimate CodeBLEU based on similarity and AST validity."""
    try:
        # Calculate basic similarity
        matcher = difflib.SequenceMatcher(None, reference, prediction)
        similarity = matcher.ratio()
        
        # Check AST validity
        try:
            ast.parse(prediction)
            ast_score = 1.0
        except:
            ast_score = 0.0
        
        # Check for preserved keywords and structure
        preserved_keywords = estimate_keyword_preservation(reference, prediction)
        
        # Weighted estimate
        estimated_score = (0.3 * similarity + 0.4 * ast_score + 0.3 * preserved_keywords)
        return round(estimated_score, 3)
    except:
        return 0.5  # Fallback score


def estimate_keyword_preservation(original: str, refactored: str) -> float:
    """Estimate how well keywords and structure are preserved."""
    keywords = ['def', 'class', 'if', 'else', 'for', 'while', 'try', 'except',
                'return', 'import', 'from', 'as', 'with', 'lambda']
    
    original_counts = {}
    refactored_counts = {}
    
    for keyword in keywords:
        original_counts[keyword] = len(re.findall(r'\b' + keyword + r'\b', original))
        refactored_counts[keyword] = len(re.findall(r'\b' + keyword + r'\b', refactored))
    
    # Calculate preservation score
    total_diff = 0
    total_keywords = 0
    
    for keyword in keywords:
        diff = abs(original_counts[keyword] - refactored_counts[keyword])
        total_diff += diff
        total_keywords += original_counts[keyword]
    
    if total_keywords == 0:
        return 1.0
    
    preservation_score = 1.0 - (total_diff / (total_keywords * 2))
    return max(0.0, min(1.0, preservation_score))


# -------------------- SEMANTIC PRESERVATION --------------------

def extract_function_info(code: str) -> Dict[str, Dict[str, Any]]:
    """Extract function signatures from code."""
    try:
        tree = ast.parse(code)
        functions = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get function name
                func_name = node.name
                
                # Get parameters
                params = [arg.arg for arg in node.args.args]
                
                # Count returns
                returns = sum(1 for n in ast.walk(node) if isinstance(n, ast.Return))
                
                # Get return statements
                return_values = []
                for n in ast.walk(node):
                    if isinstance(n, ast.Return) and n.value:
                        # Get return expression type
                        if isinstance(n.value, ast.Name):
                            return_values.append(n.value.id)
                        elif isinstance(n.value, ast.Constant):
                            return_values.append("constant")
                        elif isinstance(n.value, ast.BinOp):
                            return_values.append("binary_operation")
                        elif isinstance(n.value, ast.Call):
                            return_values.append("function_call")
                        else:
                            return_values.append("other")
                
                # Get decorators
                decorators = []
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        decorators.append(decorator.attr)
                
                functions[func_name] = {
                    "params": params,
                    "param_count": len(params),
                    "has_return": returns > 0,
                    "return_count": returns,
                    "return_types": return_values,
                    "decorators": decorators,
                    "lineno": node.lineno
                }
        
        return functions
    except Exception as e:
        logger.debug(f"Function extraction failed: {e}")
        return {}


def check_semantic_preservation(original: str, refactored: str) -> Dict[str, Any]:
    """Check if refactoring preserves semantics (function signatures and structure)."""
    
    original_funcs = extract_function_info(original)
    refactored_funcs = extract_function_info(refactored)
    
    # Check if same number of functions
    if len(original_funcs) != len(refactored_funcs):
        return {
            "preserved": False,
            "score": 0.0,
            "message": f"Function count changed: {len(original_funcs)} → {len(refactored_funcs)}",
            "details": {
                "original_count": len(original_funcs),
                "refactored_count": len(refactored_funcs)
            }
        }
    
    if not original_funcs:
        return {
            "preserved": True,
            "score": 1.0,
            "message": "No functions to preserve",
            "details": {}
        }
    
    # For semantic preservation, match functions by signature patterns
    original_patterns = []
    for func_name, func_info in original_funcs.items():
        pattern = {
            "param_count": func_info["param_count"],
            "has_return": func_info["has_return"],
            "return_type_count": len(func_info["return_types"]),
            "decorator_count": len(func_info["decorators"])
        }
        original_patterns.append(pattern)
    
    refactored_patterns = []
    for func_name, func_info in refactored_funcs.items():
        pattern = {
            "param_count": func_info["param_count"],
            "has_return": func_info["has_return"],
            "return_type_count": len(func_info["return_types"]),
            "decorator_count": len(func_info["decorators"])
        }
        refactored_patterns.append(pattern)
    
    # Sort patterns to match regardless of order
    original_patterns.sort(key=lambda x: (x["param_count"], x["has_return"], 
                                          x["return_type_count"], x["decorator_count"]))
    refactored_patterns.sort(key=lambda x: (x["param_count"], x["has_return"], 
                                            x["return_type_count"], x["decorator_count"]))
    
    # Check if patterns match
    if original_patterns == refactored_patterns:
        return {
            "preserved": True,
            "score": 1.0,
            "message": "Function structure and logic preserved",
            "details": {
                "matched_functions": len(original_funcs),
                "total_functions": len(original_funcs)
            }
        }
    else:
        # Calculate match score
        matches = 0
        total = len(original_patterns)
        
        # Try to match patterns optimally
        used_refactored = set()
        for orig_pattern in original_patterns:
            best_match_idx = -1
            best_match_score = 0
            
            for i, ref_pattern in enumerate(refactored_patterns):
                if i in used_refactored:
                    continue
                
                # Calculate similarity score
                score = 0
                if orig_pattern["param_count"] == ref_pattern["param_count"]:
                    score += 0.5
                if orig_pattern["has_return"] == ref_pattern["has_return"]:
                    score += 0.3
                if orig_pattern["return_type_count"] == ref_pattern["return_type_count"]:
                    score += 0.2
                
                if score > best_match_score:
                    best_match_score = score
                    best_match_idx = i
            
            if best_match_idx != -1 and best_match_score >= 0.7:
                matches += 1
                used_refactored.add(best_match_idx)
        
        score = matches / total if total > 0 else 0
        
        return {
            "preserved": score > 0.7,
            "score": round(score, 2),
            "message": f"Partial structure preservation ({matches}/{total} functions match)",
            "details": {
                "matched_functions": matches,
                "total_functions": total,
                "match_percentage": round(score * 100, 1)
            }
        }


# -------------------- CONFIDENCE SCORE --------------------

def compute_confidence_score(
    original_code: str,
    refactored_code: str,
    ast_validity: bool,
    change_metrics: Dict[str, Any],
    style_metrics: Dict[str, Any],
    codebleu_score: float,
    semantic_score: float
) -> Dict[str, Any]:
    """Compute overall confidence score for refactoring with proper normalization."""
    
    # Collect available components and their scores
    components = {}
    
    # AST validity
    components["ast_validity"] = 1.0 if ast_validity else 0.0
    
    # CodeBLEU
    components["codebleu"] = max(0.0, min(1.0, codebleu_score))
    
    # Style
    components["style"] = max(0.0, min(1.0, style_metrics.get("score", 0.5)))
    
    # Change score
    similarity_ratio = change_metrics.get("similarity_ratio", 0.5)
    meaningful_changes = change_metrics.get("meaningful_changes", 0)
    
    if 0.3 <= similarity_ratio <= 0.7:
        if meaningful_changes >= MIN_MEANINGFUL_CHANGES:
            change_score = 1.0
        else:
            change_score = 0.7
    elif similarity_ratio < 0.3:
        # Too much change - might be rewriting
        change_score = 0.5
    else:
        # Too little change - might not be actual refactoring
        change_score = 0.3
    components["change"] = change_score
    
    # Semantic
    components["semantic"] = max(0.0, min(1.0, semantic_score))
    
    # Define base weights
    base_weights = {
        "ast_validity": 0.20,
        "codebleu": 0.20,
        "style": 0.20,
        "change": 0.20,
        "semantic": 0.20
    }
    
    # Filter to available components
    available_components = [k for k in base_weights if k in components]
    
    if not available_components:
        return {
            "score": 0.5,
            "status": "⚠ INSUFFICIENT DATA",
            "components": components,
            "weights": base_weights,
            "normalized_weights": {}
        }
    
    # Normalize weights for available components
    total_weight = sum(base_weights[k] for k in available_components)
    normalized_weights = {
        k: base_weights[k] / total_weight 
        for k in available_components
    }
    
    # Calculate weighted confidence
    confidence = sum(
        normalized_weights[k] * components[k] 
        for k in available_components
    )
    
    # Ensure confidence is between 0 and 1
    confidence = max(0.0, min(1.0, confidence))
    
    # Determine status with more granular categories
    if confidence >= 0.85:
        status = "✅ EXCELLENT"
    elif confidence >= 0.75:
        status = "✅ GOOD"
    elif confidence >= 0.65:
        status = "⚠ MODERATE"
    elif confidence >= 0.5:
        status = "⚠ MARGINAL"
    else:
        status = "❌ POOR"
    
    return {
        "score": round(confidence, 3),
        "status": status,
        "components": {k: round(v, 3) for k, v in components.items()},
        "weights": base_weights,
        "normalized_weights": {k: round(v, 3) for k, v in normalized_weights.items()}
    }


# -------------------- DETAILED ANALYSIS --------------------

def analyze_refactoring(original: str, refactored: str) -> Dict[str, Any]:
    """Perform comprehensive analysis of refactoring."""
    
    # AST validity
    ast_validity, ast_message = ast_valid(refactored)
    
    # Change metrics
    change_metrics = change_ratio(original, refactored)
    
    # Style metrics
    style_metrics = style_improvement(original, refactored)
    
    # CodeBLEU score
    codebleu_score = compute_codebleu(original, refactored)
    
    # Semantic preservation
    semantic_metrics = check_semantic_preservation(original, refactored)
    
    # Confidence score
    confidence = compute_confidence_score(
        original, refactored,
        ast_validity, change_metrics,
        style_metrics, codebleu_score,
        semantic_metrics["score"]
    )
    
    return {
        "ast_validity": {"valid": ast_validity, "message": ast_message},
        "change_metrics": change_metrics,
        "style_metrics": style_metrics,
        "codebleu_score": codebleu_score,
        "semantic_preservation": semantic_metrics,
        "confidence": confidence
    }


# -------------------- OUTPUT SAVING --------------------

def save_evaluation_report(
    analysis: Dict[str, Any],
    original_code: str,
    refactored_code: str,
    output_file: str = "refactoring_evaluation_report.txt"
) -> None:
    """Save the complete evaluation report to a file."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_lines = []
    
    # Header
    report_lines.append("="*60)
    report_lines.append("🔍 REFACTORING QUALITY EVALUATION REPORT")
    report_lines.append("="*60)
    report_lines.append(f"Generated: {timestamp}")
    report_lines.append(f"Output file: {output_file}")
    report_lines.append("")
    
    # Basic info
    report_lines.append("📄 CODE STATISTICS")
    report_lines.append("-"*60)
    orig_lines = len(original_code.splitlines())
    ref_lines = len(refactored_code.splitlines())
    report_lines.append(f"Original code: {orig_lines} lines, {len(original_code)} chars")
    report_lines.append(f"Refactored code: {ref_lines} lines, {len(refactored_code)} chars")
    report_lines.append(f"Line count change: {ref_lines - orig_lines:+d} lines")
    report_lines.append("")
    
    # AST Validity
    ast_info = analysis["ast_validity"]
    report_lines.append("✅ AST VALIDITY")
    report_lines.append("-"*60)
    report_lines.append(f"Status: {'✅ VALID' if ast_info['valid'] else '❌ INVALID'}")
    if not ast_info["valid"]:
        report_lines.append(f"Error: {ast_info['message']}")
    report_lines.append("")
    
    # Change Metrics
    change = analysis["change_metrics"]
    report_lines.append("📈 CHANGE ANALYSIS")
    report_lines.append("-"*60)
    report_lines.append(f"Similarity Ratio: {change['similarity_ratio']} (0.3-0.7 is ideal)")
    report_lines.append(f"Meaningful Changes: {change['meaningful_changes']} (≥3 is good)")
    report_lines.append(f"Changed Lines: {change['changed_lines']}/{change['total_lines']}")
    report_lines.append(f"Change Percentage: {change['change_percentage']}%")
    report_lines.append(f"Lines Added: {change.get('lines_added', 0)}")
    report_lines.append(f"Lines Removed: {change.get('lines_removed', 0)}")
    report_lines.append("")
    
    # Style Metrics
    style = analysis["style_metrics"]
    report_lines.append("🎨 STYLE ANALYSIS")
    report_lines.append("-"*60)
    report_lines.append(f"Score: {style['score']}/1.0 ({style['improvements']}/{style['total_checks']} improvements)")
    if style["improvement_details"]:
        report_lines.append(f"Improvements: {', '.join(style['improvement_details'])}")
    report_lines.append(f"Avg Line Length: {style['before']['avg_length']} → {style['after']['avg_length']} "
                       f"(ideal {MIN_IDEAL_LINE_LENGTH}-{MAX_IDEAL_LINE_LENGTH})")
    report_lines.append(f"Max Line Length: {style['before']['max_length']} → {style['after']['max_length']} "
                       f"(PEP 8 max {MAX_LINE_LENGTH_PEP8})")
    report_lines.append(f"Name Quality: {style['before']['name_quality_score']:.3f} → {style['after']['name_quality_score']:.3f}")
    report_lines.append(f"Avg Name Length: {style['before']['avg_name_length']} → {style['after']['avg_name_length']}")
    report_lines.append(f"Functions: {style['before']['function_count']} → {style['after']['function_count']}")
    report_lines.append(f"Docstrings: {style['before']['docstring_count']} → {style['after']['docstring_count']}")
    report_lines.append("")
    
    # CodeBLEU
    report_lines.append("🤖 CODEBLEU SCORE")
    report_lines.append("-"*60)
    report_lines.append(f"Score: {analysis['codebleu_score']}")
    if analysis['codebleu_score'] < 0.5:
        report_lines.append("Note: Low CodeBLEU score suggests significant code changes")
    report_lines.append("")
    
    # Semantic Preservation
    semantic = analysis["semantic_preservation"]
    report_lines.append("🔗 SEMANTIC PRESERVATION")
    report_lines.append("-"*60)
    report_lines.append(f"Score: {semantic['score']}/1.0")
    report_lines.append(f"Status: {semantic['message']}")
    if "details" in semantic and semantic["details"]:
        details = semantic["details"]
        if "match_percentage" in details:
            report_lines.append(f"Match Rate: {details['match_percentage']}%")
    report_lines.append("")
    
    # Confidence Score
    conf = analysis["confidence"]
    report_lines.append("💯 OVERALL CONFIDENCE SCORE")
    report_lines.append("-"*60)
    report_lines.append(f"Score: {conf['score']}/1.0")
    report_lines.append(f"Status: {conf['status']}")
    report_lines.append("")
    
    report_lines.append("Component Scores:")
    for name, score in conf["components"].items():
        weight = conf["weights"][name] * 100
        bar_length = int(score * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        report_lines.append(f"  - {name.title().replace('_', ' '):<15} {bar} {score:.3f} ({weight:.0f}%)")
    report_lines.append("")
    
    # Verdict
    report_lines.append("="*60)
    report_lines.append("📋 FINAL VERDICT")
    report_lines.append("="*60)
    
    score = conf["score"]
    if score >= 0.75:
        report_lines.append("✅ Refactoring ACCEPTED - Good to excellent quality")
        report_lines.append("   The refactored code maintains functionality with improved readability.")
    elif score >= 0.65:
        report_lines.append("⚠ Refactoring CONDITIONALLY ACCEPTED - Needs review")
        report_lines.append("   Verify that all functionality is preserved and improvements are meaningful.")
    else:
        report_lines.append("❌ Refactoring REJECTED - Low quality or risky changes")
        report_lines.append("   The changes may have introduced issues or didn't provide sufficient improvement.")
    report_lines.append("")
    
    # Recommendations
    report_lines.append("📝 RECOMMENDATIONS")
    report_lines.append("-"*60)
    
    style_data = style["after"]
    change_data = change
    
    recommendations = []
    
    # Line length recommendations
    if style_data["avg_length"] > MAX_IDEAL_LINE_LENGTH:
        recommendations.append("Consider splitting long lines for better readability")
    elif style_data["avg_length"] < MIN_IDEAL_LINE_LENGTH:
        recommendations.append("Lines are very short; consider combining related operations")
    
    # Max line length recommendations
    if style_data["max_length"] > MAX_LINE_LENGTH_PEP8:
        recommendations.append(f"Some lines exceed PEP 8 limit of {MAX_LINE_LENGTH_PEP8} characters")
    
    # Name quality recommendations
    if style_data["name_quality_score"] < 0.7:
        recommendations.append("Improve variable/parameter names for better clarity")
    
    # Documentation recommendations
    if style_data["docstring_count"] < style_data["function_count"]:
        recommendations.append("Add docstrings to functions without documentation")
    
    # Change recommendations
    if change_data["similarity_ratio"] < 0.3:
        recommendations.append("Extensive changes made; ensure all original functionality is preserved")
    elif change_data["similarity_ratio"] > 0.8:
        recommendations.append("Very few changes made; consider if more refactoring is needed")
    
    # Code structure recommendations
    if style_data["function_count"] > 5:
        recommendations.append("Consider modularizing code into separate functions/files")
    
    # General recommendations based on score
    if score < 0.7:
        recommendations.append("Run unit tests to verify functionality")
        recommendations.append("Consider peer review of the refactored code")
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            report_lines.append(f"{i}. {rec}")
    else:
        report_lines.append("No specific recommendations - refactoring is already good!")
    report_lines.append("")
    
    # Comparison Summary
    report_lines.append("="*60)
    report_lines.append("🔍 COMPARISON SUMMARY")
    report_lines.append("="*60)
    report_lines.append("")
    report_lines.append("Original → Refactored:")
    report_lines.append(f"  Functions: {style['before']['function_count']} → {style['after']['function_count']}")
    report_lines.append(f"  Line length: {style['before']['avg_length']} → {style['after']['avg_length']}")
    report_lines.append(f"  Name quality: {style['before']['name_quality_score']:.2f} → {style['after']['name_quality_score']:.2f}")
    report_lines.append(f"  Docstrings: {style['before']['docstring_count']} → {style['after']['docstring_count']}")
    report_lines.append(f"  Meaningful changes: {change['meaningful_changes']}")
    report_lines.append("")
    
    # Code Comparison (excerpt)
    report_lines.append("="*60)
    report_lines.append("📝 CODE COMPARISON (EXCERPT)")
    report_lines.append("="*60)
    report_lines.append("")
    
    # Show first 5 lines of each
    orig_lines = original_code.splitlines()[:5]
    refact_lines = refactored_code.splitlines()[:5]
    
    report_lines.append("ORIGINAL (first 5 lines):")
    for i, line in enumerate(orig_lines, 1):
        report_lines.append(f"  {i:2d}: {line}")
    
    report_lines.append("")
    report_lines.append("REFACTORED (first 5 lines):")
    for i, line in enumerate(refact_lines, 1):
        report_lines.append(f"  {i:2d}: {line}")
    
    # Save to file
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        logger.info(f"Report saved to: {output_file}")
    except Exception as e:
        logger.error(f"Could not save report to file: {e}")


# -------------------- MAIN --------------------

def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("🔍 REFACTORING QUALITY EVALUATION TOOL")
    print("="*60)
    
    # Get output filename from command line or use default
    output_file = "refactoring_evaluation_report.txt"
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    
    # Check if codebleu is available
    if not CODEBLEU_AVAILABLE:
        print("\n⚠ CodeBLEU is not installed. Using similarity-based estimate.")
        print("  For more accurate results, install with: pip install codebleu")
    
    # Default input files
    input_files = [
        ("input_code.py", "codet5_refactored.py"),
        ("original_code.py", "refactored_code.py")
    ]
    
    original_code = None
    refactored_code = None
    
    # Try to find input files
    for orig_file, ref_file in input_files:
        try:
            original_code = read_file(orig_file)
            refactored_code = read_file(ref_file)
            print(f"\n📄 Using: {orig_file} and {ref_file}")
            break
        except (FileNotFoundError, SystemExit):
            continue
    
    if original_code is None or refactored_code is None:
        print("\n❌ Could not find input files. Please provide:")
        print("   - input_code.py (original code)")
        print("   - codet5_refactored.py (refactored code)")
        sys.exit(1)
    
    print(f"\n📄 Original code: {len(original_code.splitlines())} lines, {len(original_code)} chars")
    print(f"📄 Refactored code: {len(refactored_code.splitlines())} lines, {len(refactored_code)} chars")
    
    # Perform analysis
    analysis = analyze_refactoring(original_code, refactored_code)
    
    # Display results to console
    print("\n" + "="*60)
    print("📊 EVALUATION RESULTS")
    print("="*60)
    
    # AST Validity
    ast_info = analysis["ast_validity"]
    print(f"\n✅ AST Validity: {'✅ VALID' if ast_info['valid'] else '❌ INVALID'}")
    if not ast_info["valid"]:
        print(f"   Message: {ast_info['message']}")
    
    # Change Metrics
    change = analysis["change_metrics"]
    print(f"\n📈 Change Analysis:")
    print(f"   Similarity Ratio: {change['similarity_ratio']} (0.3-0.7 is ideal)")
    print(f"   Meaningful Changes: {change['meaningful_changes']} (≥3 is good)")
    print(f"   Changed Lines: {change['changed_lines']}/{change['total_lines']}")
    print(f"   Change Percentage: {change['change_percentage']}%")
    
    # Style Metrics
    style = analysis["style_metrics"]
    print(f"\n🎨 Style Analysis:")
    print(f"   Score: {style['score']}/1.0 ({style['improvements']}/{style['total_checks']} improvements)")
    if style["improvement_details"]:
        print(f"   Improvements: {', '.join(style['improvement_details'][:3])}")
    print(f"   Avg Line Length: {style['before']['avg_length']} → {style['after']['avg_length']}")
    print(f"   Max Line Length: {style['before']['max_length']} → {style['after']['max_length']}")
    print(f"   Name Quality: {style['before']['name_quality_score']} → {style['after']['name_quality_score']}")
    print(f"   Functions: {style['before']['function_count']} → {style['after']['function_count']}")
    
    # CodeBLEU
    print(f"\n🤖 CodeBLEU Score: {analysis['codebleu_score']}")
    if analysis['codebleu_score'] < 0.5:
        print("   Note: Low CodeBLEU score suggests significant code changes")
    
    # Semantic Preservation
    semantic = analysis["semantic_preservation"]
    print(f"\n🔗 Semantic Preservation: {semantic['score']}/1.0")
    print(f"   {semantic['message']}")
    
    # Confidence Score
    conf = analysis["confidence"]
    print(f"\n💯 OVERALL CONFIDENCE SCORE: {conf['score']}/1.0")
    print(f"   Status: {conf['status']}")
    print(f"\n   Component Scores:")
    for name, score in conf["components"].items():
        weight = conf["weights"][name] * 100
        bar_length = int(score * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"   - {name.title().replace('_', ' '):<15} {bar} {score:.3f} ({weight:.0f}%)")
    
    print("\n" + "="*60)
    print("📋 FINAL VERDICT")
    print("="*60)
    
    score = conf["score"]
    if score >= 0.75:
        print("✅ Refactoring ACCEPTED - Good to excellent quality")
        print("   The refactored code maintains functionality with improved readability.")
    elif score >= 0.65:
        print("⚠ Refactoring CONDITIONALLY ACCEPTED - Needs review")
        print("   Verify that all functionality is preserved and improvements are meaningful.")
    else:
        print("❌ Refactoring REJECTED - Low quality or risky changes")
        print("   The changes may have introduced issues or didn't provide sufficient improvement.")
    
    # Generate specific recommendations
    print(f"\n📝 Recommendations:")
    
    style_data = style["after"]
    change_data = change
    
    # Line length recommendations
    if style_data["avg_length"] > MAX_IDEAL_LINE_LENGTH:
        print("   - Consider splitting long lines for better readability")
    elif style_data["avg_length"] < MIN_IDEAL_LINE_LENGTH:
        print("   - Lines are very short; consider combining related operations")
    
    # Max line length recommendations
    if style_data["max_length"] > MAX_LINE_LENGTH_PEP8:
        print(f"   - Some lines exceed PEP 8 limit of {MAX_LINE_LENGTH_PEP8} characters")
    
    # Name quality recommendations
    if style_data["name_quality_score"] < 0.7:
        print("   - Improve variable/parameter names for better clarity")
    
    # Documentation recommendations
    if style_data["docstring_count"] < style_data["function_count"]:
        print("   - Add docstrings to functions without documentation")
    
    # Change recommendations
    if change_data["similarity_ratio"] < 0.3:
        print("   - Extensive changes made; ensure all original functionality is preserved")
    elif change_data["similarity_ratio"] > 0.8:
        print("   - Very few changes made; consider if more refactoring is needed")
    
    # Code structure recommendations
    if style_data["function_count"] > 5:
        print("   - Consider modularizing code into separate functions/files")
    
    # General recommendations based on score
    if score < 0.7:
        print("   - Run unit tests to verify functionality")
        print("   - Consider peer review of the refactored code")
    
    print("\n" + "="*60)
    print("🔍 COMPARISON SUMMARY")
    print("="*60)
    
    # Show quick comparison
    print("\nOriginal → Refactored:")
    print(f"  Functions: {style['before']['function_count']} → {style['after']['function_count']}")
    print(f"  Line length: {style['before']['avg_length']} → {style['after']['avg_length']}")
    print(f"  Name quality: {style['before']['name_quality_score']:.2f} → {style['after']['name_quality_score']:.2f}")
    print(f"  Docstrings: {style['before']['docstring_count']} → {style['after']['docstring_count']}")
    print(f"  Meaningful changes: {change['meaningful_changes']}")
    
    print("\n" + "="*60)
    
    # Save detailed report to file
    save_evaluation_report(analysis, original_code, refactored_code, output_file)
    
    # Also save the analysis as JSON for programmatic use
    json_output = output_file.replace('.txt', '.json')
    try:
        # Remove large code fields for JSON
        json_analysis = analysis.copy()
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(json_analysis, f, indent=2, default=str)
        print(f"📁 JSON analysis saved to: {json_output}")
    except Exception as e:
        logger.warning(f"Could not save JSON: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Evaluation interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)