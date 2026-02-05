import os
import json
from datetime import datetime
from qgis.PyQt.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox, QLabel, 
    QPushButton, QDialogButtonBox, QMessageBox, QTabWidget, QVBoxLayout, QWidget
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from qgis.core import QgsProject, QgsWkbTypes, QgsMapLayer, QgsField, edit
from qgis.PyQt.QtCore import QVariant

class ProjectInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Informações do Projeto")
        self.resize(500, 600)
        self.resize(600, 600)
        self.main_layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # --- Tab 1: Geral ---
        self.tab_general = QWidget()
        self.layout = QFormLayout(self.tab_general)
        self.tabs.addTab(self.tab_general, "Geral")
        
        # --- Basic Info ---
        self.txt_owner = QLineEdit()
        self.combo_power = QComboBox()
        self.combo_power.addItems(["Monofásico", "Bifásico", "Trifásico", "Diesel", "Solar"])
        self.combo_water = QComboBox()
        self.combo_water.addItems(["Rio", "Poço", "Represa", "Lago"])
        self.spin_sources = QSpinBox()
        self.spin_sources.setRange(0, 100)
        self.txt_location = QLineEdit()
        
        self.layout.addRow("<b>Dados Gerais</b>", QLabel(""))
        self.layout.addRow("Proprietário:", self.txt_owner)
        self.layout.addRow("Localidade:", self.txt_location)
        self.layout.addRow("Energia:", self.combo_power)
        self.layout.addRow("Fonte de Água:", self.combo_water)
        self.layout.addRow("Qtd. Fontes:", self.spin_sources)
        
        # --- Irrigation Sectors ---
        self.layout.addRow("<b>Cálculos de Setores</b>", QLabel(""))
        
        self.combo_layer = QComboBox()
        self.combo_layer.currentIndexChanged.connect(self.on_layer_changed)
        self.layout.addRow("Camada de Setores:", self.combo_layer)
        
        self.combo_emitter_field = QComboBox()
        self.layout.addRow("Campo de Emissores:", self.combo_emitter_field)
        
        self.txt_emitter_flow = QLineEdit()
        self.txt_emitter_flow.setPlaceholderText("L/h")
        self.layout.addRow("Vazão do Emissor (L/h):", self.txt_emitter_flow)
        
        self.spin_simultaneous = QSpinBox()
        self.spin_simultaneous.setRange(1, 100)
        self.spin_simultaneous.setValue(1)
        self.layout.addRow("Setores Simultâneos:", self.spin_simultaneous)
        
        self.txt_time_sector = QLineEdit()
        self.txt_time_sector.setPlaceholderText("Horas")
        self.layout.addRow("Tempo por Setor (h):", self.txt_time_sector)
        
        # --- Results ---
        self.layout.addRow("<b>Resultados</b>", QLabel(""))
        
        self.lbl_total_area = QLabel("-")
        self.layout.addRow("Área Total (ha):", self.lbl_total_area)
        
        self.lbl_total_sectors = QLabel("-")
        self.layout.addRow("Total de Setores:", self.lbl_total_sectors)
        
        self.lbl_operating_flow = QLabel("-")
        self.layout.addRow("Vazão de Funcionamento (m³/h):", self.lbl_operating_flow)
        
        self.lbl_total_time = QLabel("-")
        self.layout.addRow("Tempo Total (h):", self.lbl_total_time)
        
        self.lbl_date = QLabel(datetime.now().strftime("%d/%m/%Y"))
        self.layout.addRow("Data:", self.lbl_date)
        
        # Buttons
        btn_calc = QPushButton("Calcular")
        btn_calc.clicked.connect(self.calculate)
        self.layout.addRow(btn_calc)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        self.layout.addRow(buttons)
        
        # --- Tab 2: Dashboard ---
        self.tab_dashboard = QWidget()
        self.dash_layout = QVBoxLayout(self.tab_dashboard)
        self.tabs.addTab(self.tab_dashboard, "Análise de Custos")
        
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.dash_layout.addWidget(self.canvas)
        
        self.btn_refresh_dash = QPushButton("Atualizar Gráfico")
        self.btn_refresh_dash.clicked.connect(self.update_dashboard)
        self.dash_layout.addWidget(self.btn_refresh_dash)
        
        self.populate_layers()
        self.load_data()

    def save_and_accept(self):
        self.save_data()
        self.accept()

    def populate_layers(self):
        self.combo_layer.clear()
        self.combo_layer.addItem("Selecione...", None)
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.combo_layer.addItem(layer.name(), layer)

    def on_layer_changed(self):
        self.combo_emitter_field.clear()
        layer = self.combo_layer.currentData()
        if layer:
            for field in layer.fields():
                self.combo_emitter_field.addItem(field.name())

    def calculate(self):
        layer = self.combo_layer.currentData()
        if not layer:
            QMessageBox.warning(self, "Aviso", "Selecione uma camada de setores.")
            return
            
        emitter_field = self.combo_emitter_field.currentText()
        if not emitter_field:
             QMessageBox.warning(self, "Aviso", "Selecione o campo de emissores.")
             return

        try:
            q_emitter = float(self.txt_emitter_flow.text().replace(',', '.'))
            simultaneous = self.spin_simultaneous.value()
            time_sector = float(self.txt_time_sector.text().replace(',', '.'))
        except ValueError:
            QMessageBox.warning(self, "Erro", "Verifique os valores numéricos (Vazão, Tempo).")
            return

        total_area = 0.0
        sector_flows = []
        
        # Ensure output field for Sector Flow exists
        field_flow = "Q_Setor"
        if field_flow not in [f.name() for f in layer.fields()]:
            layer.dataProvider().addAttributes([QgsField(field_flow, QVariant.Double)])
            layer.updateFields()
        
        # Calculate
        with edit(layer):
            for feat in layer.getFeatures():
                # Area
                if feat.geometry():
                    total_area += feat.geometry().area() / 10000.0 # m2 to ha
                
                # Flow
                try:
                    n_emitters = float(feat[emitter_field])
                    q_sector = (n_emitters * q_emitter) / 1000.0 # m3/h
                    feat[field_flow] = q_sector
                    layer.updateFeature(feat)
                    sector_flows.append(q_sector)
                except:
                    pass
        
        total_sectors = len(sector_flows)
        if total_sectors > 0:
            avg_flow = sum(sector_flows) / total_sectors
            operating_flow = avg_flow * simultaneous
            total_time = (total_sectors / simultaneous) * time_sector
        else:
            operating_flow = 0
            total_time = 0
            
        # Update UI
        self.lbl_total_area.setText(f"{total_area:.2f}")
        self.lbl_total_sectors.setText(str(total_sectors))
        self.lbl_operating_flow.setText(f"{operating_flow:.2f}")
        self.lbl_total_time.setText(f"{total_time:.2f}")
        
        QMessageBox.information(self, "Sucesso", "Cálculos realizados e camada atualizada.")

    def get_project_file_path(self):
        project_path = QgsProject.instance().fileName()
        if not project_path:
            return None
        folder = os.path.dirname(project_path)
        return os.path.join(folder, "hidrocalc_data.json")

    def load_data(self):
        filepath = self.get_project_file_path()
        if not filepath or not os.path.exists(filepath):
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.txt_owner.setText(data.get("owner", ""))
            self.txt_location.setText(data.get("location", ""))
            
            idx = self.combo_power.findText(data.get("power", ""))
            if idx >= 0: self.combo_power.setCurrentIndex(idx)
            
            idx = self.combo_water.findText(data.get("water", ""))
            if idx >= 0: self.combo_water.setCurrentIndex(idx)
            
            self.spin_sources.setValue(data.get("sources", 0))
            
            # Restore calculation params
            self.txt_emitter_flow.setText(str(data.get("emitter_flow", "")))
            self.spin_simultaneous.setValue(data.get("simultaneous", 1))
            self.txt_time_sector.setText(str(data.get("time_sector", "")))
            
            # Restore Layer Selection (by name)
            layer_name = data.get("layer_name", "")
            idx = self.combo_layer.findText(layer_name)
            if idx >= 0:
                self.combo_layer.setCurrentIndex(idx)
                self.on_layer_changed()
                field_name = data.get("emitter_field", "")
                idx_f = self.combo_emitter_field.findText(field_name)
                if idx_f >= 0: self.combo_emitter_field.setCurrentIndex(idx_f)
                
            # Restore Results
            results = data.get("results", {})
            self.lbl_total_area.setText(str(results.get("total_area", "-")))
            self.lbl_total_sectors.setText(str(results.get("total_sectors", "-")))
            self.lbl_operating_flow.setText(str(results.get("operating_flow", "-")))
            self.lbl_total_time.setText(str(results.get("total_time", "-")))
            
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao carregar dados: {e}")

    def save_data(self):
        filepath = self.get_project_file_path()
        if not filepath:
            QMessageBox.warning(self, "Aviso", "Salve o projeto QGIS antes de salvar os dados.")
            return
            
        data = {
            "owner": self.txt_owner.text(),
            "location": self.txt_location.text(),
            "power": self.combo_power.currentText(),
            "water": self.combo_water.currentText(),
            "sources": self.spin_sources.value(),
            "layer_name": self.combo_layer.currentText(),
            "emitter_field": self.combo_emitter_field.currentText(),
            "emitter_flow": self.txt_emitter_flow.text(),
            "simultaneous": self.spin_simultaneous.value(),
            "time_sector": self.txt_time_sector.text(),
            "results": {
                "total_area": self.lbl_total_area.text(),
                "total_sectors": self.lbl_total_sectors.text(),
                "operating_flow": self.lbl_operating_flow.text(),
                "total_time": self.lbl_total_time.text(),
                "date": self.lbl_date.text()
            }
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao salvar dados: {e}")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao salvar dados: {e}")

    def update_dashboard(self):
        """Updates the cost analysis chart."""
        # Load parts and services from managers (mocked for now or read from files)
        # Ideally we should inject ProjectPartsManager and ProjectServicesManager
        # For this MVP, we will try to read from JSON if available or just show placeholder
        
        filepath = self.get_project_file_path()
        if not filepath or not os.path.exists(filepath):
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # We need cost data. If it's not in project_info, we can't plot.
            # Assuming 'results' might contain cost summary in future.
            # For now, let's plot dummy data or data if we had it.
            
            # Let's check if we can get data from managers.
            # Since we don't have managers here, we can't easily get live data.
            # We will plot a placeholder or simple data if available.
            
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # Example Data
            labels = ['Materiais', 'Serviços', 'Outros']
            sizes = [60, 30, 10] # Mock
            
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            ax.set_title("Distribuição Estimada de Custos")
            
            self.canvas.draw()
            
        except Exception as e:
            pass
