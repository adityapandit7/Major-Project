import os
from pathlib import Path
import sys
import logging
import json
from typing import Optional
from datetime import datetime

from rag.document_builder import build_documents
from orchestrator.planner_agent import PlannerAgent

from core.embeddings import get_embedding_model
from core.vector_store import build_vector_index
from core.symbol_index import build_symbol_index
from core.hybrid_retriever import hybrid_retrieve
from core.retriever import create_retriever

from parser.python_ast_parser import PythonASTParser
from prompt_engine import PromptingEngine, SmellDetector
from graph.state import create_repo_state


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
        sys.exit(1)

    code = input_file.read_text(encoding='utf-8')

    print(f"✅ Read code ({len(code.splitlines())} lines)")

    return code


# ============================================================
# Output Saving
# ============================================================

def save_all_outputs(prompts, report, plan, parsed_code, smells, output_prefix):

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_prefix) / f"run_{timestamp}"
    output_dir.mkdir(exist_ok=True, parents=True)

    (output_dir / "1_original_code.py").write_text(
        parsed_code.get("original_code", ""),
        encoding="utf-8"
    )

    with open(output_dir / "2_parsed_analysis.json", "w",encoding="utf-8") as f:
        parsed_copy = parsed_code.copy()
        parsed_copy.pop("original_code", None)
        json.dump(parsed_copy, f, indent=2, default=str)

    (output_dir / "3_smell_report.txt").write_text(report,encoding="utf-8")
    (output_dir / "4_refactoring_plan.txt").write_text(plan,encoding="utf-8")

    if prompts.get("refactor_prompt"):
        (output_dir / "5_refactor_prompt.txt").write_text(prompts["refactor_prompt"],encoding="utf-8")

    if prompts.get("documentation_prompt"):
        (output_dir / "6_documentation_prompt.txt").write_text(prompts["documentation_prompt"],encoding="utf-8")

    return str(output_dir)


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n🚀 Starting Code Refactoring Analysis...")

    config = load_config()

    dacos_path = find_dacos_folder(config)

    source_code = read_input_code()

    parser = PythonASTParser()

    engine = PromptingEngine(
        model_type=config.get("model_type", "codet5p-770m"),
        dacos_folder=dacos_path
    )

    detector = SmellDetector(dacos_folder=dacos_path)

    # =========================================================
    # Parse Code
    # =========================================================

    parsed_code = parser.parse(source_code)
    parsed_code["original_code"] = source_code

    print("Functions:", len(parsed_code.get("functions", [])))
    print("Classes:", len(parsed_code.get("classes", [])))

    # =========================================================
    # RepoState
    # =========================================================

    repo_state = create_repo_state(
        raw_code=source_code,
        classes=parsed_code.get("class_units", []),
        functions=parsed_code.get("function_units", []),
        imports=parsed_code.get("imports", []),
        metadata={"language": "python"}
    )

    # =========================================================
    # Build Retrieval System
    # =========================================================

    symbol_index = build_symbol_index(repo_state)

    documents = build_documents(repo_state)

    embedding_model = get_embedding_model()

    vector_db = build_vector_index(documents, embedding_model)

    retriever = create_retriever(vector_db)

    # =========================================================
    # Initialize Planner (AFTER dependencies exist)
    # =========================================================

    planner = PlannerAgent(
    engine=engine,
    retriever=retriever,
    symbol_index=symbol_index
    )

    # =========================================================
    # Smell Detection
    # =========================================================

    smells = detector.detect_smells(repo_state)

    report = detector.generate_report(repo_state)

    # =========================================================
    # Planner
    # =========================================================

    repo_state = planner.run(repo_state, smells)

    print("\nDEBUG --- Planner Tasks")

    for t in repo_state.tasks:
        print(f"Task {t.id}: {t.type} → {t.target}")

    # =========================================================
    # Prompt Generation
    # =========================================================

    prompts = engine.generate_prompts(
        repo_state=repo_state,
        user_request="both"
    )

    plan = engine.generate_refactoring_plan(parsed_code)

    # =========================================================
    # Save Results
    # =========================================================

    output_dir = save_all_outputs(
        prompts,
        report,
        plan,
        parsed_code,
        smells,
        config.get("output_prefix", "prompts_output")
    )

    print(f"\nResults saved to: {output_dir}")


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    main()