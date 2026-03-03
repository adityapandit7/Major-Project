import ast
import difflib
import sys
import re
from pathlib import Path
from typing import Dict, Any, Tuple

# Try to import codebleu, but provide comprehensive fallback
try:
    from codebleu import calc_codebleu
    CODEBLEU_AVAILABLE = True
except ImportError:
    print("⚠ Warning: codebleu not installed. Install with: pip install codebleu")
    CODEBLEU_AVAILABLE = False


# -------------------- UTILS --------------------

def read_file(path: str) -> str:
    """Read file with proper error handling"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Error: File '{path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file '{path}': {e}")
        sys.exit(1)


# -------------------- AST VALIDITY --------------------

def ast_valid(code: str) -> Tuple[float, str]:
    """Check if code is valid Python syntax and return score with message"""
    try:
        ast.parse(code)
        return 1.0, "Valid Python syntax"
    except SyntaxError as e:
        error_msg = f"Syntax error: {str(e).split(':')[-1].strip()}"
        return 0.0, error_msg


# -------------------- CHANGE RATIO --------------------

def change_ratio(original: str, refactored: str) -> Tuple[float, str]:
    """Calculate similarity ratio between two code snippets"""
    if not original or not refactored:
        return 0.0, "Empty input"
    
    matcher = difflib.SequenceMatcher(None, original, refactored)
    ratio = round(matcher.ratio(), 3)
    
    if ratio > 0.9:
        message = "Very similar (minimal changes)"
    elif ratio > 0.7:
        message = "Moderately similar"
    elif ratio > 0.5:
        message = "Significantly different"
    elif ratio > 0.3:
        message = "Very different"
    else:
        message = "Extremely different"
    
    return ratio, message


# -------------------- STYLE IMPROVEMENT --------------------

def style_improvement(original: str, refactored: str) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluate style improvements based on multiple metrics
    Returns score and detailed metrics
    """
    
    def avg_line_length(code: str) -> float:
        """Calculate average line length"""
        lines = [line.rstrip() for line in code.splitlines() if line.strip()]
        if not lines:
            return 0
        return sum(len(line) for line in lines) / len(lines)
    
    def count_long_lines(code: str, max_length: int = 79) -> int:
        """Count lines exceeding max length (PEP8)"""
        return sum(1 for line in code.splitlines() if len(line.rstrip()) > max_length)
    
    def analyze_naming(code: str) -> Dict[str, Any]:
        """Analyze naming conventions in code"""
        try:
            tree = ast.parse(code)
            short_names = []
            descriptive_names = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Function names
                    if len(node.name) <= 3:
                        short_names.append(f"function '{node.name}'")
                    elif '_' in node.name or node.name.islower():
                        descriptive_names.append(f"function '{node.name}'")
                    
                    # Parameter names
                    for arg in node.args.args:
                        if len(arg.arg) == 1 and arg.arg.isalpha():
                            short_names.append(f"parameter '{arg.arg}' in '{node.name}'")
                        elif '_' in arg.arg or arg.arg.islower():
                            descriptive_names.append(f"parameter '{arg.arg}' in '{node.name}'")
                
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    # Variable names
                    if len(node.id) == 1 and node.id.isalpha():
                        short_names.append(f"variable '{node.id}'")
                    elif '_' in node.id or node.id.islower():
                        descriptive_names.append(f"variable '{node.id}'")
            
            return {
                "short_names": short_names,
                "descriptive_names": descriptive_names,
                "short_count": len(short_names),
                "descriptive_count": len(descriptive_names)
            }
        except:
            return {"short_names": [], "descriptive_names": [], "short_count": 0, "descriptive_count": 0}
    
    # Calculate metrics
    before_avg_len = avg_line_length(original)
    after_avg_len = avg_line_length(refactored)
    
    before_long_lines = count_long_lines(original)
    after_long_lines = count_long_lines(refactored)
    
    before_naming = analyze_naming(original)
    after_naming = analyze_naming(refactored)
    
    # Calculate improvement scores (0-1)
    
    # 1. Line length score
    length_score = 0.5
    if before_avg_len > 0:
        if after_avg_len < before_avg_len:
            reduction = (before_avg_len - after_avg_len) / before_avg_len
            length_score = 0.5 + min(0.5, reduction)
        elif after_avg_len > before_avg_len:
            increase = (after_avg_len - before_avg_len) / before_avg_len
            length_score = 0.5 - min(0.5, increase * 0.5)
    
    # 2. PEP8 long lines score
    pep8_score = 0.5
    if before_long_lines > 0 or after_long_lines > 0:
        if after_long_lines < before_long_lines:
            improvement = (before_long_lines - after_long_lines) / (before_long_lines + 1)
            pep8_score = 0.5 + min(0.5, improvement)
        elif after_long_lines > before_long_lines:
            regression = (after_long_lines - before_long_lines) / (after_long_lines + 1)
            pep8_score = 0.5 - min(0.5, regression * 0.5)
    
    # 3. Naming score
    naming_score = 0.5
    if before_naming["short_count"] > 0 or after_naming["short_count"] > 0:
        if after_naming["short_count"] < before_naming["short_count"]:
            improvement = (before_naming["short_count"] - after_naming["short_count"]) / (before_naming["short_count"] + 1)
            naming_score = 0.5 + min(0.5, improvement)
        elif after_naming["short_count"] > before_naming["short_count"]:
            regression = (after_naming["short_count"] - before_naming["short_count"]) / (after_naming["short_count"] + 1)
            naming_score = 0.5 - min(0.5, regression * 0.5)
    
    # 4. Descriptive names improvement
    descriptive_score = 0.5
    if after_naming["descriptive_count"] > before_naming["descriptive_count"]:
        improvement = (after_naming["descriptive_count"] - before_naming["descriptive_count"]) / (before_naming["descriptive_count"] + 1)
        descriptive_score = 0.5 + min(0.5, improvement * 0.5)
    
    # Weighted average of scores
    style_score = (0.3 * length_score + 0.2 * pep8_score + 
                   0.3 * naming_score + 0.2 * descriptive_score)
    style_score = max(0.0, min(1.0, style_score))
    
    # Prepare detailed metrics
    metrics = {
        "avg_line_length": {
            "before": round(before_avg_len, 1),
            "after": round(after_avg_len, 1),
            "change": round(after_avg_len - before_avg_len, 1)
        },
        "long_lines": {
            "before": before_long_lines,
            "after": after_long_lines,
            "change": after_long_lines - before_long_lines
        },
        "naming": {
            "short_names_before": before_naming["short_names"],
            "short_names_after": after_naming["short_names"],
            "descriptive_names_before": before_naming["descriptive_names"],
            "descriptive_names_after": after_naming["descriptive_names"]
        }
    }
    
    return round(style_score, 3), metrics


