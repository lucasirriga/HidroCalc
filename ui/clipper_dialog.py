from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox, QMessageBox,
    QFormLayout
)
from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes

class ClipperDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recortar Linhas por Polígonos")
        self.resize(400, 150)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Select Line Layer
        self.cmb_lines = QComboBox()
        self.cmb_polys = QComboBox()
        
        self._populate_layers()
        
        form_layout.addRow("Camada de Linhas (A ser cortada/atualizada):", self.cmb_lines)
        form_layout.addRow("Camada de Polígonos (Mascara):", self.cmb_polys)
        
        layout.addLayout(form_layout)
        
        # Warning Label
        lbl_info = QLabel("Atenção: A camada de linhas selecionada será modificada!\nLinhas fora dos polígonos serão excluídas.")
        lbl_info.setStyleSheet("color: red; font-style: italic;")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _populate_layers(self):
        project = QgsProject.instance()
        for layer in project.mapLayers().values():
            if layer.type() != QgsMapLayer.VectorLayer:
                continue
                
            if layer.geometryType() == QgsWkbTypes.LineGeometry:
                self.cmb_lines.addItem(layer.name(), layer.id())
            elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.cmb_polys.addItem(layer.name(), layer.id())
                
    def get_selected_layers(self):
        line_id = self.cmb_lines.currentData()
        poly_id = self.cmb_polys.currentData()
        
        if not line_id or not poly_id:
            return None, None
            
        project = QgsProject.instance()
        return project.mapLayer(line_id), project.mapLayer(poly_id)
