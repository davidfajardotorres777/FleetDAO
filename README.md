# FleetDAO
### Sistema Avanzado de Gestión de Flotas y Telemetría Predictiva

Proyecto Integrador — Bases de Datos II · 2026

## Equipo de Trabajo / Contributors
* **Alesandro David Fajardo Torres** - [@davidfajardotorres777](https://github.com/davidfajardotorres777)

---

## 1. De qué trata el proyecto

En las empresas de transporte, muchas veces no hay un control en tiempo real del estado de los camiones. Problemas como el exceso de velocidad o el sobrecalentamiento del motor causan muchos gastos si no se detectan a tiempo. Los GPS normales solo dicen dónde está el camión, pero no avisan sobre problemas mecánicos o rutas.

**FleetDAO** es un sistema desarrollado para la materia **Bases de Datos II**. Su objetivo es recibir, guardar y mostrar datos de los camiones en vivo (ubicación, velocidad, RPM y temperatura), y además usa un modelo predictivo para tratar de adivinar si el motor se va a sobrecalentar, todo esto apoyándose fuertemente en el patrón DAO.

---

## 2. Herramientas y Tecnologías Usadas

Para armar el proyecto, integré varias herramientas para que quede lo más completo posible:

*   **MongoDB**: Usado como la base de datos principal, ya que es muy buena para guardar un montón de datos por segundo (como la telemetría del GPS).
*   **Redis**: Lo usé como una memoria caché rápida para poder ver la última posición del camión sin tener que saturar a Mongo.
*   **MinIO**: Sirve para guardar archivos (como fotos de licencias) y hacer los backups automáticos de la base de datos.
*   **FastAPI & WebSockets**: Usado para armar la API REST. Además le agregué JWT para que tenga seguridad, y WebSockets para que los datos del mapa se actualicen en vivo.
*   **Machine Learning (Scikit-Learn)**: Entrené un pequeño modelo de IA que adivina la temperatura del motor basándose en las RPM y la velocidad.
*   **Streamlit & Folium (Dashboard)**: La página web donde se muestran los mapas y los gráficos.
*   **Simulador de Camiones**: Hice un script (`simulator.py`) que inventa datos de camiones moviéndose para poder probar que todo funciona bien.
*   **Prometheus & Grafana**: Herramientas extra para monitorear qué tanto está trabajando el servidor y la memoria.
*   **GitHub Actions**: Para que se corran los tests solos cada vez que subo un cambio.

---

## 3. Estructura de la Base de Datos

El sistema tiene 5 colecciones principales en la base de datos.

### Datos Maestros

#### trucks
Registra los metadatos estáticos de los vehículos.

| Campo | Tipo | Descripción | Requerido |
|---|---|---|---|
| brand | String | Marca del camión | Sí |
| capacity_tons | Float | Capacidad de carga en toneladas | Sí |

#### drivers
Registro del personal y su habilitación.

| Campo | Tipo | Descripción | Requerido |
|---|---|---|---|
| name | String | Nombre del chofer | Sí |
| license_level | String | Categoría de la licencia profesional | Sí |

#### routes
Asignación logística. Vincula un origen y destino con un camión y un chofer específico.

| Campo | Tipo | Descripción | Requerido |
|---|---|---|---|
| origin | String | Ciudad de origen | Sí |
| destination | String | Ciudad de destino | Sí |
| truck_id | String | Referencia al camión asignado | Sí |
| driver_id | String | Referencia al chofer asignado | Sí |

#### geofences
Polígonos espaciales autorizados para la circulación.

| Campo | Tipo | Descripción | Requerido |
|---|---|---|---|
| name | String | Nombre identificador de la geocerca | Sí |
| geometry | GeoJSON | Polígono WGS84 que delimita la zona | Sí |

---

### Grupo 2 — Datos Operativos (Alta Frecuencia)

#### telemetry
Colección principal del sistema. Almacena registros periódicos de los sensores IoT.

| Campo | Tipo | Descripción | Requerido |
|---|---|---|---|
| truck_id | String | Referencia al camión | Sí |
| timestamp | Date | Fecha y hora de la captura | Sí |
| speed_kmh | Float | Velocidad actual | Sí |
| engine_rpm | Int | Revoluciones por minuto del motor | Sí |
| engine_temp_c | Float | Temperatura del motor en °C | Sí |
| fuel_level_pct | Float | Nivel de combustible restante (%) | Sí |
| lon | Float | Longitud geográfica | Sí |
| lat | Float | Latitud geográfica | Sí |
| location | GeoJSON | Punto 2D geográfico (calculado automáticamente) | Sí |

---

## 4. Índices

Para que la base de datos no se ponga lenta cuando hay muchos datos, creé un par de índices:

| Colección | Campo(s) | Tipo | Razón |
|---|---|---|---|
| telemetry | `truck_id` + `timestamp` | Compuesto Único | Para no guardar datos duplicados de un mismo camión en el mismo segundo. |
| telemetry | `location` | 2dsphere | Necesario para hacer consultas espaciales en Mongo. |

---

## 4. Estructura del Proyecto

```text
FleetDAO/
├── .github/workflows/   # Pipelines de CI/CD (GitHub Actions)
├── db_models/           # Clases Pydantic para validación de entidades
├── tests/               # Batería de pruebas automatizadas (Pytest)
├── dao.py               # Data Access Object (Conexión MongoDB, Redis y MinIO)
├── main.py              # Endpoints FastAPI y WebSockets
├── auth.py              # Seguridad, Encriptación y JWT
├── ml_service.py        # Microservicio de IA en producción
├── dashboard.py         # Interfaz Web interactiva (Streamlit + Folium)
├── simulator.py         # Simulador concurrente de hardware IoT (Camiones)
├── backup.py            # Script DevOps de respaldos automáticos hacia MinIO
├── seed.py              # Script de poblado inicial de datos sintéticos
├── demo.ipynb           # Notebook de Data Science y ML
├── prometheus.yml       # Configuración del motor de métricas
├── docker-compose.yml   # Orquestación de 6 contenedores (Mongo, MinIO, Redis, Prometheus, Grafana, UI, API)
└── libs.txt             # Dependencias del proyecto
```

---

## 5. Guía de Instalación y Despliegue

### Requisitos previos
- Python 3.12+
- Docker Engine

### Paso 1: Clonar el repositorio
```bash
git clone https://github.com/davidfajardotorres777/FleetDAO.git
cd FleetDAO
```

### Paso 2: Entorno virtual y dependencias
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r libs.txt
```

### Paso 3: Configurar variables de entorno
Crear un archivo `.env` en la raíz del proyecto con el siguiente contenido:
```
MONGO_URI=mongodb://localhost:27017
DB_NAME=fleet_db
```

### Paso 4: Base de Datos y Poblado
Asegúrese de levantar todos los microservicios (MongoDB, Redis, MinIO, Prometheus, Grafana) antes de inyectar los datos:
```bash
docker compose up -d
python setup_db.py
python seed.py
```

### Paso 5: Visualización Web (Dashboard)
Para abrir la interfaz gráfica interactiva y visualizar las geocercas y la telemetría en tiempo real:
```bash
streamlit run dashboard.py
```

### Paso 6: Probar la API y Monitoreo
Si quieres probar los endpoints a mano:
```bash
uvicorn main:app --reload
# Entrar a: http://localhost:8000/docs
# Grafana (para ver las métricas): http://localhost:3000
```

### Paso 7: Simulador de Camiones
Para ver cómo se mueven los camiones solos en el mapa, abre otra consola y corre:
```bash
python simulator.py
```
*(Déjala abierta mientras miras el Dashboard).*

### Paso 8: Pruebas Automatizadas (TDD)
Ejecuta la suite de pruebas unitarias sobre tu API y tu DAO:
```bash
pytest -v
```

### Paso 9: Cuadernos Jupyter (Demostración y DAO)
Para explorar el análisis predictivo de Machine Learning y las consultas del patrón DAO directamente en un entorno interactivo:
```bash
jupyter notebook
```
Esto abrirá tu navegador. Desde allí puedes ejecutar `demo.ipynb` o `dao_consultas.ipynb`.

