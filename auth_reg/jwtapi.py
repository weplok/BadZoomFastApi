import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from fastapi import Request, HTTPException, status
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

# ---- Настройки (вынеси в env в проде) ----
JWT_SECRET = os.getenv("JWT_SECRET", "changeme_super_secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")
ACCESS_COOKIE_NAME = os.getenv("ACCESS_COOKIE_NAME", "access_name")
REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "refresh_name")


# ---- Schemas ----
class RegisterIn(BaseModel):
    email: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = ""
    position: Optional[str] = ""
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


# ---- JWT helpers ----
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now, "type": "access"})
    encoded = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
    to_encode = {"sub": data.get("id")}
    now = datetime.utcnow()
    expire = now + (expires_delta if expires_delta else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    encoded = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded


def decode_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_invalid")


# ---- Middleware: ставим request.state.user для шаблонов/роутов ----
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        token = request.cookies.get(ACCESS_COOKIE_NAME)

        if token:
            try:
                # Пытаемся декодировать access token
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                if payload.get("type") == "access":
                    request.state.user = payload

            except jwt.ExpiredSignatureError:
                # Access токен просрочен — пробуем обновить через refresh
                refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
                if refresh_token:
                    async with httpx.AsyncClient(base_url=f"http://{request.url.hostname}") as client:
                        try:
                            resp = await client.post(
                                "/auth/refresh",
                                cookies={REFRESH_COOKIE_NAME: refresh_token}
                            )
                            if resp.status_code == 200:
                                # Новый access token пришёл в Set-Cookie, берем его из cookies ответа
                                new_access = resp.cookies.get(ACCESS_COOKIE_NAME)
                                if new_access:
                                    payload = jwt.decode(new_access, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                                    request.state.user = payload
                        except Exception:
                            request.state.user = None
                else:
                    request.state.user = None

            except jwt.PyJWTError:
                # Любая другая ошибка декодирования
                request.state.user = None

        response = await call_next(request)
        return response


# ---- Dependency для защищенных роутов ----
def get_current_user(request: Request):
    # Если middleware уже положил user в request.state -> возвращаем
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_current_user_without_401(request: Request):
    # Дубликат get_current_user для /auth
    user = getattr(request.state, "user", None)
    if not user:
        return None
    return user
