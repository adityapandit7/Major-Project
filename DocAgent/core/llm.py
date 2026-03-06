from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from langchain_community.llms import HuggingFacePipeline


def build_codet5_llm():
    model_name = "Salesforce/codet5-base"

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    pipe = pipeline(
        task="text2text-generation",
        model=model,
        tokenizer=tokenizer,
        max_length=512,
        do_sample=False,
        temperature=0.0,
    )

    return HuggingFacePipeline(pipeline=pipe)