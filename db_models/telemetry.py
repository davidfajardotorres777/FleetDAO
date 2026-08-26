from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Any, Dict

class Telemetry(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    truck_id: str = Field(..., description="ID del camion")
    timestamp: datetime = Field(..., description="Hora de la lectura")
    speed_kmh: float = Field(..., ge=0, le=180, description="Velocidad en km/h (0-180)")
    engine_rpm: int = Field(..., ge=0, le=5000, description="Revoluciones del motor")
    engine_temp_c: float = Field(..., ge=0, le=150, description="Temperatura del motor en C")
    fuel_level_pct: float = Field(..., ge=0, le=100, description="Porcentaje de gasolina (0-100)")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitud")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud")

    def to_dict(self) -> dict:
        doc = self.model_dump(exclude={"lon", "lat"})
        if self.lon is not None and self.lat is not None:
            doc["location"] = {
                "type": "Point",
                "coordinates": [self.lon, self.lat]
            }
        return doc

class TelemetryUpdate(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    speed_kmh: Optional[float] = None
    engine_rpm: Optional[int] = None
    engine_temp_c: Optional[float] = None
    fuel_level_pct: Optional[float] = None
    lon: Optional[float] = None
    lat: Optional[float] = None

    def to_dict(self) -> dict:
        data = {}
        for key in ("speed_kmh", "engine_rpm", "engine_temp_c", "fuel_level_pct"):
            val = getattr(self, key)
            if val is not None:
                data[key] = val
        if self.lon is not None and self.lat is not None:
            data["location"] = {
                "type": "Point",
                "coordinates": [self.lon, self.lat]
            }
        # Incluir otros campos dinámicos
        for key, val in self.__dict__.items():
            if key not in ("speed_kmh", "engine_rpm", "engine_temp_c", "fuel_level_pct", "lon", "lat") and val is not None:
                data[key] = val
        return data

