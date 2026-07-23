import joblib
import os
import logging
import warnings

# Silenciamos puntualmente el warning de sklearn sobre nombres de features
# (no todos los UserWarning de la app, para no tapar otros avisos importantes)
warnings.filterwarnings("ignore", message=".*does not have valid feature names.*", category=UserWarning)

logger = logging.getLogger(__name__)

class MLPredictor:
    def __init__(self, model_path="fleet_model.joblib"):
        self.model = None
        self.model_loaded = False
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            self.model_loaded = True
            logger.info("Modelo ML cargado correctamente.")
        else:
            logger.warning(f"No se encontró el modelo en {model_path}. Debe ejecutar train_model.py primero.")

    def predict_temperature(self, speed_kmh: float, engine_rpm: int) -> float:
        if not self.model:
            # No devolvemos 0.0: eso simularía "todo normal" y ocultaría
            # que el modelo nunca se entrenó. Mejor que falle explícitamente.
            raise RuntimeError("El modelo de predicción no está cargado. Ejecutá train_model.py primero.")
        prediction = self.model.predict([[speed_kmh, engine_rpm]])[0]
        return round(float(prediction), 2)
