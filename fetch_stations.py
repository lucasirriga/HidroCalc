import json
import urllib.request
import ssl

def fetch_stations():
    url = "https://apitempo.inmet.gov.br/estacoes/T"
    try:
        # Ignore SSL certificate errors
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(url, context=ctx) as response:
            data = json.loads(response.read().decode())
            
        stations = []
        for s in data:
            try:
                # Filter only automatic stations (Axxx) or relevant ones
                # The DB has Axxx, Bxxx, Sxxx. Let's keep all that have coords.
                if s.get('VL_LATITUDE') and s.get('VL_LONGITUDE'):
                    stations.append({
                        'code': s['CD_ESTACAO'],
                        'name': s['DC_NOME'],
                        'lat': float(s['VL_LATITUDE']),
                        'lon': float(s['VL_LONGITUDE']),
                        'uf': s['SG_ESTADO']
                    })
            except (ValueError, TypeError):
                continue
                
        print(f"Fetched {len(stations)} stations.")
        
        with open('c:/PyQGIS/antigos/HidroCalc/stations.json', 'w', encoding='utf-8') as f:
            json.dump(stations, f, indent=4, ensure_ascii=False)
            
        print("stations.json updated successfully.")
        
    except Exception as e:
        print(f"Error fetching stations: {e}")

if __name__ == "__main__":
    fetch_stations()
