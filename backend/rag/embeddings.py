from functools import lru_cache
from langchain_community.embeddings import HuggingFaceEmbeddings


@lru_cache(maxsize=1)
def load_embedding():
    # loaded once per server process, not per request
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
