from qgis.core import (
    QgsProject, QgsUnitTypes, QgsPrintLayout, QgsLayoutItemMap, 
    QgsLayoutSize, QgsLayoutPoint, QgsLayoutItemPage, QgsLayoutExporter, 
    QgsLayoutItemMapGrid, QgsLineSymbol, QgsLayoutItemPicture, 
    QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutMeasurement,
    QgsLayoutItemShape, QgsFillSymbol, QgsLegendStyle, QgsLayoutItem
)
from qgis.PyQt.QtGui import QFont
import os

class MapLayoutManager:
    def __init__(self, iface):
        self.iface = iface
        self.project = QgsProject.instance()
        self.layout = None
        self.page_width = 210
        self.page_height = 297
        self.margin = 5
        self.work_width = self.page_width - (2 * self.margin)
        self.work_height = self.page_height - (2 * self.margin)
        
    def _fmt_num(self, value):
        """Formats a number to Brazilian standard (1.000,00)."""
        try:
            return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return str(value)

    def create_layout(self, layout_name="HidroCalc Layout"):
        """Initializes a new print layout."""
        self.layout = QgsPrintLayout(self.project)
        self.layout.initializeDefaults()
        self.layout.setName(layout_name)
        return self.layout

    def setup_page(self, orientation="Retrato"):
        """Configures page size and orientation."""
        pc = self.layout.pageCollection()
        page = pc.page(0)
        
        if orientation == "Paisagem":
            page.setPageSize('A4', QgsLayoutItemPage.Orientation.Landscape)
            # Swap dimensions for calculation logic if needed, 
            # but the logic below assumes Portrait A4 base and rotates items.
            # If the user meant the PAGE is landscape, we should swap width/height variables.
            # However, the original code kept page portrait and rotated items for "Paisagem" map?
            # Let's check original code:
            # page.setPageSize('A4', QgsLayoutItemPage.Orientation.Portrait)
            # if orientation == "Paisagem": map_item.setMapRotation(90)
            # So the PAGE stays Portrait, but the MAP is rotated.
            # I will keep this behavior for consistency unless "setup_page" implies changing the paper.
            # The original code explicitly set Portrait.
            pass
            
        page.setPageSize('A4', QgsLayoutItemPage.Orientation.Portrait)
        
    def add_map_item(self, map_height, orientation="Retrato", grid_interval=50.0):
        """Adds the map item to the layout."""
        map_item = QgsLayoutItemMap(self.layout)
        map_item.setRect(self.margin, self.margin, self.work_width, map_height)
        map_item.setExtent(self.iface.mapCanvas().extent())
        self.layout.addLayoutItem(map_item)
        
        map_item.attemptMove(QgsLayoutPoint(self.margin, self.margin, QgsUnitTypes.LayoutMillimeters))
        map_item.attemptResize(QgsLayoutSize(self.work_width, map_height, QgsUnitTypes.LayoutMillimeters))
        
        if orientation == "Paisagem":
            map_item.setMapRotation(90)
        
        map_item.zoomToExtent(self.iface.mapCanvas().extent())
        
        # Grid
        grid = QgsLayoutItemMapGrid("Grid 1", map_item)
        map_item.grids().addGrid(grid)
        grid.setStyle(QgsLayoutItemMapGrid.Solid)
        grid.setAnnotationEnabled(True)
        grid.setFrameStyle(QgsLayoutItemMapGrid.LineBorder)
        grid.setFrameWidth(0.3)
        grid.setAnnotationFormat(QgsLayoutItemMapGrid.Decimal)
        grid.setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal, QgsLayoutItemMapGrid.Top)
        grid.setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal, QgsLayoutItemMapGrid.Bottom)
        grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Left)
        grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Right)
        grid.setAnnotationFont(QFont("Arial", 6))
        grid.setIntervalX(grid_interval)
        grid.setIntervalY(grid_interval)
        grid.setLineSymbol(QgsLineSymbol.createSimple({'line_style': 'no'}))
        
        return map_item

    def add_info_box_frame(self, box_x, box_y, box_width, box_height):
        """Adds the frame for the info box."""
        box_frame = QgsLayoutItemShape(self.layout)
        box_frame.setShapeType(QgsLayoutItemShape.Rectangle)
        box_frame.setRect(0, 0, box_width, box_height)
        self.layout.addLayoutItem(box_frame)
        box_frame.attemptMove(QgsLayoutPoint(box_x, box_y, QgsUnitTypes.LayoutMillimeters))
        box_frame.attemptResize(QgsLayoutSize(box_width, box_height, QgsUnitTypes.LayoutMillimeters))
        box_frame.setFrameEnabled(True)
        box_frame.setFrameStrokeWidth(QgsLayoutMeasurement(0.3))
        symbol = QgsFillSymbol.createSimple({'color': 'transparent', 'outline_width': '0.3', 'outline_color': 'black'})
        box_frame.setSymbol(symbol)
        return box_frame

    def add_logo(self, box_rect, align="Right", offset=0, padding=0):
        """Adds the logo to the layout with relative positioning."""
        box_x, box_y, box_width, box_height = box_rect
        
        logo_visual_width = 70
        logo_visual_height = 20
        
        base_dir = os.path.dirname(__file__)
        logo_path = os.path.join(base_dir, "logo_tocantins.png")
        
        if os.path.exists(logo_path):
            logo = QgsLayoutItemPicture(self.layout)
            logo.setPicturePath(logo_path)
            self.layout.addLayoutItem(logo)
            logo.setItemRotation(90)
            logo.attemptResize(QgsLayoutSize(logo_visual_width, logo_visual_height, QgsUnitTypes.LayoutMillimeters))
            logo.setResizeMode(QgsLayoutItemPicture.Zoom)
            
            # Rotated 90 deg: Width on page is logo_visual_height, Height on page is logo_visual_width
            visual_w_on_page = logo_visual_height
            visual_h_on_page = logo_visual_width
            
            # Calculate Center
            cy = box_y + (box_height / 2)
            
            if align == "Right":
                # Right edge = box_x + box_width - padding - offset
                # Center X = Right edge - (visual_w / 2)
                right_edge = box_x + box_width - padding - offset
                cx = right_edge - (visual_w_on_page / 2)
            else:
                # Left edge = box_x + padding + offset
                # Center X = Left edge + (visual_w / 2)
                left_edge = box_x + padding + offset
                cx = left_edge + (visual_w_on_page / 2)
            
            logo.setReferencePoint(QgsLayoutItem.ReferencePoint.Middle)
            logo.attemptMove(QgsLayoutPoint(cx, cy, QgsUnitTypes.LayoutMillimeters))
            
            return visual_w_on_page
        return 0

    def add_project_info(self, box_rect, project_info, align="Right", offset=0, padding=0):
        """Adds project info text with relative positioning."""
        box_x, box_y, box_width, box_height = box_rect
        
        info_visual_width = 120
        info_visual_height = 60
        # Rotated 90: Width on Page = 50, Height on Page = 70
        visual_w_on_page = info_visual_height
        visual_h_on_page = info_visual_width
        
        if project_info:
            try:
                op_flow = float(str(project_info.get("results", {}).get("operating_flow", "0")).replace(',', '.'))
                total_time = float(str(project_info.get("results", {}).get("total_time", "0")).replace(',', '.'))
                daily_flow = op_flow * total_time
            except:
                daily_flow = 0.0
            
            info_html = f"""
            <div style="font-family: Arial; font-size: 11pt; color: #333;">
                <div style="font-weight: bold; border-bottom: 1px solid #2E7D32; margin-bottom: 2px; color: #2E7D32;">Informações Agronômicas</div>
                <b></b><br>
                <b>Setores:</b> {project_info.get("results", {}).get("total_sectors", "-")}<br>
                <b>Área Total:</b> {project_info.get("results", {}).get("total_area", "-")} ha<br>
                <b>Simultâneos:</b> {project_info.get("simultaneous", "-")}<br>
                <b>Vazão Func.:</b> {project_info.get("results", {}).get("operating_flow", "-")} m³/h<br>
                <b>Vazão Diária:</b> {self._fmt_num(daily_flow)} m³/dia<br>
                <b>Tempo Irrig.:</b> {project_info.get("results", {}).get("total_time", "-")} h
            </div>
            """
            
            lbl_info = QgsLayoutItemLabel(self.layout)
            lbl_info.setText(info_html)
            lbl_info.setMode(QgsLayoutItemLabel.ModeHtml)
            self.layout.addLayoutItem(lbl_info)
            lbl_info.setItemRotation(90)
            lbl_info.attemptResize(QgsLayoutSize(info_visual_width, info_visual_height, QgsUnitTypes.LayoutMillimeters))
            
            cy = box_y + (box_height)
            
            if align == "Right":
                right_edge = box_x + box_width - padding
                cx = right_edge - (visual_w_on_page / 2)
            else:
                left_edge = box_x + padding + offset
                cx = left_edge + (visual_w_on_page / 2)
            
            lbl_info.setReferencePoint(QgsLayoutItem.ReferencePoint.Middle)
            lbl_info.attemptMove(QgsLayoutPoint(cx, cy, QgsUnitTypes.LayoutMillimeters))
            
            return visual_w_on_page
        return 0

    def add_legend(self, box_rect, map_item, align="Right", offset=0, padding=0):
        """Adds the legend with relative positioning."""
        box_x, box_y, box_width, box_height = box_rect
        
        legend = QgsLayoutItemLegend(self.layout)
        legend.setTitle("Legendas")
        legend.setLinkedMap(map_item)
        legend.setLegendFilterByMapEnabled(True)
        self.layout.addLayoutItem(legend)
        
        for style in [QgsLegendStyle.Title, QgsLegendStyle.Group, QgsLegendStyle.Subgroup, QgsLegendStyle.SymbolLabel]:
            r = legend.style(style)
            f = r.font()
            if style == QgsLegendStyle.Title:
                f.setPointSizeF(f.pointSizeF() * 1.2)
            else:
                f.setPointSizeF(f.pointSizeF() * 0.8)
            r.setFont(f)
            legend.setStyle(style, r)
            
        legend.setItemRotation(90)
        
        # Estimate size
        est_visual_w = 30
        est_visual_h = 30
        # Rotated 90: Width on Page = 30, Height on Page = 60
        visual_w_on_page = est_visual_h
        visual_h_on_page = est_visual_w
        
        cy = box_y - est_visual_h + offset
        
        if align == "Right":
            right_edge = box_x + box_width - padding
            cx = right_edge - (visual_w_on_page / 2)
        else:
            left_edge = box_x + padding + offset
            cx = left_edge + (visual_w_on_page / 2)
        
        legend.setReferencePoint(QgsLayoutItem.ReferencePoint.Middle)
        legend.attemptMove(QgsLayoutPoint(cx, cy, QgsUnitTypes.LayoutMillimeters))
        
        return visual_w_on_page

    def add_north_arrow(self, box_rect, align="Right", offset=0, padding=0):
        """Adds the north arrow with relative positioning."""
        box_x, box_y, box_width, box_height = box_rect
        
        north_arrow = QgsLayoutItemPicture(self.layout)
        base_dir = os.path.dirname(__file__)
        arrow_path = os.path.join(base_dir, "icon_rose_wind.png")
        if os.path.exists(arrow_path):
            north_arrow.setPicturePath(arrow_path)
        else:
            north_arrow.setPicturePath("arrows/NorthArrow_02.svg")
        self.layout.addLayoutItem(north_arrow)
        north_arrow.setItemRotation(90)
        north_arrow.attemptResize(QgsLayoutSize(40, 40, QgsUnitTypes.LayoutMillimeters))
        
        visual_size = 40
        
        cy = box_y + (box_height / 2)
        
        if align == "Right":
            right_edge = box_x + box_width - padding - offset
            cx = right_edge - (visual_size / 2)
        else:
            left_edge = box_x + padding + offset
            cx = left_edge + (visual_size / 2)
        
        north_arrow.setReferencePoint(QgsLayoutItem.ReferencePoint.Middle)
        north_arrow.attemptMove(QgsLayoutPoint(cx, cy, QgsUnitTypes.LayoutMillimeters))
        
        return visual_size

    def export_layout(self, output_path, orientation="Retrato", grid_interval=150.0, project_info=None):
        """Main method to coordinate layout creation and export."""
        self.create_layout()
        self.setup_page(orientation)
        
        # Split: 75% Map (Top), 25% Info Box (Bottom)
        gap = 5
        map_height = (self.work_height * 0.75) - (gap / 2)
        box_height = (self.work_height * 0.25) - (gap / 2)
        
        # Map
        map_item = self.add_map_item(map_height, orientation, grid_interval)
        
        # Info Box
        box_y = self.margin + map_height + gap
        box_x = self.margin
        
        self.add_info_box_frame(box_x, box_y, self.work_width, box_height)
        
        box_rect = (box_x, box_y, self.work_width, box_height)
        
        # --- Relative Positioning ---
        
        # 1. Logo (Right)
        logo_w = self.add_logo(box_rect, align="Right", padding=0)
        
        # 2. Info (Right, Left of Logo)
        # Offset = Logo Width + Gap
        info_w = self.add_project_info(box_rect, project_info, align="Right", offset=1, padding=25)
        
        # 3. North Arrow (Left)
        north_w = self.add_north_arrow(box_rect, align="Right", offset=1, padding=150)
        
        # 4. Legend (Left, Right of North Arrow)
        # Offset = North Width + Gap (10)
        self.add_legend(box_rect, map_item, align="Right", offset=9, padding=70)
        
        # Export
        exporter = QgsLayoutExporter(self.layout)
        exporter.exportToImage(output_path, QgsLayoutExporter.ImageExportSettings())
