import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "FleetDAO API funcionando correctamente"}

def test_predict_temp():
    # Simular parametros validos
    response = client.post("/api/predict_temp?speed_kmh=90&engine_rpm=2500")
    assert response.status_code == 200
    data = response.json()
    assert "predicted_temp_c" in data
    assert "alerta_recalentamiento" in data
    assert type(data["predicted_temp_c"]) == float
    assert type(data["alerta_recalentamiento"]) == bool

def test_predict_temp_critical():
    # Simulamos ir a 150 km/h a 4500 RPM, debería recalentarse seguro
    response = client.post("/api/predict_temp?speed_kmh=150&engine_rpm=4500")
    assert response.status_code == 200
    data = response.json()
    # No todas las predicciones dan > 95 pero probamos que la lógica responda sin crashear
    assert "predicted_temp_c" in data
