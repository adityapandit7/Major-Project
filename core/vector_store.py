from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

def build_vector_index(docs, embedding_model):

    documents = [
        Document(
            page_content=d["content"],
            metadata={
                "symbol": d["symbol"],
                "type": d["type"]
            }
        )
        for d in docs
    ]

    vector_db = Chroma.from_documents(
        documents,
        embedding_model,
        persist_directory="vector_db"
    )

    vector_db.persist()

    return vector_db