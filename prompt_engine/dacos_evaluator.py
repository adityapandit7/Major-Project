"""
DACOS Evaluator Module
Used to benchmark the system against the DACOS dataset
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DACOSEvaluator:
    """
    Evaluates the prompting engine and refactoring system using DACOS dataset.
    """
    
    def __init__(self, dacos_path: Optional[str] = None):
        """
        Initialize evaluator with DACOS dataset.
        
        Args:
            dacos_path: Path to DACOS dataset (SQL, CSV, or JSON)
        """
        self.dacos_path = Path(dacos_path) if dacos_path else None
        self.dataset = []
        self.results = []
        
        if self.dacos_path and self.dacos_path.exists():
            self._load_dataset()
    
    def _load_dataset(self):
        """Load DACOS dataset from various formats."""
        
        # Try different file formats
        if self.dacos_path.suffix == '.json':
            self._load_json()
        elif self.dacos_path.suffix == '.csv':
            self._load_csv()
        elif self.dacos_path.suffix == '.sql':
            logger.info("SQL file detected - you may need to export to CSV/JSON first")
            # For SQL, we'd need to connect to database
            self._load_sql_instructions()
        else:
            # Try to find any JSON/CSV files in directory
            self._scan_directory()
    
    def _load_json(self):
        """Load from JSON file."""
        try:
            with open(self.dacos_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle different JSON structures
            if isinstance(data, list):
                self.dataset = data
            elif isinstance(data, dict) and 'samples' in data:
                self.dataset = data['samples']
            else:
                logger.warning(f"Unknown JSON structure in {self.dacos_path}")
                
            logger.info(f"Loaded {len(self.dataset)} samples from JSON")
            
        except Exception as e:
            logger.error(f"Failed to load JSON: {e}")
    
    def _load_csv(self):
        """Load from CSV file."""
        try:
            with open(self.dacos_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.dataset = list(reader)
            
            logger.info(f"Loaded {len(self.dataset)} samples from CSV")
            
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
    
    def _scan_directory(self):
        """Scan directory for dataset files."""
        for ext in ['*.json', '*.csv']:
            for file in self.dacos_path.glob(ext):
                logger.info(f"Found dataset file: {file}")
                # Load first one found
                self.dacos_path = file
                if ext == '*.json':
                    self._load_json()
                else:
                    self._load_csv()
                break
    
    def _load_sql_instructions(self):
        """Provide instructions for SQL export."""
        logger.info("""
To use DACOS SQL files:
1. Import SQL into SQLite/MySQL
2. Export tables to CSV format
3. Point evaluator to CSV file
        """)
    
    def create_test_samples(self, count: int = 10) -> List[Dict]:
        """
        Create test samples from dataset.
        
        Returns:
            List of test samples with code and expected smell labels
        """
        if not self.dataset:
            return self._create_sample_data(count)
        
        # Take first 'count' samples
        samples = []
        for i, item in enumerate(self.dataset[:count]):
            # Extract code and label based on common DACOS fields
            code = self._extract_code(item)
            label = self._extract_label(item)
            
            if code and label:
                samples.append({
                    "id": i,
                    "code": code,
                    "expected_smell": label,
                    "original_data": item
                })
        
        return samples
    
    def _extract_code(self, item: Dict) -> Optional[str]:
        """Extract code from dataset item."""
        # Common field names in DACOS
        code_fields = ['code', 'source', 'method_code', 'content', 'text']
        
        for field in code_fields:
            if field in item and item[field]:
                return item[field]
        
        return None
    
    def _extract_label(self, item: Dict) -> Optional[str]:
        """Extract smell label from dataset item."""
        # Common field names for labels
        label_fields = ['smell', 'label', 'smell_type', 'type', 'category']
        
        for field in label_fields:
            if field in item and item[field]:
                return item[field]
        
        return None
    
    def _create_sample_data(self, count: int) -> List[Dict]:
        """Create sample data if no dataset available."""
        logger.warning("No DACOS dataset found. Creating sample test data.")
        
        samples = [
            {
                "code": """
def process_data(name, email, age, address, phone, items, discount, tax_rate, shipping, notes):
    total = 0
    for item in items:
        total += item['price'] * item.get('quantity', 1)
    if discount:
        total *= 0.9
    if tax_rate:
        total *= (1 + tax_rate)
    return total
                """,
                "expected_smell": "Long Parameter List"
            },
            {
                "code": """
