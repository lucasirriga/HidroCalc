from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class ChartsDialog(QDialog):
    def __init__(self, parent=None, title="Gráfico"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)
        
        self.layout = QVBoxLayout(self)
        
        # Matplotlib Figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        
    def plot_hgl(self, distances, elevations, pressures, nodes_labels=None):
        """Plots Hydraulic Grade Line (HGL) and Terrain Profile."""
        ax = self.figure.add_subplot(111)
        ax.clear()
        
        # Calculate HGL (Elevation + Pressure)
        hgl = [e + p for e, p in zip(elevations, pressures)]
        
        # Plot Terrain
        ax.plot(distances, elevations, label='Terreno (Cota)', color='brown', marker='o')
        ax.fill_between(distances, elevations, min(elevations)-5, color='brown', alpha=0.3)
        
        # Plot HGL
        ax.plot(distances, hgl, label='Linha Piezométrica (HGL)', color='blue', linestyle='--', marker='x')
        
        # Labels
        ax.set_xlabel('Distância (m)')
        ax.set_ylabel('Elevação / Cota (m)')
        ax.set_title('Perfil Hidráulico')
        ax.legend()
        ax.grid(True)
        
        # Annotate Nodes
        if nodes_labels:
            for i, txt in enumerate(nodes_labels):
                ax.annotate(txt, (distances[i], hgl[i]), textcoords="offset points", xytext=(0,10), ha='center')
        
        self.canvas.draw()
