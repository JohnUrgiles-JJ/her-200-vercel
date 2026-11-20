from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework.authtoken.models import Token

from .notify import user_group


@database_sync_to_async
def _user_id_for(key):
    token = Token.objects.filter(key=key).first()
    return token.user_id if token else None


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """ws/notifications/?token=<DRF token>"""

    async def connect(self):
        key = parse_qs(self.scope["query_string"].decode()).get("token", [None])[0]
        self.user_id = await _user_id_for(key) if key else None
        if not self.user_id:
            await self.close(code=4401)
            return
        self.group = user_group(self.user_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if getattr(self, "user_id", None):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notify(self, event):
        await self.send_json(event["payload"])
