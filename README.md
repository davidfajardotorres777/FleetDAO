# 🚚 FleetDAO - Sistema de Gestión de Flotas y Telemetría IoT

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Latest-green.svg)](https://www.mongodb.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io/)

**FleetDAO** es una solución de arquitectura limpia y autónoma basada en el patrón **Data Access Object (DAO)** sobre **MongoDB**. Permite administrar camiones, choferes, rutas logísticas, geocercas y series temporales de telemetría IoT con **flexibilidad total para agregar o modificar cualquier variable dinámica en vivo**.

---

## ⭐️ Características Principales

1. **DAO Autónomo y Standalone (`dao.py`)**:
   - Sin dependencias de esquemas rígidos: agrega o modifica campos personalizados en vivo.
   - Soporte para **`kwargs` directos**, **diccionarios planos** o **Context Manager (`with FleetDAO() as dao:`)**.
2. **Consultas Analíticas Ejecutivas**:
   - Agregaciones nativas en MongoDB para promedios de velocidad, máximos de temperatura y alertas en tiempo real.
3. **API RESTful en FastAPI (`main.py`)**:
   - Endpoints completos para todas las entidades y búsqueda dinámica por cualquier atributo custom.
   - Documentación interactiva Swagger UI integrada en `/docs`.
4. **Dashboard Web Interactivo (`dashboard.py`)**:
   - Visualización de mapa GPS en vivo con Folium, gráficos de telemetría y gestor interactivo de variables en tiempo real.
5. **Jupyter Notebook Interactivo (`pruebas_dao.ipynb`)**:
   - Cuaderno ejecutado y pre-renderizado para inspeccionar el DAO celda por celda.

---

## 📁 Estructura del Proyecto

```text
FleetDAO/
├── dao.py               # ⭐ El DAO Standalone Único (Toda la lógica de MongoDB)
├── main.py              # API RESTful en FastAPI con Swagger UI
├── dashboard.py         # Dashboard Web Interactivo (Streamlit + Folium)
├── seed.py              # Poblado automático de datos de simulación
├── pruebas_dao.ipynb    # Jupyter Notebook para pruebas e inspección interactiva
├── config_vars.py       # Configuración de variables de entorno
└── docker-compose.yml   # Servicio de MongoDB en Docker
```

---

## 💻 Ejemplo de Uso del DAO

```python
from dao import FleetDAO

# Uso con Context Manager (cierre automático de conexión)
with FleetDAO() as dao:

    # 1. Crear un camión pasando variables directamente:
    truck_id = dao.add_truck(
        brand="Volvo FH16", 
        capacity_tons=40.0, 
        patente="AB-123-CD", 
        chofer_asignado="Carlos Pérez"
    )

    # 2. Agregar o modificar variables dinámicas en tiempo real:
    dao.add_variable_to_truck(truck_id, "gps_tracker_id", "GPS-9988-X")
    dao.update_truck(truck_id, seguro_vencimiento="2027-12-31")

    # 3. Buscar camiones por cualquier variable personalizada:
    camiones = dao.get_trucks_by_variable("chofer_asignado", "Carlos Pérez")
    
    # 4. Eliminar una variable específica:
    dao.delete_variable_from_truck(truck_id, "variable_obsoleta")

    # 5. Obtener documento completo:
    print(dao.get_truck_by_id(truck_id))
```

---

## 🚀 Guía de Inicio Rápido

### 1. Iniciar la Base de Datos MongoDB
```bash
docker compose up -d
```

### 2. Poblar Datos de Prueba
```bash
python seed.py
```

### 3. Iniciar la API REST (FastAPI)
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
> Accede a la documentación interactiva Swagger UI en: **`http://localhost:8000/docs`**

### 4. Iniciar el Dashboard Web (Streamlit)
```bash
streamlit run dashboard.py --server.port 8501
```
> Accede al panel de control en: **`http://localhost:8501`**

---

## 🔗 Endpoints Principales de la API REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/fleet/summary` | Resumen ejecutivo y alertas activas de la flota |
| `GET` | `/api/telemetry/alerts` | Lecturas con excesos de velocidad o temperatura |
| `GET` | `/api/trucks/search?key=KEY&value=VAL` | Búsqueda dinámica de camiones por variable custom |
| `POST` | `/api/trucks` | Registra un nuevo camión (acepta JSON dinámico) |
| `GET` | `/api/trucks/{id}` | Obtiene los datos de un camión por ID |
| `PUT` | `/api/trucks/{id}` | Modifica campos o agrega variables dinámicas |
| `POST` | `/api/trucks/{id}/variables` | Agrega o modifica una variable por clave/valor |
| `DELETE` | `/api/trucks/{id}/variables/{name}` | Elimina una variable específica de un camión |
