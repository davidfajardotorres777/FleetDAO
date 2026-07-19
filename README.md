# FleetDAO
Sistema Avanzado de Gestion de Flotas y Telemetria

Autor: Alesandro David Fajardo Torres
Materia: Bases de Datos II - Proyecto Integrador 2026

---

## 1. El Problema

Las empresas de logistica y transporte pierden millones de pesos al año por no controlar como se manejan sus camiones. El exceso de velocidad, las rutas ineficientes y los motores sobrecalentados son gastos ocultos gigantescos. Los sistemas GPS tradicionales te dicen donde esta el camion, pero no analizan los datos mecanicos ni te ayudan a prevenir roturas.

FleetDAO es una solucion completa a este problema. Es un sistema capaz de recibir, guardar y analizar la telemetria (ubicacion, velocidad, rpm, temperatura) de cientos de camiones en tiempo real. 

## 2. Herramientas y Arquitectura

Para que el proyecto escale bien y sea rapido, arme esta estructura:

*   **MongoDB (4.4)**: Base de datos NoSQL principal. Ideal para guardar muchisimos datos por segundo (series temporales).
*   **Indices Geoespaciales (2dsphere)**: Mongo permite hacer busquedas por ubicacion (ej. "dame todos los camiones a 10km de este punto").
*   **Aggregation Pipelines**: Uso comandos de Mongo como `$group`, `$avg` y `$max` para calcular promedios directamente en la base de datos sin saturar la memoria de Python.
*   **FastAPI & Pydantic**: El backend que recibe los datos. Pydantic asegura que ningun camion mande datos corruptos (como velocidades de 500km/h).
*   **Jupyter, Folium y Matplotlib**: Un entorno de analisis de datos para mapear las rutas interactivamente y ver graficos de rendimiento del motor.

## 3. Estructura de la Base de Datos

El sistema usa 4 colecciones principales.

### Colecciones:
1. **trucks (Camiones):** Guarda la informacion estatica del vehiculo (marca, capacidad en toneladas).
2. **drivers (Choferes):** Guarda los datos del empleado y su tipo de licencia.
3. **routes (Rutas):** Asigna un camion y un chofer a un viaje desde un origen a un destino.
4. **telemetry (Telemetria):** La coleccion mas pesada. Guarda un registro cada pocos segundos de cada camion (timestamp, velocidad, temperatura, nivel de combustible y coordenadas exactas).

### Indices de la Base de Datos:
Para que las consultas sean rapidas, cree indices especiales en el archivo `dao.py`:
*   **Indice unico compuesto**: `[("truck_id", 1), ("timestamp", 1)]` -> Para que no se guarde el mismo dato dos veces si hay un error de red.
*   **Indice Geoespacial**: `[("location", "2dsphere")]` -> Para que funcionen los mapas y la busqueda por radio espacial.

---

## 4. Archivos del Proyecto

*   `db_models/` -> Todas las clases de Pydantic que validan la informacion de entrada.
*   `dao.py` -> El Data Access Object. Aca esta toda la logica de conexion y consultas a MongoDB.
*   `main.py` -> API construida en FastAPI.
*   `seed.py` -> Script para llenar la base de datos con camiones y generar un viaje de prueba.
*   `demo.ipynb` / `demo.html` -> El Notebook con el analisis geoespacial y los graficos.
*   `docker-compose.yml` -> Para levantar la base de datos con un simple comando.

---

## 5. Guia de Instalacion y Uso

Necesitas tener Python 3 y Docker instalados en tu computadora.

**Paso 1:** Clonar el proyecto y entrar a la carpeta.
```bash
git clone https://github.com/davidfajardotorres777/FleetDAO.git
cd FleetDAO
```

**Paso 2:** Crear el entorno virtual e instalar librerias.
```bash
python -m venv venv
# En windows: venv\Scripts\activate
# En linux/mac: source venv/bin/activate
pip install -r libs.txt
```

**Paso 3:** Configurar las variables.
Crea un archivo llamado `.env` en la raiz del proyecto con este texto:
```text
MONGO_URI=mongodb://localhost:27017/
DB_NAME=fleet_db
```

**Paso 4:** Levantar la base de datos (MongoDB).
```bash
docker compose up -d
```

**Paso 5:** Cargar los datos de prueba (Camiones y Rutas).
```bash
python seed.py
```

**Paso 6:** Probar la API de FastAPI.
Para levantar el servidor y probar las funciones del backend en vivo:
```bash
uvicorn main:app --reload
```
Una vez que este corriendo, abri tu navegador y entra a `http://localhost:8000/docs`. Ahi vas a ver toda la interfaz interactiva (Swagger UI) para probar la API sin programar nada extra.

**Paso 7:** Ver los graficos y mapas (Data Science).
Si solo queres ver los resultados visuales, dale doble click al archivo `demo.html` para abrirlo en tu navegador. 
Si queres ejecutar el codigo paso a paso, cerra el servidor de FastAPI, y en esa misma consola corre:
```bash
jupyter notebook
```
Y luego hace click en el archivo `demo.ipynb`.

---

## 6. Ejemplos de uso (Llamadas al DAO)

Si queres usar el codigo desde otro archivo de Python, asi funciona el modelo:

```python
from dao import FleetDAO

# 1. Me conecto a la base de datos
db = FleetDAO()

# 2. Busco todos los camiones
camiones = db.get_trucks()
camion_id = str(camiones[0]["_id"])

# 3. Saco las estadisticas de ese camion (usa Aggregation Pipelines internamente)
stats = db.get_truck_statistics(camion_id)
print(f"Velocidad Promedio: {stats['velocidad_promedio']} km/h")

# 4. Busco si el camion anduvo cerca de unas coordenadas (usa 2dsphere)
datos_cercanos = db.get_telemetry_near(camion_id, lon=-61.0, lat=-33.0, max_distance_meters=50000)
```
