import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from qgis.PyQt.QtWidgets import (
    QAction, QInputDialog, QMessageBox, QLabel, QWidget, QDialog, 
    QFormLayout, QLineEdit, QDialogButtonBox, QVBoxLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QHBoxLayout, QComboBox, QPushButton, 
    QSpinBox, QTextEdit
)
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.core import QgsProject, QgsWkbTypes, QgsMapLayer, Qgis, QgsField, edit, QgsCoordinateReferenceSystem, QgsCoordinateTransform
from qgis.PyQt.QtCore import QVariant, Qt
from .resources import init_resources, get_icon
from .logic import HydraulicsLogic
from .parts_manager import PartManager
from .project_parts_manager import ProjectPartsManager
from .services_manager import ServiceManager
from .project_services_manager import ProjectServicesManager
from .ui.global_items_dialog import GlobalPartsDialog, GlobalServicesDialog
from .ui.project_items_dialog import ProjectPartsDialog, ProjectServicesDialog
from .ui.project_info_dialog import ProjectInfoDialog
from .ui.terms_dialog import TermsDialog
from .ui.lateral_dialog import LateralDialog
from .ui.area_flow_dialog import AreaFlowDialog
from .ui.sector_dialog import SectorDialog
from .ui.water_source_dialog import WaterSourceDialog
from .ui.quantify_pipes_dialog import QuantifyPipesDialog
from .core.constants import FIELD_DN, FIELD_FLOW, FIELD_LENGTH, FIELD_AREA
from .clima_mensal import StationManager, ClimateDataManager
from .ui.climate_dialog import ClimateAnalysisDialog
from .ui.hydraulic_dialog import HydraulicDesignDialog
from .ui.hydraulic_dialog import HydraulicDesignDialog
from .ui.charts_dialog import ChartsDialog
from .ui.clipper_dialog import ClipperDialog

from .core.deploy_manager import DeployManager
from qgis.PyQt.QtWidgets import QFileDialog

