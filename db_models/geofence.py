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
                # Mongo requires the polygon to be an array of arrays of coordinates
                # and the first and last coordinate must be the same to close the ring
                "coordinates": [self.polygon]
            }
        }
