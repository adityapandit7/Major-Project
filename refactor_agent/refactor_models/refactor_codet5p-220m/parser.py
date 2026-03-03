import ast
from refactor import refactor_code_with_codet5


# ---------- VALIDATION ----------

def ensure_python_only(code: str):
    forbidden = [
        "package ", "import org.", "public class",
        "interface ", "extends ", "implements ", ";"
    ]

    for word in forbidden:
        if word in code:
            raise ValueError(
                "❌ Non-Python code detected. Only Python code is allowed."
            )


def remove_header_comments(code: str) -> str:
    lines = code.splitlines()
    cleaned = []
    skipping = True

    for line in lines:
        if skipping and (line.strip().startswith("#") or line.strip() == ""):
            continue
        skipping = False
        cleaned.append(line)

    return "\n".join(cleaned)


# ---------- AST FEATURES ----------

def extract_ast_features(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"functions": [], "variables": []}

    features = {
        "functions": [],
        "variables": []
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            features["functions"].append(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            features["variables"].append(node.id)

    return features


def is_valid_python(code: str) -> bool:
    """Check if code is valid Python syntax."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def simple_refactor_fallback(code: str) -> str:
    """Simple refactoring fallback when model fails."""
    # Basic improvements
    improvements = [
        (r'\bsub\b', 'subtract'),
        (r'\bmul\b', 'multiply'),
        (r'\bdiv\b', 'divide'),
        (r'\bcalc\b', 'calculate'),
        (r'\bcnt\b', 'count'),
        (r'\bnum\b', 'number'),
        (r'\bstr\b', 'string'),
        (r'\barr\b', 'array'),
        (r'\blst\b', 'list'),
        (r'\bdict\b', 'dictionary'),
        (r'\btemp\b', 'temporary'),
        (r'\bvar\b', 'variable'),
        (r'\bval\b', 'value'),
        (r'\bres\b', 'result'),
        (r'\br\b', 'result'),
        (r'if den == 0', 'if denominator == 0'),
        (r'\bden\b', 'denominator'),
        (r'\bnum\b', 'numerator'),
    ]
    
    import re
    for pattern, replacement in improvements:
        code = re.sub(pattern, replacement, code, flags=re.IGNORECASE)
    
    return code


# ---------- PIPELINE ----------

def parse_and_refactor(input_file: str, output_file: str, max_retries: int = 2):
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"❌ Input file '{input_file}' not found.")
        return

    # Check if file is empty
    if not source_code.strip():
        print("❌ Input file is empty.")
        return

    ensure_python_only(source_code)

    clean_code = remove_header_comments(source_code)

    # Pre-validation
    try:
        ast.parse(clean_code)
    except SyntaxError as e:
        print(f"❌ Invalid Python syntax in input: {e}")
        print("Using simple fallback refactoring...")
        refactored_code = simple_refactor_fallback(clean_code)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(refactored_code)
        print("✅ Simple refactored code written to", output_file)
        return

    ast_features = extract_ast_features(clean_code)

    refactored_code = None
    retry_count = 0
    
    print(f"📊 Found {len(ast_features['functions'])} functions: {ast_features['functions']}")
    
    while retry_count <= max_retries:
        try:
            refactored_code = refactor_code_with_codet5(
                source_code=clean_code,
                ast_features=ast_features
            )
            
            # Post-validation
            if refactored_code and is_valid_python(refactored_code):
                print(f"✅ Refactoring successful on attempt {retry_count + 1}")
                break
            else:
                print(f"⚠ Invalid Python detected (attempt {retry_count + 1}/{max_retries + 1})")
                retry_count += 1
                
        except Exception as e:
            print(f"⚠ Error during refactoring: {e}")
            retry_count += 1
    
    # If all retries failed or refactored_code is None, use fallback
    if refactored_code is None or not is_valid_python(refactored_code):
        print("⚠ Using simple refactor fallback")
        refactored_code = simple_refactor_fallback(clean_code)
    
    # Final validation
    if not is_valid_python(refactored_code):
        print("❌ Could not generate valid Python code. Using original code.")
        refactored_code = clean_code

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(refactored_code)

    print("✅ Refactored Python code written to", output_file)
    print("\n--- Result preview ---")
    print(refactored_code[:300] + "..." if len(refactored_code) > 300 else refactored_code)
    print("-" * 40)


if __name__ == "__main__":
    # You can change these filenames if needed
    parse_and_refactor("input_code.py", "refactored_code.py")