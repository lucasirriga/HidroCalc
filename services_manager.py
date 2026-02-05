import json
import os
from qgis.core import QgsMessageLog, Qgis, QgsApplication

class ServiceManager:
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        # Use QGIS user profile directory for persistence
        self.user_dir = os.path.join(QgsApplication.qgisSettingsDirPath(), 'HidroCalc')
        if not os.path.exists(self.user_dir):
            os.makedirs(self.user_dir)
            
        self.services_file = os.path.join(self.user_dir, 'services.json')
        self.services = []
        self.load_services()

    def load_services(self):
        """Load services from the JSON file."""
        if os.path.exists(self.services_file):
            try:
                with open(self.services_file, 'r', encoding='utf-8') as f:
                    self.services = json.load(f)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error loading services: {str(e)}", "HidroCalc", Qgis.Critical)
                self.services = []
        else:
            self.services = []

    def save_services(self):
        """Save services to the JSON file."""
        try:
            with open(self.services_file, 'w', encoding='utf-8') as f:
                json.dump(self.services, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error saving services: {str(e)}", "HidroCalc", Qgis.Critical)

    def add_service(self, name, cost):
        """Add a new service and save."""
        service = {
            'name': name,
            'cost': float(cost)
        }
        self.services.append(service)
        self.save_services()

    def update_service(self, index, name, cost):
        """Update an existing service and save."""
        if 0 <= index < len(self.services):
            self.services[index] = {
                'name': name,
                'cost': float(cost)
            }
            self.save_services()

    def get_services(self):
        """Return the list of services."""
        return self.services