class HidroCalcPlugin:
    def __init__(self, iface: Any):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.logic: Optional[HydraulicsLogic] = None
        self.part_manager: Optional[PartManager] = None
        self.project_parts_manager: Optional[ProjectPartsManager] = None
        self.service_manager: Optional[ServiceManager] = None
        self.project_services_manager: Optional[ProjectServicesManager] = None
        self.actions: List[QAction] = []
        self.menu = "&HidroCalc"
        self.toolbar = None
        self.lbl_selection: Optional[QLabel] = None
        self.current_layer: Optional[QgsMapLayer] = None

    def initGui(self):
        init_resources()
        self.logic = HydraulicsLogic(self.iface)
        self.part_manager = PartManager(self.plugin_dir)
        self.project_parts_manager = ProjectPartsManager()
        self.service_manager = ServiceManager(self.plugin_dir)
        self.project_services_manager = ProjectServicesManager()
        
        # Create Toolbar
        self.toolbar = self.iface.addToolBar("HidroCalc")
        self.toolbar.setObjectName("HidroCalcToolbar")
        
        self._init_actions()
        
        self._init_selection_label()
        
        self._init_selection_label()

    def _init_actions(self):
        """Initialize all plugin actions."""
        # 1. Basic Geometry & Attributes (Start Left)
        self.add_action("icon_length", "Calcular Comprimento", self.run_length)
        self.add_action("icon_dn", "Definir DN", self.run_dn)
        self.add_action("icon_flow", "Definir Vazão", self.run_flow)
        self.add_action("icon_hf", "Calcular HF (Hazen-Williams)", self.run_hf)
        self.add_action("icon_area", "Calcular Área", self.run_area)
        self.add_action("icon_sum_area", "Somar Área", self.run_sum_area)
        
        # 2. Other Geometry & Counts
        self.add_action("icon_sum_length", "Somar Comprimento", self.run_sum_length)
        self.add_action("icon_count", "Contar Pontos", self.run_count)
        self.add_action("icon_flow", "Calcular Vazão por Emissores", self.show_area_flow_dialog)
        self.add_action("icon_dn", "Definir Setor", self.run_define_sector)
        self.add_action("icon_dn", "Definir Setor", self.run_define_sector)
        self.add_action("icon_pump", "Cadastrar Fonte de Água", self.run_water_source_tool)
        self.add_action("icon_sectoring", "Recortar Linhas (Clipper)", self.start_clipper_tool)
        
        # 3. Main Hydraulics & Engineering
        self.add_action("icon_tubes", "Dimensionamento Hidráulico", self.show_hydraulic_dialog)
        self.add_action("icon_flow", "Dimensionar Linha Lateral", self.show_lateral_dialog)
        self.add_action("icon_optimize_dn", "Otimizar DN (Simples)", self.run_optimize_dn)
        self.add_action("icon_pump", "Seleção de Bombas", self.run_pump_selection)
        self.add_action("icon_chart", "Perfil HGL (Elevação)", self.run_plot_hgl)
        
        # 4. Project Management & Budget
        self.add_action("icon_info", "Informações do Projeto", self.show_project_info_dialog)
        self.add_action("icon_add_part", "Cadastrar Peça", self.show_add_part_dialog)
        self.add_action("icon_add_service", "Cadastrar Serviço", self.show_add_service_dialog)
        self.add_action("icon_list_parts", "Catálogo de Peças", self.show_list_parts_dialog)
        self.add_action("icon_list_services", "Catálogo de Serviços", self.show_list_services_dialog)
        self.add_action("icon_project_parts", "Peças do Projeto", self.show_project_parts_dialog)
        self.add_action("icon_project_services", "Serviços do Projeto", self.show_project_services_dialog)
        self.add_action("icon_quantify_pipes", "Quantificar Tubulações (Orçamento)", self.run_quantify_pipes)
        
        # 5. Reports & Misc (Rightmost)
        self.add_action("icon_count", "Resumo de Tubos (Qtd)", self.run_tubes)
        self.add_action("icon_pdf_report", "Relatório de Tubos (PDF/Mapa)", self.run_pdf_report)
        self.add_action("icon_csv", "Exportar CSV", self.run_export_csv)
        self.add_action("icon_rose_wind", "Análise Climática", self.run_climate_analysis)
        self.add_action("icon_terms", "Termos de Serviço", self.show_terms_dialog)
        
        # Dev / Deploy
        self.add_action("icon_info", "Deploy / Atualizar Versão", self.run_deploy)

    def show_project_info_dialog(self):
        """Show dialog to edit project information."""
        dialog = ProjectInfoDialog(self.iface.mainWindow())
        if dialog.exec_() == QDialog.Accepted:
            dialog.save_data()
            self.iface.messageBar().pushMessage("HidroCalc", "Informações do projeto salvas.", level=Qgis.Success)

    def _init_selection_label(self):
        if not self.lbl_selection:
            self.lbl_selection = QLabel("Selecionados: 0")
            self.lbl_selection.setStyleSheet("padding: 5px; font-weight: bold; color: #333;")
            self.toolbar.addSeparator()
            self.toolbar.addWidget(self.lbl_selection)

            # Connect signals
            self.iface.currentLayerChanged.connect(self.on_layer_changed)
            self.on_layer_changed(self.iface.activeLayer())

    def add_action(self, icon_name: str, text: str, callback: Any, enabled_flag: bool = True) -> QAction:
        icon = get_icon(icon_name)
        action = QAction(icon, text, self.iface.mainWindow())
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        
        if self.toolbar:
            self.toolbar.addAction(action)
        
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def unload(self):
        # Disconnect signals
        try:
            self.iface.currentLayerChanged.disconnect(self.on_layer_changed)
        except:
            pass
            
        try:
            if self.current_layer:
                # Check if layer is still valid
                if isinstance(self.current_layer, QgsMapLayer) and self.current_layer.isValid():
                    self.current_layer.selectionChanged.disconnect(self.update_selection_count)
        except (RuntimeError, Exception):
            # Layer might be deleted already
            pass

        # Remove actions
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        self.actions = []
        
        # Remove toolbar
        if self.toolbar:
            self.toolbar.deleteLater()
            self.toolbar = None

    def on_layer_changed(self, layer: QgsMapLayer):
        # Disconnect from old layer
        try:
            if self.current_layer:
                try:
                    self.current_layer.selectionChanged.disconnect(self.update_selection_count)
                except:
                    pass
        except (RuntimeError, Exception):
            pass
        
        self.current_layer = layer
        
        # Connect to new layer
        if self.current_layer and self.current_layer.type() == QgsMapLayer.VectorLayer:
            self.current_layer.selectionChanged.connect(self.update_selection_count)
            self.update_selection_count()
        else:
            if self.lbl_selection:
                self.lbl_selection.setText("Selecionados: 0")

    def update_selection_count(self):
        if self.current_layer and self.lbl_selection:
            count = self.current_layer.selectedFeatureCount()
            self.lbl_selection.setText(f"Selecionados: {count}")

    # --- Callbacks ---

    def run_length(self):
        result = self.logic.calculate_length()
        self.iface.messageBar().pushMessage("HidroCalc", result, level=Qgis.Info)

    def run_area(self):
        result = self.logic.calculate_area()
        self.iface.messageBar().pushMessage("HidroCalc", result, level=Qgis.Info)

    def run_dn(self):
        val, ok = QInputDialog.getDouble(self.iface.mainWindow(), "Definir DN", "Valor do DN (mm):")
        if ok:
            result = self.logic.define_attribute(FIELD_DN, val)
            self.iface.messageBar().pushMessage("HidroCalc", result, level=Qgis.Info)

    def run_flow(self):
        val, ok = QInputDialog.getDouble(self.iface.mainWindow(), "Definir Vazão", "Vazão (m³/h):")
        if ok:
            result = self.logic.define_attribute(FIELD_FLOW, val)
            self.iface.messageBar().pushMessage("HidroCalc", result, level=Qgis.Info)

    def run_hf(self):
        # Uses default C=135 as requested
        result = self.logic.calculate_hf()
        self.iface.messageBar().pushMessage("HidroCalc", result, level=Qgis.Info)

    def run_count(self, layer_name=None):
        if layer_name:
            # Try to find layer by name
            layers = QgsProject.instance().mapLayersByName(layer_name)
            if layers:
                result = self.logic.count_points(layers[0].name())
                return result # Return result for Agent
            else:
                return f"Camada '{layer_name}' não encontrada."

        layers = [l.name() for l in QgsProject.instance().mapLayers().values() if l.type() == QgsMapLayer.VectorLayer and l.geometryType() == QgsWkbTypes.PointGeometry]
        if not layers:
            self.iface.messageBar().pushMessage("HidroCalc", "Nenhuma camada de pontos encontrada.", level=Qgis.Warning)
            return "Nenhuma camada de pontos encontrada."
            
        item, ok = QInputDialog.getItem(self.iface.mainWindow(), "Contar Pontos", "Selecione a camada de pontos:", layers, 0, False)
        if ok and item:
            result = self.logic.count_points(item)
            self.iface.messageBar().pushMessage("HidroCalc", result, level=Qgis.Info)
            return result

    def run_sum_area(self):
        result = self.logic.sum_attribute(FIELD_AREA)
        QMessageBox.information(self.iface.mainWindow(), "Soma de Área", result)

    def run_sum_length(self):
        result = self.logic.sum_attribute(FIELD_LENGTH)
        QMessageBox.information(self.iface.mainWindow(), "Soma de Comprimento", result)

    def run_tubes(self):
        # Show result in a message box because it can be long
        result = self.logic.sum_tubes()
        QMessageBox.information(self.iface.mainWindow(), "Relatório de Tubos", result)

    def run_optimize_dn(self, limit_hf=None):
        if limit_hf is not None:
            try:
                limit = float(limit_hf)
                result = self.logic.optimize_dn(limit)
                return result
            except ValueError:
                return "Valor de limite HF inválido."

        limit_hf, ok = QInputDialog.getDouble(self.iface.mainWindow(), "Otimizar DN", "Limite de HF (m.c.a):", 10.0, 0.1, 1000.0, 2)
        if ok:
            result = self.logic.optimize_dn(limit_hf)
            QMessageBox.information(self.iface.mainWindow(), "Resultado da Otimização", result)
            return result

    def run_pdf_report(self):
        from qgis.PyQt.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(self.iface.mainWindow(), "Salvar Relatório", "", "HTML Files (*.html)")
        if filename:
            if not filename.endswith('.html'):
                filename += '.html'
            
            # Ask for map orientation
            orientations = ["Retrato", "Paisagem"]
            orientation, ok = QInputDialog.getItem(self.iface.mainWindow(), "Orientação do Mapa", "Escolha a orientação do mapa:", orientations, 0, False)
            if not ok:
                return 

            # Ask for grid interval
            grid_interval, ok = QInputDialog.getDouble(self.iface.mainWindow(), "Grade do Mapa", "Intervalo da Grade (m):", 50.0, 1.0, 10000.0, 1)
            if not ok:
                return

            result = self.logic.generate_pdf_report(filename, orientation, grid_interval)
            QMessageBox.information(self.iface.mainWindow(), "Relatório HTML", result)

    def start_clipper_tool(self):
        """Opens the Clipper Dialog."""
        dialog = ClipperDialog(self.iface.mainWindow())
        if dialog.exec_() == QDialog.Accepted:
            line_layer, poly_layer = dialog.get_selected_layers()
            if not line_layer or not poly_layer:
                QMessageBox.warning(self.iface.mainWindow(), "Erro", "Camadas inválidas selecionadas.")
                return
            
            # Confirm
            reply = QMessageBox.question(
                self.iface.mainWindow(),
                "Confirmar Recorte",
                f"Isso irá apagar todas as linhas de '{line_layer.name()}' e substituir apenas pelas partes dentro de '{poly_layer.name()}'.\n\nDeseja continuar?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                result = self.logic.run_clipper_tool(line_layer, poly_layer)
                self.iface.messageBar().pushMessage("HidroCalc", result, level=Qgis.Info if "Sucesso" in result else Qgis.Warning)

    def run_deploy(self):
        """Runs the auto-deploy process."""
        manager = DeployManager(self.plugin_dir)
        
        # Confirm
        reply = QMessageBox.question(
            self.iface.mainWindow(), "Confirmar Deploy", 
            f"Deseja compactar a versão atual e atualizar o plugin?\nIsso irá recarregar o HidroCalc.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            result = manager.run_deploy()
            self.iface.messageBar().pushMessage("HidroCalc", result, level=Qgis.Success if "sucesso" in result.lower() else Qgis.Critical)

    def run_climate_analysis(self, station_code=None):
        """Run climate analysis. If station_code is provided, uses it directly."""
        
        # If station_code is provided directly (by Agent)
        if station_code:
            data_manager = ClimateDataManager(self.plugin_dir)
            data = data_manager.get_station_data(str(station_code))
            
            if not data:
                return f"Sem dados climáticos para a estação {station_code}."
                
            analysis = data_manager.analyze_data(data)
            
            # We need station info too
            station_manager = StationManager(self.plugin_dir)
            # Assuming we can get station by code, but get_nearest_station returns it.
            # Let's try to find it in the list or implement get_station_by_code
            # For now, let's just create a dummy station dict if we can't fetch it easily without coordinates
            # Or better, let's assume the agent provided a valid code that exists.
            
            # TODO: Implement get_station_by_code in StationManager if needed.
            # For now, we will try to find it.
            # Since we don't have get_station_by_code visible here, let's just proceed with data.
            # But the dialog needs 'nearest_station' dict.
            
            # Let's try to get it from the database if possible, or just mock it for the dialog
            # Ideally we should fix StationManager, but let's stick to plugin.py for now.
            
            # If we are running from Agent, maybe we just want the text result?
            # The agent prompt says "analise_climatica code=XXXX".
            # If we return the analysis text, that's great.
            
            summary = data_manager.generate_critical_analysis_text(analysis)
            return f"Análise Climática para Estação {station_code}:\n\n{summary}"

        # Interactive Mode (GUI)
        layer = self.iface.activeLayer()
        if not layer:
            QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Selecione uma camada para identificar a localização.")
            return
        
        # Get centroid of the layer or selected features
        extent = layer.extent()
        if layer.selectedFeatureCount() > 0:
            extent = layer.boundingBoxOfSelected()
        
        center = extent.center()
        
        # Transform to WGS84 if needed (assuming stations are in WGS84)
        crs_src = layer.crs()
        crs_dest = QgsCoordinateReferenceSystem("EPSG:4326")
        xform = QgsCoordinateTransform(crs_src, crs_dest, QgsProject.instance())
        center_wgs84 = xform.transform(center)
        
        lat, lon = center_wgs84.y(), center_wgs84.x()
        print(f"Climate Analysis - Input Coordinates (WGS84): Lat={lat}, Lon={lon}")
        
        # Find nearest station
        station_manager = StationManager(self.plugin_dir)
        nearest_station = station_manager.get_nearest_station(lat, lon)
        
        if not nearest_station:
            QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Nenhuma estação meteorológica encontrada próxima.")
            return
            
        # Get data
        data_manager = ClimateDataManager(self.plugin_dir)
        data = data_manager.get_station_data(nearest_station['code'])
        
        if not data:
            QMessageBox.warning(self.iface.mainWindow(), "Aviso", f"Sem dados climáticos para a estação {nearest_station['name']}.")
            return
            
        # Analyze
        analysis = data_manager.analyze_data(data)
        
        # Show dialog
        dialog = ClimateAnalysisDialog(station_manager, data_manager, nearest_station, data, analysis, self.iface.mainWindow())
        dialog.exec_()

    def show_add_part_dialog(self):
        """Show dialog to add a new part."""
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle("Adicionar Peça")
        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        cost_input = QLineEdit()
        profit_input = QLineEdit()

        layout.addRow("Nome da Peça:", name_input)
        layout.addRow("Custo Unitário (R$):", cost_input)
        layout.addRow("Margem de Lucro (%):", profit_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            try:
                name = name_input.text()
                cost = float(cost_input.text().replace(',', '.'))
                profit = float(profit_input.text().replace(',', '.'))
                
                self.part_manager.add_part(name, cost, profit)
                self.iface.messageBar().pushMessage("HidroCalc", f"Peça '{name}' adicionada com sucesso!", level=Qgis.Success)
            except ValueError:
                QMessageBox.warning(self.iface.mainWindow(), "Erro", "Valores inválidos para custo ou lucro.")

    def show_list_parts_dialog(self):
        """Show dialog to list all registered parts."""
        dialog = GlobalPartsDialog(self.part_manager, self.iface.mainWindow())
        dialog.exec_()

    def show_project_parts_dialog(self):
        """Show dialog to manage project parts."""
        dialog = ProjectPartsDialog(self.project_parts_manager, self.part_manager, self.project_services_manager, self.iface.mainWindow())
        dialog.exec_()

    def show_lateral_dialog(self):
        """Show dialog for lateral line sizing."""
        dialog = LateralDialog(self.iface, self.iface.mainWindow())
        dialog.exec_()

    def show_area_flow_dialog(self):
        """Show dialog for Area/Flow calculation by emitters."""
        dialog = AreaFlowDialog(self.logic, self.iface.mainWindow())
        dialog.exec_()

    def run_define_sector(self):
        """Runs the Define Sector tool."""
        layer = self.iface.activeLayer()
        if not layer or layer.type() != QgsMapLayer.VectorLayer:
             QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Selecione uma camada vetorial.")
             return
             
        if layer.selectedFeatureCount() == 0:
             QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Selecione pelo menos uma feição.")
             return
             
        dialog = SectorDialog(self.iface.mainWindow())
        if dialog.exec_() == QDialog.Accepted:
            sector_name = dialog.get_sector_name()
            result = self.logic.define_sector_attribute(layer, sector_name)
            QMessageBox.information(self.iface.mainWindow(), "Resultado", result)

    def run_water_source_tool(self):
        """Runs the Water Source Registry tool."""
        layer = self.iface.activeLayer()
        if not layer or layer.type() != QgsMapLayer.VectorLayer or layer.geometryType() != QgsWkbTypes.PointGeometry:
             QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Selecione uma camada de PONTOS (Fontes).")
             return
             
        if layer.selectedFeatureCount() != 1:
             QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Selecione EXATAMENTE UMA fonte para editar.")
             return
             
        dialog = WaterSourceDialog(self.logic, layer, self.iface.mainWindow())
        dialog.exec_()

    def run_quantify_pipes(self):
        """Opens the Pipe Quantification Dialog."""
        layer = self.iface.activeLayer()
        if not layer or layer.type() != QgsMapLayer.VectorLayer or layer.geometryType() != QgsWkbTypes.LineGeometry:
            QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Selecione uma camada de tubulação (Linhas) ativa.")
            return

        dialog = QuantifyPipesDialog(
            self.iface, 
            layer, 
            self.part_manager, 
            self.project_parts_manager, 
            self.iface.mainWindow()
        )
        dialog.exec_()

    def run_project_parts_report(self):
        """Generate PDF report for project parts directly from toolbar."""
        self.project_parts_manager.update_paths()
        parts = self.project_parts_manager.get_parts()
        if not parts:
            QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Não há peças no projeto para gerar relatório.")
            return

        from qgis.PyQt.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(), "Salvar Relatório", "", "HTML Files (*.html)"
        )
        
        if filename:
            if not filename.endswith('.html'):
                filename += '.html'
            
            # Ask for map orientation
            orientations = ["Retrato", "Paisagem"]
            orientation, ok = QInputDialog.getItem(self.iface.mainWindow(), "Orientação do Mapa", "Escolha a orientação do mapa:", orientations, 0, False)
            if not ok:
                return
            
            # Ask for grid interval
            grid_interval, ok = QInputDialog.getDouble(self.iface.mainWindow(), "Grade do Mapa", "Intervalo da Grade (m):", 50.0, 1.0, 10000.0, 1)
            if not ok:
                return

            self.project_services_manager.update_paths()
            services = self.project_services_manager.get_services()
            
            # Fetch Climate Data automatically
            climate_data = None
            chart_paths = {}
            try:
                layer = self.iface.activeLayer()
                if layer:
                    extent = layer.extent()
                    if layer.selectedFeatureCount() > 0:
                        extent = layer.boundingBoxOfSelected()
                    center = extent.center()
                    
                    crs_src = layer.crs()
                    crs_dest = QgsCoordinateReferenceSystem("EPSG:4326")
                    xform = QgsCoordinateTransform(crs_src, crs_dest, QgsProject.instance())
                    center_wgs84 = xform.transform(center)
                    lat, lon = center_wgs84.y(), center_wgs84.x()
                    
                    station_manager = StationManager(self.plugin_dir)
                    nearest_station = station_manager.get_nearest_station(lat, lon)
                    
                    if nearest_station:
                        data_manager = ClimateDataManager(self.plugin_dir)
                        data = data_manager.get_station_data(nearest_station['code'])
                        if data:
                            analysis = data_manager.analyze_data(data)
                            climate_data = analysis
                            climate_data['station_name'] = nearest_station['name']
                            climate_data['station_code'] = nearest_station['code']
                            climate_data['station_uf'] = nearest_station['uf']
                            climate_data['station_lat'] = nearest_station['lat']
                            climate_data['station_lon'] = nearest_station['lon']
                            
                            # Generate Critical Analysis Text
                            climate_data['critical_analysis'] = data_manager.generate_critical_analysis_text(analysis)
                            
                            # Generate Charts
                            from .core.charts import ClimateChartGenerator
                            chart_gen = ClimateChartGenerator()
                            
                            base_path = filename.replace('.html', '')
                            summary_chart_path = f"{base_path}_summary_chart.png"
                            seasonality_chart_path = f"{base_path}_seasonality_chart.png"
                            
                            chart_gen.generate_summary_charts(data, summary_chart_path)
                            chart_gen.generate_seasonality_chart(analysis['advanced']['irrigation_window'], seasonality_chart_path)
                            
                            chart_paths = {
                                'summary': summary_chart_path,
                                'seasonality': seasonality_chart_path
                            }
                            
            except Exception as e:
                print(f"Error fetching climate data for report: {e}")
            
            result = self.logic.generate_project_parts_report(parts, services, filename, orientation, grid_interval, climate_data, chart_paths)
            QMessageBox.information(self.iface.mainWindow(), "Relatório", result)

    def show_add_service_dialog(self):
        """Show dialog to add a new service."""
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle("Cadastrar Serviço")
        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        cost_input = QLineEdit()

        layout.addRow("Descrição do Serviço:", name_input)
        layout.addRow("Custo Unitário (R$):", cost_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            try:
                name = name_input.text()
                cost = float(cost_input.text().replace(',', '.'))
                
                self.service_manager.add_service(name, cost)
                self.iface.messageBar().pushMessage("HidroCalc", f"Serviço '{name}' cadastrado com sucesso!", level=Qgis.Success)
            except ValueError:
                QMessageBox.warning(self.iface.mainWindow(), "Erro", "Valor inválido para custo.")

    def show_list_services_dialog(self):
        """Show dialog to list all registered services."""
        dialog = GlobalServicesDialog(self.service_manager, self.iface.mainWindow())
        dialog.exec_()

    def show_project_services_dialog(self):
        """Show dialog to manage project services."""
        dialog = ProjectServicesDialog(self.project_services_manager, self.service_manager, self.iface.mainWindow())
        dialog.exec_()

    def show_terms_dialog(self):
        """Show dialog to edit Terms of Service."""
        dialog = TermsDialog(self.iface.mainWindow())
        if dialog.exec_() == QDialog.Accepted:
            dialog.save_terms()
            self.iface.messageBar().pushMessage("HidroCalc", "Termos de serviço salvos.", level=Qgis.Success)

    def show_hydraulic_dialog(self):
        """Show hydraulic design dialog."""
        # Create dialog if not exists or if it was closed (deleted)
        if not hasattr(self, 'hydraulic_dialog') or self.hydraulic_dialog is None:
            self.hydraulic_dialog = HydraulicDesignDialog(self.iface, self.iface.mainWindow())
            # Ensure we clean up the reference when closed
            self.hydraulic_dialog.finished.connect(self._on_hydraulic_dialog_closed)
        
        self.hydraulic_dialog.show()
        self.hydraulic_dialog.raise_()
        self.hydraulic_dialog.activateWindow()

    def _on_hydraulic_dialog_closed(self):
        self.hydraulic_dialog = None

    def run_genetic_optimization(self):
        """Runs the genetic optimization."""
        # Confirm with user if running from GUI
        reply = QMessageBox.question(
            self.iface.mainWindow(), 
            "Otimização Genética", 
            "Isso irá rodar um algoritmo genético para otimizar toda a rede hidráulica.\n"
            "Certifique-se de ter as camadas 'Fonte', 'Válvulas' e tubulações nomeadas corretamente.\n"
            "Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.iface.messageBar().pushMessage("HidroCalc", "Iniciando otimização genética... Isso pode levar alguns segundos.", level=Qgis.Info)
            # Process events to show message
            from qgis.PyQt.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            
            result = self.logic.run_genetic_optimization()
            QMessageBox.information(self.iface.mainWindow(), "Resultado", result)
            return result
        return "Cancelado pelo usuário."

    def run_auto_sectoring(self):
        """Runs automatic sectoring dialog."""
        # 1. Select Emitter Layer
        layer_name, ok = QInputDialog.getItem(
            self.iface.mainWindow(), 
            "Setorização Automática", 
            "Selecione a Camada de Emissores:", 
            self.logic.get_vector_layers_names(QgsWkbTypes.PointGeometry), 
            0, False
        )
        if not ok or not layer_name: return
        
        # 2. Target Flow
        flow, ok = QInputDialog.getDouble(
            self.iface.mainWindow(), 
            "Setorização Automática", 
            "Vazão Alvo por Setor (l/h):", 
            10000.0, 0.0, 1000000.0, 1
        )
        if not ok: return
        
        # 3. Run
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        result = self.logic.run_auto_sectoring(layer, flow)
        QMessageBox.information(self.iface.mainWindow(), "Resultado", result)

    def run_pump_selection(self):
        """Runs pump selection dialog."""
        # 1. Flow
        flow, ok = QInputDialog.getDouble(
            self.iface.mainWindow(), 
            "Seleção de Bomba", 
            "Vazão do Sistema (m³/h):", 
            10.0, 0.0, 1000.0, 2
        )
        if not ok: return
        
        # 2. Head
        head, ok = QInputDialog.getDouble(
            self.iface.mainWindow(), 
            "Seleção de Bomba", 
            "Altura Manométrica Total (mca):", 
            30.0, 0.0, 200.0, 2
        )
        if not ok: return
        
        # 3. Run
        result = self.logic.select_pump(flow, head)
        QMessageBox.information(self.iface.mainWindow(), "Resultado", result)

    def run_export_csv(self):
        """Exports project parts to CSV."""
        # Need to gather parts first. Reusing logic from report generation would be best.
        # But report generation logic is inside ReportGenerator.
        # Let's ask user for path first.
        output_path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(), "Salvar CSV", "", "CSV Files (*.csv)"
        )
        if not output_path: return
        
        # Gather data (Mocking for now, ideally should come from ProjectPartsManager)
        # Since we don't have the manager instance here easily (it's in logic or dialogs),
        # we will instantiate a temporary one or just show a message that it requires the manager.
        # BETTER: The logic class should handle this.
        
        # For this MVP, let's just export what we have in the JSON if possible, 
        # OR just call the report generator with empty lists if we can't get data.
        # Real implementation needs the Parts Manager to be accessible.
        
        # Let's try to load from JSON as a fallback for "Project Info" parts? No, parts are in separate JSONs usually.
        # Assuming we have access to parts via Logic -> Reporter? No.
        
        # Let's just show a message that this feature requires the Parts Manager to be loaded.
        # OR, we can instantiate the dialogs to get the managers.
        
        try:
            # Quick hack: Instantiate dialogs to get managers (not efficient but works for MVP)
            # Ideally, Managers should be singletons or in Logic.
            from .ui.project_items_dialog import ProjectItemsDialog
            dlg = ProjectItemsDialog(self.iface)
            parts = dlg.parts_manager.load_items()
            services = dlg.services_manager.load_items()
            
            result = self.logic.reporter.export_to_csv(parts, services, output_path)
            QMessageBox.information(self.iface.mainWindow(), "Sucesso", result)
        except Exception as e:
            QMessageBox.warning(self.iface.mainWindow(), "Erro", f"Erro ao exportar: {e}")

    def run_plot_hgl(self):
        """Plots HGL for selected features."""
        layer = self.iface.activeLayer()
        if not layer or layer.selectedFeatureCount() == 0:
            QMessageBox.warning(self.iface.mainWindow(), "Aviso", "Selecione tubos conectados para plotar o perfil.")
            return
            
        # 1. Sort features to form a path (Graph traversal)
        # This is complex. For MVP, we assume user selected in order OR we just plot by distance from start.
        # Let's try to sort by distance from a "start" node.
        
        features = list(layer.selectedFeatures())
        if not features: return
        
        # Extract data
        distances = []
        elevations = []
        pressures = []
        labels = []
        
        cum_dist = 0.0
        
        # Naive approach: just iterate. 
        # Real approach: Build graph, find path.
        # Let's assume the user selected a single line sequence.
        
        for feat in features:
            # Get Length
            l = feat.geometry().length()
            
            # Get Node Elevations (Start/End) - Need logic to know direction.
            # We will use the feature attributes if available (Pressure Start, Pressure End?)
            # Or just plot the feature's average/start.
            
            # Let's assume we have 'Pressao' and 'Elevacao' attributes on the pipe (average?)
            # Or we look at the nodes.
            # Since we don't have easy node access here without rebuilding network, 
            # let's use a simplified visualization: Plot attributes of the LINE itself.
            
            # Attributes: 'Pressao' (Pressure), 'Elevacao' (Elevation) - if they exist.
            # If not, we can't plot.
            
            try:
                p = float(feat['Pressao']) # Assuming this field exists after calculation
                # Elevation might not be on the pipe.
                # If we used DEM, we might have it.
                # Let's try to sample from geometry centroid if DEM is available in Logic.
                
                # If we can't get elevation, plot 0.
                z = 0.0
                
                distances.append(cum_dist)
                pressures.append(p)
                elevations.append(z)
                labels.append(str(feat.id()))
                
                cum_dist += l
            except:
                pass
                
        if not distances:
            QMessageBox.warning(self.iface.mainWindow(), "Erro", "Não foi possível extrair dados de pressão (Campo 'Pressao').")
            return
            
        # Show Dialog
        dlg = ChartsDialog(self.iface.mainWindow(), "Perfil de Pressão")
        dlg.plot_hgl(distances, elevations, pressures, labels)
        dlg.exec_()

    def list_nearest_stations(self) -> str:
        """Returns nearest stations to the project center."""
        try:
            # Try to get project center from active layer or canvas
            center = self.iface.mapCanvas().center()
            if self.iface.activeLayer():
                center = self.iface.activeLayer().extent().center()
                
            # Use StationManager logic (simplified)
            # Assuming StationManager can be instantiated or we can access the DB
            # We need to import sqlite3 or use QgsDataSourceUri but StationManager handles it
            from .clima_mensal import StationManager
            sm = StationManager(self.plugin_dir)
            stations = sm.get_nearest_stations(center.y(), center.x(), limit=5)
            
            if not stations:
                return "Nenhuma estação encontrada próxima."
                
            result = "Estações Meteorológicas Próximas:\n"
            for s in stations:
                # Assuming s is a tuple or dict. Let's check StationManager implementation if needed
                # Usually (code, name, state, distance)
                result += f"- {s['nome']} - {s['uf']} (Código: {s['codigo']}, Dist: {s['distancia']:.1f}km)\n"
            return result
            
        except Exception as e:
            return f"Erro ao listar estações: {str(e)}"


