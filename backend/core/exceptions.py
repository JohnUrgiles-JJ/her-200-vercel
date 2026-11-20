"""JSON errors everywhere under /api/, so the frontend never has to parse an HTML error page.

Two layers:
- api_exception_handler (DRF's EXCEPTION_HANDLER): an unhandled exception inside a DRF view becomes
  500 {"detail": SERVER_ERROR} (logged with its traceback) instead of Django's HTML 500 / debug page.
- ApiJsonErrorMiddleware: any other non-JSON error response under /api/ (an unknown /api/ path's HTML 404,
  an exception outside DRF, ...) is replaced with {"detail": "..."} and the same status code. It also
  serves /api/<route> without its trailing slash as /api/<route>/ (see _add_missing_slash).
"""

import logging
from http import HTTPStatus

from django.http import JsonResponse
from django.urls import is_valid_path
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

logger = logging.getLogger(__name__)

SERVER_ERROR = "Something went wrong on our side. Please try again."
API_PREFIX = "/api/"


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:  # APIException, Http404, PermissionDenied: DRF already made a JSON response
        return response
    request = context.get("request")
    logger.error(
        "Unhandled exception in %s %s",
        getattr(request, "method", "?"), getattr(request, "path", "?"),
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    set_rollback()  # like DRF does for its own errors: undo an ATOMIC_REQUESTS transaction, if any
    return Response({"detail": SERVER_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _detail_for(code):
    if code >= 500:
        return SERVER_ERROR
    if code == 404:
        return "Not found."
    try:
        return f"{HTTPStatus(code).phrase}."
    except ValueError:
        return "Request failed."


class ApiJsonErrorMiddleware:
    """Turns non-JSON 4xx/5xx responses under /api/ into {"detail": "..."} with the same status.

    Sits right after CorsMiddleware, so the JSON error still gets CORS headers and the browser shows the
    real status instead of a CORS error. Django turns a view exception into an (HTML) 500 response before
    it reaches this middleware, so that case is covered here too.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._add_missing_slash(request)
        response = self.get_response(request)
        if (
            request.path.startswith(API_PREFIX)
            and response.status_code >= 400
            and not response.get("Content-Type", "").startswith("application/json")
        ):
            replacement = JsonResponse({"detail": _detail_for(response.status_code)}, status=response.status_code)
            for header in ("Allow", "WWW-Authenticate", "Retry-After"):
                if header in response:
                    replacement[header] = response[header]
            return replacement
        return response

    @staticmethod
    def _add_missing_slash(request):
        """`POST /api/questions` (no slash) is served as `/api/questions/` instead of failing.

        Django's APPEND_SLASH can only redirect, and it can't redirect a POST (DEBUG raises, which became a
        500). A forgotten slash in the frontend is an easy demo-day mistake, so fix it up here, but only
        when the slashed path is a real route.
        """
        path = request.path_info
        if path.startswith(API_PREFIX) and not path.endswith("/") and is_valid_path(f"{path}/", getattr(request, "urlconf", None)):
            request.path_info = f"{path}/"
            request.path = f"{request.path}/"
