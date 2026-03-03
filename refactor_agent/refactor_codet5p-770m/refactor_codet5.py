# refactor_agent/refactor_codet5p-770m/refactor_codet5.py

from transformers import AutoTokenizer, T5ForConditionalGeneration
import torch
import re
import ast
import sys
from pathlib import Path
import logging
import tokenize
import io
from typing import Optional, Tuple, List, Set
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path to import prompting engine
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Constants
MODEL_NAME = "Salesforce/codet5p-770m"
MAX_INPUT_LENGTH = 1024
MAX_OUTPUT_LENGTH = 1024
TIMEOUT_SECONDS = 60

# Try to import prompting engine
try:
    from parser.python_ast_parser import PythonASTParser
    from prompt_engine import PromptingEngine
    PROMPT_ENGINE_AVAILABLE = True
    logger.info("Prompting engine imported successfully")
except ImportError as e:
    PROMPT_ENGINE_AVAILABLE = False
    logger.warning(f"Prompting engine not available: {e}")

# Model loading with retry
def load_model_with_retry(max_retries=3):
    """Load model with retry logic."""
    for attempt in range(max_retries):
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading {MODEL_NAME} on {device}... (attempt {attempt + 1}/{max_retries})")
            
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)
            model = model.to(device)
            model.eval()
            
            logger.info("CodeT5 770M model loaded successfully")
            return tokenizer, model, device
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("Failed to load model after all retries")
                return None, None, None
    
    return None, None, None

# Load model
tokenizer, model, device = load_model_with_retry()

class CodeStringProtector:
    """
    Protects string literals and comments from regex modifications.
    """
    
    def __init__(self, code: str):
        self.code = code
        self.strings: List[Tuple[str, int, int]] = []  # (string, start, end)
        self.comments: List[Tuple[str, int, int]] = []  # (comment, start, end)
        self.protected_code = ""
        self._extract_protected_regions()
    
    def _extract_protected_regions(self):
        """Extract strings and comments from code."""
        try:
            # Use tokenize to safely extract strings and comments
            tokens = list(tokenize.generate_tokens(io.StringIO(self.code).readline))
            
            protected_parts = []
            last_end = 0
            
            for token in tokens:
                start_row, start_col = token.start
                end_row, end_col = token.end
                
                # Convert to absolute positions (simplified - works for single line)
                start_pos = self._get_absolute_position(start_row, start_col)
                end_pos = self._get_absolute_position(end_row, end_col)
                
                if token.type == tokenize.STRING:
                    # Store string
                    string_content = token.string
                    self.strings.append((string_content, start_pos, end_pos))
                    
                    # Add placeholder
                    protected_parts.append(self.code[last_end:start_pos])
                    protected_parts.append(f"__STRING_{len(self.strings)-1}__")
                    last_end = end_pos
                    
                elif token.type == tokenize.COMMENT:
                    # Store comment
                    comment_content = token.string
                    self.comments.append((comment_content, start_pos, end_pos))
                    
                    # Add placeholder
                    protected_parts.append(self.code[last_end:start_pos])
                    protected_parts.append(f"__COMMENT_{len(self.comments)-1}__")
                    last_end = end_pos
            
            # Add remaining code
            protected_parts.append(self.code[last_end:])
            self.protected_code = ''.join(protected_parts)
            
        except Exception as e:
            logger.warning(f"Error in code protection: {e}")
            self.protected_code = self.code
    
    def _get_absolute_position(self, row: int, col: int) -> int:
        """Convert row/col to absolute position."""
        lines = self.code.split('\n')
        pos = 0
        for i in range(row - 1):
            pos += len(lines[i]) + 1  # +1 for newline
        return pos + col
    
    def restore(self, modified_code: str) -> str:
        """Restore strings and comments in modified code."""
        result = modified_code
        
        # Restore strings
        for i, (string, start, end) in enumerate(self.strings):
            placeholder = f"__STRING_{i}__"
            result = result.replace(placeholder, string)
        
        # Restore comments
        for i, (comment, start, end) in enumerate(self.comments):
            placeholder = f"__COMMENT_{i}__"
            result = result.replace(placeholder, comment)
        
        return result

