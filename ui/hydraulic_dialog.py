import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDoubleSpinBox, QPushButton, QProgressBar, QMessageBox, QGroupBox, QFormLayout,
    QTabWidget, QWidget, QSpinBox, QCheckBox, QApplication
)
from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsSpatialIndex
from qgis.PyQt.QtCore import QVariant
from ..core.network import HydraulicNetwork
from ..core.network_builder import NetworkBuilder
from ..core.solver import HydraulicSolver
from ..core.layout_generator import LayoutGenerator

class HydraulicDesignDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Dimensionamento e Layout Hidráulico")
        self.resize(600, 700)
        
        self.layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # --- Tab 1: Configuração (Camadas) ---
        self.tab_config = QWidget()
        self.init_tab_config()
        self.tabs.addTab(self.tab_config, "1. Configuração")
        
        # --- Tab 2: Layout ---
        self.tab_layout = QWidget()
        self.init_tab_layout()
        self.tabs.addTab(self.tab_layout, "2. Layout")
        
        # --- Tab 3: Dimensionamento ---
        self.tab_sizing = QWidget()
        self.init_tab_sizing()
        self.tabs.addTab(self.tab_sizing, "3. Dimensionamento")
        
        # --- Footer ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        self.layout.addWidget(self.lbl_status)
        
    def init_tab_config(self):
        layout = QVBoxLayout(self.tab_config)
        
        self.group_layers = QGroupBox("Seleção de Camadas")
        self.form_layers = QFormLayout()
        
        self.cb_area = self._create_layer_combo(QgsWkbTypes.PolygonGeometry) # Area Total
        self.cb_emitters = self._create_layer_combo(QgsWkbTypes.PointGeometry) # Keep emitters for now as it is output of step 1
        self.cb_source = self._create_layer_combo(QgsWkbTypes.PointGeometry) # Water Source
        
        self.form_layers.addRow("Área Total (Para Geração):", self.cb_area)
        self.form_layers.addRow("Emissores (Gerados):", self.cb_emitters)
        self.form_layers.addRow("Fonte de Água:", self.cb_source)
        
        self.group_layers.setLayout(self.form_layers)
        layout.addWidget(self.group_layers)
        layout.addStretch()

    def init_tab_layout(self):
        layout = QVBoxLayout(self.tab_layout)
        
        # Step 1: Emitters Generation
        gb_emitters = QGroupBox("1. Geração de Emissores (Global)")
        form_emit = QFormLayout()
        
        self.spin_lat_spacing = QDoubleSpinBox()
        self.spin_lat_spacing.setValue(10.0)
        form_emit.addRow("Espaçamento entre Linhas (m):", self.spin_lat_spacing)
        
        self.spin_emit_spacing = QDoubleSpinBox()
        self.spin_emit_spacing.setValue(1.0)
        form_emit.addRow("Espaçamento entre Emissores (m):", self.spin_emit_spacing)
        
        self.spin_angle = QDoubleSpinBox()
        self.spin_angle.setRange(0, 360)
        form_emit.addRow("Ângulo das Linhas (graus):", self.spin_angle)
        
        self.cb_pattern = QComboBox()
        self.cb_pattern.addItems(["Retangular", "Triangular"])
        form_emit.addRow("Padrão:", self.cb_pattern)
        
        self.chk_auto_hoses = QCheckBox("Gerar mangueiras automaticamente")
        self.chk_auto_hoses.setChecked(True)
        form_emit.addRow(self.chk_auto_hoses)
        
        btn_gen_emitters = QPushButton("Gerar Emissores")
        btn_gen_emitters.clicked.connect(self.run_generate_emitters)
        
        gb_emitters.setLayout(form_emit)
        layout.addWidget(gb_emitters)
        layout.addWidget(btn_gen_emitters)
        
        # Step 2: Hoses Generation (Manual)
        gb_hoses = QGroupBox("2. Geração de Mangueiras")
        layout_hoses = QVBoxLayout()
        btn_gen_hoses = QPushButton("Gerar Mangueiras (Manual)")
        btn_gen_hoses.clicked.connect(self.run_generate_hoses)
        layout_hoses.addWidget(btn_gen_hoses)
        gb_hoses.setLayout(layout_hoses)
        
        layout.addWidget(gb_hoses)
        layout.addStretch()

    def run_generate_emitters(self):
        area_layer = self.cb_area.currentData()
        if not area_layer:
            QMessageBox.warning(self, "Aviso", "Selecione a camada de Área Total na aba Configuração.")
            return

        gen = LayoutGenerator()
        gen.lateral_spacing = self.spin_lat_spacing.value()
        gen.emitter_spacing = self.spin_emit_spacing.value()
        gen.lateral_angle = self.spin_angle.value()
        gen.emitter_pattern = self.cb_pattern.currentText().lower()
        
        self.lbl_status.setText("Gerando emissores...")
        
        all_emitters = []
        for feat in area_layer.getFeatures():
            if feat.geometry():
                emits = gen.generate_global_emitters(feat.geometry())
                all_emitters.extend(emits)
                
        # Create Layer
        crs = area_layer.crs().authid()
        emit_layer = QgsVectorLayer(f"Point?crs={crs}", "Emissores Gerados", "memory")
        prov = emit_layer.dataProvider()
        feats = [QgsFeature() for _ in all_emitters]
        for i, f in enumerate(feats):
            f.setGeometry(all_emitters[i])
        prov.addFeatures(feats)
        emit_layer.updateExtents()
        QgsProject.instance().addMapLayer(emit_layer)
        
        # Auto-select in combo
        self.cb_emitters.addItem(emit_layer.name(), emit_layer)
        self.cb_emitters.setCurrentIndex(self.cb_emitters.count() - 1)
        
        self.lbl_status.setText("Emissores gerados!")
        
        # Auto Generate Hoses if checked
        if self.chk_auto_hoses.isChecked():
            self.run_generate_hoses()
        else:
            QMessageBox.information(self, "Sucesso", f"{len(all_emitters)} emissores gerados.")

    def run_generate_hoses(self):
        emit_layer = self.cb_emitters.currentData()
        if not emit_layer:
            QMessageBox.warning(self, "Aviso", "Selecione a camada de Emissores.")
            return
            
        from ..core.network_generator import NetworkGenerator
        net_gen = NetworkGenerator()
        net_gen.lateral_angle = self.spin_angle.value()
        
        self.lbl_status.setText("Gerando mangueiras...")
        
        # Collect all geometries
        emitters = []
        for feat in emit_layer.getFeatures():
            if feat.geometry():
                emitters.append(feat.geometry())
                
        hoses = net_gen.generate_hoses(emitters)
        
        if hoses:
            crs = emit_layer.crs().authid()
            self._create_layer_from_geoms(hoses, "Mangueiras Geradas", crs)
            self.lbl_status.setText("Mangueiras geradas!")
            QMessageBox.information(self, "Sucesso", f"{len(hoses)} mangueiras geradas.")
        else:
            self.lbl_status.setText("Nenhuma mangueira gerada.")



    def _create_layer_from_geoms(self, geoms, name, crs_authid):
        layer = QgsVectorLayer(f"LineString?crs={crs_authid}", name, "memory")
        prov = layer.dataProvider()
        feats = [QgsFeature() for _ in geoms]
        for i, f in enumerate(feats):
            f.setGeometry(geoms[i])
        prov.addFeatures(feats)
        layer.updateExtents()
        QgsProject.instance().addMapLayer(layer)

    def _create_layer_from_points(self, points, name, crs_authid):
        layer = QgsVectorLayer(f"Point?crs={crs_authid}", name, "memory")
        prov = layer.dataProvider()
        feats = []
        for pt in points:
            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPointXY(pt))
            feats.append(f)
        prov.addFeatures(feats)
        layer.updateExtents()
        QgsProject.instance().addMapLayer(layer)

    def init_tab_sizing(self):
        layout = QVBoxLayout(self.tab_sizing)
        
        gb_params = QGroupBox("Parâmetros de Dimensionamento")
        form = QFormLayout()
        
        self.spin_max_velocity = QDoubleSpinBox()
        self.spin_max_velocity.setRange(0.1, 5.0)
        self.spin_max_velocity.setValue(1.5)
        self.spin_max_velocity.setSuffix(" m/s")
        form.addRow("Velocidade Máxima:", self.spin_max_velocity)
        
        self.spin_simultaneous_sectors = QSpinBox()
        self.spin_simultaneous_sectors.setRange(1, 100)
        self.spin_simultaneous_sectors.setValue(1)
        form.addRow("Setores Simultâneos:", self.spin_simultaneous_sectors)
        
        gb_params.setLayout(form)
        layout.addWidget(gb_params)
        
        btn_run = QPushButton("Gerar Rede e Dimensionar")
        btn_run.clicked.connect(self.run_full_sizing)
        layout.addWidget(btn_run)
        
        layout.addStretch()

    def _create_layer_combo(self, geometry_type):
        cb = QComboBox()
        cb.addItem("Selecione...", None)
        
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer and \
               QgsWkbTypes.geometryType(layer.wkbType()) == geometry_type:
                cb.addItem(layer.name(), layer)
        return cb

    def run_full_sizing(self):
        # 1. Validate Inputs
        emit_layer = self.cb_emitters.currentData()
        source_layer = self.cb_source.currentData()
        
        # We need sectors layer. Since it's generated in memory, we might need to find it or store it.
        # Let's look for "Setores Gerados" in project or store in self.
        sectors_layer = None
        for l in QgsProject.instance().mapLayers().values():
            if l.name().startswith("Setores Gerados"):
                sectors_layer = l
                break
        
        if not emit_layer or not source_layer or not sectors_layer:
             QMessageBox.warning(self, "Aviso", "Certifique-se de ter Emissores, Fonte e Setores gerados.")
             return
             
        self.lbl_status.setText("Iniciando dimensionamento...")
        self.progress_bar.setValue(0)
        
        try:
            # 2. Generate Network Geometry
            from ..core.network_generator import NetworkGenerator
            net_gen = NetworkGenerator()
            net_gen.lateral_angle = self.spin_angle.value()
            
            # Calculate Max Hose Length (needed for splitting)
            # Re-calculate or store? Let's re-calculate to be safe
            gen_layout = LayoutGenerator()
            gen_layout.hose_diameter = self.spin_hose_diameter.value()
            gen_layout.emitter_flow = self.spin_emitter_flow_sect.value()
            gen_layout.service_pressure = self.spin_service_pressure.value()
            gen_layout.emitter_spacing = self.spin_emitter_spacing_sect.value()
            max_var_percent = self.spin_pressure_variation.value()
            n_max = gen_layout.calculate_max_emitters_per_hose(max_var_percent)
            max_hose_length = n_max * gen_layout.emitter_spacing
            
            all_hoses = []
            all_laterals = []
            all_collectors = []
            valves = []
            all_junctions = []
            
            # Spatial Index for emitters
            idx = QgsSpatialIndex(emit_layer.getFeatures())
            # Get Boundary Geometry (Moved up for sector network generation)
            area_layer = self.cb_area.currentData()
            boundary_geom = None
            if area_layer:
                boundary_geom = QgsGeometry.fromWkt("POLYGON EMPTY")
                features = area_layer.selectedFeatures() if area_layer.selectedFeatureCount() > 0 else area_layer.getFeatures()
                for f in features:
                    if f.geometry():
                        if boundary_geom.isEmpty():
                            boundary_geom = QgsGeometry(f.geometry())
                        else:
                            boundary_geom = boundary_geom.combine(f.geometry())

            total_sectors = sectors_layer.featureCount()
            processed = 0
            for feat in sectors_layer.getFeatures():
                if not feat.geometry(): continue
                
                # Find emitters in this sector
                ids = idx.intersects(feat.geometry().boundingBox())
                sector_emitters = []
                for fid in ids:
                    e_feat = emit_layer.getFeature(fid)
                    if feat.geometry().contains(e_feat.geometry()):
                        sector_emitters.append(e_feat.geometry())
                
                hoses, lats, cols, valve_pos, junctions = net_gen.generate_sector_network(sector_emitters, feat.id(), max_hose_length, boundary_geom)
                
                all_hoses.extend(hoses)
                all_laterals.extend(lats)
                all_collectors.extend(cols)
                if valve_pos:
                    valves.append(valve_pos)
                if junctions:
                    all_junctions.extend(junctions)
                
                processed += 1
                self.progress_bar.setValue(int((processed / total_sectors) * 40))
                QApplication.processEvents()
                
            # Generate Main Line
            self.lbl_status.setText("Gerando linha principal...")
            
            source_feat = next(source_layer.getFeatures())
            source_pt = source_feat.geometry().asPoint()
            main_lines = net_gen.generate_main_line(valves, source_pt, boundary_geom)
            
            self.progress_bar.setValue(50)
            
            # 3. Build Hydraulic Network
            self.lbl_status.setText("Construindo modelo hidráulico...")
            network = HydraulicNetwork()
            builder = NetworkBuilder(network)
            
            # We need to pass layers or geometries to builder.
            # Builder expects layers currently.
            # Let's create temporary memory layers for the builder
            
            crs = emit_layer.crs().authid()
            
            def create_mem_layer(geoms, name):
                l = QgsVectorLayer(f"LineString?crs={crs}", name, "memory")
                pr = l.dataProvider()
                feats = [QgsFeature() for _ in geoms]
                for i, f in enumerate(feats):
                    f.setGeometry(geoms[i])
                pr.addFeatures(feats)
                l.updateExtents()
                return l
                
            def create_point_layer(pts, name):
                l = QgsVectorLayer(f"Point?crs={crs}", name, "memory")
                pr = l.dataProvider()
                feats = []
                for pt in pts:
                    f = QgsFeature()
                    f.setGeometry(QgsGeometry.fromPointXY(pt))
                    feats.append(f)
                pr.addFeatures(feats)
                l.updateExtents()
                return l

            l_hoses = create_mem_layer(all_hoses, "temp_hoses")
            l_laterals = create_mem_layer(all_laterals, "temp_laterals")
            l_collectors = create_mem_layer(all_collectors, "temp_collectors")
            l_main = create_mem_layer(main_lines, "temp_main")
            l_valves = create_point_layer(valves, "temp_valves")
            l_source = create_point_layer([source_pt], "temp_source")
            l_junctions = create_point_layer(all_junctions, "temp_junctions")
            
            # We need to map these to the builder's expected input dict
            # Builder expects: 'hoses', 'laterals', 'derivations' (collectors), 'main', 'valves', 'source'
            # Note: 'laterals' in builder usually means the pipe feeding hoses. 
            # 'derivations' means the pipe feeding laterals.
            # Our naming: 
            # Hoses -> Hoses
            # Laterals (Manifolds) -> Laterals
            # Collectors (Derivations) -> Derivations
            
            layers_map = {
                'hoses': l_hoses,
                'laterals': l_laterals,
                'derivations': l_collectors,
                'main': l_main,
                'valves': l_valves,
                'source': l_source,
                'junctions': l_junctions, # New layer for explicit connections
                'emitters': emit_layer # Needed for demand? Or builder uses hoses?
            }
            # Builder might need update if it relies on specific attributes or topology
            # Assuming builder uses spatial connectivity.
            
            builder.build(layers_map)
            
            self.progress_bar.setValue(70)
            
            # 4. Solve
            self.lbl_status.setText("Calculando hidráulica...")
            solver = HydraulicSolver(network)
            solver.max_velocity = self.spin_max_velocity.value()
            solver.simultaneous_sectors = self.spin_simultaneous_sectors.value()
            solver.emitter_flow = self.spin_emitter_flow_sect.value()
            
            # We need to set base demand for valves (sectors)
            # The builder might not know the demand of each valve if it just sees points.
            # We need to assign demand to valve nodes.
            # Each valve corresponds to a sector.
            # Sector Flow = Target Flow (approx) or calculated from emitters.
            # Let's assume Target Flow from UI for all sectors for simplicity, 
            # or calculate from emitters connected to that valve.
            # Since we built the network, the solver accumulates flow from emitters up to valves.
            # IF the builder connected emitters to hoses, hoses to laterals, etc.
            # But we didn't pass emitters to `create_mem_layer` for hoses.
            # The builder `build` method usually connects things spatially.
            # If we pass `emitters` layer, it should work.
            
            solver.solve()
            
            self.progress_bar.setValue(90)
            self.lbl_status.setText("Gerando resultados...")
            
            # 5. Create Result Layers
            # We want to show the sized pipes.
            
            res_layer = QgsVectorLayer(f"LineString?crs={crs}", "Rede Dimensionada", "memory")
            pr = res_layer.dataProvider()
            pr.addAttributes([
                QgsField("Tipo", QVariant.String),
                QgsField("DN", QVariant.Double),
                QgsField("Vazao_m3h", QVariant.Double),
                QgsField("HF_m", QVariant.Double),
                QgsField("Velocidade", QVariant.Double),
                QgsField("Comprimento", QVariant.Double)
            ])
            res_layer.updateFields()
            
            feats = []
            for link in network.links.values():
                feat = QgsFeature()
                feat.setGeometry(link.geometry)
                feat.setAttributes([
                    link.type,
                    link.diameter,
                    link.flow,
                    link.head_loss,
                    link.velocity,
                    link.length
                ])
                feats.append(feat)
            
            pr.addFeatures(feats)
            res_layer.updateExtents()
            QgsProject.instance().addMapLayer(res_layer)
            
            # Add Valves Layer
            v_layer = QgsVectorLayer(f"Point?crs={crs}", "Válvulas", "memory")
            pr_v = v_layer.dataProvider()
            pr_v.addAttributes([QgsField("Pressao_mca", QVariant.Double)])
            v_layer.updateFields()
            v_feats = []
            for node in network.nodes.values():
                if node.type == 'valve': # Assuming builder tags them
                    f = QgsFeature()
                    f.setGeometry(QgsGeometry.fromPointXY(node.point))
                    f.setAttributes([node.pressure])
                    v_feats.append(f)
            pr_v.addFeatures(v_feats)
            v_layer.updateExtents()
            QgsProject.instance().addMapLayer(v_layer)
            
            self.progress_bar.setValue(100)
            self.lbl_status.setText("Concluído!")
            QMessageBox.information(self, "Sucesso", "Rede gerada e dimensionada com sucesso!")
            
        except Exception as e:
            self.progress_bar.setValue(0)
            self.lbl_status.setText("Erro.")
            QMessageBox.critical(self, "Erro", f"Falha no dimensionamento: {str(e)}")
            import traceback
            traceback.print_exc()