def calculate_order():
    # Validate input
    if not customer:
        return None
    if not items:
        return None
    
    # Calculate subtotal
    subtotal = 0
    for item in items:
        subtotal += item.price
    
    # Apply discounts
    if customer.is_premium:
        if subtotal > 100:
            subtotal *= 0.9
        elif subtotal > 50:
            subtotal *= 0.95
    
    # Calculate tax
    tax = subtotal * 0.08
    
    # Add shipping
    if subtotal < 50:
        shipping = 5.99
    else:
        shipping = 0
    
    # Format result
    result = {
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total': subtotal + tax + shipping
    }
    
    # Log order
    logger.info(f"Order calculated: {result}")
    
    return result
                """,
                "expected_smell": "Long Method"
            },
            {
                "code": """
def process_payment(payment_type, amount, card_number, expiry, cvv, 
                   bank_account, routing_number, check_number, 
                   customer_id, notes):
    
    if payment_type == 'credit':
        return process_credit(card_number, expiry, cvv, amount)
    elif payment_type == 'debit':
        return process_debit(card_number, expiry, cvv, amount)
    elif payment_type == 'bank':
        return process_bank(bank_account, routing_number, amount)
    elif payment_type == 'check':
        return process_check(check_number, amount)
    else:
        raise ValueError(f"Unknown payment type: {payment_type}")
                """,
                "expected_smell": "Long Parameter List"
            }
        ]
        
        return samples[:min(count, len(samples))]
    
    def evaluate_smell_detection(self, smell_detector, parsed_code_func) -> Dict:
        """
        Evaluate smell detection accuracy.
        
        Args:
            smell_detector: SmellDetector instance
            parsed_code_func: Function that parses code into required format
        
        Returns:
            Evaluation metrics
        """
        test_samples = self.create_test_samples(20)
        
        results = {
            "total": len(test_samples),
            "correct": 0,
            "incorrect": 0,
            "by_smell": {},
            "details": []
        }
        
        for sample in test_samples:
            try:
                # Parse the code
                parsed = parsed_code_func(sample["code"])
                
                # Detect smells
                detected_smells = smell_detector.detect_smells(parsed)
                
                # Get top detected smell (if any)
                top_smell = detected_smells[0]["name"] if detected_smells else "None"
                
                # Compare with expected
                expected = sample["expected_smell"]
                is_correct = (top_smell == expected)
                
                if is_correct:
                    results["correct"] += 1
                else:
                    results["incorrect"] += 1
                
                # Track by smell type
                if expected not in results["by_smell"]:
                    results["by_smell"][expected] = {"total": 0, "correct": 0}
                
                results["by_smell"][expected]["total"] += 1
                if is_correct:
                    results["by_smell"][expected]["correct"] += 1
                
                # Store detail
                results["details"].append({
                    "sample_id": sample.get("id", 0),
                    "expected": expected,
                    "detected": top_smell,
                    "correct": is_correct,
                    "all_detected": [s["name"] for s in detected_smells]
                })
                
            except Exception as e:
                logger.error(f"Error evaluating sample: {e}")
        
        # Calculate accuracy
        if results["total"] > 0:
            results["accuracy"] = results["correct"] / results["total"]
            
            # Calculate per-smell accuracy
            for smell, data in results["by_smell"].items():
                if data["total"] > 0:
                    data["accuracy"] = data["correct"] / data["total"]
        
        return results
    
    def save_evaluation_report(self, results: Dict, output_path: Optional[str] = None):
        """Save evaluation results to file."""
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"dacos_evaluation_{timestamp}.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Evaluation report saved to: {output_path}")
            
            # Also save a readable summary
            summary_path = output_path.replace('.json', '_summary.txt')
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(self._format_summary(results))
            
            logger.info(f"Summary saved to: {summary_path}")
            
        except Exception as e:
            logger.error(f"Failed to save evaluation: {e}")
    
    def _format_summary(self, results: Dict) -> str:
        """Format evaluation results as readable summary."""
        
        lines = []
        lines.append("="*60)
        lines.append("DACOS EVALUATION SUMMARY")
        lines.append("="*60)
        lines.append("")
        
        lines.append(f"Total samples: {results.get('total', 0)}")
        lines.append(f"Correct predictions: {results.get('correct', 0)}")
        lines.append(f"Incorrect predictions: {results.get('incorrect', 0)}")
        
        if 'accuracy' in results:
            lines.append(f"Overall accuracy: {results['accuracy']*100:.2f}%")
        
        lines.append("")
        lines.append("-"*40)
        lines.append("Per-Smell Accuracy:")
        lines.append("-"*40)
        
        for smell, data in results.get('by_smell', {}).items():
            if data['total'] > 0:
                acc = data.get('accuracy', data['correct']/data['total'])*100
                lines.append(f"  {smell}: {data['correct']}/{data['total']} ({acc:.2f}%)")
        
        lines.append("")
        lines.append("="*60)
        
        return "\n".join(lines)