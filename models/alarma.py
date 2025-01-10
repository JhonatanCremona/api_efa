from sqlalchemy import Column, Integer, String, DateTime,ForeignKey
from sqlalchemy.orm import relationship
from config.db import Base

class Alarma(Base):
    __tablename__ = "alarma"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(30), index=True)
    fechaRegistro = Column(DateTime, index=True)
    descripcion = Column(String(255), index=True)

    id_ciclo = Column(Integer, ForeignKey("ciclo.id"), nullable=False)
    ciclo = relationship("Ciclo", back_populates="alarma")

    sdda = relationship("Sdda", back_populates="alarma")
    kuka = relationship("Kuka", back_populates="alarma")