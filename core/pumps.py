from typing import List, Dict, Optional
import math

class PumpSelector:
    def __init__(self):
        # Database of commercial pumps (Example data)
        # In a real app, this would come from a DB or JSON file
        self.pumps_db = [
            {"model": "Bomba A - 2CV", "power_cv": 2.0, "curve": {"a": -0.05, "b": 0.0, "c": 40.0}, "min_q": 5, "max_q": 20},
            {"model": "Bomba B - 3CV", "power_cv": 3.0, "curve": {"a": -0.04, "b": 0.0, "c": 50.0}, "min_q": 10, "max_q": 30},
            {"model": "Bomba C - 5CV", "power_cv": 5.0, "curve": {"a": -0.03, "b": 0.0, "c": 65.0}, "min_q": 15, "max_q": 45},
            {"model": "Bomba D - 7.5CV", "power_cv": 7.5, "curve": {"a": -0.02, "b": 0.0, "c": 80.0}, "min_q": 20, "max_q": 60},
            {"model": "Bomba E - 10CV", "power_cv": 10.0, "curve": {"a": -0.015, "b": 0.0, "c": 95.0}, "min_q": 30, "max_q": 80},
        ]

    def select_pump(self, flow_m3h: float, head_mca: float) -> List[Dict]:
        """
        Selects pumps that can operate at the given point (Flow, Head).
        Returns a list of suitable pumps sorted by power (efficiency proxy).
        """
        suitable_pumps = []
        
        for pump in self.pumps_db:
            # 1. Check Flow Range
            if not (pump["min_q"] <= flow_m3h <= pump["max_q"]):
                continue
                
            # 2. Check Head at Flow (Curve: H = aQ^2 + bQ + c)
            # Simple quadratic curve approximation
            a = pump["curve"]["a"]
            b = pump["curve"]["b"]
            c = pump["curve"]["c"]
            
            pump_head_at_flow = a * (flow_m3h ** 2) + b * flow_m3h + c
            
            # If pump provides enough head (with some tolerance, e.g. -10% to +20%)
            # Ideally, pump head should be >= required head
            if pump_head_at_flow >= head_mca:
                # Calculate operating point deviation
                # If pump head is WAY higher, we might need throttling (inefficient) or VFD
                # Let's accept if it's within reasonable range or if we assume VFD
                
                # Add efficiency info (mock)
                pump_copy = pump.copy()
                pump_copy["operating_head"] = round(pump_head_at_flow, 2)
                pump_copy["excess_head"] = round(pump_head_at_flow - head_mca, 2)
                
                suitable_pumps.append(pump_copy)
                
        # Sort by Power (lowest first -> most efficient usually for same duty)
        suitable_pumps.sort(key=lambda x: x["power_cv"])
        
        return suitable_pumps
