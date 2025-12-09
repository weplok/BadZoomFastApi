import os

import jwt
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_COOKIE_NAME = os.getenv("ACCESS_COOKIE_NAME", "access_token")
REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")


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
