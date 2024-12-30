from sqlalchemy import Column, Integer, String
from config.db import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key= True, index=True)
    name = Column(String(255), index=True)
    password = Column(String(255), unique=True, index=True)
    
