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

> **Nota:** en `dbscripts.sql` está el modelo relacional equivalente, pensado en la
> etapa de diseño inicial. Se migró a MongoDB porque para telemetría IoT de alta
> frecuencia (muchas escrituras por segundo, esquema flexible) un modelo de
> documentos rinde mejor que uno relacional normalizado.

---

## 4. Índices

Para que la base de datos no se ponga lenta cuando hay muchos datos, creé un par de índices:

| Colección | Campo(s) | Tipo | Razón |
|---|---|---|---|
| telemetry | `truck_id` + `timestamp` | Compuesto Único | Para no guardar datos duplicados de un mismo camión en el mismo segundo. |
| telemetry | `location` | 2dsphere | Necesario para hacer consultas espaciales en Mongo. |

---

## 5. Estructura del Proyecto

```text
FleetDAO/
├── .github/workflows/   # Pipelines de CI/CD (GitHub Actions)
├── db_models/           # Clases Pydantic para validación de entidades
├── tests/               # Batería de pruebas automatizadas (Pytest)
├── dao.py               # Data Access Object (Conexión MongoDB, Redis y MinIO)
├── main.py              # Endpoints FastAPI y WebSockets
├── auth.py              # Seguridad, Encriptación y JWT
├── config_vars.py       # Carga de variables de entorno (.env)
├── ml_service.py        # Microservicio de ML en producción
├── train_model.py       # Entrenamiento del modelo predictivo (Scikit-Learn)
├── dashboard.py         # Interfaz Web interactiva (Streamlit + Folium)
├── simulator.py         # Simulador concurrente de hardware IoT (Camiones)
├── backup.py            # Script DevOps de respaldos automáticos hacia MinIO
├── setup_db.py          # Creación de índices y colecciones en MongoDB
├── seed.py              # Script de poblado inicial de datos sintéticos
├── build_notebook.py    # Genera dao_consultas.ipynb de forma programática
├── dao_consultas.ipynb  # Notebook de consultas sobre el patrón DAO
├── demo.ipynb           # Notebook de Data Science y ML
├── dbscripts.sql        # Modelo relacional equivalente (etapa de diseño, no usado en runtime)
├── Dockerfile.api        # Imagen de la API (FastAPI)
├── Dockerfile.dashboard  # Imagen del Dashboard (Streamlit)
├── prometheus.yml       # Configuración del motor de métricas
├── docker-compose.yml   # Orquestación de 7 contenedores (Mongo, MinIO, Redis, Prometheus, Grafana, API, Dashboard)
├── .env.example         # Plantilla de variables de entorno
└── requirements.txt     # Dependencias del proyecto
```

---

## 6. Guía de Instalación y Despliegue

### Requisitos previos
- **Python**: Version 3.10, 3.11 o 3.12
- **Docker & Docker Desktop** (o Docker Engine con plugin compose)

---

### Paso 1: Clonar el repositorio
```bash
git clone https://github.com/davidfajardotorres777/FleetDAO.git
cd FleetDAO
```

---

### Paso 2: Crear el entorno virtual e instalar dependencias

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Paso 3: Variables de Entorno (.env)
El proyecto **ya incluye el archivo `.env` configurado y listo para usar** en la raíz del repositorio con los valores por defecto para desarrollo local:

```env
MONGO_URI=mongodb://localhost:27017/
DB_NAME=fleet_db
SECRET_KEY=clave-secreta-para-jwt-super-segura-12345
MINIO_ENDPOINT=localhost:9002
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=changeme
MINIO_SECURE=false
REDIS_URL=redis://localhost:6379/0
```
*(No es necesario crear ni modificar ningún archivo; al clonar el proyecto ya queda configurado).*

---

### Paso 4: Inicialización y Ejecución Paso a Paso

1. **Levantar las Bases de Datos e Infraestructura (Docker):**
   ```bash
   docker compose up -d mongodb redis minio
   ```
   *(Nota: Se levantan los servicios de datos e infraestructura en segundo plano).*

2. **Inicializar colecciones, índices geoespaciales y poblar con datos de prueba:**
   ```bash
   python setup_db.py
   python seed.py
   ```

3. **Iniciar la API Backend (FastAPI):**
   ```bash
   uvicorn main:app --reload
   ```
   * *API Root:* http://localhost:8000
   * *Documentación interactiva Swagger UI:* http://localhost:8000/docs
   * *Métricas en Grafana:* http://localhost:3000

4. **Iniciar el Dashboard Web Interactivo (Streamlit):** *(En otra terminal)*
   ```bash
   streamlit run dashboard.py
   ```
   * *Dashboard:* http://localhost:8501

5. **Iniciar el Simulador IoT de Camiones (Opcional):** *(En otra terminal)*
   ```bash
   python simulator.py
   ```
   *(Genera movimiento de camiones, variaciones de velocidad y datos de telemetría en tiempo real).*

---

### Paso 5: Pruebas Automatizadas (Pytest)
Para ejecutar la suite completa de pruebas unitarias sobre el DAO y los endpoints de la API:
```bash
pytest -v
```

---

### Paso 6: Cuadernos Jupyter (Examen y Demostración)
Para abrir el cuaderno interactivo de consultas DAO o el de Data Science y Machine Learning:

```bash
jupyter notebook dao_consultas.ipynb
```
Desde la interfaz web de Jupyter que se abre en el navegador, podrás explorar e interactuar tanto con `dao_consultas.ipynb` como con `demo.ipynb`.

