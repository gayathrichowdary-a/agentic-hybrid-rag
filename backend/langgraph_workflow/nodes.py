from graph.graph_retriever import GraphRetriever
from llm.groq_llm import generate_answer
from rag.retriever import retrieve_docs, get_context
from memory.memory_store import MemoryStore
from tools.web_search import search_web


def _mem_path(state):
    # one memory file per user (was a single file shared by everyone)
    return f"memory/user_{state.get('user_id', 'shared')}.json"


# ==================================
# ROUTER NODE
# ==================================
def router_node(state):
    query = state["query"].lower()

    system_keywords = [
        "which documents are loaded",
        "what documents are loaded",
        "list loaded documents",
        "list uploaded documents",
        "show uploaded documents",
        "show loaded documents"
    ]

    comparison_keywords = [
        "compare",
        "comparison",
        "which document is best",
        "best document",
        "better document",
        "difference between documents",
        "differences between documents",
        "similarities",
        "which file is best"
    ]

    graph_keywords = [
        "relationship",
        "relation",
        "connected",
        "connection",
        "linked",
        "depends on",
        "between"
    ]

    web_keywords = [
        "latest",
        "today",
        "current",
        "news",
        "recent",
        "weather",
        "price",
        "search web",
        "internet",
        "online"
    ]

    hybrid_keywords = [
        "explain",
        "difference",
        "how does",
        "architecture",
        "components",
        "workflow"
    ]

    if any(word in query for word in system_keywords):
        state["decision"] = "system"

    elif any(word in query for word in comparison_keywords):
        state["decision"] = "hybrid"

    elif any(word in query for word in graph_keywords):
        state["decision"] = "graph"

    elif any(word in query for word in web_keywords):
        state["decision"] = "web"

    elif any(word in query for word in hybrid_keywords):
        state["decision"] = "hybrid"

    else:
        state["decision"] = "vector"

    return state


# ==================================
# VECTOR RAG NODE
# ==================================
def vector_node(state):
    # Preserve context already prepared by Streamlit.
    vector_context = state.get("vector_context", "")

    # Fallback: retrieve from one vector database only if context was not sent.
    if not vector_context:
        vector_db = state.get("vector_db")

        if vector_db is not None:
            docs = retrieve_docs(vector_db, state["query"])

            vector_context = get_context(
                [("source", doc) for doc in docs]
            )

    state["vector_context"] = vector_context

    return state


# ==================================
# GRAPH RAG NODE
# ==================================
def graph_node(state):
    retriever = GraphRetriever()

    graph_context = retriever.get_subgraph_context(
        state["query"]
    )

    state["graph_context"] = graph_context

    return state


# ==================================
# HYBRID RAG NODE
# ==================================
def hybrid_node(state):
    # Important: Streamlit already sends combined context
    # from all relevant uploaded documents.
    vector_context = state.get("vector_context", "")

    # Fallback only if Streamlit did not send vector context.
    if not vector_context:
        vector_db = state.get("vector_db")

        if vector_db is not None:
            docs = retrieve_docs(
                vector_db,
                state["query"]
            )

            vector_context = get_context(
                [("source", doc) for doc in docs]
            )

    graph_retriever = GraphRetriever()

    graph_context = graph_retriever.get_subgraph_context(
        state["query"]
    )

    state["vector_context"] = vector_context
    state["graph_context"] = graph_context

    return state


# ==================================
# SYSTEM NODE
# ==================================
def system_node(state):
    uploaded_documents = state.get("uploaded_documents", [])

    if uploaded_documents:
        system_context = (
            "The following documents are currently loaded:\n- "
            + "\n- ".join(uploaded_documents)
        )
    else:
        system_context = "No documents are currently loaded."

    state["vector_context"] = system_context

    return state


# ==================================
# WEB SEARCH NODE
# ==================================
def web_node(state):
    web_context = search_web(state["query"])

    state["web_context"] = web_context

    return state


# ==================================
# MEMORY NODE
# ==================================
def memory_node(state):
    memory_store = MemoryStore(_mem_path(state))

    previous_memories = memory_store.search_memory(
        state["query"]
    )

    if previous_memories:
        memory_context = "\n\n".join(
            [
                f"Previous Question: {item['query']}\n"
                f"Previous Answer: {item['response']}"
                for item in previous_memories[-3:]
            ]
        )
    else:
        memory_context = state.get("memory_context") or "No related previous conversation found."

    state["memory_context"] = memory_context

    return state


# ==================================
# ANSWER NODE
# ==================================
def answer_node(state):
    context = f"""
VECTOR CONTEXT:
{state.get("vector_context", "")}

GRAPH CONTEXT:
{state.get("graph_context", "")}

MEMORY CONTEXT:
{state.get("memory_context", "")}

WEB CONTEXT:
{state.get("web_context", "")}
"""

    answer = generate_answer(
        context,
        state["query"]
    )

    memory_store = MemoryStore(_mem_path(state))

    memory_store.add_memory(
        state["query"],
        answer
    )

    state["final_answer"] = answer

    return state