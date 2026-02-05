from qgis.core import (
    QgsVectorLayer, QgsSpatialIndex, QgsFeatureRequest, QgsGeometry, 
    QgsPointXY, QgsWkbTypes
)
from .network import HydraulicNetwork, HydraulicNode, HydraulicLink
from .elevation import ElevationManager
from qgis.core import QgsRasterLayer

class NetworkBuilder:
    def __init__(self, network: HydraulicNetwork):
        self.network = network
        self.tolerance = 0.1 # Tolerance for snapping (meters)
        self.elevation_manager = ElevationManager()
        self.dem_layer = None

    def build(self, layers: dict, dem_layer: QgsRasterLayer = None):
        """
        Builds the network graph from the provided layers.
        layers: dict with keys 'hoses', 'laterals', 'derivations', 'main', 'valves', 'source'
        dem_layer: Optional DEM raster for elevation
        """
        self.dem_layer = dem_layer
        
        # 1. Add Fixed Nodes (Source, Valves)
        if 'source' in layers and layers['source']:
            self._add_point_nodes(layers['source'], 'source')
            
        if 'valves' in layers and layers['valves']:
            self._add_point_nodes(layers['valves'], 'valve')
            
        if 'emitters' in layers and layers['emitters']:
            # Emitters need special handling to read flow/demand if available
            # Or we assign default demand later.
            # For now, let's add them as nodes.
            self._add_point_nodes(layers['emitters'], 'emitter')
            
        # 2. Collect all lines and their types
        lines = [] # list of (geometry, type, original_id)
        if 'hoses' in layers and layers['hoses']:
            self._collect_lines(layers['hoses'], 'hose', lines)
        if 'laterals' in layers and layers['laterals']:
            self._collect_lines(layers['laterals'], 'lateral', lines)
        if 'derivations' in layers and layers['derivations']:
            self._collect_lines(layers['derivations'], 'derivation', lines)
        if 'main' in layers and layers['main']:
            self._collect_lines(layers['main'], 'main', lines)
            
        # 3. Build Graph Geometry
        # We need to find all intersection points and endpoints to define nodes
        # Then split lines at these nodes to define links
        
        # A. Collect Potential Node Points
        points = []
        
        # Add existing nodes (emitters, valves, etc)
        for node in self.network.nodes.values():
            points.append(node.point)
            
        # Add endpoints of all lines
        for geom, _, _ in lines:
            if geom.isMultipart():
                parts = geom.asMultiPolyline()
                for part in parts:
                    if part:
                        points.append(QgsPointXY(part[0]))
                        points.append(QgsPointXY(part[-1]))
            else:
                line = geom.asPolyline()
                if line:
                    points.append(QgsPointXY(line[0]))
                    points.append(QgsPointXY(line[-1]))
                    
        # B. Deduplicate Points (Snap)
        unique_nodes = self._deduplicate_points(points)
        
        # Add Junction Nodes to Network
        for pt_key, pt in unique_nodes.items():
            # Check if node already exists (from step 1)
            existing_node = self._find_node_at(pt)
            if not existing_node:
                node_id = f"junc_{pt.x():.3f}_{pt.y():.3f}"
                node = HydraulicNode(node_id, pt, 'junction')
                
                # Sample Elevation
                if self.dem_layer:
                    node.elevation = self.elevation_manager.sample_elevation(pt, self.dem_layer, self.dem_layer.crs())
                    
                self.network.add_node(node)
                
        # C. Create Links (Split lines at nodes)
        for geom, l_type, orig_id in lines:
            self._process_line_segments(geom, l_type, orig_id)

    def _collect_lines(self, layer, l_type, lines_list):
        for feat in layer.getFeatures():
            if feat.geometry():
                lines_list.append((feat.geometry(), l_type, feat.id()))

    def _deduplicate_points(self, points):
        """Merges points closer than tolerance."""
        unique = {} # "x_y" -> QgsPointXY
        for pt in points:
            # Simple grid snapping for deduplication
            # For better precision, use a spatial index or KD-tree
            key = f"{round(pt.x(), 2)}_{round(pt.y(), 2)}"
            if key not in unique:
                unique[key] = pt
        return unique

    def _find_node_at(self, point):
        # Linear search is slow, should use spatial index in Network
        # For now, iterating
        for node in self.network.nodes.values():
            if node.point.sqrDist(point) < (self.tolerance * self.tolerance):
                return node
        return None

    def _process_line_segments(self, geometry, l_type, orig_id):
        # Find all nodes that lie on this geometry
        nodes_on_line = []
        for node in self.network.nodes.values():
            # Buffer point slightly to check intersection/contains
            # Or use distance
            if geometry.distance(QgsGeometry.fromPointXY(node.point)) < self.tolerance:
                nodes_on_line.append(node)
        
        # Sort nodes by distance from start of line
        # Assuming single line for simplicity
        if geometry.isMultipart():
            return # TODO: Handle multipart
            
        line_geom = geometry.asPolyline()
        if not line_geom: return
        
        start_pt = line_geom[0]
        
        # Calculate distance of each node from start
        nodes_with_dist = []
        for node in nodes_on_line:
            dist = QgsGeometry.fromPolylineXY([start_pt, node.point]).length() # Approximation
            # Better: project point to line and get distance along line
            dist = geometry.lineLocatePoint(QgsGeometry.fromPointXY(node.point))
            nodes_with_dist.append((dist, node))
            
        nodes_with_dist.sort(key=lambda x: x[0])
        
        # Create links between consecutive nodes
        for i in range(len(nodes_with_dist) - 1):
            u_dist, u_node = nodes_with_dist[i]
            v_dist, v_node = nodes_with_dist[i+1]
            
            if u_node == v_node: continue
            
            # Create Link
            link_id = f"{l_type}_{orig_id}_{i}"
            # Geometry is segment between u and v
            # Construct simple line for now
            segment_geom = QgsGeometry.fromPolylineXY([u_node.point, v_node.point])
            
            link = HydraulicLink(link_id, segment_geom, l_type)
            self.network.add_link(link)
            self.network.connect_link(link_id, u_node.id, v_node.id)

    def _add_point_nodes(self, layer: QgsVectorLayer, node_type: str):
        # Try to find flow/demand field
        idx_flow = -1
        if node_type == 'emitter':
            fields = layer.fields()
            for f in ["Vazao", "Flow", "V", "Q", "Demand"]:
                idx = fields.indexFromName(f)
                if idx != -1:
                    idx_flow = idx
                    break
                    
        for feat in layer.getFeatures():
            geom = feat.geometry()
            if not geom: continue
            
            demand = 0.0
            if idx_flow != -1:
                try:
                    val = feat.attributes()[idx_flow]
                    if val: demand = float(val)
                except: pass
            
            if QgsWkbTypes.isMultiType(geom.wkbType()):
                points = geom.asMultiPoint()
                for pt in points:
                    node_id = f"{node_type}_{feat.id()}_{pt.x():.2f}"
                    node = HydraulicNode(node_id, pt, node_type)
                    node.base_demand = demand # Assign demand
                    
                    # Sample Elevation
                    if self.dem_layer:
                        node.elevation = self.elevation_manager.sample_elevation(pt, self.dem_layer, self.dem_layer.crs())
                        
                    self.network.add_node(node)
            else:
                pt = geom.asPoint()
                node_id = f"{node_type}_{feat.id()}"
                node = HydraulicNode(node_id, pt, node_type)
                node.base_demand = demand # Assign demand
                
                # Sample Elevation
                if self.dem_layer:
                    node.elevation = self.elevation_manager.sample_elevation(pt, self.dem_layer, self.dem_layer.crs())
                    
                self.network.add_node(node)
