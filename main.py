import os
from pathlib import Path
import sys
import logging
import json
from typing import Optional
from datetime import datetime

# Remove any existing log file
log_file = Path("prompt_engine.log")
if log_file.exists():
    log_file.unlink()

# Set up logging - disabled (commented out)
# logging.basicConfig(
#     level=logging.INFO,
#     format='[%(asctime)s] [%(levelname)s] %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S',
#     filename='prompt_engine.log',
#     filemode='a'
# )
logger = logging.getLogger(__name__)
logger.disabled = True  # Disable logging completely

# Suppress console output from imported modules
import warnings
warnings.filterwarnings("ignore")

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import local modules
from parser.python_ast_parser import PythonASTParser
from prompt_engine import PromptingEngine, SmellDetector
from prompt_engine.dacos_integration import init_dacos

# Configuration
CONFIG_FILE = Path(__file__).parent / "config.json"
DEFAULT_DACOS_PATHS = [
    "C:/Users/Administrator/Documents/GitHub/Major-Project/prompt_engine/dacos",
    "./prompt_engine/dacos",
    "./dacos"
]


def load_config() -> dict:
    """Load configuration from file."""
    config = {
        "dacos_path": "",
        "model_type": "codet5p-770m",
        "output_prefix": "prompts_output"  # Changed default
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception:
            pass
    
    return config


def find_dacos_folder(config: dict) -> Optional[str]:
    """Find DACOS folder silently."""
    
    if config.get("dacos_path") and config["dacos_path"] != "SKIP":
        path = Path(config["dacos_path"])
        if path.exists() and path.is_dir():
            return str(path)
    
    for path_str in DEFAULT_DACOS_PATHS:
        path = Path(path_str).expanduser().absolute()
        if path.exists() and path.is_dir():
            return str(path)
    
    return None


def read_input_code() -> str:
    """Read code from input_code.py"""
    input_file = Path("input_code.py")
    
    if not input_file.exists():
        print("❌ Error: input_code.py not found!")
        print("Please create input_code.py with your Python code.")
        sys.exit(1)
    
    try:
        code = input_file.read_text(encoding='utf-8')
        print(f"✅ Read code from input_code.py ({len(code.splitlines())} lines)")
        return code
    except Exception as e:
        print(f"❌ Error reading input_code.py: {e}")
        sys.exit(1)


def save_all_outputs(prompts: dict, report: str, plan: str, 
                     parsed_code: dict, smells: list, output_prefix: str = "prompts_output") -> str:
    """Save all outputs to files with clear names."""
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_prefix) / f"run_{timestamp}"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # 1. Save original code
    (output_dir / "1_original_code.py").write_text(
        parsed_code.get("original_code", ""), 
        encoding='utf-8'
    )
    
    # 2. Save parsed code info (JSON)
    with open(output_dir / "2_parsed_analysis.json", 'w', encoding='utf-8') as f:
        # Remove original_code from parsed_code for cleaner JSON
        parsed_copy = parsed_code.copy()
        parsed_copy.pop("original_code", None)
        json.dump(parsed_copy, f, indent=2, default=str)
    
    # 3. Save smell detection report
    (output_dir / "3_smell_report.txt").write_text(report, encoding='utf-8')
    
    # 4. Save refactoring plan
    (output_dir / "4_refactoring_plan.txt").write_text(plan, encoding='utf-8')
    
    # 5. Save refactoring prompt
    if prompts.get("refactor_prompt"):
        (output_dir / "5_refactor_prompt.txt").write_text(
            prompts["refactor_prompt"], 
            encoding='utf-8'
        )
    
    # 6. Save documentation prompt
    if prompts.get("documentation_prompt"):
        (output_dir / "6_documentation_prompt.txt").write_text(
            prompts["documentation_prompt"], 
            encoding='utf-8'
        )
    
    # 7. Save metadata
    with open(output_dir / "7_metadata.json", 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "function_count": len(parsed_code.get("functions", [])),
            "class_count": len(parsed_code.get("classes", [])),
            "smells_detected": len(smells),
            "smell_summary": [
                {"name": s["name"], "severity": s["severity"]} 
                for s in smells
            ],
            "dacos_initialized": prompts["metadata"].get("dacos_initialized", False)
        }, f, indent=2)
    
    return str(output_dir)


def print_summary(output_dir: str, smells: list):
    """Print a clean summary to terminal."""
    print("\n" + "="*60)
    print("✅ REFACTORING ANALYSIS COMPLETE")
    print("="*60)
    print(f"\n📁 Output folder: {output_dir}")
    print(f"\n📊 Detected {len(smells)} code smell(s):")
    
    for smell in smells:
        severity_icon = "🔴" if smell['severity'] == "critical" else "🟡" if smell['severity'] == "high" else "🟢"
        print(f"  {severity_icon} {smell['name']} ({smell['severity']})")
    
    print(f"\n📄 Files created:")
    for f in sorted(Path(output_dir).glob("*")):
        size = f.stat().st_size
        print(f"  - {f.name} ({size} bytes)")
    
    print("\n" + "="*60)


def main():
    """Main entry point - Reads from input_code.py only."""
    
    print("\n🚀 Starting Code Refactoring Analysis...")
    
    # Load configuration
    config = load_config()
    
    # Find DACOS folder silently
    dacos_path = find_dacos_folder(config)
    if dacos_path:
        print(f"✅ Using DACOS thresholds from: {dacos_path}")
    else:
        print("ℹ️ Using default thresholds (DACOS not found)")
    
    # Read code from input_code.py
    source_code = read_input_code()
    
    # Initialize components
    parser = PythonASTParser()
    engine = PromptingEngine(
        model_type=config.get("model_type", "codet5p-770m"),
        dacos_folder=dacos_path
    )
    detector = SmellDetector(dacos_folder=dacos_path)
    
    # Parse code
    parsed_code = parser.parse(source_code)
    parsed_code["original_code"] = source_code
    
    # Detect smells
    smells = detector.detect_smells(parsed_code)
    
    # Generate report and plan
    report = detector.generate_report(parsed_code)
    plan = engine.generate_refactoring_plan(parsed_code)
    
    # Generate prompts
    prompts = engine.generate_prompts(
        raw_code=source_code,
        parsed_code=parsed_code,
        user_request="both"
    )
    
    # Save everything
    output_prefix = config.get("output_prefix", "prompts_output")
    output_dir = save_all_outputs(prompts, report, plan, parsed_code, smells, output_prefix)
    
    # Print clean summary
    print_summary(output_dir, smells)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)