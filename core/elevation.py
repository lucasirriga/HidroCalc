from qgis.core import (
    QgsRasterLayer, QgsPointXY, QgsCoordinateTransform, QgsProject, QgsCoordinateReferenceSystem
)

class ElevationManager:
    def __init__(self):
        pass

    def get_dem_layer(self):
        """Finds the first raster layer in the project that looks like a DEM."""
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer):
                # Simple heuristic: name contains 'dem', 'mdt', 'elevation' or just take the first one
                name = layer.name().lower()
                if any(x in name for x in ['dem', 'mdt', 'elevation', 'cota', 'altimetria']):
                    return layer
        return None

    def sample_elevation(self, point: QgsPointXY, dem_layer: QgsRasterLayer, source_crs: QgsCoordinateReferenceSystem) -> float:
        """
        Samples elevation at the given point.
        Handles CRS transformation if necessary.
        """
        if not dem_layer or not dem_layer.isValid():
            return 0.0
            
        # Transform point to DEM CRS
        if source_crs != dem_layer.crs():
            xform = QgsCoordinateTransform(source_crs, dem_layer.crs(), QgsProject.instance())
            pt_transformed = xform.transform(point)
        else:
            pt_transformed = point
            
        # Sample
        ident = dem_layer.dataProvider().identify(
            pt_transformed, 
            QgsRasterLayer.IdentifyFormatValue
        )
        
        if ident and ident.isValid():
            results = ident.results()
            if results:
                # Return the value of the first band
                val = list(results.values())[0]
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0.0
        
        return 0.0
