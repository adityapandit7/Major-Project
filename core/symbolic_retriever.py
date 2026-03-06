def symbolic_search(query, symbol_index):
    """
    Retrieve exact symbol matches from repository.
    """

    results = []

    query = query.lower()

    for symbol, data in symbol_index.items():

        if symbol in query:
            results.append(data)

    return results