def classFactory(iface):
    from .plugin import HidroCalcPlugin
    return HidroCalcPlugin(iface)