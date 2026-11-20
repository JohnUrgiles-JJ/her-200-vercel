import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.mail import send_mail

log = logging.getLogger(__name__)


def user_group(user_id: int) -> str:
    return f"user_{user_id}"


def push(user_id: int, payload: dict) -> None:
    try:
        async_to_sync(get_channel_layer().group_send)(user_group(user_id), {"type": "notify", "payload": payload})
    except Exception:
        log.exception("WebSocket push failed for user %s", user_id)


def email(to: str, subject: str, body: str) -> None:
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to])
    except Exception:
        log.exception("Email to %s failed", to)
