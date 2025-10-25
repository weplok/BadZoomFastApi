from fastapi import FastAPI, Request
from dotenv import load_dotenv
import os
import logging
import asyncio
import ahocorasick
import re

# ==============================
# Настройка логирования
# ==============================
logging.basicConfig(filename="chat_processor.log", level=logging.INFO, encoding="UTF-8")

# ==============================
# Инициализация FastAPI и ключа
# ==============================
app = FastAPI()
load_dotenv()
SERVER_KEY = os.getenv("SERVER_KEY")

# ==============================
# Регэксп и банворды
# ==============================
ALLOWED_RE = re.compile(r'^[\w\s\-\.\,\!\?\(\)\[\]\{\}\@\#\$\%\^\&\*\:\;\"\'\/\\]+$', re.UNICODE)
BANWORDS_FILE = "banwords.txt"

# Загружаем банворды из файла (если нет — создаём)
if not os.path.exists(BANWORDS_FILE):
    with open(BANWORDS_FILE, "w", encoding="utf-8") as f:
        f.write("дурак\nтупой\nидиот\nлох\nfuck\nshit\nbitch\nasshole\nmoron")

def load_banwords():
    with open(BANWORDS_FILE, "r", encoding="utf-8") as f:
        return [w.strip().lower() for w in f if w.strip()]

# ==============================
# Построение автомата Ахо-Корасика
# ==============================
def build_automaton(words):
    A = ahocorasick.Automaton()
    for word in words:
        A.add_word(word, word)
    A.make_automaton()
    return A

BANWORDS = load_banwords()
A = build_automaton(BANWORDS)


# ==============================
# Асинхронный валидатор
# ==============================
async def validate_message(text: str) -> tuple[bool, str]:
    await asyncio.sleep(0)  # не блокируем event loop

    text = text.strip()
    if not text:
        return False, "Пустое сообщение"

    if not ALLOWED_RE.match(text):
        return False, "Недопустимые символы"

    lowered = text.lower()
    for _, found in A.iter(lowered):
        return False, f"Запрещённое слово: {found}"

    return True, "OK"


# ==============================
# Эндпоинт для обработки сообщений
# ==============================
@app.post("/process_message")
async def process_message(req: Request):
    data = await req.json()

    if data.get("server_key", "not-key") != SERVER_KEY:
        logging.error("SERVER-KEY-ERROR")
        return {"status": "error", "reason": "invalid key"}

    message = data["message"]
    sender = data["sender"]

    # ---- Валидация ----
    is_valid, reason = await validate_message(message)
    if not is_valid:
        logging.warning(f"Message rejected from {sender}: {reason} | text='{message}'")
    else:
        logging.info(f"Message OK from {sender}: {message}")

    return {"status": "ok", "validation": reason}
