from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import List

from dao import FleetDAO
from db_models.trucks import Truck
from db_models.drivers import Driver
from db_models.routes import Route
from db_models.telemetry import Telemetry
from ml_service import MLPredictor
from auth import (
    verify_password, get_password_hash, create_access_token, 
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import WebSocket, WebSocketDisconnect

app = FastAPI(
    title="FleetDAO API",
    description="API para conectar los camiones con la bd",
    version="1.0"
)

# Instrumentación para Prometheus y Grafana
Instrumentator().instrument(app).expose(app)

# Inicializar el DAO al arrancar
dao = FleetDAO()
ml_predictor = MLPredictor()

# WebSockets Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

@app.on_event("shutdown")
def shutdown_event():
    # cerrar las conexiones cuando se apaga la API
    dao.close()

@app.get("/")
def read_root():
    return {"message": "FleetDAO API funcionando correctamente"}

# Dummy Admin User (En producción usar DB)
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": get_password_hash("admin123")
    }
}

@app.post("/api/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = FAKE_USERS_DB.get(form_data.username)
    if not user_dict or not verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=400,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/trucks", response_model=dict)
def register_truck(truck: Truck, current_user: str = Depends(get_current_user)):
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

@app.put("/api/trucks/{truck_id}")
def update_truck(truck_id: str, truck: Truck, current_user: str = Depends(get_current_user)):
    try:
        updated = dao.update_truck(truck_id=truck_id, update_data=truck.to_dict())
        if not updated:
            raise HTTPException(status_code=404, detail="Camión no encontrado")
        return {"status": "success", "message": "Camión actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/trucks/{truck_id}")
def delete_truck(truck_id: str, current_user: str = Depends(get_current_user)):
    try:
        deleted = dao.delete_truck(truck_id=truck_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Camión no encontrado")
        return {"status": "success", "message": "Camión eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    # manda telemetria por websockets a la web
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/telemetry")
async def receive_telemetry(telemetry: Telemetry):
    # Endpoint que recibe los datos de velocidad y temp desde el camion
    try:
        telemetry_id = dao.add_telemetry(telemetry)
        
        # Empujar evento a clientes WebSockets
        data_to_push = {
            "truck_id": telemetry.truck_id,
            "speed_kmh": telemetry.speed_kmh,
            "engine_rpm": telemetry.engine_rpm,
            "engine_temp_c": telemetry.engine_temp_c,
            "lon": telemetry.lon,
            "lat": telemetry.lat
        }
        await manager.broadcast(data_to_push)
        
        return {"status": "success", "inserted_id": telemetry_id}
    except Exception as e:
        # Si hay algun error al insertar manda 400
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/telemetry/latest/{truck_id}")
def get_latest_telemetry_cache(truck_id: str):
    # trae la ultima posicion de redis (es mas rapido que ir a mongo)
    data = dao.get_latest_telemetry_cache(truck_id=truck_id)
    if not data:
        raise HTTPException(status_code=404, detail="Sin caché disponible en Redis")
    return data

@app.post("/api/predict_temp")
def predict_temperature(speed_kmh: float, engine_rpm: int):
    # ML que predice si el camion se va a recalentar
    try:
        predicted_temp = ml_predictor.predict_temperature(speed_kmh, engine_rpm)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    alerta_recalentamiento = predicted_temp > 95.0
    return {
        "speed_kmh": speed_kmh,
        "engine_rpm": engine_rpm,
        "predicted_temp_c": predicted_temp,
        "alerta_recalentamiento": alerta_recalentamiento
    }

@app.post("/api/drivers", response_model=dict)
def register_driver(driver: Driver, current_user: str = Depends(get_current_user)):
    try:
        driver_id = dao.add_driver(driver)
        return {"inserted_id": driver_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drivers")
def list_drivers():
    drivers = dao.get_drivers()
    for d in drivers:
        d["_id"] = str(d["_id"])
    return drivers

@app.put("/api/drivers/{driver_id}")
def update_driver(driver_id: str, driver: Driver, current_user: str = Depends(get_current_user)):
    try:
        updated = dao.update_driver(driver_id=driver_id, update_data=driver.to_dict())
        if not updated:
            raise HTTPException(status_code=404, detail="Chofer no encontrado")
        return {"status": "success", "message": "Chofer actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/drivers/{driver_id}")
def delete_driver(driver_id: str, current_user: str = Depends(get_current_user)):
    try:
        deleted = dao.delete_driver(driver_id=driver_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Chofer no encontrado")
        return {"status": "success", "message": "Chofer eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drivers/{driver_id}/license")
async def upload_driver_license(driver_id: str, file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    # Sube la foto del carnet de conducir a MinIO
    try:
        drivers = dao.get_drivers(driver_id=driver_id)
        if not drivers:
            raise HTTPException(status_code=404, detail="Chofer no encontrado")
            
        file_data = await file.read()
        object_name = f"{driver_id}_{file.filename}"
        
        file_url = dao.upload_file(
            bucket_name="licenses",
            object_name=object_name,
            file_data=file_data,
            content_type=file.content_type
        )
        
        dao.update_driver_license_url(driver_id=driver_id, license_url=file_url)
        
        return {"status": "success", "license_url": file_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/routes", response_model=dict)
def register_route(route: Route, current_user: str = Depends(get_current_user)):
    try:
        route_id = dao.add_route(route)
        return {"inserted_id": route_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/routes")
def list_routes():
    routes = dao.get_routes()
    for r in routes:
        r["_id"] = str(r["_id"])
    return routes

@app.put("/api/routes/{route_id}")
def update_route(route_id: str, route: Route, current_user: str = Depends(get_current_user)):
    try:
        updated = dao.update_route(route_id=route_id, update_data=route.to_dict())
        if not updated:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")
        return {"status": "success", "message": "Ruta actualizada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/routes/{route_id}")
def delete_route(route_id: str, current_user: str = Depends(get_current_user)):
    try:
        deleted = dao.delete_route(route_id=route_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")
        return {"status": "success", "message": "Ruta eliminada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
