from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QDoubleSpinBox, QDialogButtonBox, QMessageBox, QGroupBox, QStackedWidget, QWidget
)

class WaterSourceDialog(QDialog):
    def __init__(self, logic, layer, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.layer = layer
        self.setWindowTitle("Cadastro de Fonte de Água")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Common Fields
        self.input_name = QLineEdit()
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Selecione...", "Poço", "Reservatório", "Curso de Água"])
        self.combo_type.currentTextChanged.connect(self.on_type_changed)
        
        form_layout.addRow("Nome da Fonte:", self.input_name)
        form_layout.addRow("Tipo de Fonte:", self.combo_type)
        layout.addLayout(form_layout)
        
        # Specific Fields (Stacked or Grouped)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Page 0: Empty
        self.page_empty = QWidget()
        self.stack.addWidget(self.page_empty)
        
        # Page 1: Poço
        self.page_well = QWidget()
        l_well = QFormLayout(self.page_well)
        self.sb_nivel_est = self._make_spinbox()
        self.sb_nivel_din = self._make_spinbox()
        self.sb_vazao_well = self._make_spinbox()
        l_well.addRow("Nível Estático (m):", self.sb_nivel_est)
        l_well.addRow("Nível Dinâmico (m):", self.sb_nivel_din)
        l_well.addRow("Vazão (m³/h):", self.sb_vazao_well)
        self.stack.addWidget(self.page_well)
        
        # Page 2: Reservatório
        self.page_res = QWidget()
        l_res = QFormLayout(self.page_res)
        self.sb_cap_arm = self._make_spinbox()
        self.sb_cap_rec = self._make_spinbox()
        l_res.addRow("Capacidade Armazenamento (m³):", self.sb_cap_arm)
        l_res.addRow("Capacidade Recarga (m³/h):", self.sb_cap_rec)
        self.stack.addWidget(self.page_res)
        
        # Page 3: Curso de Água
        self.page_river = QWidget()
        l_river = QFormLayout(self.page_river)
        self.sb_cap_extr = self._make_spinbox()
        l_river.addRow("Capacidade de Extração (m³/h):", self.sb_cap_extr)
        self.stack.addWidget(self.page_river)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_data)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Load existing data if possible
        self.load_existing_data()

    def _make_spinbox(self):
        sb = QDoubleSpinBox()
        sb.setRange(0.0, 999999.0)
        sb.setDecimals(2)
        sb.setValue(0.0)
        return sb

    def on_type_changed(self, text):
        if text == "Poço":
            self.stack.setCurrentWidget(self.page_well)
        elif text == "Reservatório":
            self.stack.setCurrentWidget(self.page_res)
        elif text == "Curso de Água":
            self.stack.setCurrentWidget(self.page_river)
        else:
            self.stack.setCurrentWidget(self.page_empty)

    def load_existing_data(self):
        selection = self.layer.selectedFeatures()
        if not selection: return
        feat = selection[0]
        
        # Helper to safely get attr
        def get_val(fname):
            try:
                # Find field helper
                idx = self.layer.fields().indexFromName(fname)
                if idx != -1:
                    return feat[idx]
            except:
                pass
            return None

        # Load Name/Type
        name = get_val('NOME_FONTE')
        if name: self.input_name.setText(str(name))
        
        ftype = get_val('TIPO_FONTE')
        if ftype:
             idx = self.combo_type.findText(str(ftype))
             if idx != -1: self.combo_type.setCurrentIndex(idx)
        
        # Load Specifics
        def load_sb(sb, fname):
            val = get_val(fname)
            if val is not None:
                try: sb.setValue(float(val))
                except: pass
        
        load_sb(self.sb_nivel_est, 'NIVEL_EST')
        load_sb(self.sb_nivel_din, 'NIVEL_DIN')
        load_sb(self.sb_vazao_well, 'VAZAO_M3H')
        load_sb(self.sb_cap_arm, 'CAP_ARM')
        load_sb(self.sb_cap_rec, 'CAP_REC')
        load_sb(self.sb_cap_extr, 'CAP_EXTR')

    def save_data(self):
        name = self.input_name.text().strip()
        ftype = self.combo_type.currentText()
        
        if not name or ftype == "Selecione...":
            QMessageBox.warning(self, "Aviso", "Preencha Nome e Tipo.")
            return

        data = {
            'name': name,
            'type': ftype
        }
        
        if ftype == "Poço":
            data['nivel_est'] = self.sb_nivel_est.value()
            data['nivel_din'] = self.sb_nivel_din.value()
            data['vazao'] = self.sb_vazao_well.value()
            # Clear others? Usually good to clear if type changed
            # But the logic registers what we send.
            # Ideally verify if we need to nullify others.
            
        elif ftype == "Reservatório":
            data['cap_arm'] = self.sb_cap_arm.value()
            data['cap_rec'] = self.sb_cap_rec.value()
            
        elif ftype == "Curso de Água":
             data['cap_extr'] = self.sb_cap_extr.value()
             
        result = self.logic.register_water_source(self.layer, data)
        QMessageBox.information(self, "Resultado", result)
        if "sucesso" in result.lower():
            self.accept()
