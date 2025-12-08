import asyncio
import logging
import os
import re

import ahocorasick
from dataclasses import dataclass
import importlib.resources as res


# Регэксп
ALLOWED_RE = re.compile(r'^[\w\s\-\.\,\!\?\(\)\[\]\{\}\@\#\$\%\^\&\*\:\;\"\'\/\\]+$', re.UNICODE)
# Регулярка для замены недопустимых символов
DISALLOWED_RE = re.compile(r'[^\w\s\-\.\,\!\?\(\)\[\]\{\}\@\#\$\%\^\&\*\:\;\"\'\/\\]', re.UNICODE)


@dataclass
class ValidateResult:
    is_valid: bool
    reason: str
    new_message: str = "not required"


# Построение автомата Ахо-Корасика (алгоритм проверки слов)
def build_automaton(words):
    A = ahocorasick.Automaton()
    for word in words:
        A.add_word(word, word)
    A.make_automaton()
    return A


# Берем банворды из data/banwordlist.txt и загружаем в автомат Ахо-Корасика
BANWORDS = list()
with res.files("validator.data").joinpath("banwordlist.txt").open("r", encoding="utf-8") as f:
    for word in f.readlines():
        BANWORDS.append(word.strip())
A = build_automaton(BANWORDS)


# Асинхронный валидатор
async def validate_message(text: str) -> tuple[bool, str, str]:
    await asyncio.sleep(0)  # не блокируем event loop

    text = text.strip()
    if not text:
        return (False, "Пустое сообщение", " ")

    if not ALLOWED_RE.match(text):
        sanitized_text = DISALLOWED_RE.sub(" ", text)
        return (False, "Недопустимые символы", sanitized_text)

    lowered = text.lower()
    text = list(text)
    is_correct = True
    for i, found in A.iter(lowered):
        is_correct = False
        text[(i+1)-len(found):(i+1)] = "*"*len(found)
    if not is_correct:
        text = "".join(text)
        return (False, f"Найдены ban-слова. Цензура: {text}", text)

    return (True, "OK", "-")


# Функция валидации сообщений
async def process_message(msg_text, sender) -> ValidateResult:
    # ---- Валидация ----
    is_valid, reason, new_message = await validate_message(msg_text)

    if not is_valid:
        return ValidateResult(is_valid=is_valid, reason=reason, new_message=new_message)

    return ValidateResult(is_valid=is_valid, reason=reason)


if __name__ == "__main__":
    text = "я дурак!"
    print(validate_message(text))