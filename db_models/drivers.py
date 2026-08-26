from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Dict

class Driver(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    name: str = Field(..., min_length=2, max_length=100, description="Nombre completo del chofer")
    license_level: str = Field(..., pattern="^[A-E]$", description="Tipo de licencia (A-E)")
    phone: Optional[str] = Field(None, description="Teléfono de contacto")
    status: Optional[str] = Field("active", description="Estado del chofer (active, inactive, on_leave)")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)

class DriverUpdate(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    name: Optional[str] = None
    license_level: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_unset=True)

