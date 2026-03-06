import os
from pathlib import Path
import sys
import logging
import json
from typing import Optional
from datetime import datetime
from rag.document_builder import build_documents

from core.embeddings import get_embedding_model
from core.vector_store import build_vector_index
from core.symbol_index import build_symbol_index
from core.hybrid_retriever import hybrid_retrieve
from core.retriever import create_retriever


# ============================================================
# Logging Setup
# ============================================================

log_file = Path("prompt_engine.log")
if log_file.exists():
    log_file.unlink()

logger = logging.getLogger(__name__)
logger.disabled = True

import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))

# ============================================================
# Imports
# ============================================================

from parser.python_ast_parser import PythonASTParser
from prompt_engine import PromptingEngine, SmellDetector
from prompt_engine.dacos_integration import init_dacos

# NEW: RepoState abstraction
from graph.state import create_repo_state


# ============================================================
# Configuration
# ============================================================

CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULT_DACOS_PATHS = [
    "C:/Users/Administrator/Documents/GitHub/Major-Project/prompt_engine/dacos",
    "./prompt_engine/dacos",
    "./dacos"
]


# ============================================================
# Config Loader
# ============================================================

def load_config() -> dict:

    config = {
        "dacos_path": "",
        "model_type": "codet5p-770m",
        "output_prefix": "prompts_output"
    }

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception:
            pass

    return config


# ============================================================
# DACOS path detection
# ============================================================

def find_dacos_folder(config: dict) -> Optional[str]:

    if config.get("dacos_path") and config["dacos_path"] != "SKIP":
        path = Path(config["dacos_path"])
        if path.exists() and path.is_dir():
            return str(path)

    for path_str in DEFAULT_DACOS_PATHS:
        path = Path(path_str).expanduser().absolute()
        if path.exists() and path.is_dir():
            return str(path)

    return None


# ============================================================
# Input Reader
# ============================================================

def read_input_code() -> str:

    input_file = Path(__file__).parent / "input_code.py"


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


# ============================================================
# Output Saving
# ============================================================

def save_all_outputs(prompts: dict, report: str, plan: str,
                     parsed_code: dict, smells: list,
                     output_prefix: str = "prompts_output") -> str:

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_prefix) / f"run_{timestamp}"
    output_dir.mkdir(exist_ok=True, parents=True)

    # 1. Original code
    (output_dir / "1_original_code.py").write_text(
        parsed_code.get("original_code", ""),
        encoding='utf-8'
    )

    # 2. Parsed analysis
    with open(output_dir / "2_parsed_analysis.json", 'w', encoding='utf-8') as f:
        parsed_copy = parsed_code.copy()
        parsed_copy.pop("original_code", None)
        json.dump(parsed_copy, f, indent=2, default=str)

    # 3. Smell report
    (output_dir / "3_smell_report.txt").write_text(report, encoding='utf-8')
    

    # 4. Refactoring plan
    (output_dir / "4_refactoring_plan.txt").write_text(plan, encoding='utf-8')

    # 5. Refactor prompt
    if prompts.get("refactor_prompt"):
        (output_dir / "5_refactor_prompt.txt").write_text(
            prompts["refactor_prompt"],
            encoding='utf-8'
        )

    # 6. Documentation prompt
    if prompts.get("documentation_prompt"):
        (output_dir / "6_documentation_prompt.txt").write_text(
            prompts["documentation_prompt"],
            encoding='utf-8'
        )

    # 7. Metadata
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


# ============================================================
# Output Summary
# ============================================================

def print_summary(output_dir: str, smells: list):

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


# ============================================================
# MAIN ORCHESTRATION
# ============================================================

def main():

    print("\n🚀 Starting Code Refactoring Analysis...")

    config = load_config()

    dacos_path = find_dacos_folder(config)

    if dacos_path:
        print(f"✅ Using DACOS thresholds from: {dacos_path}")
    else:
        print("ℹ️ Using default thresholds (DACOS not found)")

    source_code = read_input_code()

    # Initialize components
    parser = PythonASTParser()

    engine = PromptingEngine(
        model_type=config.get("model_type", "codet5p-770m"),
        dacos_folder=dacos_path
    )

    detector = SmellDetector(dacos_folder=dacos_path)

    # =========================================================
    # PARSE CODE
    # =========================================================

    parsed_code = parser.parse(source_code)
    parsed_code["original_code"] = source_code
    print("DEBUG --- parser output")
    
    print("functions metrics:", len(parsed_code.get("functions", [])))
    print("classes metrics:", len(parsed_code.get("classes", [])))
    print("semantic function units:", len(parsed_code.get("function_units", [])))
    print("semantic class units:", len(parsed_code.get("class_units", [])))
    print("imports:", parsed_code.get("imports"))


    # =========================================================
    # NEW: BUILD RepoState (Semantic Abstraction)
    # =========================================================

    repo_state = create_repo_state(
        raw_code=source_code,
        classes=parsed_code.get("class_units", []),
        functions=parsed_code.get("function_units", []),
        imports=parsed_code.get("imports", []),
        metadata={
            "language": "python",
            "total_lines": parsed_code.get("total_lines", 0)
        }
    )
    symbol_index = build_symbol_index(repo_state)
    print("\nDEBUG --- RepoState")
    print("Functions:", [f.name for f in repo_state.functions])
    print("Classes:", [c.name for c in repo_state.classes])
    print("Hash:", repo_state.state_hash[:12])
    documents = build_documents(repo_state)
    embedding_model = get_embedding_model()
    vector_db = build_vector_index(documents, embedding_model)
    retriever = create_retriever(vector_db)
    results = hybrid_retrieve("refactor compute_statistics", retriever, symbol_index)

    print("\nDEBUG --- Hybrid Retrieval")

    for r in results:
        print(r["symbol"])
        
    

    

    vector_db = build_vector_index(documents, embedding_model)

    print("\nDEBUG --- RAG Documents")
    for d in documents:
        print(d["type"], d["symbol"])
    results = vector_db.similarity_search("function that adds numbers")

    print("\nDEBUG --- Retrieval")
    for r in results:
        print(r.metadata["symbol"], r.metadata["type"])
    



    # =========================================================
    # ANALYSIS PIPELINE
    # =========================================================

    smells = detector.detect_smells(repo_state)

    report = detector.generate_report(repo_state)

    plan = engine.generate_refactoring_plan(parsed_code)
    # ---------------------------------------------------------
# DEBUG: Show autonomous retrieval query
# ---------------------------------------------------------

    smells = detector.detect_smells(repo_state)

    query_tokens = []

    for f in repo_state.functions[:3]:
        query_tokens.append(f.name)

    for c in repo_state.classes[:2]:
        query_tokens.append(c.name)

    for s in smells[:2]:
        query_tokens.append(s["name"])

    query_tokens.append("refactor code")

    query = " ".join(query_tokens)


    print("====//////////////////===================================================================================\nDEBUG --- Hybrid Retrieval Query")
    print(query)

    prompts = engine.generate_prompts(
        repo_state=repo_state,
        user_request="both"
    )

    # =========================================================
    # SAVE RESULTS
    # =========================================================

    output_prefix = config.get("output_prefix", "prompts_output")

    output_dir = save_all_outputs(
        prompts,
        report,
        plan,
        parsed_code,
        smells,
        output_prefix
    )

    print_summary(output_dir, smells)


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)