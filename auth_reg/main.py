import logging
from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException, Depends, Response
from fastapi.middleware import Middleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER

from database import UserRepository

user_repository = UserRepository()

from jwtapi import *

app = FastAPI(title="Система регистрации", version="1.0.0", middleware=[Middleware(AuthMiddleware)])

logging.basicConfig(filename="auth_reg.log", level=logging.INFO)

# Получаем абсолютный путь к директории проекта
BASE_DIR = Path(__file__).parent

# Подключаем статические файлы с абсолютными путями
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Подключаем шаблоны
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user_data: dict = Depends(get_current_user_without_401)):
    await user_repository.create_defoult_admin()
    if current_user_data:
        return RedirectResponse(url="/auth/homepage", status_code=301)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Главная страница"
        }
    )


@app.get("/homepage", response_class=HTMLResponse)
async def home(request: Request, current_user_data: dict = Depends(get_current_user)):
    full_name = '{0} {1} {2}'.format(current_user_data['first_name'], current_user_data['last_name'], current_user_data.get('middle_name', ''))
    is_admin = current_user_data.get('is_admin', False)
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
async def index(request: Request, current_user_data: dict = Depends(get_current_user)):
    if not current_user_data.get('is_admin', False):
        return RedirectResponse(f"/auth/homepage", status_code=301)
    return RedirectResponse(f"/rooms/create_room", status_code=301)

@app.post("/connection_room", response_class=HTMLResponse)
async def connection_room(request: Request, link: str = Form(...)):
    return RedirectResponse(url=f"/rooms/room/{link}", status_code=301)


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
        position: str = Form(...),
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
            return RedirectResponse(url="/auth/sign", status_code=HTTP_303_SEE_OTHER)

        # Регистрируем пользователя
        user_record = await user_repository.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            position=position,
            password=password
        )

        # Формируем payload для токена
        token_data = {
            "id": user_record.id,
            "email": user_record.email,
            "first_name": user_record.first_name,
            "last_name": user_record.last_name,
            "middle_name": user_record.middle_name,
            "position": user_record.position,
            "is_admin": user_record.is_admin
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        response = RedirectResponse(url="/auth/homepage", status_code=HTTP_303_SEE_OTHER)

        # Ставим cookie
        response.set_cookie(
            key=ACCESS_COOKIE_NAME,
            value=access_token,
            httponly=True,
            secure=True,
            samesite="none",
            domain=COOKIE_DOMAIN,
            path="/"
        )
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="none",
            domain=COOKIE_DOMAIN,
            path="/refresh"
        )

        # Перенаправляем на домашнюю страницу
        return response

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

        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 6 символов")

        response_user = await user_repository.get_sign_user(email, password)
        if not response_user['status']:
            raise HTTPException(status_code=400, detail=response_user['response'])

        user_record = response_user['user']

        token_data = {
            'email': user_record.email,
            'first_name': user_record.first_name,
            'last_name': user_record.last_name,
            'middle_name': user_record.middle_name,
            'position': user_record.position,
            'is_admin': user_record.is_admin
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        response = RedirectResponse(url="/auth/homepage", status_code=HTTP_303_SEE_OTHER)

        response.set_cookie(
            key=ACCESS_COOKIE_NAME,
            value=access_token,
            httponly=True,
            secure=True,
            samesite="none",
            domain=COOKIE_DOMAIN,
            path="/"
        )
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="none",
            domain=COOKIE_DOMAIN,
            path="/refresh"
        )

        return response

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


@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/auth", status_code=303)

    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="none",
        domain=COOKIE_DOMAIN,
        path="/"
    )

    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="none",
        domain=COOKIE_DOMAIN,
        path="/refresh"
    )

    return response


@app.post("/refresh")
async def refresh(request: Request, response: Response):
    logging.info("start refresh")
    # Когда access просрочен — клиент может вызвать этот endpoint (или автоматом)
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="no_refresh_token")

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="invalid_token_type")

    # payload содержит sub=user_id, но нам нужно актуальные данные => получим из БД
    uid = payload.get("sub")
    response_user = user_repository.get_user_by_id(uid)
    user_record = response_user['user']
    if not user_record:
        raise HTTPException(status_code=401, detail="user_not_found")

    token_data = {
        "id": user_record.id,
        "email": user_record.email,
        "first_name": user_record.first_name,
        "last_name": user_record.last_name,
        "middle_name": user_record.middle_name,
        "position": user_record.position,
        "is_admin": user_record.is_admin
    }

    new_access = create_access_token(token_data)
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=new_access,
        httponly=True,
        secure=True,
        samesite="none",
        domain=COOKIE_DOMAIN,
        path="/"
    )
    logging.info("end refresh")
    return {"status": "ok"}


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


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # Если пользователь не авторизован -> отправляем на /auth
    if exc.status_code == 401:
        return RedirectResponse(url="/auth", status_code=302)

    # Для других ошибок — свой HTML-шаблон или JSON
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)