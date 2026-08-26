from fastapi import FastAPI, HTTPException, Body, Query
from typing import List, Dict, Any
from dao import FleetDAO

app = FastAPI(
    title="FleetDAO API",
    description="API RESTful directa y ligera basada en el patrón DAO sobre MongoDB.",
    version="3.2"
)

dao = FleetDAO()

@app.get("/", tags=["Root"])
def root():
    return {"status": "online", "message": "FleetDAO API v3.2", "docs": "/docs"}

# Fleet Analytics
@app.get("/api/fleet/summary", tags=["Analytics"])
def fleet_summary():
    return dao.get_fleet_summary()

@app.get("/api/telemetry/alerts", tags=["Analytics"])
def fleet_alerts(limit: int = 10):
    return dao.get_recent_alerts(limit)

# Trucks CRUD & Dynamic Search
@app.get("/api/trucks/search", tags=["Trucks"])
def search_trucks(key: str = Query(...), value: str = Query(...)):
    return dao.get_trucks_by_variable(key, value)

@app.post("/api/trucks", status_code=201, tags=["Trucks"])
def create_truck(data: Dict[str, Any] = Body(...)):
    return {"status": "created", "inserted_id": dao.add_truck(data)}

@app.get("/api/trucks", tags=["Trucks"])
def list_trucks():
    return dao.get_trucks()

@app.get("/api/trucks/{truck_id}", tags=["Trucks"])
def get_truck(truck_id: str):
    doc = dao.get_truck_by_id(truck_id)
    if not doc: raise HTTPException(404, "Camión no encontrado")
    return doc

@app.put("/api/trucks/{truck_id}", tags=["Trucks"])
@app.patch("/api/trucks/{truck_id}", tags=["Trucks"])
def update_truck(truck_id: str, data: Dict[str, Any] = Body(...)):
    if not dao.update_truck(truck_id, data): raise HTTPException(404, "Camión no encontrado")
    return {"status": "updated", "truck": dao.get_truck_by_id(truck_id)}

@app.post("/api/trucks/{truck_id}/variables", tags=["Trucks"])
def add_truck_var(truck_id: str, payload: Dict[str, Any] = Body(...)):
    if not payload.get("name"): raise HTTPException(400, "Campo 'name' requerido")
    if not dao.add_variable_to_truck(truck_id, payload["name"], payload.get("value")): raise HTTPException(404, "Camión no encontrado")
    return {"status": "variable_added", "truck": dao.get_truck_by_id(truck_id)}

@app.delete("/api/trucks/{truck_id}/variables/{var_name}", tags=["Trucks"])
def del_truck_var(truck_id: str, var_name: str):
    if not dao.delete_variable_from_truck(truck_id, var_name): raise HTTPException(404, "Variable no encontrada")
    return {"status": "variable_deleted", "truck": dao.get_truck_by_id(truck_id)}

@app.delete("/api/trucks/{truck_id}", tags=["Trucks"])
def delete_truck(truck_id: str):
    if not dao.delete_truck(truck_id): raise HTTPException(404, "Camión no encontrado")
    return {"status": "deleted", "deleted_id": truck_id}

# Drivers CRUD
@app.post("/api/drivers", status_code=201, tags=["Drivers"])
def create_driver(data: Dict[str, Any] = Body(...)):
    return {"status": "created", "inserted_id": dao.add_driver(data)}

@app.get("/api/drivers", tags=["Drivers"])
def list_drivers(): return dao.get_drivers()

@app.get("/api/drivers/{driver_id}", tags=["Drivers"])
def get_driver(driver_id: str):
    d = dao.get_driver_by_id(driver_id)
    if not d: raise HTTPException(404, "Conductor no encontrado")
    return d

@app.put("/api/drivers/{driver_id}", tags=["Drivers"])
def update_driver(driver_id: str, data: Dict[str, Any] = Body(...)):
    if not dao.update_driver(driver_id, data): raise HTTPException(404, "Conductor no encontrado")
    return {"status": "updated", "driver": dao.get_driver_by_id(driver_id)}

