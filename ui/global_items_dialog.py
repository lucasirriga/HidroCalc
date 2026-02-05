from qgis.PyQt.QtWidgets import QTableWidgetItem
from qgis.PyQt.QtGui import QColor
from .base_dialogs import BaseGlobalDialog

class GlobalPartsDialog(BaseGlobalDialog):
    def __init__(self, part_manager, parent=None):
        super().__init__(part_manager, "Lista de Peças (Global)", ["Nome", "Custo (R$)", "Lucro (%)", "Valor (R$)"], parent)
        self.load_data()

    def load_data(self):
        self.table.blockSignals(True)
        parts = self.manager.get_parts()
        self.table.setRowCount(len(parts))
        
        for i, part in enumerate(parts):
            self.set_row_data(i, part)
        self.table.blockSignals(False)

    def set_row_data(self, row, part):
        cost = float(part['cost'])
        profit = float(part['profit_margin'])
        value = cost * (1 + profit / 100)

        # Name
        self.table.setItem(row, 0, QTableWidgetItem(str(part['name'])))
        
        # Cost
        item_cost = QTableWidgetItem(f"{cost:.2f}")
        self.table.setItem(row, 1, item_cost)
        
        # Profit
        item_profit = QTableWidgetItem(f"{profit:.2f}")
        self.table.setItem(row, 2, item_profit)
        
        # Value (Read-only/Calculated)
        item_value = QTableWidgetItem(f"{value:.2f}")
        item_value.setFlags(item_value.flags() ^ 16) # Make read-only
        item_value.setBackground(QColor("#f0f0f0"))
        self.table.setItem(row, 3, item_value)

    def on_item_changed(self, item):
        row = item.row()
        col = item.column()
        
        # If Value column changed, ignore (it's calculated)
        if col == 3:
            return

        self.table.blockSignals(True)
        try:
            name = self.table.item(row, 0).text()
            cost_text = self.table.item(row, 1).text().replace(',', '.')
            profit_text = self.table.item(row, 2).text().replace(',', '.')
            
            try:
                cost = float(cost_text)
                profit = float(profit_text)
                
                # Update Manager
                self.manager.update_part(row, name, cost, profit)
                
                # Recalculate Value
                value = cost * (1 + profit / 100)
                self.table.item(row, 3).setText(f"{value:.2f}")
                
            except ValueError:
                pass
                
        finally:
            self.table.blockSignals(False)

class GlobalServicesDialog(BaseGlobalDialog):
    def __init__(self, service_manager, parent=None):
        super().__init__(service_manager, "Lista de Serviços (Global)", ["Descrição", "Custo Unitário (R$)"], parent)
        self.load_data()

    def load_data(self):
        self.table.blockSignals(True)
        services = self.manager.get_services()
        self.table.setRowCount(len(services))
        
        for i, service in enumerate(services):
            self.table.setItem(i, 0, QTableWidgetItem(str(service['name'])))
            self.table.setItem(i, 1, QTableWidgetItem(f"{float(service['cost']):.2f}"))
        self.table.blockSignals(False)

    def on_item_changed(self, item):
        row = item.row()
        self.table.blockSignals(True)
        try:
            name = self.table.item(row, 0).text()
            cost_text = self.table.item(row, 1).text().replace(',', '.')
            
            try:
                cost = float(cost_text)
                self.manager.update_service(row, name, cost)
            except ValueError:
                pass
        finally:
            self.table.blockSignals(False)
