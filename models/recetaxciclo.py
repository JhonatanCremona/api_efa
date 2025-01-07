from sqlalchemy import Column, Integer, String, Double, ForeignKey
from sqlalchemy.orm import relationship
from config.db import Base

class RecetaXCiclo(Base):
    __tablename__ = "recetaxciclo"

    id = Column(Integer, primary_key=True, index=True)
    pesoProductoXFila = Column(Double, index=True)
    cantidadNiveles = Column(Integer, index=True)

    id_recetario = Column(Integer, ForeignKey("recetario.id"), nullable=False)
    recetario = relationship("Recetario", back_populates="recetaXCiclo")

    id_ciclo = Column(Integer, ForeignKey("ciclo.id"), nullable=False)
    ciclo = relationship("Ciclo", back_populates="recetaXCiclo")

class Recetario(Base):
    __tablename__ = "recetario"

    id = Column(Integer, primary_key=True, index=True)
    numeroGripper = Column(Integer, index=True)
    tipoDeMolde = Column(String(50), index=True) 
    nombre = Column(String(50), index=True)

    recetaXCiclo = relationship("RecetaXCiclo", back_populates="recetario")