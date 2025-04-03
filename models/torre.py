from sqlalchemy import Column, Integer, String, Double, ForeignKey, Float
from sqlalchemy.orm import relationship
from config.db import Base


class Torre(Base):
    __tablename__ = "torre"

    NTorre = Column(Integer, primary_key=True, autoincrement=True)

    id = Column(String(30), index=True)
    nombreTag = Column(String(30), index=True)
    cantidadNiveles = Column(Integer, index=True)

    id_recetario = Column(Integer, ForeignKey("recetario.id"), nullable=False)
    recetario = relationship("Recetario", back_populates="torre")

    hBastidor = Column(Integer, index=True)
    hAjuste = Column(Integer, index=True)
    hAjusteN1 = Column(Integer, index=True)
    DisteNivel = Column(Integer, index=True)
    ActualizarTAG = Column(String(30), index=True)
    
    ciclodesmoldeo = relationship("CicloDesmoldeo", back_populates="torre")

    torreconfiguraciones = relationship("TorreConfiguraciones", back_populates="torre")