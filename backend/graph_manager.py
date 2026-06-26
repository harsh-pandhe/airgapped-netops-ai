import networkx as nx

class TopologyGraph:
    def __init__(self):
        # Create an empty undirected graph
        self.G = nx.Graph()

    def add_device(self, node_id, data):
        """Adds a device (node) with metadata like cpu, role, etc."""
        self.G.add_node(node_id, **data)

    def add_connection(self, source, target):
        """Adds a physical/logical link (edge) between devices."""
        self.G.add_edge(source, target)

    def get_graph_data(self):
        """Formats the graph for your React frontend."""
        nodes = [{"id": n, **self.G.nodes[n]} for n in self.G.nodes]
        edges = [{"source": u, "target": v} for u, v in self.G.edges]
        return {"nodes": nodes, "edges": edges}

    def get_neighbors(self, node_id):
        """Requirement 3 helper: Returns connected devices for RAG traversal."""
        if node_id in self.G:
            return list(self.G.neighbors(node_id))
        return []

    def seed_data(self):
        """Temporary: Populate with your network devices."""
        self.add_device("RTR-001", {"label": "Cisco ASR", "ip": "192.168.1.1"})
        self.add_device("RTR-002", {"label": "Juniper MX", "ip": "192.168.1.2"})
        self.add_device("SW-001", {"label": "Cisco Nexus", "ip": "192.168.2.1"})
        self.add_connection("RTR-001", "SW-001")
        self.add_connection("RTR-002", "SW-001")    
        
    def get_neighbor_details(self, node_id):
        """Fetches all neighbor IDs for a specific node."""
        if node_id in self.G:
            # Returns a list of neighbor node IDs
            return list(self.G.neighbors(node_id))
        return []    

# Initialize the manager
manager = TopologyGraph()