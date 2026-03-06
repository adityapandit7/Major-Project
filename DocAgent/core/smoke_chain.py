from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.llm import build_codet5_llm


def build_smoke_chain():
    """
    Minimal chain to validate LangChain + CodeT5 wiring.
    DO NOT use for production documentation.
    """

    llm = build_codet5_llm()

    prompt = PromptTemplate.from_template(
        "Say 'SMOKE TEST OK' if you received this input:\n{input}"
    )

    return prompt | llm | StrOutputParser()
