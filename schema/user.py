from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    password: str

    class Config:
        orm_mode = True

class Usuario(BaseModel):
    id: int
    name: str
    password: str

    class Config:
        orm_mode = True