import pytest
from unittest.mock import MagicMock
import sys

# Mock QGIS modules if not running inside QGIS
try:
    import qgis.core
except ImportError:
    # Create mock modules
    sys.modules['qgis'] = MagicMock()
    sys.modules['qgis.core'] = MagicMock()
    sys.modules['qgis.gui'] = MagicMock()
    sys.modules['qgis.PyQt'] = MagicMock()
    sys.modules['qgis.PyQt.QtCore'] = MagicMock()
    sys.modules['qgis.PyQt.QtWidgets'] = MagicMock()

@pytest.fixture
def mock_iface():
    """Returns a mock QGIS interface."""
    iface = MagicMock()
    iface.mainWindow.return_value = MagicMock()
    return iface

@pytest.fixture
def mock_project():
    """Returns a mock QgsProject."""
    project = MagicMock()
    return project
