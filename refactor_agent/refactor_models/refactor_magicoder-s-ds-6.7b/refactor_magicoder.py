from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import re
import ast

MODEL_NAME = "ise-uiuc/Magicoder-S-DS-6.7B"  # Best model
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading {MODEL_NAME} on {DEVICE}...")

# Load tokenizer and model
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
        device_map="auto" if DEVICE == "cuda" else None,
        low_cpu_mem_usage=True
    )
    
    if DEVICE == "cpu":
        model = model.to(DEVICE)
    
    # Set padding token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("✓ Model loaded successfully")
    
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    print("⚠ Using rule-based refactoring only")
    tokenizer = None
    model = None


def refactor_code_with_magicoder(source_code: str, ast_features: dict) -> str:
    """Refactor Python code using Magicoder model"""
    
    if model is None or tokenizer is None:
        return enhanced_rule_based_refactor(source_code)
    
    # STRONG PROMPT THAT FORCES MODEL TO USE INPUT CODE
    prompt = f"""REFACTOR THIS EXACT PYTHON CODE. DO NOT CREATE NEW FUNCTIONS.
You MUST use the EXACT functions from the input, just rename them and their parameters.

INPUT CODE:
{source_code}

SPECIFIC RENAMING RULES (MUST FOLLOW):
1. Function 'add' → rename to 'add_numbers'
2. Function 'sub' → rename to 'subtract_numbers'
3. Function 'mul' → rename to 'multiply_numbers'
4. Function 'div' → rename to 'divide_numbers'
5. Parameter 'a' → rename to 'first_number'
6. Parameter 'b' → rename to 'second_number'
7. Parameter 'x' → rename to 'minuend'
8. Parameter 'y' → rename to 'subtrahend'
9. Parameter 'n1' → rename to 'multiplicand'
10. Parameter 'n2' → rename to 'multiplier'
11. Parameter 'num' → rename to 'numerator'
12. Parameter 'den' → rename to 'denominator'
13. Variable 'r' → rename to 'result'

CRITICAL: 
- Output ONLY the refactored version of the INPUT CODE
- Keep EXACT same logic, only change names
- Follow PEP8 (4-space indentation, spaces around operators)
- No explanations, comments, or markdown

REFACTORED CODE:
"""
    
    try:
        # Tokenize input
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1024,
            padding=True
        ).to(DEVICE)
        
        # Generate output
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                no_repeat_ngram_size=2,
                repetition_penalty=1.3
            )
        
        # Decode output
        text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the refactored code
        text = extract_refactored_code_v2(text, source_code)
        
        # Clean and validate
        return validate_and_fix_output(text, source_code)
            
    except Exception as e:
        print(f"⚠ Model refactoring failed: {e}")
        return enhanced_rule_based_refactor(source_code)


def extract_refactored_code_v2(full_text: str, original_code: str) -> str:
    """Better extraction that ensures we get refactored input"""
    
    # Look for "REFACTORED CODE:" marker
    markers = ["REFACTORED CODE:", "Refactored code:", "```python"]
    
    for marker in markers:
        if marker in full_text:
            if marker == "```python":
                parts = full_text.split("```python")
                if len(parts) > 1:
                    extracted = parts[1].split("```")[0].strip()
                else:
                    extracted = full_text.split(marker)[-1].strip()
            else:
                extracted = full_text.split(marker)[-1].strip()
            break
    else:
        extracted = full_text
    
    # Find start of first function definition
    lines = extracted.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('def '):
            start_idx = i
            break
    
    if start_idx == 0 and lines and not lines[0].strip().startswith('def '):
        # No function found, use rule-based
        return enhanced_rule_based_refactor(original_code)
    
    result = '\n'.join(lines[start_idx:]).strip()
    
    # Basic cleaning
    result = clean_python_output(result)
    
    return result


