from fastapi import FastAPI, HTTPException, Body
from typing import List, Dict, Any

from dao import FleetDAO

app = FastAPI(
    title="FleetDAO API",
    description="API RESTful directa y ligera para la gestión de flotas, choferes, rutas, geocercas y telemetría.",
    version="3.0"
)

# Instancia global del DAO
dao = FleetDAO()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "FleetDAO API funcionando correctamente",
        "version": "3.0",
        "docs": "/docs"
    }

# =========================================================================
# ENDPOINTS RESUMEN & ALERTAS (Executive Fleet Analytics)
# =========================================================================

@app.get("/api/fleet/summary", response_model=dict)
def get_fleet_summary():
    """Retorna un resumen ejecutivo general de la flota (totales de camiones, choferes y alertas activas)."""
    return dao.get_fleet_summary()

@app.get("/api/telemetry/alerts", response_model=List[dict])
def get_recent_alerts(limit: int = 10):
    """Retorna las lecturas de telemetría con alertas de velocidad, temperatura o combustible."""
    return dao.get_recent_alerts(limit=limit)

# =========================================================================
# ENDPOINTS TRUCKS (Camiones) - CRUD COMPLETO
# =========================================================================

@app.post("/api/trucks", response_model=dict, status_code=201)
def create_truck(truck_data: Dict[str, Any] = Body(..., examples=[{"brand": "Volvo", "capacity_tons": 28.0, "patente": "AA-123-ZZ"}])):
    """Crea un nuevo camión. Acepta cualquier propiedad o variable personalizada en el JSON."""
    try:
        truck_id = dao.add_truck(truck_data)
        return {"status": "created", "inserted_id": truck_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando camión: {str(e)}")

@app.get("/api/trucks", response_model=List[dict])
def list_trucks():
    """Retorna la lista de todos los camiones registrados."""
    return dao.get_trucks()

@app.get("/api/trucks/{truck_id}", response_model=dict)
def get_truck(truck_id: str):
    """Obtiene un camión por su ID."""
    truck = dao.get_truck_by_id(truck_id)
    if not truck:
        raise HTTPException(status_code=404, detail=f"Camión con ID {truck_id} no encontrado")
    return truck

@app.put("/api/trucks/{truck_id}", response_model=dict)
@app.patch("/api/trucks/{truck_id}", response_model=dict)
def update_truck(truck_id: str, update_data: Dict[str, Any] = Body(...)):
    """Modifica un camión o agrega variables nuevas dinámicamente."""
    success = dao.update_truck(truck_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail=f"No se pudo actualizar el camión {truck_id}")
    return {"status": "updated", "truck": dao.get_truck_by_id(truck_id)}

@app.post("/api/trucks/{truck_id}/variables", response_model=dict)
def add_truck_variable(truck_id: str, payload: Dict[str, Any] = Body(...)):
    """Agrega o modifica una variable individual por clave y valor. Ejemplo: {"name": "patente", "value": "AA-123-ZZ"}"""
    var_name = payload.get("name")
    var_value = payload.get("value")
    if not var_name:
        raise HTTPException(status_code=400, detail="El cuerpo debe incluir el campo 'name'")
    success = dao.add_variable_to_truck(truck_id, var_name, var_value)
    if not success:
        raise HTTPException(status_code=404, detail="Camión no encontrado")
    return {"status": "variable_added", "truck": dao.get_truck_by_id(truck_id)}

@app.delete("/api/trucks/{truck_id}/variables/{variable_name}", response_model=dict)
def delete_truck_variable(truck_id: str, variable_name: str):
    """Elimina una variable personalizada específica de un camión."""
    success = dao.delete_variable_from_truck(truck_id, variable_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"No se encontró la variable '{variable_name}' en el camión {truck_id}")
    return {"status": "variable_deleted", "truck": dao.get_truck_by_id(truck_id)}

@app.delete("/api/trucks/{truck_id}", response_model=dict)
def delete_truck(truck_id: str):
    """Elimina un camión por su ID."""
    success = dao.delete_truck(truck_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"No se encontró el camión {truck_id} para eliminar")
    return {"status": "deleted", "deleted_id": truck_id}

# =========================================================================
# ENDPOINTS DRIVERS (Choferes) - CRUD COMPLETO
# =========================================================================

@app.post("/api/drivers", response_model=dict, status_code=201)
def create_driver(driver_data: Dict[str, Any] = Body(...)):
    try:
        driver_id = dao.add_driver(driver_data)
        return {"status": "created", "inserted_id": driver_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drivers", response_model=List[dict])
def list_drivers():
    return dao.get_drivers()

@app.get("/api/drivers/{driver_id}", response_model=dict)
def get_driver(driver_id: str):
    driver = dao.get_driver_by_id(driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Conductor no encontrado")
    return driver

@app.put("/api/drivers/{driver_id}", response_model=dict)
def update_driver(driver_id: str, update_data: Dict[str, Any] = Body(...)):
    success = dao.update_driver(driver_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="No se pudo actualizar el conductor")
    return {"status": "updated", "driver": dao.get_driver_by_id(driver_id)}

@app.delete("/api/drivers/{driver_id}", response_model=dict)
def delete_driver(driver_id: str):
    success = dao.delete_driver(driver_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conductor no encontrado")
    return {"status": "deleted", "deleted_id": driver_id}

# =========================================================================
# ENDPOINTS ROUTES (Rutas Logísticas) - CRUD COMPLETO
# =========================================================================

@app.post("/api/routes", response_model=dict, status_code=201)
def create_route(route_data: Dict[str, Any] = Body(...)):
    try:
        route_id = dao.add_route(route_data)
        return {"status": "created", "inserted_id": route_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/routes", response_model=List[dict])
def list_routes():
    return dao.get_routes()

@app.get("/api/routes/{route_id}", response_model=dict)
def get_route(route_id: str):
    route = dao.get_route_by_id(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return route

@app.put("/api/routes/{route_id}", response_model=dict)
def update_route(route_id: str, update_data: Dict[str, Any] = Body(...)):
    success = dao.update_route(route_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="No se pudo actualizar la ruta")
    return {"status": "updated", "route": dao.get_route_by_id(route_id)}

@app.delete("/api/routes/{route_id}", response_model=dict)
def delete_route(route_id: str):
    success = dao.delete_route(route_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return {"status": "deleted", "deleted_id": route_id}

# =========================================================================
# ENDPOINTS GEOFENCES (Geocercas) - CRUD COMPLETO
# =========================================================================

@app.post("/api/geofences", response_model=dict, status_code=201)
def create_geofence(geofence_data: Dict[str, Any] = Body(...)):
    try:
        gf_id = dao.add_geofence(geofence_data)
        return {"status": "created", "inserted_id": gf_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/geofences", response_model=List[dict])
def list_geofences():
    return dao.get_geofences()

@app.get("/api/geofences/{geofence_id}", response_model=dict)
def get_geofence(geofence_id: str):
    gf = dao.get_geofence_by_id(geofence_id)
    if not gf:
        raise HTTPException(status_code=404, detail="Geocerca no encontrada")
    return gf

@app.put("/api/geofences/{geofence_id}", response_model=dict)
def update_geofence(geofence_id: str, update_data: Dict[str, Any] = Body(...)):
    success = dao.update_geofence(geofence_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="No se pudo actualizar la geocerca")
    return {"status": "updated", "geofence": dao.get_geofence_by_id(geofence_id)}

@app.delete("/api/geofences/{geofence_id}", response_model=dict)
def delete_geofence(geofence_id: str):
    success = dao.delete_geofence(geofence_id)
    if not success:
        raise HTTPException(status_code=404, detail="Geocerca no encontrada")
    return {"status": "deleted", "deleted_id": geofence_id}

# =========================================================================
# ENDPOINTS TELEMETRY (Telemetría IoT)
# =========================================================================

@app.post("/api/telemetry", response_model=dict, status_code=201)
def receive_telemetry(telemetry_data: Dict[str, Any] = Body(...)):
    try:
        telemetry_id = dao.add_telemetry(telemetry_data)
        return {"status": "success", "inserted_id": telemetry_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/telemetry/{truck_id}", response_model=List[dict])
def get_truck_telemetry(truck_id: str):
    return dao.get_telemetry(truck_id)

@app.get("/api/telemetry/stats/{truck_id}", response_model=dict)
def get_truck_stats(truck_id: str):
    stats = dao.get_truck_statistics(truck_id)
    if not stats:
        raise HTTPException(status_code=404, detail="No hay datos de telemetría para este camión")
    return stats
