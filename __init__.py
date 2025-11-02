

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Carrega a classe CalcularComprimento do módulo calcular_comprimento.
    :param iface: QgsInterface
    """
    from .calcular_comprimento import CalcularComprimento
    return CalcularComprimento(iface)