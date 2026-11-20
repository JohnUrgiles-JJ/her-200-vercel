"""WebSocket auth: `?token=<DRF token key>` in the URL sets scope["user"].

Browsers can't send an Authorization header on a WebSocket, so the same DRF token the REST API uses goes
in the query string: ws://localhost:8000/ws/notifications/?token=<key>
"""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


def token_from_scope(scope):
    """The `token` query-string value, or "" if there isn't one."""
    raw = scope.get("query_string", b"")
    try:
        query = parse_qs(raw.decode("latin-1"))
    except Exception:  # malformed query string: treat as no token
        return ""
    values = query.get("token") or [""]
    return values[0].strip()


@database_sync_to_async  # runs in a worker thread and closes stale DB connections before and after
def get_user_for_token(key):
    if not key:
        return AnonymousUser()
    try:
        user = Token.objects.select_related("user").get(key=key).user
    except Token.DoesNotExist:
        return AnonymousUser()
    return user if user.is_active else AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    """Sets scope["user"] to the token's User, or AnonymousUser if the token is missing, unknown or the
    user is inactive. Never raises: a database error also gives AnonymousUser (and is logged)."""

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        try:
            scope["user"] = await get_user_for_token(token_from_scope(scope))
        except Exception:
            logger.exception("WebSocket token lookup failed")
            scope["user"] = AnonymousUser()
        return await super().__call__(scope, receive, send)
