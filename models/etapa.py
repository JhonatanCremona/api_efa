from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from config.db import Base

class Etapa(Base):
    __tablename__ = "etapa"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(30), index=True)

    ciclo = relationship("Ciclo", back_populates="etapa")