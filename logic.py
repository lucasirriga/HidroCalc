import os
from typing import Optional, List, Dict, Any, Union
from .core.calculations import HydraulicCalculator
from .core.reports import ReportGenerator
from .core.network import HydraulicNetwork
from .core.network_builder import NetworkBuilder
from .core.solver import HydraulicSolver
from .core.pumps import PumpSelector
from .core.elevation import ElevationManager
from .core.geometry_tools import GeometryTools

from qgis.core import QgsProject, QgsMapLayer, edit, QgsField, QgsGeometry, QgsWkbTypes, QgsFeature, QgsSpatialIndex, QgsDistanceArea, QgsUnitTypes
from qgis.PyQt.QtCore import QVariant
class HydraulicsLogic:
    def __init__(self, iface: Any):
        self.iface = iface
        self.calculator = HydraulicCalculator(iface)
        self.reporter = ReportGenerator(iface, os.path.dirname(__file__))
        self.pump_selector = PumpSelector()
        self.elevation = ElevationManager()
        self.geometry_tools = GeometryTools()


    def calculate_length(self) -> str:
        return self.calculator.calculate_length()

    def calculate_area(self) -> str:
        return self.calculator.calculate_area()

    def define_attribute(self, field_name: str, value: float) -> str:
        return self.calculator.define_attribute(field_name, value)

    def calculate_hf(self, c_factor: float = 135.0) -> str:
        return self.calculator.calculate_hf(c_factor)

    def count_points(self, point_layer_name: str) -> str:
        return self.calculator.count_points(point_layer_name)

    def sum_attribute(self, field_name: str) -> str:
        return self.calculator.sum_attribute(field_name)

    def sum_tubes(self) -> str:
        return self.calculator.sum_tubes()

    def optimize_dn(self, limit_hf: float) -> str:
        return self.calculator.optimize_dn(limit_hf)

    def generate_pdf_report(self, output_path: str, orientation: str = "Retrato", grid_interval: float = 50.0) -> str:
        return self.reporter.generate_tubes_report(output_path, orientation, grid_interval)

    def generate_project_parts_report(self, parts: List[Dict], services: List[Dict], output_path: str, orientation: str = "Retrato", grid_interval: float = 50.0, climate_data: Optional[Dict] = None, chart_paths: Optional[Dict] = None) -> str:
        return self.reporter.generate_project_parts_report(parts, services, output_path, orientation, grid_interval, climate_data, chart_paths)

    def run_clipper_tool(self, line_layer: QgsMapLayer, poly_layer: QgsMapLayer) -> str:
        return self.geometry_tools.clip_lines_and_update(line_layer, poly_layer)

    def run_genetic_optimization(self) -> str:
        """
        Orchestrates the genetic optimization process:
        1. Identifies layers.
        2. Builds network.
        3. Runs genetic solver.
        4. Updates QGIS layers.
        """
        try:
            # 1. Identify Layers (Simple heuristic by name for now)
            project = QgsProject.instance()
            layers_map = {}
            
            # Define keywords to search for layers
            keywords = {
                'source': ['source', 'fonte', 'bomba'],
                'valves': ['valve', 'valvula', 'registro'],
                'emitters': ['emitter', 'emissor', 'aspersor'],
                'hoses': ['hose', 'lateral', 'linha_lateral'], # Hoses usually lateral lines
                'main': ['main', 'principal', 'adutora'],
                'derivations': ['derivation', 'derivacao', 'secundaria']
            }
            
            found_layers = {}
            
            for key, search_terms in keywords.items():
                for layer in project.mapLayers().values():
                    if layer.type() != QgsMapLayer.VectorLayer: continue
                    
                    name_lower = layer.name().lower()
                    if any(term in name_lower for term in search_terms):
                        found_layers[key] = layer
                        break # Take first match
            
            # Validate essential layers
            if 'source' not in found_layers:
                return "Erro: Camada de Fonte (Source/Bomba) não encontrada."
            if 'main' not in found_layers and 'derivations' not in found_layers and 'hoses' not in found_layers:
                return "Erro: Nenhuma camada de tubulação encontrada."
                
            # 1.1 Check for DEM
            dem_layer = self.elevation.get_dem_layer()
            dem_msg = ""
            if dem_layer:
                dem_msg = f" (Usando DEM: {dem_layer.name()})"
                
            # 2. Build Network
            network = HydraulicNetwork()
            builder = NetworkBuilder(network)
            builder.build(found_layers, dem_layer=dem_layer)
            
            if not network.nodes:
                return "Erro: A rede criada está vazia. Verifique as camadas."
                
            # 3. Run Solver (Genetic)
            solver = HydraulicSolver(network)
            # Configure solver parameters if needed
            solver.solve_generative()
            
            # 4. Update Layers
            # We need to map links back to features.
            # NetworkBuilder stores original ID in link ID: "{type}_{orig_id}_{segment_index}"
            # But wait, NetworkBuilder might split lines.
            # If it splits, we can't easily update the original feature unless we split it in QGIS too.
            # For this MVP, let's assume lines are NOT split (node-to-node topology already exists) 
            # OR we only update if the link corresponds to a full feature.
            
            # Actually, NetworkBuilder splits lines in `_process_line_segments`.
            # If we want to write back, we should ideally rewrite the geometry or just update attributes if 1-to-1.
            # If 1-to-N (one feature split into N links), we have a problem if they get different diameters.
            # But usually, a single pipe segment in QGIS should have one diameter.
            # If the optimizer assigns different diameters to segments of the same feature, we have a conflict.
            # For now, let's take the MAX diameter assigned to any segment of the feature and apply to the whole feature.
            # This is a safe approximation for "renovating" the pipe.
            
            updates = {} # (layer_id, feature_id) -> {'dn': val, 'hf': val}
            
            for link in network.links.values():
                # Parse ID: type_origId_index
                parts = link.id.split('_')
                if len(parts) < 3: continue
                
                l_type = parts[0]
                try:
                    orig_id = int(parts[1])
                except ValueError:
                    continue
                    
                # Find layer
                layer_key = None
                if l_type == 'main': layer_key = 'main'
                elif l_type == 'derivation': layer_key = 'derivations'
                elif l_type == 'lateral': layer_key = 'laterals' # hoses?
                elif l_type == 'hose': layer_key = 'hoses'
                
                if layer_key and layer_key in found_layers:
                    layer = found_layers[layer_key]
                    
                    if (layer.id(), orig_id) not in updates:
                        updates[(layer.id(), orig_id)] = {'dn': 0.0, 'hf': 0.0}
                    
                    # Accumulate (Max DN, Sum HF?)
                    # Actually HF is per segment. We should sum HF for the feature.
                    # DN should be uniform. If segments differ, we might have an issue.
                    # Let's take the largest DN to be safe.
                    
                    curr = updates[(layer.id(), orig_id)]
                    curr['dn'] = max(curr['dn'], link.diameter)
                    curr['hf'] += link.head_loss
            
            # Apply updates
            count = 0
            for (layer_id, fid), data in updates.items():
                layer = project.mapLayer(layer_id)
                if not layer: continue
                
                # Ensure fields exist
                idx_dn = self.calculator._ensure_field(layer, 'Diametro', QVariant.Double) # Using 'Diametro' or FIELD_DN
                idx_hf = self.calculator._ensure_field(layer, 'PerdaCarga', QVariant.Double)
                
                with edit(layer):
                    layer.changeAttributeValue(fid, idx_dn, float(data['dn']))
                    layer.changeAttributeValue(fid, idx_hf, float(data['hf']))
                    count += 1
            
            return f"Otimização Genética Concluída! {count} tubos atualizados.{dem_msg}"
            
        except Exception as e:
            import traceback
            return f"Erro na otimização: {str(e)}\n{traceback.format_exc()}"

    def select_pump(self, flow, head):
        """Selects suitable pumps."""
        try:
            pumps = self.pump_selector.select_pump(flow, head)
            if not pumps:
                return "Nenhuma bomba adequada encontrada no banco de dados."
                
            msg = "Bombas Sugeridas:\n\n"
            for p in pumps:
                msg += f"- {p['model']} ({p['power_cv']} CV)\n"
                msg += f"  Ponto de Operação: {p['operating_head']} mca (Excesso: {p['excess_head']} mca)\n\n"
            return msg
        except Exception as e:
            return f"Erro na seleção de bomba: {str(e)}"

    def get_vector_layers_names(self, geometry_type=None) -> List[str]:
        """Returns a list of names of vector layers, optionally filtered by geometry type."""
        layers = []
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer:
                if geometry_type is None or layer.geometryType() == geometry_type:
                    layers.append(layer.name())
        return sorted(layers)

    def calculate_irrigation_by_points(self, polygon_layer: QgsMapLayer, point_layer: QgsMapLayer, emitter_flow_lh: float, progress_callback=None) -> str:
        """
        Calculates Area, Point Count (Emitters), and Total Flow based on points inside polygons.
        Uses QgsDistanceArea for accurate area calculation.
        """
        try:
            if not polygon_layer or not point_layer:
                return "Camadas inválidas."

            # 1. Field Management (Case Insensitive Check)
            # Goal Names
            TARGET_AREA = "Área"
            TARGET_EMIT = "Emissores"
            TARGET_FLOW = "Vazão"
            
            # Use 'Area', 'Vazao' if Shapefile (simplified logic: check provider capabilities or just try)
            # But checking existing fields is safer to avoid duplication.
            
            existing_fields = {f.name().upper(): f.name() for f in polygon_layer.fields()}
            
            # Resolve actual field names to use
            field_area = existing_fields.get('ÁREA') or existing_fields.get('AREA') or TARGET_AREA
            field_emit = existing_fields.get('EMISSORES') or TARGET_EMIT
            field_flow = existing_fields.get('VAZÃO') or existing_fields.get('VAZAO') or TARGET_FLOW
            
            # Add missing fields
            fields_to_add = []
            if field_area not in [f.name() for f in polygon_layer.fields()]:
                fields_to_add.append(QgsField(field_area, QVariant.Double, len=10, prec=4))
            if field_emit not in [f.name() for f in polygon_layer.fields()]:
                fields_to_add.append(QgsField(field_emit, QVariant.Int))
            if field_flow not in [f.name() for f in polygon_layer.fields()]:
                fields_to_add.append(QgsField(field_flow, QVariant.Double, len=10, prec=3))
            
            if fields_to_add:
                polygon_layer.dataProvider().addAttributes(fields_to_add)
                polygon_layer.updateFields()
            
            # Refresh indices
            idx_area = polygon_layer.fields().indexFromName(field_area)
            idx_emit = polygon_layer.fields().indexFromName(field_emit)
            idx_flow = polygon_layer.fields().indexFromName(field_flow)

            # 2. Setup Area Calculation
            d = QgsDistanceArea()
            d.setSourceCrs(polygon_layer.crs(), QgsProject.instance().transformContext())
            d.setEllipsoid(QgsProject.instance().ellipsoid() or 'WGS84')

            # 3. Build Spatial Index for Points
            index = QgsSpatialIndex(point_layer.getFeatures())
            
            count_processed = 0
            features = list(polygon_layer.getFeatures())
            total = len(features)

            # 4. Iterate and Update
            with edit(polygon_layer):
                for i, feat in enumerate(features):
                    if progress_callback:
                        progress_callback(i, total)
                        
                    geom = feat.geometry()
                    if not geom: continue
                    
                    # Area (ha) - Standardize to Square Meters then Ha
                    area_m2 = d.measureArea(geom)
                    area_ha = area_m2 / 10000.0
                    
                    # Count Points
                    bbox = geom.boundingBox()
                    candidate_ids = index.intersects(bbox)
                    
                    real_count = 0
                    for cid in candidate_ids:
                        pt_feat = point_layer.getFeature(cid)
                        if geom.contains(pt_feat.geometry()):
                             real_count += 1
                    
                    # Flow (m3/h)
                    flow_total_m3h = (real_count * emitter_flow_lh) / 1000.0
                    
                    # Update
                    polygon_layer.changeAttributeValue(feat.id(), idx_area, area_ha)
                    polygon_layer.changeAttributeValue(feat.id(), idx_emit, real_count)
                    polygon_layer.changeAttributeValue(feat.id(), idx_flow, flow_total_m3h)
                    
                    count_processed += 1
            
            if progress_callback:
                progress_callback(total, total)
                
            return (f"Processado com sucesso!\n"
                    f"{count_processed} setores atualizados.\n"
                    f"Campos utilizados: '{field_area}', '{field_emit}', '{field_flow}'.")

        except Exception as e:
            return f"Erro ao calcular: {str(e)}"

    def define_sector_attribute(self, layer: QgsMapLayer, sector_name: str) -> str:
        """
        Defines the 'Setor' attribute for selected features.
        Creates the field if it doesn't exist.
        """
        try:
            if not layer or not layer.isValid():
                return "Camada inválida."
            
            selection = layer.selectedFeatureIds()
            if not selection:
                return "Nenhuma feição selecionada."

            # Field Management
            TARGET_FIELD = "Setor"
            existing_fields = {f.name().upper(): f.name() for f in layer.fields()}
            
            field_name = existing_fields.get(TARGET_FIELD.upper()) or TARGET_FIELD
            
            # Create field if missing
            if field_name not in [f.name() for f in layer.fields()]:
                # String field, len 50
                layer.dataProvider().addAttributes([QgsField(field_name, QVariant.String, len=50)])
                layer.updateFields()
            
            # Get index
            idx = layer.fields().indexFromName(field_name)
            if idx == -1:
                return f"Erro ao acessar campo '{field_name}'."
            
            # Update
            with edit(layer):
                for fid in selection:
                    layer.changeAttributeValue(fid, idx, sector_name)
                    
            return f"Setor '{sector_name}' atribuído a {len(selection)} feições."
            
        except Exception as e:
             return f"Erro ao definir setor: {e}"

    def register_water_source(self, layer: QgsMapLayer, attributes: Dict[str, Any]) -> str:
        """
        Registers water source data (attributes) to the selected feature.
        Creates missing fields if necessary.
        Updates if exists.
        """
        try:
            if not layer or not layer.isValid():
                return "Camada inválida."
            
            selection = layer.selectedFeatureIds()
            if not selection:
                return "Selecione uma fonte (ponto)."
            
            if len(selection) > 1:
                return "Selecione apenas uma fonte por vez."
            
            fid = selection[0]
            
            # Map of attribute keys to Field Definitions
            # Key corresponds to what UI sends.
            # Value is (FieldName, Type, Length, Precision)
            field_defs = {
                'name': ('NOME_FONTE', QVariant.String, 50, 0),
                'type': ('TIPO_FONTE', QVariant.String, 20, 0),
                'cap_arm': ('CAP_ARM', QVariant.Double, 10, 2),
                'cap_rec': ('CAP_REC', QVariant.Double, 10, 2),
                'nivel_est': ('NIVEL_EST', QVariant.Double, 10, 2),
                'nivel_din': ('NIVEL_DIN', QVariant.Double, 10, 2),
                'vazao': ('VAZAO_M3H', QVariant.Double, 10, 2),
                'cap_extr': ('CAP_EXTR', QVariant.Double, 10, 2)
            }
            
            # 1. Ensure Fields Exist
            existing_fields = {f.name().upper(): f.name() for f in layer.fields()}
            fields_to_add = []
            
            # We iterate over keys passed in 'attributes' (only relevant ones)
            # Or ensuring ALL potential source fields exist?
            # Safer to ensure only what we use, OR all to be consistent schema.
            # Let's ensure ALL defined in schema to avoid inconsistencies if user changes type later.
            
            for key, (fname, ftype, flen, fprec) in field_defs.items():
                real_name = existing_fields.get(fname.upper()) or fname
                if real_name not in [f.name() for f in layer.fields()]:
                     fields_to_add.append(QgsField(real_name, ftype, len=flen, prec=fprec))
            
            if fields_to_add:
                layer.dataProvider().addAttributes(fields_to_add)
                layer.updateFields()
            
            # 2. Update Attributes
            idx_map = {}
            for key, (fname, _, _, _) in field_defs.items():
                real_name = existing_fields.get(fname.upper()) or fname
                idx_map[key] = layer.fields().indexFromName(real_name)
            
            with edit(layer):
                for key, value in attributes.items():
                    if key in idx_map and idx_map[key] != -1:
                        # Handle NULLs or empty strings
                        if value == "" or value is None:
                            val = None # QVariant(QVariant.String) ?
                        else:
                            val = value
                        layer.changeAttributeValue(fid, idx_map[key], val)
                        
            return "Dados da fonte salvos com sucesso!"
            
        except Exception as e:
            return f"Erro ao salvar fonte: {e}"
