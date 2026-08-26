import logging
from typing import List, Dict, Any, Optional, Union
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError

from config_vars import MONGO_URI, DB_NAME
from db_models.trucks import Truck, TruckUpdate
from db_models.drivers import Driver, DriverUpdate
from db_models.routes import Route, RouteUpdate
from db_models.telemetry import Telemetry, TelemetryUpdate
from db_models.geofence import Geofence, GeofenceUpdate

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")


class FleetDAO:
    """
    Data Access Object (DAO) para el sistema de gestión de flotas y telemetría FleetDAO.

    Proporciona una capa de abstracción para todas las operaciones CRUD (Crear, Leer,
    Modificar, Eliminar) en las colecciones de MongoDB:
      - trucks (Camiones)
      - drivers (Choferes)
      - routes (Rutas)
      - telemetry (Telemetría)
      - geofences (Geocercas)

    ¿CÓMO AGREGAR UNA NUEVA VARIABLE O MÉTODO A UNA ENTIDAD?
    -------------------------------------------------------
    1. Para agregar una variable a Truck (ej. 'year' o 'plate'):
       - Añádela en `db_models/trucks.py` dentro de la clase `Truck` (y en `TruckUpdate`).
       - Pydantic usará `ConfigDict(extra="allow")`, permitiendo variables arbitrarias.
       - En `update_truck`, cualquier variable enviada en el diccionario o modelo será
         guardada automáticamente en la base de datos con `$set`.

    2. Para agregar un nuevo método CRUD:
       - Agrega la función en esta clase usando los helpers `_to_object_id` y `_clean_doc`.
    """

    def __init__(self):
        """Inicializa la conexión con MongoDB y configura los índices necesarios."""
        try:
            self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self._db = self._client[DB_NAME]

            self._trucks = self._db["trucks"]
            self._drivers = self._db["drivers"]
            self._routes = self._db["routes"]
            self._telemetry = self._db["telemetry"]
            self._geofences = self._db["geofences"]

            # Índices de optimización
            self._telemetry.create_index([("truck_id", 1), ("timestamp", 1)], unique=True)
            self._telemetry.create_index([("location", "2dsphere")])
            logger.info("Conexión exitosa a MongoDB e índices configurados correctamente.")
        except PyMongoError as e:
            logger.error(f"Error crítico conectando a MongoDB: {e}")
            raise

    def close(self):
        """Cierra la conexión activa con MongoDB."""
        self._client.close()
        logger.info("Conexión a MongoDB cerrada.")

    # -------------------------------------------------------------------------
    # Métodos Auxiliares Internos (Normalización de ObjectId y Respuestas JSON)
    # -------------------------------------------------------------------------

    @staticmethod
    def _to_object_id(id_str: str) -> Optional[ObjectId]:
        """Convierte un string a ObjectId de MongoDB de forma segura."""
        if not id_str:
            return None
        if isinstance(id_str, ObjectId):
            return id_str
        try:
            return ObjectId(str(id_str))
        except (InvalidId, TypeError):
            logger.warning(f"ID inválido proporcionado: {id_str}")
            return None

    @staticmethod
    def _clean_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Limpia un documento de MongoDB convirtiendo `_id` a `str`
        para garantizar que sea totalmente serializable en JSON.
        """
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        doc["id"] = doc["_id"]
        return doc

    @classmethod
    def _clean_docs(cls, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aplica `_clean_doc` sobre una lista de documentos."""
        return [cls._clean_doc(d) for d in docs if d]

    # =========================================================================
    # 1. TRUCKS (Camiones) - CRUD COMPLETO
    # =========================================================================

    def add_truck(self, truck: Union[Truck, Dict[str, Any]]) -> str:
        """
        [CREATE] Registra un nuevo camión en el sistema.
        Acepta una instancia de `Truck` o un diccionario con las propiedades.
        """
        try:
            data = truck.to_dict() if isinstance(truck, Truck) else dict(truck)
            res = self._trucks.insert_one(data)
            logger.info(f"Camión insertado con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando camión: {e}")
            raise

    def get_trucks(self) -> List[Dict[str, Any]]:
        """[READ ALL] Obtiene la lista completa de camiones registrados."""
        try:
            cursor = self._trucks.find()
            return self._clean_docs(list(cursor))
        except PyMongoError as e:
            logger.error(f"Error obteniendo lista de camiones: {e}")
            return []

    def get_truck_by_id(self, truck_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene los datos de un camión específico por su ID."""
        try:
            oid = self._to_object_id(truck_id)
            if not oid:
                return None
            doc = self._trucks.find_one({"_id": oid})
            return self._clean_doc(doc)
        except PyMongoError as e:
            logger.error(f"Error buscando camión por ID {truck_id}: {e}")
            return None

    def update_truck(self, truck_id: str, update_data: Union[TruckUpdate, Dict[str, Any]]) -> bool:
        """
        [UPDATE / MODIFICAR] Actualiza cualquier campo o agrega nuevas variables a un camión.
        
        Permite enviar campos existentes (brand, capacity_tons) o cualquier variable
        nueva (ej: {"year": 2024, "license_plate": "AA123BB", "mi_variable_custom": "valor"}).
        """
        try:
            oid = self._to_object_id(truck_id)
            if not oid:
                return False

            if isinstance(update_data, TruckUpdate):
                payload = update_data.to_dict()
            elif isinstance(update_data, dict):
                payload = update_data.copy()
                payload.pop("_id", None)
                payload.pop("id", None)
            else:
                raise ValueError("Payload de actualización no válido")

            if not payload:
                return False

            res = self._trucks.update_one({"_id": oid}, {"$set": payload})
            modified = res.modified_count > 0 or res.matched_count > 0
            if modified:
                logger.info(f"Camión {truck_id} actualizado exitosamente.")
            return modified
        except PyMongoError as e:
            logger.error(f"Error actualizando camión {truck_id}: {e}")
            raise

    def add_variable_to_truck(self, truck_id: str, variable_name: str, value: Any) -> bool:
        """
        [AGREGAR VARIABLE PROPIA] Agrega una variable o propiedad nueva a un camión en el DAO.
        
        Ejemplo:
            dao.add_variable_to_truck(camion_id, "patente", "AA-123-ZZ")
            dao.add_variable_to_truck(camion_id, "color", "Azul")
        """
        return self.update_truck(truck_id, {variable_name: value})

    def modify_variable_truck(self, truck_id: str, variable_name: str, value: Any) -> bool:
        """
        [MODIFICAR VARIABLE] Modifica el valor de cualquier variable (existente o nueva) de un camión.
        
        Ejemplo:
            dao.modify_variable_truck(camion_id, "capacity_tons", 42.0)
            dao.modify_variable_truck(camion_id, "status", "maintenance")
        """
        return self.update_truck(truck_id, {variable_name: value})

    def set_truck_variables(self, truck_id: str, **variables) -> bool:
        """
        [MODIFICAR / AGREGAR MÚLTIPLES VARIABLES POR KEYWORDS]
        
        Ejemplo:
            dao.set_truck_variables(camion_id, patente="AA-999-XX", anio=2026, estado="Activo")
        """
        return self.update_truck(truck_id, variables)

    def delete_variable_from_truck(self, truck_id: str, variable_name: str) -> bool:
        """
        [ELIMINAR VARIABLE] Elimina un campo o variable específica de un camión usando $unset.
        
        Ejemplo:
            dao.delete_variable_from_truck(camion_id, "variable_obsoleta")
        """
        try:
            oid = self._to_object_id(truck_id)
            if not oid:
                return False
            res = self._trucks.update_one({"_id": oid}, {"$unset": {variable_name: ""}})
            return res.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error eliminando variable {variable_name} del camión {truck_id}: {e}")
            raise


    def delete_truck(self, truck_id: str) -> bool:
        """[DELETE / ELIMINAR] Elimina un camión del sistema por su ID."""
        try:
            oid = self._to_object_id(truck_id)
            if not oid:
                return False
            res = self._trucks.delete_one({"_id": oid})
            deleted = res.deleted_count > 0
            if deleted:
                logger.info(f"Camión {truck_id} eliminado exitosamente.")
            return deleted
        except PyMongoError as e:
            logger.error(f"Error eliminando camión {truck_id}: {e}")
            raise

    # =========================================================================
    # 2. DRIVERS (Choferes) - CRUD COMPLETO
    # =========================================================================

    def add_driver(self, driver: Union[Driver, Dict[str, Any]]) -> str:
        """[CREATE] Registra un nuevo chofer."""
        try:
            data = driver.to_dict() if isinstance(driver, Driver) else dict(driver)
            res = self._drivers.insert_one(data)
            logger.info(f"Conductor insertado con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando conductor: {e}")
            raise

    def get_drivers(self) -> List[Dict[str, Any]]:
        """[READ ALL] Obtiene todos los conductores."""
        try:
            cursor = self._drivers.find()
            return self._clean_docs(list(cursor))
        except PyMongoError as e:
            logger.error(f"Error obteniendo conductores: {e}")
            return []

    def get_driver_by_id(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Busca un conductor por ID."""
        try:
            oid = self._to_object_id(driver_id)
            if not oid:
                return None
            doc = self._drivers.find_one({"_id": oid})
            return self._clean_doc(doc)
        except PyMongoError as e:
            logger.error(f"Error buscando conductor por ID {driver_id}: {e}")
            return None

    def update_driver(self, driver_id: str, update_data: Union[DriverUpdate, Dict[str, Any]]) -> bool:
        """[UPDATE] Actualiza variables de un conductor."""
        try:
            oid = self._to_object_id(driver_id)
            if not oid:
                return False
            payload = update_data.to_dict() if isinstance(update_data, DriverUpdate) else dict(update_data)
            payload.pop("_id", None)
            payload.pop("id", None)
            if not payload:
                return False
            res = self._drivers.update_one({"_id": oid}, {"$set": payload})
            return res.modified_count > 0 or res.matched_count > 0
        except PyMongoError as e:
            logger.error(f"Error actualizando conductor {driver_id}: {e}")
            raise

    def delete_driver(self, driver_id: str) -> bool:
        """[DELETE] Elimina un conductor por ID."""
        try:
            oid = self._to_object_id(driver_id)
            if not oid:
                return False
            res = self._drivers.delete_one({"_id": oid})
            return res.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error eliminando conductor {driver_id}: {e}")
            raise

    # =========================================================================
    # 3. ROUTES (Rutas Logísticas) - CRUD COMPLETO
    # =========================================================================

    def add_route(self, route: Union[Route, Dict[str, Any]]) -> str:
        """[CREATE] Asigna una nueva ruta logística."""
        try:
            data = route.to_dict() if isinstance(route, Route) else dict(route)
            res = self._routes.insert_one(data)
            logger.info(f"Ruta insertada con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando ruta: {e}")
            raise

    def get_routes(self) -> List[Dict[str, Any]]:
        """[READ ALL] Recupera la lista de rutas."""
        try:
            cursor = self._routes.find()
            return self._clean_docs(list(cursor))
        except PyMongoError as e:
            logger.error(f"Error obteniendo rutas: {e}")
            return []

    def get_route_by_id(self, route_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una ruta por su ID."""
        try:
            oid = self._to_object_id(route_id)
            if not oid:
                return None
            doc = self._routes.find_one({"_id": oid})
            return self._clean_doc(doc)
        except PyMongoError as e:
            logger.error(f"Error buscando ruta por ID {route_id}: {e}")
            return None

    def update_route(self, route_id: str, update_data: Union[RouteUpdate, Dict[str, Any]]) -> bool:
        """[UPDATE] Modifica una ruta logística existente."""
        try:
            oid = self._to_object_id(route_id)
            if not oid:
                return False
            payload = update_data.to_dict() if isinstance(update_data, RouteUpdate) else dict(update_data)
            payload.pop("_id", None)
            payload.pop("id", None)
            if not payload:
                return False
            res = self._routes.update_one({"_id": oid}, {"$set": payload})
            return res.modified_count > 0 or res.matched_count > 0
        except PyMongoError as e:
            logger.error(f"Error actualizando ruta {route_id}: {e}")
            raise

    def delete_route(self, route_id: str) -> bool:
        """[DELETE] Elimina una ruta logística."""
        try:
            oid = self._to_object_id(route_id)
            if not oid:
                return False
            res = self._routes.delete_one({"_id": oid})
            return res.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error eliminando ruta {route_id}: {e}")
            raise

    # =========================================================================
    # 4. GEOFENCES (Geocercas Espaciales) - CRUD COMPLETO
    # =========================================================================

    def add_geofence(self, geofence: Union[Geofence, Dict[str, Any]]) -> str:
        """[CREATE] Registra una nueva geocerca espacial."""
        try:
            data = geofence.to_dict() if isinstance(geofence, Geofence) else dict(geofence)
            res = self._geofences.insert_one(data)
            logger.info(f"Geocerca insertada con ID: {res.inserted_id}")
            return str(res.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error insertando geocerca: {e}")
            raise

    def get_geofences(self) -> List[Dict[str, Any]]:
        """[READ ALL] Lista todas las geocercas registradas."""
        try:
            cursor = self._geofences.find()
            return self._clean_docs(list(cursor))
        except PyMongoError as e:
            logger.error(f"Error obteniendo geocercas: {e}")
            return []

    def get_geofence_by_id(self, geofence_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una geocerca por ID."""
        try:
            oid = self._to_object_id(geofence_id)
            if not oid:
                return None
            doc = self._geofences.find_one({"_id": oid})
            return self._clean_doc(doc)
        except PyMongoError as e:
            logger.error(f"Error buscando geocerca por ID {geofence_id}: {e}")
            return None

    def update_geofence(self, geofence_id: str, update_data: Union[GeofenceUpdate, Dict[str, Any]]) -> bool:
        """[UPDATE] Modifica una geocerca existente."""
        try:
            oid = self._to_object_id(geofence_id)
            if not oid:
                return False
            payload = update_data.to_dict() if isinstance(update_data, GeofenceUpdate) else dict(update_data)
            payload.pop("_id", None)
            payload.pop("id", None)
            if not payload:
                return False
            res = self._geofences.update_one({"_id": oid}, {"$set": payload})
            return res.modified_count > 0 or res.matched_count > 0
        except PyMongoError as e:
            logger.error(f"Error actualizando geocerca {geofence_id}: {e}")
            raise

    def delete_geofence(self, geofence_id: str) -> bool:
        """[DELETE] Elimina una geocerca por ID."""
        try:
            oid = self._to_object_id(geofence_id)
            if not oid:
                return False
            res = self._geofences.delete_one({"_id": oid})
            return res.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error eliminando geocerca {geofence_id}: {e}")
            raise

    # =========================================================================
    # 5. TELEMETRY (Lecturas IoT y Consultas Geoespaciales) - CRUD COMPLETO
    # =========================================================================

    def add_telemetry(self, telemetry: Union[Telemetry, Dict[str, Any]]) -> str:
        """
        [CREATE] Registra un evento de telemetría IoT.
        Maneja DuplicateKeyError si el sensor repite el envio en el mismo timestamp.
        """
        try:
            data = telemetry.to_dict() if isinstance(telemetry, Telemetry) else dict(telemetry)
            res = self._telemetry.insert_one(data)
            return str(res.inserted_id)
        except DuplicateKeyError:
            truck_id = getattr(telemetry, "truck_id", data.get("truck_id", "desconocido"))
            logger.warning(f"Evento de telemetría duplicado omitido para el camión {truck_id}")
            raise
        except PyMongoError as e:
            logger.error(f"Error insertando telemetría: {e}")
            raise

    def get_telemetry(self, truck_id: str, desde=None, hasta=None) -> List[Dict[str, Any]]:
        """[READ] Recupera la serie temporal de telemetría de un camión."""
        try:
            query = {"truck_id": truck_id}
            if desde or hasta:
                query["timestamp"] = {}
                if desde:
                    query["timestamp"]["$gte"] = desde
                if hasta:
                    query["timestamp"]["$lte"] = hasta

            cursor = self._telemetry.find(query).sort("timestamp", 1)
            return self._clean_docs(list(cursor))
        except PyMongoError as e:
            logger.error(f"Error obteniendo telemetría de {truck_id}: {e}")
            return []

    def get_telemetry_by_id(self, telemetry_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una lectura de telemetría por ID."""
        try:
            oid = self._to_object_id(telemetry_id)
            if not oid:
                return None
            doc = self._telemetry.find_one({"_id": oid})
            return self._clean_doc(doc)
        except PyMongoError as e:
            logger.error(f"Error buscando lectura de telemetría por ID {telemetry_id}: {e}")
            return None

    def update_telemetry(self, telemetry_id: str, update_data: Union[TelemetryUpdate, Dict[str, Any]]) -> bool:
        """[UPDATE] Modifica o agrega variables a un registro de telemetría."""
        try:
            oid = self._to_object_id(telemetry_id)
            if not oid:
                return False
            payload = update_data.to_dict() if isinstance(update_data, TelemetryUpdate) else dict(update_data)
            payload.pop("_id", None)
            payload.pop("id", None)
            if not payload:
                return False
            res = self._telemetry.update_one({"_id": oid}, {"$set": payload})
            return res.modified_count > 0 or res.matched_count > 0
        except PyMongoError as e:
            logger.error(f"Error actualizando telemetría {telemetry_id}: {e}")
            raise

    def delete_telemetry(self, telemetry_id: str) -> bool:
        """[DELETE] Elimina un registro de telemetría."""
        try:
            oid = self._to_object_id(telemetry_id)
            if not oid:
                return False
            res = self._telemetry.delete_one({"_id": oid})
            return res.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error eliminando telemetría {telemetry_id}: {e}")
            raise

    def get_telemetry_near(self, truck_id: str, lon: float, lat: float, max_distance_meters: float) -> List[Dict[str, Any]]:
        """Consulta espacial `$near` con índice `2dsphere`."""
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
            cursor = self._telemetry.find(query)
            return self._clean_docs(list(cursor))
        except PyMongoError as e:
            logger.error(f"Error en consulta $near para {truck_id}: {e}")
            return []

    def get_telemetry_in_polygon(self, truck_id: str, polygon: List[List[float]]) -> List[Dict[str, Any]]:
        """Consulta espacial `$geoWithin` para verificar presencia dentro de un polígono."""
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
            cursor = self._telemetry.find(query)
            return self._clean_docs(list(cursor))
        except PyMongoError as e:
            logger.error(f"Error en consulta $geoWithin para {truck_id}: {e}")
            return []

    def get_truck_statistics(self, truck_id: str) -> Dict[str, Any]:
        """Agregación analítica en MongoDB (velocidad promedio, temp máxima, etc.)."""
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
                doc = result[0]
                doc["_id"] = str(doc["_id"])
                return doc
            return {}
        except PyMongoError as e:
            logger.error(f"Error en agregación de estadísticas para {truck_id}: {e}")
            return {}
