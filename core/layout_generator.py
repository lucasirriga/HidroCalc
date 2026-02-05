import math
from typing import List, Tuple
from qgis.core import (
    QgsGeometry, QgsPointXY, QgsVectorLayer, QgsFeature, QgsField, QgsWkbTypes, QgsRectangle
)
from qgis.PyQt.QtCore import QVariant
from .constants import DEFAULT_HAZEN_C

class LayoutGenerator:
    def __init__(self):
        self.lateral_spacing = 10.0 # meters (between laterals/hoses)
        self.emitter_spacing = 1.0  # meters (along hose)
        self.lateral_angle = 0.0    # degrees
        self.emitter_pattern = 'rectangular' # 'rectangular' or 'triangular'
        
        # Hydraulic Params for N_max calculation
        self.service_pressure = 10.0 # mca
        self.emitter_flow = 1.6 # l/h
        self.hose_diameter = 16.0 # mm (internal)
        self.hose_roughness = DEFAULT_HAZEN_C

    def calculate_max_emitters_per_hose(self, max_pressure_variation_percent: float = 20.0) -> int:
        """
        Calculates max emitters per hose segment based on pressure variation limit.
        
        Logic:
        - Iteratively add emitters (n).
        - Calculate Head Loss (HF) for each segment k (from 2 to n).
        - Segment k carries flow for (n - k + 1) emitters.
        - Pressure difference (P_first - P_last) = Sum(HF_k) for k=2 to n.
        - Stop when (P_first - P_last) > (Service Pressure * Variation%).
        
        Args:
            max_pressure_variation_percent: Max allowed pressure variation as % of service pressure.
        """
        max_delta_p = self.service_pressure * (max_pressure_variation_percent / 100.0)
        
        # Hazen-Williams Constants
        c = self.hose_roughness
        d_m = self.hose_diameter / 1000.0
        # Pre-calculate constant part of HW formula: J = K * Q^1.852
        # J = 10.67 * Q^1.852 * D^-4.87 * C^-1.852
        # J = (10.67 * D^-4.87 * C^-1.852) * Q^1.852
        k_hw = 10.67 * (d_m ** -4.87) * (c ** -1.852)
        
        n = 1
        while True:
            # Check if n emitters are valid
            # We calculate the pressure drop from the 1st emitter to the n-th emitter.
            # This corresponds to the sum of HF for segments 2 to n.
            # Segment 1 is from inlet to 1st emitter (affects both P1 and Pn equally).
            
            current_delta_p = 0.0
            
            # Optimization: We could just add the new segment for n to the previous delta_p?
            # When we go from n to n+1:
            # The flow in ALL existing segments increases.
            # So we must recalculate everything or use a smarter update.
            # Given n is likely < 1000, a full recalculation is fast enough (O(n^2) total complexity).
            
            for k in range(2, n + 1):
                # Flow in segment k
                # It supplies emitters k to n. Count = n - k + 1
                emitters_downstream = n - k + 1
                q_segment_l_h = emitters_downstream * self.emitter_flow
                q_segment_si = q_segment_l_h / 1000.0 / 3600.0 # L/h -> m3/h -> m3/s
                
                if q_segment_si > 0:
                    j = k_hw * (q_segment_si ** 1.852)
                    hf = j * self.emitter_spacing
                    current_delta_p += hf
            
            if current_delta_p > max_delta_p:
                return max(1, n - 1)
            
            n += 1
            if n > 2000: # Safety limit
                return 2000

    def generate_global_emitters(self, area_geom: QgsGeometry) -> List[QgsGeometry]:
        """
        Generates emitters covering the entire area geometry.
        """
        emitters = []
        bbox = area_geom.boundingBox()
        center = bbox.center()
        
        # Rotate area to align with X axis for easier generation
        area_rotated = QgsGeometry(area_geom)
        area_rotated.rotate(-self.lateral_angle, center)
        bbox_rot = area_rotated.boundingBox()
        
        y_min = bbox_rot.yMinimum()
        y_max = bbox_rot.yMaximum()
        x_min = bbox_rot.xMinimum()
        x_max = bbox_rot.xMaximum()
        
        # Grid generation
        y = y_min
        row_idx = 0
        
        while y <= y_max:
            # Stagger offset for triangular pattern
            x_offset = 0.0
            if self.emitter_pattern == 'triangular' and (row_idx % 2 != 0):
                x_offset = self.emitter_spacing / 2.0
            
            x = x_min + x_offset
            while x <= x_max:
                pt = QgsPointXY(x, y)
                pt_geom = QgsGeometry.fromPointXY(pt)
                
                # Check if point is inside original area (need to rotate point back first)
                pt_geom_orig = QgsGeometry(pt_geom)
                pt_geom_orig.rotate(self.lateral_angle, center)
                
                if area_geom.contains(pt_geom_orig):
                    emitters.append(pt_geom_orig)
                
                x += self.emitter_spacing
            
            # Vertical spacing
            # For triangular equilateral: Dy = L * sin(60)
            dy = self.lateral_spacing
            if self.emitter_pattern == 'triangular':
                # Actually, lateral_spacing usually dictates the distance between hoses (rows)
                # If we want equilateral triangle between emitters on adjacent rows:
                # dy = self.emitter_spacing * math.sin(math.radians(60))
                # But usually hoses are spaced by lateral_spacing (e.g. 1m, 2m) which is independent of emitter spacing along hose.
                # So we keep lateral_spacing as row height.
                pass
                
            y += self.lateral_spacing
            row_idx += 1
            
        return emitters
