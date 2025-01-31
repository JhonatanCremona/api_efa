from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Double
from sqlalchemy.orm import relationship
from datetime import datetime
from config.db import Base


class historicoAlarma(Base):
    __tablename__ = "historicoalarma"

    id = Column(Integer, primary_key=True, unique=True)
    fechaRegistro = Column(DateTime, default=datetime.now())

    id_alarma = Column(Integer, ForeignKey("alarma_id"), nullable=False)
    alarma = relationship("Alarma", back_populates="historicoalarma")

    id_ciclo = Column(Integer, ForeignKey("ciclo_id"), nullable=False)
    ciclo = relationship("Ciclo", back_populates="historicoAlarma")
