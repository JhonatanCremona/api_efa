from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from config.db import Base

class Robot(Base):
    __tablename__ = "robot"

    id = Column(Integer, primary_key=True, index=True)
    posicionX = Column(Integer, index=True)
    posicionY = Column(Integer, index=True)
    posicionZ = Column(Integer, index=True)
    fechaRegistro = Column(Date, index=True)

    id_alarma = Column(Integer, ForeignKey("alarma.id"), nullable=False)
    alarma = relationship("Alarma", back_populates="robot")
