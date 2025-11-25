from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.status import HTTP_303_SEE_OTHER

from database import RoomRepository
room_repository = RoomRepository()

from key import generation_key

app = FastAPI(title="Комнаты")
# Получаем абсолютный путь к директории проекта
BASE_DIR = Path(__file__).parent

# Подключаем статические файлы с абсолютными путями
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Подключаем шаблоны
templates = Jinja2Templates(directory=BASE_DIR / "templates")



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
        room_record = await room_repository.create_room(
            title=title,
            code=code
        )
        room_dict = room_record.to_dict()
        # Перенаправляем на домашнюю страницу
        return RedirectResponse(url=f"/rooms/room/{room_dict['code']}", status_code=HTTP_303_SEE_OTHER)


# Проверка существования комнаты
@app.get("/room_exists/{code}")
async def room_exists(code: str):
    room = await room_repository.get_room_by_code(code)
    return {"exists": bool(room)}


# Страница комнаты
@app.get("/room/{code}", response_class=HTMLResponse)
async def room_page(request: Request, code: str):
    room = await room_repository.get_room_by_code(code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return templates.TemplateResponse("room.html", {"request": request, "room_code": code})
