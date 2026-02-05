import math
from typing import Optional, Union, List, Dict, Any
from qgis.core import (
    QgsProject, QgsUnitTypes, QgsCoordinateReferenceSystem, 
    QgsCoordinateTransform, QgsWkbTypes, edit, QgsField, 
    QgsFeatureRequest, QgsSpatialIndex, QgsGeometry, QgsVectorLayer
)
from qgis.PyQt.QtCore import QVariant
from .constants import (
    FIELD_LENGTH, FIELD_AREA, FIELD_COUNT, FIELD_DN, FIELD_FLOW, FIELD_HF,
    DEFAULT_HAZEN_C, VALID_DNS
)

class HydraulicCalculator:
    def __init__(self, iface: Any):
        self.iface = iface

    def _get_active_layer(self, geometry_type: Optional[int] = None) -> QgsVectorLayer:
        layer = self.iface.activeLayer()
        if not layer:
            raise ValueError("Nenhuma camada ativa.")
        
        if geometry_type is not None:
            if QgsWkbTypes.geometryType(layer.wkbType()) != geometry_type:
                raise ValueError(f"A camada deve ser do tipo {QgsWkbTypes.displayString(geometry_type)}.")
        
        return layer

    def _ensure_field(self, layer: QgsVectorLayer, field_name: str, field_type: QVariant.Type) -> int:
        """Ensures the field exists and returns its index."""
        idx = layer.fields().indexFromName(field_name)
        if idx == -1:
            ok = layer.dataProvider().addAttributes([QgsField(field_name, field_type)])
            if not ok:
                raise RuntimeError(f"Falha ao criar campo '{field_name}'.")
            layer.updateFields()
            idx = layer.fields().indexFromName(field_name)
        return idx

    def calculate_length(self) -> str:
        try:
            layer = self._get_active_layer(QgsWkbTypes.LineGeometry)
            idx = self._ensure_field(layer, FIELD_LENGTH, QVariant.Double)

            project_crs = QgsProject.instance().crs()
            target_crs = project_crs if (project_crs.isValid() and project_crs.mapUnits() == QgsUnitTypes.DistanceMeters) \
                else QgsCoordinateReferenceSystem("EPSG:3857")
            
            xform = QgsCoordinateTransform(layer.crs(), target_crs, QgsProject.instance())
            
            nulls = 0
            count = 0
            
            with edit(layer):
                for feat in layer.getFeatures():
                    geom = feat.geometry()
                    if not geom or geom.isEmpty():
                        nulls += 1
                        continue
                    geom.transform(xform)
                    length = float(geom.length())
                    layer.changeAttributeValue(feat.id(), idx, length)
                    count += 1
            
            return f"Calculado em {count} feições. Vazias: {nulls}"
        except Exception as e:
            return f"Erro ao calcular comprimento: {str(e)}"

    def calculate_area(self) -> str:
        try:
            layer = self._get_active_layer(QgsWkbTypes.PolygonGeometry)
            idx = self._ensure_field(layer, FIELD_AREA, QVariant.Double)

            project_crs = QgsProject.instance().crs()
            target_crs = project_crs if (project_crs.isValid() and project_crs.mapUnits() == QgsUnitTypes.DistanceMeters) \
                else QgsCoordinateReferenceSystem("EPSG:3857")
            
            xform = QgsCoordinateTransform(layer.crs(), target_crs, QgsProject.instance())

            updated = 0
            nulls = 0
            with edit(layer):
                for feat in layer.getFeatures():
                    geom = feat.geometry()
                    if not geom or geom.isEmpty():
                        nulls += 1
                        continue
                    geom.transform(xform)
                    area_m2 = float(geom.area())
                    area_ha = area_m2 / 10000.0
                    layer.changeAttributeValue(feat.id(), idx, area_ha)
                    updated += 1
            return f"Área calculada em {updated} feições."
        except Exception as e:
            return f"Erro ao calcular área: {str(e)}"

    def define_attribute(self, field_name: str, value: float) -> str:
        try:
            layer = self._get_active_layer()
            sel_ids = layer.selectedFeatureIds()
            if not sel_ids:
                return "Nenhuma feição selecionada."
            
            idx = self._ensure_field(layer, field_name, QVariant.Double)
            
            count = 0
            with edit(layer):
                for fid in sel_ids:
                    layer.changeAttributeValue(fid, idx, float(value))
                    count += 1
            return f"{count} feições atualizadas com {field_name}={value}."
        except Exception as e:
            return f"Erro ao definir atributo: {str(e)}"

    def calculate_hf(self, c_factor: float = DEFAULT_HAZEN_C) -> str:
        try:
            layer = self._get_active_layer(QgsWkbTypes.LineGeometry)
            required = [FIELD_FLOW, FIELD_DN, FIELD_LENGTH]
            field_names = [field.name() for field in layer.fields()]
            missing = [f for f in required if f not in field_names]
            if missing:
                return f"Campos ausentes: {', '.join(missing)}"
            
            idx_hf = self._ensure_field(layer, FIELD_HF, QVariant.Double)
            
            idx_v = layer.fields().indexFromName(FIELD_FLOW)
            idx_dn = layer.fields().indexFromName(FIELD_DN)
            idx_l = layer.fields().indexFromName(FIELD_LENGTH)

            updated = 0
            invalid = 0
            
            with edit(layer):
                for feat in layer.getFeatures():
                    try:
                        # Access by index is faster than by name
                        v_val = feat.attributes()[idx_v]
                        dn_val = feat.attributes()[idx_dn]
                        l_val = feat.attributes()[idx_l]
                        
                        if v_val is None or dn_val is None or l_val is None:
                            invalid += 1
                            continue

                        V = float(v_val)
                        DN = float(dn_val)
                        L = float(l_val)
                        
                        if V <= 0 or DN <= 0 or L < 0:
                            invalid += 1
                            continue

                        Q = V / 3600.0
                        D = DN / 1000.0
                        hf = 10.67 * L * (Q ** 1.852) / ((c_factor ** 1.852) * (D ** 4.87))
                        
                        layer.changeAttributeValue(feat.id(), idx_hf, float(hf))
                        updated += 1
                    except (ValueError, TypeError):
                        invalid += 1
            return f"HF calculado: {updated} ok, {invalid} inválidos."
        except Exception as e:
            return f"Erro ao calcular HF: {str(e)}"

    def count_points(self, point_layer_name: str) -> str:
        try:
            poly_layer = self._get_active_layer(QgsWkbTypes.PolygonGeometry)
            
            # Find point layer
            pts_layers = [l for l in QgsProject.instance().mapLayers().values() if l.name() == point_layer_name]
            if not pts_layers:
                return "Camada de pontos não encontrada."
            pts_layer = pts_layers[0]

            idx_cnt = self._ensure_field(poly_layer, FIELD_COUNT, QVariant.Int)
            
            idx = QgsSpatialIndex(pts_layer.getFeatures())
            xform = QgsCoordinateTransform(poly_layer.crs(), pts_layer.crs(), QgsProject.instance())
            
            updated = 0
            with edit(poly_layer):
                for feat in poly_layer.getFeatures():
                    geom = feat.geometry()
                    if not geom or geom.isEmpty():
                        continue
                    
                    # Transform polygon to point layer CRS for spatial query
                    g_trans = QgsGeometry(geom)
                    g_trans.transform(xform)
                    
                    cand_ids = idx.intersects(g_trans.boundingBox())
                    count = 0
                    if cand_ids:
                        req = QgsFeatureRequest().setFilterFids(cand_ids)
                        for pt in pts_layer.getFeatures(req):
                            if g_trans.intersects(pt.geometry()):
                                count += 1
                    
                    poly_layer.changeAttributeValue(feat.id(), idx_cnt, count)
                    updated += 1
            return f"Contagem concluída em {updated} polígonos."
        except Exception as e:
            return f"Erro ao contar pontos: {str(e)}"

    def sum_attribute(self, field_name: str) -> str:
        try:
            layer = self._get_active_layer()
            if field_name not in [f.name() for f in layer.fields()]:
                return f"Campo {field_name} não existe."
            
            total = 0.0
            count = 0
            idx = layer.fields().indexFromName(field_name)
            
            for feat in layer.getFeatures():
                val = feat.attributes()[idx]
                if val is not None:
                    try:
                        total += float(val)
                        count += 1
                    except (ValueError, TypeError):
                        pass
            return f"Soma de {field_name}: {total:.4f} ({count} registros)"
        except Exception as e:
            return f"Erro ao somar atributo: {str(e)}"

    def sum_tubes(self) -> str:
        try:
            layer = self._get_active_layer()
            field_names = [f.name() for f in layer.fields()]
            if FIELD_DN not in field_names or FIELD_LENGTH not in field_names:
                return f"Campos {FIELD_DN} ou {FIELD_LENGTH} ausentes."
            
            idx_dn = layer.fields().indexFromName(FIELD_DN)
            idx_l = layer.fields().indexFromName(FIELD_LENGTH)
            
            sums: Dict[float, float] = {}
            for feat in layer.getFeatures():
                try:
                    dn_val = feat.attributes()[idx_dn]
                    l_val = feat.attributes()[idx_l]
                    
                    if dn_val is not None and l_val is not None:
                        dn = float(dn_val)
                        l = float(l_val)
                        sums[dn] = sums.get(dn, 0) + l
                except (ValueError, TypeError):
                    pass
            
            report = []
            for dn in sorted(sums.keys()):
                total_l = sums[dn]
                tubes = math.ceil(total_l / 6.0)
                report.append(f"DN {dn:g}: {total_l:.2f}m -> {tubes} tubos")
            
            return " | ".join(report) if report else "Nenhum dado válido."
        except Exception as e:
            return f"Erro ao calcular tubos: {str(e)}"

    def optimize_dn(self, limit_hf: float) -> str:
        try:
            layer = self.iface.activeLayer()
            if not layer:
                return "Nenhuma camada ativa."
            if QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.LineGeometry:
                return "Use em camada de linhas."

            required_fields = [FIELD_FLOW, FIELD_DN, FIELD_LENGTH]
            field_names = [f.name() for f in layer.fields()]
            missing = [f for f in required_fields if f not in field_names]
            if missing:
                return f"Campos obrigatórios ausentes: {', '.join(missing)}."
            
            idx_hf = self._ensure_field(layer, FIELD_HF, QVariant.Double)
            idx_dn = layer.fields().indexFromName(FIELD_DN)
            idx_v = layer.fields().indexFromName(FIELD_FLOW)
            idx_l = layer.fields().indexFromName(FIELD_LENGTH)

            selected_ids = layer.selectedFeatureIds()
            if selected_ids:
                features = layer.getFeatures(QgsFeatureRequest().setFilterFids(selected_ids))
                count_msg = f"Processando {len(selected_ids)} feições selecionadas."
            else:
                features = layer.getFeatures()
                count_msg = "Processando todas as feições."

            updated_count = 0
            errors = 0
            
            def calc_hf(v: float, dn: float, l: float) -> float:
                if v <= 0 or dn <= 0 or l <= 0: return 0.0
                q = v / 3600.0
                d = dn / 1000.0
                c = DEFAULT_HAZEN_C
                return 10.67 * l * (q ** 1.852) / ((c ** 1.852) * (d ** 4.87))

            with edit(layer):
                for feat in features:
                    try:
                        attrs = feat.attributes()
                        v = float(attrs[idx_v]) if attrs[idx_v] else 0.0
                        dn = float(attrs[idx_dn]) if attrs[idx_dn] else 0.0
                        l = float(attrs[idx_l]) if attrs[idx_l] else 0.0
                        
                        if v <= 0 or dn <= 0 or l <= 0:
                            continue

                        current_hf = calc_hf(v, dn, l)
                        changed = False
                        
                        # Optimization logic
                        while current_hf > limit_hf:
                            current_idx = -1
                            for i, val in enumerate(VALID_DNS):
                                if dn == val:
                                    current_idx = i
                                    break
                            
                            if current_idx == -1:
                                # Snap to nearest valid DN
                                next_dn = VALID_DNS[0]
                                for val in VALID_DNS:
                                    if val > dn:
                                        next_dn = val
                                        break
                                    if val == VALID_DNS[-1] and dn > val:
                                        next_dn = val
                                dn = next_dn
                            elif current_idx < len(VALID_DNS) - 1:
                                dn = VALID_DNS[current_idx + 1]
                            else:
                                # Max DN reached
                                break
                            
                            current_hf = calc_hf(v, dn, l)
                            changed = True
                        
                        # Only update if changed or if HF field needs update
                        old_hf = attrs[idx_hf]
                        if changed or (old_hf is None) or (abs(float(old_hf) - current_hf) > 0.001):
                            layer.changeAttributeValue(feat.id(), idx_dn, float(dn))
                            layer.changeAttributeValue(feat.id(), idx_hf, float(current_hf))
                            updated_count += 1
                            
                    except (ValueError, TypeError):
                        errors += 1

            return f"{count_msg} Otimização concluída. {updated_count} feições atualizadas."
        except Exception as e:
            return f"Erro na otimização: {str(e)}"
