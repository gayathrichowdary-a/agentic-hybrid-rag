def retrieve(vector_db, query):

    docs = vector_db.similarity_search(
        query,
        k=3
    )

    return docs
