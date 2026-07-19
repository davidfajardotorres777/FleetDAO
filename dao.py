import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError

from config_vars import MONGO_URI, DB_NAME
from db_models.trucks import Truck
from db_models.drivers import Driver
from db_models.routes import Route
from db_models.telemetry import Telemetry
from db_models.geofence import Geofence

# Configuración básica para el registro de logs del sistema
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")

class FleetDAO:
    """
    Data Access Object (DAO) para la gestión del sistema de telemetría FleetDAO.

    Proporciona una capa de abstracción para todas las interacciones con MongoDB,
    garantizando el correcto manejo de errores, la gestión de índices geoespaciales
    y temporales, y la ejecución de pipelines de agregación.
    """

    def __init__(self):
        """
        Inicializa la conexión con MongoDB y establece las referencias a las colecciones.
        Configura los índices necesarios para garantizar unicidad y búsquedas espaciales eficientes.
        """
        try:
            self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self._db = self._client[DB_NAME]

            self._trucks = self._db["trucks"]
            self._drivers = self._db["drivers"]
            self._routes = self._db["routes"]
            self._telemetry = self._db["telemetry"]
            self._geofences = self._db["geofences"]
            
            # Índice compuesto único para evitar duplicación de eventos de telemetría
            self._telemetry.create_index([("truck_id", 1), ("timestamp", 1)], unique=True)
            # Índice geoespacial 2dsphere para permitir operaciones $near y $geoWithin
            self._telemetry.create_index([("location", "2dsphere")])
            logger.info("Conexión exitosa a MongoDB e índices inicializados.")
        except PyMongoError as e:
            logger.error(f"Fallo crítico en la conexión a MongoDB: {e}")
            raise

    def close(self):
        """Cierra la conexión activa con el clúster de MongoDB."""
        self._client.close()
        logger.info("Conexión a MongoDB cerrada de manera segura.")

    # --- Trucks ---
    def add_truck(self, truck: Truck) -> str:
        """
        Inserta un nuevo camión en la base de datos.
        
        Args:
            truck (Truck): Entidad validada por Pydantic que representa el camión.
            
        Returns:
            str: El ObjectID generado por MongoDB.
        """
        try:
            res = self._trucks.insert_one(truck.to_dict())
            logger.info(f"Camión insertado con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando camión: {e}")
            raise

    def get_trucks(self) -> list[dict]:
        """Recupera la lista de todos los camiones registrados."""
        try:
            return list(self._trucks.find())
        except PyMongoError as e:
            logger.error(f"Error obteniendo camiones: {e}")
            return []

    # --- Drivers ---
    def add_driver(self, driver: Driver) -> str:
        """
        Inserta un nuevo conductor en el sistema.
        
        Args:
            driver (Driver): Modelo Pydantic validado.
        """
        try:
            res = self._drivers.insert_one(driver.to_dict())
            logger.info(f"Conductor insertado con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando conductor: {e}")
            raise

    def get_drivers(self) -> list[dict]:
        """Obtiene la nómina completa de conductores."""
        try:
            return list(self._drivers.find())
        except PyMongoError as e:
            logger.error(f"Error obteniendo conductores: {e}")
            return []

    # --- Routes ---
    def add_route(self, route: Route) -> str:
        """Asigna una nueva ruta logística a un camión y conductor específicos."""
        try:
            res = self._routes.insert_one(route.to_dict())
            logger.info(f"Ruta insertada con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando ruta: {e}")
            raise

    def get_routes(self) -> list[dict]:
        """Recupera el historial de rutas planificadas."""
        try:
            return list(self._routes.find())
        except PyMongoError as e:
            logger.error(f"Error obteniendo rutas: {e}")
            return []

    # --- Telemetry ---
    def add_telemetry(self, telemetry: Telemetry) -> str:
        """
        Registra una lectura de telemetría IoT del vehículo.
        Maneja silenciosamente colisiones de timestamp (DuplicateKeyError) para
        garantizar idempotencia si los sensores reintentan el envío.
        """
        try:
            res = self._telemetry.insert_one(telemetry.to_dict())
            return str(res.inserted_id)
        except DuplicateKeyError:
            logger.warning(f"Evento de telemetría duplicado descartado para el camión {telemetry.truck_id}")
            raise
        except PyMongoError as e:
            logger.error(f"Error insertando evento de telemetría: {e}")
            raise

    def get_telemetry(self, truck_id: str, desde=None, hasta=None) -> list[dict]:
        """
        Recupera la serie temporal de telemetría de un camión.
        
        Args:
            truck_id (str): Identificador del vehículo.
            desde (datetime, optional): Límite inferior de la ventana de tiempo.
            hasta (datetime, optional): Límite superior de la ventana de tiempo.
        """
        try:
            query = {"truck_id": truck_id}
            if desde or hasta:
                query["timestamp"] = {}
                if desde:
                    query["timestamp"]["$gte"] = desde
                if hasta:
                    query["timestamp"]["$lte"] = hasta
                    
            return list(self._telemetry.find(query).sort("timestamp", 1))
        except PyMongoError as e:
            logger.error(f"Error obteniendo telemetría temporal: {e}")
            return []

    def get_telemetry_near(self, truck_id: str, lon: float, lat: float, max_distance_meters: float) -> list[dict]:
        """
        Ejecuta una consulta espacial `$near` utilizando el índice `2dsphere`.
        Detecta si un camión emitió lecturas en un radio determinado de una coordenada.
        """
        try:
            query = {
                "truck_id": truck_id,
                "location": {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        },
                        "$maxDistance": max_distance_meters
                    }
                }
            }
            return list(self._telemetry.find(query))
        except PyMongoError as e:
            logger.error(f"Error en evaluación geoespacial por radio: {e}")
            return []

    def get_truck_statistics(self, truck_id: str) -> dict:
        """
        Delega el cálculo analítico al motor de base de datos utilizando MongoDB Aggregation Pipelines.
        Evita procesar grandes volúmenes de datos en la capa de aplicación.
        """
        try:
            pipeline = [
                {"$match": {"truck_id": truck_id}},
                {"$group": {
                    "_id": "$truck_id",
                    "velocidad_promedio": {"$avg": "$speed_kmh"},
                    "temp_maxima": {"$max": "$engine_temp_c"},
                    "combustible_promedio": {"$avg": "$fuel_level_pct"},
                    "total_lecturas": {"$sum": 1}
                }}
            ]
            result = list(self._telemetry.aggregate(pipeline))
            if result:
                return result[0]
            return {}
        except PyMongoError as e:
            logger.error(f"Error durante agregación estadística: {e}")
            return {}

    # --- Geofences ---
    def add_geofence(self, geofence: Geofence) -> str:
        """Registra un nuevo polígono espacial de autorización (Geocerca)."""
        try:
            res = self._geofences.insert_one(geofence.to_dict())
            logger.info(f"Geocerca espacial insertada con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando geocerca: {e}")
            raise

    def get_telemetry_in_polygon(self, truck_id: str, polygon: list[list[float]]) -> list[dict]:
        """
        Implementa validación de trayectoria contra límites espaciales utilizando `$geoWithin`.
        Recupera toda la telemetría del camión contenida exclusivamente dentro del polígono delimitado.
        """
        try:
            query = {
                "truck_id": truck_id,
                "location": {
                    "$geoWithin": {
                        "$geometry": {
                            "type": "Polygon",
                            "coordinates": [polygon]
                        }
                    }
                }
            }
            return list(self._telemetry.find(query))
        except PyMongoError as e:
            logger.error(f"Error procesando límites de geocerca por polígono: {e}")
            return []