# -------------------- CODEBLEU --------------------

def compute_codebleu(reference: str, prediction: str) -> Tuple[float, str]:
    """Compute CodeBLEU score with robust error handling"""
    if not CODEBLEU_AVAILABLE:
        # Fallback: compute a simple similarity score
        tokens_ref = re.findall(r'\b\w+\b', reference)
        tokens_pred = re.findall(r'\b\w+\b', prediction)
        
        common_tokens = set(tokens_ref) & set(tokens_pred)
        total_tokens = set(tokens_ref) | set(tokens_pred)
        
        if total_tokens:
            token_similarity = len(common_tokens) / len(total_tokens)
        else:
            token_similarity = 0.5
        
        # Adjust for typical refactoring scenarios
        adjusted_score = 0.3 + (token_similarity * 0.4)
        return round(adjusted_score, 3), "Fallback token similarity (codebleu not installed)"
    
    try:
        # Try different parameter combinations for codebleu
        try:
            result = calc_codebleu(
                references=[reference],
                predictions=[prediction],
                lang="python"
            )
        except TypeError:
            # Try alternative parameter format
            result = calc_codebleu(
                [reference],  # references
                [prediction],  # predictions
                lang="python",
                weights=(0.25, 0.25, 0.25, 0.25)
            )
        
        score = round(result["codebleu"], 3)
        message = "CodeBLEU semantic similarity"
        return score, message
        
    except Exception as e:
        error_msg = str(e)
        print(f"⚠ CodeBLEU error details: {error_msg}")
        
        # Fallback calculation
        # 1. Check if same functions exist
        try:
            orig_tree = ast.parse(reference)
            refac_tree = ast.parse(prediction)
            
            orig_funcs = [n.name for n in ast.walk(orig_tree) if isinstance(n, ast.FunctionDef)]
            refac_funcs = [n.name for n in ast.walk(refac_tree) if isinstance(n, ast.FunctionDef)]
            
            func_match = len(set(orig_funcs) & set(refac_funcs)) / max(len(set(orig_funcs)), 1)
            
            # 2. Basic token similarity
            tokens_ref = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', reference)
            tokens_pred = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', prediction)
            
            common_tokens = set(tokens_ref) & set(tokens_pred)
            total_unique = len(set(tokens_ref) | set(tokens_pred))
            
            if total_unique > 0:
                token_similarity = len(common_tokens) / total_unique
            else:
                token_similarity = 0.5
            
            # Combined score
            fallback_score = (func_match * 0.6 + token_similarity * 0.4)
            return round(fallback_score, 3), f"Fallback similarity (CodeBLEU failed: {error_msg[:50]}...)"
            
        except Exception as inner_e:
            return 0.5, f"Emergency fallback (multiple errors: {str(inner_e)[:30]}...)"


