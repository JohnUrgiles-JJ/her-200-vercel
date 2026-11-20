"""
ASGI entry point for ConnectHER (served by Daphne via `runserver`).

Phase 0: HTTP only. Phase 5 adds a "websocket" route for live notifications.
"""

import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "connecther.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
    }
)