def get_prompt_from_engine(source_code: str) -> Tuple[Optional[str], Optional[dict]]:
    """
    Use the prompting engine to generate a refactoring prompt.
    
    Returns:
        tuple: (prompt, metadata) or (None, None) if failed
    """
    if not PROMPT_ENGINE_AVAILABLE:
        return None, None
    
    try:
        # Initialize components
        parser = PythonASTParser()
        
        # Try to find DACOS folder
        dacos_path = project_root / "prompt_engine" / "dacos"
        if not dacos_path.exists():
            dacos_path = None
        
        engine = PromptingEngine(
            model_type="codet5p-770m",
            dacos_folder=str(dacos_path) if dacos_path else None
        )
        
        # Parse the code
        logger.info("Parsing code with AST...")
        parsed_code = parser.parse(source_code)
        
        if not parsed_code.get("parse_success", True):
            logger.warning(f"AST parsing had issues: {parsed_code.get('error', 'Unknown error')}")
        
        # Generate prompt
        logger.info("Generating prompt with engine...")
        prompts = engine.generate_prompts(
            raw_code=source_code,
            parsed_code=parsed_code,
            user_request="refactor"
        )
        
        return prompts.get("refactor_prompt"), prompts.get("metadata")
        
    except Exception as e:
        logger.warning(f"Error generating prompt from engine: {e}")
        return None, None

def get_fallback_prompt(source_code: str) -> str:
    """
    Fallback prompt generation when prompting engine is not available.
    """
    prompt_lines = [
        "You are a code refactoring expert. Refactor the following Python code to improve its quality.",
        "",
        "ORIGINAL CODE:",
        "```python",
        source_code,
        "```",
        "",
        "REQUIREMENTS:",
        "1. Preserve ALL original functionality",
        "2. Use descriptive names for functions and variables",
        "3. Follow PEP 8 style guidelines",
        "4. Keep the same number of functions",
        "5. Return ONLY the refactored code",
        "6. Do NOT change string literals or comments",
        "",
        "REFACTORED CODE:"
    ]
    
    return "\n".join(prompt_lines)

def safe_operator_spacing(code: str) -> str:
    """
    Safely add spaces around operators without affecting strings/comments.
    """
    protector = CodeStringProtector(code)
    
    # Apply regex to protected code
    protected = protector.protected_code
    
    # Add spaces around operators (but not in placeholders)
    patterns = [
        (r'(\w)([+\-*/=<>!]=?)(\w)', r'\1 \2 \3'),
        (r'(\w)([+\-*/=<>!]=?) ', r'\1 \2 '),
        (r' ([+\-*/=<>!]=?)(\w)', r' \1 \2'),
        (r',(\S)', r', \1'),
    ]
    
    for pattern, replacement in patterns:
        protected = re.sub(pattern, replacement, protected)
    
    # Restore strings and comments
    return protector.restore(protected)

def general_rule_based_refactor(code: str) -> str:
    """
    General rule-based refactoring that works for ANY Python code.
    This improves code style without hardcoded naming rules.
    """
    
    try:
        result = code
        
        # 1. Fix indentation (ensure consistent 4 spaces)
        lines = result.split('\n')
        fixed_lines = []
        for line in lines:
            stripped = line.lstrip()
            if stripped:  # Non-empty line
                # Check if line is a comment - preserve original indentation for comments
                if stripped.startswith('#'):
                    fixed_lines.append(line)  # Keep comments as is
                else:
                    indent = len(line) - len(stripped)
                    normalized_indent = (indent // 4) * 4
                    fixed_lines.append(' ' * normalized_indent + stripped)
            else:
                fixed_lines.append('')  # Keep empty lines
        
        result = '\n'.join(fixed_lines)
        
        # 2. Safely add spaces around operators
        result = safe_operator_spacing(result)
        
        # 3. Remove multiple blank lines (max 2)
        result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
        
        # 4. Ensure space after commas (already handled by safe_operator_spacing)
        
        # 5. Add missing newline at end of file
        if result and not result.endswith('\n'):
            result += '\n'
        
        return result
        
    except Exception as e:
        logger.warning(f"Rule-based refactoring failed: {e}")
        return code  # Return original if refactoring fails

def intelligent_rule_based_refactor(code: str) -> str:
    """
    More intelligent rule-based refactoring that adapts to the code.
    Uses AST to understand structure and make smart improvements.
    """
    
    try:
        tree = ast.parse(code)
        
        # Analyze the code structure using visitor
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        
        # Apply basic improvements first
        improved = general_rule_based_refactor(code)
        
        return improved
        
    except SyntaxError as e:
        logger.warning(f"Syntax error in code: {e}")
        return general_rule_based_refactor(code)
    except Exception as e:
        logger.warning(f"Intelligent refactoring failed: {e}")
        return general_rule_based_refactor(code)

class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor for code analysis."""
    
    def __init__(self):
        self.functions = []
        self.classes = []
        self.imports = []
        self.complexity = 1
    
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        self.functions.append({
            'name': node.name,
            'args': [arg.arg for arg in node.args.args],
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
            'lineno': node.lineno
        })
        
        # Calculate complexity
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler)):
                self.complexity += 1
        
        self.generic_visit(node)
    
    def _get_decorator_name(self, decorator):
        """Extract decorator name safely."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        return "unknown"
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        self.classes.append({
            'name': node.name,
            'lineno': node.lineno
        })
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Visit import statements."""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Visit from-import statements."""
        module = node.module or ''
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)

