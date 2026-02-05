import os
import json
import sqlite3
import math
from typing import Optional, Dict, List, Tuple

class StationManager:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.stations_file = os.path.join(plugin_dir, 'stations.json')
        self.stations = self._load_stations()

    def _load_stations(self) -> List[Dict]:
        if not os.path.exists(self.stations_file):
            return []
        try:
            with open(self.stations_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def get_nearest_station(self, lat: float, lon: float) -> Optional[Dict]:
        if not self.stations:
            return None
        
        nearest = None
        min_dist = float('inf')

        for station in self.stations:
            s_lat = station.get('lat')
            s_lon = station.get('lon')
            if s_lat is None or s_lon is None:
                continue
            
            dist = math.sqrt((lat - s_lat)**2 + (lon - s_lon)**2)
            if dist < min_dist:
                min_dist = dist
                nearest = station
        
        if nearest:
            print(f"Nearest station found: {nearest['name']} ({nearest['code']}) at distance {min_dist:.4f} deg")
            print(f"Search coords: {lat}, {lon}. Station coords: {nearest['lat']}, {nearest['lon']}")
        else:
            print("No station found.")
            
        return nearest

    def get_all_stations(self) -> List[Dict]:
        """Retorna todas as estações ordenadas por nome."""
        return sorted(self.stations, key=lambda x: x.get('name', ''))

    def get_stations_sorted_by_distance(self, lat: float, lon: float) -> List[Dict]:
        """Retorna todas as estações ordenadas pela distância das coordenadas fornecidas."""
        def distance(station):
            s_lat = station.get('lat')
            s_lon = station.get('lon')
            if s_lat is None or s_lon is None:
                return float('inf')
            return math.sqrt((lat - s_lat)**2 + (lon - s_lon)**2)
        
        return sorted(self.stations, key=distance)

class ClimateDataManager:
    def __init__(self, plugin_dir: str):
        self.db_path = os.path.join(plugin_dir, 'clima_mensal.db')

    def get_station_data(self, station_code: str) -> List[Dict]:
        if not os.path.exists(self.db_path):
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT ano, mes, eto_total, precipitacao_total, balanco_hidrico, 
                       temp_max_media, temp_min_media, umidade_media
                FROM analise_mensal 
                WHERE estacao_codigo = ? 
                ORDER BY ano, mes
            """
            cursor.execute(query, (station_code,))
            rows = cursor.fetchall()
            conn.close()
            
            data = []
            for row in rows:
                data.append({
                    'ano': row[0],
                    'mes': row[1],
                    'eto': row[2],
                    'precipitacao': row[3],
                    'balanco': row[4],
                    'temp_max': row[5],
                    'temp_min': row[6],
                    'umidade': row[7]
                })
            return data
        except Exception as e:
            print(f"Error reading DB: {e}")
            return []

    def analyze_data(self, data: List[Dict]) -> Dict:
        if not data:
            return {}
        
        total_eto = sum(d['eto'] for d in data)
        total_precip = sum(d['precipitacao'] for d in data)
        avg_balanco = sum(d['balanco'] for d in data) / len(data)
        
        # Análise Anual
        annual_stats = {}
        for d in data:
            year = d['ano']
            if year not in annual_stats:
                annual_stats[year] = {'eto': 0.0, 'precip': 0.0, 'balanco': 0.0, 'count': 0}
            
            annual_stats[year]['eto'] += d['eto']
            annual_stats[year]['precip'] += d['precipitacao']
            annual_stats[year]['balanco'] += d['balanco']
            annual_stats[year]['count'] += 1
            
        # --- Análise Avançada (Dimensionamento & Manejo) ---
        
        # 1. Demanda Máxima (Dimensionamento)
        # Encontrar mês com maior ETo (Mês Crítico)
        # Calcular demanda diária (mm/dia) assumindo 30 dias/mês
        max_eto_month = max(data, key=lambda x: x['eto'])
        max_eto_daily = max_eto_month['eto'] / 30.0
        
        # 2. Precipitação Efetiva (Manejo)
        # Usando método USDA (simplificado): Pe = P * 0.75 (configurável futuramente)
        pe_factor = 0.75
        
        # Encontrar Ano Crítico (Menor Balanço Hídrico)
        # Queremos o ano onde (Precip - ETo) é mínimo (mais negativo ou mais próximo de zero)
        critical_year = min(annual_stats.keys(), key=lambda y: annual_stats[y]['balanco'])
        critical_year_data = [d for d in data if d['ano'] == critical_year]
        
        # Calcular totais APENAS para o ano crítico
        total_pe = sum(d['precipitacao'] for d in critical_year_data) * pe_factor
        
        # Recalcular Balanço Hídrico com Pe para o Ano Crítico
        # Déficit = ETo - Pe (se ETo > Pe)
        total_deficit_real = sum(max(0, d['eto'] - (d['precipitacao'] * pe_factor)) for d in critical_year_data)
        
        # Maior Déficit Mensal (Maior déficit em um único mês em todos os dados)
        max_monthly_deficit = 0
        for d in data:
            deficit = max(0, d['eto'] - (d['precipitacao'] * pe_factor))
            if deficit > max_monthly_deficit:
                max_monthly_deficit = deficit
        
        # 3. Janela de Irrigação (Sazonalidade)
        # Calcular frequência de déficit por mês (1-12)
        monthly_deficit_count = {m: 0 for m in range(1, 13)}
        years_count = len(annual_stats)
        
        for d in data:
            if d['eto'] > (d['precipitacao'] * pe_factor):
                monthly_deficit_count[d['mes']] += 1
                
        irrigation_window = {
            m: (count / years_count) * 100 if years_count > 0 else 0 
            for m, count in monthly_deficit_count.items()
        }

        return {
            'total_eto': total_eto,
            'total_precip': total_precip,
            'avg_balanco': avg_balanco,
            'count': len(data),
            'annual': annual_stats,
            'advanced': {
                'max_eto_month': max_eto_month,
                'max_eto_daily': max_eto_daily,
                'pe_factor': pe_factor,
                'total_pe': total_pe,
                'total_deficit_real': total_deficit_real,
                'max_monthly_deficit': max_monthly_deficit,
                'critical_year': critical_year,
                'irrigation_window': irrigation_window
            }
        }

    def generate_critical_analysis_text(self, analysis: Dict) -> str:
        """Gera um resumo textual interpretando o balanço hídrico."""
        avg_balanco = analysis.get('avg_balanco', 0)
        total_precip = analysis.get('total_precip', 0)
        total_eto = analysis.get('total_eto', 0)
        
        text = ""
        if total_precip < total_eto:
            text += "A região apresenta um déficit hídrico significativo no período analisado, indicando a necessidade de irrigação suplementar. "
        else:
            text += "A região apresenta um superávit hídrico no acumulado, mas a distribuição mensal deve ser observada nos gráficos. "
            
        if avg_balanco < 0:
            text += "O balanço hídrico médio é negativo, reforçando a demanda por reposição hídrica."
        else:
            text += "O balanço hídrico médio é positivo."
            
        return text
