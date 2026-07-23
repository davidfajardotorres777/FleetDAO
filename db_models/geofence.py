from pydantic import BaseModel, Field
from typing import List

class Geofence(BaseModel):
    name: str = Field(..., description="Nombre de la zona permitida")
    truck_id: str = Field(..., description="ID del camion asignado a esta zona")
    polygon: List[List[float]] = Field(..., description="Lista de coordenadas [lon, lat] que forman el poligono")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "truck_id": self.truck_id,
            "geometry": {
                "type": "Polygon",
                # Mongo pide el polígono como un array de arrays de coordenadas,
                # y la primera y última coordenada deben coincidir para cerrar el anillo
                "coordinates": [self.polygon]
            }
        }
