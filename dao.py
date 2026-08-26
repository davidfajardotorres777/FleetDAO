import logging
from typing import List, Dict, Any, Optional, Union
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError

from config_vars import MONGO_URI, DB_NAME

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")


class FleetDAO:
    """
    Data Access Object (DAO) para el sistema de gestión de flotas y telemetría FleetDAO.

    Capa de acceso a datos directa, limpia y 100% autónoma sobre MongoDB.
    No requiere modelos externos ni clases adicionales: todo se gestiona directamente
    con diccionarios de Python o argumentos clave-valor (`kwargs`).

    ¿CÓMO AGREGAR O MODIFICAR CUALQUIER VARIABLE?
    ---------------------------------------------
    - Con kwargs: `dao.add_truck(brand="Volvo", capacity_tons=25.0, patente="AA123ZZ", mi_variable="valor")`
    - Modificar campos: `dao.update_truck(truck_id, capacity_tons=40.0, estado="activo", mi_variable="nuevo")`
    - Agregar variable individual: `dao.add_variable_to_truck(truck_id, "patente", "AA123ZZ")`
    - Eliminar variable: `dao.delete_variable_from_truck(truck_id, "variable_obsoleta")`

    Colecciones cubiertas:
      - trucks (Camiones)
      - drivers (Choferes)
      - routes (Rutas Logísticas)
      - telemetry (Telemetría IoT)
      - geofences (Geocercas Espaciales)
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

    # -------------------------------------------------------------------------
    # Métodos Auxiliares Genéricos de Manipulación de Variables por Colección
    # -------------------------------------------------------------------------

    def update_document(self, collection_name: str, doc_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[GENÉRICO UPDATE] Modifica campos o agrega variables a cualquier documento en cualquier colección."""
        try:
            oid = self._to_object_id(doc_id)
            if not oid:
                return False

            payload = {}
            if update_data and isinstance(update_data, dict):
                payload.update(update_data)
            if kwargs:
                payload.update(kwargs)

            payload.pop("_id", None)
            payload.pop("id", None)

            if not payload:
                return False

            res = self._db[collection_name].update_one({"_id": oid}, {"$set": payload})
            return res.modified_count > 0 or res.matched_count > 0
        except PyMongoError as e:
            logger.error(f"Error actualizando documento {doc_id} en colección {collection_name}: {e}")
            raise

    def add_variable(self, collection_name: str, doc_id: str, variable_name: str, value: Any) -> bool:
        """[GENÉRICO AGREGAR VARIABLE] Agrega una variable a cualquier colección."""
        return self.update_document(collection_name, doc_id, {variable_name: value})

    def modify_variable(self, collection_name: str, doc_id: str, variable_name: str, value: Any) -> bool:
        """[GENÉRICO MODIFICAR VARIABLE] Modifica una variable en cualquier colección."""
        return self.update_document(collection_name, doc_id, {variable_name: value})

    def set_variables(self, collection_name: str, doc_id: str, **variables) -> bool:
        """[GENÉRICO SET VARIABLES] Agrega/modifica múltiples variables usando kwargs en cualquier colección."""
        return self.update_document(collection_name, doc_id, variables)

    def delete_variable(self, collection_name: str, doc_id: str, variable_name: str) -> bool:
        """[GENÉRICO ELIMINAR VARIABLE] Elimina una variable usando $unset en cualquier colección."""
        try:
            oid = self._to_object_id(doc_id)
            if not oid:
                return False
            res = self._db[collection_name].update_one({"_id": oid}, {"$unset": {variable_name: ""}})
            return res.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error eliminando variable {variable_name} en {collection_name} ID {doc_id}: {e}")
            raise

    # =========================================================================
    # 1. TRUCKS (Camiones) - CRUD COMPLETO
    # =========================================================================

    def add_truck(self, truck_data: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """
        [CREATE] Registra un nuevo camión.
        
        Ejemplos:
          dao.add_truck(brand="Volvo", capacity_tons=25.0, patente="AA123ZZ")
          dao.add_truck({"brand": "Scania", "capacity_tons": 30.0})
        """
        try:
            data = dict(truck_data) if isinstance(truck_data, dict) else {}
            if kwargs:
                data.update(kwargs)

            if not data:
                raise ValueError("Debe proporcionar los datos del camión")

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

    def update_truck(self, truck_id: str, update_data: Optional[Dict[str, Any]] = None, **kwargs) -> bool:
        """
        [UPDATE / MODIFICAR] Modifica campos o agrega variables nuevas a un camión.
        
        Ejemplos:
          dao.update_truck(camion_id, capacity_tons=40.0, patente="AA123ZZ", mi_variable="Hola")
          dao.update_truck(camion_id, {"capacity_tons": 40.0, "patente": "AA123ZZ"})
        """
        payload = dict(update_data) if isinstance(update_data, dict) else {}
        if kwargs:
            payload.update(kwargs)
        return self.update_document("trucks", truck_id, payload)

    def add_variable_to_truck(self, truck_id: str, variable_name: str, value: Any) -> bool:
        """[AGREGAR VARIABLE] Agrega una variable nueva a un camión."""
        return self.update_truck(truck_id, {variable_name: value})

    def modify_variable_truck(self, truck_id: str, variable_name: str, value: Any) -> bool:
        """[MODIFICAR VARIABLE] Modifica cualquier variable de un camión."""
        return self.update_truck(truck_id, {variable_name: value})

    def set_truck_variables(self, truck_id: str, **variables) -> bool:
        """[SET VARIABLES] Setea múltiples variables usando kwargs."""
        return self.update_truck(truck_id, **variables)

    def delete_variable_from_truck(self, truck_id: str, variable_name: str) -> bool:
        """[ELIMINAR VARIABLE] Elimina un campo o variable de un camión usando $unset."""
        return self.delete_variable("trucks", truck_id, variable_name)

    def delete_truck(self, truck_id: str) -> bool:
        """[DELETE / ELIMINAR] Elimina un camión por su ID."""
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

    def add_driver(self, driver_data: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """[CREATE] Registra un nuevo chofer."""
        data = dict(driver_data) if isinstance(driver_data, dict) else {}
        if kwargs:
            data.update(kwargs)
        res = self._drivers.insert_one(data)
        logger.info(f"Conductor insertado con ID: {res.inserted_id}")
        return str(res.inserted_id)

    def get_drivers(self) -> List[Dict[str, Any]]:
        """[READ ALL] Obtiene todos los conductores."""
        return self._clean_docs(list(self._drivers.find()))

    def get_driver_by_id(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Busca un conductor por ID."""
        oid = self._to_object_id(driver_id)
        return self._clean_doc(self._drivers.find_one({"_id": oid})) if oid else None

    def update_driver(self, driver_id: str, update_data: Optional[Dict[str, Any]] = None, **kwargs) -> bool:
        """[UPDATE] Actualiza variables de un conductor."""
        payload = dict(update_data) if isinstance(update_data, dict) else {}
        if kwargs:
            payload.update(kwargs)
        return self.update_document("drivers", driver_id, payload)

    def delete_driver(self, driver_id: str) -> bool:
        """[DELETE] Elimina un conductor por ID."""
        oid = self._to_object_id(driver_id)
        return self._drivers.delete_one({"_id": oid}).deleted_count > 0 if oid else False

    # =========================================================================
    # 3. ROUTES (Rutas Logísticas) - CRUD COMPLETO
    # =========================================================================

    def add_route(self, route_data: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """[CREATE] Asigna una nueva ruta logística."""
        data = dict(route_data) if isinstance(route_data, dict) else {}
        if kwargs:
            data.update(kwargs)
        res = self._routes.insert_one(data)
        logger.info(f"Ruta insertada con ID: {res.inserted_id}")
        return str(res.inserted_id)

    def get_routes(self) -> List[Dict[str, Any]]:
        """[READ ALL] Recupera la lista de rutas."""
        return self._clean_docs(list(self._routes.find()))

    def get_route_by_id(self, route_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una ruta por su ID."""
        oid = self._to_object_id(route_id)
        return self._clean_doc(self._routes.find_one({"_id": oid})) if oid else None

    def update_route(self, route_id: str, update_data: Optional[Dict[str, Any]] = None, **kwargs) -> bool:
        """[UPDATE] Modifica una ruta logística existente."""
        payload = dict(update_data) if isinstance(update_data, dict) else {}
        if kwargs:
            payload.update(kwargs)
        return self.update_document("routes", route_id, payload)

    def delete_route(self, route_id: str) -> bool:
        """[DELETE] Elimina una ruta logística."""
        oid = self._to_object_id(route_id)
        return self._routes.delete_one({"_id": oid}).deleted_count > 0 if oid else False

    # =========================================================================
    # 4. GEOFENCES (Geocercas Espaciales) - CRUD COMPLETO
    # =========================================================================

    def add_geofence(self, geofence_data: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """[CREATE] Registra una nueva geocerca espacial."""
        data = dict(geofence_data) if isinstance(geofence_data, dict) else {}
        if kwargs:
            data.update(kwargs)
        
        # Formatear geometría GeoJSON si viene polygon
        if "polygon" in data and "geometry" not in data:
            poly = data.pop("polygon")
            data["geometry"] = {
                "type": "Polygon",
                "coordinates": [poly]
            }

        res = self._geofences.insert_one(data)
        logger.info(f"Geocerca insertada con ID: {res.inserted_id}")
        return str(res.inserted_id)

    def get_geofences(self) -> List[Dict[str, Any]]:
        """[READ ALL] Lista todas las geocercas registradas."""
        return self._clean_docs(list(self._geofences.find()))

    def get_geofence_by_id(self, geofence_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una geocerca por ID."""
        oid = self._to_object_id(geofence_id)
        return self._clean_doc(self._geofences.find_one({"_id": oid})) if oid else None

    def update_geofence(self, geofence_id: str, update_data: Optional[Dict[str, Any]] = None, **kwargs) -> bool:
        """[UPDATE] Modifica una geocerca existente."""
        payload = dict(update_data) if isinstance(update_data, dict) else {}
        if kwargs:
            payload.update(kwargs)
        if "polygon" in payload:
            poly = payload.pop("polygon")
            payload["geometry"] = {
                "type": "Polygon",
                "coordinates": [poly]
            }
        return self.update_document("geofences", geofence_id, payload)

    def delete_geofence(self, geofence_id: str) -> bool:
        """[DELETE] Elimina una geocerca por ID."""
        oid = self._to_object_id(geofence_id)
        return self._geofences.delete_one({"_id": oid}).deleted_count > 0 if oid else False

    # =========================================================================
    # 5. TELEMETRY (Lecturas IoT y Consultas Geoespaciales) - CRUD COMPLETO
    # =========================================================================

    def add_telemetry(self, telemetry_data: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """[CREATE] Registra un evento de telemetría IoT."""
        data = dict(telemetry_data) if isinstance(telemetry_data, dict) else {}
        if kwargs:
            data.update(kwargs)

        # Si vienen coordenadas lon y lat separadas, estructurarlas en GeoJSON Point
        if "lon" in data and "lat" in data and "location" not in data:
            lon = data.pop("lon")
            lat = data.pop("lat")
            if lon is not None and lat is not None:
                data["location"] = {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }

        try:
            res = self._telemetry.insert_one(data)
            return str(res.inserted_id)
        except DuplicateKeyError:
            truck_id = data.get("truck_id", "desconocido")
            logger.warning(f"Evento de telemetría duplicado omitido para el camión {truck_id}")
            raise
        except PyMongoError as e:
            logger.error(f"Error insertando telemetría: {e}")
            raise

    def get_telemetry(self, truck_id: str, desde=None, hasta=None) -> List[Dict[str, Any]]:
        """[READ] Recupera la serie temporal de telemetría de un camión."""
        query = {"truck_id": truck_id}
        if desde or hasta:
            query["timestamp"] = {}
            if desde:
                query["timestamp"]["$gte"] = desde
            if hasta:
                query["timestamp"]["$lte"] = hasta
        cursor = self._telemetry.find(query).sort("timestamp", 1)
        return self._clean_docs(list(cursor))

    def get_telemetry_by_id(self, telemetry_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una lectura de telemetría por ID."""
        oid = self._to_object_id(telemetry_id)
        return self._clean_doc(self._telemetry.find_one({"_id": oid})) if oid else None

    def update_telemetry(self, telemetry_id: str, update_data: Optional[Dict[str, Any]] = None, **kwargs) -> bool:
        """[UPDATE] Modifica o agrega variables a un registro de telemetría."""
        payload = dict(update_data) if isinstance(update_data, dict) else {}
        if kwargs:
            payload.update(kwargs)
        if "lon" in payload and "lat" in payload:
            lon = payload.pop("lon")
            lat = payload.pop("lat")
            payload["location"] = {
                "type": "Point",
                "coordinates": [lon, lat]
            }
        return self.update_document("telemetry", telemetry_id, payload)

    def delete_telemetry(self, telemetry_id: str) -> bool:
        """[DELETE] Elimina un registro de telemetría."""
        oid = self._to_object_id(telemetry_id)
        return self._telemetry.delete_one({"_id": oid}).deleted_count > 0 if oid else False

    def get_telemetry_near(self, truck_id: str, lon: float, lat: float, max_distance_meters: float) -> List[Dict[str, Any]]:
        """Consulta espacial `$near` con índice `2dsphere`."""
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
        return self._clean_docs(list(self._telemetry.find(query)))

    def get_telemetry_in_polygon(self, truck_id: str, polygon: List[List[float]]) -> List[Dict[str, Any]]:
        """Consulta espacial `$geoWithin` para verificar presencia dentro de un polígono."""
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
        return self._clean_docs(list(self._telemetry.find(query)))

    def get_truck_statistics(self, truck_id: str) -> Dict[str, Any]:
        """Agregación analítica en MongoDB (velocidad promedio, temp máxima, etc.)."""
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
