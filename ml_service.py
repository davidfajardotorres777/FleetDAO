import joblib
import os
import logging
import warnings

# Ignorar advertencias de scikit-learn sobre feature names
warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger(__name__)

class MLPredictor:
    def __init__(self, model_path="fleet_model.joblib"):
        self.model = None
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            logger.info("Modelo ML cargado correctamente.")
        else:
            logger.warning(f"No se encontró el modelo en {model_path}. Debe ejecutar train_model.py primero.")
            
    def predict_temperature(self, speed_kmh: float, engine_rpm: int) -> float:
        if not self.model:
            return 0.0
        import pandas as pd
        input_data = pd.DataFrame([[speed_kmh, engine_rpm]], columns=["speed_kmh", "engine_rpm"])
        prediction = self.model.predict(input_data)[0]
        return round(float(prediction), 2)
