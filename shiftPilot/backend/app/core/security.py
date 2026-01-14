from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel
from app.core.config import settings

ALGORITHM = "HS256"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None:
            return None
        return TokenData(user_id=int(user_id), email=email)
    except JWTError as e:
        return None