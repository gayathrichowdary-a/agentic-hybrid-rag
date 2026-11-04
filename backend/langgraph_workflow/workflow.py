from langgraph.graph import StateGraph, END

from langgraph_workflow.state import AgentState

from langgraph_workflow.nodes import (
    router_node,
    vector_node,
    graph_node,
    hybrid_node,
    system_node,
    web_node,
    memory_node,
    answer_node
)


workflow = StateGraph(AgentState)


# ============================
# ADD NODES
# ============================

workflow.add_node("router", router_node)
workflow.add_node("vector", vector_node)
workflow.add_node("graph", graph_node)
workflow.add_node("hybrid", hybrid_node)
workflow.add_node("system", system_node)
workflow.add_node("web", web_node)
workflow.add_node("memory", memory_node)
workflow.add_node("answer", answer_node)


# ============================
# ENTRY POINT
# ============================

workflow.set_entry_point("router")


# ============================
# ROUTING FUNCTION
# ============================

def route_decision(state):
    return state["decision"]


# ============================
# CONDITIONAL ROUTES
# ============================

workflow.add_conditional_edges(
    "router",
    route_decision,
    {
        "vector": "vector",
        "graph": "graph",
        "hybrid": "hybrid",
        "system": "system",
        "web": "web"
    }
)


# ============================
# RETRIEVAL → MEMORY
# ============================

workflow.add_edge("vector", "memory")
workflow.add_edge("graph", "memory")
workflow.add_edge("hybrid", "memory")
workflow.add_edge("system", "memory")
workflow.add_edge("web", "memory")


# ============================
# MEMORY → ANSWER
# ============================

workflow.add_edge("memory", "answer")


# ============================
# ANSWER → END
# ============================

workflow.add_edge("answer", END)


app = workflow.compile()