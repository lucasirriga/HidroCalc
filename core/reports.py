import os
import json
import math
from datetime import datetime
from string import Template
from typing import Optional, List, Dict, Any, Union
from qgis.core import QgsProject, QgsWkbTypes, QgsFeatureRequest, QgsVectorLayer
from .constants import FIELD_LENGTH, FIELD_DN
import csv

class ReportGenerator:
    def __init__(self, iface: Any, plugin_dir: str):
        self.iface = iface
        self.plugin_dir = plugin_dir

    def _fmt_num(self, value: Union[float, int, str]) -> str:
        """Formata um número para o padrão brasileiro (1.000,00)."""
        try:
            return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return str(value)

    def _export_map_layout(self, output_path: str, orientation: str = "Retrato", grid_interval: float = 50.0, project_info: Optional[Dict] = None) -> None:
        """
        Exporta o canvas do mapa atual para uma imagem PNG usando MapLayoutManager.
        """
        # Importar aqui para evitar dependência circular se map_layout_manager importar isso (improvável, mas seguro)
        from ..map_layout_manager import MapLayoutManager
        manager = MapLayoutManager(self.iface)
        manager.export_layout(output_path, orientation, grid_interval, project_info)

    def generate_tubes_report(self, output_path: str, orientation: str = "Retrato", grid_interval: float = 50.0) -> str:
        try:
            layer: QgsVectorLayer = self.iface.activeLayer()
            if not layer:
                return "Nenhuma camada ativa."
            if QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.LineGeometry:
                return "Use em camada de linhas."

            required_fields = [FIELD_DN, FIELD_LENGTH]
            field_names = [f.name() for f in layer.fields()]
            missing = [f for f in required_fields if f not in field_names]
            if missing:
                return f"Campos obrigatórios ausentes: {', '.join(missing)}."
            
            selected_ids = layer.selectedFeatureIds()
            if selected_ids:
                features = layer.getFeatures(QgsFeatureRequest().setFilterFids(selected_ids))
                title_suffix = "Feições Selecionadas"
            else:
                features = layer.getFeatures()
                title_suffix = "Todas as Feições"

            sums: Dict[float, float] = {}
            
            idx_dn = layer.fields().indexFromName(FIELD_DN)
            idx_l = layer.fields().indexFromName(FIELD_LENGTH)

            for feat in features:
                try:
                    attrs = feat.attributes()
                    dn_val = attrs[idx_dn]
                    l_val = attrs[idx_l]
                    
                    if dn_val is not None and l_val is not None:
                        dn = float(dn_val)
                        l = float(l_val)
                        sums[dn] = sums.get(dn, 0) + l
                except (ValueError, TypeError):
                    pass
            
            if not sums:
                return "Nenhum dado válido para gerar relatório."

            # Preparar Dados
            logo_path = os.path.join(self.plugin_dir, "logo_tocantins.png").replace("\\", "/")
            
            project_path = QgsProject.instance().fileName()
            project_dir = os.path.dirname(project_path) if project_path else ""
            
            project_info = {}
            if project_path:
                json_path = os.path.join(project_dir, "hidrocalc_data.json")
                if os.path.exists(json_path):
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            project_info = json.load(f)
                    except Exception as e:
                        return f"Erro ao ler dados do projeto: {e}"

            results = project_info.get("results", {})
            terms = project_info.get("terms", "")
            date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

            # Gerar Linhas Tubos
            rows_html = ""
            total_tubes_all = 0
            total_length_all = 0.0

            for dn in sorted(sums.keys()):
                total_l = sums[dn]
                tubes = math.ceil(total_l / 6.0) 
                total_tubes_all += tubes
                total_length_all += total_l
                
                rows_html += f"""
                        <tr>
                            <td style="text-align: left;">{str(dn).replace('.', ',')}</td>
                            <td style="text-align: right;">{self._fmt_num(total_l)}</td>
                            <td style="text-align: right;">{tubes}</td>
                        </tr>
                """

            # --- Carregar Materiais e Serviços ---
            parts = []
            services = []
            
            if project_dir:
                parts_file = os.path.join(project_dir, 'project_parts.json')
                services_file = os.path.join(project_dir, 'project_services.json')
                
                if os.path.exists(parts_file):
                    try:
                        with open(parts_file, 'r', encoding='utf-8') as f:
                            parts = json.load(f)
                    except: parts = []
                
                if os.path.exists(services_file):
                    try:
                        with open(services_file, 'r', encoding='utf-8') as f:
                            services = json.load(f)
                    except: services = []

            # Gerar HTML Materiais
            total_parts = 0.0
            parts_rows = ""
            if parts:
                for part in parts:
                    name = part.get('name', 'Sem Nome')
                    qty = float(part.get('quantity', 0))
                    cost = float(part.get('cost', 0))
                    profit = float(part.get('profit_margin', 0))
                    unit_value = cost * (1 + profit / 100)
                    total_value = unit_value * qty
                    total_parts += total_value
                    
                    parts_rows += f"""
                        <tr>
                            <td style="text-align: left;">{name}</td>
                            <td style="text-align: center;">{self._fmt_num(qty)}</td>
                            <td style="text-align: right;">R$ {self._fmt_num(unit_value)}</td>
                            <td style="text-align: right;">R$ {self._fmt_num(total_value)}</td>
                        </tr>
                    """
            else:
                parts_rows = "<tr><td colspan='4' style='text-align: center;'>Nenhum material cadastrado.</td></tr>"

            # Gerar HTML Serviços
            total_services = 0.0
            services_rows = ""
            if services:
                for service in services:
                    name = service.get('name', 'Sem Nome')
                    qty = float(service.get('quantity', 0))
                    cost = float(service.get('cost', 0))
                    total_value = cost * qty
                    total_services += total_value
                    
                    services_rows += f"""
                        <tr>
                            <td style="text-align: left;">{name}</td>
                            <td style="text-align: center;">{self._fmt_num(qty)}</td>
                            <td style="text-align: right;">R$ {self._fmt_num(cost)}</td>
                            <td style="text-align: right;">R$ {self._fmt_num(total_value)}</td>
                        </tr>
                    """
            else:
                services_rows = "<tr><td colspan='4' style='text-align: center;'>Nenhum serviço cadastrado.</td></tr>"

            grand_total = total_parts + total_services # Tubos nao tem preco aqui, so quantidade

            # Imagem do Mapa
            map_image_path = output_path.replace('.html', '_map.png')
            self._export_map_layout(map_image_path, orientation, grid_interval, project_info)
            map_image_path = map_image_path.replace("\\", "/")

            # Modelo (Template)
            template_path = os.path.join(self.plugin_dir, "templates", "tubes_report_template.html")
            if not os.path.exists(template_path):
                return "Template tubes_report_template.html não encontrado."

            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            
            terms_section = ""
            if terms:
                terms_section = f'<div class="section-header" style="margin-top: 15pt; font-size: 12pt; font-weight: bold; color: #2E7D32;">Termos de Serviço</div><div style="margin-bottom: 15pt; font-size: 10pt; text-align: justify; white-space: pre-wrap;">{terms}</div>'

            html = template.safe_substitute(
                logo_path=logo_path,
                title_suffix=title_suffix,
                owner=project_info.get("owner", "____________________"),
                location=project_info.get("location", "____________________"),
                power=project_info.get("power", "-"),
                water=project_info.get("water", "-"),
                sources=project_info.get("sources", "-"),
                date_str=date_str,
                total_area=results.get("total_area", "-"),
                total_sectors=results.get("total_sectors", "-"),
                operating_flow=results.get("operating_flow", "-"),
                total_time=results.get("total_time", "-"),
                terms_section=terms_section,
                rows=rows_html,
                total_length=self._fmt_num(total_length_all),
                total_tubes=total_tubes_all,
                map_image_path=map_image_path,
                # Novos Campos
                parts_rows=parts_rows,
                total_parts=self._fmt_num(total_parts),
                services_rows=services_rows,
                total_services=self._fmt_num(total_services),
                grand_total=self._fmt_num(grand_total)
            )

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return f"Relatório salvo em:\n{output_path}"

        except Exception as e:
            return f"Erro ao gerar relatório: {str(e)}"

    def generate_project_parts_report(self, parts: List[Dict], services: List[Dict], output_path: str, orientation: str = "Retrato", grid_interval: float = 50.0, climate_data: Optional[Dict] = None, chart_paths: Optional[Dict] = None) -> str:
        try:
            if not parts and not services:
                return "Nenhuma peça ou serviço para gerar relatório."

            logo_path = os.path.join(self.plugin_dir, "logo_tocantins.png").replace("\\", "/")
            template_path = os.path.join(self.plugin_dir, "templates", "project_budget_template.html")
            
            project_path = QgsProject.instance().fileName()
            project_info = {}
            if project_path:
                json_path = os.path.join(os.path.dirname(project_path), "hidrocalc_data.json")
                if os.path.exists(json_path):
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            project_info = json.load(f)
                    except Exception as e:
                        return f"Erro ao ler dados do projeto: {e}"

            results = project_info.get("results", {})
            terms = project_info.get("terms", "")
            date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            total_parts = 0.0
            parts_rows = ""
            
            if parts:
                for part in parts:
                    name = part['name']
                    qty = float(part['quantity'])
                    cost = float(part['cost'])
                    profit = float(part['profit_margin'])
                    unit_value = cost * (1 + profit / 100)
                    total_value = unit_value * qty
                    total_parts += total_value
                    
                    parts_rows += f"""
                        <tr>
                            <td style="text-align: left;">{name}</td>
                            <td style="text-align: center;">{self._fmt_num(qty)}</td>
                            <td style="text-align: right;">R$ {self._fmt_num(unit_value)}</td>
                            <td style="text-align: right;">R$ {self._fmt_num(total_value)}</td>
                        </tr>
                    """
            else:
                parts_rows = "<tr><td colspan='4' style='text-align: center;'>Nenhuma peça cadastrada.</td></tr>"

            total_services = 0.0
            services_rows = ""
            
            if services:
                for service in services:
                    name = service['name']
                    qty = float(service['quantity'])
                    cost = float(service['cost'])
                    total_value = cost * qty
                    total_services += total_value
                    
                    services_rows += f"""
                        <tr>
                            <td style="text-align: left;">{name}</td>
                            <td style="text-align: center;">{self._fmt_num(qty)}</td>
                            <td style="text-align: right;">R$ {self._fmt_num(cost)}</td>
                            <td style="text-align: right;">R$ {self._fmt_num(total_value)}</td>
                        </tr>
                    """
            else:
                services_rows = "<tr><td colspan='4' style='text-align: center;'>Nenhum serviço cadastrado.</td></tr>"

            grand_total = total_parts + total_services
            
            terms_section = ""
            if terms:
                terms_section = f'<div class="section-header" style="margin-top: 15pt; font-size: 12pt; font-weight: bold; color: #2E7D32;">Termos de Serviço</div><div style="margin-bottom: 15pt; font-size: 10pt; text-align: justify; white-space: pre-wrap;">{terms}</div>'

            # Seção Climática
            climate_section = ""
            if climate_data:
                adv = climate_data.get('advanced', {})
                max_month = adv.get('max_eto_month', {})
                annual_data = climate_data.get('annual', {})
                
                # Tabela de Resumo Anual
                annual_rows = ""
                for year in sorted(annual_data.keys()):
                    stats = annual_data[year]
                    annual_rows += f"""
                        <tr>
                            <td style="text-align: center;">{year}</td>
                            <td style="text-align: center;">{self._fmt_num(stats['precip'])}</td>
                            <td style="text-align: center;">{self._fmt_num(stats['eto'])}</td>
                            <td style="text-align: center;">{self._fmt_num(stats['balanco'])}</td>
                        </tr>
                    """

                # HTML dos Gráficos
                charts_html = ""
                if chart_paths:
                    summary_chart = chart_paths.get('summary')
                    seasonality_chart = chart_paths.get('seasonality')
                    
                    if summary_chart and os.path.exists(summary_chart):
                        summary_chart = summary_chart.replace("\\", "/")
                        charts_html += f"""
                        <div style="page-break-inside: avoid; margin-top: 15px;">
                            <div style="font-weight: bold; margin-bottom: 5px;">Gráficos de Resumo (Precipitação vs ETo e Balanço Hídrico)</div>
                            <img src="{summary_chart}" style="width: 100%; border: 1px solid #ddd;" />
                        </div>
                        """
                    
                    if seasonality_chart and os.path.exists(seasonality_chart):
                        seasonality_chart = seasonality_chart.replace("\\", "/")
                        charts_html += f"""
                        <div style="page-break-inside: avoid; margin-top: 15px;">
                            <div style="font-weight: bold; margin-bottom: 5px;">Janela de Irrigação (Frequência de Déficit)</div>
                            <img src="{seasonality_chart}" style="width: 70%; margin: 0 auto; display: block; border: 1px solid #ddd;" />
                        </div>
                        """

                climate_section = f"""
                <div class="section-header" style="margin-top: 15pt; font-size: 12pt; font-weight: bold; color: #2E7D32;">Análise Climática Completa</div>
                
                <div style="margin-bottom: 10px;">
                    <b>Estação:</b> {climate_data.get('station_name', '-')} ({climate_data.get('station_code', '-')})<br>
                    <b>Localização:</b> Lat {climate_data.get('station_lat', '-')}, Lon {climate_data.get('station_lon', '-')}, {climate_data.get('station_uf', '-')}<br>
                    <b>Dados Analisados:</b> {climate_data.get('count', 0)} meses
                </div>

                <div style="font-weight: bold; margin-top: 10px; margin-bottom: 5px;">Análise Crítica</div>
                <div style="margin-bottom: 15px; text-align: justify;">
                    {climate_data.get('critical_analysis', '-')}
                </div>

                <div style="font-weight: bold; margin-top: 10px; margin-bottom: 5px;">Dimensionamento & Manejo</div>
                <table class="parts-table" style="margin-bottom: 15pt;">
                    <thead>
                        <tr>
                            <th>Parâmetro</th>
                            <th>Valor</th>
                            <th>Descrição</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="text-align: left;"><b>Mês Crítico (Pico ETo)</b></td>
                            <td style="text-align: center;">{max_month.get('mes', '-')}/{max_month.get('ano', '-')}</td>
                            <td style="text-align: left;">Mês de maior demanda hídrica</td>
                        </tr>
                        <tr>
                            <td style="text-align: left;"><b>ETo Mensal no Pico</b></td>
                            <td style="text-align: center;">{self._fmt_num(max_month.get('eto', 0))} mm</td>
                            <td style="text-align: left;">Evapotranspiração total no mês crítico</td>
                        </tr>
                        <tr>
                            <td style="text-align: left;"><b>Demanda Diária Estimada</b></td>
                            <td style="text-align: center;">{self._fmt_num(adv.get('max_eto_daily', 0))} mm/dia</td>
                            <td style="text-align: left;">Base para dimensionamento (Lâmina Líquida)</td>
                        </tr>
                        <tr>
                            <td style="text-align: left;"><b>Precipitação Efetiva Total</b></td>
                            <td style="text-align: center;">{self._fmt_num(adv.get('total_pe', 0))} mm</td>
                            <td style="text-align: left;">Chuva aproveitável ({adv.get('pe_factor', 0.75)*100:.0f}%)</td>
                        </tr>
                        <tr>
                            <td style="text-align: left;"><b>Maior Déficit Mensal</b></td>
                            <td style="text-align: center;">{self._fmt_num(adv.get('max_monthly_deficit', 0))} mm</td>
                            <td style="text-align: left;">Maior necessidade de reposição mensal</td>
                        </tr>
                    </tbody>
                </table>

                <div style="font-weight: bold; margin-top: 10px; margin-bottom: 5px;">Acumulados Anuais</div>
                <table class="parts-table" style="margin-bottom: 15pt;">
                    <thead>
                        <tr>
                            <th>Ano</th>
                            <th>Precipitação (mm)</th>
                            <th>ETo (mm)</th>
                            <th>Balanço Hídrico (mm)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {annual_rows}
                    </tbody>
                </table>

                {charts_html}
                """
                # Anexar seção climática à seção de termos (Termos primeiro, depois Clima)
                terms_section = terms_section + climate_section

            map_image_path = output_path.replace('.html', '_map.png')
            self._export_map_layout(map_image_path, orientation, grid_interval, project_info)
            map_image_path = map_image_path.replace("\\", "/")

            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                template = Template(template_content)
                
                html = template.safe_substitute(
                    logo_path=logo_path,
                    owner=project_info.get("owner", "-"),
                    location=project_info.get("location", "-"),
                    power=project_info.get("power", "-"),
                    water=project_info.get("water", "-"),
                    sources=project_info.get("sources", "-"),
                    date_str=date_str,
                    total_area=results.get("total_area", "-"),
                    total_sectors=results.get("total_sectors", "-"),
                    operating_flow=results.get("operating_flow", "-"),
                    total_time=results.get("total_time", "-"),
                    terms_section=terms_section,
                    parts_rows=parts_rows,
                    total_parts=self._fmt_num(total_parts),
                    services_rows=services_rows,
                    total_services=self._fmt_num(total_services),
                    grand_total=self._fmt_num(grand_total),
                    map_image_path=map_image_path
                )
            else:
                return "Erro: Template do relatório não encontrado."

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return f"Relatório salvo em:\n{output_path}"
            
        except Exception as e:
            return f"Erro ao gerar relatório: {str(e)}"

    def export_to_csv(self, parts: List[Dict], services: List[Dict], output_path: str) -> str:
        """Exports parts and services to a CSV file."""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # Header Parts
                writer.writerow(["TIPO", "NOME", "QUANTIDADE", "CUSTO UNIT.", "MARGEM (%)", "VALOR UNIT.", "VALOR TOTAL"])
                
                for part in parts:
                    cost = float(part['cost'])
                    profit = float(part['profit_margin'])
                    unit_val = cost * (1 + profit / 100)
                    total = unit_val * float(part['quantity'])
                    
                    writer.writerow([
                        "MATERIAL",
                        part['name'],
                        str(part['quantity']).replace('.', ','),
                        str(cost).replace('.', ','),
                        str(profit).replace('.', ','),
                        str(unit_val).replace('.', ','),
                        str(total).replace('.', ',')
                    ])
                    
                # Header Services
                writer.writerow([])
                writer.writerow(["TIPO", "NOME", "QUANTIDADE", "CUSTO UNIT.", "", "", "VALOR TOTAL"])
                
                for serv in services:
                    cost = float(serv['cost'])
                    total = cost * float(serv['quantity'])
                    
                    writer.writerow([
                        "SERVICO",
                        serv['name'],
                        str(serv['quantity']).replace('.', ','),
                        str(cost).replace('.', ','),
                        "", "",
                        str(total).replace('.', ',')
                    ])
                    
            return f"Exportação CSV concluída: {output_path}"
        except Exception as e:
            return f"Erro na exportação CSV: {str(e)}"

