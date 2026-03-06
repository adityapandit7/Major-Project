from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.llm import build_codet5_llm

llm = build_codet5_llm()

doc_prompt = PromptTemplate.from_template("""
You are an expert software documentation agent.

Given the following repository snapshot, produce clean technical documentation.

Classes:
{classes}

Functions:
{functions}

Imports:
{imports}

Write developer-facing documentation in Markdown.
""")

doc_chain = (
    doc_prompt
    | llm
    | StrOutputParser()
)
