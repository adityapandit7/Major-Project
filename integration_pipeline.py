import os
import sys
import json
from pathlib import Path
import subprocess
import shutil
from datetime import datetime
import signal
import time
import logging
from typing import Optional, Dict, List, Any
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Import local modules
from parser.python_ast_parser import PythonASTParser
from prompt_engine import PromptingEngine, SmellDetector

class TimeoutError(Exception):
    """Custom timeout exception."""
    pass

class RefactoringPipeline:
    """
    End-to-end refactoring pipeline integrating all components.
    """
    
    def __init__(self, dacos_path: Optional[str] = None):
        """
        Initialize the pipeline with all components.
        
        Args:
            dacos_path: Path to DACOS dataset (optional)
        """
        self.project_root = project_root
        self.dacos_path = dacos_path or self._find_dacos_folder()
        self.timeout_seconds = 300  # 5 minutes default
        
        # Initialize components
        logger.info("="*60)
        logger.info("🚀 INITIALIZING REFACTORING PIPELINE")
        logger.info("="*60)
        
        try:
            self.parser = PythonASTParser()
            self.engine = PromptingEngine(
                model_type="codet5p-770m",
                dacos_folder=self.dacos_path
            )
            self.detector = SmellDetector(dacos_folder=self.dacos_path)
            logger.info("✅ Components initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            raise
        
        # Set up paths
        self.refactor_agent_path = self.project_root / "refactor_agent" / "refactor_codet5p-770m"
        self.output_dir = self.project_root / "output"
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        logger.info(f"📁 Project root: {self.project_root}")
        logger.info(f"📁 Output directory: {self.output_dir}")
        if self.refactor_agent_path.exists():
            logger.info(f"🤖 Refactor agent found: {self.refactor_agent_path}")
        else:
            logger.info("ℹ️ Refactor agent not found - will run in prompts-only mode")
    
    def _find_dacos_folder(self) -> Optional[str]:
        """Find DACOS folder if it exists."""
        possible_paths = [
            self.project_root / "prompt_engine" / "dacos",
            self.project_root / "dacos",
            Path("./prompt_engine/dacos"),
            Path("./dacos")
        ]
        
        # Add Windows-specific path if on Windows
        if os.name == 'nt':
            possible_paths.append(Path("C:/Users/Administrator/Documents/GitHub/Major-Project/prompt_engine/dacos"))
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                logger.info(f"✅ Found DACOS folder: {path}")
                return str(path)
        
        logger.warning("⚠️ DACOS folder not found - using default thresholds")
        return None
    
    def _safe_copy_file(self, src: Path, dst: Path, max_retries: int = 3) -> bool:
        """Safely copy a file with retries."""
        for attempt in range(max_retries):
            try:
                if dst.exists():
                    # Create backup if destination exists
                    backup = dst.with_suffix(dst.suffix + '.bak')
                    shutil.copy2(dst, backup)
                
                shutil.copy2(src, dst)
                return True
            except PermissionError:
                logger.warning(f"Permission error copying to {dst} (attempt {attempt + 1})")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Error copying file: {e} (attempt {attempt + 1})")
                time.sleep(1)
        
        # Fallback: try to write directly
        try:
            content = src.read_text(encoding='utf-8')
            dst.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"Failed to copy/write file: {e}")
            return False
    
    def _run_subprocess_with_timeout(self, cmd: List[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
        """Run subprocess with timeout and proper cleanup."""
        process = None
        try:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=process.returncode,
                    stdout=stdout,
                    stderr=stderr
                )
            except subprocess.TimeoutExpired:
                logger.error(f"Process timed out after {timeout} seconds")
                process.kill()
                process.wait(timeout=10)
                stdout, stderr = process.communicate()
                raise TimeoutError(f"Process timed out after {timeout} seconds")
                
        except Exception as e:
            if process:
                try:
                    process.kill()
                    process.wait(timeout=5)
                except:
                    pass
            raise e
    
    def process_code(self, code: str, code_name: str = "input_code") -> Dict[str, Any]:
        """
        Process a code string through the complete pipeline.
        
        Args:
            code: Python code to refactor
            code_name: Name for this code (used for file naming)
            
        Returns:
            Dictionary with all results
        """
        logger.info("="*60)
        logger.info(f"📝 PROCESSING: {code_name}")
        logger.info("="*60)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = {
            "timestamp": timestamp,
            "code_name": code_name,
            "original_code": code,
            "steps": {},
            "success": False
        }
        
        # Create run directory
        run_dir = self.output_dir / f"{code_name}_{timestamp}"
        run_dir.mkdir(exist_ok=True, parents=True)
        result["run_dir"] = str(run_dir)
        
        try:
            # Step 1: Parse code with AST
            logger.info("🔍 Step 1: Parsing code with AST...")
            parsed_code = self.parser.parse(code)
            result["steps"]["parsing"] = {
                "functions": len(parsed_code.get("functions", [])),
                "classes": len(parsed_code.get("classes", [])),
                "success": parsed_code.get("parse_success", False)
            }
            logger.info(f"   Found {len(parsed_code.get('functions', []))} functions")
            
            if not parsed_code.get("parse_success", True):
                logger.warning(f"   ⚠️ AST parsing issues: {parsed_code.get('error', 'Unknown')}")
            
            # Step 2: Detect smells
            logger.info("🔎 Step 2: Detecting code smells...")
            smells = self.detector.detect_smells(parsed_code)
            result["steps"]["smell_detection"] = {
                "smells_detected": len(smells),
                "details": [
                    {
                        "name": s["name"],
                        "severity": s["severity"],
                        "location": s["location"]
                    } for s in smells
                ]
            }
            
            if smells:
                logger.info(f"   Found {len(smells)} smell(s):")
                for s in smells:
                    severity_icon = "🔴" if s['severity'] == "critical" else "🟡" if s['severity'] == "high" else "🟢"
                    logger.info(f"   {severity_icon} {s['name']} ({s['severity']})")
            else:
                logger.info("   ✅ No smells detected")
            
            # Step 3: Generate prompts
            logger.info("🤖 Step 3: Generating prompts...")
            prompts = self.engine.generate_prompts(
                raw_code=code,
                parsed_code=parsed_code,
                user_request="both"
            )
            result["steps"]["prompt_generation"] = {
                "refactor_prompt_length": len(prompts["refactor_prompt"]) if prompts["refactor_prompt"] else 0,
                "doc_prompt_length": len(prompts["documentation_prompt"]) if prompts["documentation_prompt"] else 0,
                "dacos_initialized": prompts["metadata"].get("dacos_initialized", False)
            }
            logger.info("   ✅ Prompts generated")
            
            # Step 4: Save files
            logger.info("💾 Step 4: Saving files...")
            
            # Save original code
            input_file = run_dir / "input_code.py"
            input_file.write_text(code, encoding='utf-8')
            
            # Save prompts
            if prompts["refactor_prompt"]:
                prompt_file = run_dir / "refactor_prompt.txt"
                prompt_file.write_text(prompts["refactor_prompt"], encoding='utf-8')
            
            if prompts["documentation_prompt"]:
                doc_file = run_dir / "documentation_prompt.txt"
                doc_file.write_text(prompts["documentation_prompt"], encoding='utf-8')
            
            # Save metadata
            metadata_file = run_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "code_name": code_name,
                    "timestamp": timestamp,
                    "smells": result["steps"]["smell_detection"]["details"],
                    "function_count": result["steps"]["parsing"]["functions"],
                    "dacos_initialized": prompts["metadata"].get("dacos_initialized", False)
                }, f, indent=2)
            
            # Save smell report
            smell_report = self.detector.generate_report(parsed_code)
            report_file = run_dir / "smell_report.txt"
            report_file.write_text(smell_report, encoding='utf-8')
            
            # Save refactoring plan
            plan = self.engine.generate_refactoring_plan(parsed_code)
            plan_file = run_dir / "refactoring_plan.txt"
            plan_file.write_text(plan, encoding='utf-8')
            
            logger.info(f"   ✅ Files saved to: {run_dir}")
            
            # Step 5: Run refactor agent (if available)
            if self.refactor_agent_path.exists() and (self.refactor_agent_path / "refactor_codet5.py").exists():
                logger.info("🚀 Step 5: Running refactor agent...")
                refactor_result = self._run_refactor_agent(input_file, run_dir)
                result["steps"]["refactoring"] = refactor_result
                
                if refactor_result.get("success"):
                    result["success"] = True
                    
                    # Step 6: Run evaluation
                    if refactor_result.get("output_file"):
                        eval_result = self._run_evaluation(
                            input_file, 
                            Path(refactor_result["output_file"]), 
                            run_dir
                        )
                        result["steps"]["evaluation"] = eval_result
            else:
                logger.info("   ⏭️ Step 5: Refactor agent not found - prompts only")
                result["steps"]["refactoring"] = {
                    "success": False,
                    "mode": "prompts_only",
                    "message": "Refactor agent not available"
                }
                result["success"] = True  # Still successful for prompt generation
        
        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}")
            logger.debug(traceback.format_exc())
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
        
        # Save complete result (without large fields)
        result_file = run_dir / "pipeline_result.json"
        result_to_save = result.copy()
        result_to_save.pop("original_code", None)
        if "refactored_code" in result_to_save.get("steps", {}).get("refactoring", {}):
            result_to_save["steps"]["refactoring"].pop("refactored_code", None)
        
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result_to_save, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save result JSON: {e}")
        
        logger.info("="*60)
        if result["success"]:
            logger.info(f"✅ PIPELINE COMPLETED: {code_name}")
        else:
            logger.info(f"❌ PIPELINE FAILED: {code_name}")
        logger.info("="*60)
        
        return result
    
    def _run_refactor_agent(self, input_file: Path, run_dir: Path) -> Dict[str, Any]:
        """Run the refactor agent script."""
        try:
            original_dir = os.getcwd()
            agent_dir = self.refactor_agent_path
            output_file = run_dir / "codet5_refactored.py"
            agent_output = agent_dir / "codet5_refactored.py"
            
            # Copy input file to agent directory
            self._safe_copy_file(input_file, agent_dir / "input_code.py")
            
            # Run refactor script
            cmd = [sys.executable, "refactor_codet5.py", "input_code.py", str(agent_output)]
            
            os.chdir(agent_dir)
            process = self._run_subprocess_with_timeout(cmd, agent_dir, self.timeout_seconds)
            os.chdir(original_dir)
            
            if process.returncode == 0 and agent_output.exists():
                refactored_code = agent_output.read_text(encoding='utf-8')
                output_file.write_text(refactored_code, encoding='utf-8')
                
                # Also save to main output directory
                final_output = self.output_dir / f"{run_dir.name}_refactored.py"
                final_output.write_text(refactored_code, encoding='utf-8')
                
                logger.info(f"   ✅ Refactoring successful")
                return {
                    "success": True,
                    "refactored_code": refactored_code,
                    "output_file": str(output_file),
                    "final_output": str(final_output),
                    "stdout": process.stdout,
                    "stderr": process.stderr
                }
            else:
                return {
                    "success": False,
                    "error": "Refactoring failed",
                    "stdout": process.stdout,
                    "stderr": process.stderr
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _run_evaluation(self, original_file: Path, refactored_file: Path, run_dir: Path) -> Dict[str, Any]:
        """Run evaluation on refactored code."""
        eval_script = self.refactor_agent_path / "evaluate_refactor.py"
        if not eval_script.exists():
            return {"success": False, "error": "Evaluation script not found"}
        
        try:
            original_dir = os.getcwd()
            os.chdir(self.refactor_agent_path)
            
            # Copy files for evaluation
            self._safe_copy_file(original_file, self.refactor_agent_path / "input_code.py")
            self._safe_copy_file(refactored_file, self.refactor_agent_path / "codet5_refactored.py")
            
            # Run evaluation
            eval_output = run_dir / "evaluation_report.txt"
            cmd = [sys.executable, "evaluate_refactor.py", str(eval_output)]
            
            process = self._run_subprocess_with_timeout(cmd, self.refactor_agent_path, 60)
            os.chdir(original_dir)
            
            if process.returncode == 0:
                # Parse confidence score
                confidence = None
                for line in process.stdout.split('\n'):
                    if "OVERALL CONFIDENCE SCORE:" in line:
                        try:
                            confidence = float(line.split(':')[-1].strip().split('/')[0])
                        except:
                            pass
                
                return {
                    "success": True,
                    "confidence": confidence,
                    "report_file": str(eval_output) if eval_output.exists() else None,
                    "output": process.stdout
                }
            else:
                return {
                    "success": False,
                    "error": process.stderr
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a Python file through the pipeline."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            code = file_path.read_text(encoding='utf-8')
            code_name = file_path.stem
            return self.process_code(code, code_name)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file": str(file_path)
            }
    
    def batch_process(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple files through the pipeline."""
        results = []
        total = len(file_paths)
        
        for i, file_path in enumerate(file_paths, 1):
            logger.info(f"📁 Processing {i}/{total}: {file_path}")
            try:
                result = self.process_file(file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                results.append({"error": str(e), "file": str(file_path), "success": False})
        
        return results
    
    def generate_summary_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate a summary report from multiple pipeline runs."""
        
        report = []
        report.append("="*60)
        report.append("📊 REFACTORING PIPELINE SUMMARY REPORT")
        report.append("="*60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total runs: {len(results)}")
        report.append("")
        
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful
        
        report.append(f"✅ Successful: {successful}")
        report.append(f"❌ Failed: {failed}")
        report.append("")
        
        # Count smells by type
        smell_counts = {}
        for result in results:
            if "steps" in result and "smell_detection" in result["steps"]:
                for smell in result["steps"]["smell_detection"].get("details", []):
                    name = smell["name"]
                    smell_counts[name] = smell_counts.get(name, 0) + 1
        
        if smell_counts:
            report.append("📈 Most Common Smells:")
            for smell, count in sorted(smell_counts.items(), key=lambda x: x[1], reverse=True):
                report.append(f"   • {smell}: {count}")
            report.append("")
        
        report.append("-"*40)
        
        for i, result in enumerate(results, 1):
            if "error" in result:
                report.append(f"{i}. ❌ {result.get('file', 'Unknown')}: {result['error']}")
            else:
                steps = result.get("steps", {})
                report.append(f"{i}. ✅ {result.get('code_name', 'Unknown')}")
                
                # Smells detected
                smells = steps.get("smell_detection", {}).get("details", [])
                if smells:
                    report.append(f"   - Smells: {len(smells)}")
                    for s in smells[:2]:
                        report.append(f"     • {s['name']} ({s['severity']})")
                else:
                    report.append(f"   - Smells: None")
                
                # Refactoring result
                refactor = steps.get("refactoring", {})
                if refactor.get("success"):
                    report.append(f"   - Refactoring: ✅ Success")
                elif refactor.get("mode") == "prompts_only":
                    report.append(f"   - Refactoring: ⏭️ Prompts only")
                else:
                    report.append(f"   - Refactoring: ❌ Failed")
        
        report.append("")
        report.append("="*60)
        report.append(f"Summary: {successful}/{len(results)} successful ({successful/len(results)*100:.1f}%)")
        report.append("="*60)
        
        return "\n".join(report)
    
    def cleanup_old_runs(self, days: int = 7):
        """Clean up run directories older than specified days."""
        cutoff = time.time() - (days * 24 * 3600)
        removed = 0
        
        for run_dir in self.output_dir.iterdir():
            if run_dir.is_dir():
                try:
                    mtime = run_dir.stat().st_mtime
                    if mtime < cutoff:
                        logger.info(f"Removing old run: {run_dir}")
                        shutil.rmtree(run_dir)
                        removed += 1
                except Exception as e:
                    logger.warning(f"Failed to remove {run_dir}: {e}")
        
        logger.info(f"✅ Cleaned up {removed} old runs")


def main():
    """Main entry point for the pipeline."""
    
    import argparse
    parser = argparse.ArgumentParser(description="Complete Refactoring Pipeline")
    parser.add_argument("--file", "-f", type=str, help="Python file to refactor")
    parser.add_argument("--code", "-c", type=str, help="Python code string to refactor")
    parser.add_argument("--name", "-n", type=str, default="custom_code", help="Name for the code")
    parser.add_argument("--batch", "-b", type=str, help="Directory with Python files to process")
    parser.add_argument("--dacos", "-d", type=str, help="Path to DACOS dataset")
    parser.add_argument("--timeout", "-t", type=int, default=300, help="Timeout in seconds")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old runs")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = RefactoringPipeline(dacos_path=args.dacos)
    pipeline.timeout_seconds = args.timeout
    
    if args.cleanup:
        pipeline.cleanup_old_runs()
        return
    
    if args.batch:
        # Batch process directory
        dir_path = Path(args.batch)
        if not dir_path.exists():
            print(f"❌ Directory not found: {args.batch}")
            return
        
        py_files = list(dir_path.glob("*.py"))
        if not py_files:
            print(f"No Python files found in {args.batch}")
            return
        
        print(f"\n📁 Found {len(py_files)} Python files")
        results = pipeline.batch_process([str(f) for f in py_files])
        
        # Generate and save summary
        summary = pipeline.generate_summary_report(results)
        print("\n" + summary)
        
        summary_file = pipeline.output_dir / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        summary_file.write_text(summary, encoding='utf-8')
        print(f"\n📁 Summary saved to: {summary_file}")
        
    elif args.file:
        # Process single file
        result = pipeline.process_file(args.file)
        
        if result.get("success"):
            print("\n" + "="*60)
            print("✅ PROCESSING SUCCESSFUL")
            print("="*60)
            print(f"\n📁 Output: {result.get('run_dir')}")
            
            if "refactored_code" in result.get("steps", {}).get("refactoring", {}):
                refactored = result["steps"]["refactoring"]["refactored_code"]
                print("\n📄 Refactored Code Preview:")
                print("-"*40)
                preview_lines = refactored.split('\n')[:15]
                print('\n'.join(preview_lines))
                if len(refactored.split('\n')) > 15:
                    print("... (truncated)")
        else:
            print("\n❌ Processing failed")
            if "error" in result:
                print(f"Error: {result['error']}")
        
    elif args.code:
        # Process code string
        result = pipeline.process_code(args.code, args.name)
        
        if result.get("success"):
            print("\n" + "="*60)
            print("✅ PROCESSING SUCCESSFUL")
            print("="*60)
            print(f"\n📁 Output: {result.get('run_dir')}")
        else:
            print("\n❌ Processing failed")
            if "error" in result:
                print(f"Error: {result['error']}")
        
    else:
        parser.print_help()
        print("\n" + "="*60)
        print("📋 EXAMPLES:")
        print("="*60)
        print("  python integration_pipeline.py --file my_code.py")
        print("  python integration_pipeline.py --batch ./code_folder")
        print("  python integration_pipeline.py --code \"def add(a,b): return a+b\" --name test")
        print("  python integration_pipeline.py --cleanup")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)