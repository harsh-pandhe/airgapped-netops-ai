import networkx as nx

class GraphManager:
    def __init__(self):
        self.graph = nx.Graph()
        self._initialize_nodes_and_edges()

    def _initialize_nodes_and_edges(self):
        # Define devices
        devices = ["RTR-001", "RTR-002", "SW-001", "FW-001"]
        self.graph.add_nodes_from(devices)

        # Define connections (edges)
        connections = [
            ("RTR-001", "SW-001"),
            ("RTR-001", "RTR-002"),
            ("RTR-002", "FW-001"),
            ("SW-001", "FW-001")
        ]
        self.graph.add_edges_from(connections)

    def get_graph_data(self):
        # Convert graph to a JSON-ready format for the frontend
        return nx.node_link_data(self.graph)

# Instantiate the singleton
graph_manager = GraphManager()