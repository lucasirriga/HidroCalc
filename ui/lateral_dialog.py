from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, 
    QDoubleSpinBox, QDialogButtonBox, QLabel, QMessageBox, QPushButton,
    QProgressBar, QTextEdit, QApplication
)
from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes
from ..core.lateral_manager import LateralManager

class LateralDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.manager = LateralManager()
        self.setWindowTitle("Dimensionamento de Linha Lateral")
        self.resize(400, 450)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Layers Selection
        self.cb_pipe = QComboBox()
        self.cb_hose = QComboBox()
        self.cb_emitter = QComboBox()
        
        # Populate Combos
        self._populate_layers(self.cb_pipe, QgsWkbTypes.LineGeometry)
        self._populate_layers(self.cb_hose, QgsWkbTypes.LineGeometry)
        self._populate_layers(self.cb_emitter, QgsWkbTypes.PointGeometry)
        
        # Flow Input
        self.sb_flow = QDoubleSpinBox()
        self.sb_flow.setRange(0.0, 1000.0)
        self.sb_flow.setValue(50.0) # Default 50 l/h
        self.sb_flow.setSuffix(" l/h")
        self.sb_flow.setDecimals(1)
        
        # Pressure Input
        self.sb_pressure = QDoubleSpinBox()
        self.sb_pressure.setRange(0.0, 500.0)
        self.sb_pressure.setValue(10.0)
        self.sb_pressure.setSuffix(" mca")
        self.sb_pressure.setDecimals(1)
        
        form_layout.addRow("Camada de Tubulação:", self.cb_pipe)
        form_layout.addRow("Camada de Mangueiras:", self.cb_hose)
        form_layout.addRow("Camada de Aspersores:", self.cb_emitter)
        form_layout.addRow("Vazão do Aspersor:", self.sb_flow)
        form_layout.addRow("Pressão de Serviço:", self.sb_pressure)
        
        # Tolerance Input
        self.sb_tolerance = QDoubleSpinBox()
        self.sb_tolerance.setRange(0.01, 5.0)
        self.sb_tolerance.setValue(0.5)
        self.sb_tolerance.setSuffix(" m")
        self.sb_tolerance.setDecimals(2)
        form_layout.addRow("Tolerância (Conexão):", self.sb_tolerance)
        
        layout.addLayout(form_layout)
        
        # Buttons
        self.btn_check = QPushButton("Verificar Geometria")
        self.btn_check.clicked.connect(self.check_geometry)
        layout.addWidget(self.btn_check)
        
        self.btn_run = QPushButton("Dimensionar")
        self.btn_run.clicked.connect(self.run_dimensioning)
        layout.addWidget(self.btn_run)
        
        # Feedback Widgets
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(100)
        self.log_box.setPlaceholderText("Log de processamento...")
        layout.addWidget(self.log_box)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def check_geometry(self):
        pipe_layer = self.cb_pipe.currentData()
        hose_layer = self.cb_hose.currentData()
        emitter_layer = self.cb_emitter.currentData()
        flow = self.sb_flow.value()
        
        if not pipe_layer or not hose_layer or not emitter_layer:
            QMessageBox.warning(self, "Aviso", "Selecione todas as camadas primeiro.")
            return
            
        try:
            # Check selection
            sel_count = pipe_layer.selectedFeatureCount()
            only_selected = sel_count > 0
            
            # Setup Visual Feedback
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.log_box.clear()
            self.log_box.append("Iniciando verificação...")
            QApplication.processEvents()
            
            def progress_cb(current, total):
                percent = int((current / total) * 100)
                self.progress_bar.setValue(percent)
                QApplication.processEvents()
                
            def log_cb(msg):
                self.log_box.append(msg)
                # Auto scroll
                sb = self.log_box.verticalScrollBar()
                sb.setValue(sb.maximum())
                QApplication.processEvents()
                
            def highlight_cb(fid):
                if pipe_layer:
                    pipe_layer.selectByIds([fid])
                    QApplication.processEvents()
            
            # Pass callbacks - Uses existing calculate_statistics logic
            results, warnings = self.manager.calculate_statistics(
                pipe_layer, hose_layer, emitter_layer, flow, 
                only_selected, 
                progress_callback=progress_cb,
                log_callback=log_cb,
                highlight_callback=highlight_cb
            )
            
            self.progress_bar.setValue(100)
            self.log_box.append("Concluído.")
            
            if not results:
                QMessageBox.information(self, "Verificação", "Nenhuma tubulação processada.")
                return

            # Analyze results
            total_pipes = len(results)
            total_flow_l_h = sum(r['flow'] for r in results)
            total_flow_m3 = total_flow_l_h / 1000.0
            total_hoses = sum(r['hoses'] for r in results)
            pipes_with_flow = sum(1 for r in results if r['flow'] > 0)
            zero_flow_pipes = total_pipes - pipes_with_flow
            
            msg = ""
            if warnings:
                msg += f"<div style='color:orange'><b>AVISO:</b> {'<br>'.join(warnings)}</div><br>"
            
            if total_pipes == 1:
                # Detail View
                r = results[0]
                flow_m3 = r['flow'] / 1000.0
                msg += (
                    f"<b>Detalhes da Lateral (ID: {r['id']}):</b><br><br>"
                    f"• Mangueiras Conectadas: {r['hoses']}<br>"
                    f"• Emissores Estimados: {r['emitters']}<br>"
                    f"• Vazão Total: <b>{flow_m3:.3f} m³/h</b>"
                )
            else:
                # Summary View
                msg += (
                    f"<b>Resumo ({total_pipes} laterais analisadas):</b><br><br>"
                    f"• Vazão Total do Sistema: {total_flow_m3:.3f} m³/h<br>"
                    f"• Total de Mangueiras: {total_hoses}<br>"
                    f"• Laterais com Vazão: {pipes_with_flow}<br>"
                )
                if zero_flow_pipes > 0:
                    msg += f"<br><b style='color:red;'>ALERTA:</b> {zero_flow_pipes} laterais não possuem mangueiras conectadas!"
                else:
                    msg += "<br><b style='color:green;'>Tudo OK!</b> Todas as laterais possuem demanda."
                    
            if only_selected:
                 msg = "(Apenas Selecionados)<br>" + msg

            QMessageBox.information(self, "Verificação Geométrica", msg)
            
        except Exception as e:
             QMessageBox.warning(self, "Erro", f"Erro na verificação: {e}")
        
    def _populate_layers(self, combo, geom_type):
        combo.clear()
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == geom_type:
                combo.addItem(layer.name(), layer)
                
    def run_dimensioning(self):
        pipe_layer = self.cb_pipe.currentData()
        hose_layer = self.cb_hose.currentData()
        emitter_layer = self.cb_emitter.currentData()
        flow = self.sb_flow.value()
        pressure = self.sb_pressure.value()
        tolerance = self.sb_tolerance.value()
        
        if not pipe_layer or not hose_layer or not emitter_layer:
            QMessageBox.warning(self, "Erro", "Selecione todas as camadas.")
            return
        
        # Confirm action
        if QMessageBox.question(self, "Confirmar", "Isso irá alterar a geometria e atributos da camada de tubulação. Continuar?") != QMessageBox.Yes:
            return

        # Disable main UI during process
        self.setEnabled(False)
        
        # Setup Feedback
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0) 
        self.log_box.clear()
        self.log_box.append("Iniciando Dimensionamento...")
        QApplication.processEvents()
        
        def progress_cb(current, total):
            pass
            
        def log_cb(msg):
            self.log_box.append(msg)
            sb = self.log_box.verticalScrollBar()
            sb.setValue(sb.maximum())
            QApplication.processEvents()
            
        def highlight_cb(fid):
            # During sizing, highlight processed segments
            if pipe_layer:
                pipe_layer.selectByIds([fid])
                QApplication.processEvents()
        
        # Determine selection mode
        sel_count = pipe_layer.selectedFeatureCount()
        only_selected = sel_count > 0
        
        # Run Calculation
        try:
            result = self.manager.process_network(
                pipe_layer, hose_layer, emitter_layer, flow, max(0.1, pressure),
                only_selected=only_selected,
                connection_tolerance=tolerance,
                progress_callback=progress_cb,
                log_callback=log_cb,
                highlight_callback=highlight_cb
            )
            
            self.progress_bar.setValue(100)
            self.log_box.append("Processo finalizado com sucesso.")
            QMessageBox.information(self, "Resultado", result)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha no processamento: {str(e)}")
        finally:
            self.setEnabled(True)

    def accept(self):
        super().accept()

