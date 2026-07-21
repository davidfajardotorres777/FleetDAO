from typing import Optional
from pydantic import BaseModel, Field

class Driver(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Nombre completo del chofer")
    license_level: str = Field(..., pattern="^[A-E]$", description="Tipo de licencia (A-E)")
    license_url: Optional[str] = Field(None, description="URL de la imagen de la licencia física en MinIO")

    def to_dict(self) -> dict:
        return self.model_dump()
