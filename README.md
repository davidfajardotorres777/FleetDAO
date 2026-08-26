# FleetDAO
### Sistema Avanzado de Gestión de Flotas y Telemetría Predictiva

Proyecto Integrador — Bases de Datos II · 2026  
Autor: **Alesandro David Fajardo Torres**

---

## 1. El Problema y la Solución

Las empresas de logística y transporte pierden millones de pesos al año debido a la falta de control predictivo sobre sus flotas. El exceso de velocidad, las rutas ineficientes y los motores sobrecalentados representan gastos ocultos gigantescos. Los sistemas GPS tradicionales únicamente informan la ubicación estática del camión, pero fallan en analizar los datos mecánicos o en advertir anomalías antes de que ocurran daños severos.

**FleetDAO** resuelve este problema mediante una arquitectura NoSQL orientada a la ingestión masiva de telemetría en tiempo real. Es un sistema capaz de recibir, almacenar, visualizar y analizar variables críticas (ubicación, velocidad, RPM, temperatura) utilizando modelos predictivos, operaciones CRUD flexibles e índices geoespaciales complejos.

---

## 2. Herramientas y Arquitectura

* **MongoDB (4.4)**: Base de datos NoSQL principal. Seleccionada por su capacidad de procesar escrituras masivas por segundo (time-series data).
* **Patrón DAO (Data Access Object)**: Capa de abstracción completa con soporte para todas las operaciones CRUD (Crear, Leer, Modificar/Actualizar y Eliminar) sobre 5 colecciones.
* **Modelos Flexibles (Pydantic v2)**: Uso de `ConfigDict(extra="allow")` en las entidades de `db_models/` para permitir que el desarrollador agregue o modifique variables personalizadas arbitrarias sin restricciones de esquema.
* **Índices Geoespaciales (`2dsphere`)**: Implementación de polígonos complejos (`$geoWithin`) y radio (`$near`) para la detección automática de violaciones de Geocercas.
* **Aggregation Pipelines**: Uso intensivo de operaciones nativas (`$group`, `$avg`, `$max`) para trasladar la carga analítica al motor de base de datos.
* **FastAPI & Pydantic**: Capa de API RESTful de alto rendimiento con validación estricta pero extensible.
* **Dashboard Interactivo (Streamlit & Folium)**: Interfaz gráfica web moderna que permite a los operadores visualizar rutas y métricas en tiempo real.

---

## 3. Estructura de la Base de Datos y Colecciones

1. **trucks (Camiones):** Metadatos estáticos y variables personalizadas dinámicas (marca, patente, capacidad, año, estado, etc.).
2. **drivers (Choferes):** Registro del personal y habilitación profesional.
3. **routes (Rutas):** Asignación logística (origen, destino, camión, chofer, estado).
4. **geofences (Geocercas):** Polígonos espaciales autorizados para la circulación (`GeoJSON`).
5. **telemetry (Telemetría):** Colección de alta frecuencia con lecturas IoT (`timestamp`, velocidad, temperatura, combustible, coordenadas GeoJSON `2dsphere`).

---

## 4. Estructura del Proyecto

```text
FleetDAO/
├── db_models/           # Clases Pydantic flexibles con extra="allow" (Truck, Driver, etc.)
├── dao.py               # Data Access Object con CRUD completo y normalización de ObjectId
├── main.py              # Endpoints de API RESTful en FastAPI (v2.0)
├── dashboard.py         # Interfaz Web interactiva construida en Streamlit y Folium
├── seed.py              # Script de poblado inicial de datos sintéticos
├── test_dao_crud.py     # Suite de pruebas automatizadas para CRUD y variables dinámicas
├── demo.ipynb           # Notebook de Data Science y entrenamiento de Machine Learning
├── docker-compose.yml   # Contenedor de MongoDB
└── libs.txt             # Dependencias del proyecto
```

---

## 5. Guía de Instalación, Despliegue y Pruebas

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

### Paso 3: Levantar la Base de Datos
```bash
docker compose up -d
python seed.py
```

### Paso 4: Ejecutar la Suite de Pruebas CRUD
Para verificar el correcto funcionamiento del DAO y la adición dinámica de variables:
```bash
python test_dao_crud.py
```

### Paso 5: Visualización Web (Dashboard)
Para abrir la interfaz gráfica interactiva:
```bash
streamlit run dashboard.py
```

### Paso 6: Backend API (FastAPI Swagger)
Para interactuar directamente con la API RESTful:
```bash
uvicorn main:app --reload
# Acceda a http://localhost:8000/docs
```
