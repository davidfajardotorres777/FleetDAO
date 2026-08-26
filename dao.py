import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import MongoClient

from config_vars import MONGO_URI, DB_NAME

# Configuración básica de registros de sistema (logs)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FleetDAO")


class FleetDAO:
    """
    Data Access Object (DAO) para la Gestión de Flotas y Telemetría en MongoDB.

    Esta clase proporciona una interfaz simple, limpia y ordenada para interactuar
    con la base de datos 'fleet_db' de MongoDB.
    """

    def __init__(self):
        """
        Inicializa la conexión con el servidor de MongoDB y establece
        las referencias a las colecciones principales.
        """
        try:
            # Conexión al servidor de MongoDB
            self.cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.base_de_datos = self.cliente[DB_NAME]

            # -----------------------------------------------------------------
            # Colecciones Principales de MongoDB (en Español)
            # -----------------------------------------------------------------
            self.camiones = self.base_de_datos["trucks"]
            self.choferes = self.base_de_datos["drivers"]
            self.rutas = self.base_de_datos["routes"]
            self.geocercas = self.base_de_datos["geofences"]
            self.telemetria = self.base_de_datos["telemetry"]

            # Aliases en inglés para garantizar compatibilidad con otros módulos
            self.trucks = self.camiones
            self.drivers = self.choferes
            self.routes = self.rutas
            self.geofences = self.geocercas
            self.telemetry = self.telemetria

            # -----------------------------------------------------------------
            # Creación de Índices de Búsqueda
            # -----------------------------------------------------------------
            self.telemetria.create_index([("truck_id", 1), ("timestamp", 1)], unique=True)
            self.telemetria.create_index([("location", "2dsphere")])

            logger.info("✔ Conexión exitosa a MongoDB e índices verificados correctamente.")

        except Exception as error:
            logger.error(f"❌ Error al conectar con la base de datos MongoDB: {error}")
            raise

    def __enter__(self):
        """Permite usar la clase con la sintaxis 'with FleetDAO() as dao:'."""
        return self

    def __exit__(self, tipo_error, valor_error, traza_error):
        """Cierra automáticamente la conexión al salir del bloque 'with'."""
        self.cerrar_conexion()

    def cerrar_conexion(self):
        """
        Cierra de forma segura la conexión activa con el servidor de MongoDB.
        """
        self.cliente.close()
        logger.info("✔ Conexión a MongoDB cerrada de forma segura.")

    def close(self):
        """Alias para cerrar la conexión."""
        self.cerrar_conexion()

    # =========================================================================
    # MÉTODOS AUXILIARES INTERNOS
    # =========================================================================

    @staticmethod
    def _convertir_a_object_id(id_texto: str) -> Optional[ObjectId]:
        """
        Convierte una cadena de texto a un identificador nativo ObjectId de MongoDB.
        """
        if not id_texto:
            return None

        if isinstance(id_texto, ObjectId):
            return id_texto

        if ObjectId.is_valid(str(id_texto)):
            return ObjectId(str(id_texto))

        return None

    @staticmethod
    def _limpiar_documento_para_json(documento: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Convierte el identificador '_id' de MongoDB a una cadena de texto
        para que pueda ser enviado por la API REST o convertido a JSON sin errores.
        """
        if documento and "_id" in documento:
            documento["_id"] = str(documento["_id"])
            documento["id"] = documento["_id"]

        return documento

    # =========================================================================
    # OPERACIONES BÁSICAS GENÉRICAS (CRUD GENÉRICO)
    # =========================================================================

    def insertar_documento(self, nombre_coleccion: str, datos: Dict[str, Any] = None, **kwargs) -> str:
        """
        Inserta un nuevo documento en cualquier colección indicada.
        """
        paquete_datos = dict(datos) if isinstance(datos, dict) else {}
        paquete_datos.update(kwargs)

        if not paquete_datos:
            raise ValueError("No se proporcionaron datos para insertar.")

        resultado = self.base_de_datos[nombre_coleccion].insert_one(paquete_datos)
        return str(resultado.inserted_id)

    def obtener_todos_los_documentos(self, nombre_coleccion: str, filtro: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Retorna la lista de todos los documentos de una colección que coincidan con el filtro.
        """
        cursor_documentos = self.base_de_datos[nombre_coleccion].find(filtro or {})
        return [self._limpiar_documento_para_json(doc) for doc in cursor_documentos]

    def obtener_documento_por_id(self, nombre_coleccion: str, id_documento: str) -> Optional[Dict[str, Any]]:
        """
        Busca y retorna un único documento a partir de su ID de MongoDB.
        """
        object_id = self._convertir_a_object_id(id_documento)
        if not object_id:
            return None

        documento = self.base_de_datos[nombre_coleccion].find_one({"_id": object_id})
        return self._limpiar_documento_para_json(documento)

    def actualizar_documento(self, nombre_coleccion: str, id_documento: str, datos: Dict[str, Any] = None, **kwargs) -> bool:
        """
        Actualiza valores existentes o agrega nuevas variables dinámicas usando el operador $set de MongoDB.
        """
        object_id = self._convertir_a_object_id(id_documento)
        if not object_id:
            return False

        paquete_actualizacion = dict(datos) if isinstance(datos, dict) else {}
        paquete_actualizacion.update(kwargs)

        # Remover campos protegidos si se pasaron por error
        paquete_actualizacion.pop("_id", None)
        paquete_actualizacion.pop("id", None)

        if not paquete_actualizacion:
            return False

        resultado = self.base_de_datos[nombre_coleccion].update_one(
            {"_id": object_id},
            {"$set": paquete_actualizacion}
        )

        return resultado.modified_count > 0 or resultado.matched_count > 0

    def eliminar_documento(self, nombre_coleccion: str, id_documento: str) -> bool:
        """
        Elimina un documento completo de la base de datos según su ID.
        """
        object_id = self._convertir_a_object_id(id_documento)
        if not object_id:
            return False

        resultado = self.base_de_datos[nombre_coleccion].delete_one({"_id": object_id})
        return resultado.deleted_count > 0

    def eliminar_variable_de_documento(self, nombre_coleccion: str, id_documento: str, nombre_variable: str) -> bool:
        """
        Elimina una variable o campo específico de un documento usando el operador $unset de MongoDB.
        """
        object_id = self._convertir_a_object_id(id_documento)
        if not object_id:
            return False

        resultado = self.base_de_datos[nombre_coleccion].update_one(
            {"_id": object_id},
            {"$unset": {nombre_variable: ""}}
        )

        return resultado.modified_count > 0

    # =========================================================================
    # SECCIÓN 1: GESTIÓN DE CAMIONES (TRUCKS)
    # =========================================================================

    def agregar_camion(self, datos_camion: Dict[str, Any] = None, **kwargs) -> str:
        """
        [CREAR CAMIÓN] Registra un nuevo camión en la colección 'trucks'.
        Permite pasar los datos como un diccionario o como argumentos individuales.
        """
        return self.insertar_documento("trucks", datos_camion, **kwargs)

    def obtener_camiones(self) -> List[Dict[str, Any]]:
        """
        [LEER CAMIONES] Retorna la lista completa de camiones guardados en MongoDB.
        """
        return self.obtener_todos_los_documentos("trucks")

    def obtener_camion_por_id(self, camion_id: str) -> Optional[Dict[str, Any]]:
        """
        [LEER UN CAMIÓN] Busca un camión específico por su ID único.
        """
        return self.obtener_documento_por_id("trucks", camion_id)

    def buscar_camiones_por_variable(self, nombre_variable: str, valor_variable: Any) -> List[Dict[str, Any]]:
        """
        [BUSCAR CAMIONES] Filtra camiones por el valor de cualquier variable dinámica personalizada.
        """
        return self.obtener_todos_los_documentos("trucks", {nombre_variable: valor_variable})

    def actualizar_camion(self, camion_id: str, datos_actualizacion: Dict[str, Any] = None, **kwargs) -> bool:
        """
        [ACTUALIZAR CAMIÓN] Modifica datos existentes o agrega nuevas variables a un camión.
        """
        return self.actualizar_documento("trucks", camion_id, datos_actualizacion, **kwargs)

    def eliminar_camion(self, camion_id: str) -> bool:
        """
        [ELIMINAR CAMIÓN] Elimina un camión completo de MongoDB.
        """
        return self.eliminar_documento("trucks", camion_id)

    def agregar_variable_camion(self, camion_id: str, nombre_variable: str, valor_variable: Any) -> bool:
        """
        [AGREGAR VARIABLE] Agrega una nueva variable dinámicamente a un camión.
        """
        return self.actualizar_camion(camion_id, **{nombre_variable: valor_variable})

    def eliminar_variable_camion(self, camion_id: str, nombre_variable: str) -> bool:
        """
        [ELIMINAR VARIABLE] Elimina una variable específica de un camión sin borrar el camión.
        """
        return self.eliminar_variable_de_documento("trucks", camion_id, nombre_variable)

    # =========================================================================
    # SECCIÓN 2: GESTIÓN DE CHOFERES (DRIVERS)
    # =========================================================================

    def agregar_chofer(self, datos_chofer: Dict[str, Any] = None, **kwargs) -> str:
        """
        [CREAR CHOFER] Registra un nuevo conductor en MongoDB.
        """
        return self.insertar_documento("drivers", datos_chofer, **kwargs)

    def obtener_choferes(self) -> List[Dict[str, Any]]:
        """
        [LEER CHOFERES] Retorna la lista de todos los choferes.
        """
        return self.obtener_todos_los_documentos("drivers")

    def obtener_chofer_por_id(self, chofer_id: str) -> Optional[Dict[str, Any]]:
        """
        [LEER UN CHOFER] Obtiene los datos de un chofer por su ID.
        """
        return self.obtener_documento_por_id("drivers", chofer_id)

    def actualizar_chofer(self, chofer_id: str, datos_actualizacion: Dict[str, Any] = None, **kwargs) -> bool:
        """
        [ACTUALIZAR CHOFER] Modifica los datos de un chofer.
        """
        return self.actualizar_documento("drivers", chofer_id, datos_actualizacion, **kwargs)

    def eliminar_chofer(self, chofer_id: str) -> bool:
        """
        [ELIMINAR CHOFER] Elimina un chofer de la base de datos.
        """
        return self.eliminar_documento("drivers", chofer_id)

    # =========================================================================
    # SECCIÓN 3: GESTIÓN DE RUTAS LOGÍSTICAS (ROUTES)
    # =========================================================================

    def agregar_ruta(self, datos_ruta: Dict[str, Any] = None, **kwargs) -> str:
        """
        [CREAR RUTA] Asigna una nueva ruta logística.
        """
        return self.insertar_documento("routes", datos_ruta, **kwargs)

    def obtener_rutas(self) -> List[Dict[str, Any]]:
        """
        [LEER RUTAS] Retorna todas las rutas registradas.
        """
        return self.obtener_todos_los_documentos("routes")

    def obtener_ruta_por_id(self, ruta_id: str) -> Optional[Dict[str, Any]]:
        """
        [LEER UNA RUTA] Obtiene una ruta logística por su ID.
        """
        return self.obtener_documento_por_id("routes", ruta_id)

    def actualizar_ruta(self, ruta_id: str, datos_actualizacion: Dict[str, Any] = None, **kwargs) -> bool:
        """
        [ACTUALIZAR RUTA] Actualiza la información de una ruta.
        """
        return self.actualizar_documento("routes", ruta_id, datos_actualizacion, **kwargs)

    def eliminar_ruta(self, ruta_id: str) -> bool:
        """
        [ELIMINAR RUTA] Elimina una ruta logística.
        """
        return self.eliminar_documento("routes", ruta_id)

    # =========================================================================
    # SECCIÓN 4: GESTIÓN DE GEOCERCAS ESPACIALES (GEOFENCES)
    # =========================================================================

    def agregar_geocerca(self, datos_geocerca: Dict[str, Any] = None, **kwargs) -> str:
        """
        [CREAR GEOCERCA] Registra una geocerca espacial en formato GeoJSON.
        """
        paquete_datos = dict(datos_geocerca) if isinstance(datos_geocerca, dict) else {}
        paquete_datos.update(kwargs)

        if "polygon" in paquete_datos and "geometry" not in paquete_datos:
            paquete_datos["geometry"] = {"type": "Polygon", "coordinates": [paquete_datos.pop("polygon")]}

        return self.insertar_documento("geofences", paquete_datos)

    def obtener_geocercas(self) -> List[Dict[str, Any]]:
        """
        [LEER GEOCERCAS] Obtiene la lista completa de geocercas.
        """
        return self.obtener_todos_los_documentos("geofences")

    def obtener_geocerca_por_id(self, geocerca_id: str) -> Optional[Dict[str, Any]]:
        """
        [LEER UNA GEOCERCA] Obtiene una geocerca específica por su ID.
        """
        return self.obtener_documento_por_id("geofences", geocerca_id)

    def actualizar_geocerca(self, geocerca_id: str, datos_actualizacion: Dict[str, Any] = None, **kwargs) -> bool:
        """
        [ACTUALIZAR GEOCERCA] Modifica las coordenadas o datos de una geocerca.
        """
        paquete_datos = dict(datos_actualizacion) if isinstance(datos_actualizacion, dict) else {}
        paquete_datos.update(kwargs)

        if "polygon" in paquete_datos:
            paquete_datos["geometry"] = {"type": "Polygon", "coordinates": [paquete_datos.pop("polygon")]}

        return self.actualizar_documento("geofences", geocerca_id, paquete_datos)

    def eliminar_geocerca(self, geocerca_id: str) -> bool:
        """
        [ELIMINAR GEOCERCA] Elimina una geocerca por ID.
        """
        return self.eliminar_documento("geofences", geocerca_id)

    # =========================================================================
    # SECCIÓN 5: GESTIÓN DE TELEMETRÍA IOT Y ALERTAS (TELEMETRY)
    # =========================================================================

    def agregar_telemetria(self, datos_telemetria: Dict[str, Any] = None, **kwargs) -> str:
        """
        [REGISTRAR TELEMETRÍA] Guarda una lectura de sensores IoT y GPS.
        """
        paquete_datos = dict(datos_telemetria) if isinstance(datos_telemetria, dict) else {}
        paquete_datos.update(kwargs)

        if "lon" in paquete_datos and "lat" in paquete_datos and "location" not in paquete_datos:
            longitud, latitud = paquete_datos.pop("lon"), paquete_datos.pop("lat")
            if longitud is not None and latitud is not None:
                paquete_datos["location"] = {"type": "Point", "coordinates": [longitud, latitud]}

        return self.insertar_documento("telemetry", paquete_datos)

    def obtener_telemetria(self, camion_id: str) -> List[Dict[str, Any]]:
        """
        [OBTENER TELEMETRÍA] Retorna la serie temporal de lecturas ordenadas por fecha para un camión.
        """
        cursor_telemetria = self.telemetria.find({"truck_id": camion_id}).sort("timestamp", 1)
        return [self._limpiar_documento_para_json(doc) for doc in cursor_telemetria]

    def obtener_telemetria_por_id(self, telemetria_id: str) -> Optional[Dict[str, Any]]:
        """
        [OBTENER UNA LECTURA] Busca un registro de telemetría específico por su ID.
        """
        return self.obtener_documento_por_id("telemetry", telemetria_id)

    def actualizar_telemetria(self, telemetria_id: str, datos_actualizacion: Dict[str, Any] = None, **kwargs) -> bool:
        """
        [ACTUALIZAR TELEMETRÍA] Modifica o agrega datos a una lectura de telemetría.
        """
        return self.actualizar_documento("telemetry", telemetria_id, datos_actualizacion, **kwargs)

    def eliminar_telemetria(self, telemetria_id: str) -> bool:
        """
        [ELIMINAR TELEMETRÍA] Elimina una lectura de telemetría.
        """
        return self.eliminar_documento("telemetry", telemetria_id)

    def obtener_resumen_flota(self) -> Dict[str, Any]:
        """
        [RESUMEN EJECUTIVO] Calcula el total de elementos en la flota y cuenta las alertas activas.
        """
        excesos_velocidad = self.telemetria.count_documents({"speed_kmh": {"$gt": 100}})
        sobrecalentamientos = self.telemetria.count_documents({"engine_temp_c": {"$gt": 95}})

        return {
            "total_camiones": self.camiones.count_documents({}),
            "total_choferes": self.choferes.count_documents({}),
            "total_rutas": self.rutas.count_documents({}),
            "total_telemetria": self.telemetria.count_documents({}),
            "alertas": {
                "exceso_velocidad": excesos_velocidad,
                "sobrecalentamiento": sobrecalentamientos,
                "total_alertas": excesos_velocidad + sobrecalentamientos
            }
        }

    def obtener_alertas_recientes(self, limite: int = 10, limit: int = None) -> List[Dict[str, Any]]:
        """
        [ALERTAS RECIENTES] Recupera las últimas lecturas con exceso de velocidad, temperatura alta o poco combustible.
        """
        cant_limite = limit if limit is not None else limite

        filtro_alertas = {
            "$or": [
                {"speed_kmh": {"$gt": 100}},
                {"engine_temp_c": {"$gt": 95}},
                {"fuel_level_pct": {"$lt": 15}}
            ]
        }
        cursor_alertas = self.telemetria.find(filtro_alertas).sort("timestamp", -1).limit(cant_limite)
        return [self._limpiar_documento_para_json(doc) for doc in cursor_alertas]

    # =========================================================================
    # ALIASES DE COMPATIBILIDAD EN INGLÉS (Garantizan cero ruptura de código)
    # =========================================================================

    def add_truck(self, *args, **kwargs):
        return self.agregar_camion(*args, **kwargs)

    def get_trucks(self, *args, **kwargs):
        return self.obtener_camiones(*args, **kwargs)

    def get_truck_by_id(self, *args, **kwargs):
        return self.obtener_camion_por_id(*args, **kwargs)

    def get_trucks_by_variable(self, *args, **kwargs):
        return self.buscar_camiones_por_variable(*args, **kwargs)

    def update_truck(self, *args, **kwargs):
        return self.actualizar_camion(*args, **kwargs)

    def delete_truck(self, *args, **kwargs):
        return self.eliminar_camion(*args, **kwargs)

    def add_variable_to_truck(self, *args, **kwargs):
        return self.agregar_variable_camion(*args, **kwargs)

    def delete_variable_from_truck(self, *args, **kwargs):
        return self.eliminar_variable_camion(*args, **kwargs)

    def add_driver(self, *args, **kwargs):
        return self.agregar_chofer(*args, **kwargs)

    def get_drivers(self, *args, **kwargs):
        return self.obtener_choferes(*args, **kwargs)

    def get_driver_by_id(self, *args, **kwargs):
        return self.obtener_chofer_por_id(*args, **kwargs)

    def update_driver(self, *args, **kwargs):
        return self.actualizar_chofer(*args, **kwargs)

    def delete_driver(self, *args, **kwargs):
        return self.eliminar_chofer(*args, **kwargs)

    def add_route(self, *args, **kwargs):
        return self.agregar_ruta(*args, **kwargs)

    def get_routes(self, *args, **kwargs):
        return self.obtener_rutas(*args, **kwargs)

    def get_route_by_id(self, *args, **kwargs):
        return self.obtener_ruta_por_id(*args, **kwargs)

    def update_route(self, *args, **kwargs):
        return self.actualizar_ruta(*args, **kwargs)

    def delete_route(self, *args, **kwargs):
        return self.eliminar_ruta(*args, **kwargs)

    def add_geofence(self, *args, **kwargs):
        return self.agregar_geocerca(*args, **kwargs)

    def get_geofences(self, *args, **kwargs):
        return self.obtener_geocercas(*args, **kwargs)

    def get_geofence_by_id(self, *args, **kwargs):
        return self.obtener_geocerca_por_id(*args, **kwargs)

    def update_geofence(self, *args, **kwargs):
        return self.actualizar_geocerca(*args, **kwargs)

    def delete_geofence(self, *args, **kwargs):
        return self.eliminar_geocerca(*args, **kwargs)

    def add_telemetry(self, *args, **kwargs):
        return self.agregar_telemetria(*args, **kwargs)

    def get_telemetry(self, *args, **kwargs):
        return self.obtener_telemetria(*args, **kwargs)

    def get_telemetry_by_id(self, *args, **kwargs):
        return self.obtener_telemetria_por_id(*args, **kwargs)

    def update_telemetry(self, *args, **kwargs):
        return self.actualizar_telemetria(*args, **kwargs)

    def delete_telemetry(self, *args, **kwargs):
        return self.eliminar_telemetria(*args, **kwargs)

    def get_fleet_summary(self, *args, **kwargs):
        return self.obtener_resumen_flota(*args, **kwargs)

    def get_recent_alerts(self, *args, **kwargs):
        return self.obtener_alertas_recientes(*args, **kwargs)

    def bulk_add_telemetry(self, lecturas):
        resultado = self.telemetria.insert_many(lecturas, ordered=False)
        return [str(i) for i in resultado.inserted_ids]

    def get_truck_statistics(self, camion_id):
        pipeline = [
            {"$match": {"truck_id": camion_id}},
            {
                "$group": {
                    "_id": "$truck_id",
                    "velocidad_promedio": {"$avg": "$speed_kmh"},
                    "temp_maxima": {"$max": "$engine_temp_c"},
                    "combustible_promedio": {"$avg": "$fuel_level_pct"},
                    "total_lecturas": {"$sum": 1}
                }
            }
        ]
        resultado = list(self.telemetria.aggregate(pipeline))
        return self._limpiar_documento_para_json(resultado[0]) if resultado else {}
