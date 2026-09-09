from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import uuid

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class User(BaseModel):
    username: str
    role: str


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def get_user(db: AsyncSession, username: str):
    from models import UserRecord
    result = await db.execute(select(UserRecord).where(UserRecord.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, password: str, role: str = "user"):
    from models import UserRecord
    record = UserRecord(username=username, hashed_password=hash_password(password), role=role)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    record = await get_user(db, username)
    if not record or not verify_password(password, record.hashed_password):
        return None
    return User(username=record.username, role=record.role)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire, "type": "access"}, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": username, "exp": expire, "type": "refresh", "jti": str(uuid.uuid4())},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_refresh_token(token: str) -> str:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise exc
        username: str = payload.get("sub")
        if not username:
            raise exc
        return username
    except JWTError:
        raise exc


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise exc
        username: str = payload.get("sub")
        if not username:
            raise exc
    except JWTError:
        raise exc
    record = await get_user(db, username)
    if not record:
        raise exc
    return User(username=record.username, role=record.role)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
