from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from config.db import Base

class Ciclo(Base):
    __tablename__ = "ciclo"

    id = Column(Integer, primary_key=True, index=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    tipoFin = Column(String(30), index=True)
    numeroGripper = Column(Integer, index=True)
    lote = Column(String(30), index=True)

    id_etapa = Column(Integer, ForeignKey("etapa.id"), nullable=False)
    etapa = relationship("Etapa", back_populates="ciclo")

    id_torre = Column(Integer, ForeignKey("torre.id"), nullable=False)
    torre = relationship("Torre", back_populates="ciclo")

    alarma = relationship("Alarma", back_populates="ciclo")
    recetaXCiclo = relationship("RecetaXCiclo", back_populates="ciclo")