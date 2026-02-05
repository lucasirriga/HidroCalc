import json
import os
import shutil
from qgis.core import QgsMessageLog, Qgis, QgsApplication

class PartManager:
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        # Use QGIS user profile directory for persistence
        self.user_dir = os.path.join(QgsApplication.qgisSettingsDirPath(), 'HidroCalc')
        if not os.path.exists(self.user_dir):
            os.makedirs(self.user_dir)
            
        self.parts_file = os.path.join(self.user_dir, 'parts.json')
        self.old_parts_file = os.path.join(plugin_dir, 'parts.json')
        
        self.parts = []
        self.migrate_data()
        self.load_parts()

    def migrate_data(self):
        """Migrate data from plugin dir to user dir if needed."""
        if os.path.exists(self.old_parts_file) and not os.path.exists(self.parts_file):
            try:
                shutil.move(self.old_parts_file, self.parts_file)
                QgsMessageLog.logMessage("Migrated parts.json to user profile directory.", "HidroCalc", Qgis.Info)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error migrating parts.json: {str(e)}", "HidroCalc", Qgis.Warning)

    def load_parts(self):
        """Load parts from the JSON file."""
        if os.path.exists(self.parts_file):
            try:
                with open(self.parts_file, 'r', encoding='utf-8') as f:
                    self.parts = json.load(f)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error loading parts: {str(e)}", "HidroCalc", Qgis.Critical)
                self.parts = []
        else:
            self.parts = []

    def save_parts(self):
        """Save parts to the JSON file."""
        try:
            with open(self.parts_file, 'w', encoding='utf-8') as f:
                json.dump(self.parts, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error saving parts: {str(e)}", "HidroCalc", Qgis.Critical)

    def add_part(self, name, cost, profit_margin):
        """Add a new part and save."""
        part = {
            'name': name,
            'cost': float(cost),
            'profit_margin': float(profit_margin)
        }
        self.parts.append(part)
        self.save_parts()

    def update_part(self, index, name, cost, profit_margin):
        """Update an existing part and save."""
        if 0 <= index < len(self.parts):
            self.parts[index] = {
                'name': name,
                'cost': float(cost),
                'profit_margin': float(profit_margin)
            }
            self.save_parts()

    def get_parts(self):
        """Return the list of parts."""
        return self.parts
