from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Dict

class Truck(BaseModel):
    """
    Modelo Pydantic para la entidad Camión (Truck).
    
    Usa `extra='allow'` para permitir que agregues o modifiques variables
    personalizadas por tu cuenta sin que Pydantic devuelva errores de validación.
    """
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    brand: str = Field(..., min_length=2, max_length=50, description="Marca del camión")
    capacity_tons: float = Field(..., gt=0, lt=100, description="Capacidad de carga en toneladas")
    
    # Variables opcionales / adicionales comunes
    model: Optional[str] = Field(None, description="Modelo del vehículo (ej. FH16, Actros)")
    year: Optional[int] = Field(None, ge=1970, le=2030, description="Año de fabricación")
    license_plate: Optional[str] = Field(None, description="Patente o dominio del vehículo")
    status: Optional[str] = Field("active", description="Estado del vehículo (active, maintenance, inactive)")

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a un diccionario limpio para MongoDB."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_mongo(cls, doc: dict) -> "Truck":
        """Crea una instancia de Truck a partir de un documento de MongoDB."""
        if not doc:
            return None
        doc_copy = doc.copy()
        if "_id" in doc_copy:
            doc_copy["id"] = str(doc_copy.pop("_id"))
        return cls(**doc_copy)

class TruckUpdate(BaseModel):
    """
    Modelo para la actualización parcial o total de un Camión (PUT / PATCH).
    Permite modificar cualquier campo existente o agregar variables nuevas.
    """
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    brand: Optional[str] = None
    capacity_tons: Optional[float] = None
    model: Optional[str] = None
    year: Optional[int] = None
    license_plate: Optional[str] = None
    status: Optional[str] = None

    def to_dict() -> Dict[str, Any]:
        """Devuelve únicamente los campos que fueron explícitamente enviados para actualizar."""
        return self.model_dump(exclude_unset=True)

