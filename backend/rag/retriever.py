def retrieve_docs(vector_db, query):

    docs = vector_db.similarity_search(
        query,
        k=3
    )

    return docs
def get_context(docs):

    context = ""

    for item in docs:

        # item is (filename, doc)
        if isinstance(item, tuple):
            name, doc = item
            context += f"[SOURCE: {name}]\n"
        else:
            doc = item

        context += doc.page_content
        context += "\n\n"

    return context