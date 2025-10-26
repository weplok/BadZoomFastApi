from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
from starlette.status import HTTP_303_SEE_OTHER

from database import UserRepository
user_repository = UserRepository()

from key import generation_key

app = FastAPI(title="Система регистрации", version="1.0.0")

# Получаем абсолютный путь к директории проекта
BASE_DIR = Path(__file__).parent

# Подключаем статические файлы с абсолютными путями
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Подключаем шаблоны
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Хранилище пользователей
current_user_data: dict = {}
key_list: dict = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    await user_repository.create_defoult_admin()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Главная страница"
        }
    )


@app.get("/homepage", response_class=HTMLResponse)
async def home(request: Request):
    full_name = '{0} {1} {2}'.format(current_user_data['first_name'], current_user_data['last_name'], current_user_data['middle_name'])
    is_admin = current_user_data['is_admin']
    if is_admin:
          return templates.TemplateResponse(
              "homepage_admin.html",
              {
                  "request": request,
                  "full_name": full_name,
                  "title": "Домашняя страница"
              }
        )
    return templates.TemplateResponse(
        "homepage.html",
        {
            "request": request,
            "full_name": full_name,
            "title": "Домашняя страница"
        }
    )


@app.get("/create_room", response_class=HTMLResponse)
async def index(request: Request):
    return RedirectResponse(url=f"http://138.124.14.160:8013/create_room")


@app.post("/connection_room", response_class=HTMLResponse)
async def connection_room(request: Request, code: str = Form(...)):
    return RedirectResponse(url=f"http://138.124.14.160:8013/rooms/{code}")


@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "title": "Регистрация"
        }
    )


# Обработка формы регистрации
@app.post("/register")
async def register_user(
        request: Request,
        email: str = Form(...),
        first_name: str = Form(...),
        last_name: str = Form(...),
        middle_name: str = Form(...),
        password: str = Form(...),
        password_confirm: str = Form(...),
        position: str = Form(...)
):
    try:
        # Проверка email
        if "@" not in email:
            raise HTTPException(status_code=400, detail=f"Неверный формат email {email}")

        # Проверка паролей
        if password != password_confirm:
            raise HTTPException(status_code=400, detail="Пароли не совпадают")

        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 6 символов")

        response_email = await user_repository.get_user_by_email(email)
        if response_email:
            return RedirectResponse(url="/sign", status_code=HTTP_303_SEE_OTHER)

        # Регистрируем пользователя
        user_record = await user_repository.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            position=position,
            password=password
        )
        current_user_data.clear()  # Очищаем предыдущие данные
        current_user_data.update({
            'email': user_record.email,
            'first_name': user_record.first_name,
            'last_name': user_record.last_name,
            'middle_name': user_record.middle_name,
            'position': user_record.position,
            'is_connecting_to_rooms': user_record.is_connecting_to_rooms,
            'is_creating_rooms': user_record.is_creating_rooms,
            'is_admin': user_record.is_admin
        })

        # Перенаправляем на домашнюю страницу
        return RedirectResponse(url="/homepage", status_code=HTTP_303_SEE_OTHER)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/create_room")
async def register_user(
        request: Request,
        title: str = Form(...),
        code: str = Form(...)
):
    try:
        key_list.clear()
        key_list.update({
            "title": title,
            "code": code,
        })
        print(key_list)
        # Перенаправляем на домашнюю страницу
        return RedirectResponse(url="/homepage", status_code=HTTP_303_SEE_OTHER)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sign")
async def sign_user(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
):
    try:
        # Проверка email
        if "@" not in email:
            raise HTTPException(status_code=400, detail="Неверный формат email")
        #дописать проверку на пароль и почту в бд

        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 6 символов")

        response_user = await user_repository.get_sign_user(email, password)
        if not response_user['status']:
            raise HTTPException(status_code=400, detail=response_user['response'])

        user_record = response_user['user']

        current_user_data.clear()  # Очищаем предыдущие данные
        current_user_data.update({
            'email': user_record.email,
            'first_name': user_record.first_name,
            'last_name': user_record.last_name,
            'middle_name': user_record.middle_name,
            'position': user_record.position,
            'is_connecting_to_rooms': user_record.is_connecting_to_rooms,
            'is_creating_rooms': user_record.is_creating_rooms,
            'is_admin': user_record.is_admin
        })

        return RedirectResponse(url="/homepage", status_code=HTTP_303_SEE_OTHER)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sign", response_class=HTMLResponse)
async def sign_form(request: Request):
    return templates.TemplateResponse(
        "sign.html",
        {
            "request": request,
            "title": "Вход пользователя"
        }
    )


# Страница списка пользователей
@app.get("/users", response_class=HTMLResponse)
async def users_list(request: Request):
    all_users = await user_repository.get_all_users()

    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "users": all_users,
            "title": "Список пользователей"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)