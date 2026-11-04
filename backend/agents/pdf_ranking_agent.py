# agents/pdf_ranking_agent.py

def rank_pdfs(query, vector_stores):
    """
    Rank uploaded documents based on similarity score.

    Lower score = Better match
    """

    scores = []

    for name, db in vector_stores.items():

        try:
            docs = db.similarity_search_with_score(
                query,
                k=1
            )

            if docs:

                score = docs[0][1]

                scores.append(
                    (
                        name,
                        float(score)
                    )
                )

        except Exception as e:

            print(
                f"Ranking Error in {name}: {e}"
            )

    # Lower score = better similarity
    scores.sort(
        key=lambda x: x[1]
    )

    return scores


def get_best_document(query, vector_stores):
    """
    Returns the single best matching document as a (doc_name, score) tuple.
    Returns None if no documents are available.
    """
    ranking = rank_pdfs(query, vector_stores)

    if not ranking:
        return None

    best_doc = ranking[0][0]
    best_score = ranking[0][1]

    return (best_doc, best_score)