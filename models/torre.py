from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from config.db import Base


class Torre(Base):
    __tablename__ = "torre"

    id = Column(Integer, primary_key=True, index=True)
    nombreTag = Column(String(30), index=True)

    ciclo = relationship("Ciclo", back_populates="torre")