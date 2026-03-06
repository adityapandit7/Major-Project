def create_retriever(vector_db):
    """
    Create a stronger semantic retriever using MMR.
    """

    retriever = vector_db.as_retriever(
        search_type="mmr",   # better than similarity
        search_kwargs={
            "k": 5,          # final results
            "fetch_k": 20    # candidates considered
        }
    )

    return retriever