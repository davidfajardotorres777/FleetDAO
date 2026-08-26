import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import MongoClient

from config_vars import MONGO_URI, DB_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")


class FleetDAO:
    """
    DAO (Data Access Object) para la gestión de flotas y telemetría en MongoDB.
    Diseño simple, ordenado, fácil de entender y con variables en español.
    """

    def __init__(self):
        """Conecta a MongoDB y obtiene referencias a las colecciones principales."""
        try:
            self.cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.db = self.cliente[DB_NAME]

            # Colecciones principales en español
            self.camiones = self.db["trucks"]
            self.choferes = self.db["drivers"]
            self.rutas = self.db["routes"]
            self.geocercas = self.db["geofences"]
            self.telemetria = self.db["telemetry"]

            # Aliases de colecciones en inglés para compatibilidad
            self.trucks = self.camiones
            self.drivers = self.choferes
            self.routes = self.rutas
            self.geofences = self.geocercas
            self.telemetry = self.telemetria

            # Índices de aceleración
            self.telemetria.create_index([("truck_id", 1), ("timestamp", 1)], unique=True)
            self.telemetria.create_index([("location", "2dsphere")])
            logger.info("Conexión exitosa a MongoDB ('fleet_db') e índices verificados.")
        except Exception as e:
            logger.error(f"Error conectando a MongoDB: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Cierra la conexión activa con MongoDB."""
        self.cliente.close()
        logger.info("Conexión a MongoDB cerrada.")

    # -------------------------------------------------------------------------
    # Métodos Auxiliares Internos
    # -------------------------------------------------------------------------

    @staticmethod
    def _convertir_oid(id_str: str) -> Optional[ObjectId]:
        """Convierte una cadena de texto a ObjectId de MongoDB."""
        if not id_str:
            return None
        return id_str if isinstance(id_str, ObjectId) else (ObjectId(str(id_str)) if ObjectId.is_valid(str(id_str)) else None)

    @staticmethod
    def _limpiar_documento(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Convierte el '_id' de MongoDB a string para que sea serializable en JSON."""
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
            doc["id"] = doc["_id"]
        return doc

    # -------------------------------------------------------------------------
    # Operaciones Genéricas Básicas (CRUD Genérico)
    # -------------------------------------------------------------------------

    def insertar(self, coleccion: str, datos: Dict[str, Any] = None, **kwargs) -> str:
        """Inserta un nuevo documento en la colección indicada."""
        payload = dict(datos) if isinstance(datos, dict) else {}
        payload.update(kwargs)
        if not payload:
            raise ValueError("Se requieren datos para realizar la inserción.")
        return str(self.db[coleccion].insert_one(payload).inserted_id)

    def obtener_todos(self, coleccion: str, filtro: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Obtiene la lista completa de documentos de una colección."""
        return [self._limpiar_documento(d) for d in self.db[coleccion].find(filtro or {})]

    def obtener_por_id(self, coleccion: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un documento por su ID de MongoDB."""
        oid = self._convertir_oid(doc_id)
        return self._limpiar_documento(self.db[coleccion].find_one({"_id": oid})) if oid else None

    def actualizar(self, coleccion: str, doc_id: str, datos: Dict[str, Any] = None, **kwargs) -> bool:
        """Modifica o agrega campos/variables usando el operador $set de MongoDB."""
        oid = self._convertir_oid(doc_id)
        if not oid:
            return False
        payload = dict(datos) if isinstance(datos, dict) else {}
        payload.update(kwargs)
        payload.pop("_id", None)
        payload.pop("id", None)
        if not payload:
            return False
        res = self.db[coleccion].update_one({"_id": oid}, {"$set": payload})
        return res.modified_count > 0 or res.matched_count > 0

    def eliminar(self, coleccion: str, doc_id: str) -> bool:
        """Elimina un documento por su ID."""
        oid = self._convertir_oid(doc_id)
        return self.db[coleccion].delete_one({"_id": oid}).deleted_count > 0 if oid else False

    def eliminar_campo(self, coleccion: str, doc_id: str, nombre_campo: str) -> bool:
        """Elimina una variable o campo específico usando $unset en MongoDB."""
        oid = self._convertir_oid(doc_id)
        return self.db[coleccion].update_one({"_id": oid}, {"$unset": {nombre_campo: ""}}).modified_count > 0 if oid else False

    # =========================================================================
    # 1. CAMIONES (CRUD & Variables Dinámicas en Español)
    # =========================================================================

    def agregar_camion(self, datos: Dict[str, Any] = None, **kwargs) -> str:
        """Crea un nuevo camión en la base de datos."""
        return self.insertar("trucks", datos, **kwargs)

    def obtener_camiones(self) -> List[Dict[str, Any]]:
        """Retorna todos los camiones registrados."""
        return self.obtener_todos("trucks")

    def obtener_camion_por_id(self, camion_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene los datos de un camión por su ID."""
        return self.obtener_por_id("trucks", camion_id)

    def buscar_camiones_por_variable(self, clave: str, valor: Any) -> List[Dict[str, Any]]:
        """Busca camiones filtrando por cualquier variable dinámica."""
        return self.obtener_todos("trucks", {clave: valor})

    def actualizar_camion(self, camion_id: str, datos: Dict[str, Any] = None, **kwargs) -> bool:
        """Actualiza valores o agrega nuevas variables a un camión."""
        return self.actualizar("trucks", camion_id, datos, **kwargs)

    def eliminar_camion(self, camion_id: str) -> bool:
        """Elimina un camión por su ID."""
        return self.eliminar("trucks", camion_id)

    def agregar_variable_camion(self, camion_id: str, nombre_variable: str, valor: Any) -> bool:
        """Agrega una nueva variable personalizada a un camión."""
        return self.actualizar_camion(camion_id, **{nombre_variable: valor})

    def eliminar_variable_camion(self, camion_id: str, nombre_variable: str) -> bool:
        """Elimina una variable específica de un camión."""
        return self.eliminar_campo("trucks", camion_id, nombre_variable)

    # =========================================================================
    # 2. CHOFERES (CRUD en Español)
    # =========================================================================

    def agregar_chofer(self, datos: Dict[str, Any] = None, **kwargs) -> str:
        return self.insertar("drivers", datos, **kwargs)

    def obtener_choferes(self) -> List[Dict[str, Any]]:
        return self.obtener_todos("drivers")

    def obtener_chofer_por_id(self, chofer_id: str) -> Optional[Dict[str, Any]]:
        return self.obtener_por_id("drivers", chofer_id)

    def actualizar_chofer(self, chofer_id: str, datos: Dict[str, Any] = None, **kwargs) -> bool:
        return self.actualizar("drivers", chofer_id, datos, **kwargs)

    def eliminar_chofer(self, chofer_id: str) -> bool:
        return self.eliminar("drivers", chofer_id)

    # =========================================================================
    # 3. RUTAS (CRUD en Español)
    # =========================================================================

    def agregar_ruta(self, datos: Dict[str, Any] = None, **kwargs) -> str:
        return self.insertar("routes", datos, **kwargs)

    def obtener_rutas(self) -> List[Dict[str, Any]]:
        return self.obtener_todos("routes")

    def obtener_ruta_por_id(self, ruta_id: str) -> Optional[Dict[str, Any]]:
        return self.obtener_por_id("routes", ruta_id)

    def actualizar_ruta(self, ruta_id: str, datos: Dict[str, Any] = None, **kwargs) -> bool:
        return self.actualizar("routes", ruta_id, datos, **kwargs)

    def eliminar_ruta(self, ruta_id: str) -> bool:
        return self.eliminar("routes", ruta_id)

    # =========================================================================
    # 4. GEOCERCAS (CRUD en Español)
    # =========================================================================

    def agregar_geocerca(self, datos: Dict[str, Any] = None, **kwargs) -> str:
        payload = dict(datos) if isinstance(datos, dict) else {}
        payload.update(kwargs)
        if "polygon" in payload and "geometry" not in payload:
            payload["geometry"] = {"type": "Polygon", "coordinates": [payload.pop("polygon")]}
        return self.insertar("geofences", payload)

    def obtener_geocercas(self) -> List[Dict[str, Any]]:
        return self.obtener_todos("geofences")

    def obtener_geocerca_por_id(self, geocerca_id: str) -> Optional[Dict[str, Any]]:
        return self.obtener_por_id("geofences", geocerca_id)

    def actualizar_geocerca(self, geocerca_id: str, datos: Dict[str, Any] = None, **kwargs) -> bool:
        payload = dict(datos) if isinstance(datos, dict) else {}
        payload.update(kwargs)
        if "polygon" in payload:
            payload["geometry"] = {"type": "Polygon", "coordinates": [payload.pop("polygon")]}
        return self.actualizar("geofences", geocerca_id, payload)

    def eliminar_geocerca(self, geocerca_id: str) -> bool:
        return self.eliminar("geofences", geocerca_id)

    # =========================================================================
    # 5. TELEMETRÍA & RESUMEN DE FLOTA
    # =========================================================================

    def agregar_telemetria(self, datos: Dict[str, Any] = None, **kwargs) -> str:
        payload = dict(datos) if isinstance(datos, dict) else {}
        payload.update(kwargs)
        if "lon" in payload and "lat" in payload and "location" not in payload:
            lon, lat = payload.pop("lon"), payload.pop("lat")
            if lon is not None and lat is not None:
                payload["location"] = {"type": "Point", "coordinates": [lon, lat]}
        return self.insertar("telemetry", payload)

    def obtener_telemetria(self, camion_id: str) -> List[Dict[str, Any]]:
        return [self._limpiar_documento(d) for d in self.telemetria.find({"truck_id": camion_id}).sort("timestamp", 1)]

    def obtener_telemetria_por_id(self, telemetria_id: str) -> Optional[Dict[str, Any]]:
        return self.obtener_por_id("telemetry", telemetria_id)

    def actualizar_telemetria(self, telemetria_id: str, datos: Dict[str, Any] = None, **kwargs) -> bool:
        return self.actualizar("telemetry", telemetria_id, datos, **kwargs)

    def eliminar_telemetria(self, telemetria_id: str) -> bool:
        return self.eliminar("telemetry", telemetria_id)

    def obtener_resumen_flota(self) -> Dict[str, Any]:
        """Calcula el resumen de totales y alertas de la flota."""
        excesos = self.telemetria.count_documents({"speed_kmh": {"$gt": 100}})
        temp_altas = self.telemetria.count_documents({"engine_temp_c": {"$gt": 95}})
        return {
            "total_camiones": self.camiones.count_documents({}),
            "total_choferes": self.choferes.count_documents({}),
            "total_rutas": self.rutas.count_documents({}),
            "total_telemetria": self.telemetria.count_documents({}),
            "alertas": {
                "exceso_velocidad": excesos,
                "sobrecalentamiento": temp_altas,
                "total_alertas": excesos + temp_altas
            }
        }

    def obtener_alertas_recientes(self, limite: int = 10) -> List[Dict[str, Any]]:
        filtro = {"$or": [{"speed_kmh": {"$gt": 100}}, {"engine_temp_c": {"$gt": 95}}, {"fuel_level_pct": {"$lt": 15}}]}
        return [self._limpiar_documento(d) for d in self.telemetria.find(filtro).sort("timestamp", -1).limit(limite)]

    # =========================================================================
    # ALIASES DE COMPATIBILIDAD EN INGLÉS (Garantizan cero ruptura)
    # =========================================================================
    def add_truck(self, *a, **kw): return self.agregar_camion(*a, **kw)
    def get_trucks(self, *a, **kw): return self.obtener_camiones(*a, **kw)
    def get_truck_by_id(self, *a, **kw): return self.obtener_camion_por_id(*a, **kw)
    def get_trucks_by_variable(self, *a, **kw): return self.buscar_camiones_por_variable(*a, **kw)
    def update_truck(self, *a, **kw): return self.actualizar_camion(*a, **kw)
    def delete_truck(self, *a, **kw): return self.eliminar_camion(*a, **kw)
    def add_variable_to_truck(self, *a, **kw): return self.agregar_variable_camion(*a, **kw)
    def delete_variable_from_truck(self, *a, **kw): return self.eliminar_variable_camion(*a, **kw)
    def add_driver(self, *a, **kw): return self.agregar_chofer(*a, **kw)
    def get_drivers(self, *a, **kw): return self.obtener_choferes(*a, **kw)
    def get_driver_by_id(self, *a, **kw): return self.obtener_chofer_por_id(*a, **kw)
    def update_driver(self, *a, **kw): return self.actualizar_chofer(*a, **kw)
    def delete_driver(self, *a, **kw): return self.eliminar_chofer(*a, **kw)
    def add_route(self, *a, **kw): return self.agregar_ruta(*a, **kw)
    def get_routes(self, *a, **kw): return self.obtener_rutas(*a, **kw)
    def get_route_by_id(self, *a, **kw): return self.obtener_ruta_por_id(*a, **kw)
    def update_route(self, *a, **kw): return self.actualizar_ruta(*a, **kw)
    def delete_route(self, *a, **kw): return self.eliminar_ruta(*a, **kw)
    def add_geofence(self, *a, **kw): return self.agregar_geocerca(*a, **kw)
    def get_geofences(self, *a, **kw): return self.obtener_geocercas(*a, **kw)
    def get_geofence_by_id(self, *a, **kw): return self.obtener_geocerca_por_id(*a, **kw)
    def update_geofence(self, *a, **kw): return self.actualizar_geocerca(*a, **kw)
    def delete_geofence(self, *a, **kw): return self.eliminar_geocerca(*a, **kw)
    def add_telemetry(self, *a, **kw): return self.agregar_telemetria(*a, **kw)
    def get_telemetry(self, *a, **kw): return self.obtener_telemetria(*a, **kw)
    def get_telemetry_by_id(self, *a, **kw): return self.obtener_telemetria_por_id(*a, **kw)
    def update_telemetry(self, *a, **kw): return self.actualizar_telemetria(*a, **kw)
    def delete_telemetry(self, *a, **kw): return self.eliminar_telemetria(*a, **kw)
    def get_fleet_summary(self, *a, **kw): return self.obtener_resumen_flota(*a, **kw)
    def get_recent_alerts(self, *a, **kw): return self.obtener_alertas_recientes(*a, **kw)
    def bulk_add_telemetry(self, lecturas): return [str(i) for i in self.telemetria.insert_many(lecturas, ordered=False).inserted_ids]
    def get_truck_statistics(self, camion_id):
        res = list(self.telemetria.aggregate([{"$match": {"truck_id": camion_id}}, {"$group": {"_id": "$truck_id", "velocidad_promedio": {"$avg": "$speed_kmh"}, "temp_maxima": {"$max": "$engine_temp_c"}, "combustible_promedio": {"$avg": "$fuel_level_pct"}, "total_lecturas": {"$sum": 1}}}]))
        return self._limpiar_documento(res[0]) if res else {}
