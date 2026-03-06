# app/service.py

from graph.orchestrator import run_graph

def run_from_cli():
    print("Paste your Python code below.")
    print("Finish input with an empty line.\n")

    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)

    code = "\n".join(lines)

    artifacts = run_graph(code)

    print("\n===== SYNTHESIZED ARTIFACTS =====\n")
    print(artifacts)


if __name__ == "__main__":
    run_from_cli()
