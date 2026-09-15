"""
Django settings for DjangoProject.

Local development:
- SQLite database
- Local media storage
- DEBUG enabled by default

Production on Render:
- PostgreSQL through DATABASE_URL
- WhiteNoise static-file serving
- Private Cloudflare R2 media storage
- Production security settings
"""

import os
from pathlib import Path

import dj_database_url


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def env_bool(name, default=False):
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_list(name, default=""):
    return [
        item.strip()
        for item in os.environ.get(name, default).split(",")
        if item.strip()
    ]


# ---------------------------------------------------------
# Core settings
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

IS_RENDER = "RENDER" in os.environ

DEBUG = env_bool(
    "DJANGO_DEBUG",
    default=not IS_RENDER,
)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "development-only-secret-key"
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY must be configured in production."
        )


# ---------------------------------------------------------
# Hosts and CSRF
# ---------------------------------------------------------

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost",
)

RENDER_EXTERNAL_HOSTNAME = os.environ.get(
    "RENDER_EXTERNAL_HOSTNAME"
)

if (
    RENDER_EXTERNAL_HOSTNAME
    and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS
):
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS"
)

if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"

    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)


# ---------------------------------------------------------
# Applications
# ---------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",

    "accounts",
    "athletes",
    "coaches.apps.CoachesConfig",
    "parents_portal",
    "surveys",
    "performance_testing",
    "communications",
    "reports",
    "practice_planner",
    "video_library",
    "pathway",
    "routine_tracker",
    "gyms",
]


# ---------------------------------------------------------
# Middleware
# ---------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # WhiteNoise must be directly after SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ---------------------------------------------------------
# URL and template configuration
# ---------------------------------------------------------

ROOT_URLCONF = "DjangoProject.urls"

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django.DjangoTemplates"
        ),
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors.request"
                ),
                (
                    "django.contrib.auth.context_processors.auth"
                ),
                (
                    "django.contrib.messages."
                    "context_processors.messages"
                ),
                (
                    "communications.context_processors."
                    "communication_context"
                ),
            ],
        },
    },
]

WSGI_APPLICATION = "DjangoProject.wsgi.application"


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ---------------------------------------------------------
# Custom user model and authentication
# ---------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"


# ---------------------------------------------------------
# Password validation
# ---------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ---------------------------------------------------------
# Internationalization
# ---------------------------------------------------------

LANGUAGE_CODE = "en-us"

# Change this to America/Toronto if event times are Ontario-based.
TIME_ZONE = os.environ.get(
    "DJANGO_TIME_ZONE",
    "America/Toronto",
)

USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------
# Static files
# ---------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}


# ---------------------------------------------------------
# Uploaded media and Supabase Storage
# ---------------------------------------------------------

SUPABASE_S3_ENDPOINT = os.environ.get(
    "SUPABASE_S3_ENDPOINT"
)

SUPABASE_S3_REGION = os.environ.get(
    "SUPABASE_S3_REGION"
)

SUPABASE_S3_ACCESS_KEY_ID = os.environ.get(
    "SUPABASE_S3_ACCESS_KEY_ID"
)

SUPABASE_S3_SECRET_ACCESS_KEY = os.environ.get(
    "SUPABASE_S3_SECRET_ACCESS_KEY"
)

SUPABASE_STORAGE_BUCKET = os.environ.get(
    "SUPABASE_STORAGE_BUCKET"
)

USE_SUPABASE_STORAGE = all(
    [
        SUPABASE_S3_ENDPOINT,
        SUPABASE_S3_REGION,
        SUPABASE_S3_ACCESS_KEY_ID,
        SUPABASE_S3_SECRET_ACCESS_KEY,
        SUPABASE_STORAGE_BUCKET,
    ]
)

if USE_SUPABASE_STORAGE:
    INSTALLED_APPS.append("storages")

    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": SUPABASE_S3_ACCESS_KEY_ID,
            "secret_key": SUPABASE_S3_SECRET_ACCESS_KEY,
            "bucket_name": SUPABASE_STORAGE_BUCKET,
            "endpoint_url": SUPABASE_S3_ENDPOINT,
            "region_name": SUPABASE_S3_REGION,
            "signature_version": "s3v4",
            "addressing_style": "path",
            "default_acl": None,
            "file_overwrite": False,
            "querystring_auth": True,
            "querystring_expire": int(
                os.environ.get(
                    "SUPABASE_SIGNED_URL_EXPIRY",
                    "3600",
                )
            ),
        },
    }

else:
    STORAGES["default"] = {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
        ),
    }

    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
# ---------------------------------------------------------
# File-upload limits
# ---------------------------------------------------------

# Maximum in-memory request body: 500 MB.
# Larger videos should eventually use direct-to-R2 uploads.
DATA_UPLOAD_MAX_MEMORY_SIZE = 500 * 1024 * 1024

# Files larger than 5 MB are streamed to a temporary file.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024


# ---------------------------------------------------------
# Production security
# ---------------------------------------------------------

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = env_bool(
        "DJANGO_SECURE_SSL_REDIRECT",
        True,
    )

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Start HSTS at one hour. Increase after confirming HTTPS works.
    SECURE_HSTS_SECONDS = int(
        os.environ.get(
            "DJANGO_SECURE_HSTS_SECONDS",
            "3600",
        )
    )

    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
        "DJANGO_HSTS_INCLUDE_SUBDOMAINS",
        False,
    )

    SECURE_HSTS_PRELOAD = env_bool(
        "DJANGO_HSTS_PRELOAD",
        False,
    )


# ---------------------------------------------------------
# General settings
# ---------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"