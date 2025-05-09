from sqlalchemy import Column, Integer, String, DateTime,ForeignKey
from sqlalchemy.orm import relationship
from config.db import Base
from datetime import datetime

class Alarma(Base):
    __tablename__ = "alarma"

    id = Column(Integer, primary_key=True, index=True, autoincrement= False)
    tipoAlarma = Column(String(20), index=True)
    descripcion = Column(String(255), index=True)
    fechaRegistro = Column(DateTime, default=datetime.now)

    sdda = relationship("Sdda", back_populates="alarma")
    robot = relationship("Robot", back_populates="alarma")
    historicoAlarma = relationship("HistoricoAlarma", back_populates="alarma")