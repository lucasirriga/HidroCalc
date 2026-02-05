from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, 
    QDoubleSpinBox, QDialogButtonBox, QLabel, QMessageBox, QPushButton,
    QProgressBar, QApplication
)
from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes

class AreaFlowDialog(QDialog):
    def __init__(self, logic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.setWindowTitle("Cálculo de Vazão e Área")
        self.resize(400, 250)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Inputs
        self.cb_polygon = QComboBox()
        self.cb_points = QComboBox()
        
        self.sb_flow = QDoubleSpinBox()
        self.sb_flow.setRange(0.0, 100000.0)
        self.sb_flow.setValue(50.0)
        self.sb_flow.setSuffix(" l/h")
        self.sb_flow.setDecimals(2)
        
        # Populate Layers
        self._populate_layers(self.cb_polygon, QgsWkbTypes.PolygonGeometry)
        self._populate_layers(self.cb_points, QgsWkbTypes.PointGeometry)
        
        form_layout.addRow("Camada de Polígonos (Setores):", self.cb_polygon)
        form_layout.addRow("Camada de Emissores (Pontos):", self.cb_points)
        form_layout.addRow("Vazão do Emissor:", self.sb_flow)
        
        layout.addLayout(form_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Ok).setText("Calcular")
        buttons.accepted.connect(self.run_process)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _populate_layers(self, combo, geom_type):
        combo.clear()
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                g_type = layer.geometryType()
                if g_type == geom_type:
                     combo.addItem(layer.name(), layer)
    
    def run_process(self):
        poly_layer = self.cb_polygon.currentData()
        pt_layer = self.cb_points.currentData()
        flow = self.sb_flow.value()
        
        if not poly_layer or not pt_layer:
            QMessageBox.warning(self, "Aviso", "Selecione as camadas corretas.")
            return
            
        # UI Feedback
        self.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        QApplication.processEvents()
        
        def update_progress(current, total):
            if total > 0:
                self.progress_bar.setValue(int((current / total) * 100))
            QApplication.processEvents()
        
        try:
            # Run logic
            result = self.logic.calculate_irrigation_by_points(poly_layer, pt_layer, flow, progress_callback=update_progress)
            
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Resultado", result)
            if "sucesso" in result.lower():
                self.accept()
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro no processamento: {e}")
            
        finally:
            self.setEnabled(True)
