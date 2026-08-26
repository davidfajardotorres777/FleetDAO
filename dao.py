import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import MongoClient

from config_vars import MONGO_URI, DB_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")


class FleetDAO:
    """
    Data Access Object (DAO) para la gestión de flotas sobre MongoDB.

    Representación clara e intuitiva de la base de datos 'fleet_db' y sus colecciones:
      - trucks     : Camiones de la flota
      - drivers    : Choferes asignados
      - routes     : Rutas logísticas
      - geofences  : Geocercas de control de zona
      - telemetry  : Lecturas IoT (velocidad, motor, posición GPS)
    """

    def __init__(self):
        """Inicializa la conexión con MongoDB y obtiene las referencias a las colecciones."""
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.db = self.client[DB_NAME]

            # Colecciones de MongoDB
            self.trucks = self.db["trucks"]
            self.drivers = self.db["drivers"]
            self.routes = self.db["routes"]
            self.geofences = self.db["geofences"]
            self.telemetry = self.db["telemetry"]

            # Índices de aceleración
            self.telemetry.create_index([("truck_id", 1), ("timestamp", 1)], unique=True)
            self.telemetry.create_index([("location", "2dsphere")])
            logger.info("Conexión exitosa a MongoDB ('fleet_db') e índices verificados.")
        except Exception as e:
            logger.error(f"Error conectando a MongoDB: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Cierra la conexión con el servidor MongoDB."""
        self.client.close()
        logger.info("Conexión a MongoDB cerrada.")

    # -------------------------------------------------------------------------
    # Operaciones Auxiliares y Limpieza de ObjectId
    # -------------------------------------------------------------------------

    @staticmethod
    def _oid(id_str: str) -> Optional[ObjectId]:
        """Convierte una cadena a ObjectId de MongoDB."""
        if not id_str:
            return None
        return id_str if isinstance(id_str, ObjectId) else (ObjectId(str(id_str)) if ObjectId.is_valid(str(id_str)) else None)

    @staticmethod
    def _clean(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Mapea '_id' de MongoDB a una cadena serializable en JSON."""
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
            doc["id"] = doc["_id"]
        return doc

    def _insert(self, coll: str, data: Dict[str, Any] = None, **kwargs) -> str:
        """Inserta un nuevo documento en la colección indicada."""
        payload = dict(data) if isinstance(data, dict) else {}
        payload.update(kwargs)
        if not payload:
            raise ValueError("Se requieren datos para realizar la inserción.")
        return str(self.db[coll].insert_one(payload).inserted_id)

    def _get_all(self, coll: str, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retorna todos los documentos de una colección."""
        return [self._clean(d) for d in self.db[coll].find(query or {})]

    def _get_by_id(self, coll: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un documento por su ID."""
        oid = self._oid(doc_id)
        return self._clean(self.db[coll].find_one({"_id": oid})) if oid else None

    def _update(self, coll: str, doc_id: str, data: Dict[str, Any] = None, **kwargs) -> bool:
        """Modifica o agrega nuevos campos/variables a un documento existente."""
        oid = self._oid(doc_id)
        if not oid:
            return False
        payload = dict(data) if isinstance(data, dict) else {}
        payload.update(kwargs)
        payload.pop("_id", None)
        payload.pop("id", None)
        if not payload:
            return False
        res = self.db[coll].update_one({"_id": oid}, {"$set": payload})
        return res.modified_count > 0 or res.matched_count > 0

    def _delete(self, coll: str, doc_id: str) -> bool:
        """Elimina un documento de la colección."""
        oid = self._oid(doc_id)
        return self.db[coll].delete_one({"_id": oid}).deleted_count > 0 if oid else False

    def _delete_field(self, coll: str, doc_id: str, field_name: str) -> bool:
        """Elimina una variable o campo dinámico específico de un documento."""
        oid = self._oid(doc_id)
        return self.db[coll].update_one({"_id": oid}, {"$unset": {field_name: ""}}).modified_count > 0 if oid else False

    # -------------------------------------------------------------------------
    # Operaciones Genéricas de Variables Dinámicas
    # -------------------------------------------------------------------------

    def search_by_variable(self, coll: str, key: str, value: Any) -> List[Dict[str, Any]]:
        """Filtra documentos por cualquier clave/valor dinámico."""
        return self._get_all(coll, {key: value})

    def add_variable(self, coll: str, doc_id: str, var_name: str, val: Any) -> bool:
        return self._update(coll, doc_id, **{var_name: val})

    def modify_variable(self, coll: str, doc_id: str, var_name: str, val: Any) -> bool:
        return self._update(coll, doc_id, **{var_name: val})

    def set_variables(self, coll: str, doc_id: str, **variables) -> bool:
        return self._update(coll, doc_id, **variables)

    def delete_variable(self, coll: str, doc_id: str, var_name: str) -> bool:
        return self._delete_field(coll, doc_id, var_name)

    # =========================================================================
    # 1. TRUCKS (Camiones) - CRUD & VARIABLES DINÁMICAS
    # =========================================================================

    def add_truck(self, truck_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Registra un camión (ejemplo: dao.add_truck(brand='Volvo', capacity_tons=25, patente='AA123'))"""
        return self._insert("trucks", truck_data, **kwargs)

    def get_trucks(self) -> List[Dict[str, Any]]:
        """[READ ALL] Obtiene todos los camiones."""
        return self._get_all("trucks")

    def get_truck_by_id(self, truck_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene un camión por su ID."""
        return self._get_by_id("trucks", truck_id)

    def get_trucks_by_variable(self, key: str, value: Any) -> List[Dict[str, Any]]:
        """[SEARCH] Filtra camiones por el valor de cualquier variable dinámica."""
        return self.search_by_variable("trucks", key, value)

    def update_truck(self, truck_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Modifica o agrega cualquier variable a un camión."""
        return self._update("trucks", truck_id, update_data, **kwargs)

    def delete_truck(self, truck_id: str) -> bool:
        """[DELETE] Elimina un camión."""
        return self._delete("trucks", truck_id)

    def add_variable_to_truck(self, truck_id: str, var_name: str, value: Any) -> bool:
        """[VARIABLE ADD] Agrega una variable a un camión."""
        return self.update_truck(truck_id, **{var_name: value})

    def modify_variable_truck(self, truck_id: str, var_name: str, value: Any) -> bool:
        """[VARIABLE MODIFY] Modifica una variable de un camión."""
        return self.update_truck(truck_id, **{var_name: value})

    def set_truck_variables(self, truck_id: str, **variables) -> bool:
        """[VARIABLE SET] Setea múltiples variables en un camión."""
        return self.update_truck(truck_id, **variables)

    def delete_variable_from_truck(self, truck_id: str, var_name: str) -> bool:
        """[VARIABLE DELETE] Elimina una variable de un camión."""
        return self._delete_field("trucks", truck_id, var_name)

    # =========================================================================
    # 2. DRIVERS (Choferes) - CRUD
    # =========================================================================

    def add_driver(self, driver_data: Dict[str, Any] = None, **kwargs) -> str:
        return self._insert("drivers", driver_data, **kwargs)

    def get_drivers(self) -> List[Dict[str, Any]]:
        return self._get_all("drivers")

    def get_driver_by_id(self, driver_id: str) -> Optional[Dict[str, Any]]:
        return self._get_by_id("drivers", driver_id)

    def update_driver(self, driver_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        return self._update("drivers", driver_id, update_data, **kwargs)

    def delete_driver(self, driver_id: str) -> bool:
        return self._delete("drivers", driver_id)

    # =========================================================================
    # 3. ROUTES (Rutas Logísticas) - CRUD
    # =========================================================================

    def add_route(self, route_data: Dict[str, Any] = None, **kwargs) -> str:
        return self._insert("routes", route_data, **kwargs)

    def get_routes(self) -> List[Dict[str, Any]]:
        return self._get_all("routes")

    def get_route_by_id(self, route_id: str) -> Optional[Dict[str, Any]]:
        return self._get_by_id("routes", route_id)

    def update_route(self, route_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        return self._update("routes", route_id, update_data, **kwargs)

    def delete_route(self, route_id: str) -> bool:
        return self._delete("routes", route_id)

    # =========================================================================
    # 4. GEOFENCES (Geocercas Espaciales) - CRUD
    # =========================================================================

    def add_geofence(self, geofence_data: Dict[str, Any] = None, **kwargs) -> str:
        data = dict(geofence_data) if isinstance(geofence_data, dict) else {}
        data.update(kwargs)
        if "polygon" in data and "geometry" not in data:
            data["geometry"] = {"type": "Polygon", "coordinates": [data.pop("polygon")]}
        return self._insert("geofences", data)

    def get_geofences(self) -> List[Dict[str, Any]]:
        return self._get_all("geofences")

    def get_geofence_by_id(self, geofence_id: str) -> Optional[Dict[str, Any]]:
        return self._get_by_id("geofences", geofence_id)

    def update_geofence(self, geofence_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        data = dict(update_data) if isinstance(update_data, dict) else {}
        data.update(kwargs)
        if "polygon" in data:
            data["geometry"] = {"type": "Polygon", "coordinates": [data.pop("polygon")]}
        return self._update("geofences", geofence_id, data)

    def delete_geofence(self, geofence_id: str) -> bool:
        return self._delete("geofences", geofence_id)

    # =========================================================================
    # 5. TELEMETRY (Telemetría IoT) - CRUD & GEO-QUERIES
    # =========================================================================

    def add_telemetry(self, telemetry_data: Dict[str, Any] = None, **kwargs) -> str:
        data = dict(telemetry_data) if isinstance(telemetry_data, dict) else {}
        data.update(kwargs)
        if "lon" in data and "lat" in data and "location" not in data:
            lon, lat = data.pop("lon"), data.pop("lat")
            if lon is not None and lat is not None:
                data["location"] = {"type": "Point", "coordinates": [lon, lat]}
        return self._insert("telemetry", data)

    def get_telemetry(self, truck_id: str, desde=None, hasta=None) -> List[Dict[str, Any]]:
        query = {"truck_id": truck_id}
        if desde or hasta:
            query["timestamp"] = {}
            if desde:
                query["timestamp"]["$gte"] = desde
            if hasta:
                query["timestamp"]["$lte"] = hasta
        return [self._clean(d) for d in self.telemetry.find(query).sort("timestamp", 1)]

    def get_telemetry_by_id(self, telemetry_id: str) -> Optional[Dict[str, Any]]:
        return self._get_by_id("telemetry", telemetry_id)

    def update_telemetry(self, telemetry_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        data = dict(update_data) if isinstance(update_data, dict) else {}
        data.update(kwargs)
        if "lon" in data and "lat" in data:
            data["location"] = {"type": "Point", "coordinates": [data.pop("lon"), data.pop("lat")]}
        return self._update("telemetry", telemetry_id, data)

    def delete_telemetry(self, telemetry_id: str) -> bool:
        return self._delete("telemetry", telemetry_id)

    def get_truck_statistics(self, truck_id: str) -> Dict[str, Any]:
        """Agregación analítica de telemetría por camión."""
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
        res = list(self.telemetry.aggregate(pipeline))
        return self._clean(res[0]) if res else {}

    # =========================================================================
    # 6. ANALYTICS & DASHBOARD SUMMARY
    # =========================================================================

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Resumen analítico ejecutivo de la flota completa."""
        speed_alerts = self.telemetry.count_documents({"speed_kmh": {"$gt": 100}})
        temp_alerts = self.telemetry.count_documents({"engine_temp_c": {"$gt": 95}})
        return {
            "total_trucks": self.trucks.count_documents({}),
            "total_drivers": self.drivers.count_documents({}),
            "total_routes": self.routes.count_documents({}),
            "total_telemetry_readings": self.telemetry.count_documents({}),
            "alerts": {
                "speed_exceeded": speed_alerts,
                "engine_overheat": temp_alerts,
                "total_alerts": speed_alerts + temp_alerts
            }
        }

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Recupera las lecturas con anomalías o alertas recientes."""
        query = {"$or": [{"speed_kmh": {"$gt": 100}}, {"engine_temp_c": {"$gt": 95}}, {"fuel_level_pct": {"$lt": 15}}]}
        return [self._clean(d) for d in self.telemetry.find(query).sort("timestamp", -1).limit(limit)]