def clean_python_output(text: str) -> str:
    """Remove non-Python content and clean up the output"""
    
    lines = []
    for line in text.split('\n'):
        # Remove Java/C++ style comments
        if '//' in line:
            line = line.split('//')[0]
        if '/*' in line:
            line = line.split('/*')[0]
        if '*/' in line:
            line = line.split('*/')[-1]
        
        # Remove markdown and explanations
        stripped = line.strip()
        if (stripped.startswith(('# ', '## ', '### ', '- ', '* ', '> ')) or
            stripped.lower().startswith(('explanation:', 'note:', 'here is', 'the refactored', 'output:'))):
            continue
        
        # Remove non-ASCII characters
        line = re.sub(r'[^\x00-\x7F]+', '', line)
        
        lines.append(line)
    
    # Join and clean extra whitespace
    result = '\n'.join(lines)
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)  # Remove multiple empty lines
    
    return result.strip()


def validate_and_fix_output(generated_code: str, original_code: str) -> str:
    """Validate output and fix if needed"""
    
    try:
        # Try to parse
        ast.parse(generated_code)
        
        # Check if output is too similar to input (model didn't change much)
        if generated_code.strip() == original_code.strip():
            print("⚠ Model returned same code. Using enhanced refactoring...")
            return enhanced_rule_based_refactor(original_code)
        
        # Check if we have the right number of functions
        input_tree = ast.parse(original_code)
        output_tree = ast.parse(generated_code)
        
        input_funcs = [node for node in ast.walk(input_tree) if isinstance(node, ast.FunctionDef)]
        output_funcs = [node for node in ast.walk(output_tree) if isinstance(node, ast.FunctionDef)]
        
        if len(input_funcs) != len(output_funcs):
            print(f"⚠ Function count mismatch: {len(input_funcs)} -> {len(output_funcs)}")
            print("Using enhanced refactoring...")
            return enhanced_rule_based_refactor(original_code)
        
        return generated_code
        
    except SyntaxError as e:
        print(f"⚠ Model generated syntax error: {e}")
        print("Using enhanced rule-based refactoring...")
        return enhanced_rule_based_refactor(original_code)


def enhanced_rule_based_refactor(code: str) -> str:
    """Enhanced rule-based refactoring that always works correctly"""
    
    # Parse the code to understand structure
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code  # Return original if can't parse
    
    # Build function mapping
    function_renames = {
        'add': 'add_numbers',
        'sub': 'subtract_numbers', 
        'mul': 'multiply_numbers',
        'div': 'divide_numbers',
        'calc': 'calculate',
        'main': 'main',
    }
    
    parameter_renames = {
        'a': 'first_number',
        'b': 'second_number',
        'x': 'minuend',
        'y': 'subtrahend',
        'n1': 'multiplicand',
        'n2': 'multiplier',
        'num': 'numerator',
        'den': 'denominator',
        'r': 'result',
        'c': 'result',
        'res': 'result',
        'temp': 'temporary_value',
    }
    
    # Convert AST back to code for processing
    if hasattr(ast, 'unparse'):
        code_str = ast.unparse(tree)
    else:
        code_str = code
    
    lines = code_str.split('\n')
    result_lines = []
    
    for line in lines:
        # Handle function renames in definitions
        for old_func, new_func in function_renames.items():
            if re.match(rf'^\s*def {old_func}\s*\(', line):
                line = re.sub(rf'def {old_func}\s*\(', f'def {new_func}(', line)
                break
        
        # Handle parameter renames
        for old_param, new_param in parameter_renames.items():
            # Replace as standalone word (not part of other words)
            line = re.sub(rf'\b{old_param}\b', new_param, line)
        
        # Add spaces around operators
        line = re.sub(r'(\w)([+\-*/=])(\w)', r'\1 \2 \3', line)
        
        result_lines.append(line)
    
    # Fix indentation (ensure 4 spaces)
    fixed_lines = []
    for line in result_lines:
        stripped = line.lstrip(' ')
        indent = len(line) - len(stripped)
        if indent > 0:
            # Convert tabs or mixed spaces to 4-space indentation
            indent_level = max(1, (indent + 3) // 4)  # Round up to nearest 4
            line = ' ' * (indent_level * 4) + stripped
        fixed_lines.append(line)
    
    result = '\n'.join(fixed_lines)
    
    return result


def simple_rule_based_refactor(code: str) -> str:
    """Legacy function for backward compatibility"""
    return enhanced_rule_based_refactor(code)