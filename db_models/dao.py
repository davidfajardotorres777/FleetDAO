# Wrapper de compatibilidad para permitir 'from db_models.dao import FleetDAO' como en SAVIA
class FleetDAO:
    """Clase proxy para instanciar la clase principal FleetDAO desde db_models.dao sin importaciones circulares."""
    def __new__(cls, *args, **kwargs):
        from dao import FleetDAO as RealFleetDAO
        return RealFleetDAO(*args, **kwargs)
