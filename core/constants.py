# -*- coding: utf-8 -*-

# Field Names
FIELD_LENGTH = "L"          # Comprimento (m)
FIELD_AREA = "Area"         # Área (ha)
FIELD_DN = "DN"             # Diâmetro Nominal (mm)
FIELD_FLOW = "V"            # Vazão (m³/h)
FIELD_HF = "HF"             # Perda de Carga (m.c.a)
FIELD_COUNT = "Aspersores"  # Contagem de pontos
FIELD_COST = "Custo"        # Custo (R$) - If used in future
FIELD_PROFIT = "Lucro"      # Lucro (%) - If used in future

# Default Values
DEFAULT_HAZEN_C = 135.0
DEFAULT_GRID_INTERVAL = 50.0
DEFAULT_MAP_ORIENTATION = "Retrato"

# Optimization
VALID_DNS = [32.0, 50.0, 75.0, 100.0, 125.0, 150.0]

# Relative Costs (Arbitrary units, proportional to diameter^1.5 approx or market data)
# User can adjust these later.
PIPE_COSTS = {
    32.0: 1.0,
    50.0: 1.8,
    75.0: 3.2,
    100.0: 5.5,
    125.0: 8.0,
    150.0: 11.0
}
