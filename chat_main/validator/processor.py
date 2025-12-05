import asyncio
import logging
import os
import re

import ahocorasick
from fastapi import FastAPI, Request
from dataclasses import dataclass

# Регэксп и банворды
ALLOWED_RE = re.compile(r'^[\w\s\-\.\,\!\?\(\)\[\]\{\}\@\#\$\%\^\&\*\:\;\"\'\/\\]+$', re.UNICODE)
BANWORDS_FILE = "banwords.txt"

@dataclass
class ValidateResult:
    is_valid: bool
    reason: str
    new_message: str = "not required"


# Загружаем банворды из файла (если нет — создаём)
if not os.path.exists(BANWORDS_FILE):
    with open(BANWORDS_FILE, "w", encoding="utf-8") as f:
        f.write("дурак\nтупой\nидиот\nлох\nfuck\nshit\nbitch\nasshole\nmoron")


def load_banwords():
    with open(BANWORDS_FILE, "r", encoding="utf-8") as f:
        return [w.strip().lower() for w in f if w.strip()]


# Построение автомата Ахо-Корасика (алгоритм проверки слов)
def build_automaton(words):
    A = ahocorasick.Automaton()
    for word in words:
        A.add_word(word, word)
    A.make_automaton()
    return A


BANWORDS = load_banwords()
A = build_automaton(BANWORDS)


# Асинхронный валидатор
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


# Функция валидации сообщений
async def process_message(msg_text, sender) -> ValidateResult:
    # ---- Валидация ----
    is_valid, reason = await validate_message(msg_text)

    if not is_valid:
        return ValidateResult(is_valid=is_valid, reason=reason, new_message="Bad message! NEW CORRECT MESSAGE HERE")

    return ValidateResult(is_valid=is_valid, reason=reason)
