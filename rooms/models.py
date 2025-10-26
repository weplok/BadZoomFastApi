from tortoise import fields
from tortoise.models import Model

class Room(Model):
    id = fields.IntField(pk=True)
    code = fields.CharField(max_length=8, unique=True)

    class Meta:
        table = "rooms"
