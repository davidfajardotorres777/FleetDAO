import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import MongoClient

from config_vars import MONGO_URI, DB_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")


class FleetDAO:
    """
    Data Access Object (DAO) para FleetDAO.
    Abstracción ligera, directa y flexible sobre MongoDB.
    """

    def __init__(self):
        self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        self._db = self._client[DB_NAME]
        self._telemetry = self._db["telemetry"]
        
        # Configuración de Índices
        self._telemetry.create_index([("truck_id", 1), ("timestamp", 1)], unique=True)
        self._telemetry.create_index([("location", "2dsphere")])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._client.close()

    # -------------------------------------------------------------------------
    # Operaciones Genéricas de BD
    # -------------------------------------------------------------------------

    @staticmethod
    def _oid(id_str: str) -> Optional[ObjectId]:
        return id_str if isinstance(id_str, ObjectId) else (ObjectId(str(id_str)) if id_str and ObjectId.is_valid(str(id_str)) else None)

    @staticmethod
    def _clean(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
            doc["id"] = doc["_id"]
        return doc

    def _insert(self, coll: str, data: Dict[str, Any] = None, **kwargs) -> str:
        payload = dict(data) if isinstance(data, dict) else {}
        payload.update(kwargs)
        if not payload:
            raise ValueError("No se proporcionaron datos para insertar.")
        return str(self._db[coll].insert_one(payload).inserted_id)

    def _get_all(self, coll: str, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return [self._clean(d) for d in self._db[coll].find(query or {})]

    def _get_by_id(self, coll: str, doc_id: str) -> Optional[Dict[str, Any]]:
        oid = self._oid(doc_id)
        return self._clean(self._db[coll].find_one({"_id": oid})) if oid else None

    def _update(self, coll: str, doc_id: str, data: Dict[str, Any] = None, **kwargs) -> bool:
        oid = self._oid(doc_id)
        if not oid:
            return False
        payload = dict(data) if isinstance(data, dict) else {}
        payload.update(kwargs)
        payload.pop("_id", None)
        payload.pop("id", None)
        if not payload:
            return False
        res = self._db[coll].update_one({"_id": oid}, {"$set": payload})
        return res.modified_count > 0 or res.matched_count > 0

    def _delete(self, coll: str, doc_id: str) -> bool:
        oid = self._oid(doc_id)
        return self._db[coll].delete_one({"_id": oid}).deleted_count > 0 if oid else False

    def _delete_field(self, coll: str, doc_id: str, field_name: str) -> bool:
        oid = self._oid(doc_id)
        return self._db[coll].update_one({"_id": oid}, {"$unset": {field_name: ""}}).modified_count > 0 if oid else False

    # Búsqueda dinámica
    def search_by_variable(self, coll: str, key: str, value: Any) -> List[Dict[str, Any]]:
        return self._get_all(coll, {key: value})

    def add_variable(self, coll: str, doc_id: str, var_name: str, val: Any) -> bool:
        return self._update(coll, doc_id, **{var_name: val})

    def modify_variable(self, coll: str, doc_id: str, var_name: str, val: Any) -> bool:
        return self._update(coll, doc_id, **{var_name: val})

    def set_variables(self, coll: str, doc_id: str, **variables) -> bool:
        return self._update(coll, doc_id, **variables)

    def delete_variable(self, coll: str, doc_id: str, var_name: str) -> bool:
        return self._delete_field(coll, doc_id, var_name)

    # -------------------------------------------------------------------------
    # 1. TRUCKS (Camiones)
    # -------------------------------------------------------------------------
    def add_truck(self, truck_data: Dict[str, Any] = None, **kwargs) -> str: return self._insert("trucks", truck_data, **kwargs)
    def get_trucks(self) -> List[Dict[str, Any]]: return self._get_all("trucks")
    def get_truck_by_id(self, truck_id: str) -> Optional[Dict[str, Any]]: return self._get_by_id("trucks", truck_id)
    def get_trucks_by_variable(self, key: str, value: Any) -> List[Dict[str, Any]]: return self.search_by_variable("trucks", key, value)
    def update_truck(self, truck_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool: return self._update("trucks", truck_id, update_data, **kwargs)
    def delete_truck(self, truck_id: str) -> bool: return self._delete("trucks", truck_id)
    def add_variable_to_truck(self, truck_id: str, var_name: str, value: Any) -> bool: return self.update_truck(truck_id, **{var_name: value})
    def modify_variable_truck(self, truck_id: str, var_name: str, value: Any) -> bool: return self.update_truck(truck_id, **{var_name: value})
    def set_truck_variables(self, truck_id: str, **variables) -> bool: return self.update_truck(truck_id, **variables)
    def delete_variable_from_truck(self, truck_id: str, var_name: str) -> bool: return self._delete_field("trucks", truck_id, var_name)

    # -------------------------------------------------------------------------
    # 2. DRIVERS (Choferes)
    # -------------------------------------------------------------------------
    def add_driver(self, driver_data: Dict[str, Any] = None, **kwargs) -> str: return self._insert("drivers", driver_data, **kwargs)
    def get_drivers(self) -> List[Dict[str, Any]]: return self._get_all("drivers")
    def get_driver_by_id(self, driver_id: str) -> Optional[Dict[str, Any]]: return self._get_by_id("drivers", driver_id)
    def update_driver(self, driver_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool: return self._update("drivers", driver_id, update_data, **kwargs)
    def delete_driver(self, driver_id: str) -> bool: return self._delete("drivers", driver_id)

    # -------------------------------------------------------------------------
    # 3. ROUTES (Rutas)
    # -------------------------------------------------------------------------
    def add_route(self, route_data: Dict[str, Any] = None, **kwargs) -> str: return self._insert("routes", route_data, **kwargs)
    def get_routes(self) -> List[Dict[str, Any]]: return self._get_all("routes")
    def get_route_by_id(self, route_id: str) -> Optional[Dict[str, Any]]: return self._get_by_id("routes", route_id)
    def update_route(self, route_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool: return self._update("routes", route_id, update_data, **kwargs)
    def delete_route(self, route_id: str) -> bool: return self._delete("routes", route_id)

    # -------------------------------------------------------------------------
    # 4. GEOFENCES (Geocercas)
    # -------------------------------------------------------------------------
    def add_geofence(self, geofence_data: Dict[str, Any] = None, **kwargs) -> str:
        data = dict(geofence_data) if isinstance(geofence_data, dict) else {}
        data.update(kwargs)
        if "polygon" in data and "geometry" not in data:
            data["geometry"] = {"type": "Polygon", "coordinates": [data.pop("polygon")]}
        return self._insert("geofences", data)

    def get_geofences(self) -> List[Dict[str, Any]]: return self._get_all("geofences")
    def get_geofence_by_id(self, geofence_id: str) -> Optional[Dict[str, Any]]: return self._get_by_id("geofences", geofence_id)
    
    def update_geofence(self, geofence_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        data = dict(update_data) if isinstance(update_data, dict) else {}
        data.update(kwargs)
        if "polygon" in data:
            data["geometry"] = {"type": "Polygon", "coordinates": [data.pop("polygon")]}
        return self._update("geofences", geofence_id, data)

    def delete_geofence(self, geofence_id: str) -> bool: return self._delete("geofences", geofence_id)

    # -------------------------------------------------------------------------
    # 5. TELEMETRY (Telemetría)
    # -------------------------------------------------------------------------
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
            if desde: query["timestamp"]["$gte"] = desde
            if hasta: query["timestamp"]["$lte"] = hasta
        return [self._clean(d) for d in self._telemetry.find(query).sort("timestamp", 1)]

    def get_telemetry_by_id(self, telemetry_id: str) -> Optional[Dict[str, Any]]: return self._get_by_id("telemetry", telemetry_id)
    
    def update_telemetry(self, telemetry_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        data = dict(update_data) if isinstance(update_data, dict) else {}
        data.update(kwargs)
        if "lon" in data and "lat" in data:
            data["location"] = {"type": "Point", "coordinates": [data.pop("lon"), data.pop("lat")]}
        return self._update("telemetry", telemetry_id, data)

    def delete_telemetry(self, telemetry_id: str) -> bool: return self._delete("telemetry", telemetry_id)

    def get_truck_statistics(self, truck_id: str) -> Dict[str, Any]:
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

    # -------------------------------------------------------------------------
    # 6. ANALYTICS & DASHBOARD
    # -------------------------------------------------------------------------
    def get_fleet_summary(self) -> Dict[str, Any]:
        speed_alerts = self._telemetry.count_documents({"speed_kmh": {"$gt": 100}})
        temp_alerts = self._telemetry.count_documents({"engine_temp_c": {"$gt": 95}})
        return {
            "total_trucks": self._db["trucks"].count_documents({}),
            "total_drivers": self._db["drivers"].count_documents({}),
            "total_routes": self._db["routes"].count_documents({}),
            "total_telemetry_readings": self._telemetry.count_documents({}),
            "alerts": {
                "speed_exceeded": speed_alerts,
                "engine_overheat": temp_alerts,
                "total_alerts": speed_alerts + temp_alerts
            }
        }

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        query = {"$or": [{"speed_kmh": {"$gt": 100}}, {"engine_temp_c": {"$gt": 95}}, {"fuel_level_pct": {"$lt": 15}}]}
        return [self._clean(d) for d in self._telemetry.find(query).sort("timestamp", -1).limit(limit)]
