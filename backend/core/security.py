from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ── Passwords ────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Genera hash bcrypt. Nunca almacenar texto plano."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica bcrypt sin propagar errores por hashes legacy/placeholder inválidos."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


# ── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_EXPIRE_MINUTES
    )
    payload["exp"] = expire
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency — extrae usuario del JWT. Inyectar en cada endpoint protegido."""
    payload = decode_token(token)
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token sin identidad")
    return payload


def require_escritura(current_user: dict = Depends(get_current_user)) -> dict:
    """Bloquea acceso a viewers (solo lectura) en endpoints de escritura."""
    if current_user.get("rol") == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: rol viewer no puede modificar datos",
        )
    return current_user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Solo el rol admin puede ejecutar esta accion."""
    if current_user.get("rol") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ejecutar esta accion",
        )
    return current_user
