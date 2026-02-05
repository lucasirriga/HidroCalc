import json
import os
from qgis.core import QgsMessageLog, Qgis, QgsProject

class ProjectPartsManager:
    def __init__(self):
        self.project_parts = []
        self.project_dir = None
        self.parts_file = None
        self.update_paths()

    def update_paths(self):
        """Update paths based on current project."""
        project_path = QgsProject.instance().fileName()
        if project_path:
            self.project_dir = os.path.dirname(project_path)
            self.parts_file = os.path.join(self.project_dir, 'project_parts.json')
            self.load_parts()
        else:
            self.project_dir = None
            self.parts_file = None
            self.project_parts = []

    def load_parts(self):
        """Load parts from the JSON file."""
        if self.parts_file and os.path.exists(self.parts_file):
            try:
                with open(self.parts_file, 'r', encoding='utf-8') as f:
                    self.project_parts = json.load(f)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error loading project parts: {str(e)}", "HidroCalc", Qgis.Critical)
                self.project_parts = []
        else:
            self.project_parts = []

    def save_parts(self):
        """Save parts to the JSON file."""
        if self.parts_file:
            try:
                with open(self.parts_file, 'w', encoding='utf-8') as f:
                    json.dump(self.project_parts, f, indent=4, ensure_ascii=False)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error saving project parts: {str(e)}", "HidroCalc", Qgis.Critical)

    def add_part(self, part_data, quantity):
        """Add a part to the project list."""
        if not self.parts_file:
            return False
            
        # Check if part already exists to update quantity? 
        # Or just add as new entry? Let's add as new entry for now, or aggregate.
        # Aggregating is better.
        
        found = False
        for p in self.project_parts:
            if p['name'] == part_data['name']:
                p['quantity'] += float(quantity)
                # Update cost/profit in case they changed in the global list?
                # Usually project parts snapshot the cost at time of addition, 
                # but if we aggregate, we might want to keep the latest or average?
                # Simpler: Just update quantity and keep original unit values, OR update values to current.
                # Let's update values to current global values to keep consistency if the user updated the global price.
                p['cost'] = float(part_data['cost'])
                p['profit_margin'] = float(part_data['profit_margin'])
                found = True
                break
        
        if not found:
            new_part = {
                'name': part_data['name'],
                'cost': float(part_data['cost']),
                'profit_margin': float(part_data['profit_margin']),
                'quantity': float(quantity)
            }
            self.project_parts.append(new_part)
            
        self.save_parts()
        return True

    def get_parts(self):
        """Return the list of project parts."""
        # Reload to ensure sync if file changed externally? Not needed for now.
        return self.project_parts

    def clear_parts(self):
        self.project_parts = []
        self.save_parts()

    def remove_part(self, index):
        if 0 <= index < len(self.project_parts):
            del self.project_parts[index]
            self.save_parts()

    def update_prices_from_global(self, global_parts):
        """Update prices of project parts based on global parts list."""
        count = 0
        # Create a dictionary for faster lookup
        global_map = {p['name']: p for p in global_parts}
        
        for part in self.project_parts:
            name = part['name']
            if name in global_map:
                global_part = global_map[name]
                # Check if values changed
                if (part['cost'] != global_part['cost'] or 
                    part['profit_margin'] != global_part['profit_margin']):
                    
                    part['cost'] = global_part['cost']
                    part['profit_margin'] = global_part['profit_margin']
                    count += 1
        
        if count > 0:
            self.save_parts()
            
        return count

    def update_part(self, index, quantity=None, unit_price=None):
        """Update a project part's quantity or unit price."""
        if 0 <= index < len(self.project_parts):
            part = self.project_parts[index]
            
            if quantity is not None:
                part['quantity'] = float(quantity)
            
            if unit_price is not None:
                # Adjust cost to match new unit price, keeping profit margin fixed
                # unit_price = cost * (1 + profit/100)
                # cost = unit_price / (1 + profit/100)
                profit = part['profit_margin']
                try:
                    new_cost = float(unit_price) / (1 + profit / 100)
                    part['cost'] = new_cost
                except ZeroDivisionError:
                    pass # Should not happen with positive profit
            
            self.save_parts()
