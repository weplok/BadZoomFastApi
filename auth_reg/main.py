from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path

app = FastAPI(title="Система регистрации", version="1.0.0")

# Получаем абсолютный путь к директории проекта
BASE_DIR = Path(__file__).parent

# Подключаем статические файлы с абсолютными путями
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Подключаем шаблоны
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Хранилище пользователей
users_db = []


# Главная страница - форма регистрации
@app.get("/", response_class=HTMLResponse)
async def registration_form(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "title": "Регистрация пользователя"
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

        # Проверяем не занят ли email
        if any(user['email'] == email for user in users_db):
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

        # Сохраняем пользователя
        user_record = {
            "id": len(users_db) + 1,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "position": position,
        }
        users_db.append(user_record)

        # Перенаправляем на страницу успеха
        return templates.TemplateResponse(
            "success.html",
            {
                "request": request,
                "user": user_record,
                "title": "Регистрация успешна!"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Страница списка пользователей
@app.get("/users", response_class=HTMLResponse)
async def users_list(request: Request):
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "users": users_db,
            "title": "Список пользователей"
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)