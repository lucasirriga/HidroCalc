from typing import List, Dict, Tuple, Optional
import math
from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsSpatialIndex, 
    QgsPointXY, QgsWkbTypes, QgsProject, QgsField, edit, QgsFeatureRequest
)
from qgis.PyQt.QtCore import QVariant

class LateralManager:
    def __init__(self):
        self.DIAMETERS = [25.0, 32.0, 50.0, 75.0] # mm
        self.HAZEN_C = 135.0

    def calculate_statistics(self, pipe_layer, hose_layer, emitter_layer, flow_per_emitter, only_selected=False, 
                           progress_callback=None, log_callback=None, highlight_callback=None):
        """
        Calculates simple flow statistics (Used by the "Quantify" tool mostly).
        Does NOT resize pipes.
        """
        return [], []

    def process_network(self, 
                       pipe_layer: QgsVectorLayer, 
                       hose_layer: QgsVectorLayer, 
                       emitter_layer: QgsVectorLayer, 
                       emitter_flow: float,
                       service_pressure: float,
                       only_selected: bool = False,
                       connection_tolerance: float = 0.5,
                       progress_callback=None, log_callback=None, highlight_callback=None) -> str:
        """
        Parte 1 & 2: Vazões (Hose -> Pipe).
        """
        try:
            if log_callback: log_callback("--- INICIANDO CÁLCULO DE VAZÃO ---")
            
            # ... (Validation code same as before) ...
            if not hose_layer or not hose_layer.isValid(): raise Exception("Camada de mangueiras inválida.")
            if not emitter_layer or not emitter_layer.isValid(): raise Exception("Camada de emissores inválida.")

            # Hose Fields
            idx_q_hose = hose_layer.fields().indexFromName("Q_Lh")
            if idx_q_hose == -1:
                hose_layer.dataProvider().addAttributes([QgsField("Q_Lh", QVariant.Double)])
                hose_layer.updateFields()
                idx_q_hose = hose_layer.fields().indexFromName("Q_Lh")

            # Pipe Fields (Q_Demand_m3h) - Changed name to be explicit
            idx_q_pipe = pipe_layer.fields().indexFromName("Q_Demand_m3h")
            if idx_q_pipe == -1:
                pipe_layer.dataProvider().addAttributes([QgsField("Q_Demand_m3h", QVariant.Double)])
                pipe_layer.updateFields()
                idx_q_pipe = pipe_layer.fields().indexFromName("Q_Demand_m3h")

            # 1. Calc Hose Flows
            if log_callback: log_callback(f"Calculando vazões de mangueiras (Emissor: {emitter_flow} l/h)...")
            hose_flows, total_network_l_h = self._calculate_hose_flows(
                hose_layer, emitter_layer, emitter_flow, log_callback
            )

            # Persist Hose Flows (L/h)
            with edit(hose_layer):
                for fid, flow in hose_flows.items():
                    hose_layer.changeAttributeValue(fid, idx_q_hose, flow)

            # 2. Assign to Pipes (m3/h)
            if log_callback: log_callback(f"Associando mangueiras aos tubos (Tolerância: {connection_tolerance}m)...")
            
            pipe_demands_l_h, connected_count, debug_info = self._assign_flows_to_pipes(
                pipe_layer, hose_layer, hose_flows, connection_tolerance
            )
            
            if log_callback: 
                log_callback(f"DEBUG: Mangueiras conectadas: {connected_count}")
                if connected_count == 0:
                    log_callback("ATENÇÃO: Nenhuma mangueira foi associada a tubos! Verifique a tolerância ou o desenho.")
            
            # Persist Pipe Demands (Convert to m3/h)
            pipes_with_demand = 0
            with edit(pipe_layer):
                for f in pipe_layer.getFeatures():
                    val_l_h = pipe_demands_l_h.get(f.id(), 0.0)
                    val_m3_h = val_l_h / 1000.0
                    
                    if val_m3_h > 0:
                        # Log first few updates to confirm write attempt
                        if pipes_with_demand < 3 and log_callback:
                            log_callback(f"DEBUG: Atualizando Tubo {f.id()} -> Vazão: {val_m3_h:.4f} m3/h")
                        
                        pipes_with_demand += 1
                        
                    pipe_layer.changeAttributeValue(f.id(), idx_q_pipe, val_m3_h)
            
            total_m3_h = total_network_l_h / 1000.0
            
            msg = f"Cálculo Concluído!\n" \
                  f"Mangueiras processadas: {len(hose_flows)}\n" \
                  f"Mangueiras conectadas: {connected_count}\n" \
                  f"Tubos com demanda: {pipes_with_demand}\n" \
                  f"Vazão Total: {total_m3_h:.3f} m³/h"
                  
            if log_callback: log_callback(msg)
            return msg
            
        except Exception as e:
            import traceback
            msg = f"Erro: {str(e)}"
            if log_callback: log_callback(msg)
            return msg

    def _assign_flows_to_pipes(self, pipe_layer, hose_layer, hose_flows, tolerance=0.5):
        """
        Soma a vazão das mangueiras ao tubo mais próximo de QUALQUER ponta (Início ou Fim).
        Retorna: ({pipe_id: flow_sum_l_h}, count_connected_hoses, debug_list)
        """
        pipe_demands = {}
        connected_hoses = 0
        debug_info = []
        
        pipe_idx = QgsSpatialIndex(pipe_layer.getFeatures())
        
        for hose in hose_layer.getFeatures():
            h_flow = hose_flows.get(hose.id(), 0.0)
            if h_flow <= 0: continue
            
            geom = hose.geometry()
            if not geom: continue
            line = geom.asMultiPolyline()[0] if geom.isMultipart() else geom.asPolyline()
            if not line: continue
            
            # Check BOTH Start and End
            points = [QgsPointXY(line[0]), QgsPointXY(line[-1])]
            
            # Find best match (closest pipe among both ends)
            best_dist = float('inf')
            best_pipe_id = None
            
            for pt in points:
                # Search slightly larger area than tolerance to debug "near misses"
                search_rad = max(tolerance, 1.0)
                nearest_ids = pipe_idx.nearestNeighbor(pt, 1)
                if not nearest_ids: continue
                
                pid = nearest_ids[0]
                pipe_feat = pipe_layer.getFeature(pid)
                p_geom = pipe_feat.geometry()
                dist = p_geom.distance(QgsGeometry.fromPointXY(pt))
                
                if dist <= tolerance:
                    if dist < best_dist:
                        best_dist = dist
                        best_pipe_id = pid
            
            if best_pipe_id is not None:
                pipe_demands[best_pipe_id] = pipe_demands.get(best_pipe_id, 0.0) + h_flow
                connected_hoses += 1
            
        return pipe_demands, connected_hoses, debug_info

    def _calculate_hose_flows(self, hose_layer, emitter_layer, flow_per_emitter, log_callback=None, tolerance=0.1):
        """
        Calcula a vazão de cada mangueira baseada na interseção com emissores.
        Retorna: (dict: {hose_id: flow}, float: total_flow)
        """
        hose_flows = {}
        total_flow = 0.0
        
        # 1. Indexar Emissores (Pontos)
        # Otimização com Índice Espacial
        if log_callback: log_callback("Indexando emissores...")
        emitter_idx = QgsSpatialIndex(emitter_layer.getFeatures())
        
        # 2. Iterar sobre Mangueiras (Linhas)
        feat_count = hose_layer.featureCount()
        processed = 0
        
        # Se quiser gravar no atributo da mangueira, precisamos garantir que o campo existe.
        # Por enquanto, apenas calculamos em memória conforme pedido, mas vamos preparar o dicionário.
        
        for hose in hose_layer.getFeatures():
            hose_geom = hose.geometry()
            if not hose_geom:
                continue
                
            # Interseção Preliminar (Bounding Box)
            # Buffer pequeno para garantir que pegue pontos na borda
            bbox = hose_geom.boundingBox()
            candidate_ids = emitter_idx.intersects(bbox)
            
            actual_count = 0
            
            # Verificação Fina (Distância Geométrica)
            # Usamos uma tolerância (ex: 10cm) para considerar que "toca"
            if candidate_ids:
                # Criar engine de geometria para medições rápidas se necessário, 
                # mas distance() direto costuma ser ok para poucos pontos.
                for eid in candidate_ids:
                    emitter_feat = emitter_layer.getFeature(eid)
                    emitter_geom = emitter_feat.geometry()
                    
                    # Verifica a distância do PONTO até a LINHA
                    # Se distance <= tolerance, considera conectado.
                    if hose_geom.distance(emitter_geom) <= tolerance:
                        actual_count += 1
            
            flow = actual_count * flow_per_emitter
            hose_flows[hose.id()] = flow
            total_flow += flow
            
            processed += 1
            
        return hose_flows, total_flow
