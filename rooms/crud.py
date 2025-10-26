from .models import Room
import random
from tortoise.exceptions import DoesNotExist


async def generate_room_code():
    return ''.join(str(random.randint(0, 9)) for _ in range(8))


async def create_room():
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
