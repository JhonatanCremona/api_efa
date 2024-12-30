from sqlalchemy import Column, Integer, String,Date, Double,ForeignKey
from sqlalchemy.orm import relationship
from config.db import Base

class Sdda(Base):
    __tablename__ = "sdda"

    id = Column(Integer, primary_key=True, index=True)
    largo = Column(Integer, index=True)
    vertical = Column(Integer, index=True)
    posicionActual = Column(Integer, index=True)
    fechaRegistro = Column(Date, index=True)

    id_alarma = Column(Integer, ForeignKey("alarma.id"), nullable=False)
    alarma = relationship("Alarma", back_populates="sdda")
