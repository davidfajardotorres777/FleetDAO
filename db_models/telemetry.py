from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Telemetry(BaseModel):
    truck_id: str = Field(..., description="ID del camion")
    timestamp: datetime = Field(..., description="Hora de la lectura")
    speed_kmh: float = Field(..., ge=0, le=180, description="Velocidad en km/h (0-180)")
    engine_rpm: int = Field(..., ge=0, le=5000, description="Revoluciones del motor")
    engine_temp_c: float = Field(..., ge=0, le=150, description="Temperatura del motor en C")
    fuel_level_pct: float = Field(..., ge=0, le=100, description="Porcentaje de gasolina (0-100)")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitud")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud")

    def to_dict(self) -> dict:
        doc = {
            "truck_id": self.truck_id,
            "timestamp": self.timestamp,
            "speed_kmh": self.speed_kmh,
            "engine_rpm": self.engine_rpm,
            "engine_temp_c": self.engine_temp_c,
            "fuel_level_pct": self.fuel_level_pct
        }
        if self.lon is not None and self.lat is not None:
            # Formato GeoJSON para indice 2dsphere
            doc["location"] = {
                "type": "Point",
                "coordinates": [self.lon, self.lat]
            }
        return doc
