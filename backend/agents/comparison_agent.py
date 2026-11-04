def compare_documents(query):

    if "compare" in query.lower():
        return True

    if "meet" in query.lower():
        return True

    if "difference" in query.lower():
        return True

    if "which" in query.lower():
        return True

    return False