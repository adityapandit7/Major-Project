from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pathlib import Path
import subprocess

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

INPUT_FILE = Path("input_code.py")


# --------------------------------------------------
# Home Page
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": None
        }
    )


# --------------------------------------------------
# Run Analysis
# --------------------------------------------------

@app.post("/run", response_class=HTMLResponse)
async def run_analysis(request: Request):

    try:

        # Read submitted code
        form = await request.form()
        code = form.get("code")

        if not code:
            raise Exception("No code submitted")

        # Save code for pipeline
        INPUT_FILE.write_text(code, encoding="utf-8")

        # Run main pipeline
        subprocess.run(
            ["python", "main.py"],
            check=True
        )

        # Find latest output directory
        output_dirs = sorted(Path("prompts_output").glob("run_*"))

        if not output_dirs:
            raise Exception("No output directory created")

        output_dir = output_dirs[-1]

        # Read outputs safely
        smell_file = output_dir / "3_smell_report.txt"
        refactor_file = output_dir / "5_refactor_prompt.txt"
        doc_file = output_dir / "6_documentation_prompt.txt"

        smell_report = smell_file.read_text(
            encoding="utf-8",
            errors="ignore"
        ) if smell_file.exists() else "No smell report found."

        refactor_prompt = refactor_file.read_text(
            encoding="utf-8",
            errors="ignore"
        ) if refactor_file.exists() else "No refactor prompt generated."

        doc_prompt = doc_file.read_text(
            encoding="utf-8",
            errors="ignore"
        ) if doc_file.exists() else "No documentation prompt generated."

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": {
                    "smells": smell_report,
                    "refactor": refactor_prompt,
                    "docs": doc_prompt
                }
            }
        )

    except Exception as e:

        # Show error on webpage instead of crashing
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": {
                    "smells": f"ERROR: {str(e)}",
                    "refactor": "",
                    "docs": ""
                }
            }
        )


# --------------------------------------------------
# Prevent favicon 404 spam
# --------------------------------------------------

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)