import os, math
from qgis.PyQt.QtWidgets import QAction, QInputDialog
from qgis.PyQt.QtGui import QIcon
from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QPushButton
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsField, edit,
    QgsProject, QgsUnitTypes,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsFeatureRequest, QgsWkbTypes, QgsSpatialIndex
)
from qgis.utils import iface

CAMPO_OUT = "L"        # comprimento (m)
CAMPO_AREA = "Area"    # área (ha)
CAMPO_CNT = "Aspersores"  # contagem de pontos
MENU_ROOT = "&Hidráulica"
HAZEN_C = 150.0

class CalcularComprimento:
    def __init__(self, iface_):
        self.iface = iface_
        self.action_toolbar = None; self.action_menu = None
        self.action_dn_toolbar = None; self.action_dn_menu = None
        self.action_v_toolbar = None; self.action_v_menu = None
        self.action_hf_toolbar = None; self.action_hf_menu = None
        self.action_area_toolbar = None; self.action_area_menu = None
        self.action_cnt_toolbar = None; self.action_cnt_menu = None
        self.action_area_total_toolbar = None; self.action_area_total_menu = None
        self.action_tubos_toolbar = None; self.action_tubos_menu = None
        self.action_somarL_toolbar = None; self.action_somarL_menu = None




    def initGui(self):
        base_dir = os.path.dirname(__file__)

        # 1) Comprimento (L)
        icon_L = os.path.join(base_dir, "icon_L.ico")
        self.action_toolbar = QAction(QIcon(icon_L), "", self.iface.mainWindow())
        self.action_toolbar.setToolTip("Calcular Comprimento (m)")
        self.action_toolbar.triggered.connect(self._executar_comprimento)
        self.iface.addToolBarIcon(self.action_toolbar)
        self.action_menu = QAction(QIcon(icon_L), "Calcular Comprimento (m)", self.iface.mainWindow())
        self.action_menu.triggered.connect(self._executar_comprimento)
        self.iface.addPluginToMenu(MENU_ROOT, self.action_menu)

        # 2) DN
        icon_DN = os.path.join(base_dir, "icon_DN.ico")
        self.action_dn_toolbar = QAction(QIcon(icon_DN), "", self.iface.mainWindow())
        self.action_dn_toolbar.setToolTip("Definir DN (seleção)")
        self.action_dn_toolbar.triggered.connect(self._definir_dn)
        self.iface.addToolBarIcon(self.action_dn_toolbar)
        self.action_dn_menu = QAction(QIcon(icon_DN), "Definir DN (seleção)", self.iface.mainWindow())
        self.action_dn_menu.triggered.connect(self._definir_dn)
        self.iface.addPluginToMenu(MENU_ROOT, self.action_dn_menu)

        # 3) V (m³/h)
        icon_V = os.path.join(base_dir, "icon_V.ico")
        self.action_v_toolbar = QAction(QIcon(icon_V), "", self.iface.mainWindow())
        self.action_v_toolbar.setToolTip("Definir Vazão (m³/h) em V (seleção)")
        self.action_v_toolbar.triggered.connect(self._definir_vazao)
        self.iface.addToolBarIcon(self.action_v_toolbar)
        self.action_v_menu = QAction(QIcon(icon_V), "Definir Vazão (m³/h) em V (seleção)", self.iface.mainWindow())
        self.action_v_menu.triggered.connect(self._definir_vazao)
        self.iface.addPluginToMenu(MENU_ROOT, self.action_v_menu)

        # 4) HF
        icon_HF = os.path.join(base_dir, "icon_HF.ico")
        self.action_hf_toolbar = QAction(QIcon(icon_HF), "", self.iface.mainWindow())
        self.action_hf_toolbar.setToolTip("Calcular HF (usa V, DN, L)")
        self.action_hf_toolbar.triggered.connect(self._calcular_hf)
        self.iface.addToolBarIcon(self.action_hf_toolbar)
        self.action_hf_menu = QAction(QIcon(icon_HF), "Calcular HF (V, DN, L)", self.iface.mainWindow())
        self.action_hf_menu.triggered.connect(self._calcular_hf)
        self.iface.addPluginToMenu(MENU_ROOT, self.action_hf_menu)

        # 5) Área (ha)
        icon_Area = os.path.join(base_dir, "icon_Area.ico")
        self.action_area_toolbar = QAction(QIcon(icon_Area), "", self.iface.mainWindow())
        self.action_area_toolbar.setToolTip("Calcular Área (ha)")
        self.action_area_toolbar.triggered.connect(self._calcular_area)
        self.iface.addToolBarIcon(self.action_area_toolbar)
        self.action_area_menu = QAction(QIcon(icon_Area), "Calcular Área (ha)", self.iface.mainWindow())
        self.action_area_menu.triggered.connect(self._calcular_area)
        self.iface.addPluginToMenu(MENU_ROOT, self.action_area_menu)

        # 6) Contar Aspersores (pontos em polígonos)
        icon_Cnt = os.path.join(base_dir, "icon_Count.ico")
        self.action_cnt_toolbar = QAction(QIcon(icon_Cnt), "", self.iface.mainWindow())
        self.action_cnt_toolbar.setToolTip("Contar pontos dentro de cada polígono")
        self.action_cnt_toolbar.triggered.connect(self._contar_pontos)
        self.iface.addToolBarIcon(self.action_cnt_toolbar)
        self.action_cnt_menu = QAction(QIcon(icon_Cnt), "Contar Aspersores (pontos em polígonos)", self.iface.mainWindow())
        self.action_cnt_menu.triggered.connect(self._contar_pontos)
        self.iface.addPluginToMenu(MENU_ROOT, self.action_cnt_menu)

        # 7) Somar Área (ha) na coluna 'Area'
        icon_AreaSum = os.path.join(base_dir, "icon_AreaSum.ico")  # opcional; use algum ícone seu
        self.action_area_total_toolbar = QAction(QIcon(icon_AreaSum), "", self.iface.mainWindow())
        self.action_area_total_toolbar.setToolTip("Somar Área total (ha) da coluna 'Area'")
        self.action_area_total_toolbar.triggered.connect(self._somar_area_total)
        self.iface.addToolBarIcon(self.action_area_total_toolbar)
        self.action_area_total_menu = QAction(QIcon(icon_AreaSum), "Somar Área total (ha) da coluna 'Area'", self.iface.mainWindow())
        self.action_area_total_menu.triggered.connect(self._somar_area_total)
        self.iface.addPluginToMenu(MENU_ROOT, self.action_area_total_menu)

        # 8) Somar L por DN e estimar tubos de 6 m
        icon_Tubos = os.path.join(base_dir, "icon_Tubos.ico")  # opcional
        self.action_tubos_toolbar = QAction(QIcon(icon_Tubos), "", self.iface.mainWindow())
        self.action_tubos_toolbar.setToolTip("Somar comprimentos por DN e calcular tubos de 6 m")
        self.action_tubos_toolbar.triggered.connect(self._somar_por_dn_tubos)
        self.iface.addToolBarIcon(self.action_tubos_toolbar)

        self.action_tubos_menu = QAction(QIcon(icon_Tubos), "Somar por DN → tubos de 6 m", self.iface.mainWindow())
        self.action_tubos_menu.triggered.connect(self._somar_por_dn_tubos)
        self.iface.addPluginToMenu(MENU_ROOT, self.action_tubos_menu)

        # 9) Somar total da coluna L
        icon_sumL = os.path.join(base_dir, "icon_SumL.ico")  # opcional
        self.action_somarL_toolbar = QAction(QIcon(icon_sumL), "", self.iface.mainWindow())
        self.action_somarL_toolbar.setToolTip("Somar total da coluna L (m)")
        self.action_somarL_toolbar.triggered.connect(self._somar_L_total)
        self.iface.addToolBarIcon(self.action_somarL_toolbar)

        self.action_somarL_menu = QAction(QIcon(icon_sumL), "Somar total da coluna L (m)", self.iface.mainWindow())
        self.action_somarL_menu.triggered.connect(self._somar_L_total)
        self.iface.addPluginToMenu(MENU_ROOT, self.action_somarL_menu)



    def unload(self):
        for a in (
            self.action_toolbar, self.action_menu,
            self.action_dn_toolbar, self.action_dn_menu,
            self.action_v_toolbar, self.action_v_menu,
            self.action_hf_toolbar, self.action_hf_menu,
            self.action_area_toolbar, self.action_area_menu,
            self.action_cnt_toolbar, self.action_cnt_menu,
            self.action_area_total_toolbar, self.action_area_total_menu,
            self.action_tubos_toolbar, self.action_tubos_menu,
            self.action_somarL_toolbar, self.action_somarL_menu,



        ):
            if not a: continue
            try: self.iface.removeToolBarIcon(a)
            except Exception: pass
            try: self.iface.removePluginMenu(MENU_ROOT, a)
            except Exception: pass

    # -------- 1) Comprimento --------
    def _executar_comprimento(self):
        layer = self.iface.activeLayer()
        if not layer:
            self.iface.messageBar().pushWarning("Calcular Comprimento (m)", "Nenhuma camada ativa."); return
        if QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.LineGeometry:
            self.iface.messageBar().pushWarning("Calcular Comprimento (m)", "Use em camada de linhas."); return

        layer_name = layer.name()
        nomes = [f.name() for f in layer.fields()]
        if CAMPO_OUT not in nomes:
            ok = layer.dataProvider().addAttributes([QgsField(CAMPO_OUT, QVariant.Double)])
            layer.updateFields()
            if not ok:
                self.iface.messageBar().pushCritical("Calcular Comprimento (m)", f"Falha ao criar campo '{CAMPO_OUT}'."); return

        project_crs = QgsProject.instance().crs()
        target_crs = project_crs if (project_crs.isValid() and project_crs.mapUnits() == QgsUnitTypes.DistanceMeters) \
            else QgsCoordinateReferenceSystem("EPSG:3857")
        need_transform = layer.crs().authid() != target_crs.authid()
        if need_transform:
            xform = QgsCoordinateTransform(layer.crs(), target_crs, QgsProject.instance())

        nulls = 0
        with edit(layer):
            for feat in layer.getFeatures():
                geom = feat.geometry()
                if not geom or geom.isEmpty(): nulls += 1; continue
                if need_transform: geom.transform(xform)
                feat[CAMPO_OUT] = float(geom.length())
                layer.updateFeature(feat)

        msg = f"Camada '{layer_name}' processada."
        msg += f" Geometrias vazias: {nulls}." if nulls else " Comprimento em metros calculado."
        (self.iface.messageBar().pushWarning if nulls else self.iface.messageBar().pushInfo)("Calcular Comprimento (m)", msg)

    # -------- 2) DN --------
    def _definir_dn(self):
        self._definir_valor_em_campo("DN", "Definir DN", "Valor para DN (mm):")

    # -------- 3) Vazão --------
    def _definir_vazao(self):
        self._definir_valor_em_campo("V", "Definir Vazão (m³/h)", "Vazão (m³/h):")

    # -------- utilitário DN/V --------
    def _definir_valor_em_campo(self, campo, titulo, prompt):
        layer = self.iface.activeLayer()
        if not layer:
            self.iface.messageBar().pushWarning(titulo, "Nenhuma camada ativa."); return

        sel_ids = layer.selectedFeatureIds()
        if not sel_ids:
            self.iface.messageBar().pushWarning(titulo, "Nenhuma feição selecionada."); return

        valor, ok = QInputDialog.getDouble(self.iface.mainWindow(), titulo, prompt, decimals=3)
        if not ok: return

        nomes = [f.name() for f in layer.fields()]
        if campo not in nomes:
            ok_add = layer.dataProvider().addAttributes([QgsField(campo, QVariant.Double)])
            layer.updateFields()
            if not ok_add:
                self.iface.messageBar().pushCritical(titulo, f"Falha ao criar campo '{campo}'."); return

        req = QgsFeatureRequest().setFilterFids(sel_ids)
        count = 0
        with edit(layer):
            for feat in layer.getFeatures(req):
                feat[campo] = float(valor); layer.updateFeature(feat); count += 1

        self.iface.messageBar().pushInfo(titulo, f"{count} feição(ões) atualizadas em '{layer.name()}' (campo {campo}).")

    # -------- 4) HF --------
    def _calcular_hf(self):
        layer = self.iface.activeLayer()
        if not layer:
            self.iface.messageBar().pushWarning("Calcular HF", "Nenhuma camada ativa."); return
        if QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.LineGeometry:
            self.iface.messageBar().pushWarning("Calcular HF", "Use em camada de linhas."); return

        nomes = [f.name() for f in layer.fields()]
        for c in ("V", "DN", CAMPO_OUT):
            if c not in nomes:
                self.iface.messageBar().pushCritical("Calcular HF", f"Campo obrigatório ausente: '{c}'."); return
        if "HF" not in nomes:
            ok_add = layer.dataProvider().addAttributes([QgsField("HF", QVariant.Double)])
            layer.updateFields()
            if not ok_add:
                self.iface.messageBar().pushCritical("Calcular HF", "Falha ao criar campo 'HF'."); return

        invalid = 0; updated = 0
        with edit(layer):
            for feat in layer.getFeatures():
                try:
                    V_m3h = float(feat["V"]); DN_mm = float(feat["DN"]); L_m = float(feat[CAMPO_OUT])
                except Exception:
                    invalid += 1; continue
                if any(x is None or x <= 0 for x in (V_m3h, DN_mm, L_m)): invalid += 1; continue

                Q = V_m3h / 3600.0; D = DN_mm / 1000.0; C = HAZEN_C
                try:
                    hf = 10.67 * L_m * (Q ** 1.852) / ((C ** 1.852) * (D ** 4.87))
                    feat["HF"] = float(hf); layer.updateFeature(feat); updated += 1
                except Exception:
                    invalid += 1

        if updated and not invalid:
            self.iface.messageBar().pushInfo("Calcular HF", f"HF calculado em {updated} feições.")
        elif updated and invalid:
            self.iface.messageBar().pushWarning("Calcular HF", f"HF calculado em {updated}. Registros inválidos: {invalid}.")
        else:
            self.iface.messageBar().pushCritical("Calcular HF", "Nenhuma feição válida para cálculo.")

    # -------- 5) Área (ha) --------
    def _calcular_area(self):
        layer = self.iface.activeLayer()
        if not layer:
            self.iface.messageBar().pushWarning("Calcular Área (ha)", "Nenhuma camada ativa."); return
        if QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.PolygonGeometry:
            self.iface.messageBar().pushWarning("Calcular Área (ha)", "Use em camada de polígonos."); return

        nomes = [f.name() for f in layer.fields()]
        if CAMPO_AREA not in nomes:
            ok = layer.dataProvider().addAttributes([QgsField(CAMPO_AREA, QVariant.Double)])
            layer.updateFields()
            if not ok:
                self.iface.messageBar().pushCritical("Calcular Área (ha)", f"Falha ao criar campo '{CAMPO_AREA}'."); return

        project_crs = QgsProject.instance().crs()
        target_crs = project_crs if (project_crs.isValid() and project_crs.mapUnits() == QgsUnitTypes.DistanceMeters) \
            else QgsCoordinateReferenceSystem("EPSG:3857")
        need_transform = layer.crs().authid() != target_crs.authid()
        if need_transform:
            xform = QgsCoordinateTransform(layer.crs(), target_crs, QgsProject.instance())

        nulls = 0; updated = 0
        with edit(layer):
            for feat in layer.getFeatures():
                geom = feat.geometry()
                if not geom or geom.isEmpty(): nulls += 1; continue
                if need_transform: geom.transform(xform)
                area_m2 = float(geom.area())
                feat[CAMPO_AREA] = area_m2 / 10000.0
                layer.updateFeature(feat); updated += 1

        if updated and not nulls:
            self.iface.messageBar().pushInfo("Calcular Área (ha)", f"Área calculada em {updated} feições.")
        elif updated and nulls:
            self.iface.messageBar().pushWarning("Calcular Área (ha)", f"Área calculada em {updated}. Geometrias vazias: {nulls}.")
        else:
            self.iface.messageBar().pushCritical("Calcular Área (ha)", "Nenhuma feição válida para cálculo.")

    # -------- 6) Contar Aspersores (pontos em polígonos) --------
    def _contar_pontos(self):
        poly_layer = self.iface.activeLayer()
        if not poly_layer:
            self.iface.messageBar().pushWarning("Contar Aspersores", "Nenhuma camada ativa."); return
        if QgsWkbTypes.geometryType(poly_layer.wkbType()) != QgsWkbTypes.PolygonGeometry:
            self.iface.messageBar().pushWarning("Contar Aspersores", "Ative a camada de polígonos."); return

        # escolher camada de pontos
        pts_layers = [lyr for lyr in QgsProject.instance().mapLayers().values()
                      if hasattr(lyr, "geometryType") and QgsWkbTypes.geometryType(lyr.wkbType()) == QgsWkbTypes.PointGeometry]
        if not pts_layers:
            self.iface.messageBar().pushWarning("Contar Aspersores", "Nenhuma camada de pontos no projeto."); return

        if len(pts_layers) == 1:
            pts_layer = pts_layers[0]
        else:
            nomes = [lyr.name() for lyr in pts_layers]
            nome, ok = QInputDialog.getItem(self.iface.mainWindow(), "Contar Aspersores",
                                            "Selecione a camada de pontos:", nomes, 0, False)
            if not ok: return
            pts_layer = next(lyr for lyr in pts_layers if lyr.name() == nome)

        # campo de saída
        nomes_fields = [f.name() for f in poly_layer.fields()]
        if CAMPO_CNT not in nomes_fields:
            ok_add = poly_layer.dataProvider().addAttributes([QgsField(CAMPO_CNT, QVariant.Int)])
            poly_layer.updateFields()
            if not ok_add:
                self.iface.messageBar().pushCritical("Contar Aspersores", f"Falha ao criar campo '{CAMPO_CNT}'."); return

        # index espacial dos pontos
        idx = QgsSpatialIndex(pts_layer.getFeatures())

        # preparar transformação CRS: polígonos -> pontos
        need_transform = poly_layer.crs().authid() != pts_layer.crs().authid()
        if need_transform:
            xform_poly_to_pts = QgsCoordinateTransform(poly_layer.crs(), pts_layer.crs(), QgsProject.instance())

        updated = 0
        with edit(poly_layer):
            for pfeat in poly_layer.getFeatures():
                geom_poly = pfeat.geometry()
                if not geom_poly or geom_poly.isEmpty():
                    pfeat[CAMPO_CNT] = 0; poly_layer.updateFeature(pfeat); updated += 1; continue

                # transformar polígono para o CRS dos pontos (se necessário)
                g = geom_poly if not need_transform else QgsGeometry(geom_poly)
                if need_transform:
                    g.transform(xform_poly_to_pts)

                # consulta por bbox no índice
                cand_ids = idx.intersects(g.boundingBox())

                # contar candidatos realmente dentro (inclui borda)
                count = 0
                if cand_ids:
                    req = QgsFeatureRequest().setFilterFids(cand_ids)
                    for pt in pts_layer.getFeatures(req):
                        ptg = pt.geometry()
                        # ponto no interior ou na borda
                        if g.contains(ptg) or g.touches(ptg) or g.intersects(ptg):
                            count += 1

                pfeat[CAMPO_CNT] = int(count)
                poly_layer.updateFeature(pfeat); updated += 1

        self.iface.messageBar().pushInfo("Contar Aspersores", f"Contagem concluída. {updated} polígonos atualizados.")

    # -------- 7) Somar Área total (ha) na coluna 'Area' --------
    def _somar_area_total(self):
        layer = self.iface.activeLayer()
        titulo = "Somar Área total (ha)"
        if not layer:
            self.iface.messageBar().pushWarning(titulo, "Nenhuma camada ativa."); return

        # checar existência do campo
        nomes = [f.name() for f in layer.fields()]
        if CAMPO_AREA not in nomes:
            self.iface.messageBar().pushCritical(titulo, f"Campo '{CAMPO_AREA}' não existe na camada '{layer.name()}'."); return

        idx = layer.fields().indexOf(CAMPO_AREA)
        total = 0.0; n_valid = 0; n_invalid = 0

        for feat in layer.getFeatures():
            val = feat.attribute(idx)
            try:
                if val is None: n_invalid += 1; continue
                v = float(val)
                total += v
                n_valid += 1
            except Exception:
                n_invalid += 1

        msg = f"Soma em '{CAMPO_AREA}': {total:.4f} ha. Registros válidos: {n_valid}."
        if n_invalid:
            msg += f" Inválidos/ausentes: {n_invalid}."
            self.iface.messageBar().pushWarning(titulo, msg)
        else:
            self.iface.messageBar().pushInfo(titulo, msg)

    # -------- 8) Somar L por DN e estimar tubos de 6 m --------
    def _somar_por_dn_tubos(self):
        # Requer imports no topo:
        # from qgis.core import Qgis
        # from qgis.PyQt.QtWidgets import QPushButton
        titulo = "Tubos por DN (6 m)"
        layer = self.iface.activeLayer()
        if not layer:
            self.iface.messageBar().pushWarning(titulo, "Nenhuma camada ativa."); return

        nomes = [f.name() for f in layer.fields()]
        if "DN" not in nomes:
            self.iface.messageBar().pushCritical(titulo, "Campo 'DN' ausente."); return
        if CAMPO_OUT not in nomes:
            self.iface.messageBar().pushCritical(titulo, f"Campo '{CAMPO_OUT}' ausente."); return

        idx_dn = layer.fields().indexOf("DN")
        idx_l  = layer.fields().indexOf(CAMPO_OUT)

        soma_por_dn = {}   # dn -> soma de L (m)
        inval = 0
        for f in layer.getFeatures():
            dn = f.attribute(idx_dn)
            l  = f.attribute(idx_l)
            try:
                if dn is None or l is None: inval += 1; continue
                dn_num = float(dn)
                l_m = float(l)
                if dn_num <= 0 or l_m < 0: inval += 1; continue
                soma_por_dn[dn_num] = soma_por_dn.get(dn_num, 0.0) + l_m
            except Exception:
                inval += 1

        if not soma_por_dn:
            self.iface.messageBar().pushCritical(titulo, "Nenhum registro válido."); return

        linhas = []
        for dn_num in sorted(soma_por_dn.keys()):
            soma_m = soma_por_dn[dn_num]
            tubos_exato = soma_m / 6.0
            tubos_qtd = math.ceil(tubos_exato)
            dn_txt = f"{int(dn_num)}" if float(dn_num).is_integer() else f"{dn_num:g}"
            linhas.append(f"DN {dn_txt}: {soma_m:.2f} m → {tubos_exato:.2f} tubos (~{tubos_qtd} un.)")

        msg = " | ".join(linhas)
        if inval:
            msg += f" | Inválidos/ausentes: {inval}"

        # mensagem persistente com botão Fechar
        self.iface.messageBar().clearWidgets()
        w = self.iface.messageBar().createMessage(titulo, msg)
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.iface.messageBar().clearWidgets)
        w.layout().addWidget(btn_close)
        self.iface.messageBar().pushWidget(w, Qgis.Warning if inval else Qgis.Info)

    # -------- 9) Somar total da coluna L --------
    # Requer no topo:
    # from qgis.core import Qgis
    # from qgis.PyQt.QtWidgets import QPushButton, QApplication

    def _somar_L_total(self):
        titulo = "Soma total de L (m)"
        layer = self.iface.activeLayer()
        if not layer:
            self.iface.messageBar().pushWarning(titulo, "Nenhuma camada ativa."); return

        nomes = [f.name() for f in layer.fields()]
        if CAMPO_OUT not in nomes:
            self.iface.messageBar().pushCritical(titulo, f"Campo '{CAMPO_OUT}' ausente."); return

        idx_l = layer.fields().indexOf(CAMPO_OUT)

        total = 0.0; n_valid = 0; n_invalid = 0
        for f in layer.getFeatures():
            val = f.attribute(idx_l)
            try:
                if val is None: n_invalid += 1; continue
                v = float(val)
                total += v; n_valid += 1
            except Exception:
                n_invalid += 1

        msg_lines = [f"Total L: {total:.2f} m", f"Registros válidos: {n_valid}"]
        if n_invalid:
            msg_lines.append(f"Inválidos/ausentes: {n_invalid}")

        plain = "\n".join(msg_lines)
        html = "<br>".join(msg_lines)

        # mensagem persistente
        self.iface.messageBar().clearWidgets()
        w = self.iface.messageBar().createMessage(titulo, html)

        btn_copy = QPushButton("Copiar")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(plain))
        w.layout().addWidget(btn_copy)

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.iface.messageBar().clearWidgets)
        w.layout().addWidget(btn_close)

        self.iface.messageBar().pushWidget(w, Qgis.Warning if n_invalid else Qgis.Info)



# def classFactory(iface): return CalcularComprimento(iface)
