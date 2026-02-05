import sys
from unittest.mock import MagicMock

# Mock QGIS classes
class QgsPointXY:
    def __init__(self, x, y):
        self._x = x
        self._y = y
    def x(self): return self._x
    def y(self): return self._y
    def sqrDist(self, other):
        return (self._x - other.x())**2 + (self._y - other.y())**2

class QgsGeometry:
    @staticmethod
    def fromPolylineXY(points):
        return QgsGeometry(points)
        
    def __init__(self, points=None):
        self.points = points or []
        
    def length(self):
        # Simple Euclidean distance for line segments
        l = 0.0
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i+1]
            l += ((p1.x() - p2.x())**2 + (p1.y() - p2.y())**2)**0.5
        return l

# Create mock module structure
mock_qgis = MagicMock()
mock_qgis.core.QgsPointXY = QgsPointXY
mock_qgis.core.QgsGeometry = QgsGeometry
mock_qgis.PyQt.QtCore.QVariant = MagicMock()

sys.modules['qgis'] = mock_qgis
sys.modules['qgis.core'] = mock_qgis.core
sys.modules['qgis.PyQt'] = mock_qgis.PyQt
sys.modules['qgis.PyQt.QtCore'] = mock_qgis.PyQt.QtCore
