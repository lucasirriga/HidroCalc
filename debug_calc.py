import math

class LayoutGenerator:
    def __init__(self):
        self.lateral_spacing = 10.0
        self.emitter_spacing = 5.0  # USER PARAM: 5m
        self.lateral_angle = 0.0
        self.emitter_pattern = 'rectangular'
        
        self.service_pressure = 20.0 # USER PARAM: 20 mca
        self.emitter_flow = 60.0 # USER PARAM: 60 l/h
        self.hose_diameter = 16.0 # USER PARAM: 16 mm
        self.hose_roughness = 140.0 # Default C

    def calculate_max_emitters_per_hose(self, max_pressure_variation_percent: float = 10.0) -> int:
        max_delta_p = self.service_pressure * (max_pressure_variation_percent / 100.0)
        print(f"Max Delta P: {max_delta_p} mca")
        
        c = self.hose_roughness
        d_m = self.hose_diameter / 1000.0
        
        # J = 10.67 * Q^1.852 * D^-4.87 * C^-1.852
        # J = (10.67 * D^-4.87 * C^-1.852) * Q^1.852
        k_hw = 10.67 * (d_m ** -4.87) * (c ** -1.852)
        print(f"K_HW: {k_hw}")
        
        n = 1
        while True:
            current_delta_p = 0.0
            
            # Debug for small n
            if n <= 5:
                print(f"--- Checking n={n} ---")
            
            for k in range(2, n + 1):
                emitters_downstream = n - k + 1
                q_segment_l_h = emitters_downstream * self.emitter_flow
                q_segment_si = q_segment_l_h / 3600.0
                
                if q_segment_si > 0:
                    j = k_hw * (q_segment_si ** 1.852)
                    hf = j * self.emitter_spacing
                    current_delta_p += hf
                    
                    if n <= 5:
                        print(f"  Seg {k}: Q={q_segment_l_h} l/h, J={j:.6f}, HF={hf:.6f}")
            
            if n <= 5:
                print(f"  Total Delta P: {current_delta_p:.6f}")

            if current_delta_p > max_delta_p:
                print(f"Limit reached at n={n}. Returning {n-1}")
                return max(1, n - 1)
            
            n += 1
            if n > 2000:
                return 2000

gen = LayoutGenerator()
n = gen.calculate_max_emitters_per_hose(10.0)
print(f"Result: {n}")
