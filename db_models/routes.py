from pydantic import BaseModel, Field

class Route(BaseModel):
    origin: str = Field(..., min_length=2, max_length=100, description="Ciudad de origen")
    destination: str = Field(..., min_length=2, max_length=100, description="Ciudad de destino")
    truck_id: str = Field(..., description="ID del camion asignado")
    driver_id: str = Field(..., description="ID del chofer asignado")

    def to_dict(self) -> dict:
        return self.model_dump()
