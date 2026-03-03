import ast
import difflib
from codebleu import calc_codebleu


# -------------------- UTILS --------------------

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# -------------------- AST VALIDITY --------------------

def ast_valid(code: str) -> float:
    try:
        ast.parse(code)
        return 1.0
    except SyntaxError:
        return 0.0


# -------------------- CHANGE RATIO --------------------

def change_ratio(original: str, refactored: str) -> float:
    matcher = difflib.SequenceMatcher(None, original, refactored)
    return matcher.ratio()   # 0–1


# -------------------- STYLE HEURISTIC --------------------

def style_improvement(original: str, refactored: str) -> float:
    """
    Simple heuristic:
    Lower average line length = better readability
    """
    def avg_line_length(code):
        lines = code.splitlines()
        if not lines:
            return 0
        return sum(len(l) for l in lines) / len(lines)

    before = avg_line_length(original)
    after = avg_line_length(refactored)

    if after < before:
        return 1.0
    return 0.5


# -------------------- CODEBLEU --------------------

def compute_codebleu(reference: str, prediction: str) -> float:
    result = calc_codebleu(
        references=[reference],
        predictions=[prediction],
        lang="python"
    )
    return round(result["codebleu"], 3)


# -------------------- CONFIDENCE SCORE --------------------

def compute_confidence_score(
    original_code: str,
    refactored_code: str,
    codebleu_score: float
) -> float:

    ast_score = ast_valid(refactored_code)
    change_score = change_ratio(original_code, refactored_code)
    style_score = style_improvement(original_code, refactored_code)

    confidence = (
        0.30 * ast_score +
        0.30 * codebleu_score +
        0.20 * style_score +
        0.20 * change_score
    )

    return round(confidence, 3)


# -------------------- MAIN --------------------

if __name__ == "__main__":
    original_code = read_file("input_code.py")
    refactored_code = read_file("refactored_code.py")

    codebleu_score = compute_codebleu(original_code, refactored_code)
    confidence_score = compute_confidence_score(
        original_code,
        refactored_code,
        codebleu_score
    )

    print("\n📊 REFACTORING EVALUATION RESULTS")
    print("--------------------------------")
    print("AST Validity        :", ast_valid(refactored_code))
    print("Change Ratio        :", round(change_ratio(original_code, refactored_code), 3))
    print("CodeBLEU Score      :", codebleu_score)
    print("Confidence Score    :", confidence_score)

    if confidence_score >= 0.7:
        print("\n✅ Refactoring ACCEPTED")
    else:
        print("\n⚠ Refactoring REJECTED (Low Confidence)")
