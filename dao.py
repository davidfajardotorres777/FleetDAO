import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import io
from minio import Minio
from minio.error import S3Error
import redis
import json

from config_vars import (
    MONGO_URI, DB_NAME, MINIO_ENDPOINT, MINIO_ACCESS_KEY, 
    MINIO_SECRET_KEY, MINIO_SECURE, REDIS_URL
)
from db_models.trucks import Truck
from db_models.drivers import Driver
from db_models.routes import Route
from db_models.telemetry import Telemetry
from db_models.geofence import Geofence

# Configuración básica para el registro de logs del sistema
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")

class FleetDAO:
    """DAO central del sistema: centraliza el acceso a MongoDB, Redis y MinIO."""

    def __init__(self):
        """Abre las conexiones a MongoDB, Redis y MinIO al instanciar el DAO."""
        try:
            self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self._db = self._client[DB_NAME]

            self._trucks = self._db["trucks"]
            self._drivers = self._db["drivers"]
            self._routes = self._db["routes"]
            self._telemetry = self._db["telemetry"]
            self._geofences = self._db["geofences"]
            
            # Redis para caché ultrarrápida
            try:
                self._redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            except Exception as e:
                logger.warning(f"No se pudo conectar a Redis: {e}")
                self._redis = None
            
            # Inicializar MinIO Client
            self._minio_client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            
            logger.info("Conexión exitosa a MongoDB, Redis y MinIO.")
        except PyMongoError as e:
            logger.error(f"No se pudo conectar a MongoDB: {e}")
            raise

    def close(self):
        """Cierra la conexión activa con el clúster de MongoDB y Redis."""
        self._client.close()
        if getattr(self, '_redis', None):
            self._redis.close()
        logger.info("Conexión a MongoDB cerrada de manera segura.")

    # --- Trucks ---
    def add_truck(self, truck: Truck) -> str:
        """Guarda un camión nuevo en MongoDB."""
        try:
            res = self._trucks.insert_one(truck.to_dict())
            logger.info(f"Camión insertado con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando camión: {e}")
            raise

    def get_trucks(self, *, truck_id=None, brand=None) -> list[dict]:
        """Obtiene camiones, con filtros opcionales por ID o marca."""
        try:
            query = {}
            if truck_id:
                query["_id"] = ObjectId(truck_id) if isinstance(truck_id, str) else truck_id
            if brand:
                query["brand"] = brand
            return list(self._trucks.find(query))
        except PyMongoError as e:
            logger.error(f"Error obteniendo camiones: {e}")
            return []

    def update_truck(self, *, truck_id: str, update_data: dict) -> bool:
        """Actualiza los campos de un camión existente."""
        try:
            res = self._trucks.update_one({"_id": ObjectId(truck_id)}, {"$set": update_data})
            return res.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error actualizando camión {truck_id}: {e}")
            raise

    def delete_truck(self, *, truck_id: str) -> bool:
        """Elimina un camión por su ID."""
        try:
            res = self._trucks.delete_one({"_id": ObjectId(truck_id)})
            return res.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error eliminando camión {truck_id}: {e}")
            raise

    # --- Drivers ---
    def add_driver(self, driver: Driver) -> str:
        """Guarda un chofer nuevo en MongoDB."""
        try:
            res = self._drivers.insert_one(driver.to_dict())
            logger.info(f"Conductor insertado con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando conductor: {e}")
            raise

    def get_drivers(self, *, driver_id=None, name=None, license_level=None) -> list[dict]:
        """Busca choferes, con filtros opcionales por ID, nombre o tipo de licencia."""
        try:
            query = {}
            if driver_id:
                query["_id"] = ObjectId(driver_id) if isinstance(driver_id, str) else driver_id
            if name:
                query["name"] = name
            if license_level:
                query["license_level"] = license_level
            return list(self._drivers.find(query))
        except PyMongoError as e:
            logger.error(f"Error obteniendo conductores: {e}")
            return []
            
    def update_driver_license_url(self, *, driver_id: str, license_url: str):
        """Actualiza la URL de la licencia física del conductor subida a MinIO."""
        try:
            res = self._drivers.update_one(
                {"_id": ObjectId(driver_id)},
                {"$set": {"license_url": license_url}}
            )
            if res.modified_count > 0:
                logger.info(f"URL de licencia actualizada para el chofer: {driver_id}")
        except PyMongoError as e:
            logger.error(f"Error actualizando licencia del conductor: {e}")
            raise

    def update_driver(self, *, driver_id: str, update_data: dict) -> bool:
        """Actualiza los campos de un chofer existente."""
        try:
            res = self._drivers.update_one({"_id": ObjectId(driver_id)}, {"$set": update_data})
            return res.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error actualizando chofer {driver_id}: {e}")
            raise

    def delete_driver(self, *, driver_id: str) -> bool:
        """Elimina un chofer por su ID."""
        try:
            res = self._drivers.delete_one({"_id": ObjectId(driver_id)})
            return res.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error eliminando chofer {driver_id}: {e}")
            raise

    # --- Routes ---
    def add_route(self, route: Route) -> str:
        """Asigna una ruta nueva a un camión y un chofer, validando que ambos existan."""
        try:
            if not self._trucks.find_one({"_id": ObjectId(route.truck_id)}):
                raise ValueError(f"No existe un camión con ID {route.truck_id}")
            if not self._drivers.find_one({"_id": ObjectId(route.driver_id)}):
                raise ValueError(f"No existe un chofer con ID {route.driver_id}")

            res = self._routes.insert_one(route.to_dict())
            logger.info(f"Ruta insertada con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando ruta: {e}")
            raise

    def get_routes(self, *, route_id=None, truck_id=None, driver_id=None) -> list[dict]:
        """Busca rutas, con filtros opcionales por ID, camión o chofer."""
        try:
            query = {}
            if route_id:
                query["_id"] = ObjectId(route_id) if isinstance(route_id, str) else route_id
            if truck_id:
                query["truck_id"] = truck_id
            if driver_id:
                query["driver_id"] = driver_id
            return list(self._routes.find(query))
        except PyMongoError as e:
            logger.error(f"Error obteniendo rutas: {e}")
            return []

    def update_route(self, *, route_id: str, update_data: dict) -> bool:
        """Actualiza los campos de una ruta existente."""
        try:
            res = self._routes.update_one({"_id": ObjectId(route_id)}, {"$set": update_data})
            return res.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error actualizando ruta {route_id}: {e}")
            raise

    def delete_route(self, *, route_id: str) -> bool:
        """Elimina una ruta por su ID."""
        try:
            res = self._routes.delete_one({"_id": ObjectId(route_id)})
            return res.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error eliminando ruta {route_id}: {e}")
            raise

    # --- Telemetry ---
    def add_telemetry(self, telemetry: Telemetry) -> str:
        """Guarda una lectura de telemetría. El índice único (truck_id + timestamp)
        evita duplicados si el camión reenvía el mismo dato."""
        try:
            data = telemetry.to_dict()
            res = self._telemetry.insert_one(data)
            
            # Guardar también en Redis para lectura O(1) de la última posición
            if self._redis:
                try:
                    cache_key = f"truck:{telemetry.truck_id}:last_telemetry"
                    self._redis.set(cache_key, json.dumps({
                        "speed_kmh": telemetry.speed_kmh,
                        "engine_rpm": telemetry.engine_rpm,
                        "engine_temp_c": telemetry.engine_temp_c,
                        "fuel_level_pct": telemetry.fuel_level_pct,
                        "lon": telemetry.lon,
                        "lat": telemetry.lat,
                        "timestamp": telemetry.timestamp.isoformat()
                    }))
                except Exception as e:
                    logger.warning(f"Error guardando caché en Redis: {e}")

            return str(res.inserted_id)
        except DuplicateKeyError:
            logger.warning(f"Evento de telemetría duplicado descartado para el camión {telemetry.truck_id}")
            raise
        except PyMongoError as e:
            logger.error(f"Error insertando evento de telemetría: {e}")
            raise

    def get_telemetry(self, truck_id: str, desde=None, hasta=None) -> list[dict]:
        """Recupera la serie temporal de telemetría de un camión, opcionalmente
        acotada por un rango de fechas (desde/hasta)."""
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
            logger.error(f"Error obteniendo telemetría de MongoDB: {e}")
            return []

    def get_latest_telemetry_cache(self, *, truck_id: str) -> dict:
        """Obtiene la última posición conocida desde Redis en tiempo constante."""
        if not self._redis:
            return {}
        try:
            data = self._redis.get(f"truck:{truck_id}:last_telemetry")
            if data:
                return json.loads(data)
            return {}
        except Exception as e:
            logger.warning(f"Error leyendo caché de Redis: {e}")
            return {}

    def get_telemetry_near(self, truck_id: str, lon: float, lat: float, max_distance_meters: float) -> list[dict]:
        """Busca lecturas de telemetría dentro de un radio determinado de una coordenada
        (usa el índice geoespacial 2dsphere)."""
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
        """Calcula estadísticas (velocidad promedio, temp máxima, etc.) usando un
        pipeline de agregación de MongoDB."""
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
    def get_geofences(self) -> list[dict]:
        """Recupera todas las geocercas registradas para dibujarlas en el mapa."""
        try:
            return list(self._geofences.find({}))
        except PyMongoError as e:
            logger.error(f"Error obteniendo geocercas: {e}")
            return []

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
        """Recupera la telemetría de un camión que cae dentro de un polígono
        (geocerca), usando el operador $geoWithin de MongoDB."""
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

    # --- MinIO Storage ---
    def upload_file(self, *, bucket_name: str, object_name: str, file_data: bytes, content_type: str = "application/octet-stream") -> str:
        """Sube un archivo físico a MinIO y devuelve su URL pre-firmada."""
        try:
            if not self._minio_client.bucket_exists(bucket_name):
                self._minio_client.make_bucket(bucket_name)
            
            data_stream = io.BytesIO(file_data)
            self._minio_client.put_object(
                bucket_name, object_name, data_stream, len(file_data), content_type=content_type
            )
            logger.info(f"Archivo subido a MinIO: {bucket_name}/{object_name}")
            return self.get_file_url(bucket_name=bucket_name, object_name=object_name)
        except S3Error as e:
            logger.error(f"Error S3 en MinIO al subir archivo: {e}")
            raise
        except Exception as e:
            logger.error(f"Error general subiendo archivo a MinIO: {e}")
            raise

    def get_file_url(self, *, bucket_name: str, object_name: str) -> str:
        """Genera una URL pre-firmada válida por 7 días para acceder al archivo."""
        from datetime import timedelta
        return self._minio_client.presigned_get_object(bucket_name, object_name, expires=timedelta(days=7))
