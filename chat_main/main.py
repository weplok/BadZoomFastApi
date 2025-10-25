import logging
import os

import asyncio
import datetime
import httpx
import json
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from sqlmodel import SQLModel, Field, create_engine, Session, select

app = FastAPI()

DATABASE_URL = "sqlite:///messages.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
load_dotenv()
SERVER_KEY = os.getenv("SERVER_KEY")
PROCESSOR_URL = os.getenv("PROCESSOR_URL")
connected_clients = set()
logging.basicConfig(filename="chat_main.log", level=logging.INFO, encoding="UTF-8")


# ---------- Модель ----------
class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    sender: str
    text: str
    room: str = "qwerty"
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# ---------- Инициализация ----------
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


@app.get("/", response_class=HTMLResponse)
async def get():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read(), media_type="text/html; charset=utf-8")


# ---------- WebSocket ----------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)

    user_agent = websocket.headers.get("user-agent", "Unknown user")
    room = "qwerty"  # заглушка, потом можно будет менять по URL или параметру

    # Загружаем последние 50 сообщений из нужной комнаты
    with Session(engine) as session:
        msgs = session.exec(
            select(Message)
            .where(Message.room == room)
            .order_by(Message.id.desc())
            .limit(50)
        ).all()

        for msg in reversed(msgs):
            await websocket.send_text(json.dumps({
                "sender": msg.sender,
                "text": msg.text,
                "room": msg.room,
                "time": msg.timestamp.isoformat()
            }))

    try:
        while True:
            text = await websocket.receive_text()
            msg = Message(sender=user_agent, text=text, room=room)

            # Сохраняем сообщение
            with Session(engine) as session:
                session.add(msg)
                session.commit()
                session.refresh(msg)

            some = asyncio.create_task(process_message(msg))
            result = await some
            logging.info(result.text)

            data = {
                "sender": msg.sender,
                "text": msg.text,
                "room": msg.room,
                "time": msg.timestamp.isoformat()
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

    except:
        connected_clients.remove(websocket)


async def process_message(msg: Message):
    try:
        async with httpx.AsyncClient() as client:
            return await client.post(f"{PROCESSOR_URL}/process_message", json={
                "message": msg.text,
                "sender": msg.sender,
                "room": "qwerty",
                "server_key": SERVER_KEY
            })
    except Exception as e:
        print(f"Processing error: {e}")
