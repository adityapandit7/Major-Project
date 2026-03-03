import ast
import sys
import re
from refactor_magicoder import refactor_code_with_magicoder, enhanced_rule_based_refactor


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
    tree = ast.parse(code)

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


def validate_refactored_code(original: str, refactored: str) -> bool:
    """Validate that refactored code maintains structure"""
    try:
        orig_tree = ast.parse(original)
        ref_tree = ast.parse(refactored)
        
        # Count functions
        orig_funcs = [node for node in ast.walk(orig_tree) if isinstance(node, ast.FunctionDef)]
        ref_funcs = [node for node in ast.walk(ref_tree) if isinstance(node, ast.FunctionDef)]
        
        if len(orig_funcs) != len(ref_funcs):
            print(f"⚠ Function count changed: {len(orig_funcs)} -> {len(ref_funcs)}")
            return False
        
        return True
    except:
        return False


# ---------- PIPELINE ----------

def parse_and_refactor(input_file: str, output_file: str, max_retries: int = 1):
    print(f"🔧 Refactoring {input_file}...")
    
    with open(input_file, "r", encoding="utf-8") as f:
        source_code = f.read()

    ensure_python_only(source_code)

    clean_code = remove_header_comments(source_code)

    # Pre-validation
    ast.parse(clean_code)

    ast_features = extract_ast_features(clean_code)
    
    print(f"📊 Found {len(ast_features['functions'])} functions: {ast_features['functions']}")
    print(f"📊 Found {len(set(ast_features['variables']))} variables: {list(set(ast_features['variables']))}")

    refactored_code = None
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            print(f"🤖 Attempting AI refactoring (attempt {retry_count + 1})...")
            refactored_code = refactor_code_with_magicoder(
                source_code=clean_code,
                ast_features=ast_features
            )
            
            # Post-validation
            if is_valid_python(refactored_code) and validate_refactored_code(clean_code, refactored_code):
                print("✅ AI refactoring successful!")
                break
            else:
                print(f"⚠ AI generated invalid or structurally different Python (attempt {retry_count + 1})")
                retry_count += 1
                
        except Exception as e:
            print(f"⚠ Error during AI refactoring: {e}")
            retry_count += 1
    
    # If all retries failed or refactored_code is None, use rule-based fallback
    if refactored_code is None or not is_valid_python(refactored_code):
        print("🤖 Using enhanced rule-based refactoring...")
        refactored_code = enhanced_rule_based_refactor(clean_code)
    
    # Final validation
    if not is_valid_python(refactored_code):
        print("❌ Could not generate valid Python code. Using original code.")
        refactored_code = clean_code

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(refactored_code)

    print(f"✅ Refactored Python code written to {output_file}")
    
    # Show comparison
    print("\n" + "="*60)
    print("ORIGINAL CODE:")
    print("="*60)
    print(clean_code)
    
    print("\n" + "="*60)
    print("REFACTORED CODE:")
    print("="*60)
    print(refactored_code)
    print("="*60)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python main.py <input_file.py> <output_file.py>")
        print("Example: python main.py input_code.py refactored_code.py")
        sys.exit(1)
    
    parse_and_refactor(sys.argv[1], sys.argv[2])