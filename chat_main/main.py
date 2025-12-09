import asyncio
import datetime
import json
import logging
import os
from http.cookies import SimpleCookie
from pathlib import Path

import httpx
import jwt
from fastapi import FastAPI, Request, WebSocket
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware import Middleware
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Field, create_engine, Session, select

import validator

from jwtapi import AuthMiddleware

app = FastAPI(middleware=[Middleware(AuthMiddleware)])

# Получаем абсолютный путь к директории проекта
BASE_DIR = Path(__file__).parent

# Подключаем статические файлы с абсолютными путями
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Подключаем шаблоны
templates = Jinja2Templates(directory=BASE_DIR / "templates")

DATABASE_URL = "sqlite:///messages.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
connected_clients = set()
logging.basicConfig(filename="chat_main.log", level=logging.INFO, encoding="UTF-8")
client = None

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.getenv("JWT_SECRET", "secret")
ACCESS_COOKIE_NAME = os.getenv("ACCESS_COOKIE_NAME", "access-name")


# ---------- Модель ----------
class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    id_in_html: str = Field(default_factory=validator.id_in_html)
    sender: str
    text: str
    room: str = "qwerty"
    visibility: bool = True
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# ---------- Инициализация ----------
@app.on_event("startup")
def on_startup():
    global client
    client = httpx.AsyncClient()
    SQLModel.metadata.create_all(engine)


@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()


@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Главная страница"
        }
    )


# Парсер куки для получения JWT юзера
def parse_cookies_from_header(cookie_header: str) -> dict:
    if not cookie_header:
        return {}
    c = SimpleCookie()
    c.load(cookie_header)
    return {k: morsel.value for k, morsel in c.items()}


# ---------- WebSocket ----------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    cookie_header = None
    for k, v in websocket.headers.raw:
        # raw — list of tuples bytes, decode
        hk = k.decode().lower()
        if hk == "cookie":
            cookie_header = v.decode()
            break

    cookies = parse_cookies_from_header(cookie_header)
    token = cookies.get(ACCESS_COOKIE_NAME)
    user = None
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("type") == "access":
                user = payload
        except Exception:
            user = None

    if not user:
        # можно закрыть соединение с 401
        await websocket.close(code=1008)
        return

    connected_clients.add(websocket)

    user_name = f"{user['last_name']} {user['first_name'][0]}.{user['middle_name'][0]}."
    room = "qwerty"  # заглушка, потом можно будет менять по URL или параметру

    # Загружаем последние 50 сообщений из нужной комнаты
    with Session(engine) as session:
        msgs = session.exec(
            select(Message)
            .where(Message.room == room)
            .where(Message.visibility)
            .order_by(Message.id.desc())
            .limit(50)
        ).all()

        for msg in reversed(msgs):
            await websocket.send_text(json.dumps({
                "htmlid": msg.id_in_html,
                "sender": msg.sender,
                "text": msg.text,
                "room": msg.room,
                "visibility": msg.visibility,
                "time": msg.timestamp.isoformat()
            }))

    # Обработка получения сообщений от клиента
    try:
        while True:
            text = await websocket.receive_text()
            msg = Message(sender=user_name, text=text, room=room)

            process_message_task = asyncio.create_task(validator.process_message(msg.text, msg.sender))

            logging.info(f"New message[{msg.id_in_html}]: {msg.text}")

            # Сообщения отправляются текущим connected_clients
            await send_msg_to_clients(msg)

            # Ожидаем ответ валидатора и при необходимости - отправляем новое сообщение
            process_result = await process_message_task
            if not process_result.is_valid:
                logging.warning(f"Incorrect message from {msg.sender}: {process_result.reason} | text='{msg.text}'")
                msg.text = process_result.new_message
                await send_msg_to_clients(msg)

            # Сохраняем сообщение
            with Session(engine) as session:
                session.add(msg)
                session.commit()
                session.refresh(msg)

    except Exception as e:
        connected_clients.remove(websocket)


@app.exception_handler(HTTPException)
async def websocket_http_exception_handler(request: Request, exc: HTTPException):
    if request.scope["type"] == "websocket":
        websocket: WebSocket = request.scope.get("websocket")

        if websocket and websocket.application_state == WebSocketState.CONNECTED:
            # отображаем 401 как 1008
            code = 1008 if exc.status_code == 401 else 1011
            await websocket.close(code=code, reason=exc.detail)
        return

    # обычный HTTP запрос → как раньше
    if exc.status_code == 401:
        return RedirectResponse(url="/auth", status_code=302)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def send_msg_to_clients(msg: Message):
    data = {
        "htmlid": msg.id_in_html,
        "sender": msg.sender,
        "text": msg.text,
        "room": msg.room,
        "visibility": msg.visibility,
        "time": msg.timestamp.isoformat(),
    }

    # Рассылаем только тем, кто в этой комнате
    dead = []
    for client in connected_clients:
        try:
            # Тут можно будет хранить мапу {websocket: room}, но пока фильтруем по заглушке
            await client.send_text(json.dumps(data))
        except:
            dead.append(client)
    for d in dead:
        connected_clients.remove(d)
