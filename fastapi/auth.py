from datetime import datetime, timedelta, timezone
from typing import Optional
import os

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    role: str


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def get_user(db: Session, username: str):
    from models import UserRecord
    return db.query(UserRecord).filter(UserRecord.username == username).first()


def create_user(db: Session, username: str, password: str, role: str = "user"):
    from models import UserRecord
    record = UserRecord(username=username, hashed_password=hash_password(password), role=role)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    record = get_user(db, username)
    if not record or not verify_password(password, record.hashed_password):
        return None
    return User(username=record.username, role=record.role)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise exc
    except JWTError:
        raise exc
    record = get_user(db, username)
    if not record:
        raise exc
    return User(username=record.username, role=record.role)
