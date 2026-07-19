# FleetDAO
### Sistema Avanzado de Gestión de Flotas y Telemetría Predictiva

Proyecto Integrador — Bases de Datos II · 2026
Autor: **Alesandro David Fajardo Torres**

---

## 1. El Problema

Las empresas de logística y transporte pierden millones de pesos al año debido a la falta de control predictivo sobre sus flotas. El exceso de velocidad, las rutas ineficientes y los motores sobrecalentados representan gastos ocultos gigantescos. Los sistemas GPS tradicionales únicamente informan la ubicación estática del camión, pero fallan en analizar los datos mecánicos o en advertir anomalías antes de que ocurran daños severos.

**FleetDAO** resuelve este problema mediante una arquitectura orientada a la ingestión masiva de telemetría en tiempo real. Es un sistema capaz de recibir, almacenar, visualizar y analizar variables críticas (ubicación, velocidad, RPM, temperatura) utilizando modelos predictivos e índices geoespaciales complejos para prevenir fallas antes de que ocurran.

---

## 2. Herramientas y Arquitectura

Para garantizar un rendimiento escalable y de grado empresarial, la arquitectura del sistema se divide en las siguientes capas tecnológicas:

*   **MongoDB (4.4)**: Base de datos NoSQL principal. Seleccionada por su capacidad inherente de procesar escrituras masivas por segundo (time-series data).
*   **Índices Geoespaciales (`2dsphere`)**: Implementación de polígonos complejos (`$geoWithin`) para la detección automática de violaciones de Geocercas.
*   **Aggregation Pipelines**: Uso intensivo de operaciones nativas (`$group`, `$avg`, `$max`) para trasladar la carga analítica al motor de base de datos, liberando recursos en la aplicación.
*   **Machine Learning (Scikit-Learn)**: Entrenamiento de modelos predictivos de regresión lineal para anticipar el recalentamiento de los motores basado en correlaciones entre RPM y velocidad.
*   **FastAPI & Pydantic**: Capa de API REST de alto rendimiento con validación estricta de tipos de datos para prevenir contaminación de la base de datos.
*   **Dashboard Interactivo (Streamlit & Folium)**: Interfaz gráfica web moderna que permite a los operadores visualizar rutas y métricas en tiempo real sin requerir interacción por consola.

---

## 3. Estructura de la Base de Datos

El sistema emplea colecciones con separación lógica de responsabilidades operativas:

### Colecciones:
1. **trucks (Camiones):** Metadatos estáticos del vehículo (marca, patente, capacidad de carga).
2. **drivers (Choferes):** Registro del personal y su habilitación profesional.
3. **routes (Rutas):** Asignación logística (origen, destino, camión, chofer).
4. **geofences (Geocercas):** Polígonos espaciales autorizados para la circulación.
5. **telemetry (Telemetría):** Colección de alta frecuencia. Almacena registros periódicos del sensor IoT (timestamp, velocidad, temperatura, combustible y coordenadas GeoJSON).

### Índices Optimizados:
*   **Índice Único Compuesto**: `[("truck_id", 1), ("timestamp", 1)]` para garantizar la idempotencia de las inserciones.
*   **Índice Espacial**: `[("location", "2dsphere")]` para permitir consultas geométricas.

---

## 4. Estructura del Proyecto

```text
FleetDAO/
├── db_models/           # Clases Pydantic para validación de entidades
├── dao.py               # Data Access Object (Conexión y Queries complejas a MongoDB)
├── main.py              # Endpoints de FastAPI
├── dashboard.py         # Interfaz Web interactiva construida en Streamlit
├── seed.py              # Script de poblado inicial de datos sintéticos
├── demo.ipynb           # Notebook de Data Science y entrenamiento de Machine Learning
├── docker-compose.yml   # Contenedor de MongoDB
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

### Paso 3: Base de Datos y Poblado
Asegúrese de levantar el contenedor antes de inyectar los datos:
```bash
docker compose up -d
python seed.py
```

### Paso 4: Visualización Web (Dashboard)
Para abrir la interfaz gráfica interactiva y visualizar las geocercas y la telemetría en tiempo real:
```bash
streamlit run dashboard.py
```

### Paso 5: Backend API (Opcional)
Para probar los endpoints directamente a través de Swagger UI:
```bash
uvicorn main:app --reload
# Acceda a http://localhost:8000/docs
```
