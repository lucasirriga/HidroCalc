from qgis.PyQt.QtWidgets import QTableWidgetItem, QPushButton, QMessageBox, QFileDialog
from qgis.PyQt.QtGui import QColor
from .base_dialogs import BaseProjectDialog

class ProjectPartsDialog(BaseProjectDialog):
    def __init__(self, project_parts_manager, global_part_manager, project_services_manager, parent=None):
        self.project_services_manager = project_services_manager # Needed for report
        super().__init__(project_parts_manager, global_part_manager, "Peças do Projeto", 
                         ["Nome", "Qtd", "Unit. (R$)", "Total (R$)", "Ações"], "Peça:", parent)
        
        # Add Report Button
        btn_report = QPushButton("Gerar Relatório PDF")
        btn_report.clicked.connect(self.generate_report)
        self.actions_layout.addWidget(btn_report)
        
        self.load_data()

    def _add_item_logic(self, item_data, qty):
        return self.project_manager.add_part(item_data, qty)

    def update_prices(self):
        global_parts = self.global_manager.get_parts()
        count = self.project_manager.update_prices_from_global(global_parts)
        
        if count > 0:
            self.load_data()
            QMessageBox.information(self, "Sucesso", f"{count} peças foram atualizadas com os preços atuais.")
        else:
            QMessageBox.information(self, "Info", "Todas as peças já estão com os preços atualizados.")

    def load_data(self):
        self.table.blockSignals(True)
        self.project_manager.update_paths()
        parts = self.project_manager.get_parts()
        self.table.setRowCount(len(parts))
        
        total_project = 0.0
        
        for i, part in enumerate(parts):
            qty = float(part['quantity'])
            cost = float(part['cost'])
            profit = float(part['profit_margin'])
            unit_value = cost * (1 + profit / 100)
            total_value = unit_value * qty
            total_project += total_value
            
            # Name (Read-only)
            item_name = QTableWidgetItem(str(part['name']))
            item_name.setFlags(item_name.flags() ^ 16)
            item_name.setBackground(QColor("#f0f0f0"))
            self.table.setItem(i, 0, item_name)
            
            # Qty (Editable)
            self.table.setItem(i, 1, QTableWidgetItem(f"{qty:.2f}"))
            
            # Unit Value (Editable)
            self.table.setItem(i, 2, QTableWidgetItem(f"{unit_value:.2f}"))
            
            # Total (Read-only)
            item_total = QTableWidgetItem(f"{total_value:.2f}")
            item_total.setFlags(item_total.flags() ^ 16)
            item_total.setBackground(QColor("#f0f0f0"))
            self.table.setItem(i, 3, item_total)
            
            # Delete Button
            btn_delete = QPushButton("Excluir")
            btn_delete.setStyleSheet("color: red;")
            btn_delete.clicked.connect(self.delete_item)
            self.table.setCellWidget(i, 4, btn_delete)

        self.lbl_total.setText(f"Total do Projeto: R$ {total_project:.2f}")
        self.table.blockSignals(False)

    def on_item_changed(self, item):
        row = item.row()
        col = item.column()
        
        if col not in [1, 2]:
            return

        self.table.blockSignals(True)
        try:
            text = item.text().replace(',', '.')
            value = float(text)
            
            if col == 1: # Quantity
                self.project_manager.update_part(row, quantity=value)
            elif col == 2: # Unit Price
                self.project_manager.update_part(row, unit_price=value)
            
            self.load_data()
            
        except ValueError:
            pass
        finally:
            self.table.blockSignals(False)

    def _remove_item_logic(self, row):
        self.project_manager.remove_part(row)

    def generate_report(self):
        parts = self.project_manager.get_parts()
        if not parts:
            QMessageBox.warning(self, "Aviso", "Não há peças no projeto para gerar relatório.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório", "", "HTML Files (*.html)"
        )
        
        if filename:
            if not filename.endswith('.html'):
                filename += '.html'
            
            # Import logic here to avoid circular imports or early init
            # We need to find where HydraulicsLogic is. It's in logic.py.
            # But logic.py imports QGIS stuff.
            # We can assume logic is available via import.
            from ..logic import HydraulicsLogic
            
            # Instantiate logic (passing None as iface since this method doesn't use it)
            logic = HydraulicsLogic(None)
            
            self.project_services_manager.update_paths()
            services = self.project_services_manager.get_services()
            
            result = logic.generate_project_parts_report(parts, services, filename)
            QMessageBox.information(self, "Relatório", result)


class ProjectServicesDialog(BaseProjectDialog):
    def __init__(self, project_services_manager, global_service_manager, parent=None):
        super().__init__(project_services_manager, global_service_manager, "Serviços do Projeto", 
                         ["Descrição", "Qtd", "Unit. (R$)", "Total (R$)", "Ações"], "Serviço:", parent)
        self.load_data()

    def _add_item_logic(self, item_data, qty):
        return self.project_manager.add_service(item_data, qty)

    def update_prices(self):
        global_services = self.global_manager.get_services()
        count = self.project_manager.update_prices_from_global(global_services)
        if count > 0:
            self.load_data()
            QMessageBox.information(self, "Sucesso", f"{count} serviços foram atualizados.")
        else:
            QMessageBox.information(self, "Info", "Todos os serviços já estão atualizados.")

    def load_data(self):
        self.table.blockSignals(True)
        self.project_manager.update_paths()
        services = self.project_manager.get_services()
        self.table.setRowCount(len(services))
        
        total_project = 0.0
        
        for i, service in enumerate(services):
            qty = float(service['quantity'])
            cost = float(service['cost'])
            total_value = cost * qty
            total_project += total_value
            
            # Name (Read-only)
            item_name = QTableWidgetItem(str(service['name']))
            item_name.setFlags(item_name.flags() ^ 16)
            item_name.setBackground(QColor("#f0f0f0"))
            self.table.setItem(i, 0, item_name)
            
            # Qty (Editable)
            self.table.setItem(i, 1, QTableWidgetItem(f"{qty:.2f}"))
            
            # Unit Value (Editable)
            self.table.setItem(i, 2, QTableWidgetItem(f"{cost:.2f}"))
            
            # Total (Read-only)
            item_total = QTableWidgetItem(f"{total_value:.2f}")
            item_total.setFlags(item_total.flags() ^ 16)
            item_total.setBackground(QColor("#f0f0f0"))
            self.table.setItem(i, 3, item_total)
            
            # Delete Button
            btn_delete = QPushButton("Excluir")
            btn_delete.setStyleSheet("color: red;")
            btn_delete.clicked.connect(self.delete_item)
            self.table.setCellWidget(i, 4, btn_delete)

        self.lbl_total.setText(f"Total de Serviços: R$ {total_project:.2f}")
        self.table.blockSignals(False)

    def on_item_changed(self, item):
        row = item.row()
        col = item.column()
        if col not in [1, 2]: return

        self.table.blockSignals(True)
        try:
            text = item.text().replace(',', '.')
            value = float(text)
            
            if col == 1: # Quantity
                self.project_manager.update_service(row, quantity=value)
            elif col == 2: # Unit Price
                self.project_manager.update_service(row, unit_price=value)
            
            self.load_data()
        except ValueError:
            pass
        finally:
            self.table.blockSignals(False)

    def _remove_item_logic(self, row):
        self.project_manager.remove_service(row)
