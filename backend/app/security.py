import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 310_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt, expected = encoded.split("$", 2)
        actual = hash_password(password, salt).split("$")[-1]
        return hmac.compare_digest(actual, expected)
    except ValueError:
        return False


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": user.id, "tenant_id": user.tenant_id, "role": user.role, "iat": now, "exp": now + timedelta(minutes=settings.token_minutes)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    user = db.scalar(select(User).where(User.id == payload["sub"], User.tenant_id == payload["tenant_id"], User.active.is_(True)))
    if not user:
        raise HTTPException(status_code=401, detail="User unavailable")
    return user


def roles(*allowed: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Permission denied")
        return user
    return dependency
