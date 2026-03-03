from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import re
import warnings
import sys
import time

# Suppress warnings
warnings.filterwarnings("ignore")

MODEL_NAME = "Salesforce/codet5p-220m"

# Global variables for model
model = None
tokenizer = None
device = None

def initialize_model():
    """Initialize the model on first use."""
    global model, tokenizer, device
    
    if model is not None:
        return True
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Using device: {device}")
    
    try:
        # Load model with error handling
        print("⏳ Loading CodeT5 model (this may take a minute and download ~800MB on first run)...")
        start_time = time.time()
        
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        model = model.to(device)
        model.eval()  # Set to evaluation mode
        
        load_time = time.time() - start_time
        print(f"✅ Model loaded successfully in {load_time:.1f} seconds!")
        return True
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print("⚠ Will use fallback refactoring methods")
        return False


def refactor_code_with_codet5(source_code: str, ast_features: dict) -> str:
    # Initialize model if needed
    if not initialize_model():
        return source_code
    
    # Limit code length for model
    if len(source_code) > 800:
        print("📝 Code is long, truncating for model processing...")
        source_code = source_code[:800] + "\n# ... (truncated for model processing)"
    
    # Create a focused prompt
    prompt = f"""Improve this Python code with better naming and structure:
    
Original functions: {ast_features['functions']}

Code to refactor:
{source_code}

Refactored Python code:"""
    
    try:
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=512,
                num_beams=2,
                temperature=0.8,
                do_sample=True,
                early_stopping=True,
                no_repeat_ngram_size=3
            )

        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Clean the output
        cleaned_code = clean_model_output(generated_text)
        
        # If cleaned code is too short, return original with simple improvements
        if len(cleaned_code) < len(source_code) * 0.3:
            print("⚠ Model output too short, using improved fallback")
            return apply_semantic_refactoring(source_code, ast_features)
        
        return cleaned_code
        
    except Exception as e:
        print(f"⚠ Model error: {e}")
        return apply_semantic_refactoring(source_code, ast_features)


def apply_semantic_refactoring(code: str, ast_features: dict) -> str:
    """Apply semantic refactoring based on common patterns."""
    
    # Common naming improvements
    naming_map = {
        'sub': 'subtract',
        'mul': 'multiply', 
        'div': 'divide',
        'calc': 'calculate',
        'func': 'function',
        'proc': 'process',
        'util': 'utility',
        'var': 'variable',
        'val': 'value',
        'arr': 'array',
        'lst': 'list',
        'dict': 'dictionary',
        'cnt': 'count',
        'num': 'number',
        'str': 'string',
        'temp': 'temporary',
        'res': 'result',
        'r': 'result',
        'x': 'first',
        'y': 'second',
        'a': 'first',
        'b': 'second',
        'n1': 'first_number',
        'n2': 'second_number',
        'den': 'denominator',
        'num': 'numerator',
    }
    
    lines = code.split('\n')
    improved_lines = []
    
    for line in lines:
        original_line = line
        
        # Improve function definitions
        for short, long in naming_map.items():
            # Function names
            if f'def {short}(' in line:
                line = line.replace(f'def {short}(', f'def {long}(')
            # Variable names in parameter lists
            line = re.sub(rf'\b{short}\b', long, line)
        
        # Improve specific patterns
        if 'return None' in line and 'if' in line:
            # Add comment for clarity
            line = line.replace('return None', 'return None  # Division by zero')
        
        improved_lines.append(line)
    
    return '\n'.join(improved_lines)


def clean_model_output(text: str) -> str:
    """
    Clean model output to get only valid Python code.
    """
    if not text:
        return ""
    
    # Remove markdown code blocks
    if '```python' in text:
        parts = text.split('```python')
        if len(parts) > 1:
            text = parts[1]
    if '```' in text:
        text = text.split('```')[0]
    
    # Split into lines
    lines = text.split('\n')
    cleaned_lines = []
    in_code = False
    
    # Find the actual code
    for line in lines:
        stripped = line.strip()
        
        # Skip explanation lines
        if not in_code:
            lower_stripped = stripped.lower()
            if any(keyword in lower_stripped for keyword in 
                  ['here is', 'refactored', 'improved', 'better', 'explanation:', 'note:']):
                continue
            if stripped and not (stripped.startswith(('#', 'def ', 'class ', 'import ', 'from ', '@')) or
                                '=' in stripped or ':' in stripped or stripped.startswith('"')):
                continue
        
        # Mark that we're in code section
        if stripped.startswith(('def ', 'class ', 'import ', 'from ')):
            in_code = True
        
        if in_code:
            # Clean the line
            line = line.rstrip()
            
            # Remove trailing comments with non-Python content
            if '//' in line:
                line = line.split('//')[0].rstrip()
            
            # Remove markdown formatting
            line = line.replace('`', '')
            
            cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines).strip()
    
    # Remove any remaining non-Python lines at start
    final_lines = []
    for line in result.split('\n'):
        stripped = line.strip()
        if stripped and not stripped.startswith(('#', 'def ', 'class ', 'import ', 'from ', '@')):
            # Check if it looks like code
            if not any(char in stripped for char in ['=', ':', '(', ')', '[', ']', '{', '}']):
                continue
        final_lines.append(line)
    
    result = '\n'.join(final_lines)
    
    # Ensure it ends properly
    if result and not result.endswith('\n'):
        result += '\n'
    
    return result


# Simple direct refactoring function for testing
def quick_refactor(code: str) -> str:
    """Quick rule-based refactoring."""
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
    
    for pattern, replacement in improvements:
        code = re.sub(pattern, replacement, code, flags=re.IGNORECASE)
    
    return code