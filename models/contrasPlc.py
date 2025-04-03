from sqlalchemy import Column, Integer, String, Date
from config.db import Base

class ContrasPLC(Base):
    __tablename__ = "contrasplc"

    id = Column(Integer, primary_key= True, index=True)
    contra = Column(String(255), unique=True, index=True)
    fecha_inicio = Column(Date, index=True)
    fecha_bloqueo = Column(Date, index=True)