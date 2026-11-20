"""
ASGI entry point for ConnectHER (served by Daphne, both through `runserver` and in production).

HTTP goes to Django. WebSockets: ws://<host>/ws/notifications/?token=<DRF token key> (Section 3.3).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "connecther.settings")

# Must run before importing anything that touches models (consumers, ws_auth): it sets Django up.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.urls import re_path  # noqa: E402

from core.consumers import NotificationConsumer  # noqa: E402
from core.ws_auth import TokenAuthMiddleware  # noqa: E402

websocket_urlpatterns = [
    # The contract URL is /ws/notifications/; the trailing slash is optional so a client typo still connects.
    re_path(r"^ws/notifications/?$", NotificationConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