# -------------------- CONFIDENCE SCORE --------------------

def compute_confidence_score(
    original_code: str,
    refactored_code: str,
    ast_score: float,
    change_score: float,
    style_score: float,
    codebleu_score: float
) -> Tuple[float, Dict[str, float]]:
    """Compute overall confidence score for refactoring"""
    
    # Normalize all scores to 0-1 range
    ast_norm = max(0.0, min(1.0, ast_score))
    change_norm = max(0.0, min(1.0, change_score))
    style_norm = max(0.0, min(1.0, style_score))
    codebleu_norm = max(0.0, min(1.0, codebleu_score))
    
    # Adjusted weights based on refactoring goals
    weights = {
        "ast": 0.30,      # Syntax validity is crucial
        "codebleu": 0.30, # Semantic preservation
        "style": 0.25,    # Code quality improvement
        "change": 0.15    # Appropriate amount of change
    }
    
    confidence = (
        weights["ast"] * ast_norm +
        weights["codebleu"] * codebleu_norm +
        weights["style"] * style_norm +
        weights["change"] * (0.3 + 0.7 * change_norm)  # Slight bias toward some change
    )
    
    confidence = max(0.0, min(1.0, confidence))
    
    # Component scores for debugging
    components = {
        "ast_component": round(weights["ast"] * ast_norm, 3),
        "codebleu_component": round(weights["codebleu"] * codebleu_norm, 3),
        "style_component": round(weights["style"] * style_norm, 3),
        "change_component": round(weights["change"] * (0.3 + 0.7 * change_norm), 3)
    }
    
    return round(confidence, 3), components


# -------------------- MAIN --------------------

