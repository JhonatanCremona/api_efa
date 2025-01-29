from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Double
from sqlalchemy.orm import relationship
from config.db import Base

class Ciclo(Base):
    __tablename__ = "ciclo"

    id = Column(Integer, primary_key=True, index=True)
    fecha_inicio = Column(DateTime, index=True, nullable=False)
    fecha_fin = Column(DateTime, index=True, nullable=False)
    estadoMaquina = Column(String(50), nullable=False)
    bandaDesmolde = Column(Integer, nullable=False)
    lote = Column(String(50), nullable=False)
    tiempoDesmolde = Column(Double, nullable=False)
    pesoDesmontado = Column(Double, nullable=False)
    

    id_etapa = Column(Integer, ForeignKey("etapa.id"), nullable=False)
    etapa = relationship("Etapa", back_populates="ciclo")

    id_torre = Column(Integer, ForeignKey("torre.id"), nullable=False)
    torre = relationship("Torre", back_populates="ciclo")

    alarma = relationship("Alarma", back_populates="ciclo")
    recetaXCiclo = relationship("RecetaXCiclo", back_populates="ciclo")