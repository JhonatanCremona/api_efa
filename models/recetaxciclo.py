from sqlalchemy import Column, Integer, String, Double, ForeignKey, Float
from sqlalchemy.orm import relationship
from config.db import Base

class RecetaXCiclo(Base):
    __tablename__ = "recetaxciclo"

    id = Column(Integer, primary_key=True, index=True)
    cantidadNivelesFinalizado = Column(Integer, index=True)

    id_recetario = Column(Integer, ForeignKey("recetario.id"), nullable=False)
    recetario = relationship("Recetario", back_populates="recetaXCiclo")

    id_ciclo = Column(Integer, ForeignKey("ciclo.id"), nullable=False)
    ciclo = relationship("Ciclo", back_populates="recetaXCiclo")

class Recetario(Base):
    __tablename__ = "recetario"

    id = Column(Integer, primary_key=True, index=True)
    codigoProducto = Column(String(50), index=True) 
    nroGripper = Column(Integer, index=True)
    pesoPorNivel = Column(Double, index=True)

    recetaXCiclo = relationship("RecetaXCiclo", back_populates="recetario")