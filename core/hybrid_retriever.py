from core.symbolic_retriever import symbolic_search


def hybrid_retrieve(query, retriever, symbol_index):

    # semantic retrieval
    semantic_results = retriever.invoke(query)

    semantic_docs = [
        {
            "symbol": r.metadata.get("symbol"),
            "content": r.page_content
        }
        for r in semantic_results
    ]

    # symbolic retrieval
    symbolic_docs = symbolic_search(query, symbol_index)

    # -------------------------
    # Remove duplicates
    # -------------------------

    seen = set()
    merged = []

    for doc in symbolic_docs + semantic_docs:

        symbol = doc.get("symbol")

        if symbol not in seen:
            merged.append(doc)
            seen.add(symbol)

    return merged