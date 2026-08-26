from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict

class Geofence(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    name: str = Field(..., description="Nombre de la zona permitida")
    truck_id: str = Field(..., description="ID del camion asignado a esta zona")
    polygon: List[List[float]] = Field(..., description="Lista de coordenadas [lon, lat] que forman el poligono")

    def to_dict(self) -> dict:
        doc = self.model_dump(exclude={"polygon"})
        doc["name"] = self.name
        doc["truck_id"] = self.truck_id
        doc["geometry"] = {
            "type": "Polygon",
            "coordinates": [self.polygon]
        }
        return doc

class GeofenceUpdate(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    name: Optional[str] = None
    truck_id: Optional[str] = None
    polygon: Optional[List[List[float]]] = None

    def to_dict(self) -> dict:
        data = {}
        if self.name is not None:
            data["name"] = self.name
        if self.truck_id is not None:
            data["truck_id"] = self.truck_id
        if self.polygon is not None:
            data["geometry"] = {
                "type": "Polygon",
                "coordinates": [self.polygon]
            }
        # Incluir otros campos extra actualizados
        for key, val in self.__dict__.items():
            if key not in ("name", "truck_id", "polygon") and val is not None:
                data[key] = val
        return data

