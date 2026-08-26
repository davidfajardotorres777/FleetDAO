import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError

from config_vars import MONGO_URI, DB_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")


class FleetDAO:
    """
    Data Access Object (DAO) Principal para el sistema de gestión de flotas FleetDAO.

    Proporciona una abstracción limpia, directa y libre de esquemas sobre la base de datos 'fleet_db' en MongoDB.

    Colecciones Administradas:
      - trucks     : Camiones de la flota
      - drivers    : Choferes asignados
      - routes     : Rutas logísticas
      - geofences  : Geocercas espaciales GeoJSON
      - telemetry  : Lecturas IoT y series temporales GPS

    Capacidades Destacadas:
      1. CRUD completo e inmediato para todas las colecciones.
      2. Adición y modificación dinámica de cualquier variable en tiempo real (`$set` y `$unset`).
      3. Consultas geoespaciales nativas (`2dsphere`, `$near`, `$geoWithin`).
      4. Inserción masiva de telemetría por lotes (Batch Ingestion).
      5. Agregaciones analíticas de rendimiento y diagnósticos de alertas.
    """

    def __init__(self):
        """Inicializa la conexión con MongoDB y configura los índices optimizados."""
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.db = self.client[DB_NAME]

            # Referencias a las Colecciones de MongoDB
            self.trucks = self.db["trucks"]
            self.drivers = self.db["drivers"]
            self.routes = self.db["routes"]
            self.geofences = self.db["geofences"]
            self.telemetry = self.db["telemetry"]

            # Configuración de Índices Nativa
            self.telemetry.create_index([("truck_id", ASCENDING), ("timestamp", ASCENDING)], unique=True)
            self.telemetry.create_index([("location", "2dsphere")])
            self.trucks.create_index([("patente", ASCENDING)], sparse=True)
            logger.info("Conexión exitosa a MongoDB ('fleet_db') e índices optimizados.")
        except Exception as e:
            logger.error(f"Error conectando a MongoDB: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Cierra la conexión activa con el servidor MongoDB."""
        self.client.close()
        logger.info("Conexión a MongoDB cerrada.")

    # -------------------------------------------------------------------------
    # Operaciones Internas y Normalización de ObjectId
    # -------------------------------------------------------------------------

    @staticmethod
    def _oid(id_str: str) -> Optional[ObjectId]:
        """Convierte una cadena a ObjectId de MongoDB de forma segura."""
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
        """Inserta un nuevo documento en cualquier colección aceptando dict o kwargs."""
        payload = dict(data) if isinstance(data, dict) else {}
        payload.update(kwargs)
        if not payload:
            raise ValueError("Se requieren datos para realizar la inserción.")
        return str(self.db[coll].insert_one(payload).inserted_id)

    def _get_all(self, coll: str, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Recupera todos los documentos de una colección."""
        return [self._clean(d) for d in self.db[coll].find(query or {})]

    def _get_by_id(self, coll: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un documento por su ID."""
        oid = self._oid(doc_id)
        return self._clean(self.db[coll].find_one({"_id": oid})) if oid else None

    def _update(self, coll: str, doc_id: str, data: Dict[str, Any] = None, **kwargs) -> bool:
        """Modifica o agrega cualquier variable a un documento usando `$set`."""
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
        """Elimina una variable específica de un documento usando `$unset`."""
        oid = self._oid(doc_id)
        return self.db[coll].update_one({"_id": oid}, {"$unset": {field_name: ""}}).modified_count > 0 if oid else False

    # -------------------------------------------------------------------------
    # Operaciones Genéricas de Variables Dinámicas por Colección
    # -------------------------------------------------------------------------

    def search_by_variable(self, coll: str, key: str, value: Any) -> List[Dict[str, Any]]:
        """Filtra documentos en cualquier colección por el valor de una variable clave."""
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
        """
        [CREATE] Registra un nuevo camión en la base de datos.
        
        Ejemplos de uso:
          dao.add_truck(brand="Volvo", capacity_tons=25.0, patente="AA123ZZ")
          dao.add_truck({"brand": "Scania", "capacity_tons": 30.0})
        """
        return self._insert("trucks", truck_data, **kwargs)

    def get_trucks(self) -> List[Dict[str, Any]]:
        """[READ ALL] Retorna la lista completa de camiones."""
        return self._get_all("trucks")

    def get_truck_by_id(self, truck_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene los datos de un camión por su ID."""
        return self._get_by_id("trucks", truck_id)

    def get_trucks_by_variable(self, key: str, value: Any) -> List[Dict[str, Any]]:
        """[SEARCH] Filtra camiones por cualquier variable o atributo personalizado."""
        return self.search_by_variable("trucks", key, value)

    def update_truck(self, truck_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Modifica o agrega cualquier variable a un camión en tiempo real."""
        return self._update("trucks", truck_id, update_data, **kwargs)

    def delete_truck(self, truck_id: str) -> bool:
        """[DELETE] Elimina un camión por su ID."""
        return self._delete("trucks", truck_id)

    def add_variable_to_truck(self, truck_id: str, var_name: str, value: Any) -> bool:
        """[VARIABLE ADD] Agrega una variable personalizada a un camión."""
        return self.update_truck(truck_id, **{var_name: value})

    def modify_variable_truck(self, truck_id: str, var_name: str, value: Any) -> bool:
        """[VARIABLE MODIFY] Modifica una variable de un camión."""
        return self.update_truck(truck_id, **{var_name: value})

    def set_truck_variables(self, truck_id: str, **variables) -> bool:
        """[VARIABLE SET] Modifica múltiples variables en un camión."""
        return self.update_truck(truck_id, **variables)

    def delete_variable_from_truck(self, truck_id: str, var_name: str) -> bool:
        """[VARIABLE DELETE] Elimina una variable específica de un camión."""
        return self._delete_field("trucks", truck_id, var_name)

    # =========================================================================
    # 2. DRIVERS (Choferes) - CRUD COMPLETO
    # =========================================================================

    def add_driver(self, driver_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Registra un nuevo chofer."""
        return self._insert("drivers", driver_data, **kwargs)

    def get_drivers(self) -> List[Dict[str, Any]]:
        """[READ ALL] Lista todos los conductores."""
        return self._get_all("drivers")

    def get_driver_by_id(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene los datos de un chofer por ID."""
        return self._get_by_id("drivers", driver_id)

    def update_driver(self, driver_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Actualiza los datos de un chofer."""
        return self._update("drivers", driver_id, update_data, **kwargs)

    def delete_driver(self, driver_id: str) -> bool:
        """[DELETE] Elimina un chofer por ID."""
        return self._delete("drivers", driver_id)

    # =========================================================================
    # 3. ROUTES (Rutas Logísticas) - CRUD COMPLETO
    # =========================================================================

    def add_route(self, route_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Asigna una nueva ruta logística."""
        return self._insert("routes", route_data, **kwargs)

    def get_routes(self) -> List[Dict[str, Any]]:
        """[READ ALL] Lista todas las rutas asignadas."""
        return self._get_all("routes")

    def get_route_by_id(self, route_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una ruta por ID."""
        return self._get_by_id("routes", route_id)

    def update_route(self, route_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Modifica una ruta logística."""
        return self._update("routes", route_id, update_data, **kwargs)

    def delete_route(self, route_id: str) -> bool:
        """[DELETE] Elimina una ruta logística."""
        return self._delete("routes", route_id)

    # =========================================================================
    # 4. GEOFENCES (Geocercas Espaciales) - CRUD COMPLETO
    # =========================================================================

    def add_geofence(self, geofence_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Registra una geocerca espacial GeoJSON."""
        data = dict(geofence_data) if isinstance(geofence_data, dict) else {}
        data.update(kwargs)
        if "polygon" in data and "geometry" not in data:
            data["geometry"] = {"type": "Polygon", "coordinates": [data.pop("polygon")]}
        return self._insert("geofences", data)

    def get_geofences(self) -> List[Dict[str, Any]]:
        """[READ ALL] Lista todas las geocercas."""
        return self._get_all("geofences")

    def get_geofence_by_id(self, geofence_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una geocerca por ID."""
        return self._get_by_id("geofences", geofence_id)

    def update_geofence(self, geofence_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Modifica una geocerca."""
        data = dict(update_data) if isinstance(update_data, dict) else {}
        data.update(kwargs)
        if "polygon" in data:
            data["geometry"] = {"type": "Polygon", "coordinates": [data.pop("polygon")]}
        return self._update("geofences", geofence_id, data)

    def delete_geofence(self, geofence_id: str) -> bool:
        """[DELETE] Elimina una geocerca por ID."""
        return self._delete("geofences", geofence_id)

    # =========================================================================
    # 5. TELEMETRY (Telemetría IoT, Geo-Consultas e Inserción Masiva)
    # =========================================================================

    def add_telemetry(self, telemetry_data: Dict[str, Any] = None, **kwargs) -> str:
        """[CREATE] Guarda un evento de telemetría IoT."""
        data = dict(telemetry_data) if isinstance(telemetry_data, dict) else {}
        data.update(kwargs)
        if "lon" in data and "lat" in data and "location" not in data:
            lon, lat = data.pop("lon"), data.pop("lat")
            if lon is not None and lat is not None:
                data["location"] = {"type": "Point", "coordinates": [lon, lat]}
        return self._insert("telemetry", data)

    def bulk_add_telemetry(self, readings: List[Dict[str, Any]]) -> List[str]:
        """[BATCH INGESTION] Inserción masiva eficiente de eventos de telemetría en MongoDB."""
        if not readings:
            return []
        formatted = []
        for r in readings:
            item = dict(r)
            if "lon" in item and "lat" in item and "location" not in item:
                lon, lat = item.pop("lon"), item.pop("lat")
                if lon is not None and lat is not None:
                    item["location"] = {"type": "Point", "coordinates": [lon, lat]}
            formatted.append(item)
        res = self.telemetry.insert_many(formatted, ordered=False)
        return [str(i) for i in res.inserted_ids]

    def get_telemetry(self, truck_id: str, desde=None, hasta=None) -> List[Dict[str, Any]]:
        """[READ] Recupera la serie temporal de telemetría de un camión."""
        query = {"truck_id": truck_id}
        if desde or hasta:
            query["timestamp"] = {}
            if desde:
                query["timestamp"]["$gte"] = desde
            if hasta:
                query["timestamp"]["$lte"] = hasta
        return [self._clean(d) for d in self.telemetry.find(query).sort("timestamp", ASCENDING)]

    def get_telemetry_by_id(self, telemetry_id: str) -> Optional[Dict[str, Any]]:
        """[READ ONE] Obtiene una lectura de telemetría por ID."""
        return self._get_by_id("telemetry", telemetry_id)

    def update_telemetry(self, telemetry_id: str, update_data: Dict[str, Any] = None, **kwargs) -> bool:
        """[UPDATE] Modifica o agrega variables a una lectura de telemetría."""
        data = dict(update_data) if isinstance(update_data, dict) else {}
        data.update(kwargs)
        if "lon" in data and "lat" in data:
            data["location"] = {"type": "Point", "coordinates": [data.pop("lon"), data.pop("lat")]}
        return self._update("telemetry", telemetry_id, data)

    def delete_telemetry(self, telemetry_id: str) -> bool:
        """[DELETE] Elimina una lectura de telemetría por ID."""
        return self._delete("telemetry", telemetry_id)

    def get_telemetry_near(self, truck_id: str, lon: float, lat: float, max_distance_meters: float = 5000.0) -> List[Dict[str, Any]]:
        """[GEO-SPATIAL $near] Consulta espacial en índice 2dsphere para buscar posiciones dentro de un radio."""
        query = {
            "truck_id": truck_id,
            "location": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "$maxDistance": max_distance_meters
                }
            }
        }
        return [self._clean(d) for d in self.telemetry.find(query)]

    def get_telemetry_in_polygon(self, truck_id: str, polygon: List[List[float]]) -> List[Dict[str, Any]]:
        """[GEO-SPATIAL $geoWithin] Verifica qué lecturas GPS ocurrieron dentro de un polígono GeoJSON."""
        query = {
            "truck_id": truck_id,
            "location": {
                "$geoWithin": {
                    "$geometry": {"type": "Polygon", "coordinates": [polygon]}
                }
            }
        }
        return [self._clean(d) for d in self.telemetry.find(query)]

    def get_truck_statistics(self, truck_id: str) -> Dict[str, Any]:
        """[ANALYTICS $aggregate] Pipeline de agregación para calcular velocidad promedio, temp máxima y combustible."""
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
        """[ANALYTICS] Resumen analítico ejecutivo completo de la flota."""
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
        """[ANALYTICS] Recupera las lecturas de telemetría con anomalías o alertas de seguridad."""
        query = {"$or": [{"speed_kmh": {"$gt": 100}}, {"engine_temp_c": {"$gt": 95}}, {"fuel_level_pct": {"$lt": 15}}]}
        return [self._clean(d) for d in self.telemetry.find(query).sort("timestamp", DESCENDING).limit(limit)]
