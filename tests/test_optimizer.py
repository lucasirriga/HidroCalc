import sys
import os

# Add root to path
sys.path.append(os.getcwd())

# Mock QGIS environment
try:
    import qgis.core
except ImportError:
    import mock_qgis_setup

from qgis.core import QgsPointXY, QgsGeometry
from core.network import HydraulicNetwork, HydraulicNode, HydraulicLink
from core.solver import HydraulicSolver
from core.constants import VALID_DNS

def test_optimization():
    print("Initializing Network...")
    network = HydraulicNetwork()
    
    # Create Nodes
    # Source (0,0,0) -> Pipe 100m -> Valve (100,0,0) -> Pipe 100m -> Emitter (200,0,0)
    source = HydraulicNode("source", QgsPointXY(0,0), "source")
    source.elevation = 10.0 # High elevation to help pressure
    
    valve = HydraulicNode("valve", QgsPointXY(100,0), "valve")
    valve.elevation = 5.0
    
    emitter = HydraulicNode("emitter", QgsPointXY(200,0), "emitter")
    emitter.elevation = 0.0
    emitter.base_demand = 10.0 # m3/h (High demand to force large pipe)
    
    network.add_node(source)
    network.add_node(valve)
    network.add_node(emitter)
    
    # Create Links
    # Link 1: Source -> Valve
    geom1 = QgsGeometry.fromPolylineXY([source.point, valve.point])
    link1 = HydraulicLink("link1", geom1, "main")
    network.add_link(link1)
    network.connect_link("link1", "source", "valve")
    
    # Link 2: Valve -> Emitter
    geom2 = QgsGeometry.fromPolylineXY([valve.point, emitter.point])
    link2 = HydraulicLink("link2", geom2, "lateral")
    network.add_link(link2)
    network.connect_link("link2", "valve", "emitter")
    
    print("Network Created.")
    
    # Solver
    solver = HydraulicSolver(network)
    solver.min_pressure = 10.0 # Require 10 mca at emitter
    
    print("Running Generative Optimization...")
    solver.solve_generative()
    
    print("\nResults:")
    for link in network.links.values():
        print(f"Link {link.id}: DN {link.diameter} mm, HF {link.head_loss:.2f} m, V {link.velocity:.2f} m/s")
        
    for node in network.nodes.values():
        print(f"Node {node.id}: Pressure {node.pressure:.2f} mca")
        
    # Validation
    # With 10 m3/h, 100m length.
    # If DN 32: V ~ 3.4 m/s (Too high), HF huge.
    # If DN 50: V ~ 1.4 m/s.
    # If DN 75: V ~ 0.6 m/s.
    # We expect something around 50mm or 75mm depending on pressure.
    # Source Z=10, Emitter Z=0. Static Head = 10m.
    # Min Pressure = 10m.
    # So we have 10m static - HF = 10m required? No.
    # P_emitter = P_source - HF + (Z_source - Z_emitter)
    # P_source is usually set to 30m in solver._establish_direction (initial guess) or we should set it.
    # Solver sets source.pressure = 30.0
    # So 30 - HF + 10 = 40 - HF >= 10 -> HF <= 30.
    # We have plenty of head.
    # So optimizer should pick smallest diameter that satisfies velocity < 1.5 m/s?
    # Solver max_velocity is 1.5.
    # Wait, optimizer fitness is COST. It doesn't explicitly penalize velocity, only pressure.
    # But `_initial_sizing` uses velocity.
    # If optimizer only cares about cost, it will pick smallest DN (32mm) if pressure is ok.
    # DN 32: Area = 0.0008 m2. Q=10/3600 = 0.00277. V = 3.4 m/s.
    # HF for DN 32, 100m, Q=10?
    # HF = 10.67 * 100 * (0.00277^1.852) / (135^1.852 * 0.032^4.87)
    # This will be huge.
    # Let's see what it picks.
    
if __name__ == "__main__":
    test_optimization()
