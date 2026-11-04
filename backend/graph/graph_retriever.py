# graph/graph_retriever.py

from graph.graph_store import GraphStore
class GraphRetriever:
    def __init__(self):
        self.store = GraphStore()

    def search(self, query):
        results = []

        for node in self.store.graph.nodes:
            if query.lower() in node.lower():
                neighbors = self.store.get_neighbors(node)

                results.append({
                    "node": node,
                    "relations": neighbors
                })

        return results

    def get_subgraph_context(self, query):
        results = self.search(query)

        context = ""
        for r in results:
            context += f"\nNode: {r['node']}\nRelations: {r['relations']}\n"

        return context