import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError

from config_vars import MONGO_URI, DB_NAME
from db_models.trucks import Truck
from db_models.drivers import Driver
from db_models.routes import Route
from db_models.telemetry import Telemetry

# Configuracion basica para ver errores
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")

class FleetDAO:
    # Clase para conectarse a MongoDB y hacer las consultas
    # Maneja los camiones, choferes y la telemetria
    def __init__(self):
        try:
            self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self._db = self._client[DB_NAME]

            self._trucks = self._db["trucks"]
            self._drivers = self._db["drivers"]
            self._routes = self._db["routes"]
            self._telemetry = self._db["telemetry"]
            
            # Create unique index for telemetry (truck_id, timestamp)
            self._telemetry.create_index([("truck_id", 1), ("timestamp", 1)], unique=True)
            # Create 2dsphere index for location
            self._telemetry.create_index([("location", "2dsphere")])
            logger.info("Se conecto bien a Mongo y se crearon los indices.")
        except PyMongoError as e:
            logger.error(f"Fallo la conexion a MongoDB: {e}")
            raise

    def close(self):
        self._client.close()
        logger.info("Conexión a MongoDB cerrada.")

    # --- Trucks ---
    def add_truck(self, truck: Truck) -> str:
        try:
            res = self._trucks.insert_one(truck.to_dict())
            logger.info(f"Camión insertado con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando camión: {e}")
            raise

    def get_trucks(self) -> list[dict]:
        try:
            return list(self._trucks.find())
        except PyMongoError as e:
            logger.error(f"Error obteniendo camiones: {e}")
            return []

    # --- Drivers ---
    def add_driver(self, driver: Driver) -> str:
        try:
            res = self._drivers.insert_one(driver.to_dict())
            logger.info(f"Conductor insertado con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando conductor: {e}")
            raise

    def get_drivers(self) -> list[dict]:
        try:
            return list(self._drivers.find())
        except PyMongoError as e:
            logger.error(f"Error obteniendo conductores: {e}")
            return []

    # --- Routes ---
    def add_route(self, route: Route) -> str:
        try:
            res = self._routes.insert_one(route.to_dict())
            logger.info(f"Ruta insertada con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando ruta: {e}")
            raise

    def get_routes(self) -> list[dict]:
        try:
            return list(self._routes.find())
        except PyMongoError as e:
            logger.error(f"Error obteniendo rutas: {e}")
            return []

    # --- Telemetry ---
    def add_telemetry(self, telemetry: Telemetry) -> str:
        try:
            res = self._telemetry.insert_one(telemetry.to_dict())
            return str(res.inserted_id)
        except DuplicateKeyError:
            logger.warning(f"Dato duplicado del camion {telemetry.truck_id}")
            raise
        except PyMongoError as e:
            logger.error(f"Error insertando telemetría: {e}")
            raise

    def get_telemetry(self, truck_id: str, desde=None, hasta=None) -> list[dict]:
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
            logger.error(f"Error obteniendo telemetría: {e}")
            return []

    def get_telemetry_near(self, truck_id: str, lon: float, lat: float, max_distance_meters: float) -> list[dict]:
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
            logger.error(f"Error en búsqueda geoespacial: {e}")
            return []

    def get_truck_statistics(self, truck_id: str) -> dict:
        # Agrupa los datos en la bd y saca el promedio de velocidad y gasolina
        # Asi evitamos procesar todo en python
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
            logger.error(f"Error en agregación estadística: {e}")
            return {}
