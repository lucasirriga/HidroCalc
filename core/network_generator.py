import math
from typing import List, Tuple
from qgis.core import (
    QgsGeometry, QgsPointXY, QgsVectorLayer, QgsFeature, QgsField, QgsWkbTypes
)
from qgis.PyQt.QtCore import QVariant

class NetworkGenerator:
    def __init__(self):
        self.lateral_angle = 0.0 # Angle of hoses

    def generate_hoses(self, emitters: List[QgsGeometry], max_hose_length: float = float('inf')) -> List[QgsGeometry]:
        """
        Generates hoses connecting emitters based on lateral_angle.
        Splits hoses if they exceed max_hose_length.
        """
        if not emitters:
            return []
            
        # 1. Group emitters by "row" (based on lateral_angle)
        center = emitters[0].asPoint()
        
        rotated_points = []
        for geom in emitters:
            pt = geom.asPoint()
            # Rotate -angle to align with X axis
            g = QgsGeometry.fromPointXY(pt)
            g.rotate(-self.lateral_angle, center)
            rotated_points.append((g.asPoint(), geom.asPoint())) # (rotated, original)
            
        # Sort by Y (rows) then X (position in row)
        rotated_points.sort(key=lambda p: (round(p[0].y(), 1), p[0].x()))
        
        rows = []
        current_row = []
        if rotated_points:
            current_y = rotated_points[0][0].y()
            
            for rot_pt, orig_pt in rotated_points:
                if abs(rot_pt.y() - current_y) > 0.5: # Tolerance for row binning
                    rows.append(current_row)
                    current_row = []
                    current_y = rot_pt.y()
                current_row.append((rot_pt, orig_pt))
            rows.append(current_row)
            
        # 2. Create Hoses
        hoses = []
        
        for row in rows:
            if not row: continue
            
            start_idx = 0
            while start_idx < len(row):
                current_segment = [row[start_idx]]
                end_idx = start_idx
                
                for i in range(start_idx + 1, len(row)):
                    dist = row[i][0].x() - current_segment[0][0].x()
                    if dist <= max_hose_length:
                        current_segment.append(row[i])
                        end_idx = i
                    else:
                        break
                
                if len(current_segment) > 1:
                    p_start = current_segment[0][1]
                    p_end = current_segment[-1][1]
                    hoses.append(QgsGeometry.fromPolylineXY([p_start, p_end]))
                
                start_idx = end_idx + 1
                
        return hoses

    def generate_sector_network(self, sector_emitters: List[QgsGeometry], sector_id: int, max_hose_length: float, boundary_geom: QgsGeometry = None) -> Tuple[List[QgsGeometry], List[QgsGeometry], List[QgsGeometry], QgsPointXY, List[QgsPointXY]]:
        """
        Generates the simplified intra-sector network:
        - Hoses: Connecting emitters.
        - Valve: At Centroid of emitters.
        - Lateral: Single line perpendicular to hoses, passing through valve, connecting all hoses.
        - Junctions: Intersections between Lateral and Hoses.
        
        Returns (hoses, laterals, collectors, valve_pos, junctions)
        Note: collectors list will be empty in this simplified model as we only have one lateral.
        """
        if not sector_emitters:
            return [], [], [], None, []

        # 1. Generate Hoses
        hoses = self.generate_hoses(sector_emitters, max_hose_length)
        if not hoses:
            return [], [], [], None, []

        # 2. Calculate Centroid for Valve
        # We can use the centroid of the sector emitters
        multipoint = QgsGeometry.fromMultiPointXY([e.asPoint() for e in sector_emitters])
        valve_pos = multipoint.centroid().asPoint()
        
        # 3. Generate Lateral
        # Lateral must be perpendicular to hoses (angle = lateral_angle + 90)
        # And pass through valve_pos.
        # It must extend to cover all hoses.
        
        center = valve_pos # Rotation center
        
        # Find extent of hoses in the lateral direction (perpendicular to hose direction)
        # Hose direction is self.lateral_angle.
        # Lateral direction is self.lateral_angle + 90.
        
        # Let's rotate everything by -(lateral_angle) so hoses are Horizontal (X).
        # Then Lateral is Vertical (Y).
        # We need to find the Min Y and Max Y of the hoses to define the lateral length.
        # And the Lateral X will be the Valve X (in rotated space).
        
        hose_ys = []
        for hose in hoses:
            bbox = hose.boundingBox()
            # To be precise, we should check the Y of the hose points.
            # Since hoses are generated aligned, checking one point is enough.
            v_pt = hose.vertexAt(0)
            pt = QgsPointXY(v_pt.x(), v_pt.y())
            g_pt = QgsGeometry.fromPointXY(pt)
            g_pt.rotate(-self.lateral_angle, QgsPointXY(0,0)) # Rotate around origin for consistent coords
            hose_ys.append(g_pt.asPoint().y())
            
        min_y = min(hose_ys)
        max_y = max(hose_ys)
        
        # Valve position in rotated space
        g_valve = QgsGeometry.fromPointXY(valve_pos)
        g_valve.rotate(-self.lateral_angle, QgsPointXY(0,0))
        valve_rot = g_valve.asPoint()
        
        lat_x = valve_rot.x()
        
        # Create Lateral Line (Vertical in rotated space)
        # Extend slightly past first and last hose
        p1_rot = QgsPointXY(lat_x, min_y - 1.0)
        p2_rot = QgsPointXY(lat_x, max_y + 1.0)
        
        # Rotate back
        g1 = QgsGeometry.fromPointXY(p1_rot)
        g1.rotate(self.lateral_angle, QgsPointXY(0,0))
        g2 = QgsGeometry.fromPointXY(p2_rot)
        g2.rotate(self.lateral_angle, QgsPointXY(0,0))
        
        lateral_geom = QgsGeometry.fromPolylineXY([g1.asPoint(), g2.asPoint()])
        
        # Check Boundary
        if boundary_geom and not boundary_geom.contains(lateral_geom):
            # If lateral is outside, we might need to trim it or warn.
            # But for now, let's assume sector geometry is inside boundary.
            # If the straight line goes out (concave boundary), we might have an issue.
            # Let's try to intersect with boundary?
            intersection = lateral_geom.intersection(boundary_geom)
            if not intersection.isEmpty():
                lateral_geom = intersection
        
        laterals = [lateral_geom]
        
        # 4. Generate Junctions
        # Intersections between Lateral and Hoses
        junctions = []
        junctions.append(valve_pos) # Valve is a junction on the lateral
        
        # We can calculate intersections mathematically or using geometry engine
        # Math is faster since we know they are orthogonal lines.
        # In rotated space: Lateral is x = lat_x. Hoses are y = hose_y.
        # Intersection is (lat_x, hose_y).
        # We just need to check if lat_x is within the hose X range.
        
        for hose in hoses:
            # Get hose range in rotated space
            v_start = hose.vertexAt(0)
            pt_start = QgsPointXY(v_start.x(), v_start.y())
            g_start = QgsGeometry.fromPointXY(pt_start)
            g_start.rotate(-self.lateral_angle, QgsPointXY(0,0))
            x1 = g_start.asPoint().x()
            
            v_end = hose.vertexAt(hose.get().numPoints()-1)
            pt_end = QgsPointXY(v_end.x(), v_end.y())
            g_end = QgsGeometry.fromPointXY(pt_end)
            g_end.rotate(-self.lateral_angle, QgsPointXY(0,0))
            x2 = g_end.asPoint().x()
            
            min_hx = min(x1, x2)
            max_hx = max(x1, x2)
            
            # Check if lateral crosses this hose
            if min_hx <= lat_x <= max_hx:
                # Intersection exists
                # Get Y (already have it from hose_ys logic, but let's re-get to be safe)
                y = g_start.asPoint().y()
                
                pt_rot = QgsPointXY(lat_x, y)
                g_int = QgsGeometry.fromPointXY(pt_rot)
                g_int.rotate(self.lateral_angle, QgsPointXY(0,0))
                junctions.append(g_int.asPoint())
                
                # We might need to split the hose at this junction?
                # The NetworkBuilder usually handles splitting if we provide the junction point.
                # But to be safe, we should ensure the hose has a vertex there?
                # NetworkBuilder splits lines at junctions if they are close.
                pass
        
        return hoses, laterals, [], valve_pos, junctions

    def generate_main_line(self, valves: List[QgsPointXY], source: QgsPointXY, boundary_geom: QgsGeometry = None) -> List[QgsGeometry]:
        """
        Generates main line connecting source to all valves using MST with orthogonal routing.
        Respects boundary_geom if provided.
        """
        if not valves:
            return []
            
        # Prim's Algorithm for MST
        nodes = [source] + valves
        n = len(nodes)
        parent = [-1] * n
        key = [float('inf')] * n
        mst_set = [False] * n
        
        key[0] = 0 # Source is root
        
        for _ in range(n):
            # Pick min key vertex
            min_val = float('inf')
            u = -1
            for i in range(n):
                if not mst_set[i] and key[i] < min_val:
                    min_val = key[i]
                    u = i
            
            if u == -1: break
            
            mst_set[u] = True
            
            # Update adjacent
            for v in range(n):
                if not mst_set[v]:
                    dist = nodes[u].sqrDist(nodes[v])
                    if dist < key[v]:
                        parent[v] = u
                        key[v] = dist
                        
        lines = []
        origin = QgsPointXY(0, 0)
        
        for i in range(1, n):
            p = parent[i]
            if p != -1:
                p1 = nodes[p]
                p2 = nodes[i]
                
                # Create orthogonal connection
                # Rotate points to align with lateral_angle (make them axis-aligned relative to crop)
                g1 = QgsGeometry.fromPointXY(p1)
                g1.rotate(-self.lateral_angle, origin)
                pt1_rot = g1.asPoint()
                
                g2 = QgsGeometry.fromPointXY(p2)
                g2.rotate(-self.lateral_angle, origin)
                pt2_rot = g2.asPoint()
                
                # Calculate two possible corner points in rotated space
                # Option A: Move X then Y -> Corner at (x2, y1)
                c1_rot = QgsPointXY(pt2_rot.x(), pt1_rot.y())
                
                # Option B: Move Y then X -> Corner at (x1, y2)
                c2_rot = QgsPointXY(pt1_rot.x(), pt2_rot.y())
                
                # Rotate corners back to real world
                gc1 = QgsGeometry.fromPointXY(c1_rot)
                gc1.rotate(self.lateral_angle, origin)
                corner1 = gc1.asPoint()
                
                gc2 = QgsGeometry.fromPointXY(c2_rot)
                gc2.rotate(self.lateral_angle, origin)
                corner2 = gc2.asPoint()
                
                # Decide which path to use based on boundary
                use_c1 = True
                if boundary_geom:
                    # Check if the corner is inside the boundary
                    is_c1_in = boundary_geom.contains(gc1)
                    is_c2_in = boundary_geom.contains(gc2)
                    
                    if is_c1_in and not is_c2_in:
                        use_c1 = True
                    elif not is_c1_in and is_c2_in:
                        use_c1 = False
                    elif not is_c1_in and not is_c2_in:
                        # Both outside.
                        # Try to pick the one that intersects less?
                        # Or just default to C1.
                        use_c1 = True
                    else:
                        # Both inside.
                        use_c1 = True
                
                if use_c1:
                    # Path: p1 -> corner1 -> p2
                    segment = [p1]
                    if p1 != corner1 and p2 != corner1:
                        segment.append(corner1)
                    segment.append(p2)
                else:
                    # Path: p1 -> corner2 -> p2
                    segment = [p1]
                    if p1 != corner2 and p2 != corner2:
                        segment.append(corner2)
                    segment.append(p2)
                    
                lines.append(QgsGeometry.fromPolylineXY(segment))
                
        return lines
