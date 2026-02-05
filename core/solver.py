import math
from .network import HydraulicNetwork, HydraulicLink, HydraulicNode
from .constants import DEFAULT_HAZEN_C, VALID_DNS

class HydraulicSolver:
    def __init__(self, network: HydraulicNetwork):
        self.network = network
        self.max_velocity = 1.5 # m/s
        self.min_pressure = 10.0 # mca
        self.emitter_flow = 60.0 # l/h (default)
        self.simultaneous_sectors = 1

    def solve(self):
        """Executes the hydraulic calculation."""
        # 1. Establish Flow Direction (BFS from Source)
        self._establish_direction()
        
        # Determine Max Sector Flow for Simultaneity Cap
        max_sector_flow = 0.0
        for node in self.network.nodes.values():
            if node.base_demand > max_sector_flow:
                max_sector_flow = node.base_demand
        
        self.max_system_flow = max_sector_flow * self.simultaneous_sectors
        
        # 2. Accumulate Flow (Bottom-Up)
        self._accumulate_flow()
        
        # 3. Initial Sizing (Velocity Based)
        self._initial_sizing()
        
        # 4. Calculate Pressure (Top-Down)
        self._calculate_pressure()
        
        # 5. Optimize Network (Iterative Pressure Check)
        self._optimize_network()

    def _establish_direction(self):
        # Reset visited
        for node in self.network.nodes.values():
            node.visited = False
            node.upstream_link = None
            node.downstream_links = []
            
        queue = []
        for source in self.network.sources:
            source.visited = True
            source.pressure = 30.0 # Initial pressure guess or fixed
            queue.append(source)
            
        while queue:
            u = queue.pop(0)
            
            for link in u.connected_links:
                # Find the other node
                v = link.end_node if link.start_node == u else link.start_node
                
                if not v.visited:
                    v.visited = True
                    # Set direction u -> v
                    link.start_node = u
                    link.end_node = v
                    
                    u.downstream_links.append(link)
                    v.upstream_link = link
                    
                    queue.append(v)

    def _accumulate_flow(self):
        # We need to process nodes from leaves to root (reverse BFS order or recursion)
        for source in self.network.sources:
            self._get_node_flow(source)

    def _get_node_flow(self, node: HydraulicNode) -> float:
        # Calculate Potential Flow (Sum of all downstream demands)
        potential_flow = node.base_demand
        
        # Fallback to default emitter flow if demand is missing
        if node.type == 'emitter' and potential_flow <= 0:
            potential_flow = self.emitter_flow
        
        for link in node.downstream_links:
            child = link.end_node
            child_potential = self._get_node_flow(child)
            
            # Apply Cap
            design_flow = min(child_potential, self.max_system_flow)
            
            link.flow = design_flow
            potential_flow += design_flow 
            
        return potential_flow

    def _initial_sizing(self):
        for link in self.network.links.values():
            if link.flow <= 0:
                continue
                
            # Select Diameter
            # Q = V * A -> A = Q / V
            # Q in m3/h -> /3600 -> m3/s
            q_si = link.flow / 3600.0
            
            # Target Area
            target_area = q_si / self.max_velocity
            target_diameter_m = math.sqrt(target_area * 4 / math.pi)
            target_diameter_mm = target_diameter_m * 1000.0
            
            # Select nearest standard DN
            # For hoses (16mm or 20mm)
            if link.type == 'hose':
                if target_diameter_mm <= 16:
                    link.diameter = 16.0
                else:
                    link.diameter = 20.0
            else:
                # For pipes, find smallest valid DN that satisfies velocity
                selected_dn = VALID_DNS[-1]
                for dn in VALID_DNS:
                    if dn >= target_diameter_mm:
                        selected_dn = dn
                        break
                link.diameter = selected_dn
            
            self._update_head_loss(link)

    def _update_head_loss(self, link: HydraulicLink):
        q_si = link.flow / 3600.0
        d_m = link.diameter / 1000.0
        c = DEFAULT_HAZEN_C
        
        # Hazen-Williams
        if q_si > 0 and d_m > 0:
            hf = 10.67 * link.length * (q_si ** 1.852) / ((c ** 1.852) * (d_m ** 4.87))
            link.head_loss = hf
            
            area = math.pi * (d_m ** 2) / 4
            link.velocity = q_si / area
        else:
            link.head_loss = 0.0
            link.velocity = 0.0

    def _calculate_pressure(self):
        # Top-Down BFS
        queue = []
        for source in self.network.sources:
            queue.append(source)
            
        while queue:
            u = queue.pop(0)
            
            for link in u.downstream_links:
                v = link.end_node
                # Bernoulli (simplified): P_v = P_u - HF + (Z_u - Z_v)
                delta_z = u.elevation - v.elevation
                v.pressure = u.pressure - link.head_loss + delta_z
                queue.append(v)

    def _optimize_network(self):
        """Iteratively increases pipe diameters to satisfy min pressure."""
        max_iterations = 50
        
        for i in range(max_iterations):
            # Find critical node (lowest pressure)
            min_p = float('inf')
            critical_node = None
            
            for node in self.network.nodes.values():
                if node.type in ['valve', 'emitter'] and node.pressure < min_p:
                    min_p = node.pressure
                    critical_node = node
            
            if min_p >= self.min_pressure:
                break # All good
                
            if not critical_node:
                break
                
            # Backtrack to find path from source
            path_links = []
            curr = critical_node
            while curr.upstream_link:
                path_links.append(curr.upstream_link)
                curr = curr.upstream_link.start_node
                
            # Find best candidate to upgrade
            # Candidate: Pipe (not hose?) with highest Unit Head Loss
            # We usually don't resize hoses in main line optimization, but we can if needed.
            # Let's prioritize Main and Derivation lines.
            
            best_link = None
            max_unit_hf = -1.0
            
            for link in path_links:
                # Skip if already max DN
                if link.diameter >= VALID_DNS[-1]:
                    continue
                    
                # Calculate unit HF
                unit_hf = link.head_loss / link.length if link.length > 0 else 0
                
                # Prioritize pipes over hoses?
                if link.type == 'hose':
                    unit_hf *= 0.1 # Penalty to avoid resizing hoses unless necessary
                    
                if unit_hf > max_unit_hf:
                    max_unit_hf = unit_hf
                    best_link = link
            
            if best_link:
                # Upgrade
                current_dn = best_link.diameter
                new_dn = current_dn
                
                if best_link.type == 'hose':
                    if current_dn < 20.0: new_dn = 20.0
                else:
                    for dn in VALID_DNS:
                        if dn > current_dn:
                            new_dn = dn
                            break
                            
                if new_dn > current_dn:
                    best_link.diameter = new_dn
                    self._update_head_loss(best_link)
                    self._calculate_pressure() # Recalculate all pressures
                else:
                    break # Cannot upgrade further
            else:
                break # No candidates

    def solve_generative(self):
        """Executes the hydraulic calculation using Genetic Algorithm optimization."""
        from .optimizer import GeneticOptimizer

        # 1. Establish Flow Direction (BFS from Source)
        self._establish_direction()
        
        # Determine Max Sector Flow for Simultaneity Cap
        max_sector_flow = 0.0
        for node in self.network.nodes.values():
            if node.base_demand > max_sector_flow:
                max_sector_flow = node.base_demand
        
        self.max_system_flow = max_sector_flow * self.simultaneous_sectors
        
        # 2. Accumulate Flow (Bottom-Up)
        self._accumulate_flow()
        
        # 3. Initial Sizing (Velocity Based) - Provides a good seed
        self._initial_sizing()
        
        # 4. Calculate Pressure (Top-Down)
        self._calculate_pressure()
        
        # 5. Optimize Network (Genetic Algorithm)
        optimizer = GeneticOptimizer(self)
        optimizer.optimize()
