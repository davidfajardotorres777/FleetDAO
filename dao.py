import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError

from config_vars import MONGO_URI, DB_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")


class FleetDAO:
    """
    Data Access Object (DAO) para el sistema FleetDAO.
    
    Proporciona un acceso directo, limpio y dinámico a MongoDB.
    Permite operaciones CRUD completas y la adición/modificación dinámica de cualquier
    variable sobre las colecciones: trucks, drivers, routes, geofences y telemetry.
    """

    def __init__(self):
        """Inicializa la conexión a MongoDB y configura índices."""
        try:
            self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self._db = self._client[DB_NAME]

            self._trucks = self._db["trucks"]
            self._drivers = self._db["drivers"]
            self._routes = self._db["routes"]
            self._telemetry = self._db["telemetry"]
            self._geofences = self._db["geofences"]

            # Índices de telemetría y consultas espaciales
            self._telemetry.create_index([("truck_id", 1), ("timestamp", 1)], unique=True)
            self._telemetry.create_index([("location", "2dsphere")])
            logger.info("Conexión exitosa a MongoDB e índices inicializados.")
        except PyMongoError as e:
            logger.error(f"Error al conectar con MongoDB: {e}")
            raise

    def close(self):
        """Cierra la conexión con MongoDB."""
        self._client.close()
        logger.info("Conexión a MongoDB cerrada.")

    # -------------------------------------------------------------------------
    # Métodos Auxiliares Genéricos de Base de Datos
    # -------------------------------------------------------------------------

    @staticmethod
    def _oid(id_str: str) -> Optional[ObjectId]:
        """Convierte una cadena a ObjectId de MongoDB de forma segura."""
        if not id_str:
            return None
        return id_str if isinstance(id_str, ObjectId) else (ObjectId(str(id_str)) if ObjectId.is_valid(str(id_str)) else None)

    @staticmethod
    def _clean(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Formatea un documento de MongoDB convirtiendo `_id` en cadena JSON-friendly."""
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
            doc["id"] = doc["_id"]
        return doc

    def _insert(self, collection_name: str, data: Dict[str, Any] = None, **kwargs) -> str:
        """Inserta un nuevo documento en cualquier colección aceptando dict o kwargs."""
        payload = dict(data) if isinstance(data, dict) else {}
        payload.update(kwargs)
        if not payload:
            raise ValueError("No se proporcionaron datos para insertar.")
        res = self._db[collection_name].insert_one(payload)
        return str(res.inserted_id)

    def _get_all(self, collection_name: str, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Recupera todos los documentos de una colección."""
        cursor = self._db[collection_name].find(query or {})
        return [self._clean(d) for d in cursor]

    def _get_by_id(self, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un documento individual por su ID."""
        oid = self._oid(doc_id)
        return self._clean(self._db[collection_name].find_one({"_id": oid})) if oid else None

    def _update(self, collection_name: str, doc_id: str, data: Dict[str, Any] = None, **kwargs) -> bool:
        """Modifica o agrega campos/variables a un documento existente."""
        oid = self._oid(doc_id)
        if not oid:
            return False
        payload = dict(data) if isinstance(data, dict) else {}
        payload.update(kwargs)
        payload.pop("_id", None)
        payload.pop("id", None)
        if not payload:
            return False
        res = self._db[collection_name].update_one({"_id": oid}, {"$set": payload})
        return res.modified_count > 0 or res.matched_count > 0

    def _delete(self, collection_name: str, doc_id: str) -> bool:
        """Elimina un documento de cualquier colección."""
        oid = self._oid(doc_id)
        return self._db[collection_name].delete_one({"_id": oid}).deleted_count > 0 if oid else False

    def _delete_field(self, collection_name: str, doc_id: str, field_name: str) -> bool:
        """Elimina un campo o variable específica de un documento."""
        oid = self._oid(doc_id)
        return self._db[collection_name].update_one({"_id": oid}, {"$unset": {field_name: ""}}).modified_count > 0 if oid else False

    # Métodos genéricos de manipulación de variables por colección
    def add_variable(self, collection_name: str, doc_id: str, variable_name: str, value: Any) -> bool:
        return self._update(collection_name, doc_id, **{variable_name: value})

    def modify_variable(self, collection_name: str, doc_id: str, variable_name: str, value: Any) -> bool:
        return self._update(collection_name, doc_id, **{variable_name: value})

    def set_variables(self, collection_name: str, doc_id: str, **variables) -> bool:
        return self._update(collection_name, doc_id, **variables)

    def delete_variable(self, collection_name: str, doc_id: str, variable_name: str) -> bool:
        return self._delete_field(collection_name, doc_id, variable_name)

    # =========================================================================
    # 1. TRUCKS (Camiones)
    # =========================================================================

    def add_truck(self, truck_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Registra un camión. Ejemplo: dao.add_truck(brand='Volvo', capacity_tons=25.0, patente='AA123')"""
        return self._insert("trucks", truck_data, **kwargs)

    def get_trucks(self) -> List[Dict[str, Any]]:
        """[READ ALL] Lista todos los camiones."""
        return self._get_all("trucks")

    def get_truck_by_id(self, truck_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Busca un camión por ID."""
        return self._get_by_id("trucks", truck_id)

    def update_truck(self, truck_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Actualiza un camión o agrega nuevas variables. Ejemplo: dao.update_truck(id, patente='BB999')"""
        return self._update("trucks", truck_id, update_data, **kwargs)

    def delete_truck(self, truck_id: str) -> bool:
        """[DELETE] Elimina un camión por ID."""
        return self._delete("trucks", truck_id)

    def add_variable_to_truck(self, truck_id: str, variable_name: str, value: Any) -> bool:
        """[VARIABLE ADD] Agrega una variable a un camión."""
        return self.update_truck(truck_id, **{variable_name: value})

    def modify_variable_truck(self, truck_id: str, variable_name: str, value: Any) -> bool:
        """[VARIABLE MODIFY] Modifica una variable de un camión."""
        return self.update_truck(truck_id, **{variable_name: value})

    def set_truck_variables(self, truck_id: str, **variables) -> bool:
        """[VARIABLE SET] Modifica múltiples variables de un camión."""
        return self.update_truck(truck_id, **variables)

    def delete_variable_from_truck(self, truck_id: str, variable_name: str) -> bool:
        """[VARIABLE DELETE] Elimina una variable de un camión."""
        return self._delete_field("trucks", truck_id, variable_name)

    # =========================================================================
    # 2. DRIVERS (Choferes)
    # =========================================================================

    def add_driver(self, driver_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Registra un chofer."""
        return self._insert("drivers", driver_data, **kwargs)

    def get_drivers(self) -> List[Dict[str, Any]]:
        """[READ ALL] Lista todos los choferes."""
        return self._get_all("drivers")

    def get_driver_by_id(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Busca un chofer por ID."""
        return self._get_by_id("drivers", driver_id)

    def update_driver(self, driver_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Modifica un chofer o agrega variables."""
        return self._update("drivers", driver_id, update_data, **kwargs)

    def delete_driver(self, driver_id: str) -> bool:
        """[DELETE] Elimina un chofer."""
        return self._delete("drivers", driver_id)

    # =========================================================================
    # 3. ROUTES (Rutas Logísticas)
    # =========================================================================

    def add_route(self, route_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Asigna una ruta."""
        return self._insert("routes", route_data, **kwargs)

    def get_routes(self) -> List[Dict[str, Any]]:
        """[READ ALL] Lista todas las rutas."""
        return self._get_all("routes")

    def get_route_by_id(self, route_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Busca una ruta por ID."""
        return self._get_by_id("routes", route_id)

    def update_route(self, route_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Modifica una ruta."""
        return self._update("routes", route_id, update_data, **kwargs)

    def delete_route(self, route_id: str) -> bool:
        """[DELETE] Elimina una ruta."""
        return self._delete("routes", route_id)

    # =========================================================================
    # 4. GEOFENCES (Geocercas Espaciales)
    # =========================================================================

    def add_geofence(self, geofence_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Registra una geocerca."""
        data = dict(geofence_data) if isinstance(geofence_data, dict) else {}
        data.update(kwargs)
        if "polygon" in data and "geometry" not in data:
            data["geometry"] = {"type": "Polygon", "coordinates": [data.pop("polygon")]}
        return self._insert("geofences", data)

    def get_geofences(self) -> List[Dict[str, Any]]:
        """[READ ALL] Lista todas las geocercas."""
        return self._get_all("geofences")

    def get_geofence_by_id(self, geofence_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Busca una geocerca por ID."""
        return self._get_by_id("geofences", geofence_id)

    def update_geofence(self, geofence_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Modifica una geocerca."""
        data = dict(update_data) if isinstance(update_data, dict) else {}
        data.update(kwargs)
        if "polygon" in data:
            data["geometry"] = {"type": "Polygon", "coordinates": [data.pop("polygon")]}
        return self._update("geofences", geofence_id, data)

    def delete_geofence(self, geofence_id: str) -> bool:
        """[DELETE] Elimina una geocerca."""
        return self._delete("geofences", geofence_id)

    # =========================================================================
    # 5. TELEMETRY (Telemetría IoT)
    # =========================================================================

    def add_telemetry(self, telemetry_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Guarda una lectura de telemetría."""
        data = dict(telemetry_data) if isinstance(telemetry_data, dict) else {}
        data.update(kwargs)
        if "lon" in data and "lat" in data and "location" not in data:
            lon, lat = data.pop("lon"), data.pop("lat")
            if lon is not None and lat is not None:
                data["location"] = {"type": "Point", "coordinates": [lon, lat]}
        return self._insert("telemetry", data)

    def get_telemetry(self, truck_id: str, desde=None, hasta=None) -> List[Dict[str, Any]]:
        """[READ] Obtiene serie de telemetría por camión."""
        query = {"truck_id": truck_id}
        if desde or hasta:
            query["timestamp"] = {}
            if desde: query["timestamp"]["$gte"] = desde
            if hasta: query["timestamp"]["$lte"] = hasta
        cursor = self._telemetry.find(query).sort("timestamp", 1)
        return [self._clean(d) for d in cursor]

    def get_telemetry_by_id(self, telemetry_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una lectura de telemetría por ID."""
        return self._get_by_id("telemetry", telemetry_id)

    def update_telemetry(self, telemetry_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Modifica lectura de telemetría."""
        data = dict(update_data) if isinstance(update_data, dict) else {}
        data.update(kwargs)
        if "lon" in data and "lat" in data:
            data["location"] = {"type": "Point", "coordinates": [data.pop("lon"), data.pop("lat")]}
        return self._update("telemetry", telemetry_id, data)

    def delete_telemetry(self, telemetry_id: str) -> bool:
        """[DELETE] Elimina un registro de telemetría."""
        return self._delete("telemetry", telemetry_id)

    def get_truck_statistics(self, truck_id: str) -> Dict[str, Any]:
        """[ANALYTICS] Agregación de promedios y máximos en MongoDB."""
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
        res = list(self._telemetry.aggregate(pipeline))
        return self._clean(res[0]) if res else {}
