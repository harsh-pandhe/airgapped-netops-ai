import networkx as nx
from datetime import datetime


class TopologyGraph:
    def __init__(self):
        self.G = nx.Graph()

    def add_device(self, node_id: str, data: dict):
        data.setdefault("added_at", datetime.now().isoformat())
        self.G.add_node(node_id, **data)

    def remove_device(self, node_id: str) -> bool:
        if node_id not in self.G:
            return False
        self.G.remove_node(node_id)  # also removes all incident edges
        return True

    def add_connection(self, source: str, target: str) -> bool:
        if source not in self.G or target not in self.G:
            return False
        self.G.add_edge(source, target, added_at=datetime.now().isoformat())
        return True

    def remove_connection(self, source: str, target: str) -> bool:
        if not self.G.has_edge(source, target):
            return False
        self.G.remove_edge(source, target)
        return True

    def update_device(self, node_id: str, data: dict) -> bool:
        if node_id not in self.G:
            return False
        self.G.nodes[node_id].update(data)
        self.G.nodes[node_id]["updated_at"] = datetime.now().isoformat()
        return True

    def get_graph_data(self) -> dict:
        nodes = [{"id": n, **self.G.nodes[n]} for n in self.G.nodes]
        edges = [{"source": u, "target": v} for u, v in self.G.edges]
        return {"nodes": nodes, "edges": edges}

    def get_neighbors(self, node_id: str) -> list:
        if node_id in self.G:
            return list(self.G.neighbors(node_id))
        return []

    def seed_data(self):
        self.add_device("RTR-001", {"label": "Cisco ASR",       "ip": "192.168.1.1"})
        self.add_device("RTR-002", {"label": "Juniper MX",      "ip": "192.168.1.2"})
        self.add_device("SW-001",  {"label": "Cisco Nexus",     "ip": "192.168.2.1"})
        self.add_device("FW-001",  {"label": "Palo Alto NGFW",  "ip": "192.168.0.1"})
        self.add_connection("RTR-001", "SW-001")
        self.add_connection("RTR-002", "SW-001")
        self.add_connection("FW-001",  "RTR-001")
        self.add_connection("FW-001",  "RTR-002")


manager = TopologyGraph()