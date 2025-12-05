import random
from tortoise import Tortoise, fields
from tortoise.models import Model
from tortoise.transactions import in_transaction
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional, AsyncGenerator
from tortoise.exceptions import DoesNotExist
import logging


logger = logging.getLogger(__name__)

# Константы
DB_URL = 'sqlite://{name_db}.db'


class DatabaseManager:
    """Менеджер для работы с базой данных"""

    def __init__(self, db_name: str = "rooms.db"):
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
class Room(Model):
    """
    title - название
    code - сгенерированный код
    """
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255, default="Комната")
    code = fields.CharField(max_length=8, unique=True)

    class Meta:
        table = "rooms"

    def __str__(self):
        return f"Room({self.id}: {self.title})"

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование объекта в словарь"""
        return {
            "id": self.id,
            "title": self.title,
            "code": self.code,
        }

# ---------------------
# CRUD операции для Rooms
# ---------------------
class RoomRepository:
    """Репозиторий для работы с комнатами"""

    @staticmethod
    async def create_room(
            title: str,
            code: str
    ) -> Room:
        """Создание новой комнаты"""
        async with db_manager.session():
            room = await Room.create(
                title=title,
                code=code
            )
            logger.info(f'Создана комната: {room.code}')
            return room

    @staticmethod
    async def get_room_by_id(room_id: int):
        """Получение комнаты по ID"""
        async with db_manager.session():
            try:
                room = await Room.filter(id=room_id).first()
                return room
            except DoesNotExist:
                return None

    @staticmethod
    async def get_room_by_code(code: str):
        """Получение комнаты по CODE"""
        async with db_manager.session():
            try:
                room = await Room.filter(code=code).first()
                return room
            except DoesNotExist:
                return None

    @staticmethod
    async def delete_room(room_id: int) -> bool:
        """Удаление комнаты"""
        async with db_manager.session():
            user = await Room.filter(id=room_id).first()
            if user:
                await user.delete()
                logger.info(f"Удалена комната: {user.title}")
                return True
            return False