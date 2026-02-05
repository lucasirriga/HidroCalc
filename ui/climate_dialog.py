from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTabWidget, QWidget, QPushButton, QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from qgis.PyQt.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib
import numpy as np
matplotlib.use('Qt5Agg')

class ClimateAnalysisDialog(QDialog):
    def __init__(self, station_manager, data_manager, current_station, data, analysis, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Análise Climática - HidroCalc")
        self.resize(1000, 700)
        
        self.station_manager = station_manager
        self.data_manager = data_manager
        self.current_station = current_station
        self.data = data
        self.analysis = analysis
        
        self.layout = QVBoxLayout(self)
        
        # Header with Station Selection
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Estação Meteorológica:"))
        
        self.combo_stations = QComboBox()
        # Sort stations by distance from current station location
        lat = self.current_station.get('lat')
        lon = self.current_station.get('lon')
        if lat is not None and lon is not None:
            self.stations_list = self.station_manager.get_stations_sorted_by_distance(lat, lon)
        else:
            self.stations_list = self.station_manager.get_all_stations()

        for s in self.stations_list:
            self.combo_stations.addItem(f"{s.get('name')} ({s.get('code')})", s['code'])
            
        # Set current station
        index = self.combo_stations.findData(self.current_station['code'])
        if index >= 0:
            self.combo_stations.setCurrentIndex(index)
            
        self.combo_stations.currentIndexChanged.connect(self.on_station_changed)
        header_layout.addWidget(self.combo_stations)
        header_layout.addStretch()
        
        self.layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # Tab 1: Resumo
        self.tab_summary = QWidget()
        self.summary_layout = QVBoxLayout(self.tab_summary)
        self.tabs.addTab(self.tab_summary, "Resumo e Análise")
        
        # Tab 2: Gráficos
        self.tab_charts = QWidget()
        self.charts_layout = QVBoxLayout(self.tab_charts)
        self.tabs.addTab(self.tab_charts, "Gráficos")

        # Tab 3: Dimensionamento & Manejo
        self.tab_advanced = QWidget()
        self.advanced_layout = QVBoxLayout(self.tab_advanced)
        self.tabs.addTab(self.tab_advanced, "Dimensionamento & Manejo")
        
        # Initial Render
        self.render_summary()
        self.render_charts()
        self.render_advanced()
        
        # Close button
        self.btn_close = QPushButton("Fechar")
        self.btn_close.clicked.connect(self.accept)
        self.layout.addWidget(self.btn_close, alignment=Qt.AlignRight)

    def on_station_changed(self, index):
        code = self.combo_stations.itemData(index)
        # Update current station object
        for s in self.stations_list:
            if s['code'] == code:
                self.current_station = s
                break
        
        # Fetch new data
        self.data = self.data_manager.get_station_data(code)
        self.analysis = self.data_manager.analyze_data(self.data)
        
        # Re-render
        self.render_summary()
        self.render_charts()
        self.render_advanced()

    def render_summary(self):
        # Clear previous content
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Station Info
        info_text = (
            f"<b>Código:</b> {self.current_station.get('code')} | "
            f"<b>Cidade:</b> {self.current_station.get('name')} | "
            f"<b>UF:</b> {self.current_station.get('uf')}<br>"
            f"<b>Latitude:</b> {self.current_station.get('lat')} | "
            f"<b>Longitude:</b> {self.current_station.get('lon')}<br><br>"
            f"<b>Dados Analisados:</b> {self.analysis.get('count', 0)} meses"
        )
        lbl_info = QLabel(info_text)
        lbl_info.setTextFormat(Qt.RichText)
        self.summary_layout.addWidget(lbl_info)
        
        # Annual Stats Table
        self.summary_layout.addWidget(QLabel("<b>Acumulados Anuais:</b>"))
        
        annual_data = self.analysis.get('annual', {})
        if annual_data:
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Ano", "Precipitação (mm)", "ETo (mm)", "Balanço Hídrico (mm)"])
            table.setRowCount(len(annual_data))
            
            sorted_years = sorted(annual_data.keys())
            for i, year in enumerate(sorted_years):
                stats = annual_data[year]
                table.setItem(i, 0, QTableWidgetItem(str(year)))
                table.setItem(i, 1, QTableWidgetItem(f"{stats['precip']:.2f}"))
                table.setItem(i, 2, QTableWidgetItem(f"{stats['eto']:.2f}"))
                table.setItem(i, 3, QTableWidgetItem(f"{stats['balanco']:.2f}"))
            
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setMinimumHeight(200)
            self.summary_layout.addWidget(table)
        else:
            self.summary_layout.addWidget(QLabel("Sem dados anuais disponíveis."))

        # Critical Analysis
        self.summary_layout.addWidget(QLabel("<b>Análise Crítica:</b>"))
        analysis_text = self._generate_critical_analysis()
        lbl_analysis = QLabel(analysis_text)
        lbl_analysis.setWordWrap(True)
        self.summary_layout.addWidget(lbl_analysis)
        
        self.summary_layout.addStretch()

    def _generate_critical_analysis(self):
        avg_balanco = self.analysis.get('avg_balanco', 0)
        total_precip = self.analysis.get('total_precip', 0)
        total_eto = self.analysis.get('total_eto', 0)
        
        text = ""
        if total_precip < total_eto:
            text += "A região apresenta um déficit hídrico significativo no período analisado, indicando a necessidade de irrigação suplementar. "
        else:
            text += "A região apresenta um superávit hídrico no acumulado, mas a distribuição mensal deve ser observada nos gráficos. "
            
        if avg_balanco < 0:
            text += "O balanço hídrico médio é negativo, reforçando a demanda por reposição hídrica."
        else:
            text += "O balanço hídrico médio é positivo."
            
        return text

    def render_advanced(self):
        # Clear previous content
        while self.advanced_layout.count():
            item = self.advanced_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        adv_data = self.analysis.get('advanced', {})
        if not adv_data:
            self.advanced_layout.addWidget(QLabel("Dados avançados não disponíveis."))
            return

        # 1. Dimensionamento (Sizing)
        self.advanced_layout.addWidget(QLabel("<h3>1. Dimensionamento (Demanda Máxima)</h3>"))
        self.advanced_layout.addWidget(QLabel("<i>Identificação do período crítico para dimensionamento do sistema.</i>"))
        
        max_month = adv_data.get('max_eto_month', {})
        max_daily = adv_data.get('max_eto_daily', 0)
        
        sizing_text = (
            f"<b>Mês Crítico (Pico de ETo):</b> {max_month.get('mes')}/{max_month.get('ano')}<br>"
            f"<b>ETo Mensal no Pico:</b> {max_month.get('eto', 0):.2f} mm<br>"
            f"<b>Demanda Diária Estimada:</b> {max_daily:.2f} mm/dia<br>"
            f"<span style='color: gray;'>*Considere a eficiência do sistema para obter a Lâmina Bruta.</span>"
        )
        lbl_sizing = QLabel(sizing_text)
        lbl_sizing.setTextFormat(Qt.RichText)
        self.advanced_layout.addWidget(lbl_sizing)
        
        # 2. Manejo (Management)
        self.advanced_layout.addWidget(QLabel("<h3>2. Manejo (Precipitação Efetiva)</h3>"))
        pe_factor = adv_data.get('pe_factor', 0.75)
        self.advanced_layout.addWidget(QLabel(f"<i>Considerando Precipitação Efetiva (Pe) = {pe_factor*100:.0f}% da Chuva Total.</i>"))
        
        total_pe = adv_data.get('total_pe', 0)
        total_deficit_real = adv_data.get('total_deficit_real', 0)
        
        management_text = (
            f"<b>Precipitação Efetiva Total:</b> {total_pe:.2f} mm<br>"
            f"<b>Déficit Hídrico Real Acumulado:</b> {total_deficit_real:.2f} mm<br>"
            f"<span style='color: blue;'>Este é o volume real que precisaria ter sido reposto via irrigação.</span>"
        )
        lbl_mgmt = QLabel(management_text)
        lbl_mgmt.setTextFormat(Qt.RichText)
        self.advanced_layout.addWidget(lbl_mgmt)
        
        # 3. Janela de Irrigação (Seasonality)
        self.advanced_layout.addWidget(QLabel("<h3>3. Janela de Irrigação (Sazonalidade)</h3>"))
        self.advanced_layout.addWidget(QLabel("<i>Probabilidade histórica de necessidade de irrigação por mês.</i>"))
        
        window = adv_data.get('irrigation_window', {})
        
        # Create a simple bar chart for seasonality
        fig, ax = plt.subplots(figsize=(6, 3))
        months = list(window.keys())
        probs = list(window.values())
        
        bars = ax.bar(months, probs, color='skyblue')
        ax.set_xlabel('Mês')
        ax.set_ylabel('Probabilidade (%)')
        ax.set_title('Frequência de Déficit Hídrico')
        ax.set_xticks(months)
        ax.set_ylim(0, 100)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}%',
                    ha='center', va='bottom', fontsize=8)
        
        fig.tight_layout()
        canvas = FigureCanvas(fig)
        self.advanced_layout.addWidget(canvas)
        
        self.advanced_layout.addStretch()

    def render_charts(self):
        # Clear previous charts
        while self.charts_layout.count():
            item = self.charts_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.data:
            self.charts_layout.addWidget(QLabel("Sem dados para gerar gráficos."))
            return

        # Prepare data
        dates = [f"{d['mes']}/{d['ano']}" for d in self.data]
        years = [d['ano'] for d in self.data]
        eto = [d['eto'] for d in self.data]
        precip = [d['precipitacao'] for d in self.data]
        balanco = [d['balanco'] for d in self.data]
        
        unique_years = sorted(list(set(years)))
        # Generate colors for years
        cmap = plt.get_cmap('tab10')
        year_colors = {year: cmap(i % 10) for i, year in enumerate(unique_years)}
        bar_colors = [year_colors[y] for y in years]

        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
        
        # Chart 1: ETo vs Precip (Grouped by Year Color)
        # Since we want to color by year, we can't just do a single bar call easily if we want a legend per year.
        # But user said "modifique as cores das barras conforme o ano".
        
        # Plot Precip bars colored by year
        ax1.bar(dates, precip, color=bar_colors, alpha=0.7, label='Precipitação (cor por ano)')
        # Plot ETo line
        ax1.plot(dates, eto, label='ETo', color='black', marker='o', linewidth=2)
        
        ax1.set_title('Precipitação vs Evapotranspiração (ETo)')
        ax1.set_ylabel('mm')
        ax1.tick_params(axis='x', rotation=90)
        
        # Create custom legend for years
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=year_colors[y], label=str(y)) for y in unique_years]
        legend_elements.append(plt.Line2D([0], [0], color='black', marker='o', label='ETo'))
        ax1.legend(handles=legend_elements, loc='upper right', ncol=len(unique_years)//2 + 1)
        
        # Chart 2: Water Balance (Colored by Year)
        ax2.bar(dates, balanco, color=bar_colors)
        ax2.set_title('Balanço Hídrico Mensal (Cores por Ano)')
        ax2.set_ylabel('mm')
        ax2.axhline(0, color='black', linewidth=0.8)
        ax2.tick_params(axis='x', rotation=90)
        ax2.legend(handles=[Patch(facecolor=year_colors[y], label=str(y)) for y in unique_years], loc='upper right')
        
        fig.tight_layout()
        
        canvas = FigureCanvas(fig)
        self.charts_layout.addWidget(canvas)