@app.delete("/api/drivers/{driver_id}", tags=["Drivers"])
def delete_driver(driver_id: str):
    if not dao.delete_driver(driver_id): raise HTTPException(404, "Conductor no encontrado")
    return {"status": "deleted", "deleted_id": driver_id}

# Routes CRUD
@app.post("/api/routes", status_code=201, tags=["Routes"])
def create_route(data: Dict[str, Any] = Body(...)):
    return {"status": "created", "inserted_id": dao.add_route(data)}

@app.get("/api/routes", tags=["Routes"])
def list_routes(): return dao.get_routes()

@app.get("/api/routes/{route_id}", tags=["Routes"])
def get_route(route_id: str):
    r = dao.get_route_by_id(route_id)
    if not r: raise HTTPException(404, "Ruta no encontrada")
    return r

@app.put("/api/routes/{route_id}", tags=["Routes"])
def update_route(route_id: str, data: Dict[str, Any] = Body(...)):
    if not dao.update_route(route_id, data): raise HTTPException(404, "Ruta no encontrada")
    return {"status": "updated", "route": dao.get_route_by_id(route_id)}

@app.delete("/api/routes/{route_id}", tags=["Routes"])
def delete_route(route_id: str):
    if not dao.delete_route(route_id): raise HTTPException(404, "Ruta no encontrada")
    return {"status": "deleted", "deleted_id": route_id}

# Geofences CRUD
@app.post("/api/geofences", status_code=201, tags=["Geofences"])
def create_geofence(data: Dict[str, Any] = Body(...)):
    return {"status": "created", "inserted_id": dao.add_geofence(data)}

@app.get("/api/geofences", tags=["Geofences"])
def list_geofences(): return dao.get_geofences()

@app.get("/api/geofences/{geofence_id}", tags=["Geofences"])
def get_geofence(geofence_id: str):
    g = dao.get_geofence_by_id(geofence_id)
    if not g: raise HTTPException(404, "Geocerca no encontrada")
    return g

@app.put("/api/geofences/{geofence_id}", tags=["Geofences"])
def update_geofence(geofence_id: str, data: Dict[str, Any] = Body(...)):
    if not dao.update_geofence(geofence_id, data): raise HTTPException(404, "Geocerca no encontrada")
    return {"status": "updated", "geofence": dao.get_geofence_by_id(geofence_id)}

@app.delete("/api/geofences/{geofence_id}", tags=["Geofences"])
def delete_geofence(geofence_id: str):
    if not dao.delete_geofence(geofence_id): raise HTTPException(404, "Geocerca no encontrada")
    return {"status": "deleted", "deleted_id": geofence_id}

# Telemetry IoT & Geo-Queries
@app.post("/api/telemetry", status_code=201, tags=["Telemetry"])
def receive_telemetry(data: Dict[str, Any] = Body(...)):
    return {"status": "success", "inserted_id": dao.add_telemetry(data)}

@app.post("/api/telemetry/bulk", status_code=201, tags=["Telemetry"])
def bulk_telemetry(readings: List[Dict[str, Any]] = Body(...)):
    inserted_ids = dao.bulk_add_telemetry(readings)
    return {"status": "success", "count": len(inserted_ids), "inserted_ids": inserted_ids}

@app.get("/api/telemetry/{truck_id}", tags=["Telemetry"])
def get_telemetry(truck_id: str): return dao.get_telemetry(truck_id)

@app.get("/api/telemetry/{truck_id}/near", tags=["Telemetry"])
def get_telemetry_near(truck_id: str, lon: float = Query(...), lat: float = Query(...), radius_m: float = Query(5000.0)):
    return dao.get_telemetry_near(truck_id, lon, lat, radius_m)

@app.get("/api/telemetry/stats/{truck_id}", tags=["Telemetry"])
def get_truck_stats(truck_id: str):
    s = dao.get_truck_statistics(truck_id)
    if not s: raise HTTPException(404, "Sin datos de telemetría")
    return s
