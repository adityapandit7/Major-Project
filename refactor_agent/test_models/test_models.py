import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

models_to_test = [
    "Salesforce/codet5p-770m",
    "Salesforce/codet5p-220m-py",
    "bigcode/santacoder",
    "microsoft/CodeGPT-small-py",
    "ise-uiuc/Magicoder-S-DS-6.7B"
]

test_code = """def calc(a,b):
    c=a+b
    return c"""

for model_name in models_to_test:
    try:
        print(f"\n{'='*60}")
        print(f"Testing: {model_name}")
        print('='*60)
        
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16)
        
        prompt = f"Refactor this Python code to use better names:\n\n{test_code}\n\nRefactored code:"
        
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_length=200)
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        print(f"Result:\n{result}")
        
    except Exception as e:
        print(f"Failed: {e}")