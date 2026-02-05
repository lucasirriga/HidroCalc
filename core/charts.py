import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch
import os

class ClimateChartGenerator:
    def __init__(self):
        pass

    def generate_summary_charts(self, data, output_path=None):
        """
        Generates the summary charts (Precip vs ETo and Water Balance).
        If output_path is provided, saves the figure to that path.
        Returns the Figure object.
        """
        if not data:
            return None

        dates = [f"{d['mes']}/{d['ano']}" for d in data]
        years = [d['ano'] for d in data]
        eto = [d['eto'] for d in data]
        precip = [d['precipitacao'] for d in data]
        balanco = [d['balanco'] for d in data]
        
        unique_years = sorted(list(set(years)))
        cmap = plt.get_cmap('tab10')
        year_colors = {year: cmap(i % 10) for i, year in enumerate(unique_years)}
        bar_colors = [year_colors[y] for y in years]

        fig = Figure(figsize=(10, 10))
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)
        
        # Chart 1: ETo vs Precip
        ax1.bar(dates, precip, color=bar_colors, alpha=0.7, label='Precipitação')
        ax1.plot(dates, eto, label='ETo', color='black', marker='o', linewidth=2)
        
        ax1.set_title('Precipitação vs Evapotranspiração (ETo)')
        ax1.set_ylabel('mm')
        ax1.tick_params(axis='x', rotation=90)
        
        legend_elements = [Patch(facecolor=year_colors[y], label=str(y)) for y in unique_years]
        legend_elements.append(plt.Line2D([0], [0], color='black', marker='o', label='ETo'))
        ax1.legend(handles=legend_elements, loc='upper right', ncol=max(1, len(unique_years)//2 + 1))
        
        # Chart 2: Water Balance
        ax2.bar(dates, balanco, color=bar_colors)
        ax2.set_title('Balanço Hídrico Mensal')
        ax2.set_ylabel('mm')
        ax2.axhline(0, color='black', linewidth=0.8)
        ax2.tick_params(axis='x', rotation=90)
        ax2.legend(handles=[Patch(facecolor=year_colors[y], label=str(y)) for y in unique_years], loc='upper right')
        
        fig.tight_layout()
        
        if output_path:
            fig.savefig(output_path, dpi=100)
            
        return fig

    def generate_seasonality_chart(self, irrigation_window, output_path=None):
        """
        Generates the seasonality chart.
        If output_path is provided, saves the figure to that path.
        Returns the Figure object.
        """
        if not irrigation_window:
            return None

        fig = Figure(figsize=(6, 3))
        ax = fig.add_subplot(111)
        
        months = list(irrigation_window.keys())
        probs = list(irrigation_window.values())
        
        bars = ax.bar(months, probs, color='skyblue')
        ax.set_xlabel('Mês')
        ax.set_ylabel('Probabilidade (%)')
        ax.set_title('Frequência de Déficit Hídrico')
        ax.set_xticks(months)
        ax.set_ylim(0, 100)
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}%',
                    ha='center', va='bottom', fontsize=8)
        
        fig.tight_layout()
        
        if output_path:
            fig.savefig(output_path, dpi=100)
            
        return fig
