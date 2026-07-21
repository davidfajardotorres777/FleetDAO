from pydantic import BaseModel, Field

class Truck(BaseModel):
    brand: str = Field(..., min_length=2, max_length=50, description="Marca del camion")
    capacity_tons: float = Field(..., gt=0, lt=100, description="Capacidad de carga en toneladas")

    def to_dict(self) -> dict:
        return self.model_dump()
