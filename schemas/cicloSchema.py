from typing import List
from pydantic import BaseModel

class ProductoDataSchema(BaseModel):
    x: str  # Fecha en formato string (ISO 8601)
    y: float

class gHCicloProducto(BaseModel):
    nombreProducto: str
    lote: str
    nombreTorre: str
    data: List[ProductoDataSchema]


