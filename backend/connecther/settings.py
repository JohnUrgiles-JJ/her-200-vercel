"""
Django settings for the ConnectHER backend.

Values that change between machines (secrets, API keys, email) come from
backend/.env, loaded below with python-dotenv. See .env.example.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    """Read a true/false env var ("true", "1", "yes" count as true)."""
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# --- Core ---------------------------------------------------------------

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or "dev-secret-change-me"
DEBUG = env_bool("DEBUG", default=True)

# Hackathon only: accept any host.
ALLOWED_HOSTS = ["*"]


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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

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


# --- Email --------------------------------------------------------------

# Console backend by default (emails print in the server terminal).
# For real Gmail, set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# and EMAIL_HOST_USER / EMAIL_HOST_PASSWORD (a Gmail app password) in .env.
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND") or "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = (
    f"ConnectHER <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "ConnectHER <noreply@connecther.local>"
)


# --- App settings -------------------------------------------------------

FRONTEND_URL = os.getenv("FRONTEND_URL") or "http://localhost:5173"


# --- Internationalization / static ----------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