def main():
    """Main evaluation function"""
    print("\n" + "="*60)
    print("📊 REFACTORING EVALUATION TOOL")
    print("="*60)
    
    # Check if files exist
    input_file = "input_code.py"
    output_file = "refactored_output.py"
    
    if not Path(input_file).exists():
        print(f"❌ Input file '{input_file}' not found")
        sys.exit(1)
    
    if not Path(output_file).exists():
        print(f"❌ Refactored file '{output_file}' not found")
        sys.exit(1)
    
    print(f"📂 Input file: {input_file}")
    print(f"📂 Refactored file: {output_file}")
    print("-" * 60)
    
    # Read files
    original_code = read_file(input_file)
    refactored_code = read_file(output_file)
    
    # Basic info
    orig_lines = original_code.splitlines()
    refac_lines = refactored_code.splitlines()
    
    print(f"📝 Original: {len(orig_lines)} lines, {len(original_code)} chars")
    print(f"📝 Refactored: {len(refac_lines)} lines, {len(refactored_code)} chars")
    print("-" * 60)
    
    # Calculate all metrics
    print("\n🔍 Calculating metrics...")
    
    ast_score, ast_message = ast_valid(refactored_code)
    change_score, change_message = change_ratio(original_code, refactored_code)
    codebleu_score, codebleu_message = compute_codebleu(original_code, refactored_code)
    style_score, style_details = style_improvement(original_code, refactored_code)
    
    confidence_score, confidence_components = compute_confidence_score(
        original_code, refactored_code, ast_score, change_score, 
        style_score, codebleu_score
    )
    
    # Display results
    print("\n" + "="*60)
    print("📊 EVALUATION RESULTS")
    print("="*60)
    
    # Main metrics table
    print("\n📈 CORE METRICS:")
    print("-" * 40)
    print(f"{'✓' if ast_score == 1.0 else '✗'} AST Validity:      {ast_score:.3f} - {ast_message}")
    print(f"🔄 Change Ratio:       {change_score:.3f} - {change_message}")
    print(f"🎨 Style Improvement:  {style_score:.3f}")
    print(f"🧠 Semantic Similarity: {codebleu_score:.3f} - {codebleu_message}")
    print("-" * 40)
    print(f"🚀 CONFIDENCE SCORE:   {confidence_score:.3f}/1.0")
    print("="*60)
    
    # Style details
    print("\n🎯 STYLE IMPROVEMENT DETAILS:")
    print("-" * 40)
    print(f"Average line length: {style_details['avg_line_length']['before']} → {style_details['avg_line_length']['after']} chars ({style_details['avg_line_length']['change']:+g})")
    print(f"Long lines (>79 chars): {style_details['long_lines']['before']} → {style_details['long_lines']['after']} ({style_details['long_lines']['change']:+g})")
    
    # Naming improvements
    before_short = len(style_details['naming']['short_names_before'])
    after_short = len(style_details['naming']['short_names_after'])
    if before_short > 0 or after_short > 0:
        print(f"\n📝 NAMING IMPROVEMENTS:")
        print(f"  Short names: {before_short} → {after_short} ({after_short - before_short:+g})")
        if before_short > 0:
            print(f"  Before: {', '.join(style_details['naming']['short_names_before'][:5])}")
            if before_short > 5:
                print(f"  ... and {before_short - 5} more")
        if after_short > 0:
            print(f"  After: {', '.join(style_details['naming']['short_names_after'][:5])}")
            if after_short > 5:
                print(f"  ... and {after_short - 5} more")
    
    # Confidence breakdown
    print("\n🔧 CONFIDENCE BREAKDOWN:")
    print("-" * 40)
    for component, value in confidence_components.items():
        component_name = component.replace('_', ' ').title()
        print(f"  {component_name}: {value:.3f}")
    
    # Decision
    print("\n" + "="*60)
    if confidence_score >= 0.85:
        print("✅✅ EXCELLENT REFACTORING (High Confidence)")
        print("   The refactoring is very likely correct and improved the code.")
    elif confidence_score >= 0.70:
        print("✅ GOOD REFACTORING (Moderate Confidence)")
        print("   The refactoring appears correct with clear improvements.")
    elif confidence_score >= 0.55:
        print("⚠ ACCEPTABLE REFACTORING (Low Confidence)")
        print("   Review recommended - some aspects may need verification.")
    elif confidence_score >= 0.40:
        print("⚠ MARGINAL REFACTORING (Very Low Confidence)")
        print("   Thorough review required - likely issues detected.")
    else:
        print("❌ POOR REFACTORING (Reject)")
        print("   Significant problems detected - not recommended.")
    print("="*60)
    
    # Additional recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 40)
    
    if ast_score < 1.0:
        print("• Fix syntax errors in refactored code")
    
    if change_score < 0.2:
        print("• Very little change detected - ensure refactoring was meaningful")
    elif change_score > 0.8:
        print("• Very similar to original - confirm improvements are substantial")
    
    if style_score < 0.6:
        print("• Limited style improvement - consider further refactoring")
    elif style_score > 0.8:
        print("• Good style improvements detected")
    
    if codebleu_score < 0.4:
        print("• Low semantic similarity - verify logic preservation")
    
    print("-" * 40)
    
    return confidence_score


if __name__ == "__main__":
    # Run evaluation
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)