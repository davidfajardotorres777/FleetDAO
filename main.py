from fastapi import FastAPI, HTTPException
from typing import List

from dao import FleetDAO
from db_models.trucks import Truck
from db_models.telemetry import Telemetry

app = FastAPI(
    title="FleetDAO API",
    description="API para conectar los camiones con la bd",
    version="1.0"
)

# Inicializar el DAO al arrancar
dao = FleetDAO()

@app.get("/")
def read_root():
    return {"message": "FleetDAO API funcionando correctamente"}

@app.post("/api/trucks", response_model=dict)
def register_truck(truck: Truck):
    try:
        truck_id = dao.add_truck(truck)
        return {"inserted_id": truck_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trucks")
def list_trucks():
    trucks = dao.get_trucks()
    # Convertir ObjectId a string para serializar en JSON
    for t in trucks:
        t["_id"] = str(t["_id"])
    return trucks

@app.post("/api/telemetry")
def receive_telemetry(telemetry: Telemetry):
    # Endpoint que recibe los datos de velocidad y temp desde el camion
    try:
        telemetry_id = dao.add_telemetry(telemetry)
        return {"status": "success", "inserted_id": telemetry_id}
    except Exception as e:
        # Si hay algun error al insertar manda 400
        raise HTTPException(status_code=400, detail=str(e))
