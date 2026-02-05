import os
import json
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QMessageBox
from qgis.core import QgsProject

class TermsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Termos de Serviço")
        self.resize(600, 500)
        self.layout = QVBoxLayout(self)
        
        self.text_edit = QTextEdit()
        self.layout.addWidget(self.text_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        
        self.load_terms()

    def save_and_accept(self):
        self.save_terms()
        self.accept()

    def get_project_file_path(self):
        project_path = QgsProject.instance().fileName()
        if not project_path:
            return None
        folder = os.path.dirname(project_path)
        return os.path.join(folder, "hidrocalc_data.json")

    def load_terms(self):
        filepath = self.get_project_file_path()
        if not filepath or not os.path.exists(filepath):
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.text_edit.setPlainText(data.get("terms", ""))
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao carregar termos: {e}")

    def save_terms(self):
        filepath = self.get_project_file_path()
        if not filepath:
            QMessageBox.warning(self, "Aviso", "Salve o projeto QGIS antes de salvar os termos.")
            return

        data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                pass
        
        data["terms"] = self.text_edit.toPlainText()
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao salvar termos: {e}")
