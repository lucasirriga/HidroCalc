import math
from typing import List, Dict, Optional, Tuple
from qgis.core import QgsPointXY, QgsGeometry

class HydraulicNode:
    def __init__(self, node_id: str, point: QgsPointXY, node_type: str):
        self.id = node_id
        self.point = point
        self.type = node_type  # 'emitter', 'valve', 'source', 'junction'
        self.elevation = 0.0
        self.base_demand = 0.0  # Vazão consumida neste nó (ex: emissor)
        self.pressure = 0.0
        self.connected_links = [] # Todos os links conectados (independente da direção)
        self.downstream_links = [] # Links saindo deste nó (após definir direção)
        self.upstream_link = None  # Link chegando neste nó (após definir direção)

class HydraulicLink:
    def __init__(self, link_id: str, geometry: QgsGeometry, link_type: str):
        self.id = link_id
        self.geometry = geometry
        self.type = link_type  # 'hose', 'lateral', 'derivation', 'main'
        self.start_node: Optional[HydraulicNode] = None
        self.end_node: Optional[HydraulicNode] = None
        self.length = geometry.length()
        self.diameter = 0.0  # mm
        self.flow = 0.0      # m3/h
        self.head_loss = 0.0 # mca
        self.velocity = 0.0  # m/s

class HydraulicNetwork:
    def __init__(self):
        self.nodes: Dict[str, HydraulicNode] = {}
        self.links: Dict[str, HydraulicLink] = {}
        self.sources: List[HydraulicNode] = []

    def add_node(self, node: HydraulicNode):
        self.nodes[node.id] = node
        if node.type == 'source':
            self.sources.append(node)

    def add_link(self, link: HydraulicLink):
        self.links[link.id] = link

    def connect_link(self, link_id: str, start_node_id: str, end_node_id: str):
        if link_id not in self.links or start_node_id not in self.nodes or end_node_id not in self.nodes:
            return
        
        link = self.links[link_id]
        start_node = self.nodes[start_node_id]
        end_node = self.nodes[end_node_id]
        
        link.start_node = start_node
        link.end_node = end_node
        
        start_node.connected_links.append(link)
        end_node.connected_links.append(link)

    def clear(self):
        self.nodes.clear()
        self.links.clear()
        self.sources.clear()
