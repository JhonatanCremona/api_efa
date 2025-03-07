from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Double
from sqlalchemy.orm import relationship
from datetime import datetime
from config.db import Base


class TorreConfiguraciones(Base):
    __tablename__ = "torreconfiguraciones"

    id = Column(Integer, primary_key=True, unique=True)
    fecha_registro = Column(DateTime, default=datetime.now())
    tipo = Column(String(30), index=True)
    nivel = Column(Integer, index=True)
    valor = Column(Integer, index=True)

    id_torreNum = Column(Integer, ForeignKey("torre.NTorre"), nullable=False)
    id_torre = Column(String(30), index=True)
    torre = relationship("Torre", back_populates="torreconfiguraciones")
