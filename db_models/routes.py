from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Dict

class Route(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    origin: str = Field(..., min_length=2, max_length=100, description="Ciudad de origen")
    destination: str = Field(..., min_length=2, max_length=100, description="Ciudad de destino")
    truck_id: str = Field(..., description="ID del camion asignado")
    driver_id: str = Field(..., description="ID del chofer asignado")
    status: Optional[str] = Field("planned", description="Estado de la ruta (planned, in_transit, completed, cancelled)")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)

class RouteUpdate(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    origin: Optional[str] = None
    destination: Optional[str] = None
    truck_id: Optional[str] = None
    driver_id: Optional[str] = None
    status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_unset=True)

