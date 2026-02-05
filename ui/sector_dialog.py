from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
    QDialogButtonBox, QMessageBox
)

class SectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Definir Setor")
        self.resize(300, 100)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.input_sector = QLineEdit()
        self.input_sector.setPlaceholderText("Ex: Setor A")
        
        form_layout.addRow("Nome do Setor:", self.input_sector)
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_sector_name(self):
        return self.input_sector.text().strip()

    def accept(self):
        if not self.get_sector_name():
            QMessageBox.warning(self, "Aviso", "Digite um nome para o setor.")
            return
        super().accept()
