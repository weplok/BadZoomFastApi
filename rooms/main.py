import random
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from tortoise import fields
from tortoise.contrib.fastapi import register_tortoise
from tortoise.exceptions import DoesNotExist
from tortoise.models import Model

from key import generation_key

app = FastAPI(title="Комнаты")
# Получаем абсолютный путь к директории проекта
BASE_DIR = Path(__file__).parent

# Подключаем статические файлы с абсолютными путями
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Подключаем шаблоны
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class Room(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    code = fields.CharField(max_length=8, unique=True)

    class Meta:
        table = "rooms"


async def generate_room_code():
    return ''.join(str(random.randint(0, 9)) for _ in range(8))


async def def_create_room():
    code = await generate_room_code()
    while await Room.exists(code=code):
        code = await generate_room_code()
    room = await Room.create(code=code)
    return room


async def get_room_by_code(code: str):
    try:
        room = await Room.get(code=code)
        return room
    except DoesNotExist:
        return None


# Инициализация Tortoise ORM
register_tortoise(
    app,
    db_url="sqlite://rooms.db",
    modules={"models": ["main"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


@app.get("/create_room", response_class=HTMLResponse)
async def index(request: Request):
    key = generation_key()
    return templates.TemplateResponse(
        "create_room.html",
        {
            "request": request,
            "key": key,
            "title": "Создание комнаты"
        }
    )


# Создание новой комнаты
@app.post("/create_room")
async def create_room(
        request: Request,
        title: str = Form(...),
        code: str = Form(...)
):
    try:
            #TODO: Добавление комнаты в БД
            '''key_list.clear()
            key_list.update({
                "title": title,
                "code": code,
            })'''
        # Перенаправляем на домашнюю страницу
        return RedirectResponse(url="/homepage", status_code=HTTP_303_SEE_OTHER)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Проверка существования комнаты
@app.get("/room_exists/{code}")
async def room_exists(code: str):
    room = await get_room_by_code(code)
    return {"exists": bool(room)}


# Страница комнаты
@app.get("/room/{code}", response_class=HTMLResponse)
async def room_page(request: Request, code: str):
    room = await get_room_by_code(code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return templates.TemplateResponse("room.html", {"request": request, "room_code": code})
