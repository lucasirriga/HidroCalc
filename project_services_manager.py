import json
import os
from qgis.core import QgsMessageLog, Qgis, QgsProject

class ProjectServicesManager:
    def __init__(self):
        self.project_services = []
        self.project_dir = None
        self.services_file = None
        self.update_paths()

    def update_paths(self):
        """Update paths based on current project."""
        project_path = QgsProject.instance().fileName()
        if project_path:
            self.project_dir = os.path.dirname(project_path)
            self.services_file = os.path.join(self.project_dir, 'project_services.json')
            self.load_services()
        else:
            self.project_dir = None
            self.services_file = None
            self.project_services = []

    def load_services(self):
        """Load services from the JSON file."""
        if self.services_file and os.path.exists(self.services_file):
            try:
                with open(self.services_file, 'r', encoding='utf-8') as f:
                    self.project_services = json.load(f)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error loading project services: {str(e)}", "HidroCalc", Qgis.Critical)
                self.project_services = []
        else:
            self.project_services = []

    def save_services(self):
        """Save services to the JSON file."""
        if self.services_file:
            try:
                with open(self.services_file, 'w', encoding='utf-8') as f:
                    json.dump(self.project_services, f, indent=4, ensure_ascii=False)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error saving project services: {str(e)}", "HidroCalc", Qgis.Critical)

    def add_service(self, service_data, quantity):
        """Add a service to the project list."""
        if not self.services_file:
            return False
            
        found = False
        for s in self.project_services:
            if s['name'] == service_data['name']:
                s['quantity'] += float(quantity)
                s['cost'] = float(service_data['cost']) # Update cost to current
                found = True
                break
        
        if not found:
            new_service = {
                'name': service_data['name'],
                'cost': float(service_data['cost']),
                'quantity': float(quantity)
            }
            self.project_services.append(new_service)
            
        self.save_services()
        return True

    def get_services(self):
        """Return the list of project services."""
        return self.project_services

    def remove_service(self, index):
        if 0 <= index < len(self.project_services):
            del self.project_services[index]
            self.save_services()

    def update_service(self, index, quantity=None, unit_price=None):
        """Update a project service's quantity or unit price."""
        if 0 <= index < len(self.project_services):
            service = self.project_services[index]
            
            if quantity is not None:
                service['quantity'] = float(quantity)
            
            if unit_price is not None:
                service['cost'] = float(unit_price)
            
            self.save_services()

    def update_prices_from_global(self, global_services):
        """Update prices of project services based on global services list."""
        count = 0
        # Create a dictionary for faster lookup
        global_map = {s['name']: s for s in global_services}
        
        for service in self.project_services:
            name = service['name']
            if name in global_map:
                global_service = global_map[name]
                # Check if values changed
                if service['cost'] != global_service['cost']:
                    service['cost'] = global_service['cost']
                    count += 1
        
        if count > 0:
            self.save_services()
            
        return count
