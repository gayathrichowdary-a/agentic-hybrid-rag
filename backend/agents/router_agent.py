def route_query(query):

    query = query.lower()

    graph_keywords = [
        "who",
        "relationship",
        "connected",
        "between",
        "linked",
        "belongs",
        "manager",
        "worked",
        "experience"
    ]

    vector_keywords = [
        "summarize",
        "summary",
        "explain",
        "describe",
        "tell",
        "what"
    ]

    for word in graph_keywords:
        if word in query:
            return "graph"

    for word in vector_keywords:
        if word in query:
            return "vector"

    return "hybrid"