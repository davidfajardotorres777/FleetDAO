import time
import random
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("IoTSimulator")

API_URL = "http://localhost:8000"

def get_trucks():
    try:
        response = requests.get(f"{API_URL}/api/trucks")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error conectando a la API: {e}")
    return []

def simulate():
    logger.info("Iniciando Simulador IoT de Flota...")
    trucks = get_trucks()
    if not trucks:
        logger.warning("No hay camiones registrados para simular. Abortando.")
        return

    # Coordenadas base (ej: Chilecito, La Rioja)
    base_lat, base_lon = -29.1633, -67.4988

    # Estado inicial de cada camión
    state = {}
    for t in trucks:
        state[t["_id"]] = {
            "lat": base_lat + random.uniform(-0.01, 0.01),
            "lon": base_lon + random.uniform(-0.01, 0.01),
            "speed": random.uniform(60, 90),
            "temp": random.uniform(85, 93),
            "fuel": random.uniform(50, 100)
        }

    while True:
        for t in trucks:
            t_id = t["_id"]
            
            # Variaciones aleatorias simulando movimiento y aceleración
            state[t_id]["lat"] += random.uniform(-0.001, 0.001)
            state[t_id]["lon"] += random.uniform(-0.001, 0.001)
            state[t_id]["speed"] = max(0, min(120, state[t_id]["speed"] + random.uniform(-5, 6)))
            
            # Simulamos que a más velocidad, más revoluciones
            rpm = int(state[t_id]["speed"] * random.uniform(25, 30))
            
            # Forzamos un recalentamiento si la velocidad es muy alta (para activar la alerta predictiva de la IA)
            if state[t_id]["speed"] > 105:
                state[t_id]["temp"] += random.uniform(0.5, 2.0) # Recalentamiento!
            else:
                state[t_id]["temp"] = max(80, min(94, state[t_id]["temp"] - random.uniform(0.1, 1.0)))
                
            state[t_id]["fuel"] = max(0, state[t_id]["fuel"] - 0.1)

            telemetry = {
                "truck_id": t_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "speed_kmh": round(state[t_id]["speed"], 2),
                "engine_rpm": rpm,
                "engine_temp_c": round(state[t_id]["temp"], 2),
                "fuel_level_pct": round(state[t_id]["fuel"], 2),
                "lon": round(state[t_id]["lon"], 6),
                "lat": round(state[t_id]["lat"], 6)
            }

            try:
                res = requests.post(f"{API_URL}/api/telemetry", json=telemetry)
                if res.status_code == 200:
                    logger.info(f"[IoT] Telemetria subida [Camion {t_id[-4:]}]: {telemetry['speed_kmh']} km/h | {telemetry['engine_temp_c']} degC")
            except Exception as e:
                logger.error(f"Error enviando telemetría: {e}")
        
        logger.info("Esperando 5 segundos para el siguiente ciclo...")
        time.sleep(5)

if __name__ == "__main__":
    simulate()
