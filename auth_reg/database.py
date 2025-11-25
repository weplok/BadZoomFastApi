import asyncio

from tortoise import Tortoise, fields
from tortoise.models import Model
from tortoise.transactions import in_transaction
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging


logger = logging.getLogger(__name__)

# Константы
DB_URL = 'sqlite://{name_db}.db'


class DatabaseManager:
    """Менеджер для работы с базой данных"""

    def __init__(self, db_name: str = "auth_reg.db"):
        self.db_name = db_name
        self.db_url = f'sqlite://{db_name}'
        self._initialized = False

    async def init_db(self):
        """Инициализация базы данных и подключение к ней"""
        if self._initialized:
            logger.info("База данных уже инициализирована")
            await Tortoise.generate_schemas()
            logger.info("Подключение к БД успешно")
            return

        try:
            await Tortoise.init(
                db_url=self.db_url,
                modules={"models": ["database"]},
            )
            await Tortoise.generate_schemas()
            self._initialized = True
            logger.info(f"База данных {self.db_name} успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    async def close_db(self):
        """Закрытие подключений к БД"""
        if self._initialized:
            await Tortoise.close_connections()
            self._initialized = False
            logger.info("Подключения к БД закрыты")

    @asynccontextmanager
    async def session(self):
        """Контекстный менеджер для сессии БД"""
        try:
            await self.init_db()
            yield
        except Exception as e:
            logger.error(f"Ошибка в сессии БД: {e}")
            raise
        finally:
            await self.close_db()

    @asynccontextmanager
    async def transaction(self):
        """Контекстный менеджер для транзакций"""
        async with self.session():
            async with in_transaction() as transaction:
                try:
                    yield transaction
                except Exception as e:
                    logger.error(f"Ошибка в транзакции, откат: {e}")
                    await transaction.rollback()
                    raise

# Создаем экземпляр менеджера БД
db_manager = DatabaseManager()


# ---------------------
# Утилиты
# ---------------------

async def init_database():
    """Инициализация базы данных (отдельная функция)"""
    await db_manager.init_db()

async def close_database():
    """Закрытие базы данных (отдельная функция)"""
    await db_manager.close_db()


# ---------------------
# Модели данных
# ---------------------
class User(Model):
    """
    email - почта
    first_name - имя
    last_name - фамилия
    middle_name - отчество
    position - должность
    password - пароль
    is_connecting_to_rooms - подключение к комнатам
    is_creating_rooms - создание комнат
    is_admin - статус админа
    """
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=250, null=True)
    first_name = fields.CharField(max_length=50, null=True)
    last_name = fields.CharField(max_length=50, null=True)
    middle_name = fields.CharField(max_length=50, null=True)
    position = fields.CharField(max_length=250, null=True)
    password = fields.CharField(max_length=250, null=True)
    is_connecting_to_rooms = fields.BooleanField(default=False)
    is_creating_rooms = fields.BooleanField(default=False)
    is_admin = fields.BooleanField(default=False)

    class Meta:
        table = "users"

    def __str__(self):
        return f"User({self.id}: {self.email})"

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование объекта в словарь"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'middle_name': self.middle_name,
            'position': self.position,
            'is_connecting_to_rooms': self.is_connecting_to_rooms,
            'is_creating_rooms': self.is_creating_rooms,
            'is_admin': self.is_admin
        }


# ---------------------
# CRUD операции для User
# ---------------------

class UserRepository:
    """Репозиторий для работы с пользователями"""

    @staticmethod
    async def create_user(
            email: str,
            password: str,
            first_name: str = None,
            last_name: str = None,
            middle_name: str = None,
            position: str = None,
            is_connecting_to_rooms: bool = False,
            is_creating_rooms: bool = False,
            is_admin: bool = False
    ) -> User:
        """Создание нового пользователя"""
        async with db_manager.session():
            user = await User.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                position=position,
                password=password,
                is_connecting_to_rooms=is_connecting_to_rooms,
                is_creating_rooms=is_creating_rooms,
                is_admin=is_admin
            )
            logger.info(f"Создан пользователь: {user.email}")
            return user

    @staticmethod
    async def create_defoult_admin() -> User:
        """Создание дефолтного аккаунта админа"""
        async with db_manager.session():
            admin_email = 'Admin@gmail.com'

            response_admin = await User.filter(email=admin_email).first()
            if response_admin:
                logger.info(f"Дефолтный аккаунт админа уже создан: {response_admin.email}")
                return response_admin

            user = await User.create(
                email=admin_email,
                first_name='Админ',
                last_name='Царь',
                middle_name='Конференций',
                position='Директор',
                password='admin1234',
                is_connecting_to_rooms=True,
                is_creating_rooms=True,
                is_admin=True
            )
            logger.info(f"Создан дефолтный аккаунт админа: {user.email}")
            return user

    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        async with db_manager.session():
            user = await User.filter(id=user_id).first()
            return user

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """Получение пользователя по email"""
        async with db_manager.session():
            user = await User.filter(email=email).first()
            return user

    @staticmethod
    async def get_sign_user(email: str, password: str) -> Dict[str, Any]:
        async with db_manager.session():
            response_email = await User.filter(email=email).first()
            if response_email is None:
                return {'status': False, 'response': 'Email не найден', 'user': None}

            response_user = await User.filter(email=email, password=password).first()
            if response_user is None:
                return {'status': False, 'response': 'Не верный пароль', 'user': None}

            return {'status': True, 'response': 'Пользователь найден', 'user': response_user}


    @staticmethod
    async def get_all_users() -> List[User]:
        """Получение всех пользователей"""
        async with db_manager.session():
            users = await User.all()
            return users

    @staticmethod
    async def update_user(user_id: int, **kwargs) -> Optional[User]:
        """Обновление данных пользователя"""
        async with db_manager.session():
            user = await User.filter(id=user_id).first()
            if user:
                await user.update_from_dict(kwargs).save()
                logger.info(f"Обновлен пользователь: {user.email}")
                return user
            return None

    @staticmethod
    async def delete_user(user_id: int) -> bool:
        """Удаление пользователя"""
        async with db_manager.session():
            user = await User.filter(id=user_id).first()
            if user:
                await user.delete()
                logger.info(f"Удален пользователь: {user.email}")
                return True
            return False
