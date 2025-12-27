# core/writer.py

def generate_docs(prompt: str) -> str:
    return (
        "## Auto-Generated Documentation\n\n"
        f"{prompt}\n\n"
        "This documentation was generated using filler logic."
    )
