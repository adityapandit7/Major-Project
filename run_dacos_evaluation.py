"""
Script to run DACOS evaluation on the prompting engine.
"""

import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from prompt_engine.dacos_evaluator import DACOSEvaluator
from prompt_engine.smell_detector import SmellDetector
from parser.python_ast_parser import PythonASTParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run DACOS evaluation."""
    
    print("="*60)
    print("🧪 DACOS EVALUATION")
    print("="*60)
    
    # Initialize components
    parser = PythonASTParser()
    
    # Try to find DACOS dataset
    dacos_paths = [
        r"C:\Users\Administrator\Documents\GitHub\Major-Project\prompt_engine\dacos",
        "./prompt_engine/dacos",
        "./dacos"
    ]
    
    dacos_path = None
    for path in dacos_paths:
        if Path(path).exists():
            dacos_path = path
            break
    
    # Initialize evaluator
    evaluator = DACOSEvaluator(dacos_path)
    
    # Initialize smell detector (without DACOS for baseline)
    detector = SmellDetector(dacos_folder=None)
    
    # Define parsing function
    def parse_code(code):
        return parser.parse(code)
    
    # Run evaluation
    print("\n📊 Running smell detection evaluation...")
    results = evaluator.evaluate_smell_detection(detector, parse_code)
    
    # Print summary
    print("\n" + evaluator._format_summary(results))
    
    # Save results
    evaluator.save_evaluation_report(results)
    
    # If DACOS is available, also run with DACOS thresholds
    if dacos_path:
        print("\n📊 Running evaluation with DACOS thresholds...")
        detector_dacos = SmellDetector(dacos_folder=dacos_path)
        results_dacos = evaluator.evaluate_smell_detection(detector_dacos, parse_code)
        
        print("\n" + evaluator._format_summary(results_dacos))
        evaluator.save_evaluation_report(results_dacos, "dacos_evaluation_with_dacos.json")
        
        # Compare
        print("\n📈 Comparison:")
        print(f"  Without DACOS: {results.get('accuracy', 0)*100:.2f}%")
        print(f"  With DACOS:    {results_dacos.get('accuracy', 0)*100:.2f}%")
    
    print("\n✅ Evaluation complete!")

if __name__ == "__main__":
    main()