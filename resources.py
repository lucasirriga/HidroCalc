import os
from qgis.PyQt.QtGui import QIcon

class Resources:
    """Helper class to access plugin resources (icons)."""
    
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)

    def get_icon(self, name):
        """Returns a QIcon for the given name (without extension)."""
        path = os.path.join(self.base_dir, f"{name}.png")
        if os.path.exists(path):
            return QIcon(path)
        return QIcon()

# Global instance
resources = None

def init_resources():
    global resources
    resources = Resources()

def get_icon(name):
    if resources is None:
        init_resources()
    return resources.get_icon(name)
