from fastapi import APIRouter, HTTPException, Depends, status
from datetime import timedelta, datetime, timezone
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from config import db
from typing import Annotated
from models.usuario import Usuario
from dotenv import load_dotenv
from jose import jwt
import os
from desp import db_dependency, bcrypt_context,user_dependency

load_dotenv()

RouterUsers = APIRouter(prefix="/usuario", tags=["Usuarios"])

SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ALGORITHM = os.getenv("AUTH_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class UserCreateRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    role: str
    token_type: str

def authenticate_user(username: str, password: str, db):
    user = db.query(Usuario).filter(Usuario.name == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.password):
        return False
    
    return user

def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

@RouterUsers.get("/lista-usuarios")
def read_test(user: user_dependency, db: db_dependency):
    listaUsers = (
        db.query(Usuario)
        .all()
    )
    return listaUsers

@RouterUsers.post("/registrar", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: UserCreateRequest):
    create_user_model = Usuario(
        name=create_user_request.username,
        role="ADMIN",  # Por defecto es administrador
        password=bcrypt_context.hash(create_user_request.password)
    )
    db.add(create_user_model)
    db.commit()

@RouterUsers.post("/login", response_model= Token)
async def loginAccesoToken(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    print(f"DATOS DEL FORMULARIO {form_data.username} {form_data.password}")
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.name, user.id , expires_delta=access_token_expires)
    return {"access_token": access_token,"role":user.role ,"token_type": "bearer"}