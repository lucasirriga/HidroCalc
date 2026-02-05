from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QDialogButtonBox, 
    QHeaderView, QHBoxLayout, QComboBox, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QWidget
)
from qgis.PyQt.QtGui import QColor

class BaseGlobalDialog(QDialog):
    """Diálogo base para itens globais (Peças/Serviços)."""
    def __init__(self, manager, title, headers, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle(title)
        self.resize(700, 400)
        self.layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemChanged.connect(self.on_item_changed)
        
        self.layout.addWidget(self.table)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        
    def load_data(self):
        raise NotImplementedError
        
    def on_item_changed(self, item):
        raise NotImplementedError

class BaseProjectDialog(QDialog):
    """Diálogo base para itens do projeto (Peças/Serviços do Projeto)."""
    def __init__(self, project_manager, global_manager, title, headers, item_label="Item:", parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.global_manager = global_manager
        self.setWindowTitle(title)
        self.resize(800, 500)
        self.layout = QVBoxLayout(self)
        
        # --- Seção Adicionar Item ---
        add_layout = QHBoxLayout()
        
        # Campo de Busca
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar...")
        self.txt_search.textChanged.connect(self.filter_items)
        add_layout.addWidget(self.txt_search, 1) # Stretch factor 1
        
        self.combo_items = QComboBox()
        # Definir itens visíveis máximos para acionar barra de rolagem
        self.combo_items.setMaxVisibleItems(20)
        
        self.all_items = [] # Armazena todos os itens para filtragem
        self.refresh_combo_items()
        
        add_layout.addWidget(QLabel(item_label))
        add_layout.addWidget(self.combo_items, 2) # Stretch factor 2 para ser maior que a busca
        
        self.spin_qty = QLineEdit()
        self.spin_qty.setPlaceholderText("Qtd")
        self.spin_qty.setFixedWidth(80)
        add_layout.addWidget(QLabel("Qtd:"))
        add_layout.addWidget(self.spin_qty)
        
        btn_add = QPushButton("Adicionar")
        btn_add.clicked.connect(self.add_item_to_project)
        add_layout.addWidget(btn_add)
        
        self.layout.addLayout(add_layout)
        
        # --- Seção Ações ---
        self.actions_layout = QHBoxLayout()
        
        btn_update_prices = QPushButton("Atualizar Preços")
        btn_update_prices.clicked.connect(self.update_prices)
        self.actions_layout.addWidget(btn_update_prices)
        
        # Subclasses podem adicionar mais botões ao self.actions_layout
        
        self.actions_layout.addStretch()
        self.layout.addLayout(self.actions_layout)
        
        # --- Seção Tabela ---
        self.table = QTableWidget()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemChanged.connect(self.on_item_changed)
        self.layout.addWidget(self.table)
        
        # --- Rodapé ---
        self.lbl_total = QLabel("Total: R$ 0.00")
        self.lbl_total.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        self.layout.addWidget(self.lbl_total)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        
    def refresh_combo_items(self):
        self.combo_items.clear()
        items = self.global_manager.get_parts() if hasattr(self.global_manager, 'get_parts') else self.global_manager.get_services()
        
        # Ordenar itens alfabeticamente por nome
        self.all_items = sorted(items, key=lambda x: x['name'])
        
        self.filter_items("")

    def filter_items(self, text):
        self.combo_items.clear()
        search_text = text.lower()
        
        for item in self.all_items:
            if search_text in item['name'].lower():
                self.combo_items.addItem(item['name'], item)

    def add_item_to_project(self):
        index = self.combo_items.currentIndex()
        if index < 0:
            return
            
        item_data = self.combo_items.itemData(index)
        qty_text = self.spin_qty.text().replace(',', '.')
        
        try:
            qty = float(qty_text)
            if qty <= 0:
                raise ValueError
            
            if self._add_item_logic(item_data, qty):
                self.load_data()
                self.spin_qty.clear()
            else:
                QMessageBox.warning(self, "Aviso", "Salve o projeto QGIS antes de adicionar itens.")
                
        except ValueError:
            QMessageBox.warning(self, "Erro", "Quantidade inválida.")

    def _add_item_logic(self, item_data, qty):
        # A ser implementado por subclasses para chamar método específico do gerenciador
        raise NotImplementedError

    def update_prices(self):
        # A ser implementado por subclasses
        raise NotImplementedError

    def load_data(self):
        # A ser implementado por subclasses
        raise NotImplementedError

    def on_item_changed(self, item):
        # A ser implementado por subclasses
        raise NotImplementedError

    def delete_item(self):
        button = self.sender()
        if button:
            index = self.table.indexAt(button.pos())
            if index.isValid():
                row = index.row()
                item_name = self.table.item(row, 0).text()
                
                confirm = QMessageBox.question(
                    self, 
                    "Confirmar Exclusão", 
                    f"Tem certeza que deseja remover '{item_name}' do projeto?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if confirm == QMessageBox.Yes:
                    self._remove_item_logic(row)
                    self.load_data()

    def _remove_item_logic(self, row):
        raise NotImplementedError
