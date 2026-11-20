"""
Django settings for the ConnectHER backend.

Values that change between machines (secrets, API keys, email) come from
backend/.env, loaded below with python-dotenv. See .env.example.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Local dev reads backend/.env. On Railway there is no .env file; variables come
# from the service's Variables tab. load_dotenv never overrides real env vars.
load_dotenv(BASE_DIR / ".env")


def env_list(name):
    """Read a comma-separated env var as a list, dropping empty items."""
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


# --- Core ---------------------------------------------------------------

DEBUG = os.getenv("DEBUG", "true").lower() == "true"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-secret-change-me"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is not set. It is required when DEBUG is false (production). "
            "Set it in Railway's Variables tab."
        )

# HACKATHON ONLY: accept any Host header. This also covers Railway's
# healthcheck host (healthcheck.railway.app). Lock this down for a real launch.
ALLOWED_HOSTS = ["*"]

# Railway terminates HTTPS at its edge and forwards plain HTTP with
# X-Forwarded-Proto, so this makes request.is_secure() true behind it.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

FRONTEND_URL = (os.getenv("FRONTEND_URL") or "http://localhost:5173").rstrip("/")

# Needed for POSTs from a browser session (e.g. the Django admin login) over HTTPS.
CSRF_TRUSTED_ORIGINS = ["https://*.up.railway.app"]
if os.getenv("FRONTEND_URL"):
    CSRF_TRUSTED_ORIGINS.append(FRONTEND_URL)


# --- Apps ---------------------------------------------------------------

INSTALLED_APPS = [
    "daphne",  # must be first so `runserver` uses the ASGI (Daphne) server
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "corsheaders",
    "channels",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be first
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # directly after SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "connecther.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "connecther.wsgi.application"
ASGI_APPLICATION = "connecther.asgi.application"


# --- Channels (WebSockets) ----------------------------------------------

# In-memory layer: no Redis needed, but only works inside ONE server process.
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}


# --- Database -----------------------------------------------------------

# Railway sets DATABASE_URL (Postgres). Without it, local dev uses SQLite.
# conn_max_age=0 (close the connection after each request) because Django's docs
# say: "When using ASGI, persistent connections should be disabled." We run Daphne (ASGI).
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=0,
        conn_health_checks=True,
    )
}
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    # Fail fast instead of hanging if Postgres is unreachable (libpq waits forever by
    # default), so /api/health/ can actually report "db": false.
    DATABASES["default"].setdefault("OPTIONS", {}).setdefault("connect_timeout", 5)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Auth ---------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Django REST Framework ----------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Swagger UI at /api/docs/, raw OpenAPI schema at /api/schema/.
# Click "Authorize" and enter: Token <your-token>
SPECTACULAR_SETTINGS = {
    "TITLE": "ConnectHER API",
    "DESCRIPTION": "Backend API for ConnectHER.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
}


# --- CORS (React dev server) --------------------------------------------

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if os.getenv("FRONTEND_URL"):
    CORS_ALLOWED_ORIGINS.append(FRONTEND_URL)
# Optional extra origins, comma-separated, e.g. a Vercel preview URL.
CORS_ALLOWED_ORIGINS += [origin.rstrip("/") for origin in env_list("EXTRA_CORS_ORIGINS")]
CORS_ALLOWED_ORIGINS = list(dict.fromkeys(CORS_ALLOWED_ORIGINS))  # drop duplicates


# --- Email --------------------------------------------------------------

# Console backend by default (emails print in the server terminal).
# For real Gmail, set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# and EMAIL_HOST_USER / EMAIL_HOST_PASSWORD (a Gmail app password) in .env.
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND") or "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
# Gmail shows app passwords as "abcd efgh ijkl mnop"; the spaces aren't part of it, so strip them.
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").replace(" ", "")
DEFAULT_FROM_EMAIL = (
    f"ConnectHER <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "ConnectHER <noreply@connecther.local>"
)
# Seconds before an SMTP connect/send gives up. Emails are sent off the request thread, but a hung
# Gmail connection shouldn't keep a thread alive forever.
EMAIL_TIMEOUT = 10
# True sends notification emails inline instead of on a background thread. Tests set it; leave it off
# otherwise so SMTP never slows an API response.
NOTIFY_EMAILS_SYNC = os.getenv("NOTIFY_EMAILS_SYNC", "false").lower() == "true"


# --- App settings -------------------------------------------------------

# FRONTEND_URL is defined near the top (CORS/CSRF use it).


# --- Internationalization / static ----------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (the Django admin's CSS/JS) are collected into STATIC_ROOT by
# `collectstatic` and served by WhiteNoise, so no separate file server is needed.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# --- Logging --------------------------------------------------------------

# Everything goes to stdout/stderr, which Railway shows in the service's logs.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "core": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
