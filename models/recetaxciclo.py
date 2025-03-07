from sqlalchemy import Column, Integer, String, Double, ForeignKey, Float
from sqlalchemy.orm import relationship
from config.db import Base

class RecetaXCiclo(Base):
    __tablename__ = "recetaxciclo"

    id = Column(Integer, primary_key=True, index=True)
    cantidadNivelesFinalizado = Column(Integer, index=True)
    pesoPorNivel = Column(Double, index=True)

    id_recetario = Column(Integer, ForeignKey("recetario.id"), nullable=False)
    recetario = relationship("Recetario", back_populates="recetaXCiclo")

    id_ciclo = Column(Integer, ForeignKey("ciclo.id"), nullable=False)
    ciclo = relationship("Ciclo", back_populates="recetaXCiclo")

class Recetario(Base):
    __tablename__ = "recetario"

    id = Column(Integer, primary_key=True, index=True)
    codigoProducto = Column(String(50), index=True)  #NOMBRE
    nroGripper = Column(Integer, index=True)
    tipoMolde = Column(String(50), index=True)
    anchoProducto = Column(Integer, index=True)
    altoProducto = Column(Integer, index=True)
    largoProducto = Column(Integer, index=True)
    pesoProducto = Column(Integer, index=True)
    moldesNivel = Column(Integer, index=True)
    altoMolde = Column(Integer, index=True)
    largoMolde = Column(Integer, index=True)
    ajusteAltura = Column(Integer, index=True)
    cantidadNiveles = Column(Integer, index=True)
    deltaNiveles = Column(Integer, index=True)
    n1Altura = Column(Integer, index=True)
    bastidorAltura = Column(Integer, index=True)
    ajusteN1Altura = Column(Integer, index=True)
    
    recetaXCiclo = relationship("RecetaXCiclo", back_populates="recetario")

    torre = relationship("Torre", back_populates="recetario")