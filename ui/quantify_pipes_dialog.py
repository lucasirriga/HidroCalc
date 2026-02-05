import math
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QComboBox, QPushButton, QHeaderView, QMessageBox
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsVectorLayer, QgsProject
from ..core.constants import FIELD_DN, FIELD_LENGTH

class QuantifyPipesDialog(QDialog):
    def __init__(self, iface, active_layer, part_manager, project_parts_manager, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.layer = active_layer
        self.part_manager = part_manager
        self.project_parts_manager = project_parts_manager
        
        self.setWindowTitle("Quantificar Tubulações")
        self.resize(800, 400)
        
        self.layout = QVBoxLayout(self)
        
        # Header Info
        self.info_label = QLabel(f"Camada Alvo: {self.layer.name()}")
        self.layout.addWidget(self.info_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Diâmetro (DN)", "Comprimento Total (m)", "Varas (6m)", "Selecionar Material (Catálogo)", "Preço Unit."])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("Adicionar ao Orçamento")
        self.btn_add.clicked.connect(self.add_to_budget)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_cancel)
        self.layout.addLayout(button_layout)
        
        self.data_map = {} # dn -> {total_length, bars, combos_parts}
        self.populate_table()
        
    def populate_table(self):
        # 1. Aggregate Data from Layer
        idx_dn = self.layer.fields().indexFromName(FIELD_DN)
        # Fallback fields if FIELD_DN ('Diametro') not found
        if idx_dn == -1:
            idx_dn = self.layer.fields().indexFromName('dn')
        
        if idx_dn == -1:
            QMessageBox.warning(self, "Erro", f"Campo de diâmetro ('{FIELD_DN}') não encontrado na camada.")
            return

        aggregated = {} # dn (float) -> length (float)
        
        for feat in self.layer.getFeatures():
            try:
                dn = feat.attributes()[idx_dn]
                if dn is None: continue
                dn = float(dn)
                
                # Check geometry length
                geom = feat.geometry()
                if not geom: continue
                l = geom.length()
                
                aggregated[dn] = aggregated.get(dn, 0.0) + l
            except:
                pass
                
        if not aggregated:
            QMessageBox.warning(self, "Aviso", "Nenhum tubo com diâmetro válido encontrado.")
            return

        # 2. Populate Table
        self.table.setRowCount(len(aggregated))
        all_parts = self.part_manager.get_parts()
        
        self.data_map = {}
        
        for row, (dn, length) in enumerate(sorted(aggregated.items())):
            bars = math.ceil(length / 6.0)
            
            # DN
            item_dn = QTableWidgetItem(f"{dn} mm")
            item_dn.setFlags(item_dn.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 0, item_dn)
            
            # Length
            item_len = QTableWidgetItem(f"{length:.2f}")
            item_len.setFlags(item_len.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 1, item_len)
            
            # Bars
            item_bars = QTableWidgetItem(str(bars))
            item_bars.setFlags(item_bars.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 2, item_bars)
            
            # Combo Parts
            combo = QComboBox()
            # Filter parts matching "DN {dn}" or "DN{dn}"
            matching_parts = []
            
            dn_str = str(int(dn)) if dn.is_integer() else str(dn)
            
            for p in all_parts:
                name_upper = p['name'].upper()
                # Simple heuristic: Look for "DN 50" or "DN50"
                # Also look for just the number if specific "Tubo 50mm"
                
                # Rigid logic: Must contain "DN" and the number
                if f"DN {dn_str}" in name_upper or f"DN{dn_str}" in name_upper or f" {dn_str}MM" in name_upper:
                    matching_parts.append(p)
            
            # Sort by name (usually groups PNs together if consistent naming)
            matching_parts.sort(key=lambda x: x['name'])
            
            combo.addItem("Selecione um material...", None)
            for p in matching_parts:
                combo.addItem(f"{p['name']} (R$ {p['cost']:.2f})", p)
            
            self.table.setCellWidget(row, 3, combo)
            
            # Price Column (Updates on change)
            item_price = QTableWidgetItem("-")
            item_price.setFlags(item_price.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 4, item_price)
            
            # Connect signal
            combo.currentIndexChanged.connect(lambda idx, r=row, c=combo: self.on_combo_changed(r, c))
            
            self.data_map[row] = {
                'dn': dn,
                'quantity': bars,
                'combo': combo
            }

    def on_combo_changed(self, row, combo):
        data = combo.currentData()
        item = self.table.item(row, 4)
        if data:
            item.setText(f"R$ {data['cost']:.2f}")
        else:
            item.setText("-")
            
    def add_to_budget(self):
        count = 0
        for row, info in self.data_map.items():
            combo = info['combo']
            part_data = combo.currentData()
            if part_data:
                qty = info['quantity']
                self.project_parts_manager.add_part(part_data, qty)
                count += 1
        
        if count > 0:
            QMessageBox.information(self, "Sucesso", f"{count} itens adicionados ao orçamento do projeto!")
            self.accept()
        else:
            QMessageBox.warning(self, "Aviso", "Nenhum material selecionado. Escolha os materiais na tabela.")

