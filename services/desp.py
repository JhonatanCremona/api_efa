from typing import Annotated
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from dotenv import load_dotenv
from jose import jwt, JWTError

from config.db import SessionLocal
import os

load_dotenv()

SECRET_KEY = os.getenv('AUTH_SECRET_KEY')
ALGORITHM = os.getenv('AUTH_ALGORITHM')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')
oauth2_bearer_dependency = Annotated[str, Depends(oauth2_bearer)]

async def get_current_user(token: oauth2_bearer_dependency):
    try:
        print("")
        payload = jwt.decode(token, SECRET_KEY, algorithms={ALGORITHM} )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Missing username in token')
        return { "username": username }
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')
    
user_dependency = Annotated[dict, Depends(get_current_user)]