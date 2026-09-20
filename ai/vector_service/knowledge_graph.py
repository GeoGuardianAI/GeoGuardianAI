from typing import Dict, List, Any

class DisasterKnowledgeGraph:
    def __init__(self):
        self.nodes = {}  # id -> {label, type, properties}
        self.edges = []  # List of {source, target, type}
        self.initialize_graph()
        
    def initialize_graph(self):
        # Setup initial nodes representing Maharashtra state and Pune District scenario
        self.add_node("State:MH", "State", {"name": "Maharashtra"})
        self.add_node("Dist:Pune", "District", {"name": "Pune", "population": "9.4M"})
        self.add_node("City:Pune_City", "City", {"name": "Pune City"})
        
        self.add_edge("Dist:Pune", "State:MH", "LOCATED_IN")
        self.add_edge("City:Pune_City", "Dist:Pune", "LOCATED_IN")
        
        # Disaster reference nodes
        self.add_node("Disaster:Flood", "Disaster", {"name": "Riverine Flood", "severity": "High"})
        self.add_node("Disaster:Wildfire", "Disaster", {"name": "Forest Wildfire", "severity": "Medium"})
        self.add_node("Disaster:Earthquake", "Disaster", {"name": "Seismic Shaking", "severity": "Critical"})
        
        # Critical infrastructure nodes
        self.add_node("Hospital:Sassoon", "Hospital", {"name": "Sassoon General Hospital", "status": "Active", "capacity": "Normal"})
        self.add_node("Hospital:Noble", "Hospital", {"name": "Noble Hospital", "status": "At Risk", "capacity": "Strained"})
        self.add_node("Bridge:Sangam", "Bridge", {"name": "Sangam Bridge", "status": "Blocked", "damage": "Severe"})
        self.add_node("Bridge:Krishna", "Bridge", {"name": "Krishna River Bridge", "status": "Active", "damage": "None"})
        self.add_node("Shelter:SportsComplex", "Shelter", {"name": "Sports Complex", "status": "Active", "occupancy": "40%"})
        self.add_node("Sensor:WaterLevel", "Sensor", {"name": "Mutha River Sensor", "status": "Warning", "value": "1.9m"})
        
        # Connect infrastructure
        self.add_edge("Hospital:Sassoon", "City:Pune_City", "LOCATED_IN")
        self.add_edge("Hospital:Noble", "City:Pune_City", "LOCATED_IN")
        self.add_edge("Bridge:Sangam", "City:Pune_City", "CONNECTS")
        self.add_edge("Bridge:Krishna", "City:Pune_City", "CONNECTS")
        self.add_edge("Shelter:SportsComplex", "City:Pune_City", "LOCATED_IN")
        self.add_edge("Sensor:WaterLevel", "City:Pune_City", "MONITORS")
        
        # Scenario status connections
        self.add_edge("City:Pune_City", "Disaster:Flood", "AFFECTED_BY")
        self.add_edge("Hospital:Noble", "Disaster:Flood", "THREATENED_BY")
        self.add_edge("Bridge:Sangam", "Disaster:Flood", "DAMAGED_BY")
        self.add_edge("Sensor:WaterLevel", "Disaster:Flood", "TRIGGERS_ON")
        
    def add_node(self, node_id: str, label: str, properties: Dict[str, Any]):
        self.nodes[node_id] = {
            "id": node_id,
            "label": label,
            "properties": properties
        }
        
    def add_edge(self, source: str, target: str, rel_type: str):
        # Avoid duplicate edges
        for edge in self.edges:
            if edge["source"] == source and edge["target"] == target and edge["type"] == rel_type:
                return
        self.edges.append({
            "source": source,
            "target": target,
            "type": rel_type
        })
        
    def get_graph_data(self) -> Dict[str, Any]:
        """
        Returns JSON-serializable list of nodes and edges for rendering.
        """
        nodes_list = []
        for n_id, n_data in self.nodes.items():
            nodes_list.append({
                "id": n_id,
                "label": n_data["properties"].get("name", n_id),
                "type": n_data["label"],
                "status": n_data["properties"].get("status", "Active"),
                "details": n_data["properties"]
            })
            
        return {
            "nodes": nodes_list,
            "edges": self.edges
        }
        
    def query_relationships(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Returns connected edges and target nodes for a specific entity.
        """
        target_node_id = None
        for n_id, n_data in self.nodes.items():
            if entity_name.lower() in n_data["properties"].get("name", "").lower():
                target_node_id = n_id
                break
                
        if not target_node_id:
            return []
            
        results = []
        for edge in self.edges:
            if edge["source"] == target_node_id:
                target_data = self.nodes.get(edge["target"], {})
                results.append({
                    "relationship": edge["type"],
                    "direction": "out",
                    "target_type": target_data.get("label", "Unknown"),
                    "target_name": target_data.get("properties", {}).get("name", edge["target"])
                })
            elif edge["target"] == target_node_id:
                source_data = self.nodes.get(edge["source"], {})
                results.append({
                    "relationship": edge["type"],
                    "direction": "in",
                    "source_type": source_data.get("label", "Unknown"),
                    "source_name": source_data.get("properties", {}).get("name", edge["source"])
                })
                
        return results

    def path_find_safe_hospital(self, starting_location: str) -> List[Dict[str, Any]]:
        """
        Finds active hospitals in the location that are NOT damaged or blocked.
        """
        safe_hospitals = []
        for n_id, n_data in self.nodes.items():
            if n_data["label"] == "Hospital" and n_data["properties"].get("status") == "Active":
                safe_hospitals.append({
                    "hospital": n_data["properties"].get("name"),
                    "status": "Active",
                    "details": n_data["properties"]
                })
        return safe_hospitals
