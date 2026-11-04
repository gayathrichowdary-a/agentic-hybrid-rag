# graph/graph_builder.py

import requests
import json
import os
from graph.graph_store import GraphStore
# REMOVED: circular import -> "from graph.graph_builder import GraphBuilder"

GROK_API_KEY = os.getenv("GROK_API_KEY")

class GraphBuilder:
    def __init__(self, embedding=None, chunk_text_fn=None, create_vector_db_fn=None):
        self.store = GraphStore()
        self.embedding = embedding
        self.chunk_text_fn = chunk_text_fn
        self.create_vector_db_fn = create_vector_db_fn

    def extract_graph(self, text):
        if not GROK_API_KEY:
            print("GROK_API_KEY not found.")
            return {
                "nodes": [],
                "edges": []
            }

        url = "https://api.x.ai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = f"""
Extract a knowledge graph from the text.

Return ONLY valid JSON.

Format:
{{
    "nodes": [
        "Entity1",
        "Entity2"
    ],
    "edges": [
        {{
            "source": "Entity1",
            "relation": "related_to",
            "target": "Entity2"
        }}
    ]
}}

TEXT:
{text[:8000]}
"""

        payload = {
            "model": "grok-beta",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            content = content.replace("```json", "").replace("```", "").strip()
            graph_data = json.loads(content)

            return graph_data

        except Exception as e:
            print(f"Graph extraction failed: {e}")
            return {
                "nodes": [],
                "edges": []
            }

    def build(self, text):
        graph_data = self.extract_graph(text)

        for node in graph_data.get("nodes", []):
            self.store.add_node(node)

        for edge in graph_data.get("edges", []):
            self.store.add_edge(
                edge["source"],
                edge["relation"],
                edge["target"]
            )

        self.store.save_graph()

        print(
            f"Graph Built: "
            f"{len(graph_data.get('nodes', []))} nodes, "
            f"{len(graph_data.get('edges', []))} edges"
        )

        return graph_data

    def build_from_file(self, file_path, load_document_fn, st=None):
        """
        Loads a document from file_path, builds the knowledge graph,
        chunks the text, and creates a vector DB.

        Args:
            file_path       : Path to the document file.
            load_document_fn: Function to load the document (e.g. from LangChain).
            st              : Streamlit module (optional) for displaying results.

        Returns:
            dict: {
                "graph_data" : graph nodes/edges dict,
                "vector_db"  : the created vector database,
                "chunks"     : the text chunks
            }
        """
        # 1. Load documents
        documents = load_document_fn(file_path)

        # 2. Concatenate all page content into one string
        full_text = ""
        for doc in documents:
            full_text += doc.page_content + "\n"

        # 3. Build knowledge graph
        graph_data = self.build(full_text)

        # 4. Optionally display results in Streamlit
        if st is not None:
            st.write("Graph Nodes:", len(graph_data["nodes"]))
            st.write("Graph Edges:", len(graph_data["edges"]))

        # 5. Chunk text and create vector DB
        vector_db = None
        chunks = []

        if self.chunk_text_fn is not None:
            chunks = self.chunk_text_fn(documents)

        if self.create_vector_db_fn is not None and self.embedding is not None:
            vector_db = self.create_vector_db_fn(chunks, self.embedding)

        return {
            "graph_data": graph_data,
            "vector_db": vector_db,
            "chunks": chunks
        }