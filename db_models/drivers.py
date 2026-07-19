from pydantic import BaseModel, Field

class Driver(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Nombre completo del chofer")
    license_level: str = Field(..., pattern="^[A-E]$", description="Tipo de licencia (A-E)")

    def to_dict(self) -> dict:
        return self.model_dump()