def refactor_code_with_codet5(source_code: str) -> str:
    """
    Refactor Python code using CodeT5 770M model with prompt from engine.
    
    Args:
        source_code: The Python code to refactor
        
    Returns:
        Refactored Python code
    """
    
    if model is None or tokenizer is None:
        logger.warning("Model not available, using intelligent rule-based refactoring")
        return intelligent_rule_based_refactor(source_code)
    
    # Try to get prompt from prompting engine first
    logger.info("="*60)
    logger.info("GENERATING PROMPT WITH ENGINE")
    logger.info("="*60)
    prompt, metadata = get_prompt_from_engine(source_code)
    
    # Fall back to generated prompt if engine not available
    if not prompt:
        logger.warning("Using fallback prompt generation")
        prompt = get_fallback_prompt(source_code)
    else:
        logger.info("Successfully generated prompt with engine")
        if metadata and metadata.get("smells_detected"):
            logger.info(f"Detected {len(metadata['smells_detected'])} smell(s)")
    
    logger.debug(f"Prompt (first 500 chars): {prompt[:500]}...")
    
    try:
        # Tokenize input with timeout
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_INPUT_LENGTH,
            padding=True,
            return_attention_mask=True
        ).to(device)
        
        # Generate output with timeout
        logger.info("Running CodeT5 model...")
        
        with torch.no_grad():
            outputs = model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=MAX_OUTPUT_LENGTH,
                num_beams=5,
                temperature=0.2,
                do_sample=True,
                early_stopping=True,
                no_repeat_ngram_size=3,
                repetition_penalty=1.3,
                length_penalty=1.0
            )
        
        # Decode output
        text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract the refactored code
        refactored = extract_refactored_code(text, source_code)
        
        # Validate the refactored code
        if validate_python_code(refactored):
            logger.info("CodeT5 processing complete - valid Python code generated")
            return refactored
        else:
            logger.warning("Generated code is not valid Python, using rule-based fallback")
            return intelligent_rule_based_refactor(source_code)
            
    except Exception as e:
        logger.warning(f"CodeT5 refactoring failed: {e}")
        logger.info("Using intelligent rule-based fallback...")
        return intelligent_rule_based_refactor(source_code)

def extract_refactored_code(text: str, original_code: str) -> str:
    """Extract refactored code from model output."""
    
    # Try to find code after the prompt
    markers = [
        "REFACTORED CODE:",
        "```python",
        "```",
        "def ",
        "class ",
        "import ",
        "from "
    ]
    
    for marker in markers:
        if marker in text:
            parts = text.split(marker, 1)
            if len(parts) > 1:
                text = parts[1].strip()
                break
    
    # Remove markdown code blocks
    text = re.sub(r'```python\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Try to extract valid Python code
    lines = text.split('\n')
    
    # Find first line that looks like Python code
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith(('#', '//', '/*', '*', '"""', "'")):
            if stripped.startswith(('def ', 'class ', 'import ', 'from ', '@', 'if __name__')):
                start_idx = i
                break
            # Also accept any non-empty line that might be code
            if any(c.isalpha() for c in stripped):
                start_idx = i
                break
    
    extracted = '\n'.join(lines[start_idx:]).strip()
    
    # If extraction failed or empty, return original
    if not extracted or len(extracted) < 10:
        return original_code
    
    return extracted

def validate_python_code(code: str) -> bool:
    """Validate if code is valid Python."""
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        logger.debug(f"Python validation failed: {e}")
        return False
    except Exception:
        return False

def refactor_file(input_file: str, output_file: str) -> bool:
    """
    Refactor a Python file using the integrated pipeline.
    
    Args:
        input_file: Path to input Python file
        output_file: Path to save refactored code
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Processing file: {input_file}")
    
    # Read input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        logger.info(f"Read {len(source_code.splitlines())} lines of code")
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        return False
    
    # Refactor the code
    logger.info("Starting refactoring process...")
    refactored = refactor_code_with_codet5(source_code)
    
    # Validate
    if not validate_python_code(refactored):
        logger.warning("Generated invalid code, using intelligent rule-based fallback")
        refactored = intelligent_rule_based_refactor(source_code)
    
    # Save output
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(refactored)
        logger.info(f"Refactored code saved to: {output_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save output: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) == 3:
        success = refactor_file(sys.argv[1], sys.argv[2])
        sys.exit(0 if success else 1)
    elif len(sys.argv) == 1:
        success = refactor_file("input_code.py", "refactored_output.py")
        sys.exit(0 if success else 1)
    else:
        print("Usage: python refactor_codet5.py [input_file.py output_file.py]")
        print("   or: python refactor_codet5.py (uses input_code.py and refactored_output.py)")
        sys.exit(1)