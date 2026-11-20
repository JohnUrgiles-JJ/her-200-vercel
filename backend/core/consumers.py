"""Live notifications. Each authenticated socket joins the group f"user_{user.id}"; core.notify.push()
sends {"type": "notify", "payload": {...}} to that group and notify() below forwards the payload as JSON.

Event shapes are fixed by Section 3.3 of the plan (the React frontend depends on them).
"""

import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)

CLOSE_UNAUTHORIZED = 4401


def group_for(user_id):
    return f"user_{user_id}"


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    group_name = None

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            # Accept first, then close: a close sent before accept becomes an HTTP 403 on the handshake and
            # the browser only ever sees code 1006. This way the client gets 4401 and can tell "bad token"
            # (log in again, don't retry) apart from a network drop (reconnect).
            await self.accept()
            await self.close(code=CLOSE_UNAUTHORIZED)
            return
        self.group_name = group_for(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("WebSocket connected: user %s", user.id)

    async def disconnect(self, code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info("WebSocket disconnected: %s (code %s)", self.group_name, code)
            self.group_name = None

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        # The server only sends. Junk (non-JSON, binary) is ignored instead of crashing the socket.
        if text_data is None:
            return
        try:
            content = json.loads(text_data)
        except ValueError:
            return
        await self.receive_json(content, **kwargs)

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("event") == "ping":
            await self.send_json({"event": "pong"})

    async def notify(self, event):
        """Handler for {"type": "notify", "payload": {...}} group messages."""
        await self.send_json(event["payload"])
