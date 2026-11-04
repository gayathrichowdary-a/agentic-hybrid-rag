# graph/graph_store.py

import networkx as nx
import json
import os

class GraphStore:
    def __init__(self, path="graph/data_graph.json"):
        self.path = path
        self.graph = nx.DiGraph()
        self.load_graph()

    def add_node(self, node, node_type="entity"):
        self.graph.add_node(node, type=node_type)

    def add_edge(self, source, relation, target):
        self.graph.add_edge(source, target, relation=relation)

    def save_graph(self):
        data = nx.node_link_data(self.graph)
        with open(self.path, "w") as f:
            json.dump(data, f)

    def load_graph(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                data = json.load(f)
                self.graph = nx.node_link_graph(data)

    def get_neighbors(self, node):
        return list(self.graph.neighbors(node))