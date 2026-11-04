from typing import TypedDict, Any, List


class AgentState(TypedDict):
    query: str
    user_id: int
    system_context: str
    decision: str
    vector_db: object
    uploaded_documents: list
    vector_context: str
    graph_context: str
    memory_context: str 
    web_context: str
    final_answer: str