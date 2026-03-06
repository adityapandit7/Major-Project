def retrieve_context(retriever, query):

    docs = retriever.invoke(query)

    print("\nDEBUG --- Retrieved docs:", len(docs))

    context = "\n\n".join([d.page_content for d in docs])

    return context