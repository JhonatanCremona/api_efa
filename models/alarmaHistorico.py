from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Double, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from config.db import Base


class HistoricoAlarma(Base):
    __tablename__ = "historicoalarma"

    id = Column(Integer, primary_key=True, unique=True)
    #fechaRegistro = Column(DateTime, default=datetime.now())
    tiempo_inicio = Column(DateTime, nullable=True)
    tiempo_fin = Column(DateTime, nullable=True)
    duracion_minutos = Column(Float, nullable=True)
    
    estadoAlarma = Column(Boolean, index=True)

    id_alarma = Column(Integer, ForeignKey("alarma.id"), nullable=False)
    alarma = relationship("Alarma", back_populates="historicoAlarma")

    id_ciclo_desmoldeo = Column(Integer, ForeignKey("ciclodesmoldeo.id"), nullable=True)
    ciclodesmoldeo = relationship("CicloDesmoldeo", back_populates="historicoAlarma")