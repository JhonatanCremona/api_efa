from sqlalchemy import Column, Integer, String, Double, ForeignKey, Float
from sqlalchemy.orm import relationship
from config.db import Base

class RecetarioXCiclo(Base):
    __tablename__ = "recetarioxciclo"

    id = Column(Integer, primary_key=True, index=True)
    cantidadNivelesFinalizado = Column(Integer, index=True)
    pesoPorNivel = Column(Double, index=True)

    id_recetario = Column(Integer, ForeignKey("recetario.id"), nullable=False)
    recetario = relationship("Recetario", back_populates="recetarioxciclo")

    id_ciclo_desmoldeo = Column(Integer, ForeignKey("ciclodesmoldeo.id"), nullable=False)
    ciclodesmoldeo = relationship("CicloDesmoldeo", back_populates="recetarioxciclo")