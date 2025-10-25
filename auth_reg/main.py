from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
from starlette.status import HTTP_303_SEE_OTHER

from database import UserRepository

user_repository = UserRepository()

app = FastAPI(title="Система регистрации", version="1.0.0")

# Получаем абсолютный путь к директории проекта
BASE_DIR = Path(__file__).parent

# Подключаем статические файлы с абсолютными путями
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Подключаем шаблоны
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Хранилище пользователей
users_db = []




@app.get("/homepage", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "homepage.html",
        {
            "request": request,
            "title": "Домашний экран"
        }
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Главная страница"
        }
    )


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
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

        # Регистрируем пользователя
        user_record = await user_repository.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            position=position,
            password=password
        )
        user_dict = user_record.to_dict()
        users_db.append(user_dict)

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